"""Textual UI for reclaimed with interactive file/folder management."""

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Callable, List, Optional

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    LoadingIndicator,
    RadioButton,
    RadioSet,
    Static,
)
from textual.worker import Worker, WorkerState

from ..core import DiskScanner, FileInfo, ScanOptions
from ..utils.formatters import format_size
from .styles import TEXTUAL_CSS


class ProgressManager:
    """Manages progress bar lifecycle to prevent duplicate IDs and provide smoother updates."""

    def __init__(self, app: App, container_id: str):
        """Initialize the progress manager.

        Args:
            app: The parent Textual app
            container_id: ID of the container to mount progress bars in
        """
        self.app = app
        self.container_id = container_id
        self.last_update_time = 0
        self.update_interval = 0.1  # Update at most 10 times per second
        self.last_progress_value = 0
        self.min_progress_increment = 0.005  # Minimum 0.5% change to update


class ConfirmationDialog(ModalScreen):
    """A modal dialog for confirming file/folder deletion."""

    def __init__(self, item_path: Path, is_dir: bool = False):
        super().__init__()
        self.item_path = item_path
        self.is_dir = is_dir
        self.item_type = "directory" if is_dir else "file"

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with Container(id="dialog-container"):
            yield Static(
                f"Are you sure you want to delete this {self.item_type}?", id="dialog-title"
            )
            yield Static(f"[bold red]{self.item_path}[/]", id="dialog-path")

            if self.is_dir:
                yield Static("[yellow]Warning: This will delete all contents recursively![/]")

            with Horizontal(id="dialog-buttons"):
                yield Button("Cancel", variant="primary", id="cancel-button")
                yield Button("Delete", variant="error", id="confirm-button")

    @on(Button.Pressed, "#cancel-button")
    def cancel_deletion(self) -> None:
        """Cancel the deletion operation."""
        self.dismiss(False)

    @on(Button.Pressed, "#confirm-button")
    def confirm_deletion(self) -> None:
        """Confirm the deletion operation."""
        self.dismiss(True)


class SortOptions(ModalScreen):
    """A modal dialog for selecting sort options."""

    def compose(self) -> ComposeResult:
        """Compose the sort options dialog."""
        with Container(id="sort-container"):
            yield Static("Sort by:", id="sort-title")
            with RadioSet(id="sort-options"):
                yield RadioButton("Size (largest first)", id="sort-size", value=True)
                yield RadioButton("Name (A-Z)", id="sort-name")
                yield RadioButton("Path (A-Z)", id="sort-path")

            with Horizontal(id="sort-buttons"):
                yield Button("Cancel", variant="primary", id="sort-cancel")
                yield Button("Apply", variant="success", id="sort-apply")

    @on(Button.Pressed, "#sort-cancel")
    def cancel_sort(self) -> None:
        """Cancel the sort operation."""
        self.dismiss(None)

    @on(Button.Pressed, "#sort-apply")
    def apply_sort(self) -> None:
        """Apply the selected sort option."""
        sort_option = self.query_one("#sort-options").pressed_button.id
        self.dismiss(sort_option)


class ReclaimedApp(App):
    """Textual app for reclaimed with interactive file management."""

    CSS = TEXTUAL_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "focus_files", "Focus Files"),
        Binding("d", "focus_dirs", "Focus Directories"),
        Binding("tab", "toggle_focus", "Toggle Focus"),
        Binding("s", "sort", "Sort"),
        Binding("r", "refresh", "Refresh"),
        Binding("delete", "delete_selected", "Delete"),
        Binding("?", "help", "Help"),
    ]

    def __init__(
        self, path: Path, options: ScanOptions, on_exit_callback: Optional[Callable] = None
    ):
        """Initialize the app with the path to scan.

        Args:
            path: Directory to scan
            options: Scan configuration options
            on_exit_callback: Optional callback to run on exit
        """
        super().__init__()
        self.path = path.resolve()
        self.options = options
        self.on_exit_callback = on_exit_callback
        self.scanner = DiskScanner(options)
        self.largest_files: List[FileInfo] = []
        self.largest_dirs: List[FileInfo] = []
        self.current_focus = "files"  # Tracks which table has focus
        self.sort_method = "sort-size"  # Default sort method
        self.progress_manager = None  # Will be initialized after mount

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header(show_clock=True)
        yield Static("[bold]Reclaimed[/bold]", id="title")

        with Container(id="main-container"):
            # Status bar with scan info
            with Horizontal(id="status-bar"):
                yield Static("Path:", id="status-label")
                yield Static(f"{self.path}", id="path-display")
                yield Static("", id="scan-timer")
                yield Static("", id="scan-count")

            # Directories section
            yield Static("[bold]Largest Directories[/bold]", id="dirs-section-header")
            dirs_table = DataTable(id="dirs-table")
            dirs_table.add_columns("Size", "Storage", "Path")
            yield dirs_table

            # Files section
            yield Static("[bold]Largest Files[/bold]", id="files-section-header")
            files_table = DataTable(id="files-table")
            files_table.add_columns("Size", "Storage", "Path")
            yield files_table

        with Horizontal(id="footer-container"):
            yield Footer()
            yield LoadingIndicator(id="scan-progress")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        # Initialize progress manager
        self.progress_manager = ProgressManager(self, "main-container")

        # Start the initial scan
        self.scan_directory()

        # Set initial focus to the files table after scan completes
        self.set_timer(0.1, self.focus_active_table)

        # Check header visibility again after a short delay
        self.set_timer(1.0, self.check_header_visibility)

    def scan_directory(self) -> None:
        """Scan the directory and update the tables incrementally."""
        # Reset state before starting new scan
        self.largest_files = []
        self.largest_dirs = []

        # Start timing with monotonic clock
        self.start_time = time.monotonic()

        # Notify user that scan is starting
        self.notify("Starting directory scan...", timeout=2)

        # Reset sort tracking
        self._files_sorted = False
        self._dirs_sorted = False

        # Show loading indicator
        loading = self.query_one("#scan-progress")
        loading.styles.display = "block"

        # Start async scan with optimized worker function
        self.scan_task = self.run_worker(
            self._scan_directory_worker(),
            name="Directory Scanner",
            description="Scanning directory...",
        )

    async def _scan_directory_worker(self):
        """Worker function to process async generator from scan_async with optimized UI updates."""
        # Track when we last updated the UI
        last_ui_update = 0
        base_ui_update_interval = 0.5

        # Get UI elements once
        timer_display = self.query_one("#scan-timer")
        count_display = self.query_one("#scan-count")

        # Create independent timer task
        async def update_timer():
            start = time.monotonic()
            while True:
                elapsed = time.monotonic() - start
                minutes, seconds = divmod(int(elapsed), 60)
                timer_display.update(f"Time: {minutes:02d}:{seconds:02d}")
                await asyncio.sleep(0.05)  # Update 20 times per second for smooth display

        # Start timer task and store reference
        self._timer_task = asyncio.create_task(update_timer())

        # Buffers to collect data between UI updates
        files_buffer = []
        dirs_buffer = []
        last_file_count = 0

        # Initialize progress with default values in case of early exception
        progress = None
        current_time = time.monotonic()

        try:
            async for progress in self.scanner.scan_async(self.path):
                if not progress:
                    continue

                # Update our data in memory
                if progress.files:
                    files_buffer = progress.files
                if progress.dirs:
                    dirs_buffer = progress.dirs

                # Update file count independently
                count_display.update(f"Files: {progress.scanned:,}")

                # Dynamically adjust update interval based on files scanned
                ui_update_interval = base_ui_update_interval
                if progress.scanned > 100000:
                    ui_update_interval = 5.0
                elif progress.scanned > 50000:
                    ui_update_interval = 3.0
                elif progress.scanned > 10000:
                    ui_update_interval = 2.0
                elif progress.scanned > 5000:
                    ui_update_interval = 1.0

                # Check if it's time to update tables
                current_time = time.monotonic()
                if current_time - last_ui_update > ui_update_interval:
                    self.largest_files = files_buffer
                    self.largest_dirs = dirs_buffer
                    self.apply_sort(self.sort_method)
                    self.update_tables()
                    last_ui_update = current_time
                    last_file_count = progress.scanned
                    await asyncio.sleep(0)

        except Exception as e:
            self.notify(f"Scan error: {str(e)}", severity="error")
            raise

        finally:
            # Always clean up the timer task
            if hasattr(self, "_timer_task"):
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass

            # Dynamically adjust update interval based on files scanned
            ui_update_interval = base_ui_update_interval

            # Only process progress data if we have a valid progress object
            if progress is not None:
                if progress.scanned > 100000:
                    ui_update_interval = 5.0  # Very infrequent updates for huge directories
                elif progress.scanned > 50000:
                    ui_update_interval = 3.0  # Very infrequent updates for very large directories
                elif progress.scanned > 10000:
                    ui_update_interval = 2.0  # Less frequent updates for large directories
                elif progress.scanned > 5000:
                    ui_update_interval = 1.0  # Moderate updates for medium directories

                # Force an update if we've scanned a lot more files since the last update
                # This ensures we show progress even during long update intervals
                force_update = progress.scanned - last_file_count > 5000

                # Use adaptive interval between UI updates
                time_to_update = current_time - last_ui_update > ui_update_interval

                # Only update UI periodically, on completion, or when forced
                if time_to_update or progress.progress >= 1.0 or force_update:
                    # Update our data
                    self.largest_files = files_buffer
                    self.largest_dirs = dirs_buffer

                    # Apply sort and update tables
                    self.apply_sort(self.sort_method)
                    self.update_tables()
                    last_ui_update = current_time
                    last_file_count = progress.scanned

                    # Brief yield to allow UI to update, but keep it minimal
                    await asyncio.sleep(0)

        # Return final data
        return {
            "files": self.largest_files,
            "dirs": self.largest_dirs,
            "total_size": self.scanner._total_size,
            "file_count": self.scanner._file_count,
        }

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle updates from the background scan task with optimized UI updates."""
        if event.worker.name != "Directory Scanner":
            return

        # Get loading indicator
        loading = self.query_one("#scan-progress")

        if event.worker.state == WorkerState.SUCCESS:
            # Hide loading indicator
            loading.styles.display = "none"

            # Get result data from worker
            file_count = 0
            if event.worker.result:
                result = event.worker.result
                file_count = result.get("file_count", 0)

                # Only update UI if we have new data
                if "files" in result and result["files"]:
                    self.largest_files = result["files"]
                    self._files_sorted = False

                if "dirs" in result and result["dirs"]:
                    self.largest_dirs = result["dirs"]
                    self._dirs_sorted = False

            # Get elapsed time for notification
            elapsed = time.monotonic() - self.start_time

            # Update final file count
            count_display = self.query_one("#scan-count")
            count_display.update(f"Files: {file_count:,}")

            # Show completion notification
            self.notify(f"Scan complete in {elapsed:.1f}s. Found {file_count:,} files.", timeout=5)

            # Clean up timer task
            if hasattr(self, "_timer_task"):
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass

            # Apply sort and update tables only once at the end
            self.apply_sort(self.sort_method)
            self.update_tables()

            # focus the active table
            self.focus_active_table()

        elif event.worker.state == WorkerState.ERROR:
            # Hide loading indicator
            loading.styles.display = "none"
            self.notify("Scan failed!", severity="error")

    # Track last table update to avoid redundant updates
    _last_table_update = {}
    _last_table_items = {}

    def update_tables(self) -> None:
        """Update both data tables with current data, avoiding redundant updates."""
        # Update files table if data has changed
        self._update_table_if_changed("#files-table", self.largest_files)

        # Update dirs table if data has changed
        self._update_table_if_changed("#dirs-table", self.largest_dirs)

    def _update_table_if_changed(self, table_id: str, items: List[FileInfo]) -> None:
        """Update a table only if its data has changed significantly.

        Args:
            table_id: CSS selector for the table
            items: List of FileInfo objects to display
        """
        # Skip update if no items
        if not items:
            return

        # Check if data has changed significantly
        current_items = self._last_table_items.get(table_id, [])

        # If item count is the same, check if top items are the same
        if len(current_items) == len(items):
            # Only check the first few items for performance
            check_count = min(5, len(items))
            items_changed = False

            for i in range(check_count):
                if (
                    i >= len(current_items)
                    or items[i].path != current_items[i].path
                    or items[i].size != current_items[i].size
                ):
                    items_changed = True
                    break

            if not items_changed:
                # Data hasn't changed significantly, skip update
                return

        # Update last items
        self._last_table_items[table_id] = items

        # Now update the table
        self._update_table(table_id, items)

    def _update_table(self, table_id: str, items: List[FileInfo]) -> None:
        """Helper method to update a specific table with items.

        Args:
            table_id: CSS selector for the table
            items: List of FileInfo objects to display
        """
        table = self.query_one(table_id)
        table.clear()
        table.can_focus = True

        # Skip update if no items
        if not items:
            return

        # Limit the number of items to display for better performance
        display_items = items[: min(100, len(items))]

        # Render all items at once - Textual's DataTable has built-in virtualization
        for item_info in display_items:
            self._add_row_to_table(table, item_info)

    def _add_row_to_table(self, table, item_info: FileInfo) -> None:
        """Add a single row to a table.

        Args:
            table: The DataTable to add the row to
            item_info: FileInfo object with data for the row
        """
        try:
            rel_path = item_info.path.relative_to(self.path)
        except ValueError:
            rel_path = item_info.path

        storage_status = "☁️ iCloud" if item_info.is_icloud else "💾 Local"
        storage_cell = Text(storage_status, style="#268bd2" if item_info.is_icloud else "#859900")

        table.add_row(
            format_size(item_info.size), storage_cell, str(rel_path), key=str(item_info.path)
        )

    # Track current sort state to avoid redundant sorts
    _current_sort_method = "sort-size"
    _files_sorted = False
    _dirs_sorted = False

    def apply_sort(self, sort_method: str) -> None:
        """Apply the selected sort method to the data, avoiding redundant sorts."""
        # Skip if no data to sort
        if not self.largest_files and not self.largest_dirs:
            return

        # Skip if sort method hasn't changed and data is already sorted
        if sort_method == self._current_sort_method and self._files_sorted and self._dirs_sorted:
            return

        # Define sort keys based on method
        sort_keys = {
            "sort-size": lambda x: -x.size,  # Negative for descending order
            "sort-name": lambda x: x.path.name.lower(),
            "sort-path": lambda x: str(x.path).lower(),
        }

        # Get the appropriate sort key function
        key_func = sort_keys.get(sort_method)
        if not key_func:
            return  # Invalid sort method

        # Only sort if we have data and sort method has changed
        if self.largest_files:
            self.largest_files.sort(key=key_func)
            self._files_sorted = True

        if self.largest_dirs:
            self.largest_dirs.sort(key=key_func)
            self._dirs_sorted = True

        # Update current sort method
        self._current_sort_method = sort_method

    def action_focus_files(self) -> None:
        """Focus the files table."""
        self.current_focus = "files"
        self.focus_active_table()

    def action_focus_dirs(self) -> None:
        """Focus the directories table."""
        self.current_focus = "dirs"
        self.focus_active_table()

    def action_toggle_focus(self) -> None:
        """Toggle focus between files and directories tables."""
        self.current_focus = "dirs" if self.current_focus == "files" else "files"
        self.focus_active_table()

    def action_sort(self) -> None:
        """Show the sort options dialog."""

        def handle_sort_result(sort_option: Optional[str]) -> None:
            if sort_option:
                self.sort_method = sort_option
                self.apply_sort(sort_option)
                self.update_tables()
                self.focus_active_table()

        self.push_screen(SortOptions(), handle_sort_result)

    def action_refresh(self) -> None:
        """Refresh the directory scan."""
        self.scan_directory()

    def action_delete_selected(self) -> None:
        """Delete the selected file or directory."""
        # Get the current table based on the focus
        table = self.query_one("#files-table" if self.current_focus == "files" else "#dirs-table")

        # Check if a row is selected
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if row < len(table.rows):
                # Get the path from the row key
                # Get row data (unused but kept for potential future use)
                table.get_row_at(row)

                # In the current version of Textual, we need to access the key differently
                # The key is stored when we add the row, so we need to look it up in our data
                if self.current_focus == "files" and row < len(self.largest_files):
                    path = self.largest_files[row].path
                elif self.current_focus == "dirs" and row < len(self.largest_dirs):
                    path = self.largest_dirs[row].path
                else:
                    self.notify("Could not determine the path for this item", timeout=5)
                    return

                is_dir = path.is_dir()

                # Show confirmation dialog
                def handle_confirmation(confirmed: bool) -> None:
                    if confirmed:
                        try:
                            if is_dir:
                                shutil.rmtree(path)
                            else:
                                os.remove(path)
                            self.notify(f"Successfully deleted {path}", timeout=5)
                            # Refresh the view
                            self.scan_directory()
                        except Exception as e:
                            self.notify(f"Error deleting {path}: {e}", timeout=5)

                self.push_screen(ConfirmationDialog(path, is_dir), handle_confirmation)

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
        [#93a1a1]Reclaimed Help[/]

        [#268bd2]Navigation:[/]
        - Arrow keys: Navigate within a table
        - F: Focus Files table
        - D: Focus Directories table
        - Tab: Move between tables

        [#268bd2]Actions:[/]
        - Delete: Delete selected item
        - S: Sort items
        - R: Refresh scan
        - Q: Quit application

        [#268bd2]Selection:[/]
        - Click on a row to select it
        - Press Delete to remove the selected item
        """
        self.notify(help_text, timeout=10)

    # Tab button handlers removed as we now have a unified view

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in data tables."""
        table_id = event.data_table.id
        row = event.cursor_coordinate.row

        # Update current_focus based on which table was selected
        if table_id == "files-table":
            items = self.largest_files
            self.current_focus = "files"
        else:
            items = self.largest_dirs
            self.current_focus = "dirs"

        if 0 <= row < len(items):
            path = items[row].path
            self.notify(f"Selected: {path}", timeout=3)

    def check_header_visibility(self) -> None:
        """Check header visibility after a delay."""
        try:
            # Debug header visibility
            dirs_header = self.query_one("#dirs-section-header")
            files_header = self.query_one("#files-section-header")
            print(f"DEBUG: dirs_header visible: {dirs_header.styles.display}")
            print(f"DEBUG: files_header visible: {files_header.styles.display}")
            print(f"DEBUG: dirs_header text: {dirs_header.render()}")
            print(f"DEBUG: files_header text: {files_header.render()}")

            # Check the DOM order
            all_widgets = list(self.query("Static"))
            print("DEBUG: Widget order in DOM:")
            for i, widget in enumerate(all_widgets):
                print(f"DEBUG: {i}: {widget.id} - {widget.render()}")
        except Exception as e:
            print(f"DEBUG: Error checking headers: {e}")

    def focus_active_table(self) -> None:
        """Focus the currently active table based on current_focus."""
        table_id = "#files-table" if self.current_focus == "files" else "#dirs-table"
        table = self.query_one(table_id)

        # Only set focus if the table has rows
        if len(table.rows) > 0:
            self.set_focus(table)
            # Set cursor to first row if no row is selected
            if table.cursor_coordinate is None:
                table.move_cursor(row=0, column=0)

    def on_unmount(self) -> None:
        """Event handler called when app is unmounted."""
        if self.on_exit_callback:
            self.on_exit_callback()


def run_textual_ui(
    path: Path, max_files: int = 100, max_dirs: int = 100, skip_dirs: list[str] = None
) -> None:
    """Run the Textual UI application.

    Args:
        path: Directory to scan
        max_files: Maximum number of files to show
        max_dirs: Maximum number of directories to show
        skip_dirs: List of directory names to skip
    """
    if skip_dirs is None:
        skip_dirs = [".Trash", "System Volume Information"]

    options = ScanOptions(max_files=max_files, max_dirs=max_dirs, skip_dirs=skip_dirs)

    app = ReclaimedApp(path, options)
    app.run()
