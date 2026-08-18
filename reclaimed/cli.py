"""Command-line interface for reclaimed"""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console

from .core.errors import AccessError, DiskScannerError, InvalidPathError, ScanInterruptedError
from .core.scanner import DiskScanner
from .core.types import ScanOptions
from .ui.formatters import TableFormatter
from .ui.textual_app import run_textual_ui
from .utils.formatters import format_size
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def handle_scan_error(
    error: Exception, console: Console, root_path: Optional[Path] = None
) -> int:
    """Handle scanning errors with appropriate messages.

    Args:
        error: Exception that occurred
        console: Rich console for output

    Returns:
        Exit code to use
    """
    if isinstance(error, InvalidPathError):
        console.print(f"[red]Error:[/] Invalid path: {error.path}")
        return 1
    elif isinstance(error, ScanInterruptedError):
        console.print("\n[yellow]Scan interrupted.[/] Showing partial results...")
        if error.partial is not None and root_path is not None:
            formatter = TableFormatter(console)
            formatter.print_scan_summary(
                error.partial.files,
                error.partial.directories,
                root_path,
                error.partial.access_issues,
                error.partial.total_size,
            )
            console.print(
                f"\nScanned [cyan]{error.partial.files_scanned:,}[/] files, "
                f"total size: [cyan]{format_size(error.partial.total_size)}[/]"
            )
        return 0
    elif isinstance(error, AccessError):
        console.print(f"[red]Access error:[/] {error}")
        return 1
    elif isinstance(error, DiskScannerError):
        console.print(f"[red]Scan error:[/] {error}")
        return 1
    else:
        console.print(f"[red]Unexpected error:[/] {error}")
        logger.exception("Unexpected error during scan")
        return 2


@click.command()
@click.version_option(__version__)
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
)
@click.option(
    "--max-files",
    "--files",
    "-f",
    type=click.IntRange(min=0),
    default=10,
    help="Maximum number of largest files to show",
    show_default=True,
)
@click.option(
    "--max-dirs",
    "--dirs",
    "-d",
    type=click.IntRange(min=0),
    default=10,
    help="Maximum number of largest directories to show",
    show_default=True,
)
@click.option(
    "--skip-dirs",
    "-s",
    multiple=True,
    help="Additional directories to skip (can be specified multiple times)",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--interactive/--no-interactive",
    "-i",
    default=True,
    help="Use interactive TUI mode (default) or simple text output",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save the JSON scan results",
)
@click.option(
    "--jobs",
    "-j",
    type=click.IntRange(1, 8),
    default=4,
    help="Concurrent directory-listing workers",
    show_default=True,
)
def main(
    path: Path,
    max_files: int,
    max_dirs: int,
    skip_dirs: Tuple[str, ...],
    debug: bool,
    interactive: bool,
    output: Optional[Path],
    jobs: int,
) -> None:
    """Analyze disk space usage and find large files/directories.

    Scans the specified PATH (defaults to current directory) and displays the
    largest files and directories found. The scan can be interrupted at any
    time with Ctrl+C to show partial results.
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    console = Console()
    scanner: Optional[DiskScanner] = None

    try:
        if interactive:
            # Run interactive TUI mode
            run_textual_ui(
                path,
                max_files,
                max_dirs,
                list(skip_dirs),
                max_workers=jobs,
                output_path=output,
            )
            return
        else:
            # Run non-interactive mode
            formatter = TableFormatter(console)

            # Configure scanner
            options = ScanOptions(
                max_files=max_files,
                max_dirs=max_dirs,
                skip_dirs=list(skip_dirs),
                max_workers=jobs,
            )

            scanner = DiskScanner(options, console)

            # Perform scan
            result = scanner.scan(path)

            # Display results
            formatter.print_scan_summary(
                result.files,
                result.directories,
                path,
                result.access_issues,
                result.total_size,
            )

            # Show final stats
            console.print(
                f"\nScanned [cyan]{result.files_scanned:,}[/] files, "
                f"total size: [cyan]{format_size(result.total_size)}[/]"
            )

            # Save results if output path is specified
            if output:
                scanner.save_results(output, result.files, result.directories, path)

            return

    except Exception as e:
        if (
            output is not None
            and scanner is not None
            and isinstance(e, ScanInterruptedError)
            and e.partial is not None
        ):
            try:
                scanner.save_results(output, e.partial.files, e.partial.directories, path)
            except DiskScannerError as save_error:
                sys.exit(handle_scan_error(save_error, console, path))
        sys.exit(handle_scan_error(e, console, path))


if __name__ == "__main__":
    main()
