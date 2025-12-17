#!/usr/bin/env python3
"""
PopKit Notification Formatter Hook

Auto-formats structured messages from Power Mode into human-readable output.
Aligns with output-styles (agent-handoff.md, etc.) for consistent formatting.

Input: Raw JSON message from protocol layer OR notification data
Output: Formatted system message with metadata

Message Categories:
- TELEMETRY: Developer-facing metrics (safe to log)
- PROJECT_DATA: Inter-agent context (follows agent-handoff format)
- STATUS: User-visible notifications (emoji + short text)

Features:
- Auto-formats power mode messages into readable text
- Filters sensitive data (API keys, tokens, credentials)
- Logs to notification.json for history
- Optional TTS announcement
- Colorized emoji output

Part of Issue #189: Slack notification idle UI fix adaptation for PopKit
"""

import sys
import json
import re
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


# =============================================================================
# EMOJI MAP & COLORS
# =============================================================================

EMOJI_MAP = {
    # States
    "active": "🔵",
    "idle": "⏱",
    "busy": "🔄",
    "blocked": "⛔",
    "waiting": "⏳",
    "paused": "⏸",
    "error": "❌",
    "success": "✅",
    "warning": "⚠️",

    # Actions
    "start": "🚀",
    "handoff": "➜",
    "question": "❓",
    "discovery": "🔍",
    "blocker": "🚫",
    "pattern": "🎯",
    "docs": "📝",
    "metrics": "📊",
    "token": "💰",
    "time": "⏱",
    "agent": "🤖",
}


# =============================================================================
# MESSAGE CATEGORIZATION
# =============================================================================

class MessageCategory(Enum):
    """Message category for formatting decisions."""
    TELEMETRY = "telemetry"
    PROJECT_DATA = "project_data"
    STATUS = "status"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================

def format_duration(seconds: float) -> str:
    """Convert seconds to human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def sanitize_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from context."""
    sensitive_patterns = [
        r"UPSTASH_REDIS_REST_TOKEN",
        r"UPSTASH_VECTOR_REST_TOKEN",
        r"VOYAGER_API_KEY",
        r"api[_-]key",
        r"secret[_-]key",
        r"password",
        r"token",
        r"auth",
        r"\.env",
        r"credentials?",
    ]

    sanitized = {}
    for key, value in data.items():
        # Check if key matches sensitive pattern
        is_sensitive = any(
            re.search(pattern, key, re.IGNORECASE)
            for pattern in sensitive_patterns
        )

        if is_sensitive:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_context(value)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            sanitized[key] = [sanitize_context(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value

    return sanitized


def categorize_message(msg: Dict[str, Any]) -> MessageCategory:
    """Determine message category."""
    msg_type = msg.get("type", "")

    # Check if it's a power mode protocol message
    telemetry_types = {
        "HEARTBEAT", "PROGRESS", "BOUNDARY_ALERT", "DRIFT_ALERT",
        "SYNC_ACK", "AGENT_DOWN"
    }
    project_types = {
        "TASK", "INSIGHT", "QUERY", "RESPONSE", "OBJECTIVE_UPDATE",
        "COURSE_CORRECT", "RESULT"
    }
    status_types = {"HUMAN_REQUIRED", "STREAM_ERROR"}

    if msg_type in telemetry_types:
        return MessageCategory.TELEMETRY
    elif msg_type in project_types:
        return MessageCategory.PROJECT_DATA
    elif msg_type in status_types:
        return MessageCategory.STATUS
    elif msg.get("message") or msg.get("notification"):
        # Legacy notification format
        return MessageCategory.NOTIFICATION
    else:
        return MessageCategory.UNKNOWN


# =============================================================================
# TELEMETRY FORMATTERS
# =============================================================================

def format_heartbeat(msg: Dict[str, Any]) -> str:
    """Format agent heartbeat message."""
    payload = msg.get("payload", {})
    agent_id = msg.get("from_agent", "unknown")
    progress = payload.get("progress", 0)

    if progress >= 100:
        state_emoji = EMOJI_MAP["success"]
        state_text = "complete"
    elif progress > 0:
        state_emoji = EMOJI_MAP["busy"]
        state_text = f"{progress:.0f}%"
    else:
        state_emoji = EMOJI_MAP["idle"]
        state_text = "idle"

    return f"{state_emoji} {agent_id} ⎿ Status is {state_text}"


def format_progress(msg: Dict[str, Any]) -> str:
    """Format progress update message."""
    payload = msg.get("payload", {})
    agent_id = msg.get("from_agent", "unknown")
    progress = payload.get("progress", 0)
    tokens = payload.get("tokens_used", 0)

    output = f"{EMOJI_MAP['metrics']} {agent_id} ⎿ Progress {progress:.0f}%"
    if tokens > 0:
        output += f" ({tokens:,} tokens)"
    return output


def format_telemetry_message(msg: Dict[str, Any]) -> str:
    """Route to appropriate telemetry formatter."""
    msg_type = msg.get("type", "")

    if msg_type == "HEARTBEAT":
        return format_heartbeat(msg)
    elif msg_type == "PROGRESS":
        return format_progress(msg)
    else:
        agent = msg.get("from_agent", "system")
        return f"{EMOJI_MAP['metrics']} {agent} ⎿ {msg_type}"


# =============================================================================
# PROJECT DATA FORMATTERS
# =============================================================================

def format_project_data_message(msg: Dict[str, Any]) -> str:
    """Format project data message for inter-agent communication."""
    msg_type = msg.get("type", "")
    agent = msg.get("from_agent", "unknown")
    payload = msg.get("payload", {})

    if msg_type == "INSIGHT":
        insight_type = payload.get("type", "discovery")
        content = payload.get("content", "")
        type_emoji = {
            "discovery": EMOJI_MAP["discovery"],
            "blocker": EMOJI_MAP["blocker"],
            "pattern": EMOJI_MAP["pattern"],
            "question": EMOJI_MAP["question"],
        }.get(insight_type, EMOJI_MAP["discovery"])
        return f"{type_emoji} {agent} ⎿ {insight_type}: {content}"

    elif msg_type == "TASK":
        task = payload.get("description", "")
        return f"{EMOJI_MAP['start']} Task assigned to {agent} ⎿ {task}"

    elif msg_type == "RESULT":
        status = payload.get("status", "completed")
        status_emoji = {
            "completed": EMOJI_MAP["success"],
            "partial": EMOJI_MAP["warning"],
            "blocked": EMOJI_MAP["blocked"],
            "failed": EMOJI_MAP["error"],
        }.get(status, EMOJI_MAP["success"])
        return f"{status_emoji} {agent} ⎿ Handoff ({status})"

    else:
        return f"📋 {agent} ⎿ {msg_type}"


# =============================================================================
# STATUS FORMATTERS
# =============================================================================

def format_status_message(msg: Dict[str, Any]) -> str:
    """Format status message for user display."""
    payload = msg.get("payload", {})
    msg_type = msg.get("type", "")

    if msg_type == "HUMAN_REQUIRED":
        decision = payload.get("decision_needed", "")
        return f"{EMOJI_MAP['waiting']} Action needed ⎿ {decision}"
    else:
        return f"ℹ️  {msg_type}"


# =============================================================================
# DIRECTORY & LOGGING UTILITIES
# =============================================================================

def create_popkit_message_dir():
    """Create .popkit/messages directory for storing message history."""
    home = Path.home()
    msg_dir = home / ".popkit" / "messages"
    msg_dir.mkdir(parents=True, exist_ok=True)
    return msg_dir


def create_logs_directory():
    """Create logs directory if it doesn't exist (legacy support)."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def log_notification(data: Dict[str, Any], category: str = "general"):
    """Log notification data to JSON file."""
    # Modern: Store in .popkit/messages/
    try:
        msg_dir = create_popkit_message_dir()

        # Create category subdirectory
        category_dir = msg_dir / category
        category_dir.mkdir(exist_ok=True)

        # Store with timestamp-based filename
        timestamp = datetime.now().isoformat()
        safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
        log_file = category_dir / f"{safe_timestamp}.json"

        with open(log_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "category": category,
                "data": data
            }, f, indent=2)
    except Exception:
        pass  # Silent failure


def announce_notification(message):
    """Announce notification using TTS if available and requested."""
    try:
        # Windows TTS
        if os.name == 'nt':
            subprocess.run([
                'powershell', '-Command',
                f'Add-Type -AssemblyName System.Speech; '
                f'$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                f'$synth.Speak("{message}")'
            ], check=False, capture_output=True, timeout=5)
        # macOS TTS
        elif sys.platform == 'darwin':
            subprocess.run(
                ['say', message],
                check=False,
                capture_output=True,
                timeout=5
            )
    except Exception:
        pass  # Silent failure for TTS


# =============================================================================
# MAIN MESSAGE FORMATTER
# =============================================================================

def format_message(raw_msg: Dict[str, Any]) -> Dict[str, Any]:
    """Main formatter that routes to category-specific handlers."""

    # Determine category
    category = categorize_message(raw_msg)

    # Format based on category
    if category == MessageCategory.TELEMETRY:
        formatted_output = format_telemetry_message(raw_msg)
    elif category == MessageCategory.PROJECT_DATA:
        formatted_output = format_project_data_message(raw_msg)
    elif category == MessageCategory.STATUS:
        formatted_output = format_status_message(raw_msg)
    elif category == MessageCategory.NOTIFICATION:
        # Legacy notification format
        formatted_output = raw_msg.get("message", raw_msg.get("notification", "Notification"))
    else:
        # Fallback
        formatted_output = str(raw_msg.get("message", raw_msg.get("notification", "Unknown message")))

    # Sanitize sensitive data
    sanitized_payload = sanitize_context(raw_msg.get("payload", {}))

    # Build output message
    output = {
        "systemMessage": formatted_output,
        "metadata": {
            "source": "notification-formatter",
            "message_type": raw_msg.get("type", "NOTIFICATION"),
            "category": category.value,
            "timestamp": datetime.now().isoformat(),
        }
    }

    # Add agent info if present
    if raw_msg.get("from_agent"):
        output["metadata"]["agent"] = raw_msg.get("from_agent")

    return output


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the hook - JSON stdin/stdout protocol"""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        raw_msg = json.loads(input_data) if input_data.strip() else {}

        # Check if this is a power mode message or legacy notification
        if raw_msg.get("type") in {
            "HEARTBEAT", "PROGRESS", "INSIGHT", "TASK", "RESULT",
            "BOUNDARY_ALERT", "DRIFT_ALERT", "HUMAN_REQUIRED", "STREAM_ERROR"
        }:
            # Power mode protocol message - format it
            formatted = format_message(raw_msg)
            log_notification(formatted, category=formatted["metadata"]["category"])
        else:
            # Legacy notification format or pass-through
            formatted = {
                "systemMessage": raw_msg.get("message", raw_msg.get("notification", "Notification")),
                "metadata": {
                    "source": "notification-formatter",
                    "timestamp": datetime.now().isoformat(),
                    "tts_announced": raw_msg.get("notify", raw_msg.get("tts", False))
                }
            }
            log_notification(raw_msg, category="notification")

            # Check if TTS notification is requested
            if formatted["metadata"].get("tts_announced"):
                message = formatted["systemMessage"]
                announce_notification(message)

        # Output formatted message
        sys.stdout.write(json.dumps(formatted, indent=2))
        sys.stdout.flush()

    except json.JSONDecodeError as e:
        error_output = {
            "systemMessage": f"❌ Failed to parse notification: {str(e)}",
            "metadata": {
                "source": "formatter-error",
                "error": "json_decode_error",
                "timestamp": datetime.now().isoformat()
            }
        }
        sys.stdout.write(json.dumps(error_output, indent=2))
        sys.exit(0)  # Don't block on errors

    except Exception as e:
        error_output = {
            "systemMessage": f"❌ Notification formatter error: {str(e)}",
            "metadata": {
                "source": "formatter-error",
                "error": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        }
        sys.stdout.write(json.dumps(error_output, indent=2))
        print(f"Error in notification hook: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block on errors


if __name__ == "__main__":
    main()