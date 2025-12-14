#!/usr/bin/env python3
"""
Test Telemetry Schema and Core Types

Defines the core telemetry types for the PopKit sandbox testing platform:
- TestSession: Complete test execution record
- ToolTrace: Individual tool call with timing
- DecisionPoint: AskUserQuestion interactions
- CustomEvent: Skill lifecycle events

Part of Issue #225: Telemetry Schema & Local Storage

Usage:
    from hooks.utils.test_telemetry import (
        TestSession, ToolTrace, DecisionPoint, CustomEvent,
        is_test_mode, get_test_session_id, create_session
    )

    # Check if running in test mode
    if is_test_mode():
        session_id = get_test_session_id()

    # Create a new test session
    session = create_session(
        test_type="skill",
        test_name="pop-brainstorming"
    )
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# =============================================================================
# Environment Variables for Test Mode
# =============================================================================

ENV_TEST_MODE = "POPKIT_TEST_MODE"
ENV_TEST_SESSION_ID = "POPKIT_TEST_SESSION_ID"
ENV_TEST_TYPE = "POPKIT_TEST_TYPE"
ENV_TEST_NAME = "POPKIT_TEST_NAME"


def is_test_mode() -> bool:
    """Check if running in test mode.

    Returns True if POPKIT_TEST_MODE environment variable is set to 'true'.
    """
    return os.environ.get(ENV_TEST_MODE, "").lower() == "true"


def get_test_session_id() -> Optional[str]:
    """Get the current test session ID from environment.

    Returns None if not in test mode or no session ID set.
    """
    if not is_test_mode():
        return None
    return os.environ.get(ENV_TEST_SESSION_ID)


def get_test_type() -> Optional[str]:
    """Get the current test type from environment."""
    return os.environ.get(ENV_TEST_TYPE)


def get_test_name() -> Optional[str]:
    """Get the current test name from environment."""
    return os.environ.get(ENV_TEST_NAME)


def set_test_mode(
    session_id: Optional[str] = None,
    test_type: Optional[str] = None,
    test_name: Optional[str] = None
) -> str:
    """Enable test mode and return the session ID.

    Sets environment variables for test mode detection.

    Args:
        session_id: Optional session ID (auto-generated if not provided)
        test_type: Type of test (skill, command, scenario)
        test_name: Name of the test

    Returns:
        The session ID (generated or provided)
    """
    os.environ[ENV_TEST_MODE] = "true"

    session_id = session_id or str(uuid.uuid4())
    os.environ[ENV_TEST_SESSION_ID] = session_id

    if test_type:
        os.environ[ENV_TEST_TYPE] = test_type
    if test_name:
        os.environ[ENV_TEST_NAME] = test_name

    return session_id


def clear_test_mode():
    """Clear test mode environment variables."""
    for var in [ENV_TEST_MODE, ENV_TEST_SESSION_ID, ENV_TEST_TYPE, ENV_TEST_NAME]:
        os.environ.pop(var, None)


# =============================================================================
# Telemetry Data Types
# =============================================================================

TestType = Literal["skill", "command", "scenario"]
ExecutionMode = Literal["local", "e2b"]
Outcome = Literal["success", "failure", "partial", "running"]
EventType = Literal["skill_start", "skill_end", "phase_change", "checkpoint", "custom"]


@dataclass
class ToolTrace:
    """Record of a single tool call with timing information.

    Captures everything about a tool invocation for replay and analysis.
    """
    timestamp: str                        # ISO timestamp
    sequence: int                         # Order in session (1, 2, 3...)
    tool_name: str                        # "Bash", "Read", "Edit", "Write", etc.
    tool_input: Dict[str, Any]            # Tool parameters
    tool_output: str                      # Output (truncated if >10KB)
    duration_ms: int                      # Execution time in milliseconds
    success: bool                         # Whether tool succeeded
    error: Optional[str] = None           # Error message if failed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolTrace":
        """Create from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class DecisionPoint:
    """Record of an AskUserQuestion interaction.

    Tracks user decisions during test execution for behavior analysis.
    """
    timestamp: str                        # ISO timestamp
    question: str                         # The question asked
    header: str                           # Short header/label
    options: List[Dict[str, str]]         # Available options [{label, description}]
    selected: str                         # Which option was selected
    context: str                          # What led to this decision

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionPoint":
        """Create from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class CustomEvent:
    """Record of a custom event during test execution.

    Used for skill lifecycle events, phase transitions, etc.
    """
    timestamp: str                        # ISO timestamp
    event_type: str                       # skill_start, skill_end, phase_change, etc.
    data: Dict[str, Any]                  # Event-specific data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomEvent":
        """Create from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class TestMetrics:
    """Aggregated metrics for a test session."""
    total_duration_ms: int = 0            # Total execution time
    tool_calls: int = 0                   # Number of tool invocations
    tokens_in: int = 0                    # Input tokens consumed
    tokens_out: int = 0                   # Output tokens generated
    estimated_cost_usd: float = 0.0       # Approximate cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestMetrics":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TestSession:
    """Complete record of a test session.

    The top-level container for all telemetry data from a test run.
    """
    id: str                               # Unique session ID (UUID)
    mode: ExecutionMode                   # local or e2b
    test_type: TestType                   # skill, command, or scenario
    test_name: str                        # e.g., "pop-brainstorming"
    started_at: str                       # ISO timestamp
    ended_at: Optional[str] = None        # ISO timestamp (None if running)

    # Execution traces (populated during test)
    traces: List[ToolTrace] = field(default_factory=list)
    decisions: List[DecisionPoint] = field(default_factory=list)
    events: List[CustomEvent] = field(default_factory=list)

    # Metrics (aggregated at end)
    metrics: TestMetrics = field(default_factory=TestMetrics)

    # Result
    outcome: Outcome = "running"
    artifacts: List[str] = field(default_factory=list)  # Files created
    error: Optional[str] = None

    # Context (optional)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "mode": self.mode,
            "test_type": self.test_type,
            "test_name": self.test_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "traces": [t.to_dict() for t in self.traces],
            "decisions": [d.to_dict() for d in self.decisions],
            "events": [e.to_dict() for e in self.events],
            "metrics": self.metrics.to_dict(),
            "outcome": self.outcome,
            "artifacts": self.artifacts,
            "error": self.error,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestSession":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            mode=data["mode"],
            test_type=data["test_type"],
            test_name=data["test_name"],
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            traces=[ToolTrace.from_dict(t) for t in data.get("traces", [])],
            decisions=[DecisionPoint.from_dict(d) for d in data.get("decisions", [])],
            events=[CustomEvent.from_dict(e) for e in data.get("events", [])],
            metrics=TestMetrics.from_dict(data.get("metrics", {})),
            outcome=data.get("outcome", "running"),
            artifacts=data.get("artifacts", []),
            error=data.get("error"),
            context=data.get("context", {})
        )

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def add_trace(self, trace: ToolTrace):
        """Add a tool trace to the session."""
        self.traces.append(trace)
        self.metrics.tool_calls += 1
        self.metrics.total_duration_ms += trace.duration_ms

    def add_decision(self, decision: DecisionPoint):
        """Add a decision point to the session."""
        self.decisions.append(decision)

    def add_event(self, event: CustomEvent):
        """Add a custom event to the session."""
        self.events.append(event)

    def complete(self, outcome: Outcome, error: Optional[str] = None):
        """Mark the session as complete."""
        self.ended_at = _utc_now().isoformat().replace("+00:00", "Z")
        self.outcome = outcome
        self.error = error

        # Recalculate total duration
        if self.started_at:
            start = datetime.fromisoformat(self.started_at.replace("Z", ""))
            end = datetime.fromisoformat(self.ended_at.replace("Z", ""))
            self.metrics.total_duration_ms = int((end - start).total_seconds() * 1000)


# =============================================================================
# Factory Functions
# =============================================================================

def create_session(
    test_type: TestType,
    test_name: str,
    mode: ExecutionMode = "local",
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> TestSession:
    """Create a new test session.

    Args:
        test_type: Type of test (skill, command, scenario)
        test_name: Name of the test being run
        mode: Execution mode (local or e2b)
        session_id: Optional session ID (auto-generated if not provided)
        context: Optional context dictionary

    Returns:
        New TestSession instance
    """
    return TestSession(
        id=session_id or str(uuid.uuid4()),
        mode=mode,
        test_type=test_type,
        test_name=test_name,
        started_at=_utc_now().isoformat().replace("+00:00", "Z"),
        context=context or {}
    )


def create_trace(
    sequence: int,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: str,
    duration_ms: int,
    success: bool = True,
    error: Optional[str] = None,
    max_output_length: int = 10000
) -> ToolTrace:
    """Create a tool trace with output truncation.

    Args:
        sequence: Order in session
        tool_name: Name of the tool
        tool_input: Tool parameters
        tool_output: Tool output (will be truncated if too long)
        duration_ms: Execution time
        success: Whether tool succeeded
        error: Error message if failed
        max_output_length: Maximum output length before truncation

    Returns:
        New ToolTrace instance
    """
    # Truncate output if too long
    if len(tool_output) > max_output_length:
        tool_output = tool_output[:max_output_length] + f"\n... [truncated, {len(tool_output)} total chars]"

    return ToolTrace(
        timestamp=_utc_now().isoformat().replace("+00:00", "Z"),
        sequence=sequence,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        duration_ms=duration_ms,
        success=success,
        error=error
    )


def create_decision(
    question: str,
    header: str,
    options: List[Dict[str, str]],
    selected: str,
    context: str = ""
) -> DecisionPoint:
    """Create a decision point record.

    Args:
        question: The question asked
        header: Short header/label
        options: Available options
        selected: Which option was selected
        context: What led to this decision

    Returns:
        New DecisionPoint instance
    """
    return DecisionPoint(
        timestamp=_utc_now().isoformat().replace("+00:00", "Z"),
        question=question,
        header=header,
        options=options,
        selected=selected,
        context=context
    )


def create_event(
    event_type: str,
    data: Optional[Dict[str, Any]] = None
) -> CustomEvent:
    """Create a custom event record.

    Args:
        event_type: Type of event (skill_start, skill_end, etc.)
        data: Event-specific data

    Returns:
        New CustomEvent instance
    """
    return CustomEvent(
        timestamp=_utc_now().isoformat().replace("+00:00", "Z"),
        event_type=event_type,
        data=data or {}
    )


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("Testing test_telemetry.py...")

    # Test mode detection
    print("\n1. Test mode detection:")
    assert not is_test_mode(), "Should not be in test mode initially"
    print("  Not in test mode: OK")

    session_id = set_test_mode(test_type="skill", test_name="test-skill")
    assert is_test_mode(), "Should be in test mode after set_test_mode"
    assert get_test_session_id() == session_id, "Session ID should match"
    assert get_test_type() == "skill", "Test type should be 'skill'"
    assert get_test_name() == "test-skill", "Test name should match"
    print(f"  Test mode enabled: OK (session: {session_id[:8]}...)")

    clear_test_mode()
    assert not is_test_mode(), "Should not be in test mode after clear"
    print("  Test mode cleared: OK")

    # Test session creation
    print("\n2. Test session creation:")
    session = create_session(
        test_type="skill",
        test_name="pop-brainstorming",
        context={"topic": "authentication"}
    )
    assert session.id is not None
    assert session.test_type == "skill"
    assert session.outcome == "running"
    print(f"  Session created: OK (id: {session.id[:8]}...)")

    # Test trace creation
    print("\n3. Test trace creation:")
    trace = create_trace(
        sequence=1,
        tool_name="Read",
        tool_input={"file_path": "/test/file.ts"},
        tool_output="file contents here",
        duration_ms=45,
        success=True
    )
    session.add_trace(trace)
    assert len(session.traces) == 1
    assert session.metrics.tool_calls == 1
    print(f"  Trace added: OK (tool: {trace.tool_name})")

    # Test decision point
    print("\n4. Test decision point:")
    decision = create_decision(
        question="Which auth provider?",
        header="Auth",
        options=[
            {"label": "Clerk", "description": "Easy setup"},
            {"label": "Auth0", "description": "Enterprise features"}
        ],
        selected="Clerk",
        context="User choosing auth provider for new feature"
    )
    session.add_decision(decision)
    assert len(session.decisions) == 1
    print(f"  Decision added: OK (selected: {decision.selected})")

    # Test custom event
    print("\n5. Test custom event:")
    event = create_event(
        event_type="skill_start",
        data={"skill": "pop-brainstorming", "phase": 1}
    )
    session.add_event(event)
    assert len(session.events) == 1
    print(f"  Event added: OK (type: {event.event_type})")

    # Test session completion
    print("\n6. Test session completion:")
    session.complete(outcome="success")
    assert session.outcome == "success"
    assert session.ended_at is not None
    print(f"  Session completed: OK (duration: {session.metrics.total_duration_ms}ms)")

    # Test serialization
    print("\n7. Test serialization:")
    session_dict = session.to_dict()
    assert session_dict["id"] == session.id
    assert len(session_dict["traces"]) == 1
    print("  to_dict: OK")

    session_json = session.to_json()
    assert isinstance(session_json, str)
    parsed = json.loads(session_json)
    assert parsed["id"] == session.id
    print("  to_json: OK")

    # Test deserialization
    restored = TestSession.from_dict(session_dict)
    assert restored.id == session.id
    assert len(restored.traces) == 1
    assert restored.traces[0].tool_name == "Read"
    print("  from_dict: OK")

    # Test output truncation
    print("\n8. Test output truncation:")
    long_output = "x" * 15000
    trace2 = create_trace(
        sequence=2,
        tool_name="Bash",
        tool_input={"command": "echo test"},
        tool_output=long_output,
        duration_ms=100,
        max_output_length=10000
    )
    assert len(trace2.tool_output) < 15000
    assert "truncated" in trace2.tool_output
    print(f"  Output truncated: OK (from 15000 to {len(trace2.tool_output)})")

    print("\n" + "=" * 50)
    print("All tests passed!")
