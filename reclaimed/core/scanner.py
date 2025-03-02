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
        self._dir_sizes: Dict[Path, Tuple[int, bool]] = {}
        self._total_size = 0
        self._file_count = 0

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

            async for path, is_file, size in self._walk_directory_async(root_path):
                if is_file:
                    try:
                        # Create file info directly with the size we already have
                        is_icloud = (
                            self.options.icloud_base
                            and self.options.icloud_base in path.parents
                            or "Mobile Documents" in str(path)
                        )
                        file_info = FileInfo(path, size, is_icloud)

                        # Update directory sizes incrementally
                        self._update_dir_sizes(path, size, is_icloud)

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
            self._total_size = 0
            self._file_count = 0

            # Collect all files first
            files: List[FileInfo] = []

            for path, is_file, size in self._walk_directory(root_path):
                if is_file:
                    try:
                        # Create file info directly with the size we already have
                        is_icloud = (
                            self.options.icloud_base
                            and self.options.icloud_base in path.parents
                            or "Mobile Documents" in str(path)
                        )
                        file_info = FileInfo(path, size, is_icloud)

                        # Update directory sizes incrementally
                        self._update_dir_sizes(path, size, is_icloud)

                        # Add to files list
                        files.append(file_info)
                        self._total_size += size
                        self._file_count += 1
                    except (PermissionError, OSError) as e:
                        self._handle_access_error(path, e)

            # Sort files by size
            files.sort(key=lambda x: x.size, reverse=True)

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

    async def _walk_directory_async(self, path: Path) -> AsyncIterator[Tuple[Path, bool, int]]:
        """Asynchronously walk directory tree with adaptive traversal.

        Args:
            path: Directory to walk

        Yields:
            Tuple of (path, is_file, size) for each path encountered
        """
        try:
            # Process directories in batches for better performance
            dirs_to_process = [path]
            processed_count = 0
            is_small_directory = True  # Assume small directory initially

            while dirs_to_process:
                current_dir = dirs_to_process.pop(0)

                try:
                    # Use os.scandir directly for better performance
                    entries = list(os.scandir(current_dir))

                    # First collect subdirectories to process
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue

                            if entry.is_dir():
                                if entry.name not in self.options.skip_dirs:
                                    dirs_to_process.append(Path(entry.path))
                            else:
                                # Get file size directly from DirEntry for better performance
                                try:
                                    # Use stat from DirEntry which is faster than Path.stat()
                                    size = entry.stat().st_size
                                    yield Path(entry.path), True, size
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

                # Yield the directory itself after processing its contents
                # Use 0 size for directories as we calculate their size separately
                yield current_dir, False, 0

                # For small directories, don't yield between directories to complete faster
                # For larger directories, yield occasionally to keep UI responsive
                if not is_small_directory:
                    await asyncio.sleep(0)

        except (AccessError, OSError) as e:
            self._handle_access_error(path, e)

    def _walk_directory(self, path: Path) -> Iterator[Tuple[Path, bool, int]]:
        """Synchronous version of _walk_directory_async.

        Yields:
            Tuple of (path, is_file, size) for each path encountered
        """
        try:
            # Use os.scandir directly for better performance
            for entry in os.scandir(path):
                try:
                    entry_path = Path(entry.path)

                    if entry.is_symlink():
                        continue

                    if entry.is_dir():
                        if entry.name not in self.options.skip_dirs:
                            # Recursively process subdirectory
                            yield from self._walk_directory(entry_path)

                        # Yield directory itself with size 0 (we calculate dir sizes separately)
                        yield entry_path, False, 0
                    else:
                        # Get file size directly from DirEntry for better performance
                        try:
                            size = entry.stat().st_size
                            yield entry_path, True, size
                        except (OSError, AttributeError) as e:
                            self._handle_access_error(entry_path, e)
                except (OSError, AttributeError) as e:
                    self._handle_access_error(Path(entry.path), e)
        except (AccessError, OSError) as e:
            self._handle_access_error(path, e)

    def _update_dir_sizes(self, file_path: Path, file_size: int, is_icloud: bool) -> None:
        """Update directory sizes incrementally as files are processed.

        Args:
            file_path: Path to the file
            file_size: Size of the file in bytes
            is_icloud: Whether the file is in iCloud
        """
        # Initialize update counter if it doesn't exist
        if not hasattr(self, "_update_counter"):
            self._update_counter = 0
        self._update_counter += 1

        # Update size for all parent directories in memory
        for parent in file_path.parents:
            curr_size, curr_cloud = self._dir_sizes.get(parent, (0, False))
            new_size = curr_size + file_size
            new_cloud = curr_cloud or is_icloud
            self._dir_sizes[parent] = (new_size, new_cloud)

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
                size, is_cloud = self._dir_sizes.get(parent, (0, False))
                self._cache.set(parent, size, is_cloud)

    def _get_largest_dirs(self, root: Path) -> List[FileInfo]:
        """Get the largest directories from the calculated sizes.

        Args:
            root: Root directory of scan

        Returns:
            List of directories sorted by size
        """
        # Convert directory sizes to FileInfo objects
        dirs = [
            FileInfo(p, s, c)
            for p, (s, c) in self._dir_sizes.items()
            if p.is_dir() and (p == root or root in p.parents or p in root.parents)
        ]

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
                "files_scanned": self._file_count,
            },
            "largest_files": [
                {
                    "path": str(f.path.absolute()),
                    "size_bytes": f.size,
                    "size_human": format_size(f.size),
                    "storage_type": "icloud" if f.is_icloud else "local",
                }
                for f in files
            ],
            "largest_directories": [
                {
                    "path": str(d.path.absolute()),
                    "size_bytes": d.size,
                    "size_human": format_size(d.size),
                    "storage_type": "icloud" if d.is_icloud else "local",
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
