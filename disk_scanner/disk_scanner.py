#!/usr/bin/env python3
"""
Disk Space Scanner - Analyze directory sizes and find large files

This script scans a given directory, displays scan progress with Rich, and
computes both largest files and directories. It also saves results to a JSON file.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Set up basic logging (could be extended)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Constant for directories to skip during scanning
SKIP_DIRS = [".Trash", "System Volume Information"]


class FileInfo(NamedTuple):
    """Store file information in an immutable structure."""

    path: Path
    size: int
    is_icloud: bool = False


class DiskScanner:
    """Core scanning logic for analyzing disk usage."""

    def __init__(
        self, console: Optional[Console] = None, icloud_base: Optional[Path] = None
    ) -> None:
        self.console = console or Console()
        self._file_data: Dict[Path, Tuple[int, bool]] = {}
        self._icloud_base = icloud_base or Path.home() / "Library/Mobile Documents"
        self._access_issues: Dict[Path, str] = {}
        self._total_size: int = 0
        self._file_count: int = 0

    def scan_directory(
        self, root_path: Path, max_files: int = 10, max_dirs: int = 10
    ) -> Tuple[List[FileInfo], List[FileInfo]]:
        """
        Scan a directory and return the largest files and directories.

        Args:
            root_path: Directory path to scan.
            max_files: Maximum number of files to return.
            max_dirs: Maximum number of directories to return.

        Returns:
            A tuple containing two lists: largest files and largest directories.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[cyan]{task.fields[files]} files"),
            TextColumn("[magenta]{task.fields[size]}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Scanning...", total=None, files="0", size="0 B")

            # Optionally, update progress every N files for performance
            update_interval = 100

            try:
                for i, path in enumerate(self._walk_directory(root_path)):
                    if path.is_file():
                        try:
                            size = path.stat().st_size
                            is_icloud = (
                                self._icloud_base in path.parents or "Mobile Documents" in str(path)
                            )
                            self._file_data[path] = (size, is_icloud)
                            self._total_size += size
                            self._file_count += 1

                            if self._file_count % update_interval == 0:
                                progress.update(
                                    task,
                                    files=f"{self._file_count:,}",
                                    size=self.format_size(self._total_size),
                                )
                        except (PermissionError, OSError) as e:
                            err_msg = f"{e.__class__.__name__}: {e}"
                            self._access_issues[path] = err_msg
                    # Even if not a file, update some progress info occasionally
                    if i % update_interval == 0:
                        progress.update(task)
            except KeyboardInterrupt:
                self.console.print(
                    "\n[yellow]Scan interrupted. Showing partial results...[/yellow]"
                )

        # Get largest files – the keys in _file_data are all the scanned items that are files.
        files = [FileInfo(p, s, i) for p, (s, i) in self._file_data.items() if p.is_file()]
        files.sort(key=lambda x: x.size, reverse=True)

        # Calculate sizes for directories.
        dirs = self._calculate_dir_sizes(root_path)

        # Display summary of access issues if any occurred.
        if self._access_issues:
            self._print_access_issues_summary()

        return files[:max_files], dirs[:max_dirs]

    def _walk_directory(self, path: Path) -> Iterator[Path]:
        """
        Recursively walk directory while handling permissions.

        Args:
            path: The directory path to traverse.
        Yields:
            Each Path encountered in the directory tree.
        """
        try:
            for item in path.iterdir():
                # Skip directories that might cause permission issues
                if item.is_dir() and not item.is_symlink():
                    if any(skip in item.name for skip in SKIP_DIRS):
                        continue
                    yield from self._walk_directory(item)
                yield item
        except PermissionError:
            self._access_issues[path] = "Permission denied"
        except OSError as e:
            self._access_issues[path] = f"{e.__class__.__name__}: {e}"

    def _calculate_dir_sizes(self, root: Path) -> List[FileInfo]:
        """
        Calculate accumulated directory sizes based on scanned files.

        Args:
            root: The root directory for the scan.
        Returns:
            A sorted list of FileInfo for directories (largest first).
        """
        dir_sizes: Dict[Path, Tuple[int, bool]] = {}

        for path, (size, is_icloud) in self._file_data.items():
            for parent in path.parents:
                if parent < root:
                    break
                curr_size, curr_cloud = dir_sizes.get(parent, (0, is_icloud))
                dir_sizes[parent] = (curr_size + size, curr_cloud or is_icloud)

        dirs = [FileInfo(p, s, c) for p, (s, c) in dir_sizes.items()]
        dirs.sort(key=lambda x: x.size, reverse=True)
        return dirs

    def format_size(self, size: int) -> str:
        """
        Convert a size in bytes to a human-readable string.

        Args:
            size: Size in bytes.
        Returns:
            A human-readable size string.
        """
        size_float = float(size)  # Convert to float for division
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024
        return f"{size_float:.1f} PB"

    def save_results(
        self, output_path: Path, files: List[FileInfo], dirs: List[FileInfo], scanned_path: Path
    ) -> None:
        """
        Save the scan results to a JSON file.

        Args:
            output_path: Path to the output JSON file.
            files: List of largest files.
            dirs: List of largest directories.
            scanned_path: The root directory that was scanned.
        """
        results = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "scanned_path": str(scanned_path.absolute()),
                "total_size_bytes": self._total_size,
                "total_size_human": self.format_size(self._total_size),
                "files_scanned": self._file_count,
            },
            "largest_files": [
                {
                    "path": str(f.path.absolute()),
                    "size_bytes": f.size,
                    "size_human": self.format_size(f.size),
                    "storage_type": "icloud" if f.is_icloud else "local",
                }
                for f in files
            ],
            "largest_directories": [
                {
                    "path": str(d.path.absolute()),
                    "size_bytes": d.size,
                    "size_human": self.format_size(d.size),
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
            self.console.print(f"[green]Results saved to {output_path.absolute()}[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to save results: {e}[/red]")

    def _print_access_issues_summary(self) -> None:
        """Print a rich-formatted summary of access issues."""
        issues_by_type: Dict[str, List[Path]] = {}
        for path, error in self._access_issues.items():
            issues_by_type.setdefault(error, []).append(path)

        issue_table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
            title="[bold yellow]Access Issues Summary[/]",
            title_justify="left",
            border_style="yellow",
        )

        for error_type, paths in issues_by_type.items():
            issue_table.add_row(
                "[yellow]•[/yellow]", f"[yellow]{error_type}[/yellow] ({len(paths)} items)"
            )
            # Show up to three examples per error type.
            for sample in sorted(paths)[:3]:
                issue_table.add_row("  [dim]>[/dim]", f"[dim]{sample.name}[/dim]")
            if len(paths) > 3:
                issue_table.add_row(
                    "  [dim]>[/dim]", f"[dim]...and {len(paths) - 3} more similar items[/dim]"
                )

        self.console.print(issue_table)
        self.console.print()


def main() -> None:
    """Entrypoint for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Analyze disk space usage and find large files/directories."
    )
    parser.add_argument("path", type=Path, help="Path to the directory to scan")
    parser.add_argument(
        "--max-files", type=int, default=10, help="Maximum number of largest files to display"
    )
    parser.add_argument(
        "--max-dirs", type=int, default=10, help="Maximum number of largest directories to display"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("scan_results.json"),
        help="Path to save the JSON scan results",
    )
    args = parser.parse_args()

    if not args.path.is_dir():
        Console().print(f"[red]Error:[/red] {args.path} is not a valid directory.")
        sys.exit(1)

    scanner = DiskScanner()
    largest_files, largest_dirs = scanner.scan_directory(args.path, args.max_files, args.max_dirs)

    # Display summary results
    console = scanner.console
    # Display results in tables
    file_table = Table(
        title="[bold]Largest Files[/]",
        border_style="cyan",
        header_style="bold cyan",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    file_table.add_column("Size", justify="right", style="cyan", no_wrap=True)
    file_table.add_column("Storage", style="yellow", no_wrap=True)
    file_table.add_column("Path", style="bright_white")
    for f in largest_files:
        file_table.add_row(
            scanner.format_size(f.size),
            "☁️ iCloud" if f.is_icloud else "💾 Local",
            str(f.path.relative_to(args.path)),
        )
    console.print()
    console.print(file_table)

    dir_table = Table(
        title="[bold]Largest Directories[/]",
        border_style="blue",
        header_style="bold blue",
        show_lines=True,
        padding=(0, 1),
        expand=True,
    )
    dir_table.add_column("Size", justify="right", style="cyan", no_wrap=True)
    dir_table.add_column("Storage", style="yellow", no_wrap=True)
    dir_table.add_column("Path", style="bright_white")
    for d in largest_dirs:
        dir_table.add_row(
            scanner.format_size(d.size),
            "☁️ iCloud" if d.is_icloud else "💾 Local",
            str(d.path.relative_to(args.path)),
        )
    console.print()
    console.print(dir_table)

    # Save the results
    scanner.save_results(args.output, largest_files, largest_dirs, args.path)


if __name__ == "__main__":
    main()
