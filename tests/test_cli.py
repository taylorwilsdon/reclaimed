import json
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from click.testing import CliRunner
from rich.console import Console


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


# Create a more comprehensive mock for textual and its submodules
class MockTextual:
    def __init__(self):
        self.app = mock.MagicMock()
        self.app.App = mock.MagicMock()
        self.app.ComposeResult = mock.MagicMock()
        self.on = mock.MagicMock()
        self.work = mock.MagicMock()
        self.containers = mock.MagicMock()
        self.containers.Container = mock.MagicMock()
        self.containers.Grid = mock.MagicMock()
        self.containers.Horizontal = mock.MagicMock()
        self.containers.Vertical = mock.MagicMock()
        self.screen = mock.MagicMock()
        self.screen.Screen = mock.MagicMock()
        self.screen.ModalScreen = mock.MagicMock()
        self.widgets = mock.MagicMock()
        self.widgets.Button = mock.MagicMock()
        self.widgets.DataTable = mock.MagicMock()
        self.widgets.Footer = mock.MagicMock()
        self.widgets.Header = mock.MagicMock()
        self.widgets.Label = mock.MagicMock()
        self.widgets.ProgressBar = mock.MagicMock()
        self.widgets.Static = mock.MagicMock()


# Apply the mock before importing
textual_mock = MockTextual()
sys.modules['textual'] = textual_mock
sys.modules['textual.app'] = textual_mock.app
sys.modules['textual.containers'] = textual_mock.containers
sys.modules['textual.screen'] = textual_mock.screen
sys.modules['textual.widgets'] = textual_mock.widgets

# Now import the CLI module
from disk_scanner.cli import main


def test_cli_basic_scan(cli_runner: CliRunner, test_directory: Path, test_console: Console) -> None:
    """Test basic CLI scanning functionality."""
    result = cli_runner.invoke(main, [str(test_directory)], obj={"console": test_console})

    assert result.exit_code == 0
    output = result.output.lower()

    # Check for expected content
    assert "scanning" in output
    assert "largest files" in output
    assert "largest directories" in output

    # Check for test files (case insensitive)
    assert "large.txt" in output
    assert "medium.txt" in output
    assert "small.txt" in output
    assert "subdir" in output


def test_cli_custom_limits(
    cli_runner: CliRunner, test_directory: Path, test_console: Console
) -> None:
    """Test CLI with custom file and directory limits."""
    result = cli_runner.invoke(
        main, [str(test_directory), "--files", "2", "--dirs", "1"], obj={"console": test_console}
    )

    assert result.exit_code == 0
    output = result.output.lower()

    # Count the number of .txt files mentioned
    txt_files = [line for line in output.split("\n") if ".txt" in line]
    assert len(txt_files) <= 2


def test_cli_json_output(
    cli_runner: CliRunner, test_directory: Path, test_console: Console
) -> None:
    """Test saving results to JSON file."""
    with cli_runner.isolated_filesystem():
        output_file = Path("results.json")
        result = cli_runner.invoke(
            main, [str(test_directory), "--output", str(output_file)], obj={"console": test_console}
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "scan_info" in data
        assert "largest_files" in data
        assert "largest_directories" in data


def test_cli_invalid_path(cli_runner: CliRunner, test_console: Console) -> None:
    """Test CLI behavior with invalid path."""
    result = cli_runner.invoke(main, ["nonexistent_directory"], obj={"console": test_console})

    assert result.exit_code == 2  # Click's standard exit code for invalid input
    assert "error" in result.output.lower()


def test_cli_keyboard_interrupt(
    cli_runner: CliRunner,
    test_directory: Path,
    test_console: Console,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CLI handling of keyboard interrupt."""

    def mock_scan(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt()

    # Patch the scan_directory method
    import disk_scanner.disk_scanner

    monkeypatch.setattr(disk_scanner.disk_scanner.DiskScanner, "scan_directory", mock_scan)

    result = cli_runner.invoke(main, [str(test_directory)], obj={"console": test_console})

    assert result.exit_code == 1
    assert "cancelled" in result.output.lower()


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


def test_cli_default_path(cli_runner: CliRunner, test_console: Console) -> None:
    """Test CLI with default path (current directory)."""
    with cli_runner.isolated_filesystem():
        # Create a test file in current directory
        Path("test.txt").write_text("x" * 1000)

        result = cli_runner.invoke(main, obj={"console": test_console})

        assert result.exit_code == 0
        assert "test.txt" in result.output.lower()


def test_cli_rich_output_format(
    cli_runner: CliRunner, test_directory: Path, test_console: Console
) -> None:
    """Test that Rich formatting is applied correctly."""
    result = cli_runner.invoke(main, [str(test_directory)], obj={"console": test_console})

    assert result.exit_code == 0
    output = result.output.lower()

    # Check for expected table elements
    assert "largest files" in output
    assert "largest directories" in output
    assert "size" in output
    assert "path" in output
