"""
In-memory retry buffer for pushes to VictoriaMetrics' import API.

Every payload is rendered with fixed sample timestamps at poll time, so a
payload that could not be delivered (VictoriaMetrics down, DNS failure, …)
can be POSTed unchanged later on.  ``PushBuffer.submit()`` appends the new
payload and then tries to deliver the backlog, oldest first, in batched
requests.  When the buffer is full the oldest payloads are dropped.

Delivery work is bounded per ``submit()`` call so a large backlog can never
stall the poll loop long enough to trip the systemd watchdog, and the HTTP
request is performed without holding the lock, so the buffer stays readable
while a delivery is in flight.

The buffer lives in memory only; a daemon restart discards the backlog.
"""

from __future__ import annotations

import itertools
import logging
import threading
from collections import deque

import requests

logger = logging.getLogger("heizung")

DEFAULT_MAX_PAYLOADS = 1440  # ≈ 24 h at one heizung payload per minute
DEFAULT_BATCH_SIZE = 60  # payloads per POST while catching up
DEFAULT_MAX_BATCHES_PER_FLUSH = 4  # bounds how long one submit() may block
# Client errors that only mean "not now" and must be retried.
RETRYABLE_STATUS = frozenset({408, 425, 429})


def parse_push_buffer_max(value: object = DEFAULT_MAX_PAYLOADS) -> int:
    """Validate a ``push_buffer_max`` setting.

    Args:
        value: Raw config value. ``None`` keeps the default, ``0`` disables
            buffering, positive numbers bound the buffer.

    Returns:
        The validated maximum number of buffered payloads.

    Raises:
        ValueError: If the value is not an integer >= 0.
    """
    message = f"push_buffer_max must be an integer >= 0 (0 disables buffering), got {value!r}"
    if value is None:
        return DEFAULT_MAX_PAYLOADS
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(message)
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(message)
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(message) from None
    if parsed < 0:
        raise ValueError(message)
    return parsed


class PushBuffer:
    """Thread-safe FIFO of rendered import payloads with batched redelivery."""

    def __init__(
        self,
        vm_url: str,
        max_payloads: int = DEFAULT_MAX_PAYLOADS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        timeout: int = 15,
        max_batches_per_flush: int = DEFAULT_MAX_BATCHES_PER_FLUSH,
    ) -> None:
        """Create the buffer.

        Args:
            vm_url: Base URL of the VictoriaMetrics instance, e.g.
                ``http://victoriametrics.lan:8428``.
            max_payloads: Maximum number of buffered payloads; the oldest are
                dropped beyond that.
            batch_size: Maximum number of payloads combined into one POST.
            timeout: HTTP timeout in seconds per request.
            max_batches_per_flush: Maximum number of POSTs per ``submit()``, so
                one call cannot occupy the poll thread for the whole backlog.
        """
        self.url = f"{vm_url.rstrip('/')}/api/v1/import/prometheus"
        self._queue: deque[str] = deque(maxlen=max(1, int(max_payloads)))
        self._batch_size = max(1, int(batch_size))
        self._max_batches_per_flush = max(1, int(max_batches_per_flush))
        self._timeout = timeout
        self._lock = threading.Lock()
        self._failing = False
        self._redelivered = 0
        self._delivered_during_outage = 0
        self._dropped_overflow = 0
        self._dropped_rejected = 0
        self._rejection_logged = False

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)

    def submit(self, payload: str) -> None:
        """Queue a payload and try to deliver the backlog; never raises.

        Args:
            payload: Prometheus text lines with explicit timestamps.
        """
        if not payload:
            return
        warn_full = False
        with self._lock:
            if len(self._queue) == self._queue.maxlen:
                self._dropped_overflow += 1
                warn_full = self._dropped_overflow == 1
            self._queue.append(payload)
        if warn_full:
            logger.warning(
                "push buffer full (%d payloads), dropping oldest samples",
                self._queue.maxlen,
            )
        try:
            self._flush(fresh=1)
        except Exception:
            logger.exception("unexpected error while flushing push buffer")

    def _flush(self, fresh: int = 0) -> None:
        """Deliver up to ``max_batches_per_flush`` batches, oldest first.

        Args:
            fresh: Number of payloads that were just submitted and therefore
                do not count as redelivered backlog.
        """
        for _ in range(self._max_batches_per_flush):
            batch = self._next_batch()
            if not batch:
                break
            try:
                resp = requests.post(
                    self.url, data="".join(batch).encode("utf-8"), timeout=self._timeout
                )
            except requests.RequestException as exc:
                self._mark_failing(str(exc))
                return
            status = resp.status_code
            if status in (200, 204):
                self._discard(batch, fresh=fresh)
                continue
            if status in RETRYABLE_STATUS or not 400 <= status < 500:
                # Server-side problem or "come back later": keep everything.
                self._mark_failing(f"HTTP {status}: {resp.text[:200]}")
                return
            # Permanent client error: the data or the URL is wrong, so retrying
            # would block the queue forever.
            if self._discard(batch, rejected=True):
                self._log_rejection(status, resp.text)

        self._mark_recovered_if_drained()

    def _next_batch(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(itertools.islice(self._queue, self._batch_size))

    def _discard(
        self, batch: tuple[str, ...], *, rejected: bool = False, fresh: int = 0
    ) -> bool:
        """Remove a delivered batch from the front of the queue.

        The queue may have changed while the POST was in flight (another
        submitter flushed the same batch, or an overflow dropped the oldest
        entries), so only remove it when it is still the head of the queue.
        """
        with self._lock:
            current = tuple(itertools.islice(self._queue, len(batch)))
            if current != batch:
                return False
            # The payloads of the current submit are the last ones queued, so
            # only the final batch may contain them.
            tail_batch = len(self._queue) == len(batch)
            for _ in range(len(batch)):
                self._queue.popleft()
            if rejected:
                # Only count rejections that belong to the current outage;
                # steady-state rejections are reported by the ERROR line alone.
                if self._failing:
                    self._dropped_rejected += len(batch)
            elif self._failing:
                self._delivered_during_outage += len(batch)
                self._redelivered += max(0, len(batch) - (fresh if tail_batch else 0))
            return True

    def _log_rejection(self, status: int, text: str) -> None:
        with self._lock:
            first = not self._rejection_logged
            self._rejection_logged = True
        if first:
            logger.error(
                "push to %s rejected (HTTP %d), dropping pushed data: %s",
                self.url,
                status,
                text[:200],
            )
        else:
            logger.debug("push to %s still rejected (HTTP %d)", self.url, status)

    def _mark_recovered_if_drained(self) -> None:
        with self._lock:
            if not self._failing or self._queue:
                return
            delivered = self._redelivered
            delivered_any = self._delivered_during_outage
            rejected = self._dropped_rejected
            dropped = self._dropped_overflow + self._dropped_rejected
            self._failing = False
            self._redelivered = 0
            self._delivered_during_outage = 0
            self._dropped_overflow = 0
            self._dropped_rejected = 0
            self._rejection_logged = False
        if rejected and not delivered_any:
            # Nothing got through: the target is still rejecting the data.
            logger.warning(
                "push to %s still rejecting, dropped %d payloads", self.url, rejected
            )
            return
        logger.info(
            "push to %s recovered, delivered %d buffered payloads%s",
            self.url,
            delivered,
            f" ({dropped} dropped)" if dropped else "",
        )

    def _mark_failing(self, reason: str) -> None:
        with self._lock:
            failing = self._failing
            self._failing = True
            buffered = len(self._queue)
        if not failing:
            logger.warning(
                "push to %s failed, buffering payloads for later delivery: %s", self.url, reason
            )
        else:
            logger.debug("push to %s still failing (%d buffered): %s", self.url, buffered, reason)
