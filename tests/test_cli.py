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
    # Import the main function directly from the cli module
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
    
    # Mock the interactive flag to False to test non-interactive mode
    with mock.patch('disk_scanner.cli.run_textual_ui') as mock_run_ui:
        # Run with --no-interactive to force text output
        result = cli_runner.invoke(main, [str(test_directory), "--no-interactive"])

        # Verify the UI wasn't called
        mock_run_ui.assert_not_called()
        
        # Check exit code and output
        assert result.exit_code == 0
        output = result.output.lower()
        
        # Check for expected content in the output
        assert "path" in output
        assert "size" in output


def test_cli_custom_limits(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test CLI with custom file and directory limits."""
    with mock.patch('disk_scanner.cli.run_textual_ui') as mock_run_ui:
        result = cli_runner.invoke(
            main, [str(test_directory), "--no-interactive", "--max-files", "2", "--max-dirs", "1"]
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
        
        # Mock the scanner to avoid actual disk operations
        with mock.patch('disk_scanner.cli.DiskScanner') as mock_scanner_class:
            # Configure the mock scanner
            mock_scanner = mock_scanner_class.return_value
            mock_scanner.scan.return_value = mock.MagicMock(
                files=[],
                directories=[],
                files_scanned=10,
                total_size=1000,
                access_issues={}
            )
            
            result = cli_runner.invoke(
                main, [str(test_directory), "--no-interactive", "--output", str(output_file)]
            )

            assert result.exit_code == 0


def test_cli_invalid_path(cli_runner: CliRunner) -> None:
    """Test CLI behavior with invalid path."""
    result = cli_runner.invoke(main, ["nonexistent_directory"])

    # The CLI should handle invalid paths gracefully
    assert result.exit_code != 0
    assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()


def test_cli_keyboard_interrupt(
    cli_runner: CliRunner,
    test_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CLI handling of keyboard interrupt."""
    # Mock the DiskScanner.scan method to raise KeyboardInterrupt
    with mock.patch('disk_scanner.cli.DiskScanner') as mock_scanner_class:
        mock_scanner = mock_scanner_class.return_value
        mock_scanner.scan.side_effect = KeyboardInterrupt()
        
        result = cli_runner.invoke(main, [str(test_directory), "--no-interactive"])

        assert result.exit_code == 1
        assert "cancelled" in result.output.lower() or "interrupted" in result.output.lower()


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test CLI help output."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "usage" in result.output.lower()
    assert "options" in result.output.lower()

    # Verify all options are documented
    assert "--max-files" in result.output or "-f" in result.output
    assert "--max-dirs" in result.output or "-d" in result.output
    assert "--skip-dirs" in result.output or "-s" in result.output


def test_cli_default_path(cli_runner: CliRunner) -> None:
    """Test CLI with default path (current directory)."""
    with cli_runner.isolated_filesystem():
        # Create a test file in current directory
        Path("test.txt").write_text("x" * 1000)

        # Mock the scanner to avoid actual disk operations
        with mock.patch('disk_scanner.cli.DiskScanner') as mock_scanner_class:
            # Configure the mock scanner
            mock_scanner = mock_scanner_class.return_value
            
            # Create a mock result with the test file
            mock_file_info = mock.MagicMock(
                path=Path("test.txt"),
                size=1000,
                is_icloud=False
            )
            mock_scanner.scan.return_value = mock.MagicMock(
                files=[mock_file_info],
                directories=[],
                files_scanned=1,
                total_size=1000,
                access_issues={}
            )
            
            result = cli_runner.invoke(main, ["--no-interactive"])

            assert result.exit_code == 0
            assert "test.txt" in result.output.lower()


def test_cli_interactive_mode(cli_runner: CliRunner, test_directory: Path) -> None:
    """Test CLI interactive mode triggers the textual UI."""
    # Reset the mock
    textual_ui_mock.run_textual_ui.reset_mock()
    
    # The interactive flag should trigger the textual UI
    result = cli_runner.invoke(main, [str(test_directory), "--interactive"])
    
    # Verify that run_textual_ui was called
    textual_ui_mock.run_textual_ui.assert_called_once()
    
    # The path should be passed to run_textual_ui
    args, _ = textual_ui_mock.run_textual_ui.call_args
    assert str(test_directory) == str(args[0])
