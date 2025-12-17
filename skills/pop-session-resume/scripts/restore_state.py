#!/usr/bin/env python3
"""
Session State Restore Script.

Restore session state from STATUS.json.

Usage:
    python restore_state.py [--mode MODE] [--status-path PATH]

Modes:
    find       - Find STATUS.json in expected locations
    parse      - Parse STATUS.json and validate structure
    verify-git - Verify git state matches saved state
    summary    - Generate session summary
    all        - Full restore process

Output:
    JSON object with restored state and session type
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def run_command(cmd: str, timeout: int = 30) -> Tuple[str, bool]:
    """Run a shell command and return output and success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.returncode == 0
    except subprocess.TimeoutExpired:
        return "Command timed out", False
    except Exception as e:
        return str(e), False


def find_status_file() -> Optional[Path]:
    """Find STATUS.json in expected locations."""
    locations = [
        Path(".claude/STATUS.json"),
        Path("STATUS.json"),
        Path.home() / ".claude" / "STATUS.json"
    ]

    for path in locations:
        if path.exists():
            return path

    return None


def parse_status_file(path: Path) -> Dict[str, Any]:
    """Parse STATUS.json and return contents."""
    content = path.read_text()
    return json.loads(content)


def calculate_session_type(last_update: str) -> Dict[str, Any]:
    """Calculate session type based on time since last update."""
    try:
        # Parse the timestamp
        if last_update.endswith('Z'):
            last_update = last_update[:-1] + '+00:00'
        last_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
        now = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()

        # Calculate hours since
        delta = now - last_dt.replace(tzinfo=None) if not last_dt.tzinfo else now - last_dt
        hours_since = delta.total_seconds() / 3600

        if hours_since < 0.5:
            session_type = "Continuation"
            behavior = "Quick restore, assume full context"
        elif hours_since < 4:
            session_type = "Resume"
            behavior = "Restore context, brief refresh"
        else:
            session_type = "Fresh Start"
            behavior = "Full context load, verify state"

        # Format time since
        if hours_since < 1:
            time_since = f"{int(hours_since * 60)} minutes ago"
        elif hours_since < 24:
            time_since = f"{int(hours_since)} hours ago"
        else:
            days = int(hours_since / 24)
            time_since = f"{days} day{'s' if days > 1 else ''} ago"

        return {
            "session_type": session_type,
            "hours_since": round(hours_since, 2),
            "time_since": time_since,
            "behavior": behavior
        }
    except Exception as e:
        return {
            "session_type": "Fresh Start",
            "hours_since": -1,
            "time_since": "unknown",
            "behavior": "Full context load, verify state",
            "error": str(e)
        }


def verify_git_state(saved_git: Dict[str, Any]) -> Dict[str, Any]:
    """Verify current git state matches saved state."""
    verification = {
        "matches": True,
        "discrepancies": []
    }

    # Check branch
    current_branch, ok = run_command("git branch --show-current")
    if ok:
        if current_branch != saved_git.get("branch", ""):
            verification["matches"] = False
            verification["discrepancies"].append({
                "field": "branch",
                "saved": saved_git.get("branch"),
                "current": current_branch
            })

    # Check uncommitted files count
    status, ok = run_command("git status --porcelain")
    if ok:
        current_uncommitted = len([l for l in status.split('\n') if l.strip()])
        saved_uncommitted = saved_git.get("uncommittedFiles", 0)

        if current_uncommitted != saved_uncommitted:
            verification["matches"] = False
            verification["discrepancies"].append({
                "field": "uncommittedFiles",
                "saved": saved_uncommitted,
                "current": current_uncommitted
            })

    # Check last commit
    commit, ok = run_command("git log -1 --format='%h - %s'")
    if ok:
        if commit != saved_git.get("lastCommit", ""):
            verification["discrepancies"].append({
                "field": "lastCommit",
                "saved": saved_git.get("lastCommit"),
                "current": commit,
                "note": "New commits since last session"
            })

    verification["current_git"] = {
        "branch": current_branch if ok else "unknown",
        "uncommittedFiles": current_uncommitted if ok else -1,
        "lastCommit": commit if ok else "unknown"
    }

    return verification


def generate_summary(status: Dict[str, Any], session_info: Dict[str, Any], verification: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate session summary for display."""
    summary = {
        "session_type": session_info["session_type"],
        "time_since": session_info["time_since"],
        "project": status.get("project", "unknown"),
        "git": {
            "branch": status.get("git", {}).get("branch", "unknown"),
            "uncommitted": status.get("git", {}).get("uncommittedFiles", 0),
            "lastCommit": status.get("git", {}).get("lastCommit", "unknown")
        },
        "tasks": {
            "inProgress": status.get("tasks", {}).get("inProgress", []),
            "completed": status.get("tasks", {}).get("completed", [])[:3],  # Last 3
            "blocked": status.get("tasks", {}).get("blocked", [])
        },
        "context": {
            "focusArea": status.get("context", {}).get("focusArea", ""),
            "nextAction": status.get("context", {}).get("nextAction", ""),
            "blocker": status.get("context", {}).get("blocker"),
            "keyDecisions": status.get("context", {}).get("keyDecisions", [])
        },
        "projectData": status.get("projectData", {}),
        "options": [
            {"label": "Continue with next action", "value": "continue"},
            {"label": "Review full context first", "value": "review"},
            {"label": "Start fresh", "value": "fresh"}
        ]
    }

    if verification:
        summary["verification"] = verification

    return summary


def format_display_box(summary: Dict[str, Any]) -> str:
    """Format summary as display box."""
    session_emoji = {
        "Continuation": "⚡",
        "Resume": "🔄",
        "Fresh Start": "🌅"
    }

    emoji = session_emoji.get(summary["session_type"], "📋")

    lines = [
        f"┌─────────────────────────────────────────────┐",
        f"│ {emoji} {summary['session_type']} Session{' ' * (30 - len(summary['session_type']))}│",
        f"│ Last: {summary['time_since']}{' ' * (36 - len(summary['time_since']))}│",
        f"├─────────────────────────────────────────────┤",
        f"│ Branch: {summary['git']['branch'][:30]}{' ' * (34 - min(30, len(summary['git']['branch'])))}│",
        f"│ Uncommitted: {summary['git']['uncommitted']} files{' ' * 24}│",
    ]

    if summary["tasks"]["inProgress"]:
        lines.append(f"├─────────────────────────────────────────────┤")
        lines.append(f"│ In Progress:                                │")
        for task in summary["tasks"]["inProgress"][:3]:
            task_short = task[:38]
            lines.append(f"│ • {task_short}{' ' * (40 - len(task_short))}│")

    if summary["context"]["nextAction"]:
        lines.append(f"├─────────────────────────────────────────────┤")
        lines.append(f"│ Next Action:                                │")
        next_action = summary["context"]["nextAction"][:38]
        lines.append(f"│ {next_action}{' ' * (42 - len(next_action))}│")

    lines.append(f"└─────────────────────────────────────────────┘")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Restore session state")
    parser.add_argument("--mode", choices=["find", "parse", "verify-git", "summary", "all"],
                        default="all", help="Operation mode")
    parser.add_argument("--status-path", help="Path to STATUS.json")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    args = parser.parse_args()

    result = {
        "operation": "restore_state",
        "mode": args.mode,
        "timestamp": datetime.now().isoformat()
    }

    # Find STATUS.json
    if args.status_path:
        status_path = Path(args.status_path)
    else:
        status_path = find_status_file()

    if args.mode == "find":
        if status_path and status_path.exists():
            result["found"] = True
            result["path"] = str(status_path)
        else:
            result["found"] = False
            result["searched"] = [
                ".claude/STATUS.json",
                "STATUS.json",
                "~/.claude/STATUS.json"
            ]
        print(json.dumps(result, indent=2))
        return 0 if result.get("found") else 1

    if not status_path or not status_path.exists():
        result["success"] = False
        result["error"] = "STATUS.json not found"
        print(json.dumps(result, indent=2))
        return 1

    result["status_path"] = str(status_path)

    # Parse STATUS.json
    try:
        status = parse_status_file(status_path)
        result["status"] = status
    except json.JSONDecodeError as e:
        result["success"] = False
        result["error"] = f"Invalid JSON: {e}"
        print(json.dumps(result, indent=2))
        return 1

    if args.mode == "parse":
        result["success"] = True
        print(json.dumps(result, indent=2))
        return 0

    # Calculate session type
    session_info = calculate_session_type(status.get("lastUpdate", ""))
    result["session_info"] = session_info

    # Verify git state
    verification = None
    if args.mode in ["verify-git", "all"] and session_info["session_type"] == "Fresh Start":
        verification = verify_git_state(status.get("git", {}))
        result["verification"] = verification

    # Generate summary
    if args.mode in ["summary", "all"]:
        summary = generate_summary(status, session_info, verification)
        result["summary"] = summary

        if args.format == "display":
            print(format_display_box(summary))
            return 0

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
