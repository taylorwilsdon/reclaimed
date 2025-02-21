"""Command line interface for reclaim"""
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from .disk_scanner import DiskScanner

@click.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--files', '-f', default=10, help='Number of largest files to show')
@click.option('--dirs', '-d', default=10, help='Number of largest directories to show')
@click.option('--output', '-o', type=click.Path(), help='Save results to JSON file')
def main(path: str, files: int, dirs: int, output: Optional[str]):
    """Analyze disk usage and optimize storage with Reclaim.
    
    Scans directories and shows largest files and folders.
    PATH is the directory to analyze. Defaults to current directory if not specified."""
    console = Console()
    scanner = DiskScanner(console)
    
    try:
        path_obj = Path(path).resolve()
        if not path_obj.is_dir():
            console.print("[red]Error: Specified path must be a directory")
            sys.exit(1)
            
        # Create header panel
        header = Panel(
            Text(f"Scanning {path_obj}", style="bold green"),
            border_style="green",
            expand=True
        )
        console.print(header)
        largest_files, largest_dirs = scanner.scan_directory(path_obj, max_files=files, max_dirs=dirs)
        
        # Display results in tables
        file_table = Table(
            title="[bold]Largest Files[/]",
            expand=True,
            border_style="cyan",
            header_style="bold cyan",
            show_lines=True,
            padding=(0, 1)
        )
        file_table.add_column("Size", justify="right", style="cyan", width=8, no_wrap=True)
        file_table.add_column("Storage", style="yellow", width=12, no_wrap=True)
        file_table.add_column("Path", style="bright_white", ratio=1, overflow="ellipsis")
        
        for file in largest_files:
            file_table.add_row(
                scanner.format_size(file.size),
                f"[{'bright_blue' if file.is_icloud else 'green'}]{'☁️ iCloud' if file.is_icloud else '💾 Local'}[/]",
                str(file.path)
            )
        
        dir_table = Table(
            title="[bold]Largest Directories[/]",
            expand=True,
            border_style="blue",
            header_style="bold blue",
            show_lines=True,
            padding=(0, 1)
        )
        dir_table.add_column("Size", justify="right", style="cyan", width=8, no_wrap=True)
        dir_table.add_column("Storage", style="yellow", width=12, no_wrap=True)
        dir_table.add_column("Path", style="bright_white", ratio=1, overflow="ellipsis")
        
        for dir in largest_dirs:
            dir_table.add_row(
                scanner.format_size(dir.size),
                f"[{'bright_blue' if dir.is_icloud else 'green'}]{'☁️ iCloud' if dir.is_icloud else '💾 Local'}[/]",
                str(dir.path)
            )
        
        console.print()
        console.print(file_table)
        console.print()
        console.print(dir_table)

        # Save results to file if requested
        if output:
            scanner.save_results(
                Path(output),
                largest_files,
                largest_dirs,
                path_obj
            )
            save_panel = Panel(
                Text(f"Results saved to: {output}", style="green"),
                border_style="green",
                expand=True
            )
            console.print("\n", save_panel)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
