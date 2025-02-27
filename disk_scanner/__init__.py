"""Disk space analysis and optimization tool."""

from ._version import __version__
from .core import (
    DiskScanner,
    FileInfo,
    ScanOptions,
    ScanProgress,
    ScanResult,
    AccessError,
    DiskScannerError,
    InvalidPathError,
    PermissionError,
    ScanInterruptedError,
)
from .formatters import format_size, parse_size
from .io import FileSystemOperations

__all__ = [
    '__version__',
    'DiskScanner',
    'FileInfo',
    'ScanOptions',
    'ScanProgress',
    'ScanResult',
    'AccessError',
    'DiskScannerError',
    'InvalidPathError',
    'PermissionError',
    'ScanInterruptedError',
    'format_size',
    'parse_size',
    'FileSystemOperations',
]
