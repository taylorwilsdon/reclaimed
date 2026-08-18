import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from reclaimed.core.errors import InvalidPathError, ScanInterruptedError
from reclaimed.core.scanner import DiskScanner
from reclaimed.core.types import FileInfo, ScanOptions, ScanResult


def test_scanner_initialization():
    """Test scanner initialization with default and custom options."""
    # Test with default options
    scanner = DiskScanner()
    assert scanner.options is not None

    # Test with custom options
    custom_options = ScanOptions(max_files=5, max_dirs=3)
    scanner = DiskScanner(options=custom_options)
    assert scanner.options.max_files == 5
    assert scanner.options.max_dirs == 3


def test_invalid_path(temp_dir):
    """Test scanning an invalid path raises appropriate error."""
    scanner = DiskScanner()
    invalid_path = temp_dir / "nonexistent"

    with pytest.raises(InvalidPathError):
        scanner.scan(invalid_path)


def test_basic_scan(sample_file_structure):
    """Test basic scanning functionality with known file structure."""
    scanner = DiskScanner()
    result = scanner.scan(sample_file_structure)

    assert isinstance(result, ScanResult)
    assert result.total_size > 0
    assert result.files_scanned == 3  # We created 3 files in sample_file_structure
    assert len(result.files) > 0
    assert len(result.directories) > 0

    # Verify files are sorted by size (largest first)
    for i in range(len(result.files) - 1):
        assert result.files[i].size >= result.files[i + 1].size


def test_directory_size_calculation(sample_file_structure):
    """Test that directory sizes are calculated correctly."""
    scanner = DiskScanner()
    result = scanner.scan(sample_file_structure)

    # Find dir1 in results
    dir1 = next(d for d in result.directories if d.path.name == "dir1")
    assert dir1.size == 1500  # 500 + 1000 bytes from our sample files


def test_max_files_limit(tmp_path):
    """Test that max_files limit is respected."""
    scanner = DiskScanner(options=ScanOptions(max_files=2))

    # Create more files than the limit
    for i in range(5):
        (tmp_path / f"file{i}.txt").write_text("x" * (1000 + i))

    result = scanner.scan(tmp_path)
    assert len(result.files) == 2
    # Verify we kept the largest files
    assert result.files[0].size > result.files[1].size


def test_scan_async_yields_progress(sample_file_structure):
    """scan_async drives a real event loop and ends with an exact snapshot."""

    async def collect():
        return [p async for p in DiskScanner().scan_async(sample_file_structure)]

    updates = asyncio.run(collect())

    assert updates, "scan_async yielded nothing"
    final = updates[-1]
    assert final.progress == 1.0
    assert final.scanned == 3
    assert final.total_size == 2700
    assert len(final.files) == 3


def test_access_issues(mock_filesystem):
    """Test handling of access issues."""
    scanner = DiskScanner()

    # Create a directory with restricted permissions
    restricted_dir = mock_filesystem / "restricted"
    restricted_dir.mkdir()
    restricted_file = restricted_dir / "secret.txt"
    restricted_file.write_text("secret data")
    restricted_dir.chmod(0o000)  # Remove all permissions

    try:
        result = scanner.scan(mock_filesystem)

        # Verify access issues were recorded
        assert len(result.access_issues) > 0
        assert any(str(restricted_dir) in str(path) for path in result.access_issues.keys())
    finally:
        # Restore permissions so the directory can be cleaned up
        restricted_dir.chmod(0o755)


def test_icloud_detection(tmp_path):
    """Test iCloud file detection."""
    scanner = DiskScanner(options=ScanOptions(icloud_base=tmp_path / "Library/Mobile Documents"))

    # Create mock iCloud path
    icloud_path = tmp_path / "Library/Mobile Documents/test.txt"
    icloud_path.parent.mkdir(parents=True)
    icloud_path.write_text("icloud test")

    result = scanner.scan(tmp_path)

    # Verify iCloud file was detected
    icloud_files = [f for f in result.files if f.is_icloud]
    assert len(icloud_files) > 0
    assert str(icloud_files[0].path).endswith("test.txt")


def test_skip_dirs(mock_filesystem):
    """Test directory skipping functionality."""
    scanner = DiskScanner(options=ScanOptions(skip_dirs={"tests"}))
    result = scanner.scan(mock_filesystem)

    # Verify 'tests' directory was skipped
    test_files = [f for f in result.files if "tests" in str(f.path)]
    assert len(test_files) == 0


def test_scan_interruption(mock_filesystem, monkeypatch):
    """Test handling of scan interruption."""

    def raise_keyboard_interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    # Patch os.scandir to raise KeyboardInterrupt
    monkeypatch.setattr("os.scandir", raise_keyboard_interrupt)

    scanner = DiskScanner()
    with pytest.raises(ScanInterruptedError):
        scanner.scan(mock_filesystem)


def test_top_n_files_selection(tmp_path):
    """Only the largest files survive, in descending order."""
    for i in range(20):
        (tmp_path / f"f{i}.bin").write_bytes(b"x" * (1000 + i * 10))

    result = DiskScanner(ScanOptions(max_files=5)).scan(tmp_path)

    assert [f.size for f in result.files] == [1190, 1180, 1170, 1160, 1150]


def test_files_with_equal_sizes_do_not_break_ordering(tmp_path):
    """Equal sizes are resolved deterministically without comparing Path objects."""
    for name in ("a.bin", "b.bin", "c.bin"):
        (tmp_path / name).write_bytes(b"x" * 500)

    result = DiskScanner(ScanOptions(max_files=2)).scan(tmp_path)

    assert [file_info.path.name for file_info in result.files] == ["a.bin", "b.bin"]


def test_directory_results_bounded_by_scan_root(sample_file_structure):
    """No ancestor of the scan root may appear in the directory results.

    Regression test for the bug where every parent up to '/' accumulated the
    full scan total and crowded the real directories out of the table.
    """
    root = sample_file_structure
    result = DiskScanner().scan(root)

    paths = {d.path for d in result.directories}
    assert Path("/") not in paths
    assert root.parent not in paths
    assert all(p == root or root in p.parents for p in paths)

    # The root's rolled-up size is the whole scan.
    root_entry = next(d for d in result.directories if d.path == root)
    assert root_entry.size == result.total_size


def test_deep_tree_rollup(tmp_path):
    """Subtree totals remain exact in a deeply nested tree."""
    current = tmp_path
    for name in ("a", "b", "c", "d", "e"):
        current = current / name
        current.mkdir()
        (current / "f.bin").write_bytes(b"x" * 100)

    result = DiskScanner(ScanOptions(max_dirs=10)).scan(tmp_path)
    sizes = {d.path.name: d.size for d in result.directories}

    assert sizes["a"] == 500  # five files of 100 bytes below it
    assert sizes["e"] == 100  # the deepest holds only its own
    assert result.total_size == 500


def test_sync_and_async_agree(sample_file_structure):
    """The two entry points share one implementation, so they must not diverge."""
    sync_result = DiskScanner().scan(sample_file_structure)

    async def collect():
        return [p async for p in DiskScanner().scan_async(sample_file_structure)]

    updates = asyncio.run(collect())
    final = updates[-1]

    assert final.progress == 1.0
    assert final.scanned == sync_result.files_scanned
    assert final.total_size == sync_result.total_size
    assert [f.path for f in final.files] == [f.path for f in sync_result.files]
    assert [d.path for d in final.dirs] == [d.path for d in sync_result.directories]


def test_threaded_matches_serial(mock_filesystem):
    """Worker count must not change results."""
    serial = DiskScanner(ScanOptions(max_workers=1)).scan(mock_filesystem)
    threaded = DiskScanner(ScanOptions(max_workers=4)).scan(mock_filesystem)

    assert serial.total_size == threaded.total_size
    assert serial.files_scanned == threaded.files_scanned
    assert [f.path for f in serial.files] == [f.path for f in threaded.files]
    assert [d.path for d in serial.directories] == [d.path for d in threaded.directories]


def test_symlinks_are_not_followed(tmp_path):
    """Symlinked files and directories contribute nothing to the total."""
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "data.bin").write_bytes(b"x" * 400)

    (tmp_path / "link_to_dir").symlink_to(real_dir, target_is_directory=True)
    (tmp_path / "link_to_file").symlink_to(real_dir / "data.bin")

    result = DiskScanner().scan(tmp_path)

    assert result.total_size == 400
    assert result.files_scanned == 1


def test_partial_results_on_interrupt(mock_filesystem, monkeypatch):
    """An interrupted scan carries what it managed to collect."""
    real_scandir = os.scandir
    calls = {"n": 0}

    def flaky_scandir(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > 2:
            raise KeyboardInterrupt()
        return real_scandir(*args, **kwargs)

    monkeypatch.setattr("os.scandir", flaky_scandir)

    scanner = DiskScanner(options=ScanOptions(max_workers=1))
    with pytest.raises(ScanInterruptedError) as exc_info:
        scanner.scan(mock_filesystem)

    partial = exc_info.value.partial
    assert partial is not None
    assert partial is scanner.last_partial_result
    assert isinstance(partial, ScanResult)


def test_save_results(tmp_path):
    """Test the save_results method."""
    scanner = DiskScanner()

    # Create test data
    files = [
        FileInfo(Path("/test/file1.txt"), 1000, 1234567890.0, False),
        FileInfo(Path("/test/file2.txt"), 2000, 1234567891.0, True)
    ]

    dirs = [
        FileInfo(Path("/test/dir1"), 3000, 1234567892.0, False),
        FileInfo(Path("/test/dir2"), 4000, 1234567893.0, True)
    ]

    # Set up scanner internal state
    scanner._total_size = 10000
    scanner._file_count = 5
    scanner._access_issues = {Path("/test/error"): "Permission denied"}

    # Create output path
    output_path = tmp_path / "results.json"

    # Mock console to avoid actual printing
    scanner.console = MagicMock()

    # Save results
    scanner.save_results(output_path, files, dirs, Path("/test"))

    # Verify file was created
    assert output_path.exists()

    # Load and verify contents
    with open(output_path, "r") as f:
        results = json.load(f)

    # Check structure
    assert "scan_info" in results
    assert "largest_files" in results
    assert "largest_directories" in results
    assert "access_issues" in results

    # Check content
    assert results["scan_info"]["total_size_bytes"] == 10000
    assert results["scan_info"]["files_scanned"] == 5
    assert len(results["largest_files"]) == 2
    assert len(results["largest_directories"]) == 2
    assert len(results["access_issues"]) == 1

    # Check file details
    assert results["largest_files"][0]["size_bytes"] == 1000
    assert results["largest_files"][1]["size_bytes"] == 2000
    assert results["largest_files"][1]["storage_type"] == "icloud"

    # Check directory details
    assert results["largest_directories"][0]["size_bytes"] == 3000
    assert results["largest_directories"][1]["size_bytes"] == 4000
    assert results["largest_directories"][1]["storage_type"] == "icloud"


def test_scan_async_exists():
    """Test that the scan_async method exists."""
    scanner = DiskScanner()
    # Just verify the method exists
    assert hasattr(scanner, 'scan_async')
    assert callable(scanner.scan_async)
