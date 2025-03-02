"""High-performance metrics system for disk scanning operations."""

import logging
from typing import Optional

from .buffer import MetricsBuffer
from .collector import MetricsCollector
from .publisher import MetricsPublisher
from .subscriber import (
    BaseMetricsSubscriber,
    CallbackMetricsSubscriber,
    LoggingMetricsSubscriber,
    MetricsSubscriber,
)
from .types import MetricsError, MetricsSnapshot, MetricType, OperationTiming
from .utils import PerformanceTimer, RateCalculator, ResourceMonitor, cleanup_resources, format_rate

__version__ = "0.1.0"

# Set up logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MetricsSystem:
    """Facade for the metrics system providing a simplified interface."""

    def __init__(
        self,
        collector: Optional[MetricsCollector] = None,
        publisher: Optional[MetricsPublisher] = None,
        buffer_size: int = 1000,
        update_frequency: float = 1 / 30,
    ):
        """Initialize the metrics system.

        Args:
            collector: Optional custom metrics collector
            publisher: Optional custom metrics publisher
            buffer_size: Size of metrics buffer
            update_frequency: Target update frequency in Hz
        """
        self._collector = collector or MetricsCollector(buffer_size)
        self._publisher = publisher or MetricsPublisher(
            update_frequency=update_frequency, buffer_size=buffer_size
        )

    def start(self) -> None:
        """Start the metrics system."""
        self._publisher.start()

    def stop(self) -> None:
        """Stop the metrics system."""
        self._publisher.stop()
        self._collector.stop()

    def add_subscriber(self, subscriber: MetricsSubscriber) -> None:
        """Add a subscriber to receive metrics updates.

        Args:
            subscriber: Subscriber to add
        """
        self._publisher.add_subscriber(subscriber)

    def remove_subscriber(self, subscriber: MetricsSubscriber) -> None:
        """Remove a subscriber.

        Args:
            subscriber: Subscriber to remove
        """
        self._publisher.remove_subscriber(subscriber)

    @property
    def collector(self) -> MetricsCollector:
        """Get the metrics collector."""
        return self._collector

    @property
    def publisher(self) -> MetricsPublisher:
        """Get the metrics publisher."""
        return self._publisher

    def reset(self) -> None:
        """Reset the metrics system."""
        self._collector.reset()
        self._publisher.reset_stats()

    def __enter__(self) -> "MetricsSystem":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


# Convenience function to create a metrics system with a logging subscriber
def create_logging_metrics(
    log_level: int = logging.INFO, buffer_size: int = 1000, update_frequency: float = 1 / 30
) -> MetricsSystem:
    """Create a metrics system with a logging subscriber.

    Args:
        log_level: Logging level for metrics updates
        buffer_size: Size of metrics buffer
        update_frequency: Target update frequency in Hz

    Returns:
        Configured MetricsSystem instance
    """
    metrics = MetricsSystem(buffer_size=buffer_size, update_frequency=update_frequency)
    metrics.add_subscriber(LoggingMetricsSubscriber(log_level))
    return metrics


__all__ = [
    # Main classes
    "MetricsSystem",
    "MetricsCollector",
    "MetricsPublisher",
    "MetricsBuffer",
    # Subscriber classes
    "MetricsSubscriber",
    "BaseMetricsSubscriber",
    "LoggingMetricsSubscriber",
    "CallbackMetricsSubscriber",
    # Data types
    "MetricsSnapshot",
    "MetricsError",
    "OperationTiming",
    "MetricType",
    # Utilities
    "RateCalculator",
    "ResourceMonitor",
    "PerformanceTimer",
    "cleanup_resources",
    "format_rate",
    # Factory functions
    "create_logging_metrics",
]
