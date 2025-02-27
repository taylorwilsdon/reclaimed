"""Core disk scanning functionality."""

from .scanner import DiskScanner
from .types import FileInfo, ScanOptions, ScanProgress, ScanResult
from .errors import (
    AccessError,
    DiskScannerError,
    InvalidPathError,
    PermissionError,
    ScanInterruptedError,
)

__all__ = [
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
]