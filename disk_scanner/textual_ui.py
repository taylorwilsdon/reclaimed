"""Textual UI for reclaim with interactive file/folder management."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Callable

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Static, 
    Label, Input, RadioSet, RadioButton
)

from .disk_scanner import DiskScanner, FileInfo


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
            yield Static(f"Are you sure you want to delete this {self.item_type}?", id="dialog-title")
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


class ReclaimApp(App):
    """Textual app for reclaim with interactive file management."""

    CSS = """
    /* Solarized Dark color palette */
    $base03: #002b36;
    $base02: #073642;
    $base01: #586e75;
    $base00: #657b83;
    $base0: #839496;
    $base1: #93a1a1;
    $base2: #eee8d5;
    $base3: #fdf6e3;
    $yellow: #b58900;
    $orange: #cb4b16;
    $red: #dc322f;
    $magenta: #d33682;
    $violet: #6c71c4;
    $blue: #268bd2;
    $cyan: #2aa198;
    $green: #859900;

    Screen {
        background: $base03;
        color: $base0;
    }

    #header {
        dock: top;
        height: 1;
        background: $base02;
        color: $base1;
        text-align: center;
    }

    #footer {
        dock: bottom;
        height: 1;
        background: $base02;
        color: $base1;
    }

    #main-container {
        width: 100%;
        height: 100%;
    }

    #title {
        dock: top;
        height: 1;
        background: $base02;
        color: $blue;
        text-align: center;
    }

    #path-display {
        dock: top;
        height: 1;
        background: $base02;
        color: $base01;
        padding: 0 1;
    }

    #tabs-container {
        dock: top;
        height: 3;
        background: $base03;
        color: $base0;
    }

    .tab-button {
        width: 50%;
        height: 3;
        content-align: center middle;
        background: $base02;
        color: $base1;
    }

    .tab-button.active {
        background: $blue;
        color: $base3;
    }

    .tab-button:hover {
        background: $base01;
    }

    #files-table, #dirs-table {
        height: 100%;
        width: 100%;
        background: $base03;
        color: $base0;
    }

    DataTable {
        border: none;
    }

    DataTable > .datatable--header {
        background: $base02;
        color: $base1;
    }

    DataTable > .datatable--cursor {
        background: $base01;
    }

    #dialog-container {
        width: 60%;
        height: auto;
        background: $base02;
        border: tall $blue;
        padding: 1 2;
    }

    #dialog-title {
        width: 100%;
        height: 1;
        content-align: center middle;
        color: $base1;
    }

    #dialog-path {
        width: 100%;
        height: 3;
        content-align: center middle;
        margin: 1 0;
        color: $red;
    }

    #dialog-buttons {
        width: 100%;
        height: 3;
        content-align: center middle;
        margin-top: 1;
    }

    #sort-container {
        width: 40%;
        height: auto;
        background: $base02;
        border: tall $blue;
        padding: 1 2;
    }

    #sort-title {
        width: 100%;
        height: 1;
        content-align: center middle;
        margin-bottom: 1;
        color: $base1;
    }

    #sort-buttons {
        width: 100%;
        height: 3;
        content-align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
        background: $base01;
        color: $base2;
    }

    Button:hover {
        background: $base00;
    }

    Button.primary {
        background: $blue;
    }

    Button.success {
        background: $green;
    }

    Button.error {
        background: $red;
    }

    RadioButton {
        background: $base02;
        color: $base1;
    }

    RadioButton:checked {
        background: $blue;
        color: $base3;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "toggle_files", "Show Files"),
        Binding("d", "toggle_dirs", "Show Directories"),
        Binding("s", "sort", "Sort"),
        Binding("r", "refresh", "Refresh"),
        Binding("delete", "delete_selected", "Delete"),
        Binding("?", "help", "Help"),
    ]

    def __init__(
        self, 
        path: Path, 
        max_files: int = 100, 
        max_dirs: int = 100,
        on_exit_callback: Optional[Callable] = None
    ):
        """Initialize the app with the path to scan."""
        super().__init__()
        self.path = path.resolve()
        self.max_files = max_files
        self.max_dirs = max_dirs
        self.on_exit_callback = on_exit_callback
        self.scanner = DiskScanner(None)  # We'll handle the console output
        self.largest_files: List[FileInfo] = []
        self.largest_dirs: List[FileInfo] = []
        self.current_view = "files"  # or "dirs"
        self.sort_method = "sort-size"  # Default sort method

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header(show_clock=True)
        yield Static("[bold]Reclaim[/bold]", id="title")
        
        with Container(id="main-container"):
            yield Static(f"Path: {self.path}", id="path-display")
            
            with Container(id="tabs-container"):
                yield Button("Files", id="files-tab", classes="tab-button active")
                yield Button("Directories", id="dirs-tab", classes="tab-button")
            
            # Files table
            files_table = DataTable(id="files-table")
            files_table.add_columns("Size", "Storage", "Path")
            yield files_table
            
            # Directories table (initially hidden)
            dirs_table = DataTable(id="dirs-table")
            dirs_table.add_columns("Size", "Storage", "Path")
            dirs_table.display = False
            yield dirs_table
        
        yield Footer()

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.scan_directory()

    def scan_directory(self) -> None:
        """Scan the directory and update the tables."""
        self.notify("Scanning directory... This may take a while.", style="#b58900")
        
        # Perform the scan
        self.largest_files, self.largest_dirs = self.scanner.scan_directory(
            self.path, self.max_files, self.max_dirs
        )
        
        # Apply current sort
        self.apply_sort(self.sort_method)
        
        # Update the tables
        self.update_tables()
        
        self.notify(f"Scan complete. Found {len(self.largest_files)} files and {len(self.largest_dirs)} directories.", style="#859900")

    def update_tables(self) -> None:
        """Update the data tables with current data."""
        # Update files table
        files_table = self.query_one("#files-table")
        files_table.clear()
        
        for file_info in self.largest_files:
            try:
                rel_path = file_info.path.relative_to(self.path)
            except ValueError:
                rel_path = file_info.path
                
            storage_status = "☁️ iCloud" if file_info.is_icloud else "💾 Local"
            storage_cell = Text(storage_status, style="#268bd2" if file_info.is_icloud else "#859900")
            
            files_table.add_row(
                self.scanner.format_size(file_info.size),
                storage_cell,
                str(rel_path),
                key=str(file_info.path)
            )
        
        # Update directories table
        dirs_table = self.query_one("#dirs-table")
        dirs_table.clear()
        
        for dir_info in self.largest_dirs:
            try:
                rel_path = dir_info.path.relative_to(self.path)
            except ValueError:
                rel_path = dir_info.path
                
            storage_status = "☁️ iCloud" if dir_info.is_icloud else "💾 Local"
            storage_cell = Text(storage_status, style="#268bd2" if dir_info.is_icloud else "#859900")
            
            dirs_table.add_row(
                self.scanner.format_size(dir_info.size),
                storage_cell,
                str(rel_path),
                key=str(dir_info.path)
            )

    def apply_sort(self, sort_method: str) -> None:
        """Apply the selected sort method to the data."""
        if sort_method == "sort-size":
            # Already sorted by size from the scanner
            pass
        elif sort_method == "sort-name":
            self.largest_files.sort(key=lambda x: x.path.name.lower())
            self.largest_dirs.sort(key=lambda x: x.path.name.lower())
        elif sort_method == "sort-path":
            self.largest_files.sort(key=lambda x: str(x.path).lower())
            self.largest_dirs.sort(key=lambda x: str(x.path).lower())

    def action_toggle_files(self) -> None:
        """Switch to the files view."""
        if self.current_view != "files":
            self.current_view = "files"
            self.query_one("#files-table").display = True
            self.query_one("#dirs-table").display = False
            self.query_one("#files-tab").add_class("active")
            self.query_one("#dirs-tab").remove_class("active")

    def action_toggle_dirs(self) -> None:
        """Switch to the directories view."""
        if self.current_view != "dirs":
            self.current_view = "dirs"
            self.query_one("#files-table").display = False
            self.query_one("#dirs-table").display = True
            self.query_one("#files-tab").remove_class("active")
            self.query_one("#dirs-tab").add_class("active")

    def action_sort(self) -> None:
        """Show the sort options dialog."""
        def handle_sort_result(sort_option: Optional[str]) -> None:
            if sort_option:
                self.sort_method = sort_option
                self.apply_sort(sort_option)
                self.update_tables()
        
        self.push_screen(SortOptions(), handle_sort_result)

    def action_refresh(self) -> None:
        """Refresh the directory scan."""
        self.scan_directory()

    def action_delete_selected(self) -> None:
        """Delete the selected file or directory."""
        # Get the current table based on the view
        table = self.query_one("#files-table" if self.current_view == "files" else "#dirs-table")
        
        # Check if a row is selected
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if row < len(table.rows):
                # Get the path from the key
                path_str = table.get_row_at(row).key
                path = Path(path_str)
                is_dir = path.is_dir()
                
                # Show confirmation dialog
                def handle_confirmation(confirmed: bool) -> None:
                    if confirmed:
                        try:
                            if is_dir:
                                shutil.rmtree(path)
                            else:
                                os.remove(path)
                            self.notify(f"Successfully deleted {path}", style="#859900")
                            # Refresh the view
                            self.scan_directory()
                        except Exception as e:
                            self.notify(f"Error deleting {path}: {e}", style="#dc322f")
                
                self.push_screen(ConfirmationDialog(path, is_dir), handle_confirmation)

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
        [#93a1a1]Reclaim Help[/]
        
        [#268bd2]Navigation:[/]
        - Arrow keys: Navigate tables
        - F: Switch to Files view
        - D: Switch to Directories view
        
        [#268bd2]Actions:[/]
        - Delete: Delete selected item
        - S: Sort items
        - R: Refresh scan
        - Q: Quit application
        
        [#268bd2]Selection:[/]
        - Click on a row to select it
        - Press Delete to remove the selected item
        """
        self.notify(help_text, severity="information", timeout=10)

    @on(Button.Pressed, "#files-tab")
    def switch_to_files(self) -> None:
        """Handle files tab button press."""
        self.action_toggle_files()

    @on(Button.Pressed, "#dirs-tab")
    def switch_to_dirs(self) -> None:
        """Handle directories tab button press."""
        self.action_toggle_dirs()

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in data tables."""
        table_id = event.data_table.id
        row = event.cursor_coordinate.row
        
        if table_id == "files-table":
            items = self.largest_files
        else:
            items = self.largest_dirs
            
        if 0 <= row < len(items):
            path = event.data_table.get_row_at(row).key
            self.notify(f"Selected: {path}")

    def on_unmount(self) -> None:
        """Event handler called when app is unmounted."""
        if self.on_exit_callback:
            self.on_exit_callback()


def run_textual_ui(path: Path, max_files: int = 100, max_dirs: int = 100) -> None:
    """Run the Textual UI application."""
    app = ReclaimApp(path, max_files, max_dirs)
    app.run()
