#!/usr/bin/env python3
"""Test telemetry module for PopKit behavioral validation (Issue #258)."""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


def is_test_mode() -> bool:
    """Check if running in test mode."""
    return os.getenv('TEST_MODE', '').lower() == 'true'


def get_test_session_id() -> Optional[str]:
    """Get the current test session ID."""
    return os.getenv('TEST_SESSION_ID')


def create_event(
    event_type: str,
    data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized telemetry event."""
    return {
        'type': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'session_id': session_id or get_test_session_id(),
        'data': data
    }


def emit_event(event: Dict[str, Any]) -> None:
    """Emit a telemetry event to stdout."""
    if not is_test_mode():
        return
    try:
        print(f"TELEMETRY:{json.dumps(event)}", file=sys.stdout, flush=True)
    except Exception:
        pass


def emit_routing_decision(
    trigger: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    selected: List[str],
    confidence: Optional[int] = None,
    reasoning: Optional[str] = None
) -> None:
    """Emit a routing decision event.

    Called by agent-orchestrator.py when routing user prompts to agents.
    """
    event = create_event('routing_decision', {
        'trigger': trigger,
        'candidates': candidates,
        'selected': selected,
        'confidence': confidence,
        'reasoning': reasoning
    })
    emit_event(event)


def emit_agent_invocation(
    agent_name: str,
    agent_id: str,
    prompt: str,
    invoked_by: str = 'hook',
    background: bool = False,
    effort: Optional[str] = None
) -> None:
    """Emit an agent invocation start event.

    Called by agent-orchestrator.py when Task tool is invoked.
    """
    event = create_event('agent_invocation_start', {
        'agent_name': agent_name,
        'agent_id': agent_id,
        'prompt': prompt,
        'invoked_by': invoked_by,
        'background': background,
        'effort': effort
    })
    emit_event(event)


def emit_agent_completion(
    agent_name: str,
    agent_id: str,
    status: str,
    duration_ms: Optional[int] = None,
    exit_code: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    """Emit an agent invocation completion event.

    Called when an agent completes (success or failure).
    """
    event = create_event('agent_invocation_complete', {
        'agent_name': agent_name,
        'agent_id': agent_id,
        'status': status,
        'duration_ms': duration_ms,
        'exit_code': exit_code,
        'error': error
    })
    emit_event(event)


def emit_skill_start(
    skill_name: str,
    workflow_id: Optional[str] = None,
    invoked_by: str = 'agent',
    activity_id: Optional[str] = None
) -> None:
    """Emit a skill start event.

    Called by skill_state.py when a skill is invoked via Skill tool.
    """
    event = create_event('skill_start', {
        'skill_name': skill_name,
        'workflow_id': workflow_id,
        'invoked_by': invoked_by,
        'activity_id': activity_id
    })
    emit_event(event)


def emit_skill_complete(
    skill_name: str,
    workflow_id: Optional[str] = None,
    status: str = 'complete',
    tool_calls: int = 0,
    decisions_made: Optional[List[str]] = None,
    error: Optional[str] = None,
    duration_ms: Optional[int] = None
) -> None:
    """Emit a skill completion event.

    Called by skill_state.py when a skill completes.
    """
    event = create_event('skill_complete', {
        'skill_name': skill_name,
        'workflow_id': workflow_id,
        'status': status,
        'tool_calls': tool_calls,
        'decisions_made': decisions_made or [],
        'error': error,
        'duration_ms': duration_ms
    })
    emit_event(event)


def emit_phase_transition(
    workflow_id: str,
    from_phase: Optional[str],
    to_phase: str,
    skill_name: Optional[str] = None,
    tool_calls_so_far: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Emit a workflow phase transition event.

    Called by skill_state.py when a multi-phase workflow transitions between phases.
    """
    event = create_event('phase_transition', {
        'workflow_id': workflow_id,
        'from_phase': from_phase,
        'to_phase': to_phase,
        'skill_name': skill_name,
        'tool_calls_so_far': tool_calls_so_far,
        'metadata': metadata or {}
    })
    emit_event(event)


def emit_user_decision(
    decision_id: str,
    question: str,
    selected_options: List[str],
    skill_name: Optional[str] = None,
    workflow_id: Optional[str] = None
) -> None:
    """Emit a user decision event.

    Called when AskUserQuestion tool is used during skill execution.
    """
    event = create_event('user_decision', {
        'decision_id': decision_id,
        'question': question,
        'selected_options': selected_options,
        'skill_name': skill_name,
        'workflow_id': workflow_id
    })
    emit_event(event)


def emit_tool_call(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    session_id: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Emit a tool call event.

    Can be called to track individual tool usage patterns.
    """
    event = create_event('tool_call', {
        'tool_name': tool_name,
        'tool_input': tool_input,
        'tool_output': tool_output[:200] if tool_output else None,
        'agent_id': agent_id,
        'agent_name': agent_name,
        'error': error
    }, session_id=session_id)
    emit_event(event)
