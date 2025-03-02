"""Metrics collection and aggregation functionality."""

import os
import threading
import time
from typing import Dict, Optional

import psutil

from .buffer import AtomicCounter, MetricsBuffer
from .types import MetricsSnapshot, OperationTiming


class MetricsCollector:
    """Collects and aggregates metrics from disk operations."""

    def __init__(self, buffer_size: int = 1000):
        """Initialize the metrics collector.

        Args:
            buffer_size: Size of the metrics buffer
        """
        # Initialize atomic counters
        self._file_count = AtomicCounter()
        self._dir_count = AtomicCounter()
        self._total_bytes = AtomicCounter()

        # Performance tracking
        self._start_time = time.perf_counter_ns() / 1e9
        self._last_update_time = self._start_time
        self._last_file_count = 0
        self._last_byte_count = 0

        # Operation timing
        self._operation_timings: Dict[int, OperationTiming] = {}
        self._next_operation_id = AtomicCounter()
        self._timings_lock = threading.Lock()

        # Resource monitoring
        self._process = psutil.Process(os.getpid())

        # Metrics buffer
        self._buffer = MetricsBuffer(buffer_size)

        # Update thread
        self._should_stop = threading.Event()
        self._update_thread = threading.Thread(
            target=self._update_loop, name="MetricsCollector", daemon=True
        )
        self._update_thread.start()

    def increment_file_count(self, count: int = 1) -> None:
        """Increment the file count.

        Args:
            count: Number of files to add
        """
        self._file_count.increment(count)

    def increment_dir_count(self, count: int = 1) -> None:
        """Increment the directory count.

        Args:
            count: Number of directories to add
        """
        self._dir_count.increment(count)

    def add_bytes(self, bytes_count: int) -> None:
        """Add to the total bytes count.

        Args:
            bytes_count: Number of bytes to add
        """
        self._total_bytes.increment(bytes_count)

    def start_operation(self, operation_name: str) -> int:
        """Start timing an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Operation ID for use with end_operation
        """
        operation_id = self._next_operation_id.increment()
        timing = OperationTiming.start(operation_name)

        with self._timings_lock:
            self._operation_timings[operation_id] = timing

        return operation_id

    def end_operation(self, operation_id: int) -> Optional[float]:
        """End timing an operation.

        Args:
            operation_id: ID from start_operation

        Returns:
            Duration in seconds if operation exists, None otherwise
        """
        with self._timings_lock:
            timing = self._operation_timings.get(operation_id)
            if timing:
                completed_timing = timing.complete()
                self._operation_timings[operation_id] = completed_timing
                return completed_timing.duration
        return None

    def get_metrics_snapshot(self) -> MetricsSnapshot:
        """Get current snapshot of all metrics.

        Returns:
            Current metrics snapshot
        """
        current_time = time.perf_counter_ns() / 1e9
        elapsed = current_time - self._last_update_time

        # Get current counter values
        current_files = self._file_count.get()
        current_bytes = self._total_bytes.get()

        # Calculate rates
        if elapsed > 0:
            scan_rate = (current_files - self._last_file_count) / elapsed
            transfer_rate = (current_bytes - self._last_byte_count) / elapsed
        else:
            scan_rate = 0.0
            transfer_rate = 0.0

        # Update last values
        self._last_update_time = current_time
        self._last_file_count = current_files
        self._last_byte_count = current_bytes

        # Get resource usage
        try:
            memory_usage = self._process.memory_info().rss
            cpu_usage = self._process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            memory_usage = 0
            cpu_usage = 0.0

        # Get completed operation timings
        with self._timings_lock:
            timings = {
                op.operation_name: op for op in self._operation_timings.values() if op.is_complete
            }

        return MetricsSnapshot.create(
            file_count=current_files,
            dir_count=self._dir_count.get(),
            total_bytes=current_bytes,
            scan_rate=scan_rate,
            transfer_rate=transfer_rate,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            operation_timings=timings,
        )

    def _update_loop(self) -> None:
        """Background thread that updates metrics periodically."""
        update_interval = 1.0 / 30  # 30Hz updates

        while not self._should_stop.is_set():
            try:
                # Get current metrics
                metrics = self.get_metrics_snapshot()

                # Try to add to buffer, if full we'll just drop it
                self._buffer.push(metrics)

                # Sleep for remainder of interval
                next_update = self._last_update_time + update_interval
                current_time = time.perf_counter_ns() / 1e9
                sleep_time = max(0, next_update - current_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception:
                # Log error but keep running
                import logging

                logging.exception("Error in metrics update loop")

    def stop(self) -> None:
        """Stop the metrics collector and clean up resources."""
        self._should_stop.set()
        if self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        self._file_count.set(0)
        self._dir_count.set(0)
        self._total_bytes.set(0)
        self._start_time = time.perf_counter_ns() / 1e9
        self._last_update_time = self._start_time
        self._last_file_count = 0
        self._last_byte_count = 0

        with self._timings_lock:
            self._operation_timings.clear()

        self._buffer.clear()

    def get_buffer(self) -> MetricsBuffer:
        """Get the metrics buffer.

        Returns:
            The metrics buffer instance
        """
        return self._buffer

    def __enter__(self) -> "MetricsCollector":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
