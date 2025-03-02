"""Custom error types for the disk scanner."""

from pathlib import Path
from typing import Optional


class DiskScannerError(Exception):
    """Base class for disk scanner errors."""

    pass


class AccessError(DiskScannerError):
    """Error when accessing a file or directory."""

    def __init__(self, path: Path, message: str, original_error: Optional[Exception] = None):
        self.path = path
        self.original_error = original_error
        super().__init__(f"{message}: {path}")


class PermissionError(AccessError):
    """Error when permission is denied."""

    def __init__(self, path: Path, original_error: Optional[Exception] = None):
        super().__init__(path, "Permission denied", original_error)


class FileNotFoundError(AccessError):
    """Error when a file or directory is not found."""

    def __init__(self, path: Path, original_error: Optional[Exception] = None):
        super().__init__(path, "File not found", original_error)


class IOError(AccessError):
    """Error during file I/O operations."""

    def __init__(self, path: Path, message: str, original_error: Optional[Exception] = None):
        super().__init__(path, f"IO Error: {message}", original_error)


class ScanInterruptedError(DiskScannerError):
    """Error when scanning is interrupted."""

    def __init__(self, message: str = "Scan interrupted by user"):
        super().__init__(message)


class InvalidPathError(DiskScannerError):
    """Error when an invalid path is provided."""

    def __init__(self, path: Path, message: str = "Invalid path"):
        self.path = path
        super().__init__(f"{message}: {path}")
