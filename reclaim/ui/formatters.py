"""UI formatting utilities for disk scanner."""

from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..core.types import FileInfo
from ..utils.formatters import format_size
from .styles import BASE0, BASE1, BLUE, CYAN, GREEN, YELLOW


class TableFormatter:
    """Format scan results into rich tables."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the formatter.

        Args:
            console: Rich console to use for output
        """
        self.console = console or Console()

    def format_files_table(self, files: List[FileInfo], root_path: Path) -> Table:
        """Format list of files into a rich table.

        Args:
            files: List of files to display
            root_path: Root path for relative path display

        Returns:
            Rich table of formatted file information
        """
        table = Table(
            title=f"[{BASE1}]Largest Files[/]",
            border_style=CYAN,
            header_style=f"bold {BASE1}",
            show_lines=True,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Size", justify="right", style=CYAN, no_wrap=True)
        table.add_column("Storage", style=YELLOW, no_wrap=True)
        table.add_column("Path", style=BASE0)

        for file_info in files:
            try:
                rel_path = file_info.path.relative_to(root_path)
            except ValueError:
                rel_path = file_info.path

            storage_status = "☁️ iCloud" if file_info.is_icloud else "💾 Local"
            storage_cell = Text(storage_status, style=BLUE if file_info.is_icloud else GREEN)

            table.add_row(format_size(file_info.size), storage_cell, str(rel_path))

        return table

    def format_dirs_table(self, dirs: List[FileInfo], root_path: Path) -> Table:
        """Format list of directories into a rich table.

        Args:
            dirs: List of directories to display
            root_path: Root path for relative path display

        Returns:
            Rich table of formatted directory information
        """
        table = Table(
            title=f"[{BASE1}]Largest Directories[/]",
            border_style=BLUE,
            header_style=f"bold {BASE1}",
            show_lines=True,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Size", justify="right", style=CYAN, no_wrap=True)
        table.add_column("Storage", style=YELLOW, no_wrap=True)
        table.add_column("Path", style=BASE0)

        for dir_info in dirs:
            try:
                rel_path = dir_info.path.relative_to(root_path)
            except ValueError:
                rel_path = dir_info.path

            storage_status = "☁️ iCloud" if dir_info.is_icloud else "💾 Local"
            storage_cell = Text(storage_status, style=BLUE if dir_info.is_icloud else GREEN)

            table.add_row(format_size(dir_info.size), storage_cell, str(rel_path))

        return table

    def format_access_issues(self, issues: dict[Path, str]) -> Optional[Table]:
        """Format access issues into a rich table.

        Args:
            issues: Dictionary of paths and their access errors

        Returns:
            Rich table of formatted issues, or None if no issues
        """
        if not issues:
            return None

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
            title=f"[bold {YELLOW}]Access Issues Summary[/]",
            title_justify="left",
            border_style=YELLOW,
        )

        # Group issues by error type
        issues_by_type: dict[str, List[Path]] = {}
        for path, error in issues.items():
            issues_by_type.setdefault(error, []).append(path)

        for error_type, paths in issues_by_type.items():
            table.add_row(f"[{YELLOW}]•[/]", f"[{YELLOW}]{error_type}[/] ({len(paths)} items)")
            # Show up to three examples per error type
            for sample in sorted(paths)[:3]:
                table.add_row("  [dim]>[/dim]", f"[dim]{sample.name}[/dim]")
            if len(paths) > 3:
                table.add_row(
                    "  [dim]>[/dim]", f"[dim]...and {len(paths) - 3} more similar items[/dim]"
                )

        return table

    def print_scan_summary(
        self, files: List[FileInfo], dirs: List[FileInfo], root_path: Path, issues: dict[Path, str]
    ) -> None:
        """Print complete scan results.

        Args:
            files: List of largest files
            dirs: List of largest directories
            root_path: Root path that was scanned
            issues: Dictionary of access issues
        """
        self.console.print()
        self.console.print(self.format_files_table(files, root_path))
        self.console.print()
        self.console.print(self.format_dirs_table(dirs, root_path))

        if issues:
            self.console.print()
            issues_table = self.format_access_issues(issues)
            if issues_table:
                self.console.print(issues_table)
                self.console.print()
