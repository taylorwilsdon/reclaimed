"""Disk space analysis and optimization tool."""

from .core import (
    AccessError,
    DiskScanner,
    DiskScannerError,
    FileInfo,
    InvalidPathError,
    PermissionError,
    ScanInterruptedError,
    ScanOptions,
    ScanProgress,
    ScanResult,
)
from .io import FileSystemOperations
from .utils.formatters import format_size, parse_size
from .version import __version__

__all__ = [
    "__version__",
    "DiskScanner",
    "FileInfo",
    "ScanOptions",
    "ScanProgress",
    "ScanResult",
    "AccessError",
    "DiskScannerError",
    "InvalidPathError",
    "PermissionError",
    "ScanInterruptedError",
    "format_size",
    "parse_size",
    "FileSystemOperations",
]
