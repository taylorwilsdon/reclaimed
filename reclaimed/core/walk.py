"""Leaf-level directory listing, designed to run in worker threads.

Everything here is module-level and free of instance state so it can be handed
to a :class:`~concurrent.futures.ThreadPoolExecutor` without sharing anything
mutable except the explicitly-documented fields of :class:`WalkContext`.

Paths stay as ``str`` throughout. Building ``pathlib.Path`` objects during
traversal is what made the previous implementation allocation-bound: only the
handful of entries that reach a result are ever converted.
"""

import heapq
import os
import threading
from typing import FrozenSet, List, NamedTuple, Optional, Tuple

#: Directory name that marks the root of iCloud Drive storage on macOS.
MOBILE_DOCUMENTS = "Mobile Documents"

#: Prefix used by personal and business OneDrive sync roots.
ONEDRIVE_PREFIX = "OneDrive"

#: Windows cloud placeholders may use either recall-on-open attribute.
_WIN_RECALL_ATTRS = 0x00040000 | 0x00400000

#: Absolute paths whose entire subtree is a kernel-backed virtual filesystem.
#: The entries under them report sizes that have nothing to do with disk usage
#: -- ``/proc/kcore`` alone stat()s at ~128 TiB on x86-64 -- so the scanner
#: neither counts those files nor recurses into these trees. Empty off POSIX,
#: where none of these paths exist.
VIRTUAL_FS_ROOTS: FrozenSet[str] = (
    frozenset({"/proc", "/sys", "/dev"}) if os.name == "posix" else frozenset()
)


def is_onedrive_root_name(name: str) -> bool:
    """Return whether a directory name follows OneDrive's standard naming."""
    normalized = name.casefold()
    return normalized == ONEDRIVE_PREFIX.casefold() or normalized.startswith(
        f"{ONEDRIVE_PREFIX.casefold()} - "
    )


def _under_virtual_fs(abs_path: str, roots: FrozenSet[str]) -> bool:
    """True if ``abs_path`` is one of ``roots`` or lives beneath one."""
    return any(abs_path == root or abs_path.startswith(root + os.sep) for root in roots)


class WalkJob(NamedTuple):
    """One directory queued for listing."""

    dir_id: int
    path: str


class DirListing(NamedTuple):
    """Everything a worker learned about a single directory."""

    dir_id: int
    subdirs: List[Tuple[str, str]]  # (name, path) of child directories
    own_bytes: int  # sum of sizes of files directly in this directory
    file_count: int
    candidates: List[Tuple[int, str, float]]  # (size, path, mtime) above the floor
    error: Optional[str]  # scandir() failure for the directory itself
    entry_errors: List[Tuple[str, str]]  # (path, message) per-entry failures


class WalkContext:
    """Shared, mostly-read-only configuration handed to every worker.

    ``floor`` is the only field written during a scan. It holds the size of the
    smallest file currently in the top-N heap, letting workers discard the
    overwhelming majority of files without the parent ever seeing them. Workers
    read it without synchronisation: rebinding an int attribute is atomic under
    CPython, and because the floor only ever rises, a stale read is always low,
    which admits a few extra candidates but can never drop a real one. Do not
    "fix" this with a lock; the contention would cost more than it saves.
    """

    __slots__ = ("skip", "max_files", "actual_size", "floor", "cancel", "virtual_roots")

    def __init__(
        self,
        skip: FrozenSet[str],
        max_files: int,
        actual_size: bool,
        cancel: threading.Event,
        virtual_roots: FrozenSet[str] = VIRTUAL_FS_ROOTS,
    ):
        self.skip = skip
        self.max_files = max_files
        self.actual_size = actual_size
        self.floor = -1
        self.cancel = cancel
        self.virtual_roots = virtual_roots


def list_dir(job: WalkJob, ctx: WalkContext) -> DirListing:
    """List one directory, summing its direct files.

    Per file this costs exactly one ``stat`` syscall, one addition and one
    comparison. Note the deliberate absence of ``except Exception``: a
    ``KeyboardInterrupt`` raised in here must propagate so that an interrupted
    scan surfaces as one, rather than being recorded as an access issue.
    """
    subdirs: List[Tuple[str, str]] = []
    candidates: List[Tuple[int, str, float]] = []
    entry_errors: List[Tuple[str, str]] = []
    own_bytes = 0
    file_count = 0
    skip = ctx.skip
    virtual_roots = ctx.virtual_roots
    # Resolve the listing root once so /proc, /sys and /dev can be recognised
    # regardless of how the scan was invoked; skipped entirely off POSIX.
    base = os.path.abspath(job.path) if virtual_roots else job.path
    parent_virtual = bool(virtual_roots) and _under_virtual_fs(base, virtual_roots)

    try:
        with os.scandir(job.path) as entries:
            for entry in entries:
                if ctx.cancel.is_set():
                    break
                try:
                    # is_dir/is_symlink are answered from the directory entry's
                    # d_type where the filesystem supplies it, costing no syscall.
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in skip:
                            continue
                        if virtual_roots and _under_virtual_fs(
                            os.path.join(base, entry.name), virtual_roots
                        ):
                            continue
                        subdirs.append((entry.name, entry.path))
                        continue
                    if entry.is_symlink():
                        continue
                    # Files inside a virtual filesystem (e.g. /proc/kcore) carry
                    # sizes unrelated to disk usage; don't count or rank them.
                    if parent_virtual:
                        continue

                    stat_result = entry.stat(follow_symlinks=False)
                    size = local_disk_size(stat_result) if ctx.actual_size else stat_result.st_size
                    own_bytes += size
                    file_count += 1
                    if size >= ctx.floor:
                        _offer_candidate(
                            candidates,
                            ctx.max_files,
                            size,
                            entry.path,
                            stat_result.st_mtime,
                        )
                except OSError as error:
                    entry_errors.append((entry.path, _describe(error)))
    except OSError as error:
        return DirListing(
            job.dir_id,
            subdirs,
            own_bytes,
            file_count,
            candidates,
            _describe(error),
            entry_errors,
        )

    return DirListing(job.dir_id, subdirs, own_bytes, file_count, candidates, None, entry_errors)


def list_chunk(jobs: List[WalkJob], ctx: WalkContext) -> List[DirListing]:
    """List a batch of directories, stopping early if the scan was cancelled."""
    listings = []
    for job in jobs:
        if ctx.cancel.is_set():
            break
        listings.append(list_dir(job, ctx))
    return listings


def _offer_candidate(
    heap: List[Tuple[int, str, float]],
    limit: int,
    size: int,
    path: str,
    mtime: float,
) -> None:
    """Keep a bounded per-directory top-N without materializing every file."""
    if limit <= 0:
        return
    candidate = (size, path, mtime)
    if len(heap) < limit:
        heapq.heappush(heap, candidate)
    elif size > heap[0][0]:
        heapq.heapreplace(heap, candidate)
    elif size == heap[0][0]:
        tied = [index for index, item in enumerate(heap) if item[0] == size]
        worst = max(tied, key=lambda index: heap[index][1])
        if path < heap[worst][1]:
            heap[worst] = candidate
            heapq.heapify(heap)


def _describe(error: OSError) -> str:
    """Render an exception the way the scanner has always recorded it."""
    return f"{error.__class__.__name__}: {error}"


def local_disk_size(stat_result: os.stat_result) -> int:
    """Return allocated local bytes for a file, with a Windows fallback."""
    st_blocks = getattr(stat_result, "st_blocks", None)
    if st_blocks is not None:
        # POSIX specifies st_blocks in 512-byte units, independent of block size.
        return int(st_blocks) * 512

    attributes = getattr(stat_result, "st_file_attributes", None)
    if attributes is not None and attributes & _WIN_RECALL_ATTRS:
        return 0

    return stat_result.st_size
