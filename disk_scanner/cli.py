"""Command line interface for disk scanner"""
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from .disk_scanner import DiskScanner

@click.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--files', '-f', default=10, help='Number of largest files to show')
@click.option('--dirs', '-d', default=10, help='Number of largest directories to show')
def main(path: str, files: int, dirs: int):
    """Scan directory and show largest files and folders.
    
    PATH is the directory to scan. Defaults to current directory if not specified."""
    console = Console()
    scanner = DiskScanner(console)
    
    try:
        path_obj = Path(path).resolve()
        if not path_obj.is_dir():
            console.print("[red]Error: Specified path must be a directory")
            sys.exit(1)
            
        console.print(f"[green]Scanning[/green] {path_obj}")
        largest_files, largest_dirs = scanner.scan_directory(path_obj, max_files=files, max_dirs=dirs)
        
        # Display results in tables
        file_table = Table(title="Largest Files")
        file_table.add_column("Size", justify="right", style="cyan")
        file_table.add_column("Storage", style="yellow")
        file_table.add_column("Path")
        
        for file in files:
            file_table.add_row(
                scanner.format_size(file.size),
                "☁️ iCloud" if file.is_icloud else "💾 Local",
                str(file.path.relative_to(path_obj))
            )
        
        dir_table = Table(title="Largest Directories")
        dir_table.add_column("Size", justify="right", style="cyan")
        dir_table.add_column("Storage", style="yellow")
        dir_table.add_column("Path")
        
        for dir in dirs:
            dir_table.add_row(
                scanner.format_size(dir.size),
                "☁️ iCloud" if dir.is_icloud else "💾 Local",
                str(dir.path.relative_to(path_obj))
            )
        
        console.print()
        console.print(file_table)
        console.print()
        console.print(dir_table)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
