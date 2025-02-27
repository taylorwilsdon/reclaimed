"""Tests for the DiskScanner module."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.table import Table

from disk_scanner.disk_scanner import DiskScanner, FileInfo


@pytest.fixture
def mock_console():
    """Create a mock Rich console."""
    return MagicMock(spec=Console)


@pytest.fixture
def scanner(mock_console):
    """Create a DiskScanner instance with a mock console."""
    return DiskScanner(console=mock_console)


@pytest.fixture
def temp_dir():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple directory structure
        base_path = Path(temp_dir)
        
        # Create some directories
        dir1 = base_path / "dir1"
        dir2 = base_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        # Create some files with known sizes
        (dir1 / "file1.txt").write_bytes(b"a" * 1000)  # 1KB
        (dir1 / "file2.txt").write_bytes(b"b" * 2000)  # 2KB
        (dir2 / "file3.txt").write_bytes(b"c" * 3000)  # 3KB
        
        yield base_path


class TestDiskScanner:
    """Tests for the DiskScanner class."""

    def test_init(self):
        """Test initialization of DiskScanner."""
        console = MagicMock()
        scanner = DiskScanner(console=console)
        
        assert scanner.console == console
        assert scanner._file_data == {}
        assert scanner._access_issues == {}
        assert scanner._total_size == 0
        assert scanner._file_count == 0

    def test_format_size(self, scanner):
        """Test the format_size method."""
        assert scanner.format_size(0) == "0.0 B"
        assert scanner.format_size(1023) == "1023.0 B"
        assert scanner.format_size(1024) == "1.0 KB"
        assert scanner.format_size(1024 * 1024) == "1.0 MB"
        assert scanner.format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert scanner.format_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"
        assert scanner.format_size(1024 * 1024 * 1024 * 1024 * 1024) == "1.0 PB"

    @patch("disk_scanner.disk_scanner.Path.iterdir")
    @patch("disk_scanner.disk_scanner.Path.is_dir")
    @patch("disk_scanner.disk_scanner.Path.is_symlink")
    @patch("disk_scanner.disk_scanner.Path.is_file")
    @patch("disk_scanner.disk_scanner.Path.stat")
    def test_walk_directory(self, mock_stat, mock_is_file, mock_is_symlink, 
                           mock_is_dir, mock_iterdir, scanner):
        """Test the _walk_directory method."""
        # Setup mocks
        mock_path = MagicMock()
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_dir = MagicMock()
        
        mock_iterdir.side_effect = [
            [mock_file1, mock_dir, mock_file2],  # First level
            [MagicMock()]  # Inside mock_dir
        ]
        
        mock_is_dir.side_effect = [False, True, False, True]
        mock_is_symlink.side_effect = [False, False, False, False]
        mock_is_file.side_effect = [True, False, True, True]
        
        # Execute
        result = list(scanner._walk_directory(mock_path))
        
        # Verify
        assert len(result) == 4  # All items including the one in subdirectory
        assert mock_iterdir.call_count == 2

    @patch("disk_scanner.disk_scanner.Path.iterdir")
    def test_walk_directory_permission_error(self, mock_iterdir, scanner):
        """Test handling of permission errors in _walk_directory."""
        mock_path = MagicMock()
        mock_iterdir.side_effect = PermissionError("Permission denied")
        
        # Execute
        list(scanner._walk_directory(mock_path))
        
        # Verify
        assert mock_path in scanner._access_issues
        assert "Permission denied" in scanner._access_issues[mock_path]

    @patch("disk_scanner.disk_scanner.Path.iterdir")
    def test_walk_directory_os_error(self, mock_iterdir, scanner):
        """Test handling of OS errors in _walk_directory."""
        mock_path = MagicMock()
        mock_iterdir.side_effect = OSError("Some OS error")
        
        # Execute
        list(scanner._walk_directory(mock_path))
        
        # Verify
        assert mock_path in scanner._access_issues
        assert "OSError" in scanner._access_issues[mock_path]

    def test_calculate_dir_sizes(self, scanner):
        """Test the _calculate_dir_sizes method."""
        # Setup test data
        root = Path("/test")
        file1 = root / "dir1" / "file1.txt"
        file2 = root / "dir1" / "file2.txt"
        file3 = root / "dir2" / "file3.txt"
        
        scanner._file_data = {
            file1: (1000, False),
            file2: (2000, False),
            file3: (3000, True),
        }
        
        # Execute
        result = scanner._calculate_dir_sizes(root)
        
        # Verify
        assert len(result) == 3  # root, dir1, dir2
        
        # Find each directory in results
        dir_dict = {str(item.path): item for item in result}
        
        assert str(root) in dir_dict
        assert str(root / "dir1") in dir_dict
        assert str(root / "dir2") in dir_dict
        
        # Check sizes
        assert dir_dict[str(root)].size == 6000  # Total of all files
        assert dir_dict[str(root / "dir1")].size == 3000  # file1 + file2
        assert dir_dict[str(root / "dir2")].size == 3000  # file3
        
        # Check iCloud flags
        assert dir_dict[str(root)].is_icloud  # Should be True because dir2 has iCloud files
        assert not dir_dict[str(root / "dir1")].is_icloud  # No iCloud files
        assert dir_dict[str(root / "dir2")].is_icloud  # Has iCloud files

    def test_save_results(self, scanner, temp_dir):
        """Test the save_results method."""
        # Setup test data
        output_path = temp_dir / "results.json"
        files = [
            FileInfo(temp_dir / "file1.txt", 1000, False),
            FileInfo(temp_dir / "file2.txt", 2000, True),
        ]
        dirs = [
            FileInfo(temp_dir / "dir1", 3000, False),
            FileInfo(temp_dir / "dir2", 4000, True),
        ]
        
        scanner._total_size = 6000
        scanner._file_count = 2
        
        # Execute
        scanner.save_results(output_path, files, dirs, temp_dir)
        
        # Verify
        assert output_path.exists()
        
        # Load and check JSON content
        with open(output_path, "r") as f:
            data = json.load(f)
        
        assert data["scan_info"]["total_size_bytes"] == 6000
        assert data["scan_info"]["files_scanned"] == 2
        assert len(data["largest_files"]) == 2
        assert len(data["largest_directories"]) == 2
        
        # Check file entries
        assert any(f["path"].endswith("file1.txt") for f in data["largest_files"])
        assert any(f["path"].endswith("file2.txt") for f in data["largest_files"])
        
        # Check directory entries
        assert any(d["path"].endswith("dir1") for d in data["largest_directories"])
        assert any(d["path"].endswith("dir2") for d in data["largest_directories"])

    def test_print_access_issues_summary(self, scanner):
        """Test the _print_access_issues_summary method."""
        # Setup test data
        scanner._access_issues = {
            Path("/test/dir1"): "Permission denied",
            Path("/test/dir2"): "Permission denied",
            Path("/test/file1.txt"): "OSError: Some error",
        }
        
        # Execute
        scanner._print_access_issues_summary()
        
        # Verify
        assert scanner.console.print.call_count >= 2  # At least called for table and newline

    @patch("disk_scanner.disk_scanner.DiskScanner._walk_directory")
    @patch("disk_scanner.disk_scanner.Path.stat")
    @patch("disk_scanner.disk_scanner.Path.is_file")
    @patch("disk_scanner.disk_scanner.Progress")
    def test_scan_directory_async(self, mock_progress_cls, mock_is_file, 
                                 mock_stat, mock_walk_directory, scanner):
        """Test the scan_directory_async method."""
        # Setup mocks
        mock_progress = MagicMock()
        mock_progress_cls.return_value.__enter__.return_value = mock_progress
        
        mock_path1 = MagicMock()
        mock_path2 = MagicMock()
        mock_path3 = MagicMock()
        
        mock_walk_directory.return_value = [mock_path1, mock_path2, mock_path3]
        mock_is_file.side_effect = [True, True, False]
        
        mock_stat_result1 = MagicMock()
        mock_stat_result1.st_size = 1000
        mock_stat_result2 = MagicMock()
        mock_stat_result2.st_size = 2000
        
        mock_stat.side_effect = [mock_stat_result1, mock_stat_result2]
        
        # Execute
        import asyncio
        result = asyncio.run(scanner.scan_directory_async(Path("/test")))
        
        # Verify
        assert scanner._total_size == 3000  # 1000 + 2000
        assert scanner._file_count == 2
        assert mock_progress.update.call_count > 0

    def test_integration_with_real_files(self, scanner, temp_dir):
        """Integration test with real files."""
        # Execute
        import asyncio
        files, dirs = asyncio.run(scanner.scan_directory_async(temp_dir))
        
        # Verify
        assert len(files) == 3  # We created 3 files
        assert len(dirs) == 3  # root + 2 subdirs
        
        # Check file sizes
        file_sizes = {os.path.basename(f.path): f.size for f in files}
        assert file_sizes["file1.txt"] == 1000
        assert file_sizes["file2.txt"] == 2000
        assert file_sizes["file3.txt"] == 3000
        
        # Check directory sizes
        dir_dict = {os.path.basename(d.path) if d.path != temp_dir else "root": d.size for d in dirs}
        assert dir_dict["root"] == 6000  # Total of all files
        assert dir_dict["dir1"] == 3000  # file1 + file2
        assert dir_dict["dir2"] == 3000  # file3
