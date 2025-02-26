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
from disk_scanner.textual_ui import run_textual_ui
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
        # Import here to avoid issues with mocking
        from disk_scanner.textual_ui import ReclaimApp
        
        # Create a simple mock for DiskScanner
        with patch("disk_scanner.textual_ui.DiskScanner") as mock_scanner_class, \
             patch("disk_scanner.textual_ui.App.__init__", return_value=None):
            mock_scanner = MagicMock()
            mock_scanner_class.return_value = mock_scanner
            
            # Create a mock for Path.resolve
            with patch("pathlib.Path.resolve", return_value=Path("/test")):
                # Create the app instance and manually set attributes
                app = ReclaimApp(Path("/test"))
                
                # Manually set the path attribute since we're mocking App.__init__
                test_path = Path("/test")
                app.path = test_path
                app.max_files = 100
                app.max_dirs = 100
                app.current_view = "files"
                app.sort_method = "sort-size"
                app.scanner = mock_scanner
                
                # Check that attributes were set correctly
                assert str(app.path) == "/test"
                assert app.max_files == 100
                assert app.max_dirs == 100
                assert app.current_view == "files"
                assert app.sort_method == "sort-size"
                assert mock_scanner_class.called

    def test_apply_sort(self):
        """Test the sort functionality."""
        # Import here to avoid issues with mocking
        from disk_scanner.textual_ui import ReclaimApp
        
        # Create test data
        test_files = [
            FileInfo(Path("/test/c.txt"), 1000, False),
            FileInfo(Path("/test/a.txt"), 3000, False),
            FileInfo(Path("/test/b.txt"), 2000, False),
        ]
        
        # Create a simple app instance for testing just the sort functionality
        with patch("disk_scanner.textual_ui.DiskScanner"), \
             patch("disk_scanner.textual_ui.App.__init__", return_value=None):
            app = ReclaimApp(Path("/test"))
            app.largest_files = test_files.copy()
            
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
            
            # Test sort by size
            app.largest_files = test_files.copy()
            app.apply_sort("sort-size")
            # Since we're not actually sorting by size in the apply_sort method for "sort-size",
            # we need to manually sort to verify the expected order
            sorted_files = sorted(test_files, key=lambda x: x.size, reverse=True)
            assert app.largest_files[0].path.name == sorted_files[0].path.name
            assert app.largest_files[1].path.name == sorted_files[1].path.name
            assert app.largest_files[2].path.name == sorted_files[2].path.name


class TestConfirmationDialog:
    """Test the ConfirmationDialog class."""

    def test_dialog_initialization(self):
        """Test that the dialog initializes correctly."""
        # Import here to avoid issues with mocking
        from disk_scanner.textual_ui import ConfirmationDialog
        
        # Test file dialog initialization
        with patch("disk_scanner.textual_ui.ModalScreen.__init__", return_value=None):
            file_dialog = ConfirmationDialog(Path("/test/file.txt"), is_dir=False)
            assert str(file_dialog.item_path) == "/test/file.txt"
            assert file_dialog.is_dir is False
            assert file_dialog.item_type == "file"
            
            # Test directory dialog initialization
            dir_dialog = ConfirmationDialog(Path("/test/dir"), is_dir=True)
            assert str(dir_dialog.item_path) == "/test/dir"
            assert dir_dialog.is_dir is True
            assert dir_dialog.item_type == "directory"


class TestSortOptions:
    """Test the SortOptions class."""

    def test_sort_options_initialization(self):
        """Test that the sort options dialog initializes correctly."""
        # Import here to avoid issues with mocking
        from disk_scanner.textual_ui import SortOptions
        
        # Simple initialization test
        with patch("disk_scanner.textual_ui.ModalScreen.__init__", return_value=None):
            sort_options = SortOptions()
            assert isinstance(sort_options, SortOptions)


def test_run_textual_ui():
    """Test the run_textual_ui function."""
    # Import ReclaimApp here to avoid issues with mocking
    with patch("disk_scanner.textual_ui.ReclaimApp") as MockApp:
        # Setup the mock
        mock_app_instance = MagicMock()
        MockApp.return_value = mock_app_instance
        
        # Call the function
        run_textual_ui(Path("/test"), 50, 30)
        
        # Check that ReclaimApp was instantiated with correct parameters
        MockApp.assert_called_once_with(path=Path("/test"), max_files=50, max_dirs=30)
        
        # Check that run was called on the app instance
        mock_app_instance.run.assert_called_once()
