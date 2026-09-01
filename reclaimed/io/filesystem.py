"""Optimized file system operations for disk scanning."""

import os
import stat
import uuid
from pathlib import Path
from typing import Iterator, Optional, Tuple

from ..core.errors import AccessError, InvalidPathError

# Aliased on import: the scanner's error types deliberately share names with
# builtin exceptions, and importing them unqualified would shadow the builtins
# that os.stat and os.scandir actually raise, making every `except` clause
# below unreachable.
from ..core.errors import FileNotFoundError as ScanFileNotFoundError
from ..core.errors import IOError as ScanIOError
from ..core.errors import PermissionError as ScanPermissionError

try:  # pwd is Unix-only; absent on Windows.
    import pwd
except ImportError:  # pragma: no cover - exercised only on Windows
    pwd = None  # type: ignore[assignment]


class FileSystemOperations:
    """High-performance file system operations with proper error handling."""

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
            raise ScanFileNotFoundError(path, e) from e
        except PermissionError as e:
            raise ScanPermissionError(path, e) from e
        except OSError as e:
            raise ScanIOError(path, str(e), e) from e

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

        return cls._iter_scandir(path)

    @staticmethod
    def _iter_scandir(path: Path) -> Iterator[os.DirEntry]:
        """Yield directory entries while translating iteration errors."""
        try:
            # Keeping the context manager alive for the duration of iteration
            # ensures the scandir handle is closed promptly.
            with os.scandir(path) as entries:
                yield from entries
        except PermissionError as e:
            raise ScanPermissionError(path, e) from e
        except OSError as e:
            raise ScanIOError(path, str(e), e) from e

    @classmethod
    def get_path_info(cls, path: Path) -> Tuple[int, bool, bool, float]:
        """Get size, type, and last modified time information for a path.

        Args:
            path: Path to check

        Returns:
            Tuple of (size, is_file, is_dir, last_modified_timestamp)

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
                stat_result.st_mtime,  # Added last modified timestamp
            )
        except OSError as e:
            raise AccessError(path, f"Failed to get path info: {e}", e) from e

    @classmethod
    def is_symlink(cls, path: Path) -> bool:
        """Check if a path is a symlink.

        Args:
            path: Path to check

        Returns:
            True if path is a symlink
        """
        try:
            # A cached answer becomes incorrect as soon as an entry is replaced
            # in place, so query the directory entry each time.
            return os.path.islink(path)
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
        if pwd is None:
            return None

        try:
            # Use os.stat directly for better performance
            stat_info = os.stat(path)
            return pwd.getpwuid(stat_info.st_uid).pw_name
        except (KeyError, OSError):
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

        probe_name = f".ReClAiMeD_CaSe_PrObE_{uuid.uuid4().hex}"
        test_path = os.path.join(path, probe_name)
        test_path_lower = os.path.join(path, probe_name.lower())
        probe_created = False

        try:
            # Exclusive creation avoids truncating an existing user file even
            # in the vanishingly unlikely event of a name collision.
            with open(test_path, "x"):
                pass
            probe_created = True
            return not os.path.exists(test_path_lower)
        except OSError:
            return True  # Assume case-sensitive on error
        finally:
            if probe_created:
                # Cleanup errors must not change the probe result. Retrying once
                # handles transient unlink failures without leaving our file
                # behind; a persistent filesystem error remains non-fatal.
                for _ in range(2):
                    try:
                        os.unlink(test_path)
                        break
                    except FileNotFoundError:
                        break
                    except OSError:
                        continue
