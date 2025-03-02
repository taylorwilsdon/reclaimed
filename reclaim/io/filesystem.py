"""Optimized file system operations for disk scanning."""

import os
import stat
from pathlib import Path
from typing import Iterator, Optional, Tuple

from ..core.errors import (
    AccessError,
    FileNotFoundError,
    InvalidPathError,
    IOError,
    PermissionError,
)


class FileSystemOperations:
    """High-performance file system operations with proper error handling."""

    # Cache for symlink checks to avoid repeated calls
    _symlink_cache = {}
    # Maximum size of symlink cache to prevent memory leaks
    _MAX_SYMLINK_CACHE_SIZE = 10000

    @staticmethod
    def get_file_size(path: Path) -> int:
        """Get size of a file with proper error handling.

        Args:
            path: Path to file

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be accessed
            IOError: For other IO errors
        """
        try:
            # Use os.stat directly for better performance
            return os.stat(path).st_size
        except FileNotFoundError as e:
            raise FileNotFoundError(path, e) from e
        except PermissionError as e:
            raise PermissionError(path, e) from e
        except OSError as e:
            raise IOError(path, str(e), e) from e

    @staticmethod
    def is_readable(path: Path) -> bool:
        """Check if a path is readable.

        Args:
            path: Path to check

        Returns:
            True if path is readable
        """
        try:
            # Use os.access for better performance
            return os.access(path, os.R_OK)
        except (OSError, AttributeError):
            return False

    @staticmethod
    def is_directory_accessible(path: Path) -> bool:
        """Check if a directory is accessible.

        Args:
            path: Directory to check

        Returns:
            True if directory can be accessed
        """
        try:
            # Use os.access for better performance
            return os.access(path, os.R_OK | os.X_OK)
        except (OSError, AttributeError):
            return False

    @classmethod
    def safe_scandir(cls, path: Path) -> Iterator[os.DirEntry]:
        """Safely scan a directory with proper error handling.

        Args:
            path: Directory to scan

        Yields:
            Directory entries

        Raises:
            InvalidPathError: If path is not a directory
            PermissionError: If directory can't be accessed
            IOError: For other IO errors
        """
        # Use os.path.isdir for better performance
        if not os.path.isdir(path):
            raise InvalidPathError(path, "Not a directory")

        try:
            # Use os.scandir for better performance
            for entry in os.scandir(path):
                yield entry
        except PermissionError as e:
            raise PermissionError(path, e) from e
        except OSError as e:
            raise IOError(path, str(e), e) from e

    @classmethod
    def get_path_info(cls, path: Path) -> Tuple[int, bool, bool]:
        """Get size and type information for a path.

        Args:
            path: Path to check

        Returns:
            Tuple of (size, is_file, is_dir)

        Raises:
            AccessError: If path can't be accessed
        """
        try:
            # Use os.stat directly for better performance
            stat_result = os.stat(path)
            return (
                stat_result.st_size,
                stat.S_ISREG(stat_result.st_mode),
                stat.S_ISDIR(stat_result.st_mode),
            )
        except OSError as e:
            raise AccessError(path, f"Failed to get path info: {e}", e) from e

    @classmethod
    def is_symlink(cls, path: Path) -> bool:
        """Check if a path is a symlink with caching for better performance.

        Args:
            path: Path to check

        Returns:
            True if path is a symlink
        """
        # Convert to string for faster dictionary lookup
        path_str = str(path)

        # Check cache first
        if path_str in cls._symlink_cache:
            return cls._symlink_cache[path_str]

        try:
            # Use os.path.islink for better performance
            result = os.path.islink(path)

            # Cache the result
            if len(cls._symlink_cache) < cls._MAX_SYMLINK_CACHE_SIZE:
                cls._symlink_cache[path_str] = result

            return result
        except OSError:
            return False

    @staticmethod
    def get_file_owner(path: Path) -> Optional[str]:
        """Get the owner of a file.

        Args:
            path: Path to file

        Returns:
            Owner name if available, None otherwise
        """
        try:
            import pwd  # Unix-specific

            # Use os.stat directly for better performance
            stat_info = os.stat(path)
            return pwd.getpwuid(stat_info.st_uid).pw_name
        except (ImportError, KeyError, OSError):
            return None

    @staticmethod
    def is_path_case_sensitive(path: Path) -> bool:
        """Check if the filesystem at path is case-sensitive.

        Args:
            path: Path to check

        Returns:
            True if filesystem is case-sensitive
        """
        # Use os.path.exists for better performance
        if not os.path.exists(path):
            return True  # Assume case-sensitive if path doesn't exist

        test_path = os.path.join(path, "TeSt_CaSe_SeNsItIvE")
        test_path_lower = os.path.join(path, "test_case_sensitive")

        try:
            with open(test_path, "w"):
                pass
            is_sensitive = not os.path.exists(test_path_lower)
            os.unlink(test_path)
            return is_sensitive
        except OSError:
            return True  # Assume case-sensitive on error
