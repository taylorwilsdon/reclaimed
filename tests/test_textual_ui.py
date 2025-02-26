"""Tests for the Textual UI functionality."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock the textual imports to avoid requiring the package for tests
sys.modules['textual'] = MagicMock()
sys.modules['textual.app'] = MagicMock()
sys.modules['textual.widgets'] = MagicMock()
sys.modules['textual.binding'] = MagicMock()
sys.modules['textual.containers'] = MagicMock()
sys.modules['textual.screen'] = MagicMock()
sys.modules['textual.on'] = MagicMock()
sys.modules['rich.text'] = MagicMock()

# Import after mocking
with patch.dict('sys.modules', {
    'textual': sys.modules['textual'],
    'textual.app': sys.modules['textual.app'],
    'textual.widgets': sys.modules['textual.widgets'],
    'textual.binding': sys.modules['textual.binding'],
    'textual.containers': sys.modules['textual.containers'],
    'textual.screen': sys.modules['textual.screen'],
    'textual.on': sys.modules['textual.on'],
    'rich.text': sys.modules['rich.text']
}):
    from disk_scanner.textual_ui import (
        ReclaimApp, 
        ConfirmationDialog, 
        SortOptions,
        run_textual_ui
    )

from disk_scanner.disk_scanner import FileInfo, DiskScanner


@pytest.fixture
def mock_file_info():
    """Create mock file info objects for testing."""
    return [
        FileInfo(Path("/test/file1.txt"), 1024, False),
        FileInfo(Path("/test/file2.txt"), 2048, True),
    ]


@pytest.fixture
def mock_dir_info():
    """Create mock directory info objects for testing."""
    return [
        FileInfo(Path("/test/dir1"), 4096, False),
        FileInfo(Path("/test/dir2"), 8192, True),
    ]


class TestReclaimApp:
    """Test the ReclaimApp class."""

    def test_app_initialization(self):
        """Test that the app initializes correctly."""
        with patch("disk_scanner.textual_ui.DiskScanner") as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_scanner_class.return_value = mock_scanner
        
            app = ReclaimApp(Path("/test"))
        
            assert app.path == Path("/test").resolve()
            assert app.max_files == 100
            assert app.max_dirs == 100
            assert app.current_view == "files"
            assert app.sort_method == "sort-size"
            assert mock_scanner_class.called

    def test_apply_sort(self):
        """Test the sort functionality."""
        app = ReclaimApp(Path("/test"))
    
        # Create test data
        app.largest_files = [
            FileInfo(Path("/test/c.txt"), 1000, False),
            FileInfo(Path("/test/a.txt"), 3000, False),
            FileInfo(Path("/test/b.txt"), 2000, False),
        ]
    
        # Test sort by name
        app.apply_sort("sort-name")
        assert app.largest_files[0].path.name == "a.txt"
        assert app.largest_files[1].path.name == "b.txt"
        assert app.largest_files[2].path.name == "c.txt"
    
        # Test sort by path
        app.apply_sort("sort-path")
        assert "a.txt" in str(app.largest_files[0].path)
        assert "b.txt" in str(app.largest_files[1].path)
        assert "c.txt" in str(app.largest_files[2].path)
    
        # Test sort by size (default)
        app.apply_sort("sort-size")
        # The original data is already sorted by size in reverse order
        assert app.largest_files[0].path.name == "a.txt"  # 3000
        assert app.largest_files[1].path.name == "b.txt"  # 2000
        assert app.largest_files[2].path.name == "c.txt"  # 1000


class TestConfirmationDialog:
    """Test the ConfirmationDialog class."""

    def test_dialog_initialization(self):
        """Test that the dialog initializes correctly."""
        # Test file dialog
        file_dialog = ConfirmationDialog(Path("/test/file.txt"), is_dir=False)
        assert file_dialog.item_path == Path("/test/file.txt")
        assert file_dialog.is_dir is False
        assert file_dialog.item_type == "file"
        
        # Test directory dialog
        dir_dialog = ConfirmationDialog(Path("/test/dir"), is_dir=True)
        assert dir_dialog.item_path == Path("/test/dir")
        assert dir_dialog.is_dir is True
        assert dir_dialog.item_type == "directory"


class TestSortOptions:
    """Test the SortOptions class."""

    def test_sort_options_initialization(self):
        """Test that the sort options dialog initializes correctly."""
        sort_options = SortOptions()
        assert sort_options is not None


@patch("disk_scanner.textual_ui.ReclaimApp.run")
def test_run_textual_ui(mock_run):
    """Test the run_textual_ui function."""
    run_textual_ui(Path("/test"), 50, 30)
    
    # Check that app.run() was called
    assert mock_run.called
    
    # Get the app instance that was created
    app_instance = mock_run.call_args[0][0]
    
    # Verify app was initialized with correct parameters
    assert app_instance.path == Path("/test").resolve()
    assert app_instance.max_files == 50
    assert app_instance.max_dirs == 30
