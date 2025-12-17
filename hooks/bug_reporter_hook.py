#!/usr/bin/env python3
"""
Automatic Bug Reporter Hook

Part of Issue #90 (Automatic Bug Reporting System)

PostToolUse hook that automatically detects errors from tool outputs,
captures context, and stores them with privacy-first defaults.
Uses existing bug_detector.py for error pattern matching and
bug_store.py for persistent storage.
"""

import json
import sys
import os
from pathlib import Path

# Add utils to path
utils_dir = Path(__file__).parent / "utils"
sys.path.insert(0, str(utils_dir))

from bug_detector import BugDetector, DetectedBug, format_detection_result
from bug_store import get_bug_store, ShareStatus
from bug_context import BugContextCapture


def process_hook(hook_input: dict) -> dict:
    """
    Process PostToolUse events for automatic bug detection.

    Args:
        hook_input: Hook input with tool_name, tool_input, tool_output, session_id

    Returns:
        Hook output dict with continue/warn status and any captured bug info
    """
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    tool_output = hook_input.get("tool_output", "")
    session_id = hook_input.get("session_id", "")

    # Get bug store and check if auto-detection is enabled
    try:
        store = get_bug_store()
        if not store.is_auto_detect_enabled():
            return {"action": "continue"}
    except Exception:
        # If store fails, continue without detection
        return {"action": "continue"}

    # Initialize detector
    detector = BugDetector()

    # Get history from session if available
    history = hook_input.get("tool_history", [])

    # Run detection
    result = detector.detect(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output if tool_output else "",
        history=history
    )

    # No bugs detected
    if not result.detected:
        return {"action": "continue"}

    # Process each detected bug
    captured_bugs = []
    for bug in result.bugs:
        captured = capture_bug(bug, tool_name, tool_input, tool_output, session_id)
        if captured:
            captured_bugs.append(captured)

    # Build response based on detection
    response = {
        "action": "continue",
        "detected_bugs": len(captured_bugs),
    }

    # Add warning message for high-confidence bugs
    high_confidence_bugs = [b for b in result.bugs if b.confidence >= 0.8]
    if high_confidence_bugs:
        # Format warning
        warning_lines = ["🐛 Bug detected and logged:"]
        for bug in high_confidence_bugs[:2]:  # Max 2 in warning
            if bug.detection_type == "error":
                warning_lines.append(f"  • {bug.error_type}: {(bug.error_message or '')[:60]}...")
            else:
                warning_lines.append(f"  • {bug.stuck_pattern}")

        if result.matched_patterns:
            best_pattern = max(result.matched_patterns, key=lambda p: p.get("similarity", 0))
            if best_pattern.get("similarity", 0) >= 0.7:
                warning_lines.append("")
                warning_lines.append(f"💡 Similar issue found: {best_pattern.get('solution', '')[:80]}...")

        warning_lines.append("")
        warning_lines.append("Use `/popkit:bug` to view, share, or search for solutions.")

        response["message"] = "\n".join(warning_lines)

    # Add suggestions if available
    if result.bugs and result.bugs[0].suggestions:
        response["suggestions"] = result.bugs[0].suggestions[:3]

    # Recommend action based on detection result
    if result.action == "inject_hint" and result.matched_patterns:
        # Found a matching pattern - inject the hint
        best_pattern = max(result.matched_patterns, key=lambda p: p.get("similarity", 0))
        response["hint"] = best_pattern.get("solution", "")
        response["hint_source"] = "collective_learning"
    elif result.action == "pause":
        # Multiple stuck patterns - suggest taking a step back
        response["message"] = (
            response.get("message", "") +
            "\n\n⚠️ Multiple stuck patterns detected. Consider reviewing your approach."
        )

    return response


def capture_bug(
    bug: DetectedBug,
    tool_name: str,
    tool_input: dict,
    tool_output: str,
    session_id: str
) -> dict:
    """
    Capture a detected bug to the store.

    Args:
        bug: The detected bug
        tool_name: Tool that triggered the bug
        tool_input: Tool input parameters
        tool_output: Tool output
        session_id: Current session ID

    Returns:
        Captured bug info dict or None
    """
    try:
        store = get_bug_store()

        # Build context summary
        if bug.detection_type == "error":
            context_summary = f"{bug.error_type} in {tool_name}"
            if tool_name == "Bash":
                cmd = tool_input.get("command", "")[:50]
                context_summary = f"{bug.error_type} when running: {cmd}"
        else:
            context_summary = bug.stuck_pattern or f"Stuck pattern in {tool_name}"

        # Build command pattern if applicable
        command_pattern = None
        if tool_name == "Bash":
            command_pattern = tool_input.get("command", "")[:100]

        # Build raw context (for later anonymization if shared)
        raw_context = {
            "tool_name": tool_name,
            "tool_input": {k: v[:200] if isinstance(v, str) else v for k, v in tool_input.items()},
            "tool_output_preview": tool_output[:500] if tool_output else "",
            "session_id": session_id,
            "detection_type": bug.detection_type,
            "suggestions": bug.suggestions,
        }

        # Detect platform
        platform = sys.platform
        shell = os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown"))

        # Capture the bug
        captured = store.capture_bug(
            error_type=bug.error_type or "stuck_behavior",
            context_summary=context_summary,
            error_message=bug.error_message,
            command_pattern=command_pattern,
            platform=platform,
            shell=shell,
            raw_context=raw_context,
            detection_source="auto",
            confidence=bug.confidence
        )

        return {
            "id": captured.id,
            "error_type": captured.error_type,
            "confidence": captured.confidence
        }

    except Exception as e:
        # Log error but don't fail the hook
        return None


def main():
    """Main entry point for the hook."""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            # No input provided
            print(json.dumps({"action": "continue"}))
            return

        hook_input = json.loads(input_data)

        # Process the hook
        result = process_hook(hook_input)

        # Output result
        print(json.dumps(result))

    except json.JSONDecodeError as e:
        # Invalid JSON input
        print(json.dumps({
            "action": "continue",
            "error": f"Invalid JSON input: {str(e)}"
        }))
    except Exception as e:
        # Unexpected error - continue without failing
        print(json.dumps({
            "action": "continue",
            "error": f"Hook error: {str(e)}"
        }))


if __name__ == "__main__":
    main()
