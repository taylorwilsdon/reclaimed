import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import json
from disk_scanner.cli import main

@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()

@pytest.fixture
def test_directory():
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

def test_cli_basic_scan(cli_runner, test_directory):
    """Test basic CLI scanning functionality."""
    result = cli_runner.invoke(main, [str(test_directory)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.output
    assert "Largest Files" in result.output
    assert "Largest Directories" in result.output
    
    # Verify all test files are mentioned in output
    assert "small.txt" in result.output
    assert "medium.txt" in result.output
    assert "large.txt" in result.output
    assert "subdir" in result.output

def test_cli_custom_limits(cli_runner, test_directory):
    """Test CLI with custom file and directory limits."""
    result = cli_runner.invoke(main, [
        str(test_directory),
        "--files", "2",
        "--dirs", "1"
    ])
    
    assert result.exit_code == 0
    
    # Count the number of file entries (excluding header)
    file_entries = len([line for line in result.output.split('\n') 
                       if '.txt' in line])
    assert file_entries <= 2

def test_cli_json_output(cli_runner, test_directory):
    """Test saving results to JSON file."""
    output_file = test_directory / "results.json"
    
    result = cli_runner.invoke(main, [
        str(test_directory),
        "--output", str(output_file)
    ])
    
    assert result.exit_code == 0
    assert output_file.exists()
    
    # Verify JSON structure
    with open(output_file) as f:
        data = json.load(f)
    
    assert "scan_info" in data
    assert "largest_files" in data
    assert "largest_directories" in data

def test_cli_invalid_path(cli_runner):
    """Test CLI behavior with invalid path."""
    result = cli_runner.invoke(main, ["nonexistent_directory"])
    
    assert result.exit_code == 1
    assert "Error" in result.output

def test_cli_keyboard_interrupt(cli_runner, test_directory, monkeypatch):
    """Test CLI handling of keyboard interrupt."""
    def mock_scan(*args, **kwargs):
        raise KeyboardInterrupt()
    
    # Patch the scan_directory method
    import disk_scanner.disk_scanner
    monkeypatch.setattr(disk_scanner.disk_scanner.DiskScanner, 
                       "scan_directory", 
                       mock_scan)
    
    result = cli_runner.invoke(main, [str(test_directory)])
    
    assert result.exit_code == 1
    assert "cancelled" in result.output.lower()

def test_cli_help(cli_runner):
    """Test CLI help output."""
    result = cli_runner.invoke(main, ["--help"])
    
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Options:" in result.output
    
    # Verify all options are documented
    assert "--files" in result.output
    assert "--dirs" in result.output
    assert "--output" in result.output

def test_cli_default_path(cli_runner):
    """Test CLI with default path (current directory)."""
    with cli_runner.isolated_filesystem():
        # Create a test file in current directory
        Path("test.txt").write_text("x" * 1000)
        
        result = cli_runner.invoke(main, [])
        
        assert result.exit_code == 0
        assert "test.txt" in result.output

def test_cli_rich_output_format(cli_runner, test_directory):
    """Test that Rich formatting is applied correctly."""
    result = cli_runner.invoke(main, [str(test_directory)])
    
    assert result.exit_code == 0
    
    # Check for Rich formatting characters
    assert "[bold]" in result.output
    assert "[/]" in result.output
    assert "│" in result.output  # Table border character
