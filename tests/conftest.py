import tempfile
from pathlib import Path

import pytest

from reclaimed.metrics.buffer import MetricsBuffer
from reclaimed.metrics.collector import MetricsCollector


@pytest.fixture
def temp_dir():
    """Provide a clean temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file_structure(temp_dir):
    """Create a sample file structure for testing."""
    # Create directories
    dir1 = temp_dir / "dir1"
    dir2 = temp_dir / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Create sample files with known sizes
    (dir1 / "file1.txt").write_text("Hello" * 100)  # 500 bytes
    (dir1 / "file2.txt").write_text("World" * 200)  # 1000 bytes
    (dir2 / "file3.txt").write_text("Test" * 300)  # 1200 bytes

    return temp_dir


@pytest.fixture
def metrics_buffer():
    """Provide a clean metrics buffer for testing."""
    return MetricsBuffer()


@pytest.fixture
def metrics_collector():
    """Provide a metrics collector instance for testing."""
    return MetricsCollector()


@pytest.fixture
def mock_filesystem(temp_dir):
    """Create a controlled filesystem environment for testing."""
    # Create a more complex directory structure
    structure = {
        "project": {
            "src": {
                "main.py": "print('hello')",
                "utils": {
                    "helper.py": "def help(): pass",
                },
            },
            "tests": {"test_main.py": "def test_main(): pass"},
            "data": {"sample.txt": "sample data"},
        }
    }

    def create_structure(base_path, struct):
        for name, content in struct.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir(exist_ok=True)
                create_structure(path, content)
            else:
                path.write_text(content)

    root = temp_dir / "mock_fs"
    root.mkdir()
    create_structure(root, structure)
    return root
