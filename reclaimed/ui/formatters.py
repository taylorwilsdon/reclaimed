"""UI formatting utilities for disk scanner."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..core.types import FileInfo
from ..utils.formatters import format_bar, format_size
from .styles import BASE0, BASE1, BLUE, CYAN, GREEN, VIOLET, YELLOW


def format_display_path(path: Path, root_path: Path, max_width: int) -> str:
    """Format a root-relative path, preserving its basename when truncated."""
    try:
        display = str(path.relative_to(root_path))
    except ValueError:
        display = str(path)

    if len(display) <= max_width:
        return display
    if max_width <= 1:
        return "…"[:max_width]

    basename = path.name or display
    if len(basename) + 2 >= max_width:
        return "…" + basename[-(max_width - 1) :]

    prefix_width = max_width - len(basename) - 2
    return f"{display[:prefix_width]}…{os.sep}{basename}"


def format_percentage(fraction: float) -> str:
    """Format a table percentage compactly."""
    clamped = min(1.0, max(0.0, fraction))
    if clamped >= 0.9995:
        return "100%"
    return f"{clamped * 100:.1f}%"


class TableFormatter:
    """Format scan results into Rich tables."""

    BAR_WIDTH = 20

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    @staticmethod
    def _storage_cell(item: FileInfo) -> Text:
        """Format the item's local or cloud-sync storage classification."""
        if item.is_icloud:
            return Text("☁ iCloud", style=BLUE)
        if item.is_onedrive:
            return Text("☁ OneDrive", style=VIOLET)
        return Text("Local", style=GREEN)

    def _format_usage_table(
        self,
        title: str,
        border_style: str,
        items: List[FileInfo],
        root_path: Path,
        total_size: Optional[int],
    ) -> Table:
        show_storage = any(item.is_icloud or item.is_onedrive for item in items)
        table = Table(
            title=f"[{BASE1}]{title}[/]",
            border_style=border_style,
            header_style=f"bold {BASE1}",
            show_lines=False,
            padding=(0, 1),
            expand=True,
        )
        table.add_column(
            "Size", justify="right", style=CYAN, no_wrap=True, width=10, max_width=10
        )
        table.add_column(
            "Bar",
            style=CYAN,
            no_wrap=True,
            width=self.BAR_WIDTH,
            max_width=self.BAR_WIDTH,
        )
        table.add_column(
            "%", justify="right", style=GREEN, no_wrap=True, width=6, max_width=6
        )
        if show_storage:
            table.add_column(
                "Storage", style=YELLOW, no_wrap=True, width=10, max_width=10
            )
        table.add_column("Path", style=BASE0, no_wrap=True, overflow="ellipsis")

        denominator = total_size if total_size is not None else max(
            (item.size for item in items), default=0
        )
        # Leave two cells of safety for Rich's borders and column separators so
        # it never adds a second tail ellipsis after our middle truncation.
        reserved_width = 62 if show_storage else 50
        path_width = max(12, self.console.width - reserved_width)

        for item in items:
            fraction = item.size / denominator if denominator else 0.0
            row: List[Union[str, Text]] = [
                format_size(item.size),
                format_bar(fraction, self.BAR_WIDTH),
                format_percentage(fraction),
            ]
            if show_storage:
                row.append(self._storage_cell(item))
            row.append(format_display_path(item.path, root_path, path_width))
            table.add_row(*row)

        return table

    def format_files_table(
        self,
        files: List[FileInfo],
        root_path: Path,
        total_size: Optional[int] = None,
    ) -> Table:
        """Format the largest files as a proportional usage table."""
        return self._format_usage_table(
            "Largest Files", CYAN, files, root_path, total_size
        )

    def format_dirs_table(
        self,
        dirs: List[FileInfo],
        root_path: Path,
        total_size: Optional[int] = None,
    ) -> Table:
        """Format the largest directories as a proportional usage table."""
        return self._format_usage_table(
            "Largest Directories", BLUE, dirs, root_path, total_size
        )

    def format_access_issues(self, issues: Dict[Path, str]) -> Optional[Table]:
        """Format access issues grouped by error message."""
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
        issues_by_type: Dict[str, List[Path]] = {}
        for path, error in issues.items():
            issues_by_type.setdefault(error, []).append(path)

        for error_type, paths in issues_by_type.items():
            table.add_row(f"[{YELLOW}]•[/]", f"[{YELLOW}]{error_type}[/] ({len(paths)} items)")
            for sample in sorted(paths)[:3]:
                table.add_row("  [dim]>[/dim]", f"[dim]{sample.name}[/dim]")
            if len(paths) > 3:
                table.add_row(
                    "  [dim]>[/dim]",
                    f"[dim]...and {len(paths) - 3} more similar items[/dim]",
                )

        return table

    def print_scan_summary(
        self,
        files: List[FileInfo],
        dirs: List[FileInfo],
        root_path: Path,
        issues: Dict[Path, str],
        total_size: Optional[int] = None,
    ) -> None:
        """Print the complete scan result."""
        if total_size is None:
            root_entry = next((item for item in dirs if item.path == root_path), None)
            total_size = root_entry.size if root_entry is not None else None

        self.console.print()
        self.console.print(self.format_files_table(files, root_path, total_size))
        self.console.print()
        self.console.print(self.format_dirs_table(dirs, root_path, total_size))

        if issues:
            self.console.print()
            issues_table = self.format_access_issues(issues)
            if issues_table:
                self.console.print(issues_table)
                self.console.print()
