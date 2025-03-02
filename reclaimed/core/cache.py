"""Optimized cache implementation for directory sizes."""

import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple


@dataclass
class CacheEntry:
    """Entry in the directory size cache."""

    size: int
    is_icloud: bool
    timestamp: float
    valid: bool = True


class DirectorySizeCache:
    """High-performance cache for directory sizes."""

    def __init__(self, ttl: float = 600.0):  # 10 minute default TTL
        """Initialize the cache.

        Args:
            ttl: Time-to-live in seconds for cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}  # Use string keys for better performance
        self._lock = RLock()  # Use RLock for better performance with recursive calls
        self._ttl = ttl

    def get(self, path: Path) -> Optional[Tuple[int, bool]]:
        """Get size and iCloud status for a directory if cached.

        Args:
            path: Directory path to look up

        Returns:
            Tuple of (size, is_icloud) if cached and valid, None otherwise
        """
        # Convert path to string for faster dictionary lookup
        path_str = str(path)

        # Use a try/finally with lock to ensure lock is always released
        try:
            self._lock.acquire()
            entry = self._cache.get(path_str)
            if entry and entry.valid:
                # Check if entry has expired
                if time.time() - entry.timestamp > self._ttl:
                    entry.valid = False
                    return None

                return entry.size, entry.is_icloud
            return None
        finally:
            self._lock.release()

    def set(self, path: Path, size: int, is_icloud: bool) -> None:
        """Cache the size and iCloud status for a directory.

        Args:
            path: Directory path to cache
            size: Total size in bytes
            is_icloud: Whether directory contains iCloud files
        """
        # Convert path to string for faster dictionary operations
        path_str = str(path)

        try:
            self._lock.acquire()
            self._cache[path_str] = CacheEntry(
                size=size, is_icloud=is_icloud, timestamp=time.time()
            )
        finally:
            self._lock.release()

    def get_all_cached_dirs(self) -> List[Path]:
        """Get all cached directory paths.

        Returns:
            List of all cached directory paths
        """
        try:
            self._lock.acquire()
            return [Path(p) for p, entry in self._cache.items() if entry.valid]
        finally:
            self._lock.release()

    def invalidate(self, path: Path) -> None:
        """Invalidate cache entry for a directory.

        Args:
            path: Directory path to invalidate
        """
        path_str = str(path)

        try:
            self._lock.acquire()
            if path_str in self._cache:
                self._cache[path_str].valid = False
        finally:
            self._lock.release()

    def invalidate_by_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: String pattern to match against path names
        """
        try:
            self._lock.acquire()
            for path_str in list(self._cache.keys()):
                if pattern in path_str:
                    self._cache[path_str].valid = False
        finally:
            self._lock.release()

    def clear(self) -> None:
        """Clear all cached entries."""
        try:
            self._lock.acquire()
            self._cache.clear()
        finally:
            self._lock.release()

    def cleanup(self) -> None:
        """Remove expired and invalid entries."""
        current_time = time.time()

        try:
            self._lock.acquire()
            # Create list of keys to remove to avoid modifying dict during iteration
            to_remove = [
                path_str
                for path_str, entry in self._cache.items()
                if not entry.valid or (current_time - entry.timestamp > self._ttl)
            ]

            # Remove invalid entries
            for path_str in to_remove:
                del self._cache[path_str]
        finally:
            self._lock.release()
