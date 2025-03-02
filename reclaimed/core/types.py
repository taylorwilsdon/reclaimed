"""Type definitions for the disk scanner."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional


class FileInfo(NamedTuple):
    """Store file information in an immutable structure."""

    path: Path
    size: int
    is_icloud: bool = False


@dataclass
class ScanProgress:
    """Progress information during scanning."""

    progress: float  # 0.0 to 1.0
    files: List[FileInfo]
    dirs: List[FileInfo]
    scanned: int  # Number of files scanned
    total_size: int  # Total size in bytes


@dataclass
class ScanResult:
    """Final results of a directory scan."""

    files: List[FileInfo]
    directories: List[FileInfo]
    total_size: int
    files_scanned: int
    access_issues: Dict[Path, str]


@dataclass
class ScanOptions:
    """Configuration options for directory scanning."""

    max_files: int = 10
    max_dirs: int = 10
    skip_dirs: List[str] = None  # Directories to skip
    icloud_base: Optional[Path] = None  # Base path for iCloud detection

    def __post_init__(self):
        """Set default values after initialization."""
        if self.skip_dirs is None:
            self.skip_dirs = [".Trash", "System Volume Information"]
