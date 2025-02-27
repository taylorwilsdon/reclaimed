import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator, Iterator, List

import pytest
from rich.console import Console

from disk_scanner.disk_scanner import DiskScanner, FileInfo


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory with known file structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a predictable directory structure
        root = Path(tmpdir)

        # Create some regular files
        (root / "file1.txt").write_text("x" * 1000)  # 1KB file
        (root / "file2.txt").write_text("x" * 2000)  # 2KB file

        # Create a subdirectory with files
        subdir = root / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("x" * 3000)  # 3KB file

        # Create a mock iCloud directory structure (full path)
        icloud_base = root / "Library" / "Mobile Documents"
        icloud_base.mkdir(parents=True)
        icloud_file = icloud_base / "com~apple~CloudDocs" / "cloud_file.txt"
        icloud_file.parent.mkdir(parents=True)
        icloud_file.write_text("x" * 4000)  # 4KB file

        yield root


@pytest.fixture
def scanner(temp_directory: Path) -> DiskScanner:
    """Create a DiskScanner instance with a test console."""
    # Initialize scanner with the test directory's iCloud base
    icloud_base = temp_directory / "Library" / "Mobile Documents"
    return DiskScanner(Console(force_terminal=True), icloud_base=icloud_base)


def test_scan_directory_basic(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test basic directory scanning functionality."""
    # Call scan_directory method which should populate the internal file and dir lists
    scanner._calculate_dir_sizes(temp_directory)
    
    # Access the internal file and directory lists
    files = scanner._files
    dirs = scanner._dirs

    # Verify files are found and sorted by size
    assert len(files) > 0
    assert all(isinstance(f, FileInfo) for f in files)
    assert all(f.size > 0 for f in files)
    assert all(files[i].size >= files[i + 1].size for i in range(len(files) - 1))

    # Verify directories are found and sorted by size
    assert len(dirs) > 0
    assert all(isinstance(d, FileInfo) for d in dirs)
    assert all(d.size > 0 for d in dirs)
    assert all(dirs[i].size >= dirs[i + 1].size for i in range(len(dirs) - 1))


def test_icloud_detection(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test detection of iCloud vs local files."""
    # Call scan_directory method which should populate the internal file list
    scanner._calculate_dir_sizes(temp_directory)
    
    # Access the internal file list
    files = scanner._files

    icloud_files = [f for f in files if f.is_icloud]
    local_files = [f for f in files if not f.is_icloud]

    # Verify we can detect both iCloud and local files
    assert len(icloud_files) > 0, "No iCloud files found"
    assert len(local_files) > 0, "No local files found"
    assert any("Mobile Documents" in str(f.path) for f in icloud_files)
    assert any("Mobile Documents" not in str(f.path) for f in local_files)


def test_format_size() -> None:
    """Test human-readable size formatting."""
    scanner = DiskScanner()

    assert scanner.format_size(0) == "0.0 B"
    assert scanner.format_size(1024) == "1.0 KB"
    assert scanner.format_size(1024 * 1024) == "1.0 MB"
    assert scanner.format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_access_issues(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test handling of permission errors."""
    restricted_dir = temp_directory / "restricted"
    restricted_dir.mkdir()
    restricted_file = restricted_dir / "secret.txt"
    restricted_file.write_text("secret")

    # Make directory inaccessible
    os.chmod(restricted_dir, 0o000)

    try:
        # Call scan_directory method which should populate the internal lists
        scanner._calculate_dir_sizes(temp_directory)
        
        # Access the internal file and directory lists
        files = scanner._files
        dirs = scanner._dirs

        # Verify the scan completed despite access issues
        assert len(files) > 0
        assert len(dirs) > 0

        # Verify access issues were recorded
        assert restricted_dir in scanner._access_issues
        assert "Permission denied" in scanner._access_issues[restricted_dir]
    finally:
        # Restore permissions so cleanup can occur
        os.chmod(restricted_dir, 0o755)


def test_save_results(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test saving scan results to JSON."""
    output_file = temp_directory / "results.json"

    # Perform scan
    scanner._calculate_dir_sizes(temp_directory)
    
    # Access the internal file and directory lists
    files = scanner._files
    dirs = scanner._dirs

    # Save results
    scanner.save_results(output_file, files, dirs, temp_directory)

    # Verify JSON file was created and contains expected structure
    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)

    assert "scan_info" in data
    assert "largest_files" in data
    assert "largest_directories" in data
    assert "access_issues" in data

    # Verify scan info
    assert data["scan_info"]["scanned_path"] == str(temp_directory.absolute())
    assert isinstance(data["scan_info"]["total_size_bytes"], int)
    assert isinstance(data["scan_info"]["files_scanned"], int)


def test_keyboard_interrupt_handling(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test graceful handling of keyboard interrupts."""

    # Mock the _walk_directory method to raise KeyboardInterrupt
    def mock_walk(*args: Any) -> Iterator[Path]:
        raise KeyboardInterrupt()

    scanner._walk_directory = mock_walk  # type: ignore

    # Verify scan completes gracefully with empty results
    scanner._calculate_dir_sizes(temp_directory)
    
    # Access the internal file and directory lists
    files = scanner._files
    dirs = scanner._dirs
    
    assert len(files) == 0
    assert len(dirs) == 0


def test_max_results_limit(scanner: DiskScanner, temp_directory: Path) -> None:
    """Test respecting max_files and max_dirs limits."""
    max_files = 2
    max_dirs = 1

    # Call the method with max limits
    scanner._calculate_dir_sizes(temp_directory, max_files=max_files, max_dirs=max_dirs)
    
    # Access the internal file and directory lists
    files = scanner._files
    dirs = scanner._dirs

    # Verify the limits were respected
    assert len(files) <= max_files
    assert len(dirs) <= max_dirs
