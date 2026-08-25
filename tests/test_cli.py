"""Command-line behavior promised by the README."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from reclaimed.cli import main
from reclaimed.core.types import ScanResult
from reclaimed.version import __version__


def test_version_option() -> None:
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_documented_limit_aliases_and_jobs(tmp_path: Path) -> None:
    captured = {}

    class FakeScanner:
        def __init__(self, options, console):
            captured["options"] = options

        def scan(self, path):
            return ScanResult([], [], 0, 0, {})

    with patch("reclaimed.cli.DiskScanner", FakeScanner):
        result = CliRunner().invoke(
            main,
            [
                str(tmp_path),
                "--no-interactive",
                "--files",
                "3",
                "--dirs",
                "4",
                "--jobs",
                "2",
                "--apparent-size",
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["options"].max_files == 3
    assert captured["options"].max_dirs == 4
    assert captured["options"].max_workers == 2
    assert captured["options"].actual_size is False


def test_interactive_output_is_forwarded_for_post_tui_export(tmp_path: Path) -> None:
    output = tmp_path / "result.json"

    with patch("reclaimed.cli.run_textual_ui") as run_ui:
        result = CliRunner().invoke(main, [str(tmp_path), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert run_ui.call_args.kwargs["output_path"] == output


def test_interactive_size_mode_is_forwarded(tmp_path: Path) -> None:
    with patch("reclaimed.cli.run_textual_ui") as run_ui:
        result = CliRunner().invoke(main, [str(tmp_path), "--apparent-size"])

    assert result.exit_code == 0, result.output
    assert run_ui.call_args.kwargs["actual_size"] is False
