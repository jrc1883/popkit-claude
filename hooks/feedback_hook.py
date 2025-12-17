#!/usr/bin/env python3
"""
Feedback Collection Hook

Part of Issue #91 (User Feedback Collection System)
Parent: Epic #88 (Self-Improvement & Learning System)

PostToolUse hook that tracks tool calls and determines when to
request user feedback without causing feedback fatigue.
Uses AskUserQuestion for consistent UX.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add utils to path
utils_dir = Path(__file__).parent / "utils"
sys.path.insert(0, str(utils_dir))

from feedback_store import get_feedback_store, ContextType, FeedbackRating
from feedback_triggers import (
    get_trigger_manager,
    FeedbackTrigger,
    TriggerPriority,
    create_feedback_prompt
)


def process_hook(hook_input: dict) -> dict:
    """
    Process PostToolUse events for feedback collection.

    Args:
        hook_input: Hook input with tool_name, tool_input, tool_output, session_id

    Returns:
        Hook output dict with continue status and optional feedback prompt
    """
    tool_name = hook_input.get("tool_name", "")
    tool_output = hook_input.get("tool_output", "")
    session_id = hook_input.get("session_id", "unknown")

    # Get feedback store and check if enabled
    try:
        store = get_feedback_store()
        if not store.is_feedback_enabled():
            return {"action": "continue"}
    except Exception:
        # If store fails, continue without feedback
        return {"action": "continue"}

    # Increment tool call counter for this session
    tool_calls = store.increment_tool_calls(session_id)

    # Get trigger manager
    manager = get_trigger_manager()

    # Determine if this tool call should trigger feedback
    trigger = evaluate_trigger(hook_input, manager)

    if not trigger:
        return {"action": "continue"}

    # Check session state to see if we should show feedback
    session = store.get_or_create_session(session_id)
    should_show, reason = manager.should_show_feedback(
        trigger=trigger,
        tool_calls_since_last=session['tool_calls_since_feedback'],
        dismissed_count=session['dismissed_count'],
        never_ask_session=bool(session['never_ask_this_session']),
        min_tool_calls=int(store.get_preference('min_tool_calls', '10'))
    )

    if not should_show:
        return {"action": "continue"}

    # Build feedback response with AskUserQuestion format
    response = {
        "action": "continue",
        "feedback_request": trigger.to_ask_user_question(),
        "feedback_context": {
            "trigger_type": trigger.trigger_type.value,
            "context_type": trigger.context_type,
            "context_id": trigger.context_id,
            "agent_name": trigger.agent_name,
            "command_name": trigger.command_name,
            "workflow_phase": trigger.workflow_phase,
            "session_id": session_id,
            "tool_call_count": tool_calls
        }
    }

    return response


def evaluate_trigger(hook_input: dict, manager) -> Optional[FeedbackTrigger]:
    """
    Evaluate if the current tool call should trigger a feedback request.

    Args:
        hook_input: Hook input with tool details
        manager: FeedbackTriggerManager instance

    Returns:
        FeedbackTrigger if feedback should be requested, None otherwise
    """
    tool_name = hook_input.get("tool_name", "")
    tool_output = hook_input.get("tool_output", "")
    agent_name = hook_input.get("agent_name")
    command_name = hook_input.get("command_name")
    workflow_phase = hook_input.get("workflow_phase")

    # Check for error in output
    error_occurred = is_error_output(tool_output)

    # Check Task tool completion (agent completion)
    if tool_name == "Task" and agent_name:
        return manager.evaluate_agent_completion(
            agent_name=agent_name,
            tool_output=tool_output,
            error_occurred=error_occurred
        )

    # Check SlashCommand tool (command execution)
    if tool_name == "SlashCommand" and command_name:
        return manager.evaluate_command_execution(
            command_name=command_name,
            success=not error_occurred,
            output_size=len(tool_output) if tool_output else 0
        )

    # Check Skill tool (may indicate workflow phase)
    if tool_name == "Skill" and workflow_phase:
        return manager.evaluate_workflow_phase(
            phase_name=workflow_phase,
            phase_output=tool_output
        )

    return None


def is_error_output(output: str) -> bool:
    """
    Check if the tool output indicates an error.

    Args:
        output: Tool output string

    Returns:
        True if error detected, False otherwise
    """
    if not output:
        return False

    output_lower = output.lower()

    # Common error indicators
    error_patterns = [
        "error:",
        "exception:",
        "failed:",
        "traceback",
        "errno",
        "permission denied",
        "not found",
        "command not found",
        "syntax error"
    ]

    return any(pattern in output_lower for pattern in error_patterns)


def record_feedback_response(
    response: str,
    context: dict,
    store=None
) -> dict:
    """
    Record feedback from user response.

    This should be called when user responds to a feedback prompt.

    Args:
        response: User's response string
        context: Feedback context from the original request
        store: FeedbackStore instance (optional, uses singleton if not provided)

    Returns:
        Result dict with recorded feedback info
    """
    if store is None:
        store = get_feedback_store()

    manager = get_trigger_manager()

    # Parse the response
    rating, comment = manager.parse_feedback_response(response)

    # Handle "Skip" or dismissal
    if rating is None and comment is None:
        store.record_dismissed(context.get('session_id', 'unknown'))
        return {"action": "dismissed"}

    # Handle comment-only response (couldn't parse rating)
    if rating is None:
        # Store as a comment without rating
        return {
            "action": "comment_only",
            "comment": comment
        }

    # Record the feedback
    feedback = store.record_feedback(
        rating=rating,
        context_type=context.get('context_type', 'unknown'),
        context_id=context.get('context_id'),
        agent_name=context.get('agent_name'),
        command_name=context.get('command_name'),
        workflow_phase=context.get('workflow_phase'),
        user_comment=comment,
        session_id=context.get('session_id'),
        tool_call_count=context.get('tool_call_count', 0)
    )

    # Return result
    result = {
        "action": "recorded",
        "feedback_id": feedback.id,
        "rating": rating
    }

    # Add warning for low ratings
    if rating <= 1:
        result["low_rating_flagged"] = True

    return result


def handle_never_ask_response(response: str, session_id: str, store=None) -> dict:
    """
    Handle response to "pause feedback" prompt.

    Args:
        response: User's response string
        session_id: Current session ID
        store: FeedbackStore instance (optional)

    Returns:
        Result dict
    """
    if store is None:
        store = get_feedback_store()

    response_lower = response.lower()

    if "disable" in response_lower:
        store.set_feedback_enabled(False)
        return {"action": "disabled", "message": "Feedback collection disabled"}
    elif "pause" in response_lower:
        store.set_never_ask_session(session_id)
        return {"action": "paused", "message": "Feedback paused for this session"}
    else:
        return {"action": "continue", "message": "Feedback prompts will continue"}


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            print(json.dumps({"action": "continue"}))
            return

        hook_input = json.loads(input_data)

        # Check if this is a feedback response being recorded
        if hook_input.get("feedback_response"):
            result = record_feedback_response(
                response=hook_input["feedback_response"],
                context=hook_input.get("feedback_context", {})
            )
            print(json.dumps(result))
            return

        # Process normal hook
        result = process_hook(hook_input)
        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "action": "continue",
            "error": f"Invalid JSON input: {str(e)}"
        }))
    except Exception as e:
        print(json.dumps({
            "action": "continue",
            "error": f"Hook error: {str(e)}"
        }))


if __name__ == "__main__":
    main()
