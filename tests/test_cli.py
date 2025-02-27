import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from click.testing import CliRunner
from rich.console import Console

# Mock the entire textual_ui module before any imports happen
textual_ui_mock = mock.MagicMock()
textual_ui_mock.run_textual_ui = mock.MagicMock()

# Apply module-level mocking
with mock.patch.dict('sys.modules', {'disk_scanner.textual_ui': textual_ui_mock}):
    # Now we can safely import the CLI module
    from disk_scanner.cli import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_directory() -> Generator:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create some test files
        (root / "small.txt").write_text("x" * 100)
        (root / "medium.txt").write_text("x" * 1000)
        (root / "large.txt").write_text("x" * 10000)

        # Create a subdirectory
        subdir = root / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("x" * 5000)

        yield root


@pytest.fixture
def test_console() -> Console:
    """Create a Rich console for testing."""
    return Console(force_terminal=False, width=100, color_system=None)


def test_cli_basic_scan(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test basic CLI scanning functionality."""
    # Reset any mocks that might have been called in previous tests
    textual_ui_mock.run_textual_ui.reset_mock()
    
    # Don't pass the console as obj, as it might be causing issues
    result = cli_runner.invoke(main, [str(test_directory)])

    assert result.exit_code == 0
    output = result.output.lower()

    # Check for expected content - adjust based on actual CLI output
    assert "path" in output  # Most CLI outputs will include the path
    assert "size" in output  # Most CLI outputs will include size information


def test_cli_custom_limits(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test CLI with custom file and directory limits."""
    result = cli_runner.invoke(
        main, [str(test_directory), "--files", "2", "--dirs", "1"]
    )

    assert result.exit_code == 0
    output = result.output.lower()

    # Adjust assertions based on actual CLI output
    assert "path" in output
    assert "size" in output


def test_cli_json_output(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test saving results to JSON file."""
    with cli_runner.isolated_filesystem():
        output_file = Path("results.json")
        result = cli_runner.invoke(
            main, [str(test_directory), "--output", str(output_file)]
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "scan_info" in data
        assert "largest_files" in data
        assert "largest_directories" in data


def test_cli_invalid_path(cli_runner: CliRunner) -> None:
    """Test CLI behavior with invalid path."""
    result = cli_runner.invoke(main, ["nonexistent_directory"])

    # The CLI should handle invalid paths gracefully
    assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()


def test_cli_keyboard_interrupt(
    cli_runner: CliRunner,
    test_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CLI handling of keyboard interrupt."""

    def mock_scan(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt()

    # Patch the scan_directory method
    import disk_scanner.disk_scanner

    monkeypatch.setattr(disk_scanner.disk_scanner.DiskScanner, "scan_directory", mock_scan)

    result = cli_runner.invoke(main, [str(test_directory)])

    assert result.exit_code == 1
    assert "cancelled" in result.output.lower() or "interrupted" in result.output.lower()


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test CLI help output."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "usage" in result.output.lower()
    assert "options" in result.output.lower()

    # Verify all options are documented
    assert "--files" in result.output
    assert "--dirs" in result.output
    assert "--output" in result.output


def test_cli_default_path(cli_runner: CliRunner) -> None:
    """Test CLI with default path (current directory)."""
    with cli_runner.isolated_filesystem():
        # Create a test file in current directory
        Path("test.txt").write_text("x" * 1000)

        result = cli_runner.invoke(main)

        assert result.exit_code == 0
        assert "test.txt" in result.output.lower()


def test_cli_interactive_mode(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test CLI interactive mode triggers the textual UI."""
    # Reset the mock
    textual_ui_mock.run_textual_ui.reset_mock()
    
    # The interactive flag should trigger the textual UI
    cli_runner.invoke(main, [str(test_directory), "--interactive"])
    
    # Verify that run_textual_ui was called
    textual_ui_mock.run_textual_ui.assert_called_once()
    
    # The path should be passed to run_textual_ui
    args, _ = textual_ui_mock.run_textual_ui.call_args
    assert str(test_directory) == str(args[0])
