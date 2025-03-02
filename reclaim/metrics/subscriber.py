"""Subscriber interface and base implementation for metrics consumers."""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional

from .types import MetricsError, MetricsSnapshot

logger = logging.getLogger(__name__)


class MetricsSubscriber(ABC):
    """Abstract base class for components that consume metrics."""

    def __init__(self):
        """Initialize the subscriber."""
        self._callback_lock = threading.Lock()
        self._error_handler: Optional[Callable[[MetricsError], None]] = None
        self._last_snapshot: Optional[MetricsSnapshot] = None

    @abstractmethod
    def on_metrics_update(self, metrics: MetricsSnapshot) -> None:
        """Called when new metrics are available.

        Args:
            metrics: New metrics snapshot
        """
        pass

    def set_error_handler(self, handler: Optional[Callable[[MetricsError], None]]) -> None:
        """Set the error handler for this subscriber.

        Args:
            handler: Callback function for handling errors
        """
        with self._callback_lock:
            self._error_handler = handler

    def _handle_error(self, error: MetricsError) -> None:
        """Handle an error that occurred during metrics processing.

        Args:
            error: Error information
        """
        with self._callback_lock:
            if self._error_handler:
                try:
                    self._error_handler(error)
                except Exception:
                    logger.exception("Error in metrics error handler")
            else:
                logger.error("Metrics error: %s - %s", error.error_type, error.message)


class BaseMetricsSubscriber(MetricsSubscriber):
    """Base implementation of MetricsSubscriber with common functionality."""

    def __init__(self):
        """Initialize the base subscriber."""
        super().__init__()
        self._update_count = 0
        self._is_active = True
        self._active_lock = threading.Lock()

    def on_metrics_update(self, metrics: MetricsSnapshot) -> None:
        """Process a metrics update with error handling.

        Args:
            metrics: New metrics snapshot
        """
        if not self.is_active:
            return

        try:
            with self._callback_lock:
                self._update_count += 1
                self._last_snapshot = metrics
                self.process_metrics(metrics)
        except Exception as e:
            error = MetricsError.create(
                error_type="ProcessingError", message=f"Error processing metrics update: {str(e)}"
            )
            self._handle_error(error)

    @abstractmethod
    def process_metrics(self, metrics: MetricsSnapshot) -> None:
        """Process the metrics update.

        This method should be implemented by concrete subscribers to handle
        the actual metrics processing logic.

        Args:
            metrics: New metrics snapshot
        """
        pass

    @property
    def is_active(self) -> bool:
        """Check if the subscriber is active."""
        with self._active_lock:
            return self._is_active

    @property
    def last_snapshot(self) -> Optional[MetricsSnapshot]:
        """Get the last received metrics snapshot."""
        with self._callback_lock:
            return self._last_snapshot

    @property
    def update_count(self) -> int:
        """Get the number of updates received."""
        with self._callback_lock:
            return self._update_count

    def activate(self) -> None:
        """Activate the subscriber."""
        with self._active_lock:
            self._is_active = True

    def deactivate(self) -> None:
        """Deactivate the subscriber."""
        with self._active_lock:
            self._is_active = False

    def reset(self) -> None:
        """Reset the subscriber state."""
        with self._callback_lock:
            self._update_count = 0
            self._last_snapshot = None


class LoggingMetricsSubscriber(BaseMetricsSubscriber):
    """Example subscriber that logs metrics updates."""

    def __init__(self, log_level: int = logging.INFO):
        """Initialize the logging subscriber.

        Args:
            log_level: Logging level to use
        """
        super().__init__()
        self.log_level = log_level

    def process_metrics(self, metrics: MetricsSnapshot) -> None:
        """Log the metrics update.

        Args:
            metrics: New metrics snapshot
        """
        logger.log(
            self.log_level,
            "Metrics Update: Files=%d, Dirs=%d, Bytes=%d, Rate=%.2f files/sec",
            metrics.file_count,
            metrics.dir_count,
            metrics.total_bytes,
            metrics.scan_rate,
        )


class CallbackMetricsSubscriber(BaseMetricsSubscriber):
    """Subscriber that calls a provided callback function with metrics updates."""

    def __init__(
        self,
        callback: Callable[[MetricsSnapshot], None],
        error_handler: Optional[Callable[[MetricsError], None]] = None,
    ):
        """Initialize the callback subscriber.

        Args:
            callback: Function to call with metrics updates
            error_handler: Optional function to handle errors
        """
        super().__init__()
        self._callback = callback
        if error_handler:
            self.set_error_handler(error_handler)

    def process_metrics(self, metrics: MetricsSnapshot) -> None:
        """Call the callback with the metrics update.

        Args:
            metrics: New metrics snapshot
        """
        self._callback(metrics)
