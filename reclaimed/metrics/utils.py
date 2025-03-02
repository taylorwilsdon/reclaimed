"""Utility functions for the metrics system."""

import gc
import os
import threading
import time
from typing import Optional, Tuple

import psutil


def get_process_metrics() -> Tuple[int, float]:
    """Get current process memory and CPU usage.

    Returns:
        Tuple of (memory_bytes, cpu_percent)
    """
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        return memory_info.rss, cpu_percent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0, 0.0


class RateCalculator:
    """Calculate rates over time windows."""

    def __init__(self, window_size: float = 1.0):
        """Initialize the rate calculator.

        Args:
            window_size: Time window for rate calculation in seconds
        """
        self._window_size = window_size
        self._values = []
        self._timestamps = []
        self._lock = threading.Lock()

    def add_value(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add a value to the calculator.

        Args:
            value: Value to add
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.perf_counter_ns() / 1e9

        with self._lock:
            # Add new value
            self._values.append(value)
            self._timestamps.append(timestamp)

            # Remove old values outside the window
            cutoff = timestamp - self._window_size
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.pop(0)
                self._values.pop(0)

    def get_rate(self) -> float:
        """Calculate the current rate.

        Returns:
            Rate (units/second) over the window
        """
        with self._lock:
            if len(self._values) < 2:
                return 0.0

            time_diff = self._timestamps[-1] - self._timestamps[0]
            if time_diff <= 0:
                return 0.0

            value_diff = self._values[-1] - self._values[0]
            return value_diff / time_diff

    def reset(self) -> None:
        """Reset the calculator."""
        with self._lock:
            self._values.clear()
            self._timestamps.clear()


class ResourceMonitor:
    """Monitor system resource usage."""

    def __init__(self, check_interval: float = 1.0):
        """Initialize the resource monitor.

        Args:
            check_interval: How often to check resource usage (seconds)
        """
        self._check_interval = check_interval
        self._last_check = 0.0
        self._last_memory = 0
        self._last_cpu = 0.0
        self._lock = threading.Lock()

    def check_resources(self, force: bool = False) -> Tuple[int, float]:
        """Check current resource usage.

        Args:
            force: Force check even if interval hasn't elapsed

        Returns:
            Tuple of (memory_bytes, cpu_percent)
        """
        current_time = time.perf_counter_ns() / 1e9

        with self._lock:
            if not force and current_time - self._last_check < self._check_interval:
                return self._last_memory, self._last_cpu

            self._last_memory, self._last_cpu = get_process_metrics()
            self._last_check = current_time
            return self._last_memory, self._last_cpu


def cleanup_resources() -> None:
    """Perform resource cleanup operations."""
    # Force garbage collection
    gc.collect()

    # Suggest memory cleanup to OS
    if hasattr(gc, "garbage"):
        del gc.garbage[:]

    # On Unix-like systems, try to free memory back to OS
    if hasattr(psutil, "Process"):
        try:
            process = psutil.Process(os.getpid())
            # Try to release memory back to OS
            if hasattr(process, "memory_full_info"):
                process.memory_full_info()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


class PerformanceTimer:
    """High-precision timer for performance measurements."""

    def __init__(self, name: str):
        """Initialize the timer.

        Args:
            name: Name of the operation being timed
        """
        self.name = name
        self._start_time = 0.0
        self._end_time = 0.0
        self._is_running = False

    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.perf_counter_ns() / 1e9
        self._is_running = True

    def stop(self) -> float:
        """Stop the timer and get elapsed time.

        Returns:
            Elapsed time in seconds
        """
        if not self._is_running:
            return 0.0

        self._end_time = time.perf_counter_ns() / 1e9
        self._is_running = False
        return self.elapsed

    @property
    def elapsed(self) -> float:
        """Get elapsed time.

        Returns:
            Elapsed time in seconds
        """
        if self._is_running:
            return time.perf_counter_ns() / 1e9 - self._start_time
        return self._end_time - self._start_time

    def __enter__(self) -> "PerformanceTimer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


def format_rate(rate: float) -> str:
    """Format a rate value for display.

    Args:
        rate: Rate value to format

    Returns:
        Formatted rate string
    """
    if rate >= 1_000_000:
        return f"{rate/1_000_000:.1f}M/s"
    elif rate >= 1_000:
        return f"{rate/1_000:.1f}K/s"
    else:
        return f"{rate:.1f}/s"
