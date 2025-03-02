"""Type definitions for the metrics system."""

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Optional


class MetricType(Enum):
    """Types of metrics that can be collected."""

    FILE_COUNT = auto()
    DIRECTORY_COUNT = auto()
    TOTAL_BYTES = auto()
    SCAN_RATE = auto()  # files/sec
    TRANSFER_RATE = auto()  # bytes/sec
    OPERATION_TIMING = auto()
    MEMORY_USAGE = auto()
    CPU_USAGE = auto()


@dataclass(frozen=True)
class OperationTiming:
    """Timing information for a specific operation."""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None

    @property
    def is_complete(self) -> bool:
        """Check if the operation timing is complete."""
        return self.end_time is not None and self.duration is not None

    @classmethod
    def start(cls, operation_name: str) -> "OperationTiming":
        """Create a new operation timing with start time."""
        return cls(
            operation_name=operation_name,
            start_time=time.perf_counter_ns() / 1e9,  # Convert to seconds
        )

    def complete(self) -> "OperationTiming":
        """Complete the operation timing and calculate duration."""
        if self.is_complete:
            return self

        end_time = time.perf_counter_ns() / 1e9  # Convert to seconds
        return OperationTiming(
            operation_name=self.operation_name,
            start_time=self.start_time,
            end_time=end_time,
            duration=end_time - self.start_time,
        )


@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable snapshot of metrics at a point in time."""

    # Timestamp in seconds since epoch with nanosecond precision
    timestamp: float

    # File statistics
    file_count: int = 0
    dir_count: int = 0
    total_bytes: int = 0

    # Performance metrics
    scan_rate: float = 0.0  # files/sec
    transfer_rate: float = 0.0  # bytes/sec

    # Resource usage
    memory_usage: int = 0  # bytes
    cpu_usage: float = 0.0  # percentage (0-100)

    # Operation timings
    operation_timings: Dict[str, OperationTiming] = None

    @classmethod
    def create(cls, **kwargs) -> "MetricsSnapshot":
        """Create a new metrics snapshot with current timestamp."""
        return cls(
            timestamp=time.perf_counter_ns() / 1e9,  # Convert to seconds
            operation_timings=(
                {} if kwargs.get("operation_timings") is None else kwargs["operation_timings"]
            ),
            **{k: v for k, v in kwargs.items() if k != "operation_timings"},
        )

    def with_updates(self, **kwargs) -> "MetricsSnapshot":
        """Create a new snapshot with updated values."""
        # Create dictionary of current values
        current = {
            "timestamp": time.perf_counter_ns() / 1e9,  # Always use current time
            "file_count": self.file_count,
            "dir_count": self.dir_count,
            "total_bytes": self.total_bytes,
            "scan_rate": self.scan_rate,
            "transfer_rate": self.transfer_rate,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "operation_timings": (dict(self.operation_timings) if self.operation_timings else {}),
        }

        # Update with new values
        current.update(kwargs)

        return MetricsSnapshot(**current)


@dataclass(frozen=True)
class MetricsError:
    """Error information for metrics collection/processing."""

    error_type: str
    message: str
    timestamp: float = time.perf_counter_ns() / 1e9

    @classmethod
    def create(cls, error_type: str, message: str) -> "MetricsError":
        """Create a new metrics error with current timestamp."""
        return cls(error_type=error_type, message=message)
