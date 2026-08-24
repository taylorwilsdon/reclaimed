"""Type definitions for the disk scanner."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

#: Directories skipped by default. Single source of truth: the CLI and the
#: Textual UI both defer to ScanOptions rather than repeating this list.
DEFAULT_SKIP_DIRS: Tuple[str, ...] = (".Trash", "System Volume Information")


class FileInfo(NamedTuple):
    """Store file information in an immutable structure."""

    path: Path
    size: int
    last_modified: float  # Timestamp (seconds since epoch)
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
    skip_dirs: Optional[List[str]] = None  # Additional directories to skip
    icloud_base: Optional[Path] = None  # Base path for iCloud detection
    max_workers: Optional[int] = None  # None -> min(4, cpu_count()); 1 disables the pool

    def __post_init__(self) -> None:
        """Set default values after initialization."""
        additional = [] if self.skip_dirs is None else list(self.skip_dirs)
        self.skip_dirs = list(dict.fromkeys(DEFAULT_SKIP_DIRS + tuple(additional)))
        self.max_files = max(0, self.max_files)
        self.max_dirs = max(0, self.max_dirs)
