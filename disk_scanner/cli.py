"""Command line interface for reclaim"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .disk_scanner import DiskScanner


def _format_storage_status(is_icloud: bool) -> str:
    """Format storage status with appropriate color and icon."""
    color = "bright_blue" if is_icloud else "green"
    status = "☁️ iCloud" if is_icloud else "💾 Local"
    return f"[{color}]{status}[/]"


def _truncate_path(path: str, max_width: int) -> str:
    """Truncate the path from the left at path separators to fit within max_width."""
    if len(path) <= max_width:
        return path

    # Use os.path.sep for cross-platform compatibility
    sep = os.path.sep
    parts = path.split(sep)
    truncated = ''

    for i in range(len(parts)):
        truncated = f'...{sep}' + f'{sep}'.join(parts[i:])
        if len(truncated) <= max_width:
            return truncated

    return '...' + path[-max_width + 3:]


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--files", "-f", default=10, help="Number of largest files to show")
@click.option("--dirs", "-d", default=10, help="Number of largest directories to show")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option("--interactive", "-i", is_flag=True, help="Launch interactive Textual UI")
def main(
    path: str,
    files: int,
    dirs: int,
    output: Optional[str],
    interactive: bool = False,
    console: Optional[Console] = None
) -> None:
    """Analyze disk usage and optimize storage with Reclaim.

    Scans directories and shows largest files and folders.
    PATH is the directory to analyze. Defaults to current directory if not specified."""
    console = console or Console()
    scanner = DiskScanner(console)

    try:
        # Validate inputs
        if files <= 0 or dirs <= 0:
            console.print("[red]Error: Files and directories count must be positive")
            sys.exit(1)

        path_obj = Path(path).resolve()
        if not path_obj.is_dir():
            console.print("[red]Error: Specified path must be a directory")
            sys.exit(1)
            
        # Launch interactive UI if requested
        if interactive:
            try:
                from .textual_ui import run_textual_ui
                console.print("[green]Launching interactive UI...[/green]")
                run_textual_ui(path_obj, files, dirs)
                return
            except ImportError as e:
                console.print("[yellow]Could not load interactive UI. Make sure textual is installed.[/yellow]")
                console.print(f"[dim]Error: {e}[/dim]")
                console.print("[green]Continuing with standard CLI mode...[/green]")

        # Create header panel and start timer
        start_time = time.time()
        header = Panel(Text(f"Scanning {path_obj}", style="bold green"), border_style="green")
        console.print(header)

        largest_files, largest_dirs = scanner.scan_directory(
            path_obj,
            max_files=files,
            max_dirs=dirs,
        )

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
        file_table.add_column("Path", style="bright_white", no_wrap=True, ratio=1, overflow="ellipsis")

        # Calculate maximum width for the path column
        max_path_width = console.width - 20  # Adjust based on estimated width of other columns
        for file in largest_files:
            try:
                full_path = str(file.path.relative_to(path_obj))
            except ValueError:
                # Handle files not relative to base path
                full_path = str(file.path)

            truncated_path = _truncate_path(full_path, max_path_width)
            path_text = Text(truncated_path)
            file_table.add_row(
                scanner.format_size(file.size),
                _format_storage_status(file.is_icloud),
                path_text,
            )

        dir_table = Table(
            title="[bold]Largest Directories[/]",
            border_style="blue",
            header_style="bold blue",
            show_lines=True,
            padding=(0, 1),
        )
        dir_table.add_column("Size", justify="right", style="cyan", width=8, no_wrap=True)
        dir_table.add_column("Storage", style="yellow", width=12, no_wrap=True)
        dir_table.add_column("Path", style="bright_white")

        for dir_item in largest_dirs:
            try:
                dir_path = str(dir_item.path.relative_to(path_obj))
            except ValueError:
                # Handle directories not relative to base path
                dir_path = str(dir_item.path)

            dir_table.add_row(
                scanner.format_size(dir_item.size),
                _format_storage_status(dir_item.is_icloud),
                dir_path,
            )

        # Calculate and display elapsed time
        elapsed_time = time.time() - start_time
        time_text = Text(f"Scan completed in {elapsed_time:.2f} seconds", style="bold green")
        console.print()
        console.print(file_table)
        console.print()
        console.print(dir_table)
        console.print(time_text)

        # Save results to file if requested
        if output:
            scanner.save_results(Path(output), largest_files, largest_dirs, path_obj)
            save_panel = Panel(
                Text(f"Results saved to: {output}", style="green"),
                border_style="green",
            )
            console.print("\n", save_panel)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
