#!/usr/bin/env python3
"""
Upstash Telemetry Sync for PopKit Sandbox Testing

Streams telemetry data to Upstash Redis Streams for real-time observability
and async sync from local tests. Part of Issue #228.

Features:
- Real-time streaming (E2B mode) via XADD
- Batch sync (local mode, post-test)
- Async background sync with queue
- Rate limiting to stay within free tier
- Data retention via MAXLEN and TTL

Stream Key Naming:
- popkit:test:{session_id}:traces    - Tool execution traces
- popkit:test:{session_id}:decisions - User decision points
- popkit:test:{session_id}:events    - Skill lifecycle events
- popkit:test:{session_id}:meta      - Session metadata

Usage:
    from hooks.utils.upstash_telemetry import (
        UpstashTelemetryClient,
        stream_trace, sync_local_session,
        is_upstash_telemetry_available
    )

    # Real-time streaming
    client = UpstashTelemetryClient()
    client.stream_trace(session_id, trace)

    # Batch sync after local test
    sync_local_session(session_id)
"""

import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Try to import telemetry types
try:
    from test_telemetry import (
        ToolTrace, DecisionPoint, CustomEvent, TestSession, TestMetrics,
        is_test_mode, get_test_session_id
    )
    from local_telemetry import get_local_storage, LocalTelemetryStorage
    TELEMETRY_TYPES_AVAILABLE = True
except ImportError:
    TELEMETRY_TYPES_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================

UPSTASH_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Stream configuration
STREAM_PREFIX = "popkit:test"
DEFAULT_MAXLEN = 1000          # Max entries per stream
DEFAULT_TTL = 86400 * 7        # 7 days retention
RATE_LIMIT_REQUESTS = 100      # Max requests per second (Upstash free tier)
RATE_LIMIT_WINDOW = 1.0        # Window in seconds
BATCH_SIZE = 50                # Max items per batch sync

SyncMode = Literal["realtime", "batch", "async"]


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: int = RATE_LIMIT_REQUESTS, window: float = RATE_LIMIT_WINDOW):
        self.rate = rate
        self.window = window
        self.tokens = rate
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill

            # Refill tokens based on elapsed time
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.window))
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    def wait_for_token(self, timeout: float = 5.0) -> bool:
        """Wait until a token is available or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            if self.acquire():
                return True
            time.sleep(0.01)
        return False


# =============================================================================
# Upstash Telemetry Client
# =============================================================================

class UpstashTelemetryClient:
    """
    Client for streaming telemetry to Upstash Redis Streams.

    Provides methods for real-time streaming, batch sync, and async queue.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        rate_limit: bool = True
    ):
        """Initialize the telemetry client.

        Args:
            url: Upstash REST URL (defaults to env var)
            token: Upstash REST token (defaults to env var)
            rate_limit: Enable rate limiting
        """
        self.url = (url or UPSTASH_REST_URL or "").rstrip("/")
        self.token = token or UPSTASH_REST_TOKEN

        if not self.url or not self.token:
            raise ValueError(
                "Upstash credentials required. Set UPSTASH_REDIS_REST_URL and "
                "UPSTASH_REDIS_REST_TOKEN environment variables."
            )

        self.rate_limiter = RateLimiter() if rate_limit else None
        self._async_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._async_worker: Optional[threading.Thread] = None
        self._async_running = False

    def _execute(self, *args: str, retry: int = 2) -> Any:
        """Execute Redis command via Upstash REST API with retry."""
        if self.rate_limiter and not self.rate_limiter.wait_for_token():
            return None  # Rate limited

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        for attempt in range(retry + 1):
            try:
                request = Request(self.url, method="POST")
                for key, value in headers.items():
                    request.add_header(key, value)

                body = json.dumps(list(args)).encode('utf-8')

                with urlopen(request, body, timeout=10) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return result.get("result")

            except HTTPError as e:
                if e.code == 429 and attempt < retry:
                    time.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                return None
            except URLError:
                if attempt < retry:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                return None

        return None

    def _stream_key(self, session_id: str, stream_type: str) -> str:
        """Generate stream key for a session."""
        return f"{STREAM_PREFIX}:{session_id}:{stream_type}"

    # =========================================================================
    # Stream Operations
    # =========================================================================

    def xadd(
        self,
        stream_key: str,
        fields: Dict[str, str],
        maxlen: int = DEFAULT_MAXLEN
    ) -> Optional[str]:
        """Add entry to stream with MAXLEN limit.

        Args:
            stream_key: Redis stream key
            fields: Fields to add
            maxlen: Maximum stream length

        Returns:
            Entry ID if successful, None otherwise
        """
        args = ["XADD", stream_key, "MAXLEN", "~", str(maxlen), "*"]
        for k, v in fields.items():
            args.extend([k, str(v)])

        result = self._execute(*args)
        return result if isinstance(result, str) else None

    def xread(
        self,
        streams: Dict[str, str],
        count: int = 10,
        block: Optional[int] = None
    ) -> List:
        """Read from streams.

        Args:
            streams: Dict of stream_key -> last_id
            count: Max entries to return
            block: Block timeout in ms (None for no blocking)

        Returns:
            List of stream entries
        """
        args = ["XREAD", "COUNT", str(count)]
        if block is not None:
            args.extend(["BLOCK", str(block)])
        args.append("STREAMS")
        args.extend(streams.keys())
        args.extend(streams.values())

        result = self._execute(*args)
        return result if isinstance(result, list) else []

    def xrange(
        self,
        stream_key: str,
        min_id: str = "-",
        max_id: str = "+",
        count: Optional[int] = None
    ) -> List:
        """Get stream entries in range.

        Args:
            stream_key: Redis stream key
            min_id: Start ID (- for beginning)
            max_id: End ID (+ for end)
            count: Max entries to return

        Returns:
            List of [id, fields] entries
        """
        args = ["XRANGE", stream_key, min_id, max_id]
        if count:
            args.extend(["COUNT", str(count)])

        result = self._execute(*args)
        return result if isinstance(result, list) else []

    def xlen(self, stream_key: str) -> int:
        """Get stream length."""
        result = self._execute("XLEN", stream_key)
        return result if isinstance(result, int) else 0

    def set_ttl(self, key: str, seconds: int = DEFAULT_TTL) -> bool:
        """Set expiration on key."""
        result = self._execute("EXPIRE", key, str(seconds))
        return result == 1

    # =========================================================================
    # Telemetry Streaming
    # =========================================================================

    def stream_trace(self, session_id: str, trace: "ToolTrace") -> bool:
        """Stream a tool trace to Upstash.

        Args:
            session_id: Test session ID
            trace: ToolTrace to stream

        Returns:
            True if successful
        """
        stream_key = self._stream_key(session_id, "traces")

        fields = {
            "timestamp": trace.timestamp,
            "sequence": str(trace.sequence),
            "tool_name": trace.tool_name,
            "tool_input": json.dumps(trace.tool_input),
            "tool_output": trace.tool_output[:5000],  # Truncate for streams
            "duration_ms": str(trace.duration_ms),
            "success": "1" if trace.success else "0",
            "error": trace.error or ""
        }

        entry_id = self.xadd(stream_key, fields)
        if entry_id:
            self.set_ttl(stream_key)
        return entry_id is not None

    def stream_decision(self, session_id: str, decision: "DecisionPoint") -> bool:
        """Stream a decision point to Upstash.

        Args:
            session_id: Test session ID
            decision: DecisionPoint to stream

        Returns:
            True if successful
        """
        stream_key = self._stream_key(session_id, "decisions")

        fields = {
            "timestamp": decision.timestamp,
            "question": decision.question,
            "header": decision.header,
            "options": json.dumps(decision.options),
            "selected": decision.selected,
            "context": decision.context[:1000]
        }

        entry_id = self.xadd(stream_key, fields)
        if entry_id:
            self.set_ttl(stream_key)
        return entry_id is not None

    def stream_event(self, session_id: str, event: "CustomEvent") -> bool:
        """Stream a custom event to Upstash.

        Args:
            session_id: Test session ID
            event: CustomEvent to stream

        Returns:
            True if successful
        """
        stream_key = self._stream_key(session_id, "events")

        fields = {
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "data": json.dumps(event.data)
        }

        entry_id = self.xadd(stream_key, fields)
        if entry_id:
            self.set_ttl(stream_key)
        return entry_id is not None

    def stream_session_meta(self, session: "TestSession") -> bool:
        """Stream session metadata.

        Args:
            session: TestSession to stream

        Returns:
            True if successful
        """
        stream_key = self._stream_key(session.id, "meta")

        fields = {
            "session_id": session.id,
            "mode": session.mode,
            "test_type": session.test_type,
            "test_name": session.test_name,
            "started_at": session.started_at,
            "ended_at": session.ended_at or "",
            "outcome": session.outcome,
            "metrics": json.dumps(session.metrics.to_dict() if hasattr(session.metrics, 'to_dict') else {}),
            "artifacts": json.dumps(session.artifacts)
        }

        entry_id = self.xadd(stream_key, fields, maxlen=10)  # Keep only latest
        if entry_id:
            self.set_ttl(stream_key)
        return entry_id is not None

    # =========================================================================
    # Batch Sync
    # =========================================================================

    def sync_local_session(
        self,
        session_id: str,
        storage: Optional["LocalTelemetryStorage"] = None
    ) -> Dict[str, int]:
        """Sync a local test session to Upstash.

        Reads JSONL files from local storage and streams to Upstash.

        Args:
            session_id: Session ID to sync
            storage: Local storage instance (defaults to get_local_storage())

        Returns:
            Dict with counts: {traces, decisions, events, meta}
        """
        if not TELEMETRY_TYPES_AVAILABLE:
            return {"error": "Telemetry types not available"}

        storage = storage or get_local_storage()
        session_dir = Path.home() / ".popkit" / "tests" / "sessions" / session_id

        if not session_dir.exists():
            return {"error": f"Session not found: {session_id}"}

        counts = {"traces": 0, "decisions": 0, "events": 0, "meta": 0}

        # Sync traces
        traces_file = session_dir / "traces.jsonl"
        if traces_file.exists():
            for line in traces_file.read_text().strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        trace = ToolTrace.from_dict(data)
                        if self.stream_trace(session_id, trace):
                            counts["traces"] += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Sync decisions
        decisions_file = session_dir / "decisions.jsonl"
        if decisions_file.exists():
            for line in decisions_file.read_text().strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        decision = DecisionPoint.from_dict(data)
                        if self.stream_decision(session_id, decision):
                            counts["decisions"] += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Sync events
        events_file = session_dir / "events.jsonl"
        if events_file.exists():
            for line in events_file.read_text().strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        event = CustomEvent.from_dict(data)
                        if self.stream_event(session_id, event):
                            counts["events"] += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Sync metadata
        meta_file = session_dir / "meta.json"
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text())
                session = storage.get_session(session_id)
                if session and self.stream_session_meta(session):
                    counts["meta"] = 1
            except (json.JSONDecodeError, TypeError):
                pass

        return counts

    # =========================================================================
    # Async Queue
    # =========================================================================

    def start_async_worker(self):
        """Start background worker for async streaming."""
        if self._async_running:
            return

        self._async_running = True
        self._async_worker = threading.Thread(target=self._async_worker_loop, daemon=True)
        self._async_worker.start()

    def stop_async_worker(self):
        """Stop background worker."""
        self._async_running = False
        if self._async_worker:
            self._async_worker.join(timeout=5.0)
            self._async_worker = None

    def _async_worker_loop(self):
        """Background worker that processes async queue."""
        while self._async_running:
            try:
                item = self._async_queue.get(timeout=1.0)
                session_id, item_type, data = item

                if item_type == "trace":
                    self.stream_trace(session_id, data)
                elif item_type == "decision":
                    self.stream_decision(session_id, data)
                elif item_type == "event":
                    self.stream_event(session_id, data)

                self._async_queue.task_done()

            except queue.Empty:
                continue
            except Exception:
                pass

    def queue_trace(self, session_id: str, trace: "ToolTrace") -> bool:
        """Queue trace for async streaming."""
        try:
            self._async_queue.put_nowait((session_id, "trace", trace))
            return True
        except queue.Full:
            return False

    def queue_decision(self, session_id: str, decision: "DecisionPoint") -> bool:
        """Queue decision for async streaming."""
        try:
            self._async_queue.put_nowait((session_id, "decision", decision))
            return True
        except queue.Full:
            return False

    def queue_event(self, session_id: str, event: "CustomEvent") -> bool:
        """Queue event for async streaming."""
        try:
            self._async_queue.put_nowait((session_id, "event", event))
            return True
        except queue.Full:
            return False

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_session_traces(
        self,
        session_id: str,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get traces from a session stream.

        Args:
            session_id: Test session ID
            count: Max traces to return

        Returns:
            List of trace dictionaries
        """
        stream_key = self._stream_key(session_id, "traces")
        entries = self.xrange(stream_key, count=count)

        traces = []
        for entry in entries:
            if isinstance(entry, list) and len(entry) >= 2:
                fields = entry[1]
                trace_data = {}
                for i in range(0, len(fields), 2):
                    trace_data[fields[i]] = fields[i + 1]

                # Parse JSON fields
                if "tool_input" in trace_data:
                    try:
                        trace_data["tool_input"] = json.loads(trace_data["tool_input"])
                    except json.JSONDecodeError:
                        pass

                trace_data["sequence"] = int(trace_data.get("sequence", 0))
                trace_data["duration_ms"] = int(trace_data.get("duration_ms", 0))
                trace_data["success"] = trace_data.get("success") == "1"

                traces.append(trace_data)

        return traces

    def get_session_events(
        self,
        session_id: str,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events from a session stream."""
        stream_key = self._stream_key(session_id, "events")
        entries = self.xrange(stream_key, count=count)

        events = []
        for entry in entries:
            if isinstance(entry, list) and len(entry) >= 2:
                fields = entry[1]
                event_data = {}
                for i in range(0, len(fields), 2):
                    event_data[fields[i]] = fields[i + 1]

                if "data" in event_data:
                    try:
                        event_data["data"] = json.loads(event_data["data"])
                    except json.JSONDecodeError:
                        pass

                events.append(event_data)

        return events

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a session from Upstash streams.

        Args:
            session_id: Test session ID

        Returns:
            Summary with counts and latest metadata
        """
        summary = {
            "session_id": session_id,
            "trace_count": self.xlen(self._stream_key(session_id, "traces")),
            "decision_count": self.xlen(self._stream_key(session_id, "decisions")),
            "event_count": self.xlen(self._stream_key(session_id, "events")),
            "meta": None
        }

        # Get latest metadata
        meta_entries = self.xrange(self._stream_key(session_id, "meta"), count=1)
        if meta_entries and len(meta_entries) > 0:
            entry = meta_entries[-1]
            if isinstance(entry, list) and len(entry) >= 2:
                fields = entry[1]
                meta = {}
                for i in range(0, len(fields), 2):
                    meta[fields[i]] = fields[i + 1]
                summary["meta"] = meta

        return summary

    def ping(self) -> bool:
        """Check Upstash connection."""
        result = self._execute("PING")
        return result == "PONG"


# =============================================================================
# Convenience Functions
# =============================================================================

_client_instance: Optional[UpstashTelemetryClient] = None


def get_telemetry_client() -> UpstashTelemetryClient:
    """Get singleton telemetry client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = UpstashTelemetryClient()
    return _client_instance


def is_upstash_telemetry_available() -> bool:
    """Check if Upstash telemetry is available."""
    if not UPSTASH_REST_URL or not UPSTASH_REST_TOKEN:
        return False

    try:
        client = UpstashTelemetryClient()
        return client.ping()
    except Exception:
        return False


def stream_trace_if_available(session_id: str, trace: "ToolTrace") -> bool:
    """Stream trace if Upstash is available."""
    if not is_upstash_telemetry_available():
        return False

    try:
        client = get_telemetry_client()
        return client.stream_trace(session_id, trace)
    except Exception:
        return False


def stream_event_if_available(session_id: str, event: "CustomEvent") -> bool:
    """Stream event if Upstash is available."""
    if not is_upstash_telemetry_available():
        return False

    try:
        client = get_telemetry_client()
        return client.stream_event(session_id, event)
    except Exception:
        return False


def sync_local_session(session_id: str) -> Dict[str, int]:
    """Sync a local session to Upstash."""
    if not is_upstash_telemetry_available():
        return {"error": "Upstash not available"}

    client = get_telemetry_client()
    return client.sync_local_session(session_id)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PopKit Upstash Telemetry Sync")
    parser.add_argument("--status", action="store_true", help="Check Upstash status")
    parser.add_argument("--sync", metavar="SESSION_ID", help="Sync local session to Upstash")
    parser.add_argument("--query", metavar="SESSION_ID", help="Query session from Upstash")
    parser.add_argument("--test", action="store_true", help="Run integration test")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.status:
        print("Upstash Telemetry Status")
        print("=" * 40)
        if UPSTASH_REST_URL:
            print(f"URL: {UPSTASH_REST_URL[:40]}...")
        else:
            print("URL: Not configured")
        print(f"Token: {'Configured' if UPSTASH_REST_TOKEN else 'Not configured'}")
        print(f"Available: {is_upstash_telemetry_available()}")

    elif args.sync:
        result = sync_local_session(args.sync)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sync result for {args.sync}:")
            for key, value in result.items():
                print(f"  {key}: {value}")

    elif args.query:
        if not is_upstash_telemetry_available():
            print("Upstash not available")
            return

        client = get_telemetry_client()
        summary = client.get_session_summary(args.query)

        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Session: {args.query}")
            print(f"Traces: {summary['trace_count']}")
            print(f"Decisions: {summary['decision_count']}")
            print(f"Events: {summary['event_count']}")
            if summary.get("meta"):
                print(f"Test: {summary['meta'].get('test_name', 'unknown')}")
                print(f"Outcome: {summary['meta'].get('outcome', 'unknown')}")

    elif args.test:
        if not is_upstash_telemetry_available():
            print("Upstash not available - cannot run test")
            return

        print("Running Upstash Telemetry Integration Test...")
        print()

        try:
            client = get_telemetry_client()

            # Create test session
            test_session_id = f"test-{int(time.time())}"
            print(f"Test session: {test_session_id}")

            # Test trace streaming
            if TELEMETRY_TYPES_AVAILABLE:
                from test_telemetry import create_trace, create_event

                trace = create_trace(
                    sequence=1,
                    tool_name="TestTool",
                    tool_input={"test": "input"},
                    tool_output="test output",
                    duration_ms=100,
                    success=True
                )
                result = client.stream_trace(test_session_id, trace)
                print(f"[{'OK' if result else 'FAIL'}] Stream trace")

                event = create_event("test_event", {"test": "data"})
                result = client.stream_event(test_session_id, event)
                print(f"[{'OK' if result else 'FAIL'}] Stream event")

            # Query back
            summary = client.get_session_summary(test_session_id)
            print(f"[{'OK' if summary['trace_count'] > 0 else 'FAIL'}] Query traces: {summary['trace_count']}")
            print(f"[{'OK' if summary['event_count'] > 0 else 'FAIL'}] Query events: {summary['event_count']}")

            print()
            print("Integration test complete!")

        except Exception as e:
            print(f"[FAIL] {e}")
            import traceback
            traceback.print_exc()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
