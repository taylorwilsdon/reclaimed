"""Thread-safe buffer implementation for metrics exchange."""

import threading
from typing import Generic, Optional, TypeVar

from .types import MetricsSnapshot

T = TypeVar("T")


class AtomicCounter:
    """Thread-safe counter using atomic operations."""

    def __init__(self, initial: int = 0):
        """Initialize the counter.

        Args:
            initial: Initial value for the counter
        """
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, delta: int = 1) -> int:
        """Atomically increment the counter.

        Args:
            delta: Amount to increment by

        Returns:
            New counter value
        """
        with self._lock:
            self._value += delta
            return self._value

    def decrement(self, delta: int = 1) -> int:
        """Atomically decrement the counter.

        Args:
            delta: Amount to decrement by

        Returns:
            New counter value
        """
        with self._lock:
            self._value -= delta
            return self._value

    def get(self) -> int:
        """Get the current counter value."""
        with self._lock:
            return self._value

    def set(self, value: int) -> None:
        """Set the counter value.

        Args:
            value: New value for counter
        """
        with self._lock:
            self._value = value


class RingBuffer(Generic[T]):
    """Thread-safe ring buffer implementation."""

    def __init__(self, capacity: int):
        """Initialize the ring buffer.

        Args:
            capacity: Maximum number of items the buffer can hold
        """
        if capacity <= 0:
            raise ValueError("Buffer capacity must be positive")
        if not (capacity & (capacity - 1) == 0):
            # Round up to next power of 2 for efficient modulo
            capacity = 1 << (capacity - 1).bit_length()

        self._capacity = capacity
        self._mask = capacity - 1  # For fast modulo
        self._buffer = [None] * capacity
        self._read_index = 0
        self._write_index = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        """Get the buffer capacity."""
        return self._capacity

    def _increment_index(self, index: int) -> int:
        """Increment an index with wrap-around.

        Args:
            index: Current index

        Returns:
            New index
        """
        return (index + 1) & self._mask

    def push(self, item: T) -> bool:
        """Push an item to the buffer.

        Args:
            item: Item to push

        Returns:
            True if successful, False if buffer is full
        """
        with self._lock:
            next_write = self._increment_index(self._write_index)
            if next_write == self._read_index:
                return False  # Buffer is full

            self._buffer[self._write_index] = item
            self._write_index = next_write
            return True

    def pop(self) -> Optional[T]:
        """Pop an item from the buffer.

        Returns:
            Item if available, None if buffer is empty
        """
        with self._lock:
            if self._read_index == self._write_index:
                return None  # Buffer is empty

            item = self._buffer[self._read_index]
            self._buffer[self._read_index] = None  # Allow GC
            self._read_index = self._increment_index(self._read_index)
            return item

    def clear(self) -> None:
        """Clear all items from the buffer."""
        with self._lock:
            self._buffer = [None] * self._capacity
            self._read_index = 0
            self._write_index = 0

    def is_empty(self) -> bool:
        """Check if the buffer is empty."""
        with self._lock:
            return self._read_index == self._write_index

    def is_full(self) -> bool:
        """Check if the buffer is full."""
        with self._lock:
            return self._increment_index(self._write_index) == self._read_index

    def size(self) -> int:
        """Get the current number of items in the buffer."""
        with self._lock:
            if self._write_index >= self._read_index:
                return self._write_index - self._read_index
            return self._capacity - (self._read_index - self._write_index)


class MetricsBuffer:
    """Thread-safe buffer specifically for metrics exchange."""

    def __init__(self, capacity: int = 1000):
        """Initialize the metrics buffer.

        Args:
            capacity: Maximum number of metrics snapshots to store
        """
        self._buffer = RingBuffer[MetricsSnapshot](capacity)
        self._dropped_count = AtomicCounter(0)

    def push(self, metrics: MetricsSnapshot) -> bool:
        """Push a metrics snapshot to the buffer.

        Args:
            metrics: Metrics snapshot to push

        Returns:
            True if successful, False if buffer is full
        """
        if not self._buffer.push(metrics):
            self._dropped_count.increment()
            return False
        return True

    def pop(self) -> Optional[MetricsSnapshot]:
        """Pop a metrics snapshot from the buffer.

        Returns:
            Metrics snapshot if available, None if buffer is empty
        """
        return self._buffer.pop()

    def clear(self) -> None:
        """Clear all metrics from the buffer."""
        self._buffer.clear()
        self._dropped_count.set(0)

    @property
    def dropped_count(self) -> int:
        """Get the number of dropped metrics due to buffer overflow."""
        return self._dropped_count.get()

    @property
    def is_empty(self) -> bool:
        """Check if the buffer is empty."""
        return self._buffer.is_empty()

    @property
    def is_full(self) -> bool:
        """Check if the buffer is full."""
        return self._buffer.is_full()

    @property
    def size(self) -> int:
        """Get the current number of metrics in the buffer."""
        return self._buffer.size()

    @property
    def capacity(self) -> int:
        """Get the buffer capacity."""
        return self._buffer.capacity
