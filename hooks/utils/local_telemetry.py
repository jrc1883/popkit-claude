#!/usr/bin/env python3
"""
Local Telemetry Storage

File-based storage for test telemetry using JSONL format.
Stores test sessions in ~/.popkit/tests/ with streaming append-only logs.

Part of Issue #225: Telemetry Schema & Local Storage

Storage Structure:
    ~/.popkit/tests/
    ├── sessions/
    │   └── {session_id}/
    │       ├── meta.json           # Session metadata
    │       ├── traces.jsonl        # Streaming tool traces (append-only)
    │       ├── decisions.jsonl     # Decision points
    │       └── events.jsonl        # Custom events
    └── index.json                  # Session index for quick lookup

Usage:
    from hooks.utils.local_telemetry import LocalTelemetryStorage

    storage = LocalTelemetryStorage()

    # Start a session
    session = storage.start_session("skill", "pop-brainstorming")

    # Log traces as they happen (streaming)
    storage.log_trace(session.id, trace)
    storage.log_decision(session.id, decision)
    storage.log_event(session.id, event)

    # Complete session
    storage.complete_session(session.id, outcome="success")

    # Query sessions
    sessions = storage.list_sessions()
    session = storage.get_session("session-id")
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

try:
    from .test_telemetry import (
        TestSession, ToolTrace, DecisionPoint, CustomEvent, TestMetrics,
        create_session, is_test_mode, get_test_session_id,
        TestType, ExecutionMode, Outcome
    )
except ImportError:
    # For direct execution
    from test_telemetry import (
        TestSession, ToolTrace, DecisionPoint, CustomEvent, TestMetrics,
        create_session, is_test_mode, get_test_session_id,
        TestType, ExecutionMode, Outcome
    )


class LocalTelemetryStorage:
    """File-based telemetry storage using JSONL format.

    Provides streaming append-only storage for test telemetry.
    Session data is stored in separate files for efficient streaming writes.
    """

    DEFAULT_BASE_DIR = Path.home() / ".popkit" / "tests"

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize local telemetry storage.

        Args:
            base_dir: Base directory for storage (default: ~/.popkit/tests/)
        """
        self.base_dir = base_dir or self.DEFAULT_BASE_DIR
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure directory structure exists."""
        (self.base_dir / "sessions").mkdir(parents=True, exist_ok=True)

        # Create index if it doesn't exist
        index_file = self.base_dir / "index.json"
        if not index_file.exists():
            self._write_json(index_file, {"sessions": {}, "version": "1.0.0"})

    def _session_dir(self, session_id: str) -> Path:
        """Get directory for a session."""
        return self.base_dir / "sessions" / session_id

    def _write_json(self, path: Path, data: Any):
        """Write JSON to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def _read_json(self, path: Path) -> Optional[Dict]:
        """Read JSON from file."""
        if not path.exists():
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _append_jsonl(self, path: Path, data: Dict):
        """Append to JSONL file."""
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, default=str) + "\n")

    def _read_jsonl(self, path: Path) -> List[Dict]:
        """Read all entries from JSONL file."""
        if not path.exists():
            return []

        entries = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except IOError:
            pass
        return entries

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(
        self,
        test_type: TestType,
        test_name: str,
        mode: ExecutionMode = "local",
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TestSession:
        """Start a new test session.

        Creates the session directory and initializes files.

        Args:
            test_type: Type of test (skill, command, scenario)
            test_name: Name of the test
            mode: Execution mode (local or e2b)
            session_id: Optional session ID
            context: Optional context dictionary

        Returns:
            New TestSession instance
        """
        session = create_session(
            test_type=test_type,
            test_name=test_name,
            mode=mode,
            session_id=session_id,
            context=context
        )

        # Create session directory
        session_dir = self._session_dir(session.id)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Write initial metadata
        self._write_json(session_dir / "meta.json", {
            "id": session.id,
            "mode": session.mode,
            "test_type": session.test_type,
            "test_name": session.test_name,
            "started_at": session.started_at,
            "ended_at": None,
            "outcome": "running",
            "context": session.context,
            "metrics": session.metrics.to_dict()
        })

        # Create empty JSONL files
        (session_dir / "traces.jsonl").touch()
        (session_dir / "decisions.jsonl").touch()
        (session_dir / "events.jsonl").touch()

        # Update index
        self._update_index(session)

        return session

    def complete_session(
        self,
        session_id: str,
        outcome: Outcome,
        error: Optional[str] = None,
        artifacts: Optional[List[str]] = None
    ) -> bool:
        """Mark a session as complete.

        Updates metadata with final outcome and metrics.

        Args:
            session_id: Session ID
            outcome: Final outcome (success, failure, partial)
            error: Error message if failed
            artifacts: List of artifact file paths

        Returns:
            True if successful
        """
        session_dir = self._session_dir(session_id)
        meta_file = session_dir / "meta.json"

        if not meta_file.exists():
            return False

        meta = self._read_json(meta_file)
        if not meta:
            return False

        # Calculate metrics from traces
        traces = self._read_jsonl(session_dir / "traces.jsonl")
        total_duration = sum(t.get("duration_ms", 0) for t in traces)

        # Update metadata
        meta["ended_at"] = _utc_now().isoformat().replace("+00:00", "Z")
        meta["outcome"] = outcome
        meta["error"] = error
        meta["artifacts"] = artifacts or []
        meta["metrics"]["tool_calls"] = len(traces)
        meta["metrics"]["total_duration_ms"] = total_duration

        self._write_json(meta_file, meta)

        # Update index
        index = self._read_json(self.base_dir / "index.json") or {"sessions": {}}
        if session_id in index.get("sessions", {}):
            index["sessions"][session_id]["outcome"] = outcome
            index["sessions"][session_id]["ended_at"] = meta["ended_at"]
            self._write_json(self.base_dir / "index.json", index)

        return True

    def get_session(self, session_id: str) -> Optional[TestSession]:
        """Load a complete session with all telemetry data.

        Args:
            session_id: Session ID

        Returns:
            TestSession if found, None otherwise
        """
        session_dir = self._session_dir(session_id)
        meta_file = session_dir / "meta.json"

        if not meta_file.exists():
            return None

        meta = self._read_json(meta_file)
        if not meta:
            return None

        # Load telemetry data
        traces = [ToolTrace.from_dict(t) for t in self._read_jsonl(session_dir / "traces.jsonl")]
        decisions = [DecisionPoint.from_dict(d) for d in self._read_jsonl(session_dir / "decisions.jsonl")]
        events = [CustomEvent.from_dict(e) for e in self._read_jsonl(session_dir / "events.jsonl")]

        return TestSession(
            id=meta["id"],
            mode=meta["mode"],
            test_type=meta["test_type"],
            test_name=meta["test_name"],
            started_at=meta["started_at"],
            ended_at=meta.get("ended_at"),
            traces=traces,
            decisions=decisions,
            events=events,
            metrics=TestMetrics.from_dict(meta.get("metrics", {})),
            outcome=meta.get("outcome", "running"),
            artifacts=meta.get("artifacts", []),
            error=meta.get("error"),
            context=meta.get("context", {})
        )

    def list_sessions(
        self,
        limit: int = 50,
        test_type: Optional[str] = None,
        outcome: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List sessions with optional filtering.

        Returns session metadata (not full telemetry data).

        Args:
            limit: Maximum number of sessions to return
            test_type: Filter by test type
            outcome: Filter by outcome

        Returns:
            List of session metadata dictionaries
        """
        index = self._read_json(self.base_dir / "index.json") or {"sessions": {}}
        sessions = list(index.get("sessions", {}).values())

        # Sort by started_at (newest first)
        sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)

        # Apply filters
        if test_type:
            sessions = [s for s in sessions if s.get("test_type") == test_type]
        if outcome:
            sessions = [s for s in sessions if s.get("outcome") == outcome]

        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data.

        Args:
            session_id: Session ID

        Returns:
            True if deleted successfully
        """
        session_dir = self._session_dir(session_id)

        if not session_dir.exists():
            return False

        # Remove directory
        shutil.rmtree(session_dir)

        # Update index
        index = self._read_json(self.base_dir / "index.json") or {"sessions": {}}
        if session_id in index.get("sessions", {}):
            del index["sessions"][session_id]
            self._write_json(self.base_dir / "index.json", index)

        return True

    def _update_index(self, session: TestSession):
        """Update the session index."""
        index = self._read_json(self.base_dir / "index.json") or {"sessions": {}, "version": "1.0.0"}

        index["sessions"][session.id] = {
            "id": session.id,
            "test_type": session.test_type,
            "test_name": session.test_name,
            "mode": session.mode,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "outcome": session.outcome
        }

        self._write_json(self.base_dir / "index.json", index)

    # =========================================================================
    # Streaming Telemetry Logging
    # =========================================================================

    def log_trace(self, session_id: str, trace: ToolTrace) -> bool:
        """Log a tool trace to the session.

        Appends to traces.jsonl for streaming writes.

        Args:
            session_id: Session ID
            trace: ToolTrace to log

        Returns:
            True if logged successfully
        """
        session_dir = self._session_dir(session_id)
        traces_file = session_dir / "traces.jsonl"

        if not traces_file.exists():
            return False

        self._append_jsonl(traces_file, trace.to_dict())
        return True

    def log_decision(self, session_id: str, decision: DecisionPoint) -> bool:
        """Log a decision point to the session.

        Args:
            session_id: Session ID
            decision: DecisionPoint to log

        Returns:
            True if logged successfully
        """
        session_dir = self._session_dir(session_id)
        decisions_file = session_dir / "decisions.jsonl"

        if not decisions_file.exists():
            return False

        self._append_jsonl(decisions_file, decision.to_dict())
        return True

    def log_event(self, session_id: str, event: CustomEvent) -> bool:
        """Log a custom event to the session.

        Args:
            session_id: Session ID
            event: CustomEvent to log

        Returns:
            True if logged successfully
        """
        session_dir = self._session_dir(session_id)
        events_file = session_dir / "events.jsonl"

        if not events_file.exists():
            return False

        self._append_jsonl(events_file, event.to_dict())
        return True

    # =========================================================================
    # Metrics and Analysis
    # =========================================================================

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a session for quick review.

        Args:
            session_id: Session ID

        Returns:
            Summary dictionary or None
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Calculate tool usage
        tool_counts = {}
        for trace in session.traces:
            tool_counts[trace.tool_name] = tool_counts.get(trace.tool_name, 0) + 1

        return {
            "id": session.id,
            "test_type": session.test_type,
            "test_name": session.test_name,
            "outcome": session.outcome,
            "duration_ms": session.metrics.total_duration_ms,
            "tool_calls": session.metrics.tool_calls,
            "decisions": len(session.decisions),
            "events": len(session.events),
            "tool_usage": tool_counts,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "error": session.error
        }

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        deleted = 0

        index = self._read_json(self.base_dir / "index.json") or {"sessions": {}}
        sessions_to_delete = []

        for session_id, meta in index.get("sessions", {}).items():
            started_at = meta.get("started_at", "")
            try:
                session_time = datetime.fromisoformat(started_at.replace("Z", "")).timestamp()
                if session_time < cutoff:
                    sessions_to_delete.append(session_id)
            except (ValueError, TypeError):
                continue

        for session_id in sessions_to_delete:
            if self.delete_session(session_id):
                deleted += 1

        return deleted


# =============================================================================
# Convenience Functions
# =============================================================================

_storage_instance: Optional[LocalTelemetryStorage] = None


def get_local_storage() -> LocalTelemetryStorage:
    """Get or create the global local storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalTelemetryStorage()
    return _storage_instance


def log_trace_if_test_mode(trace: ToolTrace) -> bool:
    """Log a trace if currently in test mode.

    Convenience function for use in hooks.

    Args:
        trace: ToolTrace to log

    Returns:
        True if logged (in test mode), False otherwise
    """
    if not is_test_mode():
        return False

    session_id = get_test_session_id()
    if not session_id:
        return False

    return get_local_storage().log_trace(session_id, trace)


def log_decision_if_test_mode(decision: DecisionPoint) -> bool:
    """Log a decision if currently in test mode."""
    if not is_test_mode():
        return False

    session_id = get_test_session_id()
    if not session_id:
        return False

    return get_local_storage().log_decision(session_id, decision)


def log_event_if_test_mode(event: CustomEvent) -> bool:
    """Log an event if currently in test mode."""
    if not is_test_mode():
        return False

    session_id = get_test_session_id()
    if not session_id:
        return False

    return get_local_storage().log_event(session_id, event)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import tempfile

    print("Testing local_telemetry.py...")

    # Use temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "popkit-tests"
        storage = LocalTelemetryStorage(base_dir=test_dir)

        # Test session creation
        print("\n1. Test session creation:")
        session = storage.start_session(
            test_type="skill",
            test_name="pop-brainstorming",
            context={"topic": "auth"}
        )
        assert session.id is not None
        assert (test_dir / "sessions" / session.id).exists()
        print(f"  Session created: OK (id: {session.id[:8]}...)")

        # Test trace logging
        print("\n2. Test trace logging:")
        from test_telemetry import create_trace
        trace = create_trace(
            sequence=1,
            tool_name="Read",
            tool_input={"file_path": "/test.ts"},
            tool_output="content",
            duration_ms=50
        )
        success = storage.log_trace(session.id, trace)
        assert success
        print("  Trace logged: OK")

        # Test decision logging
        print("\n3. Test decision logging:")
        from test_telemetry import create_decision
        decision = create_decision(
            question="Which provider?",
            header="Auth",
            options=[{"label": "Clerk", "description": "Easy"}],
            selected="Clerk"
        )
        success = storage.log_decision(session.id, decision)
        assert success
        print("  Decision logged: OK")

        # Test event logging
        print("\n4. Test event logging:")
        from test_telemetry import create_event
        event = create_event("skill_start", {"skill": "pop-brainstorming"})
        success = storage.log_event(session.id, event)
        assert success
        print("  Event logged: OK")

        # Test session completion
        print("\n5. Test session completion:")
        success = storage.complete_session(session.id, outcome="success")
        assert success
        print("  Session completed: OK")

        # Test session retrieval
        print("\n6. Test session retrieval:")
        loaded = storage.get_session(session.id)
        assert loaded is not None
        assert loaded.id == session.id
        assert len(loaded.traces) == 1
        assert len(loaded.decisions) == 1
        assert len(loaded.events) == 1
        assert loaded.outcome == "success"
        print(f"  Session loaded: OK (traces: {len(loaded.traces)}, decisions: {len(loaded.decisions)})")

        # Test session listing
        print("\n7. Test session listing:")
        sessions = storage.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["id"] == session.id
        print(f"  Sessions listed: OK (count: {len(sessions)})")

        # Test session summary
        print("\n8. Test session summary:")
        summary = storage.get_session_summary(session.id)
        assert summary is not None
        assert summary["tool_calls"] == 1
        assert "Read" in summary["tool_usage"]
        print(f"  Summary: OK (tool_calls: {summary['tool_calls']})")

        # Test session deletion
        print("\n9. Test session deletion:")
        success = storage.delete_session(session.id)
        assert success
        assert not (test_dir / "sessions" / session.id).exists()
        sessions = storage.list_sessions()
        assert len(sessions) == 0
        print("  Session deleted: OK")

        # Test multiple sessions
        print("\n10. Test multiple sessions:")
        s1 = storage.start_session("skill", "skill-1")
        s2 = storage.start_session("command", "command-1")
        s3 = storage.start_session("scenario", "scenario-1")

        storage.complete_session(s1.id, "success")
        storage.complete_session(s2.id, "failure", error="Test error")
        storage.complete_session(s3.id, "partial")

        all_sessions = storage.list_sessions()
        assert len(all_sessions) == 3

        skill_sessions = storage.list_sessions(test_type="skill")
        assert len(skill_sessions) == 1

        failed_sessions = storage.list_sessions(outcome="failure")
        assert len(failed_sessions) == 1
        print(f"  Multiple sessions: OK (total: {len(all_sessions)})")

    print("\n" + "=" * 50)
    print("All tests passed!")
