"""Core disk scanning functionality."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, Iterator, List, Optional, Tuple

from rich.console import Console

from ..utils.formatters import format_size
from .cache import DirectorySizeCache
from .errors import (
    AccessError,
    InvalidPathError,
    PermissionError,
    ScanInterruptedError,
)
from .types import FileInfo, ScanOptions, ScanProgress, ScanResult

logger = logging.getLogger(__name__)

# Windows FILE_ATTRIBUTE_RECALL_ON_OPEN / FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS: set on
# cloud-only placeholder files (e.g. OneDrive Files On-Demand) that have not been
# downloaded locally.
_WIN_RECALL_ATTRS = 0x00040000 | 0x00400000


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
        self._cache = DirectorySizeCache()
        self._access_issues: Dict[Path, str] = {}
        self._dir_sizes: Dict[Path, Tuple[int, bool, bool]] = {}
        self._total_size = 0
        self._file_count = 0
        # Directories whose entire subtree has finished scanning
        self._completed_dirs: set = set()
        # Number of not-yet-completed subdirectories under each directory,
        # used to detect when a directory's subtree becomes fully scanned
        self._pending_subdirs: Dict[Path, int] = {}

    async def scan_async(self, root_path: Path) -> AsyncIterator[ScanProgress]:
        """Scan a directory asynchronously, yielding progress updates.

        Args:
            root_path: Directory to scan

        Yields:
            ScanProgress updates during scanning

        Raises:
            InvalidPathError: If root_path is not a directory
            ScanInterruptedError: If scanning is interrupted
        """
        if not root_path.is_dir():
            raise InvalidPathError(root_path, "Not a directory")

        try:
            # Reset scan state
            self._access_issues.clear()
            self._dir_sizes.clear()
            self._completed_dirs.clear()
            self._pending_subdirs.clear()
            self._total_size = 0
            self._file_count = 0

            # Track largest files and dirs during scan
            largest_files: List[FileInfo] = []
            largest_dirs: List[FileInfo] = []

            # Process files in chunks for smoother progress updates
            chunk_size = 250  # Increased chunk size for better performance
            paths_chunk: List[Path] = []

            # Pre-populate cache with any existing entries for better performance
            # Track when we last calculated directory sizes
            last_dir_calc_time = 0
            # Start with frequent calculations, then reduce frequency based on file count
            dir_calc_interval = 1.0  # Default: Calculate directory sizes once per second

            # Unpack the new last_modified value
            async for path, is_file, size, last_modified in self._walk_directory_async(root_path):
                if is_file:
                    try:
                        # Create file info directly with the size we already have
                        is_icloud = (
                            self.options.icloud_base
                            and self.options.icloud_base in path.parents
                            or "Mobile Documents" in str(path)
                        )
                        is_onedrive = (
                            self.options.onedrive_base
                            and self.options.onedrive_base in path.parents
                            or "OneDrive" in str(path)
                        )
                        # Include last_modified in FileInfo creation
                        file_info = FileInfo(path, size, last_modified, is_icloud, is_onedrive)

                        # Update directory sizes incrementally
                        self._update_dir_sizes(path, size, is_icloud, is_onedrive)

                        # Insert file in sorted position if it's large enough
                        if (
                            not largest_files
                            or len(largest_files) < self.options.max_files
                            or size > largest_files[-1].size
                        ):
                            self._insert_sorted(largest_files, file_info, self.options.max_files)
                            # No need to manually trim the list as _insert_sorted now handles this

                        self._total_size += size
                        self._file_count += 1

                        # Add to chunk for batch processing
                        paths_chunk.append(path)
                        if len(paths_chunk) >= chunk_size:
                            paths_chunk.clear()

                            # Check if it's time to calculate directory sizes
                            current_time = time.time()

                            # Dynamically adjust directory calculation interval based on file count
                            if self._file_count > 50000:
                                dir_calc_interval = 5.0  # Very infrequent for huge directories
                            elif self._file_count > 10000:
                                dir_calc_interval = 3.0  # Less frequent for large directories
                            elif self._file_count > 5000:
                                dir_calc_interval = 2.0  # Moderate for medium directories
                            else:
                                dir_calc_interval = 1.0  # Frequent for small directories

                            if current_time - last_dir_calc_time >= dir_calc_interval:
                                # Get largest directories
                                largest_dirs = self._get_largest_dirs(root_path)
                                last_dir_calc_time = current_time

                                # Calculate a rough progress estimate
                                # Not accurate for total completion but provides visual feedback
                                progress_estimate = min(
                                    0.95, self._file_count / (self._file_count + 1000)
                                )

                                # Yield progress
                                yield ScanProgress(
                                    progress=progress_estimate,
                                    files=largest_files[: self.options.max_files],
                                    dirs=largest_dirs[: self.options.max_dirs],
                                    scanned=self._file_count,
                                    total_size=self._total_size,
                                )

                                # Allow other tasks to run
                                await asyncio.sleep(0)
                    except (PermissionError, OSError) as e:
                        self._handle_access_error(path, e)

            # The walk has fully finished, so every directory is now complete
            # (belt-and-braces in case propagation missed an edge case, e.g. a
            # directory whose stat() failed after its children were queued)
            self._completed_dirs.add(root_path)

            # Final directory size calculation
            largest_dirs = self._get_largest_dirs(root_path)

            # Final progress update
            yield ScanProgress(
                progress=1.0,
                files=largest_files[: self.options.max_files],
                dirs=largest_dirs[: self.options.max_dirs],
                scanned=self._file_count,
                total_size=self._total_size,
            )

        except KeyboardInterrupt:
            raise ScanInterruptedError() from None

    def scan(self, root_path: Path) -> ScanResult:
        """Synchronous version of scan_async.

        Args:
            root_path: Directory to scan

        Returns:
            Complete scan results

        Raises:
            InvalidPathError: If root_path is not a directory
            ScanInterruptedError: If scanning is interrupted
        """
        if not root_path.is_dir():
            raise InvalidPathError(root_path, "Not a directory")

        try:
            # Reset scan state
            self._access_issues.clear()
            self._dir_sizes.clear()
            self._completed_dirs.clear()
            self._pending_subdirs.clear()
            self._total_size = 0
            self._file_count = 0

            # Collect all files first
            files: List[FileInfo] = []

            # Unpack the new last_modified value
            for path, is_file, size, last_modified in self._walk_directory(root_path):
                if is_file:
                    try:
                        # Create file info directly with the size we already have
                        is_icloud = (
                            self.options.icloud_base
                            and self.options.icloud_base in path.parents
                            or "Mobile Documents" in str(path)
                        )
                        is_onedrive = (
                            self.options.onedrive_base
                            and self.options.onedrive_base in path.parents
                            or "OneDrive" in str(path)
                        )
                        # Include last_modified in FileInfo creation
                        file_info = FileInfo(path, size, last_modified, is_icloud, is_onedrive)

                        # Update directory sizes incrementally
                        self._update_dir_sizes(path, size, is_icloud, is_onedrive)

                        # Add to files list
                        files.append(file_info)
                        self._total_size += size
                        self._file_count += 1
                    except (PermissionError, OSError) as e:
                        self._handle_access_error(path, e)

            # Sort files by size
            files.sort(key=lambda x: x.size, reverse=True)

            # The walk has fully finished, so every directory is now complete;
            # root_path itself is never yielded by _walk_directory, so mark it here
            self._completed_dirs.add(root_path)

            # Get largest directories
            dirs = self._get_largest_dirs(root_path)

            return ScanResult(
                files=files[: self.options.max_files],
                directories=dirs[: self.options.max_dirs],
                total_size=self._total_size,
                files_scanned=self._file_count,
                access_issues=dict(self._access_issues),
            )

        except KeyboardInterrupt:
            raise ScanInterruptedError() from None

    @staticmethod
    def _local_disk_size(stat_result: os.stat_result) -> int:
        """Estimate bytes actually resident on local disk for a file.

        Cloud-sync placeholder files (evicted iCloud/OneDrive items) report their
        full logical size via st_size even when little or no data is stored
        locally, so this reads the OS's actual block allocation instead. This
        also naturally accounts for sparse and filesystem-compressed files.

        Args:
            stat_result: Result of os.stat()/DirEntry.stat() for the file

        Returns:
            Estimated number of bytes occupied on local disk
        """
        st_blocks = getattr(stat_result, "st_blocks", None)
        if st_blocks is not None:
            # POSIX: block count is always in 512-byte units
            return st_blocks * 512

        st_file_attributes = getattr(stat_result, "st_file_attributes", None)
        if st_file_attributes is not None and st_file_attributes & _WIN_RECALL_ATTRS:
            return 0

        return stat_result.st_size

    def _get_size(self, stat_result: os.stat_result) -> int:
        """Get the file size to report, based on the configured size mode.

        Args:
            stat_result: Result of os.stat()/DirEntry.stat() for the file

        Returns:
            st_size (apparent size) or on-disk size, per self.options.actual_size
        """
        if self.options.actual_size:
            return self._local_disk_size(stat_result)
        return stat_result.st_size

    def _mark_dir_complete(self, dir_path: Path) -> None:
        """Mark a directory's subtree as fully scanned, propagating upward.

        When a directory has no more pending subdirectories, its parent's
        pending count is decremented; if that reaches zero the parent is
        marked complete too, and so on up to the scan root.

        Args:
            dir_path: Directory whose subtree just finished scanning
        """
        stack = [dir_path]
        while stack:
            current = stack.pop()
            self._completed_dirs.add(current)
            parent = current.parent
            if parent in self._pending_subdirs:
                self._pending_subdirs[parent] -= 1
                if self._pending_subdirs[parent] <= 0:
                    stack.append(parent)

    def _should_skip_directory(self, dir_path: Path) -> bool:
        """Check if a directory should be skipped based on skip_dirs patterns.

        Args:
            dir_path: Path to the directory to check

        Returns:
            True if the directory should be skipped, False otherwise
        """
        if not self.options.skip_dirs:
            return False

        dir_name = dir_path.name

        for skip_pattern in self.options.skip_dirs:
            # Exact name match (original behavior)
            if dir_name == skip_pattern:
                return True

            # Path component matching - check if pattern matches any path component
            # This avoids false positives from substring matching on full paths
            for part in dir_path.parts:
                if part == skip_pattern:
                    return True

        return False

    async def _walk_directory_async(self, path: Path) -> AsyncIterator[Tuple[Path, bool, int, float]]:
        """Asynchronously walk directory tree with adaptive traversal.

        Args:
            path: Directory to walk

        Yields:
            Tuple of (path, is_file, size, last_modified) for each path encountered
        """
        try:
            # Process directories in batches for better performance
            dirs_to_process = [path]
            processed_count = 0
            is_small_directory = True  # Assume small directory initially

            while dirs_to_process:
                current_dir = dirs_to_process.pop(0)
                subdir_count = 0

                try:
                    # Use os.scandir directly for better performance
                    entries = list(os.scandir(current_dir))

                    # First collect subdirectories to process
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue

                            if entry.is_dir():
                                if not self._should_skip_directory(Path(entry.path)):
                                    dirs_to_process.append(Path(entry.path))
                                    subdir_count += 1
                            else:
                                # Get file stats directly from DirEntry for better performance
                                try:
                                    stat_result = entry.stat() # Get stat result once
                                    size = self._get_size(stat_result)
                                    last_modified = stat_result.st_mtime # Get timestamp
                                    yield Path(entry.path), True, size, last_modified # Yield timestamp
                                    processed_count += 1

                                    # After processing 500 files, we know it's not a small directory
                                    if processed_count == 500 and is_small_directory:
                                        is_small_directory = False

                                    # For small directories, don't yield to avoid overhead
                                    # For larger directories, yield occasionally to keep
                                    # UI responsive
                                    if not is_small_directory and processed_count % 500 == 0:
                                        await asyncio.sleep(0)
                                except (OSError, AttributeError) as e:
                                    self._handle_access_error(Path(entry.path), e)
                        except (OSError, AttributeError) as e:
                            self._handle_access_error(Path(entry.path), e)

                except (AccessError, OSError) as e:
                    self._handle_access_error(current_dir, e)

                # Track how many subdirectories still need to finish before this
                # directory's own subtree can be considered fully scanned
                self._pending_subdirs[current_dir] = subdir_count
                if subdir_count == 0:
                    self._mark_dir_complete(current_dir)

                # Yield the directory itself after processing its contents
                try:
                    # Get stat for the directory to yield its mtime
                    dir_stat = current_dir.stat()
                    yield current_dir, False, 0, dir_stat.st_mtime
                except (OSError, AttributeError) as e:
                    self._handle_access_error(current_dir, e) # Handle potential error getting stat

                # For small directories, don't yield between directories to complete faster
                # For larger directories, yield occasionally to keep UI responsive
                if not is_small_directory:
                    await asyncio.sleep(0)

        except (AccessError, OSError) as e:
            self._handle_access_error(path, e)

    def _walk_directory(self, path: Path) -> Iterator[Tuple[Path, bool, int, float]]:
        """Synchronous version of _walk_directory_async.

        Yields:
            Tuple of (path, is_file, size, last_modified) for each path encountered
        """
        try:
            # Use os.scandir directly for better performance
            for entry in os.scandir(path):
                try:
                    entry_path = Path(entry.path)

                    if entry.is_symlink():
                        continue

                    if entry.is_dir():
                        if not self._should_skip_directory(entry_path):
                            # Recursively process subdirectory
                            yield from self._walk_directory(entry_path)

                        # By this point every descendant of entry_path (at any depth)
                        # has already been yielded above, so its subtree is complete.
                        self._completed_dirs.add(entry_path)

                        # Yield directory itself with size 0 and its mtime
                        try:
                            dir_stat = entry_path.stat()
                            yield entry_path, False, 0, dir_stat.st_mtime
                        except (OSError, AttributeError) as e:
                            self._handle_access_error(entry_path, e)
                    else:
                        # Get file stats directly from DirEntry for better performance
                        try:
                            stat_result = entry.stat() # Get stat result once
                            size = self._get_size(stat_result)
                            last_modified = stat_result.st_mtime # Get timestamp
                            yield entry_path, True, size, last_modified # Yield timestamp
                        except (OSError, AttributeError) as e:
                            self._handle_access_error(entry_path, e)
                except (OSError, AttributeError) as e:
                    self._handle_access_error(Path(entry.path), e)
        except (AccessError, OSError) as e:
            self._handle_access_error(path, e)

    def _update_dir_sizes(
        self, file_path: Path, file_size: int, is_icloud: bool, is_onedrive: bool = False
    ) -> None:
        """Update directory sizes incrementally as files are processed.

        Args:
            file_path: Path to the file
            file_size: Size of the file in bytes
            is_icloud: Whether the file is in iCloud
            is_onedrive: Whether the file is in OneDrive
        """
        # Initialize update counter if it doesn't exist
        if not hasattr(self, "_update_counter"):
            self._update_counter = 0
        self._update_counter += 1

        # Update size for all parent directories in memory
        for parent in file_path.parents:
            curr_size, curr_icloud, curr_onedrive = self._dir_sizes.get(parent, (0, False, False))
            new_size = curr_size + file_size
            new_icloud = curr_icloud or is_icloud
            new_onedrive = curr_onedrive or is_onedrive
            self._dir_sizes[parent] = (new_size, new_icloud, new_onedrive)

        # Only update cache periodically to reduce overhead
        # For large directories, update cache less frequently
        cache_update_frequency = 100
        if self._file_count > 10000:
            cache_update_frequency = 500
        elif self._file_count > 5000:
            cache_update_frequency = 250

        if self._update_counter % cache_update_frequency == 0:
            # Batch update the cache for all parent directories
            for parent in file_path.parents:
                size, is_cloud, is_od = self._dir_sizes.get(parent, (0, False, False))
                self._cache.set(parent, size, is_cloud, is_od)

    def _get_largest_dirs(self, root: Path) -> List[FileInfo]:
        """Get the largest directories from the calculated sizes.

        Args:
            root: Root directory of scan

        Returns:
            List of directories sorted by size
        """
        # Convert directory sizes to FileInfo objects, fetching mtime
        dirs = []
        for p, (s, ic, od) in self._dir_sizes.items():
            # Apply the same filtering as before
            if p.is_dir() and (p == root or root in p.parents or p in root.parents):
                try:
                    # Get the last modified time for the directory
                    last_modified = os.stat(p).st_mtime
                except OSError:
                    # Default to 0.0 if stat fails
                    last_modified = 0.0
                # Ancestors of root are never themselves walked (only the slice of
                # their contents under root is counted), so their partial size is
                # final exactly when root's own subtree finishes, not when they
                # individually appear in _completed_dirs (which never happens)
                if p in root.parents:
                    is_complete = root in self._completed_dirs
                else:
                    is_complete = p in self._completed_dirs
                dirs.append(FileInfo(p, s, last_modified, ic, od, is_complete))

        # Sort by size (largest first)
        dirs.sort(key=lambda x: x.size, reverse=True)
        return dirs[: self.options.max_dirs]

    def _handle_access_error(self, path: Path, error: Exception) -> None:
        """Handle and record access errors.

        Args:
            path: Path that caused error
            error: Exception that occurred
        """
        err_msg = f"{error.__class__.__name__}: {str(error)}"
        self._access_issues[path] = err_msg
        logger.debug("Access error for %s: %s", path, err_msg)

    @staticmethod
    def _insert_sorted(items: List[FileInfo], item: FileInfo, max_items: int = None) -> None:
        """Insert item into sorted list maintaining size order.

        Args:
            items: Sorted list to insert into
            item: Item to insert
            max_items: Maximum number of items to keep (defaults to None for unlimited)
        """
        # If max_items is specified and the list is already at capacity,
        # only insert if the item is larger than the smallest item
        if max_items is not None and len(items) >= max_items and item.size <= items[-1].size:
            return  # Skip insertion for items that won't make it into the final list

        # Fast path for empty list or when item is smaller than all existing items
        if not items or item.size <= items[-1].size:
            items.append(item)
            # Trim if needed
            if max_items is not None and len(items) > max_items:
                items.pop()
            return

        # Fast path for when item is larger than all existing items
        if item.size > items[0].size:
            items.insert(0, item)
            # Trim if needed
            if max_items is not None and len(items) > max_items:
                items.pop()
            return

        # Binary search for insertion point
        low, high = 0, len(items) - 1
        while low <= high:
            mid = (low + high) // 2
            if items[mid].size < item.size:
                high = mid - 1
            else:
                low = mid + 1

        items.insert(low, item)

        # Trim if needed
        if max_items is not None and len(items) > max_items:
            items.pop()

    def _print_access_issues_summary(self) -> None:
        """Print a rich-formatted summary of access issues."""
        from ..ui.formatters import TableFormatter

        if not self._access_issues:
            return

        formatter = TableFormatter(self.console)
        issues_table = formatter.format_access_issues(self._access_issues)
        if issues_table:
            self.console.print(issues_table)
            self.console.print()

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
        from ..ui.styles import GREEN, RED

        results = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "scanned_path": str(scanned_path.absolute()),
                "total_size_bytes": self._total_size,
                "total_size_human": format_size(self._total_size),
                "size_mode": "actual" if self.options.actual_size else "apparent",
                "files_scanned": self._file_count,
            },
            "largest_files": [
                {
                    "path": str(f.path.absolute()),
                    "size_bytes": f.size,
                    "size_human": format_size(f.size),
                    "storage_type": "icloud" if f.is_icloud else "onedrive" if f.is_onedrive else "local",
                }
                for f in files
            ],
            "largest_directories": [
                {
                    "path": str(d.path.absolute()),
                    "size_bytes": d.size,
                    "size_human": format_size(d.size),
                    "storage_type": "icloud" if d.is_icloud else "onedrive" if d.is_onedrive else "local",
                }
                for d in dirs
            ],
            "access_issues": [
                {"path": str(path), "error": error} for path, error in self._access_issues.items()
            ],
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.console.print(f"[{GREEN}]Results saved to {output_path.absolute()}[/]")
        except Exception as e:
            self.console.print(f"[{RED}]Failed to save results: {e}[/]")
