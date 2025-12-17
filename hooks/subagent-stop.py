#!/usr/bin/env python3
"""
Subagent Stop Hook
Handles subagent completion with logging, error tracking, and optional TTS notifications.
Integrates with the popkit error tracking and lessons learned system.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Import error tracking utilities
try:
    from utils.github_issues import save_error_locally, save_lesson_locally
except ImportError:
    # Fallback if utils not available
    def save_error_locally(error, status_file=None):
        return {"status": "skip", "reason": "utils not available"}
    def save_lesson_locally(lesson, status_file=None):
        return {"status": "skip", "reason": "utils not available"}


# Retry configuration
MAX_RETRIES = 1
RETRY_BACKOFF_SECONDS = 2


def create_logs_directory():
    """Create logs directory if it doesn't exist."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def check_validation_result(data: dict) -> dict | None:
    """Check if there was a validation failure from output-validator hook.

    Args:
        data: Input data from subagent stop event

    Returns:
        Validation failure dict if found, None otherwise
    """
    validation = data.get("validation_result", {})
    if validation.get("status") == "invalid":
        return {
            "type": "validation_failure",
            "agent": validation.get("agent", "unknown"),
            "output_style": validation.get("output_style", "unknown"),
            "missing_fields": validation.get("missing_fields", []),
            "confidence": validation.get("confidence", 0),
            "timestamp": datetime.now().isoformat()
        }
    return None


def track_error(error_data: dict) -> dict:
    """Track error in local STATUS.json.

    Args:
        error_data: Error information to track

    Returns:
        Result of save operation
    """
    status_file = Path(".claude/STATUS.json")
    return save_error_locally(error_data, status_file)


def should_retry(data: dict, error_data: dict) -> bool:
    """Determine if the subagent should be retried.

    Args:
        data: Original input data
        error_data: Error information

    Returns:
        True if retry should be attempted
    """
    current_retries = data.get("retry_count", 0)
    if current_retries >= MAX_RETRIES:
        return False

    # Only retry for validation failures (not for other errors)
    if error_data.get("type") == "validation_failure":
        return True

    return False


def create_retry_instruction(error_data: dict) -> str:
    """Create instruction for retry attempt.

    Args:
        error_data: Error information

    Returns:
        Instruction string for the retry
    """
    missing = error_data.get("missing_fields", [])
    output_style = error_data.get("output_style", "unknown")

    return f"""Your previous output was missing required fields for the {output_style} format.
Missing fields: {', '.join(missing)}
Please regenerate your response including these required fields."""

def get_tts_script_path():
    """Determine the best TTS script to use based on available API keys."""
    utils_dir = Path(".claude/hooks/utils/tts")
    
    # Check for API keys and return appropriate TTS script
    tts_options = [
        ("ELEVENLABS_API_KEY", utils_dir / "elevenlabs.py"),
        ("OPENAI_API_KEY", utils_dir / "openai_tts.py"),
        (None, utils_dir / "pyttsx3_tts.py")  # Local fallback
    ]
    
    for env_key, script_path in tts_options:
        if env_key is None or (env_key and env_key in os.environ):
            if script_path.exists():
                return script_path
    
    return None

def announce_subagent_completion():
    """Announce subagent completion using TTS if available."""
    try:
        import os
        import subprocess
        tts_script = get_tts_script_path()
        
        if tts_script:
            subprocess.run([
                sys.executable, str(tts_script), 
                "Subagent Complete"
            ], check=False, capture_output=True)
    except Exception:
        pass  # Silent failure for TTS

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Create logs directory
        logs_dir = create_logs_directory()

        # Log subagent stop event
        log_file = logs_dir / "subagent_stop.json"
        log_data = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []

        log_data.append(data)

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)

        # Check for validation failures and track errors
        validation_error = check_validation_result(data)
        retry_requested = False
        retry_instruction = None

        if validation_error:
            # Track the error
            track_result = track_error(validation_error)

            # Check if we should retry
            if should_retry(data, validation_error):
                retry_requested = True
                retry_instruction = create_retry_instruction(validation_error)

        # Check if chat saving is requested via data
        save_chat = data.get("save_chat", data.get("chat", False))
        if save_chat and 'transcript' in data:
            chat_file = logs_dir / "chat.json"
            with open(chat_file, 'w', encoding='utf-8') as f:
                json.dump(data['transcript'], f, indent=2)

        # Announce completion
        announce_subagent_completion()

        # Output JSON response to stdout
        response = {
            "status": "success",
            "message": "Subagent stopped - logs saved",
            "timestamp": datetime.now().isoformat(),
            "chat_saved": save_chat and 'transcript' in data,
            "validation_tracked": validation_error is not None,
            "retry_requested": retry_requested
        }

        if retry_requested and retry_instruction:
            response["retry_instruction"] = retry_instruction
            response["retry_count"] = data.get("retry_count", 0) + 1

        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)  # Don't block on errors
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in subagent_stop hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors

if __name__ == "__main__":
    main()