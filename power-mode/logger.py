#!/usr/bin/env python3
"""
Power Mode Session Logger (Issue #66)

Logs Power Mode session activity to files for debugging and visibility.

Features:
- Session-specific log files
- Structured JSON entries
- Log rotation (keeps last 10 sessions)
- Quick access to recent events

Log location: ~/.claude/power-mode/logs/<session_id>.log
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_DIR = Path.home() / ".claude" / "power-mode" / "logs"
MAX_SESSIONS = 10  # Keep last N session logs
MAX_LOG_SIZE_MB = 5  # Max size per log file


# =============================================================================
# LOG ENTRY
# =============================================================================

@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    level: str = "INFO"
    event_type: str = "general"
    agent_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary."""
        return cls(**d)


# =============================================================================
# SESSION LOGGER
# =============================================================================

class SessionLogger:
    """
    Logs Power Mode session activity to files.

    Usage:
        logger = SessionLogger(session_id)
        logger.info("agent-1", "Starting exploration phase")
        logger.checkin("agent-1", {"progress": 0.5, "files_touched": ["src/api.ts"]})
        logger.error("agent-2", "Failed to connect to database")
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log_file = LOG_DIR / f"{session_id}.log"
        self._ensure_log_dir()
        self._rotate_old_logs()

    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _rotate_old_logs(self):
        """Remove old session logs, keeping only MAX_SESSIONS."""
        try:
            log_files = sorted(
                LOG_DIR.glob("*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            # Keep only the most recent logs
            for old_log in log_files[MAX_SESSIONS:]:
                old_log.unlink()
        except Exception:
            pass  # Best effort cleanup

    def _write_entry(self, entry: LogEntry):
        """Write a log entry to file."""
        try:
            # Check file size
            if self.log_file.exists():
                size_mb = self.log_file.stat().st_size / (1024 * 1024)
                if size_mb >= MAX_LOG_SIZE_MB:
                    # Truncate to last 1000 lines
                    lines = self.log_file.read_text().splitlines()[-1000:]
                    self.log_file.write_text('\n'.join(lines) + '\n')

            # Append entry
            with open(self.log_file, 'a') as f:
                f.write(entry.to_json() + '\n')
        except Exception as e:
            # Don't fail silently but don't crash either
            print(f"Warning: Failed to write log entry: {e}", file=sys.stderr)

    def info(self, agent_id: str, message: str, details: Dict = None):
        """Log an info message."""
        entry = LogEntry(
            level="INFO",
            event_type="info",
            agent_id=agent_id,
            message=message,
            details=details or {}
        )
        self._write_entry(entry)

    def debug(self, agent_id: str, message: str, details: Dict = None):
        """Log a debug message."""
        entry = LogEntry(
            level="DEBUG",
            event_type="debug",
            agent_id=agent_id,
            message=message,
            details=details or {}
        )
        self._write_entry(entry)

    def warning(self, agent_id: str, message: str, details: Dict = None):
        """Log a warning message."""
        entry = LogEntry(
            level="WARNING",
            event_type="warning",
            agent_id=agent_id,
            message=message,
            details=details or {}
        )
        self._write_entry(entry)

    def error(self, agent_id: str, message: str, details: Dict = None):
        """Log an error message."""
        entry = LogEntry(
            level="ERROR",
            event_type="error",
            agent_id=agent_id,
            message=message,
            details=details or {}
        )
        self._write_entry(entry)

    def checkin(self, agent_id: str, state: Dict):
        """Log an agent check-in."""
        entry = LogEntry(
            level="INFO",
            event_type="checkin",
            agent_id=agent_id,
            message=f"Agent check-in: {state.get('current_task', 'no task')}",
            details={
                "progress": state.get("progress", 0),
                "tool_call_count": state.get("tool_call_count", 0),
                "files_touched": state.get("files_touched", [])[-5:],  # Last 5
                "tools_used": state.get("tools_used", [])
            }
        )
        self._write_entry(entry)

    def insight(self, agent_id: str, insight: Dict):
        """Log an insight shared or received."""
        entry = LogEntry(
            level="INFO",
            event_type="insight",
            agent_id=agent_id,
            message=f"Insight: {insight.get('content', '')[:100]}",
            details={
                "insight_type": insight.get("type"),
                "confidence": insight.get("confidence"),
                "relevance_tags": insight.get("relevance_tags", [])
            }
        )
        self._write_entry(entry)

    def phase_change(self, phase_name: str, phase_index: int, total_phases: int):
        """Log a phase transition."""
        entry = LogEntry(
            level="INFO",
            event_type="phase_change",
            agent_id="coordinator",
            message=f"Phase transition: {phase_name} ({phase_index}/{total_phases})",
            details={
                "phase_name": phase_name,
                "phase_index": phase_index,
                "total_phases": total_phases
            }
        )
        self._write_entry(entry)

    def bug_detected(self, agent_id: str, bug: Dict):
        """Log a bug detection."""
        entry = LogEntry(
            level="WARNING",
            event_type="bug_detected",
            agent_id=agent_id,
            message=f"Bug detected: {bug.get('error_type', 'unknown')}",
            details=bug
        )
        self._write_entry(entry)

    def session_start(self, objective: str, agents: List[str]):
        """Log session start."""
        entry = LogEntry(
            level="INFO",
            event_type="session_start",
            agent_id="coordinator",
            message=f"Power Mode started: {objective[:100]}",
            details={
                "objective": objective,
                "agents": agents,
                "session_id": self.session_id
            }
        )
        self._write_entry(entry)

    def session_end(self, summary: Dict):
        """Log session end."""
        entry = LogEntry(
            level="INFO",
            event_type="session_end",
            agent_id="coordinator",
            message="Power Mode ended",
            details=summary
        )
        self._write_entry(entry)

    def get_recent_entries(self, count: int = 50) -> List[Dict]:
        """Get recent log entries.

        Args:
            count: Number of entries to return

        Returns:
            List of log entry dicts, most recent first
        """
        if not self.log_file.exists():
            return []

        try:
            lines = self.log_file.read_text().splitlines()[-count:]
            entries = []
            for line in reversed(lines):
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except Exception:
            return []

    def get_errors(self) -> List[Dict]:
        """Get all error entries from current session.

        Returns:
            List of error entry dicts
        """
        if not self.log_file.exists():
            return []

        try:
            errors = []
            for line in self.log_file.read_text().splitlines():
                try:
                    entry = json.loads(line)
                    if entry.get("level") in ("ERROR", "WARNING"):
                        errors.append(entry)
                except json.JSONDecodeError:
                    continue
            return errors
        except Exception:
            return []


# =============================================================================
# GLOBAL LOGGER ACCESS
# =============================================================================

_session_logger: Optional[SessionLogger] = None


def get_logger(session_id: Optional[str] = None) -> Optional[SessionLogger]:
    """Get or create the session logger.

    Args:
        session_id: Session ID (required on first call)

    Returns:
        SessionLogger instance or None if not initialized
    """
    global _session_logger

    if session_id:
        _session_logger = SessionLogger(session_id)

    return _session_logger


def log_info(agent_id: str, message: str, details: Dict = None):
    """Convenience function to log info if logger is available."""
    if _session_logger:
        _session_logger.info(agent_id, message, details)


def log_error(agent_id: str, message: str, details: Dict = None):
    """Convenience function to log error if logger is available."""
    if _session_logger:
        _session_logger.error(agent_id, message, details)


def log_checkin(agent_id: str, state: Dict):
    """Convenience function to log check-in if logger is available."""
    if _session_logger:
        _session_logger.checkin(agent_id, state)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for viewing session logs."""
    import argparse

    parser = argparse.ArgumentParser(description="Power Mode Session Logger")
    parser.add_argument("session_id", nargs="?", help="Session ID to view")
    parser.add_argument("--list", "-l", action="store_true", help="List recent sessions")
    parser.add_argument("--tail", "-t", type=int, default=20, help="Number of entries to show")
    parser.add_argument("--errors", "-e", action="store_true", help="Show only errors")

    args = parser.parse_args()

    if args.list:
        # List recent sessions
        if not LOG_DIR.exists():
            print("No session logs found.")
            return

        log_files = sorted(
            LOG_DIR.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not log_files:
            print("No session logs found.")
            return

        print("\nRecent Power Mode Sessions:")
        print("-" * 60)
        for log_file in log_files[:10]:
            session_id = log_file.stem
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            size_kb = log_file.stat().st_size / 1024
            print(f"  {session_id}  {mtime.strftime('%Y-%m-%d %H:%M')}  {size_kb:.1f}KB")
        print()
        return

    if not args.session_id:
        # Try to find most recent session
        if not LOG_DIR.exists():
            print("No session logs found. Specify a session ID.")
            return

        log_files = sorted(
            LOG_DIR.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not log_files:
            print("No session logs found.")
            return

        args.session_id = log_files[0].stem
        print(f"Using most recent session: {args.session_id}\n")

    logger = SessionLogger(args.session_id)

    if args.errors:
        errors = logger.get_errors()
        if not errors:
            print("No errors in this session.")
            return

        print(f"\nErrors in session {args.session_id}:")
        print("-" * 60)
        for entry in errors:
            print(f"[{entry['timestamp'][:19]}] {entry['level']}: {entry['message']}")
            if entry.get('details'):
                for k, v in entry['details'].items():
                    print(f"  {k}: {v}")
        return

    entries = logger.get_recent_entries(args.tail)
    if not entries:
        print(f"No log entries for session {args.session_id}")
        return

    print(f"\nRecent activity in session {args.session_id}:")
    print("-" * 60)
    for entry in reversed(entries):  # Chronological order
        time_str = entry['timestamp'][11:19]  # HH:MM:SS
        level = entry['level'][:4]
        agent = entry.get('agent_id', '?')[:10]
        message = entry['message'][:60]
        print(f"[{time_str}] {level:4} {agent:10} {message}")


if __name__ == "__main__":
    main()
