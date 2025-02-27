"""Tests for the CLI module."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from disk_scanner.cli import handle_scan_error, main
from disk_scanner.core.errors import (
    AccessError,
    DiskScannerError,
    InvalidPathError,
    ScanInterruptedError
)


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Create a mock Rich console."""
    with patch("disk_scanner.cli.Console") as mock_console_cls:
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        yield mock_console


class TestHandleScanError:
    """Tests for the handle_scan_error function."""

    def test_invalid_path_error(self, mock_console):
        """Test handling of InvalidPathError."""
        error = InvalidPathError(Path("/nonexistent"))
        exit_code = handle_scan_error(error, mock_console)
        
        mock_console.print.assert_called_once()
        assert "Invalid path" in mock_console.print.call_args[0][0]
        assert exit_code == 1

    def test_scan_interrupted_error(self, mock_console):
        """Test handling of ScanInterruptedError."""
        error = ScanInterruptedError("Interrupted")
        exit_code = handle_scan_error(error, mock_console)
        
        mock_console.print.assert_called_once()
        assert "Scan interrupted" in mock_console.print.call_args[0][0]
        assert exit_code == 0

    def test_access_error(self, mock_console):
        """Test handling of AccessError."""
        error = AccessError("Permission denied")
        exit_code = handle_scan_error(error, mock_console)
        
        mock_console.print.assert_called_once()
        assert "Access error" in mock_console.print.call_args[0][0]
        assert exit_code == 1

    def test_disk_scanner_error(self, mock_console):
        """Test handling of DiskScannerError."""
        error = DiskScannerError("Scanner error")
        exit_code = handle_scan_error(error, mock_console)
        
        mock_console.print.assert_called_once()
        assert "Scan error" in mock_console.print.call_args[0][0]
        assert exit_code == 1

    def test_unexpected_error(self, mock_console):
        """Test handling of unexpected errors."""
        error = ValueError("Unexpected error")
        exit_code = handle_scan_error(error, mock_console)
        
        mock_console.print.assert_called_once()
        assert "Unexpected error" in mock_console.print.call_args[0][0]
        assert exit_code == 2


class TestMainCLI:
    """Tests for the main CLI function."""

    @patch("disk_scanner.cli.run_textual_ui")
    def test_interactive_mode(self, mock_run_textual_ui, cli_runner):
        """Test running in interactive mode."""
        with cli_runner.isolated_filesystem():
            os.makedirs("test_dir")
            result = cli_runner.invoke(main, ["test_dir"])
            
            assert result.exit_code == 0
            mock_run_textual_ui.assert_called_once()

    @patch("disk_scanner.cli.DiskScanner")
    @patch("disk_scanner.cli.TableFormatter")
    def test_non_interactive_mode(self, mock_formatter_cls, mock_scanner_cls, cli_runner):
        """Test running in non-interactive mode."""
        mock_scanner = MagicMock()
        mock_scanner_cls.return_value = mock_scanner
        
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        
        with cli_runner.isolated_filesystem():
            os.makedirs("test_dir")
            result = cli_runner.invoke(main, ["test_dir", "--no-interactive"])
            
            assert result.exit_code == 0
            mock_scanner.scan.assert_called_once()
            mock_formatter.print_scan_summary.assert_called_once()

    @patch("disk_scanner.cli.DiskScanner")
    def test_with_custom_options(self, mock_scanner_cls, cli_runner):
        """Test CLI with custom options."""
        mock_scanner = MagicMock()
        mock_scanner_cls.return_value = mock_scanner
        
        with cli_runner.isolated_filesystem():
            os.makedirs("test_dir")
            result = cli_runner.invoke(
                main, 
                ["test_dir", "--no-interactive", "--max-files", "20", "--max-dirs", "15", "--skip-dirs", "node_modules"]
            )
            
            assert result.exit_code == 0
            # Verify options were passed correctly
            options = mock_scanner_cls.call_args[0][0]
            assert options.max_files == 20
            assert options.max_dirs == 15
            assert "node_modules" in options.skip_dirs

    @patch("disk_scanner.cli.logging")
    def test_debug_flag(self, mock_logging, cli_runner):
        """Test the debug flag sets appropriate log level."""
        with cli_runner.isolated_filesystem():
            os.makedirs("test_dir")
            with patch("disk_scanner.cli.run_textual_ui"):
                result = cli_runner.invoke(main, ["test_dir", "--debug"])
                
                assert result.exit_code == 0
                mock_logging.getLogger.return_value.setLevel.assert_called_with(mock_logging.DEBUG)

    @patch("disk_scanner.cli.DiskScanner")
    def test_error_handling(self, mock_scanner_cls, cli_runner):
        """Test error handling in the CLI."""
        mock_scanner = MagicMock()
        mock_scanner.scan.side_effect = AccessError("Permission denied")
        mock_scanner_cls.return_value = mock_scanner
        
        with cli_runner.isolated_filesystem():
            os.makedirs("test_dir")
            result = cli_runner.invoke(main, ["test_dir", "--no-interactive"])
            
            assert result.exit_code == 1
            assert "Access error" in result.output
