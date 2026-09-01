"""Core disk scanning functionality.

The scanner keeps every directory in dense, integer-indexed parallel arrays
rather than in ``Path``-keyed dictionaries. Because a directory is always
discovered after its parent, ``_parent[i] < i`` holds for every ``i > 0``, which
turns subtree accounting into a single reverse pass with no recursion and no
per-file ancestor walking.

Traversal itself lives in :mod:`reclaimed.core.walk` so it can run in worker
threads. The algorithm is expressed once, in :meth:`DiskScanner._engine`, as a
generator that asks for work and is fed results; the sync and async entry points
are thin drivers over it and share no scanning logic.
"""

import asyncio
import heapq
import json
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import (
    AsyncIterator,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.formatters import format_size
from .errors import DiskScannerError, InvalidPathError, ScanInterruptedError
from .types import FileInfo, ScanOptions, ScanProgress, ScanResult
from .walk import (
    MOBILE_DOCUMENTS,
    DirListing,
    WalkContext,
    WalkJob,
    is_onedrive_root_name,
    list_chunk,
)

#: Seconds between progress emissions. The Textual UI throttles further.
EMIT_INTERVAL = 1.0

#: Directories dispatched per batch. Starts small so the first results paint
#: quickly, then grows to amortise dispatch overhead across a large tree.
FIRST_BATCH = 64
MAX_BATCH = 1024

#: Upper bound on worker threads. Measured on APFS: 4 threads scan ~1.1M files
#: in 12.2s, 8 in 12.6s, 16 in 16.2s. More workers actively hurt.
MAX_WORKERS = 8
DEFAULT_WORKERS = 4


class _Work(NamedTuple):
    """Engine request: list these directories and send the listings back."""

    jobs: List[WalkJob]


class _Emit(NamedTuple):
    """Engine request: surface this progress snapshot, if anyone is watching."""

    progress: ScanProgress


_Request = Union[_Work, _Emit]


class DiskScanner:
    """Core scanning logic for analyzing disk usage."""

    def __init__(self, options: Optional[ScanOptions] = None, console: Optional[Console] = None):
        """Initialize the scanner.

        Args:
            options: Scanning configuration options
            console: Optional Rich console for output
        """
        self.options = options or ScanOptions()
        self.console = console or Console()
        self._access_issues: Dict[Path, str] = {}
        self._total_size = 0
        self._file_count = 0
        #: Results from the most recent interrupted scan, if any.
        self.last_partial_result: Optional[ScanResult] = None
        #: Immutable snapshot from the most recent successfully completed scan.
        self.last_result: Optional[ScanResult] = None
        self._reset_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, root_path: Path) -> ScanResult:
        """Scan a directory synchronously.

        Args:
            root_path: Directory to scan

        Returns:
            Complete scan results

        Raises:
            InvalidPathError: If root_path is not a directory
            ScanInterruptedError: If scanning is interrupted. The results
                gathered so far are attached as ``.partial``.
        """
        if not root_path.is_dir():
            raise InvalidPathError(root_path, "Not a directory")

        self._reset_state(root_path)
        engine = self._engine()
        executor = self._make_pool(always=False)
        progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", markup=False),
            console=self.console,
            transient=True,
            disable=not self.console.is_terminal,
        )
        try:
            with progress:
                task = progress.add_task("Starting scan…", total=None)
                current_directory = str(root_path)
                try:
                    request = next(engine)
                    while True:
                        if isinstance(request, _Work):
                            if request.jobs:
                                current_directory = request.jobs[-1].path
                            request = engine.send(self._run_batch(executor, request.jobs))
                        else:
                            progress.update(
                                task,
                                description=(
                                    f"{request.progress.scanned:,} files • "
                                    f"{format_size(request.progress.total_size)} • "
                                    f"{current_directory}"
                                ),
                            )
                            request = engine.send(None)
                except StopIteration:
                    pass
            result = self._build_result()
            self.last_result = result
            return result
        except KeyboardInterrupt:
            raise self._interrupted() from None
        finally:
            engine.close()
            if executor is not None:
                executor.shutdown(wait=False)

    async def scan_async(self, root_path: Path) -> AsyncIterator[ScanProgress]:
        """Scan a directory asynchronously, yielding progress updates.

        Args:
            root_path: Directory to scan

        Yields:
            ScanProgress updates during scanning, ending with a final snapshot
            whose directory sizes are exact at every depth.

        Raises:
            InvalidPathError: If root_path is not a directory
            ScanInterruptedError: If scanning is interrupted
        """
        if not root_path.is_dir():
            raise InvalidPathError(root_path, "Not a directory")

        self._reset_state(root_path)
        loop = asyncio.get_running_loop()
        engine = self._engine()
        # Always use a pool here, even for a single worker, so that blocking
        # scandir calls never run on the event loop driving the UI.
        executor = self._make_pool(always=True)
        assert executor is not None
        try:
            try:
                request = next(engine)
                while True:
                    if isinstance(request, _Work):
                        listings = await self._run_batch_async(loop, executor, request.jobs)
                        request = engine.send(listings)
                    else:
                        yield request.progress
                        request = engine.send(None)
            except StopIteration:
                pass
            except KeyboardInterrupt:
                raise self._interrupted() from None
        finally:
            # Never yield from here: an async generator that yields while
            # handling GeneratorExit raises RuntimeError.
            engine.close()
            executor.shutdown(wait=False)

        result = self._build_result()
        self.last_result = result
        yield ScanProgress(
            progress=1.0,
            files=result.files,
            dirs=result.directories,
            scanned=self._file_count,
            total_size=self._total_size,
        )

    # ------------------------------------------------------------------
    # The algorithm
    # ------------------------------------------------------------------

    def _engine(self) -> Generator[_Request, Optional[List[DirListing]], None]:
        """Drive the traversal, requesting work and folding in the results.

        Yields ``_Work`` to have directories listed (the driver sends back the
        listings) and ``_Emit`` to surface progress. Contains the whole
        algorithm; the drivers contribute only their concurrency model.
        """
        frontier = self._frontier
        batch_size = FIRST_BATCH
        last_emit = time.monotonic()

        while frontier:
            jobs = [
                WalkJob(dir_id, self._paths[dir_id])
                for dir_id in (frontier.popleft() for _ in range(min(batch_size, len(frontier))))
            ]
            listings = yield _Work(jobs)
            for listing in listings or ():
                self._absorb(listing, frontier)

            batch_size = min(MAX_BATCH, batch_size * 2)

            now = time.monotonic()
            if not frontier or now - last_emit >= EMIT_INTERVAL:
                last_emit = now
                yield _Emit(self._live_progress())

    def _absorb(self, listing: DirListing, frontier: "deque") -> None:
        """Fold one directory listing into scanner state."""
        dir_id = listing.dir_id
        self._own[dir_id] = listing.own_bytes
        self._file_count += listing.file_count
        self._total_size += listing.own_bytes

        if listing.error is not None:
            self._access_issues[Path(self._paths[dir_id])] = listing.error
        for path, message in listing.entry_errors:
            self._access_issues[Path(path)] = message

        is_icloud = self._icloud[dir_id]
        is_onedrive = self._onedrive[dir_id]
        for size, path, mtime in listing.candidates:
            self._offer_file(size, path, mtime, is_icloud, is_onedrive)

        for name, path in listing.subdirs:
            child_icloud = is_icloud or (
                name == MOBILE_DOCUMENTS
                or (
                    self._icloud_base is not None
                    and name == os.path.basename(self._icloud_base)
                    and os.path.realpath(path) == self._icloud_base
                )
            )
            child_onedrive = (
                is_onedrive
                or is_onedrive_root_name(name)
                or (
                    self._onedrive_base is not None
                    and name.casefold() == os.path.basename(self._onedrive_base).casefold()
                    and os.path.normcase(os.path.realpath(path)) == self._onedrive_base
                )
            )
            frontier.append(self._new_dir(path, dir_id, child_icloud, child_onedrive))

        self._pending_children[dir_id] = len(listing.subdirs)
        if not listing.subdirs:
            self._mark_dir_complete(dir_id)

    def _new_dir(self, path: str, parent: int, is_icloud: bool, is_onedrive: bool) -> int:
        """Register a directory and return its dense id."""
        dir_id = len(self._paths)
        self._paths.append(path)
        self._parent.append(parent)
        self._own.append(0)
        self._icloud.append(is_icloud)
        self._onedrive.append(is_onedrive)
        self._pending_children.append(0)
        self._complete.append(False)
        return dir_id

    def _offer_file(
        self,
        size: int,
        path: str,
        mtime: float,
        is_icloud: bool,
        is_onedrive: bool,
    ) -> None:
        """Offer a file to the bounded top-N heap.

        The tuple carries ``path`` second so that equal sizes are broken by a
        string comparison. Holding a ``Path`` there instead would raise
        TypeError when two paths of different flavours tie.
        """
        limit = self.options.max_files
        if limit <= 0:
            return
        heap = self._file_heap
        if len(heap) < limit:
            heapq.heappush(heap, (size, path, mtime, is_icloud, is_onedrive))
            if len(heap) == limit:
                self._ctx.floor = heap[0][0]
        elif size > heap[0][0]:
            heapq.heapreplace(heap, (size, path, mtime, is_icloud, is_onedrive))
            self._ctx.floor = heap[0][0]
        elif size == heap[0][0]:
            # For equal sizes keep the lexicographically smallest paths. The
            # regular heap root is the smallest path, so locate the worst tie
            # explicitly; this touches at most max_files entries.
            tied = [index for index, item in enumerate(heap) if item[0] == size]
            worst = max(tied, key=lambda index: heap[index][1])
            if path < heap[worst][1]:
                heap[worst] = (size, path, mtime, is_icloud, is_onedrive)
                heapq.heapify(heap)

    def _mark_dir_complete(self, dir_id: int) -> None:
        """Mark a finished subtree complete and propagate to its ancestors."""
        while dir_id >= 0 and not self._complete[dir_id]:
            self._complete[dir_id] = True
            parent = self._parent[dir_id]
            if parent < 0:
                break
            self._pending_children[parent] -= 1
            if self._pending_children[parent] > 0:
                break
            dir_id = parent

    def _rollup(self) -> Tuple[List[int], List[bool], List[bool]]:
        """Compute exact subtree totals for every directory.

        One reverse pass over the arrays. Valid because a directory is always
        discovered after its parent, so every child's index exceeds its own.
        """
        totals = list(self._own)
        icloud = list(self._icloud)
        onedrive = list(self._onedrive)
        parent = self._parent
        for index in range(len(totals) - 1, 0, -1):
            ancestor = parent[index]
            totals[ancestor] += totals[index]
            if icloud[index]:
                icloud[ancestor] = True
            if onedrive[index]:
                onedrive[ancestor] = True
        return totals, icloud, onedrive

    # ------------------------------------------------------------------
    # Result assembly
    # ------------------------------------------------------------------

    def _build_result(self) -> ScanResult:
        totals, icloud, onedrive = self._rollup()
        return ScanResult(
            files=self._top_files(),
            directories=self._top_dirs(totals, icloud, onedrive),
            total_size=self._total_size,
            files_scanned=self._file_count,
            access_issues=dict(self._access_issues),
            actual_size=self.options.actual_size,
        )

    def _top_files(self) -> List[FileInfo]:
        """Largest files, biggest first, ties broken by path for determinism."""
        ordered = sorted(self._file_heap, key=lambda item: (-item[0], item[1]))
        return [
            FileInfo(Path(path), size, mtime, is_icloud, is_onedrive)
            for size, path, mtime, is_icloud, is_onedrive in ordered
        ]

    def _top_dirs(
        self, totals: List[int], icloud: List[bool], onedrive: List[bool]
    ) -> List[FileInfo]:
        """Largest directories, biggest first.

        ``nlargest`` is O(dirs) with a small constant and runs once, replacing a
        full sort of every known directory repeated throughout the scan.
        """
        if not totals:
            return []
        ids = heapq.nlargest(
            max(0, self.options.max_dirs), range(len(totals)), key=totals.__getitem__
        )
        return [
            FileInfo(
                Path(self._paths[i]),
                totals[i],
                self._dir_mtime(i),
                icloud[i],
                onedrive[i],
                self._complete[i],
            )
            for i in ids
        ]

    def _live_progress(self) -> ScanProgress:
        """Snapshot for mid-scan display.

        A reverse rollup over the discovered directories uses no syscalls. A
        directory whose subtree has not yet been walked simply under-reports
        and grows as the scan proceeds.
        """
        totals, icloud, onedrive = self._rollup()
        ids = heapq.nlargest(
            max(0, self.options.max_dirs), range(len(totals)), key=totals.__getitem__
        )
        dirs = [
            FileInfo(
                Path(self._paths[i]),
                totals[i],
                0.0,
                icloud[i],
                onedrive[i],
                self._complete[i],
            )
            for i in ids
        ]
        return ScanProgress(
            progress=min(0.95, self._file_count / (self._file_count + 1000)),
            files=self._top_files(),
            dirs=dirs,
            scanned=self._file_count,
            total_size=self._total_size,
        )

    def _dir_mtime(self, dir_id: int) -> float:
        """Modification time for a directory, stat'd lazily and cached.

        Only directories that actually reach a result are stat'd, which avoids
        one syscall per directory across the whole tree.
        """
        cached = self._mtime_cache.get(dir_id)
        if cached is None:
            try:
                cached = os.stat(self._paths[dir_id]).st_mtime
            except OSError:
                cached = 0.0
            self._mtime_cache[dir_id] = cached
        return cached

    def _interrupted(self) -> ScanInterruptedError:
        """Cancel outstanding work and package up whatever was collected."""
        self._cancel.set()
        partial = self._build_result()
        self.last_partial_result = partial
        return ScanInterruptedError(partial=partial)

    # ------------------------------------------------------------------
    # Concurrency
    # ------------------------------------------------------------------

    def _worker_count(self) -> int:
        configured = self.options.max_workers
        if configured is None:
            return min(DEFAULT_WORKERS, os.cpu_count() or 1)
        return max(1, min(int(configured), MAX_WORKERS))

    def _make_pool(self, always: bool) -> Optional[ThreadPoolExecutor]:
        """Create the worker pool, or None to run listings inline."""
        if self._workers == 1 and not always:
            return None
        return ThreadPoolExecutor(max_workers=self._workers, thread_name_prefix="reclaimed-walk")

    def _split(self, jobs: List[WalkJob]) -> List[List[WalkJob]]:
        """Split a batch into several dynamically scheduled chunks.

        One future per directory would drown the speedup in executor overhead,
        while one large slice per worker leaves fast workers idle behind the
        slowest slice. Four chunks per worker balances both costs.
        """
        step = max(1, -(-len(jobs) // (self._workers * 4)))
        return [jobs[i : i + step] for i in range(0, len(jobs), step)]

    def _run_batch(
        self, executor: Optional[ThreadPoolExecutor], jobs: List[WalkJob]
    ) -> List[DirListing]:
        if not jobs:
            return []
        if executor is None:
            return list_chunk(jobs, self._ctx)
        futures = [executor.submit(list_chunk, chunk, self._ctx) for chunk in self._split(jobs)]
        listings: List[DirListing] = []
        for future in futures:
            listings.extend(future.result())
        return listings

    async def _run_batch_async(
        self,
        loop: asyncio.AbstractEventLoop,
        executor: ThreadPoolExecutor,
        jobs: List[WalkJob],
    ) -> List[DirListing]:
        if not jobs:
            return []
        futures = [
            loop.run_in_executor(executor, list_chunk, chunk, self._ctx)
            for chunk in self._split(jobs)
        ]
        listings: List[DirListing] = []
        for chunk in await asyncio.gather(*futures):
            listings.extend(chunk)
        return listings

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _reset_state(self, root_path: Optional[Path] = None) -> None:
        """Clear per-scan state and seed the root directory."""
        self._paths: List[str] = []
        self._parent: List[int] = []
        self._own: List[int] = []
        self._icloud: List[bool] = []
        self._onedrive: List[bool] = []
        self._pending_children: List[int] = []
        self._complete: List[bool] = []
        self._file_heap: List[Tuple[int, str, float, bool, bool]] = []
        self._mtime_cache: Dict[int, float] = {}
        self._access_issues = {}
        self._total_size = 0
        self._file_count = 0
        self._frontier: "deque" = deque()
        self._workers = self._worker_count()
        self._cancel = threading.Event()
        self._icloud_base = (
            os.path.realpath(os.fspath(self.options.icloud_base))
            if self.options.icloud_base is not None
            else None
        )
        self._onedrive_base = (
            os.path.normcase(os.path.realpath(os.fspath(self.options.onedrive_base)))
            if self.options.onedrive_base is not None
            else None
        )
        self._ctx = WalkContext(
            skip=frozenset(self.options.skip_dirs or ()),
            max_files=self.options.max_files,
            actual_size=self.options.actual_size,
            cancel=self._cancel,
        )

        if root_path is not None:
            self.last_result = None
            self.last_partial_result = None
            root = str(root_path)
            comparable_root = os.path.realpath(root)
            # Seed from the full root string so that a scan rooted inside
            # iCloud is recognised even though its marker lies above the root.
            root_icloud = MOBILE_DOCUMENTS in Path(comparable_root).parts or (
                self._icloud_base is not None
                and (
                    comparable_root == self._icloud_base
                    or comparable_root.startswith(self._icloud_base + os.sep)
                )
            )
            comparable_onedrive_root = os.path.normcase(comparable_root)
            root_onedrive = any(
                is_onedrive_root_name(part) for part in Path(comparable_root).parts
            ) or (
                self._onedrive_base is not None
                and (
                    comparable_onedrive_root == self._onedrive_base
                    or comparable_onedrive_root.startswith(self._onedrive_base + os.sep)
                )
            )
            self._frontier.append(self._new_dir(root, -1, root_icloud, root_onedrive))

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def save_results(
        self, output_path: Path, files: List[FileInfo], dirs: List[FileInfo], scanned_path: Path
    ) -> None:
        """Save the scan results to a JSON file.

        Args:
            output_path: Path to the output JSON file.
            files: List of largest files.
            dirs: List of largest directories.
            scanned_path: The root directory that was scanned.
        """
        result = ScanResult(
            files=list(files),
            directories=list(dirs),
            total_size=self._total_size,
            files_scanned=self._file_count,
            access_issues=dict(self._access_issues),
            actual_size=self.options.actual_size,
        )
        self.save_scan_result(output_path, result, scanned_path)

    def save_scan_result(self, output_path: Path, result: ScanResult, scanned_path: Path) -> None:
        """Save one self-contained scan snapshot to JSON.

        Unlike :meth:`save_results`, this method does not consult mutable
        scanner state. It is therefore safe to use after an interactive UI has
        hidden, sorted, or deleted displayed entries.
        """
        results = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "scanned_path": str(scanned_path.absolute()),
                "total_size_bytes": result.total_size,
                "total_size_human": format_size(result.total_size),
                "size_mode": "actual" if result.actual_size else "apparent",
                "files_scanned": result.files_scanned,
            },
            "largest_files": [
                {
                    "path": str(f.path.absolute()),
                    "size_bytes": f.size,
                    "size_human": format_size(f.size),
                    "storage_type": (
                        "icloud" if f.is_icloud else "onedrive" if f.is_onedrive else "local"
                    ),
                }
                for f in result.files
            ],
            "largest_directories": [
                {
                    "path": str(d.path.absolute()),
                    "size_bytes": d.size,
                    "size_human": format_size(d.size),
                    "storage_type": (
                        "icloud" if d.is_icloud else "onedrive" if d.is_onedrive else "local"
                    ),
                }
                for d in result.directories
            ],
            "access_issues": [
                {"path": str(path), "error": error} for path, error in result.access_issues.items()
            ],
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.console.print(f"[green]Results saved to {output_path.absolute()}[/]")
        except Exception as error:
            raise DiskScannerError(f"Failed to save results: {error}") from error
