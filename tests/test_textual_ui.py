"""Tests for the Textual UI functionality."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from textual.widgets import DataTable, Select

from reclaimed.core.types import FileInfo, ScanOptions, ScanResult
from reclaimed.ui.textual_app import ReclaimedApp, ReclaimedHeader, run_textual_ui


def test_sort_keys() -> None:
    """The supported sort keys produce the expected ordering."""
    file_a = FileInfo(Path("/test/a.txt"), 3000, 0.0, False)
    file_b = FileInfo(Path("/test/b.txt"), 2000, 0.0, False)
    file_c = FileInfo(Path("/test/c.txt"), 1000, 0.0, False)

    assert sorted((file_c, file_a, file_b), key=lambda item: item.path.name.lower()) == [
        file_a,
        file_b,
        file_c,
    ]
    assert sorted((file_c, file_a, file_b), key=lambda item: str(item.path).lower()) == [
        file_a,
        file_b,
        file_c,
    ]
    assert sorted((file_c, file_a, file_b), key=lambda item: -item.size) == [
        file_a,
        file_b,
        file_c,
    ]


def test_modern_dashboard_mounts_and_responds(tmp_path: Path) -> None:
    """The real Textual widget tree mounts at wide and narrow breakpoints."""

    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()

            assert app.theme == "solarized-dark"
            assert app.screen.has_class("-wide")
            assert app.query_one("#app-header", ReclaimedHeader).region.height == 3
            assert app.query_one("#sort-select", Select).compact is True

            tables = list(app.query(DataTable))
            assert len(tables) == 2
            assert all(table.cursor_type == "row" for table in tables)
            assert all(table.zebra_stripes for table in tables)
            dirs_table = app.query_one("#dirs-table", DataTable)
            assert [column.label.plain for column in dirs_table.columns.values()][0] == "Status"

            await pilot.resize_terminal(70, 30)
            await pilot.pause()
            assert app.screen.has_class("-narrow")
            assert not app.screen.has_class("-wide")

    asyncio.run(exercise_app())


def test_toolbar_sort_and_theme_actions(tmp_path: Path) -> None:
    """Toolbar controls sort the displayed data and cycle built-in themes."""

    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            app.largest_files = [
                FileInfo(tmp_path / "z.txt", 10, 1.0, False),
                FileInfo(tmp_path / "a.txt", 20, 2.0, False),
            ]
            app.largest_dirs = []
            app._files_sorted = False
            app._dirs_sorted = False

            app.query_one("#sort-select", Select).value = "sort-name"
            await pilot.pause()
            assert [item.path.name for item in app.largest_files] == ["a.txt", "z.txt"]

            app.action_next_theme()
            await pilot.pause()
            assert app.theme == "nord"

    asyncio.run(exercise_app())


def test_selecting_table_row_uses_row_selected_event_api(tmp_path: Path) -> None:
    """Selecting a result uses the row index exposed by Textual's event."""
    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            selected = FileInfo(tmp_path / "selected.txt", 10, 1.0, False)
            app._displayed_items["files-table"] = [selected]
            table = app.query_one("#files-table", DataTable)
            row_key = table.add_row("10 B", "", "100%", str(selected.path))

            with patch.object(app, "notify") as notify:
                app.on_data_table_row_selected(DataTable.RowSelected(table, 0, row_key))

            assert app.current_focus == "files"
            notify.assert_called_once_with(f"Selected: {selected.path}", timeout=3)

    asyncio.run(exercise_app())


def test_run_textual_ui() -> None:
    """The entry point constructs and runs the app."""
    with patch("reclaimed.ui.textual_app.ReclaimedApp") as mock_app:
        mock_app_instance = MagicMock()
        mock_app.return_value = mock_app_instance

        run_textual_ui(Path("/test"), 50, 30)

        assert mock_app.called
        assert mock_app_instance.run.called


def test_directory_row_shows_completion_and_onedrive(tmp_path: Path) -> None:
    """Directory rows expose both live subtree status and OneDrive storage."""

    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            directory = FileInfo(tmp_path / "OneDrive", 10, 0.0, False, True, False)
            app.largest_dirs = [directory]
            app._last_table_items.clear()
            app.update_tables()
            await pilot.pause()

            table = app.query_one("#dirs-table", DataTable)
            row = table.get_row(str(directory.path))
            assert row[0].plain == "… Scanning"
            assert any(getattr(cell, "plain", cell) == "☁ OneDrive" for cell in row)

    asyncio.run(exercise_app())


def test_interactive_export_uses_completed_snapshot(tmp_path: Path) -> None:
    """UI mutations cannot leak into the JSON export source."""
    output = tmp_path / "results.json"
    completed = ScanResult(
        files=[FileInfo(tmp_path / "original.bin", 10, 0.0, False)],
        directories=[FileInfo(tmp_path, 10, 0.0, False)],
        total_size=10,
        files_scanned=1,
        access_issues={},
    )

    with patch("reclaimed.ui.textual_app.ReclaimedApp") as mock_app:
        app = mock_app.return_value
        app.completed_result = completed
        app.path = tmp_path
        # These represent UI state after hiding or deleting results.
        app.largest_files = []
        app.largest_dirs = []

        run_textual_ui(tmp_path, output_path=output)

    app.scanner.save_scan_result.assert_called_once_with(output, completed, tmp_path)
