"""Publisher implementation for distributing metrics to subscribers."""

import logging
import threading
import time
import weakref
from typing import List, Optional, Set

from .buffer import MetricsBuffer
from .subscriber import MetricsSubscriber
from .types import MetricsError, MetricsSnapshot

logger = logging.getLogger(__name__)


class MetricsPublisher:
    """Publishes metrics to subscribers with backpressure handling."""

    def __init__(
        self,
        update_frequency: float = 1 / 30,  # 30Hz default
        buffer_size: int = 1000,
        max_latency: float = 0.1,  # 100ms max latency
    ):
        """Initialize the publisher.

        Args:
            update_frequency: Target frequency for publishing updates (Hz)
            buffer_size: Size of the metrics buffer
            max_latency: Maximum acceptable latency before dropping updates (seconds)
        """
        self._update_frequency = update_frequency
        self._update_interval = 1.0 / update_frequency
        self._max_latency = max_latency

        # Metrics buffer
        self._buffer = MetricsBuffer(buffer_size)

        # Subscriber management
        self._subscribers: Set[weakref.ref[MetricsSubscriber]] = set()
        self._subscribers_lock = threading.Lock()

        # Publisher thread control
        self._should_stop = threading.Event()
        self._is_running = threading.Event()
        self._publish_thread: Optional[threading.Thread] = None

        # Performance tracking
        self._last_publish_time = 0.0
        self._publish_count = 0
        self._drop_count = 0
        self._stats_lock = threading.Lock()

    def start(self) -> None:
        """Start the publisher thread."""
        if self._is_running.is_set():
            return

        self._should_stop.clear()
        self._publish_thread = threading.Thread(
            target=self._publish_loop, name="MetricsPublisher", daemon=True
        )
        self._publish_thread.start()
        self._is_running.set()

    def stop(self) -> None:
        """Stop the publisher thread."""
        self._should_stop.set()
        if self._publish_thread and self._publish_thread.is_alive():
            self._publish_thread.join(timeout=1.0)
        self._is_running.clear()

    def add_subscriber(self, subscriber: MetricsSubscriber) -> None:
        """Add a subscriber to receive metrics updates.

        Args:
            subscriber: Subscriber to add
        """

        def cleanup(ref: weakref.ref) -> None:
            """Remove dead subscriber reference."""
            with self._subscribers_lock:
                self._subscribers.discard(ref)

        with self._subscribers_lock:
            # Use weak reference to avoid memory leaks
            self._subscribers.add(weakref.ref(subscriber, cleanup))

    def remove_subscriber(self, subscriber: MetricsSubscriber) -> None:
        """Remove a subscriber.

        Args:
            subscriber: Subscriber to remove
        """
        with self._subscribers_lock:
            to_remove = None
            for ref in self._subscribers:
                if ref() is subscriber:
                    to_remove = ref
                    break
            if to_remove:
                self._subscribers.remove(to_remove)

    def publish(self, metrics: MetricsSnapshot) -> bool:
        """Publish metrics to the buffer.

        Args:
            metrics: Metrics snapshot to publish

        Returns:
            True if published successfully, False if dropped
        """
        # Check if we're too far behind
        current_time = time.perf_counter_ns() / 1e9
        if metrics.timestamp < current_time - self._max_latency:
            with self._stats_lock:
                self._drop_count += 1
            return False

        # Try to add to buffer
        if self._buffer.push(metrics):
            with self._stats_lock:
                self._publish_count += 1
            return True

        # Buffer full, increment drop count
        with self._stats_lock:
            self._drop_count += 1
        return False

    def _publish_loop(self) -> None:
        """Main publishing loop."""
        while not self._should_stop.is_set():
            try:
                loop_start = time.perf_counter_ns() / 1e9

                # Process all available metrics
                self._process_metrics()

                # Calculate sleep time to maintain target frequency
                elapsed = time.perf_counter_ns() / 1e9 - loop_start
                sleep_time = max(0, self._update_interval - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception:
                logger.exception("Error in metrics publish loop")
                # Brief sleep to avoid tight loop on persistent errors
                time.sleep(0.1)

    def _process_metrics(self) -> None:
        """Process and publish metrics to subscribers."""
        current_time = time.perf_counter_ns() / 1e9

        # Get active subscribers
        active_subscribers: List[MetricsSubscriber] = []
        with self._subscribers_lock:
            for ref in self._subscribers:
                subscriber = ref()
                if subscriber is not None:
                    active_subscribers.append(subscriber)

        # Nothing to do if no subscribers
        if not active_subscribers:
            # Clear buffer to avoid buildup
            self._buffer.clear()
            return

        # Process all available metrics
        while True:
            metrics = self._buffer.pop()
            if metrics is None:
                break

            # Skip if too old
            if metrics.timestamp < current_time - self._max_latency:
                with self._stats_lock:
                    self._drop_count += 1
                continue

            # Publish to all active subscribers
            for subscriber in active_subscribers:
                try:
                    subscriber.on_metrics_update(metrics)
                except Exception as e:
                    logger.exception("Error publishing to subscriber")
                    error = MetricsError.create(
                        error_type="PublishError", message=f"Error publishing metrics: {str(e)}"
                    )
                    try:
                        subscriber._handle_error(error)
                    except Exception:
                        logger.exception("Error handling subscriber error")

            self._last_publish_time = current_time

    @property
    def publish_count(self) -> int:
        """Get the number of successful publishes."""
        with self._stats_lock:
            return self._publish_count

    @property
    def drop_count(self) -> int:
        """Get the number of dropped metrics."""
        with self._stats_lock:
            return self._drop_count

    @property
    def subscriber_count(self) -> int:
        """Get the current number of subscribers."""
        with self._subscribers_lock:
            return len(self._subscribers)

    def reset_stats(self) -> None:
        """Reset publishing statistics."""
        with self._stats_lock:
            self._publish_count = 0
            self._drop_count = 0

    def __enter__(self) -> "MetricsPublisher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
