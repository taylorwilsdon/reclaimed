"""Textual UI for reclaimed with interactive file/folder management."""

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    LoadingIndicator,
    ProgressBar,
    RadioButton,
    RadioSet,
    Select,
    Static,
)
from textual.worker import Worker, WorkerState

from ..core import DiskScanner, FileInfo, ScanOptions, ScanResult
from ..core.errors import DiskScannerError
from ..utils.formatters import format_bar, format_size
from .formatters import format_display_path, format_percentage
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


class ConfirmationDialog(ModalScreen[bool]):
    """A modal dialog for confirming file/folder deletion."""

    def __init__(self, item_path: Path, item_size: int, is_dir: bool = False):
        super().__init__()
        self.item_path = item_path
        self.item_size = item_size
        self.is_dir = is_dir
        self.item_type = "directory" if is_dir else "file"

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with Container(id="dialog-container"):
            yield Static("DELETE ITEM", classes="dialog-eyebrow")
            yield Static(f"Delete this {self.item_type}?", id="dialog-title")
            yield Static(str(self.item_path), id="dialog-path", markup=False)
            yield Static(
                f"This will free up {format_size(self.item_size)}.",
                id="dialog-size-info",
            )

            if self.is_dir:
                yield Static(
                    "This also removes every item inside the directory.",
                    classes="dialog-warning",
                )

            with Horizontal(id="dialog-buttons"):
                yield Button(
                    "Cancel", variant="default", id="cancel-button", compact=True, flat=True
                )
                yield Button(
                    "Delete", variant="error", id="confirm-button", compact=True, flat=True
                )

    @on(Button.Pressed, "#cancel-button")
    def cancel_deletion(self) -> None:
        """Cancel the deletion operation."""
        self.dismiss(False)

    @on(Button.Pressed, "#confirm-button")
    def confirm_deletion(self) -> None:
        """Confirm the deletion operation."""
        self.dismiss(True)


class SortOptions(ModalScreen[Optional[str]]):
    """A modal dialog for selecting sort options."""

    def compose(self) -> ComposeResult:
        """Compose the sort options dialog."""
        with Container(id="sort-container"):
            yield Static("SORT RESULTS", classes="dialog-eyebrow")
            yield Static("Sort by", id="sort-title")
            with RadioSet(id="sort-options", compact=True):
                yield RadioButton("Size (largest first)", id="sort-size", value=True)
                yield RadioButton("Last modified (newest first)", id="sort-modified")
                yield RadioButton("Name (A-Z)", id="sort-name")
                yield RadioButton("Path (A-Z)", id="sort-path")

            with Horizontal(id="sort-buttons"):
                yield Button("Cancel", variant="default", id="sort-cancel", compact=True, flat=True)
                yield Button("Apply", variant="success", id="sort-apply", compact=True, flat=True)

    @on(Button.Pressed, "#sort-cancel")
    def cancel_sort(self) -> None:
        """Cancel the sort operation."""
        self.dismiss(None)

    @on(Button.Pressed, "#sort-apply")
    def apply_sort(self) -> None:
        """Apply the selected sort option."""
        sort_option = self.query_one("#sort-options").pressed_button.id
        self.dismiss(sort_option)


class ReclaimedHeader(Header):
    """A branded masthead built on Textual's customizable header API."""

    def format_title(self) -> Content:
        """Render a compact wordmark and product descriptor."""
        return Content.from_markup(
            f"[bold]{self.screen_title.upper()}[/]  [dim]╱[/]  "
            f"[dim]{self.screen_sub_title.upper()}[/]"
        )

    def _on_click(self) -> None:
        """Keep the branded masthead at its intentional fixed height."""


class ReclaimedApp(App[None]):
    """Textual app for reclaimed with interactive file management."""

    CSS = TEXTUAL_CSS
    TITLE = "Reclaimed"
    SUB_TITLE = "Storage intelligence"

    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (76, "-compact"), (116, "-wide")]

    NAVIGATION = Binding.Group("Navigate", compact=True)
    RESULTS = Binding.Group("Results", compact=True)
    APP = Binding.Group("App", compact=True)

    BINDINGS = [
        Binding("f", "focus_files", group=NAVIGATION),
        Binding("d", "focus_dirs", group=NAVIGATION),
        Binding("tab", "toggle_focus", group=NAVIGATION),
        Binding("s", "sort", group=RESULTS),
        Binding("r", "refresh", group=RESULTS),
        Binding("p", "toggle_pause", group=RESULTS),
        Binding("h", "hide_selected", group=RESULTS),
        Binding("u", "show_hidden", group=RESULTS),
        Binding("delete", "delete_selected", group=RESULTS),
        Binding("t", "next_theme", group=APP),
        Binding("?", "help", group=APP),
        Binding("q", "quit", group=APP),
    ]

    THEMES = (
        "solarized-dark",
        "nord",
        "rose-pine-moon",
        "catppuccin-mocha",
        "atom-one-dark",
        "textual-light",
    )

    # The path remains the final column even when status/storage columns appear.
    COL_PATH = -1

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
        self.completed_result: Optional[ScanResult] = None
        self.largest_files: List[FileInfo] = []
        self.largest_dirs: List[FileInfo] = []
        self.current_focus = "files"  # Tracks which table has focus
        self.sort_method = "sort-size"  # Default sort method
        self.progress_manager = None  # Will be initialized after mount
        self.hidden_dirs: set = set()  # Directories hidden from current view
        self._hidden_cache: dict = {}  # Cache for _is_hidden results
        self._last_table_items = {}
        self._displayed_items: Dict[str, List[FileInfo]] = {
            "files-table": [],
            "dirs-table": [],
        }
        self._table_storage_state = {"files-table": False, "dirs-table": False}
        self.scan_task: Optional[Worker] = None
        self.scan_paused = False
        # Created per scan, inside the event loop, so the worker can await it.
        self._resume_gate: Optional[asyncio.Event] = None
        self._paused_total = 0.0  # Seconds spent paused during the current scan
        self._paused_at: Optional[float] = None
        self._indicator_refresh: Optional[float] = None  # Dots rate, kept across a pause
        self.theme = self.THEMES[0]

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield ReclaimedHeader(
            show_clock=True,
            icon="♻",
            time_format="%H:%M",
            id="app-header",
        )

        with Container(id="main-container"):
            with Horizontal(id="path-bar"):
                yield LoadingIndicator(id="scan-progress")
                yield Static("SCANNING", id="scan-state", classes="scanning")
                yield Static(str(self.path), id="path-display", markup=False)

            with Horizontal(id="summary-strip"):
                with Container(classes="metric-card"):
                    yield Static("0 B", id="scan-total", classes="metric-value")
                    yield Static("DISCOVERED", classes="metric-label")
                with Container(classes="metric-card"):
                    yield Static("0", id="scan-count", classes="metric-value")
                    yield Static("FILES", classes="metric-label")
                with Container(classes="metric-card"):
                    yield Static("00:00", id="scan-timer", classes="metric-value")
                    yield Static("ELAPSED", classes="metric-label")
                with Container(classes="metric-card"):
                    yield Static("0", id="hidden-count", classes="metric-value")
                    yield Static("HIDDEN", classes="metric-label")

            yield ProgressBar(
                total=1,
                show_percentage=False,
                show_eta=False,
                id="scan-progress-bar",
            )

            with Horizontal(id="toolbar"):
                yield Static("Largest items", id="results-title")
                yield Static("Sort", id="sort-label")
                yield Select(
                    (
                        ("Size · largest first", "sort-size"),
                        ("Modified · newest first", "sort-modified"),
                        ("Name · A–Z", "sort-name"),
                        ("Path · A–Z", "sort-path"),
                    ),
                    value=self.sort_method,
                    allow_blank=False,
                    compact=True,
                    id="sort-select",
                    tooltip="Choose how both result tables are ordered",
                )
                yield Button(
                    "Theme",
                    id="theme-button",
                    action="app.next_theme",
                    compact=True,
                    flat=True,
                    tooltip="Cycle through Textual's built-in themes (T)",
                )
                yield Button(
                    "Delete",
                    id="delete-button",
                    variant="error",
                    compact=True,
                    flat=True,
                    disabled=True,
                    tooltip="Delete the selected item (Delete key)",
                )
                yield Button(
                    "Pause",
                    id="pause-button",
                    action="app.toggle_pause",
                    compact=True,
                    flat=True,
                    disabled=True,
                    tooltip="Freeze the scan without losing progress (P)",
                )
                yield Button(
                    "Rescan",
                    id="refresh-button",
                    variant="primary",
                    action="app.refresh",
                    compact=True,
                    flat=True,
                    tooltip="Scan this directory again (R)",
                )

            with Horizontal(id="tables-container"):
                with Container(id="dirs-panel", classes="table-panel"):
                    with Horizontal(classes="section-header"):
                        yield Static("Directories", classes="section-title")
                        yield Static("0 results", id="dirs-result-count", classes="result-count")
                    dirs_table = DataTable(
                        id="dirs-table",
                        cursor_type="row",
                        zebra_stripes=True,
                        fixed_columns=1,
                    )
                    dirs_table.add_columns(
                        ("Status", "status"),
                        ("Size", "size"),
                        ("Bar", "bar"),
                        ("%", "percent"),
                        ("Path", "path"),
                    )
                    yield dirs_table

                with Container(id="files-panel", classes="table-panel"):
                    with Horizontal(classes="section-header"):
                        yield Static("Files", classes="section-title")
                        yield Static("0 results", id="files-result-count", classes="result-count")
                    files_table = DataTable(
                        id="files-table",
                        cursor_type="row",
                        zebra_stripes=True,
                        fixed_columns=1,
                    )
                    files_table.add_columns(
                        ("Size", "size"), ("Bar", "bar"), ("%", "percent"), ("Path", "path")
                    )
                    yield files_table

        yield Footer(compact=True)

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        # Initialize progress manager
        self.progress_manager = ProgressManager(self, "main-container")

        # Start the initial scan
        self.scan_directory()

        # Set initial focus to the files table after scan completes
        self.set_timer(0.1, self.focus_active_table)

    def _set_scan_state(self, state: str) -> None:
        """Update the scan status pill and its semantic styling."""
        status = self.query_one("#scan-state", Static)
        status.update(state.upper())
        status.update_classes(
            {
                "scanning": state == "scanning",
                "paused": state == "paused",
                "complete": state == "ready",
                "failed": state == "failed",
            }
        )

    def _scan_elapsed(self) -> float:
        """Seconds the current scan has actually spent working, ignoring pauses."""
        now = time.monotonic()
        elapsed = now - self.start_time - self._paused_total
        if self._paused_at is not None:
            elapsed -= now - self._paused_at
        return elapsed

    def _set_pause_button(self, label: str, *, disabled: bool = False) -> None:
        """Keep the toolbar pause control in sync with the scan state."""
        try:
            button = self.query_one("#pause-button", Button)
        except Exception:
            # Toolbar might not be mounted yet, or is being torn down.
            return
        button.label = label
        button.disabled = disabled

    def _set_dots_animated(self, animated: bool) -> None:
        """Run or freeze the scanning dots so they match the scan itself."""
        try:
            indicator = self.query_one("#scan-progress", LoadingIndicator)
        except Exception:
            # Indicator might not be mounted yet, or is being torn down.
            return
        if animated:
            indicator.auto_refresh = self._indicator_refresh
        else:
            self._indicator_refresh = indicator.auto_refresh
            indicator.auto_refresh = None

    def action_toggle_pause(self) -> None:
        """Freeze the running scan in place, or let it carry on."""
        if self._resume_gate is None or self.scan_task is None:
            return
        if not self.scan_task.is_running:
            return

        self.scan_paused = not self.scan_paused
        if self.scan_paused:
            self._paused_at = time.monotonic()
            self._resume_gate.clear()
            self._set_scan_state("paused")
            self._set_pause_button("Resume")
            self._set_dots_animated(False)
            self.notify("Scan paused", timeout=2)
        else:
            if self._paused_at is not None:
                self._paused_total += time.monotonic() - self._paused_at
                self._paused_at = None
            self._resume_gate.set()
            self._set_scan_state("scanning")
            self._set_pause_button("Pause")
            self._set_dots_animated(True)
            self.notify("Scan resumed", timeout=2)

    def _update_scan_metrics(
        self, scanned: int, total_size: int, progress: Optional[float] = None
    ) -> None:
        """Refresh the dashboard metrics shown above the result tables."""
        self.query_one("#scan-count", Static).update(f"{scanned:,}")
        self.query_one("#scan-total", Static).update(format_size(total_size))
        if progress is not None:
            self.query_one("#scan-progress-bar", ProgressBar).update(
                progress=max(0.0, min(1.0, progress))
            )

    def _update_hidden_count(self) -> None:
        """Keep the hidden-directory metric in sync with the current view."""
        self.query_one("#hidden-count", Static).update(f"{len(self.hidden_dirs):,}")

    def scan_directory(self) -> None:
        """Scan the directory and update the tables incrementally."""
        # Reset state before starting new scan
        self.largest_files = []
        self.largest_dirs = []
        self.completed_result = None
        self._last_table_items.clear()
        for table_name in ("files-table", "dirs-table"):
            self._displayed_items[table_name] = []

        # Start timing with monotonic clock
        self.start_time = time.monotonic()

        # A fresh scan always starts unpaused, with an open gate for the worker.
        self.scan_paused = False
        self._paused_total = 0.0
        self._paused_at = None
        self._resume_gate = asyncio.Event()
        self._resume_gate.set()
        self._set_pause_button("Pause", disabled=False)

        # Notify user that scan is starting
        self.notify("Starting directory scan...", timeout=2)

        self._set_scan_state("scanning")
        self._update_scan_metrics(0, 0, 0.0)
        self.query_one("#scan-timer", Static).update("00:00")
        self.query_one("#files-result-count", Static).update("0 results")
        self.query_one("#dirs-result-count", Static).update("0 results")
        for table in self.query(DataTable):
            table.clear()

        # Reset sort tracking
        self._files_sorted = False
        self._dirs_sorted = False

        # Show loading indicator
        try:
            loading = self.query_one("#scan-progress")
            loading.styles.display = "block"
        except Exception:
            # Loading indicator might not be mounted yet
            pass

        # Start async scan with optimized worker function
        self.scan_task = self.run_worker(
            self._scan_directory_worker(),
            name="Directory Scanner",
            description="Scanning directory...",
            exclusive=True,
        )

    async def _scan_directory_worker(self):
        """Worker function to process async generator from scan_async with optimized UI updates."""
        # Track when we last updated the UI
        last_ui_update = 0
        base_ui_update_interval = 0.5

        # Get UI elements once, with error handling
        try:
            timer_display = self.query_one("#scan-timer")
            self.query_one("#scan-count")
        except Exception:
            # UI elements not mounted yet, wait a bit and retry
            await asyncio.sleep(0.1)
            try:
                timer_display = self.query_one("#scan-timer")
                self.query_one("#scan-count")
            except Exception:
                # Still not available, abort scan
                self.notify("UI not ready, please try again", severity="error")
                return

        # Create independent timer task
        async def update_timer():
            while True:
                try:
                    minutes, seconds = divmod(int(self._scan_elapsed()), 60)
                    timer_display.update(f"Time: {minutes:02d}:{seconds:02d}")
                except Exception:
                    # Timer display might have been removed, stop updating
                    break
                await asyncio.sleep(0.1)

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

                # Update the dashboard independently of the more expensive tables.
                try:
                    self._update_scan_metrics(
                        progress.scanned, progress.total_size, progress.progress
                    )
                except Exception:
                    # Dashboard widgets might have been removed while quitting.
                    pass

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
                if self.scan_paused or current_time - last_ui_update > ui_update_interval:
                    self.largest_files = files_buffer
                    self.largest_dirs = dirs_buffer
                    self.apply_sort(self.sort_method)
                    self.update_tables()
                    last_ui_update = current_time
                    last_file_count = progress.scanned
                    await asyncio.sleep(0)

                # Suspend here while paused. The scan generator stays parked on
                # its last yield, so no traversal happens until the gate opens.
                if self._resume_gate is not None:
                    await self._resume_gate.wait()

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
        try:
            loading = self.query_one("#scan-progress")
        except Exception:
            # Loading indicator might not be available
            loading = None

        if event.worker.state == WorkerState.SUCCESS:
            # Hide loading indicator
            if loading:
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

            # Keep export data independent from the mutable lists backing the
            # interactive tables. Hiding and deletion may alter those lists.
            if self.scanner.last_result is not None:
                completed = self.scanner.last_result
                self.completed_result = ScanResult(
                    files=list(completed.files),
                    directories=list(completed.directories),
                    total_size=completed.total_size,
                    files_scanned=completed.files_scanned,
                    access_issues=dict(completed.access_issues),
                    actual_size=completed.actual_size,
                )

            # Get elapsed time for notification
            elapsed = self._scan_elapsed()

            # Update the final dashboard state.
            self.scan_paused = False
            self._set_pause_button("Pause", disabled=True)
            try:
                self._set_scan_state("ready")
                self._update_scan_metrics(file_count, self.scanner._total_size, 1.0)
            except Exception:
                # Dashboard widgets might have been removed while quitting.
                pass

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
            if loading:
                loading.styles.display = "none"
            self.scan_paused = False
            self._set_pause_button("Pause", disabled=True)
            self._set_scan_state("failed")
            self.notify("Scan failed!", severity="error")

    # Track last table update to avoid redundant updates
    _last_table_update = {}
    _last_table_items = {}

    def update_tables(self) -> None:
        """Update both data tables with current data, avoiding redundant updates."""
        # Check if tables exist before trying to update them
        # This prevents race conditions during app startup
        try:
            # Update files table if data has changed
            self._update_table_if_changed("#files-table", self.largest_files)

            # Update dirs table if data has changed
            self._update_table_if_changed("#dirs-table", self.largest_dirs)

            self._update_delete_button()
        except Exception:
            # Tables might not be mounted yet, skip update
            pass

    def _update_table_if_changed(self, table_id: str, items: List[FileInfo]) -> None:
        """Update a table only if its data has changed significantly.

        Args:
            table_id: CSS selector for the table
            items: List of FileInfo objects to display
        """
        filtered_items = [item for item in items if not self._is_hidden(item.path)]
        current_items = self._last_table_items.get(table_id, [])
        table_name = table_id.lstrip("#")
        show_storage = any(
            item.is_icloud or item.is_onedrive
            for item in self.largest_files + self.largest_dirs
        )
        if (
            current_items == filtered_items
            and self._table_storage_state[table_name] == show_storage
        ):
            return

        # Update last items
        self._last_table_items[table_id] = filtered_items

        # Now update the table
        self._update_table(table_id, filtered_items)

    def _update_table(self, table_id: str, items: List[FileInfo]) -> None:
        """Helper method to update a specific table with items.

        Args:
            table_id: CSS selector for the table
            items: List of FileInfo objects to display
        """
        # Use query instead of query_one to handle missing tables gracefully
        tables = self.query(table_id)
        if not tables:
            # Table doesn't exist yet, skip update
            return

        table = tables.first()
        table.can_focus = True

        table_name = table_id.lstrip("#")
        show_storage = any(
            item.is_icloud or item.is_onedrive
            for item in self.largest_files + self.largest_dirs
        )
        if self._table_storage_state[table_name] != show_storage:
            table.clear(columns=True)
            columns = []
            if table_name == "dirs-table":
                columns.append(("Status", "status"))
            columns.extend([("Size", "size"), ("Bar", "bar"), ("%", "percent")])
            if show_storage:
                columns.append(("Storage", "storage"))
            columns.append(("Path", "path"))
            table.add_columns(*columns)
            self._table_storage_state[table_name] = show_storage
        else:
            table.clear()

        max_items = self.options.max_files if table_id == "#files-table" else self.options.max_dirs
        display_items = items[:max_items]
        self._displayed_items[table_name] = display_items
        count = len(display_items)
        self.query_one(f"#{table_name.removesuffix('-table')}-result-count", Static).update(
            f"{count:,} result{'s' if count != 1 else ''}"
        )

        # Render all items at once - Textual's DataTable has built-in virtualization
        for item_info in display_items:
            self._add_row_to_table(table, item_info)

    def _add_row_to_table(self, table, item_info: FileInfo) -> None:
        """Add a single row to a table.

        Args:
            table: The DataTable to add the row to
            item_info: FileInfo object with data for the row
        """
        total_size = self.scanner._total_size
        fraction = item_info.size / total_size if total_size else 0.0
        width = table.size.width or (self.size.width if hasattr(self, "size") else 80)
        show_storage = self._table_storage_state[table.id]
        show_status = table.id == "dirs-table"
        reserved_width = 53 if show_storage else 41
        if show_status:
            reserved_width += 13
        path_width = max(12, width - reserved_width)
        theme = self.current_theme

        row = []
        if show_status:
            row.append(
                Text(
                    "✓ Done" if item_info.is_complete else "… Scanning",
                    style=theme.success if item_info.is_complete else theme.warning,
                )
            )
        row.extend([
            format_size(item_info.size),
            Text(format_bar(fraction, 20), style=theme.secondary),
            format_percentage(fraction),
        ])
        if show_storage:
            if item_info.is_icloud:
                storage_status, storage_style = "☁ iCloud", theme.primary
            elif item_info.is_onedrive:
                storage_status, storage_style = "☁ OneDrive", theme.secondary
            else:
                storage_status, storage_style = "Local", theme.success
            row.append(
                Text(storage_status, style=storage_style)
            )
        row.append(format_display_path(item_info.path, self.path, path_width))
        table.add_row(*row, key=str(item_info.path))

    def _is_hidden(self, path: Path) -> bool:
        """Check if a path or any of its parents is hidden.

        Args:
            path: Path to check

        Returns:
            True if the path should be hidden, False otherwise
        """
        # Use cached result if available
        path_str = str(path)
        if path_str in self._hidden_cache:
            return self._hidden_cache[path_str]

        # Check if this exact path is hidden
        if path in self.hidden_dirs:
            self._hidden_cache[path_str] = True
            return True

        # Check parents from most specific to least specific
        current_path = path
        while current_path != current_path.parent:
            current_path = current_path.parent
            if current_path in self.hidden_dirs:
                self._hidden_cache[path_str] = True
                return True

        self._hidden_cache[path_str] = False
        return False

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
            "sort-modified": lambda x: -x.last_modified,
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
        """Focus and open the always-visible sort control."""
        select = self.query_one("#sort-select", Select)
        select.focus()
        select.action_show_overlay()

    @on(Select.Changed, "#sort-select")
    def sort_selection_changed(self, event: Select.Changed) -> None:
        """Apply sort changes from the toolbar control."""
        if event.value not in {"sort-size", "sort-modified", "sort-name", "sort-path"}:
            return
        self.sort_method = str(event.value)
        self._files_sorted = False
        self._dirs_sorted = False
        self.apply_sort(self.sort_method)
        self._last_table_items.clear()
        self.update_tables()

    def action_next_theme(self) -> None:
        """Cycle through a curated set of built-in Textual themes."""
        try:
            index = self.THEMES.index(self.theme)
        except ValueError:
            index = -1
        self.theme = self.THEMES[(index + 1) % len(self.THEMES)]
        self._last_table_items.clear()
        self.update_tables()
        self.notify(f"Theme: {self.theme}", timeout=2)

    def action_refresh(self) -> None:
        """Refresh the directory scan."""
        # Clear hidden directories on refresh
        self.hidden_dirs.clear()
        self._hidden_cache.clear()
        self._update_hidden_count()
        self.scan_directory()

    def _update_parent_sizes_on_hide(self, hidden_path: Path, hidden_size: int) -> None:
        """Update parent directory sizes when a directory is hidden.

        Args:
            hidden_path: Path of the hidden directory
            hidden_size: Size of the hidden directory to subtract
        """
        # Create updated directory list with adjusted sizes
        updated_dirs = []

        for dir_info in self.largest_dirs:
            # Check if this directory is a parent of the hidden directory
            try:
                if hidden_path != dir_info.path:
                    hidden_path.relative_to(dir_info.path)
                    # Create new FileInfo with reduced size
                    new_size = max(0, dir_info.size - hidden_size)
                    updated_dir = FileInfo(
                        path=dir_info.path,
                        size=new_size,
                        last_modified=dir_info.last_modified,
                        is_icloud=dir_info.is_icloud,
                        is_onedrive=dir_info.is_onedrive,
                        is_complete=dir_info.is_complete,
                    )
                    updated_dirs.append(updated_dir)
                else:
                    # Keep the original directory info
                    updated_dirs.append(dir_info)
            except (ValueError, OSError):
                # Handle any path comparison errors, keep original
                updated_dirs.append(dir_info)

        # Replace the directories list with updated one
        self.largest_dirs = updated_dirs

    def action_hide_selected(self) -> None:
        """Hide the selected directory from the current view."""
        # Only works for directories
        if self.current_focus != "dirs":
            self.notify(
                "Hiding only works for directories. Switch to directories view (D) first.",
                timeout=3,
            )
            return

        try:
            table = self.query_one("#dirs-table")
        except Exception:
            self.notify("Directories table not available yet", timeout=3)
            return

        # Check if a row is selected
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            displayed = self._displayed_items["dirs-table"]
            if row < len(displayed):
                selected = displayed[row]
                path = selected.path
                hidden_size = selected.size
                self.hidden_dirs.add(path)
                self._hidden_cache.clear()
                self._update_hidden_count()

                # Update parent directory sizes
                self._update_parent_sizes_on_hide(path, hidden_size)

                # Force update the tables to reflect the hidden directory
                # Clear change detection cache to force refresh
                self._last_table_items.clear()
                self.update_tables()

                self.notify(f"Hidden: {path.name} ({format_size(hidden_size)})", timeout=3)

                # Focus back to the table
                self.focus_active_table()
        else:
            self.notify(
                "No directory selected. Use arrow keys to select a directory first.", timeout=3
            )

    def action_show_hidden(self) -> None:
        """Unhide all hidden directories by refreshing the scan."""
        if not self.hidden_dirs:
            self.notify("No directories are currently hidden.", timeout=3)
            return

        hidden_count = len(self.hidden_dirs)

        # Clear hidden directories and refresh scan to restore original sizes
        self.hidden_dirs.clear()
        self._hidden_cache.clear()
        self._update_hidden_count()
        noun = "directory" if hidden_count == 1 else "directories"
        self.notify(
            f"Unhiding {hidden_count} {noun} and refreshing scan...",
            timeout=3,
        )
        self.scan_directory()

    def action_delete_selected(self) -> None:
        """Delete the selected file or directory."""
        # Get the current table based on the focus
        try:
            table = self.query_one(
                "#files-table" if self.current_focus == "files" else "#dirs-table"
            )
        except Exception:
            self.notify("Table not available yet", timeout=3)
            return

        # Check if a row is selected
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            table_name = "files-table" if self.current_focus == "files" else "dirs-table"
            displayed = self._displayed_items[table_name]
            if row < len(displayed):
                selected = displayed[row]
                path = selected.path
                item_size = selected.size

                is_dir = path.is_dir()

                # Show confirmation dialog
                def handle_confirmation(confirmed: bool) -> None:
                    if confirmed:
                        try:
                            # Delete the file/directory
                            if is_dir:
                                shutil.rmtree(path)
                            else:
                                os.remove(path)

                            # Remove the item from our data
                            items = (
                                self.largest_files
                                if self.current_focus == "files"
                                else self.largest_dirs
                            )
                            items[:] = [item for item in items if item.path != path]

                            # Remove the row from the table using the path as the key
                            try:
                                table = self.query_one(
                                    "#files-table"
                                    if self.current_focus == "files"
                                    else "#dirs-table"
                                )
                                table.remove_row(str(path))
                            except Exception:
                                # Table might not exist, just continue
                                pass

                            # If we have remaining rows, ensure cursor is in a valid position
                            if len(table.rows) > 0:
                                current_row = (
                                    table.cursor_coordinate.row if table.cursor_coordinate else 0
                                )
                                # If cursor would be past the end, move it to last row
                                if current_row >= len(table.rows):
                                    current_row = len(table.rows) - 1
                                table.move_cursor(row=current_row, column=0)

                            self.notify(
                                f"Deleted {path.name}, freed {format_size(item_size)}",
                                timeout=5,
                            )
                            self._update_delete_button()
                        except Exception as e:
                            self.notify(f"Error deleting {path}: {e}", timeout=5)

                self.push_screen(
                    ConfirmationDialog(path, item_size, is_dir), handle_confirmation
                )

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
        [bold]Reclaimed Help[/]

        [bold]Navigation[/]
        - Arrow keys: Navigate within a table
        - F: Focus Files table
        - D: Focus Directories table
        - Tab: Move between tables

        [bold]Actions[/]
        - Delete: Delete selected item
        - S: Sort items
        - H: Hide selected directory (dirs only)
        - U: Unhide all directories
        - R: Refresh scan (clears hidden dirs)
        - P: Pause or resume the running scan
        - T: Cycle theme
        - Ctrl+P: Open command palette and choose any theme
        - Q: Quit application

        [bold]Selection[/]
        - Click on a row to select it
        - Press Delete to remove the selected item
        """
        self.notify(help_text, timeout=10)

    # Tab button handlers removed as we now have a unified view

    def _update_delete_button(self) -> None:
        """Update the delete button label and state based on the current cursor."""
        try:
            btn = self.query_one("#delete-button", Button)
        except Exception:
            return
        table_name = "files-table" if self.current_focus == "files" else "dirs-table"
        try:
            table = self.query_one(f"#{table_name}")
        except Exception:
            btn.disabled = True
            btn.label = "Delete"
            return
        displayed = self._displayed_items.get(table_name, [])
        if table.cursor_coordinate is not None and table.cursor_coordinate.row < len(displayed):
            item = displayed[table.cursor_coordinate.row]
            btn.disabled = False
            btn.label = f"Delete ({format_size(item.size)})"
        else:
            btn.disabled = True
            btn.label = "Delete"

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update delete button when the cursor moves to a new row."""
        table_id = event.data_table.id
        if table_id == "files-table":
            self.current_focus = "files"
        else:
            self.current_focus = "dirs"
        self._update_delete_button()

    @on(Button.Pressed, "#delete-button")
    def delete_button_pressed(self) -> None:
        """Handle delete button click."""
        self.action_delete_selected()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data tables."""
        table_id = event.data_table.id
        row = event.cursor_row

        # Update current_focus based on which table was selected
        if table_id == "files-table":
            self.current_focus = "files"
        else:
            self.current_focus = "dirs"

        items = self._displayed_items.get(table_id, [])
        if 0 <= row < len(items):
            path = items[row].path
            self.notify(f"Selected: {path}", timeout=3)

    def focus_active_table(self) -> None:
        """Focus the currently active table based on current_focus."""
        table_id = "#files-table" if self.current_focus == "files" else "#dirs-table"
        try:
            table = self.query_one(table_id)
            # Only set focus if the table has rows
            if len(table.rows) > 0:
                self.set_focus(table)
                # Set cursor to first row if no row is selected
                if table.cursor_coordinate is None:
                    table.move_cursor(row=0, column=0)
        except Exception:
            # Table might not be mounted yet, skip
            pass

    def on_unmount(self) -> None:
        """Event handler called when app is unmounted."""
        if self.on_exit_callback:
            self.on_exit_callback()


def run_textual_ui(
    path: Path,
    max_files: int = 100,
    max_dirs: int = 100,
    skip_dirs: Optional[List[str]] = None,
    max_workers: Optional[int] = None,
    output_path: Optional[Path] = None,
    actual_size: bool = True,
) -> None:
    """Run the Textual UI application.

    Args:
        path: Directory to scan
        max_files: Maximum number of files to show.
        max_dirs: Maximum number of directories to show.
        skip_dirs: List of directory names to skip
        max_workers: Concurrent directory-listing workers.
        output_path: Optional JSON destination written after the TUI exits.
        actual_size: Count allocated bytes instead of logical file sizes.
    """
    options = ScanOptions(
        max_files=max_files,
        max_dirs=max_dirs,
        skip_dirs=skip_dirs,
        max_workers=max_workers,
        actual_size=actual_size,
    )

    app = ReclaimedApp(path, options)
    app.run()
    if output_path is not None:
        if app.completed_result is None:
            raise DiskScannerError("Cannot export results because no scan completed")
        app.scanner.save_scan_result(output_path, app.completed_result, app.path)
