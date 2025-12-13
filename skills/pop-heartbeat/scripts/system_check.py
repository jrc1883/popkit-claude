#!/usr/bin/env python3
"""
System Health Check Script.

Monitor session health, detect stuck patterns, and report status.

Usage:
    python system_check.py [--mode MODE] [--session SESSION]

Modes:
    status - Current session status
    stuck  - Stuck detection analysis
    beat   - Record heartbeat
    list   - List all sessions

Output:
    JSON object with session health status
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_heartbeat_dir() -> Path:
    """Get heartbeat storage directory."""
    home = Path(os.path.expanduser("~"))
    return home / ".claude" / "popkit" / "heartbeats"


def get_current_session_id() -> str:
    """Get or generate current session ID."""
    session_file = get_heartbeat_dir() / "current_session.txt"
    if session_file.exists():
        return session_file.read_text().strip()

    # Generate new session ID
    session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)
    return session_id


def load_session_state(session_id: str) -> Dict[str, Any]:
    """Load session state from storage."""
    state_file = get_heartbeat_dir() / session_id / "session_state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())

    return {
        "session_id": session_id,
        "started": datetime.now().isoformat(),
        "status": "active",
        "tool_calls": 0,
        "files_touched": [],
        "heartbeats": [],
        "recent_edits": []
    }


def save_session_state(session_id: str, state: Dict[str, Any]) -> None:
    """Save session state to storage."""
    session_dir = get_heartbeat_dir() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    state_file = session_dir / "session_state.json"
    state_file.write_text(json.dumps(state, indent=2))


def record_heartbeat(session_id: str, progress: Optional[str] = None) -> Dict[str, Any]:
    """Record a heartbeat for the session."""
    state = load_session_state(session_id)

    heartbeat = {
        "timestamp": datetime.now().isoformat(),
        "tool_calls": state.get("tool_calls", 0),
        "files_touched": len(state.get("files_touched", [])),
        "progress": progress
    }

    # Append to heartbeats
    state["heartbeats"].append(heartbeat)

    # Update latest heartbeat
    state["last_heartbeat"] = datetime.now().isoformat()

    save_session_state(session_id, state)

    # Also append to heartbeats.jsonl
    session_dir = get_heartbeat_dir() / session_id
    heartbeats_file = session_dir / "heartbeats.jsonl"
    with open(heartbeats_file, "a") as f:
        f.write(json.dumps(heartbeat) + "\n")

    return heartbeat


def detect_stuck_patterns(session_id: str) -> Dict[str, Any]:
    """Detect stuck patterns in the session."""
    state = load_session_state(session_id)

    result = {
        "is_stuck": False,
        "confidence": 0.0,
        "indicators": [],
        "recommendations": []
    }

    # Check 1: Heartbeat age (no heartbeat for 3+ minutes)
    if state.get("last_heartbeat"):
        try:
            last_hb = datetime.fromisoformat(state["last_heartbeat"])
            age_minutes = (datetime.now() - last_hb).total_seconds() / 60
            if age_minutes >= 3:
                result["confidence"] += 0.4
                result["indicators"].append({
                    "type": "heartbeat_age",
                    "message": f"No heartbeat for {int(age_minutes)} minutes",
                    "severity": "warning"
                })
        except Exception:
            pass

    # Check 2: Repeated edits (same file edited 5+ times)
    recent_edits = state.get("recent_edits", [])
    file_counts = {}
    for edit in recent_edits:
        path = edit.get("file", "")
        file_counts[path] = file_counts.get(path, 0) + 1

    for file_path, count in file_counts.items():
        if count >= 5:
            result["confidence"] += 0.2
            result["indicators"].append({
                "type": "repeated_edits",
                "message": f"File '{file_path}' edited {count} times",
                "severity": "warning"
            })
            result["recommendations"].append(f"Step back from {file_path} - consider different approach")

    # Check 3: Circular edit pattern (A→B→A→B)
    if len(recent_edits) >= 4:
        edit_files = [e.get("file", "") for e in recent_edits[-10:]]
        for i in range(len(edit_files) - 3):
            if edit_files[i] == edit_files[i + 2] and edit_files[i + 1] == edit_files[i + 3]:
                if edit_files[i] != edit_files[i + 1]:
                    result["confidence"] += 0.3
                    result["indicators"].append({
                        "type": "circular_edits",
                        "message": f"Circular edit pattern detected ({edit_files[i]} → {edit_files[i+1]} → {edit_files[i]} → {edit_files[i+1]})",
                        "severity": "warning"
                    })
                    result["recommendations"].append("Breaking circular pattern - try different approach")
                    break

    # Determine stuck status
    result["is_stuck"] = result["confidence"] >= 0.5

    if result["is_stuck"] and not result["recommendations"]:
        result["recommendations"].append("Consider creating a checkpoint before continuing")
        result["recommendations"].append("Review recent changes: git diff HEAD~5")
        result["recommendations"].append("Consider asking for help or taking a break")

    return result


def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get current session status."""
    state = load_session_state(session_id)

    # Calculate duration
    started = state.get("started", datetime.now().isoformat())
    try:
        start_dt = datetime.fromisoformat(started)
        duration_seconds = (datetime.now() - start_dt).total_seconds()
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        if hours > 0:
            duration = f"{hours}h {minutes}m"
        else:
            duration = f"{minutes}m"
    except Exception:
        duration = "unknown"

    # Run stuck detection
    stuck = detect_stuck_patterns(session_id)

    status = "active"
    emoji = "🟢"
    if stuck["is_stuck"]:
        status = "stuck"
        emoji = "🔴"
    elif len(state.get("heartbeats", [])) == 0:
        status = "idle"
        emoji = "🟡"

    return {
        "session_id": session_id,
        "status": status,
        "emoji": emoji,
        "duration": duration,
        "tool_calls": state.get("tool_calls", 0),
        "files_touched": len(state.get("files_touched", [])),
        "last_heartbeat": state.get("last_heartbeat"),
        "started": started,
        "stuck_detection": stuck,
        "status_line": f"[POP] {duration} | {emoji} {state.get('tool_calls', 0)} calls | {len(state.get('files_touched', []))} files"
    }


def list_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """List all sessions."""
    sessions = []
    heartbeat_dir = get_heartbeat_dir()

    if not heartbeat_dir.exists():
        return sessions

    for session_dir in sorted(heartbeat_dir.iterdir(), reverse=True):
        if session_dir.is_dir() and session_dir.name.startswith("session-"):
            state_file = session_dir / "session_state.json"
            if state_file.exists():
                try:
                    state = json.loads(state_file.read_text())
                    sessions.append({
                        "session_id": state.get("session_id", session_dir.name),
                        "status": state.get("status", "unknown"),
                        "started": state.get("started"),
                        "last_heartbeat": state.get("last_heartbeat"),
                        "tool_calls": state.get("tool_calls", 0)
                    })
                except Exception:
                    pass

        if len(sessions) >= limit:
            break

    return sessions


def generate_status_report(status: Dict[str, Any]) -> str:
    """Generate formatted status report."""
    lines = [
        "Session Health Check",
        "====================",
        "",
        status["status_line"],
        "",
        f"Status: {status['status'].title()} ({'Healthy' if not status['stuck_detection']['is_stuck'] else 'Issues Detected'})",
        f"Started: {status['started']}",
        f"Tool Calls: {status['tool_calls']}",
        f"Files Modified: {status['files_touched']}",
        "",
        "Recent Activity:",
        f"  - Last heartbeat: {status.get('last_heartbeat', 'none')}",
    ]

    if status["stuck_detection"]["indicators"]:
        lines.append("")
        lines.append("Stuck Indicators:")
        for indicator in status["stuck_detection"]["indicators"]:
            lines.append(f"  ⚠️ {indicator['message']}")

    if status["stuck_detection"]["recommendations"]:
        lines.append("")
        lines.append("Recommendations:")
        for i, rec in enumerate(status["stuck_detection"]["recommendations"], 1):
            lines.append(f"  {i}. {rec}")

    if not status["stuck_detection"]["indicators"]:
        lines.append("")
        lines.append("No stuck indicators detected.")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="System health check")
    parser.add_argument("--mode", choices=["status", "stuck", "beat", "list"],
                        default="status", help="Operation mode")
    parser.add_argument("--session", "-s", help="Session ID (default: current)")
    parser.add_argument("--progress", "-p", help="Progress description (for beat)")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    parser.add_argument("--limit", type=int, default=10, help="Max sessions to list")
    args = parser.parse_args()

    session_id = args.session or get_current_session_id()

    result = {
        "operation": f"system_check_{args.mode}",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }

    if args.mode == "status":
        status = get_session_status(session_id)
        result["status"] = status

        if args.format == "display":
            print(generate_status_report(status))
            return 0

    elif args.mode == "stuck":
        stuck = detect_stuck_patterns(session_id)
        result["stuck_detection"] = stuck

    elif args.mode == "beat":
        heartbeat = record_heartbeat(session_id, args.progress)
        result["heartbeat"] = heartbeat

    elif args.mode == "list":
        sessions = list_sessions(args.limit)
        result["sessions"] = sessions

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
