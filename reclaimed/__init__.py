"""Disk space analysis and optimization tool."""

from .version import __version__
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
