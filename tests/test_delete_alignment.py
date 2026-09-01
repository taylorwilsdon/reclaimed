"""Regression tests for row/item alignment after a delete.

Every row-to-item lookup in the app (``_selected_item``, ``action_delete_selected``
and ``on_data_table_row_selected``) indexes ``_displayed_items`` by the
DataTable's cursor row. Removing a row from the table without removing the same
entry from ``_displayed_items`` shifts every later row by one, so the next
delete acts on a different file than the one highlighted.
"""

import asyncio
from pathlib import Path

from textual.widgets import DataTable

from reclaimed.core.types import FileInfo, ScanOptions
from reclaimed.ui.textual_app import ReclaimedApp


def _make_files(tmp_path: Path) -> list:
    """Create three real files, largest first, and describe them."""
    infos = []
    for name, size in (("big.bin", 3000), ("mid.bin", 2000), ("small.bin", 1000)):
        target = tmp_path / name
        target.write_bytes(b"x" * size)
        infos.append(FileInfo(target, size, 0.0, False))
    return infos


def _delete_row(app: ReclaimedApp, row: int) -> Path:
    """Delete the item at ``row`` the way the confirmed dialog callback does."""
    displayed = app._displayed_items["files-table"]
    target = displayed[row].path
    table = app.query_one("#files-table", DataTable)
    table.move_cursor(row=row, column=0)
    app.action_delete_selected()
    # The dialog is modal; approve it directly rather than driving keystrokes.
    app.screen.dismiss(True)
    return target


def test_displayed_items_stay_aligned_with_table_after_delete(tmp_path: Path) -> None:
    """After deleting a middle row, row N must still resolve to row N's file."""

    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            app.largest_files = _make_files(tmp_path)
            app.current_focus = "files"
            app._update_table("#files-table", app.largest_files)
            await pilot.pause()

            table = app.query_one("#files-table", DataTable)
            assert table.row_count == 3

            removed = _delete_row(app, 1)  # delete "mid.bin"
            await pilot.pause()

            assert not removed.exists()
            displayed = app._displayed_items["files-table"]

            # The stale entry must be gone, so the two stay the same length.
            assert len(displayed) == table.row_count == 2
            assert removed not in [item.path for item in displayed]

            # Row 1 now holds small.bin in the table; the lookup must agree.
            table.move_cursor(row=1, column=0)
            selected = app._selected_item()
            assert selected is not None
            assert selected.path.name == "small.bin"

    asyncio.run(exercise_app())


def test_second_delete_removes_the_highlighted_file(tmp_path: Path) -> None:
    """Two deletes in a row must each remove the file the cursor is on."""

    async def exercise_app() -> None:
        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            app.largest_files = _make_files(tmp_path)
            app.current_focus = "files"
            app._update_table("#files-table", app.largest_files)
            await pilot.pause()

            _delete_row(app, 0)  # big.bin
            await pilot.pause()

            # Row 0 is now mid.bin. Deleting it must not take small.bin instead.
            second = _delete_row(app, 0)
            await pilot.pause()

            assert second.name == "mid.bin"
            assert not (tmp_path / "mid.bin").exists()
            assert (tmp_path / "small.bin").exists()

    asyncio.run(exercise_app())


def test_delete_directory_symlink_does_not_delete_target(tmp_path: Path) -> None:
    """A directory symlink is a file-like entry and must not be traversed."""

    async def exercise_app() -> None:
        target = tmp_path / "target"
        target.mkdir()
        preserved = target / "preserved.txt"
        preserved.write_text("keep me")
        link = tmp_path / "directory-link"
        link.symlink_to(target, target_is_directory=True)

        app = ReclaimedApp(tmp_path, ScanOptions(max_files=5, max_dirs=5))
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            app.largest_files = [FileInfo(link, 0, 0.0, False)]
            app.current_focus = "files"
            app._update_table("#files-table", app.largest_files)
            await pilot.pause()

            removed = _delete_row(app, 0)
            await pilot.pause()

            assert removed == link
            assert not link.exists()
            assert preserved.read_text() == "keep me"

    asyncio.run(exercise_app())
