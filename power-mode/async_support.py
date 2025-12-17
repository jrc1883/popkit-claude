#!/usr/bin/env python3
"""
Async Support Utilities for Power Mode

Provides async patterns for streaming and embeddings integration.
Uses ThreadPoolExecutor for running sync code in async context.

Part of PopKit Issue #19 (Embeddings) and #23 (Streaming).
"""

import asyncio
from typing import AsyncIterator, Callable, Any, Optional, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
import threading
import queue

T = TypeVar('T')

# =============================================================================
# THREAD POOL EXECUTOR
# =============================================================================

# Shared thread pool for sync-to-async operations
_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=max_workers)
        return _executor


def shutdown_executor(wait: bool = True) -> None:
    """Shutdown the shared executor."""
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=wait)
            _executor = None


async def run_sync(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in the thread pool.

    Args:
        func: Synchronous function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the function
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    return await loop.run_in_executor(
        executor,
        lambda: func(*args, **kwargs)
    )


# =============================================================================
# ASYNC REDIS LISTENER
# =============================================================================

async def async_redis_listen(
    pubsub,
    timeout: float = 1.0,
    stop_event: Optional[asyncio.Event] = None
) -> AsyncIterator[dict]:
    """
    Async wrapper for Redis pub/sub listener.

    Args:
        pubsub: Redis pubsub object (already subscribed)
        timeout: Timeout for get_message calls
        stop_event: Optional event to signal stop

    Yields:
        Message dictionaries from Redis
    """
    while True:
        if stop_event and stop_event.is_set():
            break

        message = await run_sync(pubsub.get_message, timeout=timeout)

        if message and message.get("type") == "message":
            yield message

        # Yield to event loop to prevent blocking
        await asyncio.sleep(0.01)


# =============================================================================
# ASYNC EVENT EMITTER
# =============================================================================

class AsyncEventEmitter:
    """
    Simple async event emitter for stream events.

    Supports both sync and async handlers.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def on(self, event: str, handler: Callable) -> 'AsyncEventEmitter':
        """
        Register an event handler.

        Args:
            event: Event name
            handler: Handler function (sync or async)

        Returns:
            Self for chaining
        """
        with self._lock:
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(handler)
        return self

    def off(self, event: str, handler: Optional[Callable] = None) -> 'AsyncEventEmitter':
        """
        Remove event handler(s).

        Args:
            event: Event name
            handler: Specific handler to remove, or None for all

        Returns:
            Self for chaining
        """
        with self._lock:
            if event in self._handlers:
                if handler is None:
                    del self._handlers[event]
                else:
                    self._handlers[event] = [
                        h for h in self._handlers[event] if h != handler
                    ]
        return self

    async def emit(self, event: str, data: Any = None) -> int:
        """
        Emit an event to all handlers.

        Args:
            event: Event name
            data: Event data

        Returns:
            Number of handlers called
        """
        with self._lock:
            handlers = list(self._handlers.get(event, []))

        count = 0
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
                count += 1
            except Exception as e:
                # Log but don't break emission
                print(f"Handler error for event '{event}': {e}")

        return count

    def handler_count(self, event: str) -> int:
        """Get number of handlers for an event."""
        with self._lock:
            return len(self._handlers.get(event, []))


# =============================================================================
# ASYNC QUEUE
# =============================================================================

class AsyncQueue(Generic[T]):
    """
    Thread-safe async queue for producer-consumer patterns.

    Useful for streaming chunks from sync producers to async consumers.
    """

    def __init__(self, maxsize: int = 0):
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._closed = False

    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """Put an item into the queue (sync)."""
        if self._closed:
            raise RuntimeError("Queue is closed")
        self._queue.put(item, block=block, timeout=timeout)

    def put_nowait(self, item: T) -> None:
        """Put an item without blocking."""
        self.put(item, block=False)

    async def get(self, timeout: Optional[float] = None) -> T:
        """Get an item from the queue (async)."""
        while True:
            try:
                return await run_sync(
                    self._queue.get,
                    block=True,
                    timeout=0.1
                )
            except queue.Empty:
                if self._closed and self._queue.empty():
                    raise StopAsyncIteration("Queue closed and empty")
                if timeout is not None:
                    timeout -= 0.1
                    if timeout <= 0:
                        raise asyncio.TimeoutError("Queue get timeout")
                await asyncio.sleep(0.01)

    def close(self) -> None:
        """Close the queue (no more puts allowed)."""
        self._closed = True

    @property
    def closed(self) -> bool:
        """Check if queue is closed."""
        return self._closed

    def __aiter__(self):
        return self

    async def __anext__(self) -> T:
        try:
            return await self.get()
        except StopAsyncIteration:
            raise StopAsyncIteration


# =============================================================================
# ASYNC BATCH PROCESSOR
# =============================================================================

@dataclass
class BatchResult(Generic[T]):
    """Result of a batch processing operation."""
    items: list[T]
    processed: int
    errors: list[Exception] = field(default_factory=list)
    duration_ms: float = 0.0


async def process_batch(
    items: list[T],
    processor: Callable[[T], Any],
    batch_size: int = 10,
    concurrency: int = 4
) -> BatchResult:
    """
    Process items in batches with controlled concurrency.

    Args:
        items: Items to process
        processor: Function to apply to each item
        batch_size: Number of items per batch
        concurrency: Max concurrent batches

    Returns:
        BatchResult with processed items and statistics
    """
    start = datetime.now()
    results = []
    errors = []

    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(item: T) -> Any:
        async with semaphore:
            if asyncio.iscoroutinefunction(processor):
                return await processor(item)
            else:
                return await run_sync(processor, item)

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        tasks = [process_one(item) for item in batch]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in batch_results:
            if isinstance(result, Exception):
                errors.append(result)
            else:
                results.append(result)

    duration = (datetime.now() - start).total_seconds() * 1000

    return BatchResult(
        items=results,
        processed=len(results),
        errors=errors,
        duration_ms=duration
    )


# =============================================================================
# RATE LIMITER
# =============================================================================

class AsyncRateLimiter:
    """
    Token bucket rate limiter for API calls.

    Useful for Voyage API rate limiting.
    """

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens needed

        Returns:
            Time waited in seconds
        """
        async with self._lock:
            waited = 0.0

            while True:
                now = datetime.now()
                elapsed = (now - self._last_update).total_seconds()
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return waited

                # Calculate wait time
                needed = tokens - self._tokens
                wait_time = needed / self.rate
                await asyncio.sleep(wait_time)
                waited += wait_time


# =============================================================================
# UTILITIES
# =============================================================================

async def with_timeout(
    coro,
    timeout: float,
    default: Any = None
) -> Any:
    """
    Run coroutine with timeout, returning default on timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        default: Value to return on timeout

    Returns:
        Result or default
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def retry_async(
    func: Callable[..., Any],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to call
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay after each retry
        exceptions: Exception types to catch

    Returns:
        Result of successful call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise last_exception


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("Testing async_support.py...")

        # Test event emitter
        emitter = AsyncEventEmitter()
        received = []

        def sync_handler(data):
            received.append(f"sync:{data}")

        async def async_handler(data):
            received.append(f"async:{data}")

        emitter.on("test", sync_handler)
        emitter.on("test", async_handler)

        await emitter.emit("test", "hello")

        assert len(received) == 2, f"Expected 2, got {len(received)}"
        print(f"  EventEmitter: OK ({received})")

        # Test async queue
        q = AsyncQueue()
        q.put("item1")
        q.put("item2")

        item = await q.get()
        assert item == "item1"
        print(f"  AsyncQueue: OK")

        # Test rate limiter
        limiter = AsyncRateLimiter(rate=10, burst=2)
        start = datetime.now()
        await limiter.acquire(1)
        await limiter.acquire(1)
        elapsed = (datetime.now() - start).total_seconds()
        print(f"  RateLimiter: OK (elapsed: {elapsed:.3f}s)")

        # Test batch processor
        items = list(range(10))
        result = await process_batch(
            items,
            lambda x: x * 2,
            batch_size=3,
            concurrency=2
        )
        assert result.processed == 10
        print(f"  BatchProcessor: OK ({result.processed} items in {result.duration_ms:.1f}ms)")

        print("\nAll tests passed!")

    asyncio.run(test())
