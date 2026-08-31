"""Tests for proportional result-table formatting."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from reclaimed.core.types import FileInfo
from reclaimed.ui.formatters import TableFormatter, format_display_path
from reclaimed.utils.formatters import format_bar


def test_format_bar_is_fixed_width_and_clamped() -> None:
    bar = format_bar(0.348, 20)

    assert len(bar) == 20
    assert bar.count("█") == 7
    assert format_bar(-1, 4) == " " * 4
    assert format_bar(2, 4) == "█" * 4


def test_display_path_is_relative_and_preserves_basename() -> None:
    root = Path("/scan")
    path = root / "a-very-long-directory-name" / "important.sqlite"

    display = format_display_path(path, root, 24)

    assert len(display) <= 24
    assert display.endswith("important.sqlite")
    assert "…" in display


def test_usage_table_has_compact_columns_and_conditional_storage() -> None:
    console = Console(width=100)
    formatter = TableFormatter(console)
    local = FileInfo(Path("/scan/local.bin"), 50, 0.0, False)
    cloud = FileInfo(Path("/scan/cloud.bin"), 25, 0.0, True)

    local_table = formatter.format_files_table([local], Path("/scan"), 100)
    cloud_table = formatter.format_files_table([local, cloud], Path("/scan"), 100)

    assert [column.header for column in local_table.columns] == ["Size", "Bar", "%", "Path"]
    assert [column.header for column in cloud_table.columns] == [
        "Size",
        "Bar",
        "%",
        "Storage",
        "Path",
    ]
    assert local_table.show_lines is False


def test_onedrive_items_get_a_storage_column_and_badge() -> None:
    output = StringIO()
    console = Console(file=output, width=100, force_terminal=False)
    formatter = TableFormatter(console)
    item = FileInfo(Path("/scan/onedrive.bin"), 25, 0.0, False, True)

    table = formatter.format_files_table([item], Path("/scan"), 100)
    console.print(table)

    assert [column.header for column in table.columns][-2:] == ["Storage", "Path"]
    assert "OneDrive" in output.getvalue()


def test_rendered_table_keeps_the_end_of_a_long_basename() -> None:
    output = StringIO()
    console = Console(file=output, width=80, force_terminal=False)
    formatter = TableFormatter(console)
    item = FileInfo(
        Path("/scan") / ("abcdef0123456789" * 4 + ".pack"),
        100,
        0.0,
        False,
    )

    console.print(formatter.format_files_table([item], Path("/scan"), 100))

    assert ".pack" in output.getvalue()
