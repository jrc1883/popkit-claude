#!/usr/bin/env python3
"""
Heartbeat Monitor

Part of Issue #94 (Long Horizon Agent Patterns Integration)

Monitors session health through periodic heartbeats.
Detects stuck sessions, tracks progress, and enables recovery.

Based on patterns from Anthropic's Long Horizon Coding Agent Demo.
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

HEARTBEAT_DIR = Path.home() / ".claude" / "popkit" / "heartbeats"
HEARTBEAT_INTERVAL = 30  # seconds
STUCK_THRESHOLD = 180  # 3 minutes without heartbeat = stuck
MAX_SAME_FILE_EDITS = 5  # Same file edited 5+ times = potentially stuck


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class HeartbeatData:
    """Single heartbeat record."""
    timestamp: str
    session_id: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    status: str = "active"  # active, stuck, recovering, completed
    progress: Optional[str] = None


@dataclass
class SessionHealth:
    """Health indicators for a session."""
    session_id: str
    status: str  # active, stuck, idle, completed
    last_heartbeat: str
    duration_seconds: int
    tool_calls: int
    files_touched: List[str] = field(default_factory=list)
    stuck_indicators: List[str] = field(default_factory=list)
    memory_usage: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """Check if session is healthy."""
        return self.status == "active" and len(self.stuck_indicators) == 0

    @property
    def duration_formatted(self) -> str:
        """Format duration as human-readable string."""
        minutes = self.duration_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


@dataclass
class StuckDetectionResult:
    """Result of stuck detection analysis."""
    is_stuck: bool
    confidence: float  # 0.0 to 1.0
    indicators: List[str]
    recommendations: List[str]


# =============================================================================
# HEARTBEAT MONITOR
# =============================================================================

class HeartbeatMonitor:
    """
    Monitors session health through heartbeats.

    Features:
    - Periodic heartbeat recording
    - Stuck session detection
    - Progress tracking
    - Recovery suggestions
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize monitor for a session."""
        self.session_id = session_id or self._generate_session_id()
        self.session_dir = HEARTBEAT_DIR / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.heartbeats: List[HeartbeatData] = []
        self.start_time = datetime.now()
        self.tool_calls = 0
        self.files_touched: Dict[str, int] = {}  # file -> edit count

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"session-{timestamp}-{random_part}"

    def beat(
        self,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        progress: Optional[str] = None
    ) -> HeartbeatData:
        """
        Record a heartbeat.

        Args:
            tool_name: Name of tool being used
            tool_input: Tool input parameters
            progress: Human-readable progress description

        Returns:
            HeartbeatData record
        """
        self.tool_calls += 1

        # Track file touches
        if tool_name in ("Edit", "Write", "Read") and tool_input:
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.files_touched[file_path] = self.files_touched.get(file_path, 0) + 1

        heartbeat = HeartbeatData(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            tool_name=tool_name,
            tool_input={"file": tool_input.get("file_path")} if tool_input else None,
            status="active",
            progress=progress
        )

        self.heartbeats.append(heartbeat)
        self._save_heartbeat(heartbeat)

        return heartbeat

    def _save_heartbeat(self, heartbeat: HeartbeatData) -> None:
        """Save heartbeat to disk."""
        heartbeat_file = self.session_dir / "heartbeats.jsonl"
        with open(heartbeat_file, "a") as f:
            f.write(json.dumps(asdict(heartbeat)) + "\n")

        # Also update latest heartbeat for quick access
        latest_file = self.session_dir / "latest.json"
        with open(latest_file, "w") as f:
            json.dump(asdict(heartbeat), f)

    def get_health(self) -> SessionHealth:
        """
        Get current session health.

        Returns:
            SessionHealth with current indicators
        """
        now = datetime.now()
        duration = int((now - self.start_time).total_seconds())

        last_heartbeat = self.heartbeats[-1].timestamp if self.heartbeats else now.isoformat()

        # Detect stuck indicators
        stuck_indicators = []
        detection = self.detect_stuck()
        if detection.is_stuck:
            stuck_indicators = detection.indicators

        # Determine status
        if detection.is_stuck:
            status = "stuck"
        elif not self.heartbeats:
            status = "idle"
        else:
            status = "active"

        return SessionHealth(
            session_id=self.session_id,
            status=status,
            last_heartbeat=last_heartbeat,
            duration_seconds=duration,
            tool_calls=self.tool_calls,
            files_touched=list(self.files_touched.keys()),
            stuck_indicators=stuck_indicators
        )

    def detect_stuck(self) -> StuckDetectionResult:
        """
        Detect if session is stuck.

        Checks:
        - Time since last heartbeat
        - Same file edited repeatedly
        - Same tool called repeatedly with same input
        - Build/test failures in sequence

        Returns:
            StuckDetectionResult with analysis
        """
        indicators = []
        recommendations = []
        confidence = 0.0

        # Check heartbeat age
        if self.heartbeats:
            last_time = datetime.fromisoformat(self.heartbeats[-1].timestamp)
            age = (datetime.now() - last_time).total_seconds()
            if age > STUCK_THRESHOLD:
                indicators.append(f"No heartbeat for {int(age)}s (threshold: {STUCK_THRESHOLD}s)")
                confidence += 0.4
                recommendations.append("Session may have crashed - consider restarting")

        # Check repeated file edits
        for file_path, count in self.files_touched.items():
            if count >= MAX_SAME_FILE_EDITS:
                file_name = Path(file_path).name
                indicators.append(f"File '{file_name}' edited {count} times")
                confidence += 0.2
                recommendations.append(f"Consider stepping back from {file_name}")

        # Check for repeated failures (look at last 10 heartbeats)
        recent = self.heartbeats[-10:] if len(self.heartbeats) >= 10 else self.heartbeats
        bash_failures = sum(1 for h in recent if h.tool_name == "Bash" and "error" in str(h.progress or "").lower())
        if bash_failures >= 3:
            indicators.append(f"{bash_failures} Bash failures in recent calls")
            confidence += 0.3
            recommendations.append("Multiple command failures - review approach")

        # Check for circular edits (A -> B -> A -> B pattern)
        if len(self.heartbeats) >= 6:
            recent_files = [
                h.tool_input.get("file") for h in self.heartbeats[-6:]
                if h.tool_input and h.tool_input.get("file")
            ]
            if len(recent_files) >= 4:
                # Check for A-B-A-B pattern
                if recent_files[0] == recent_files[2] == recent_files[4] or \
                   recent_files[1] == recent_files[3] == recent_files[5]:
                    indicators.append("Circular edit pattern detected")
                    confidence += 0.3
                    recommendations.append("Breaking circular pattern - try different approach")

        is_stuck = confidence >= 0.5

        return StuckDetectionResult(
            is_stuck=is_stuck,
            confidence=min(confidence, 1.0),
            indicators=indicators,
            recommendations=recommendations
        )

    def format_status_line(self) -> str:
        """
        Format health as status line.

        Returns:
            Status line like: [POP] Session 45m | 🟢 127 calls | 5 files
        """
        health = self.get_health()

        # Status indicator
        status_emoji = {
            "active": "🟢",
            "stuck": "🔴",
            "idle": "🟡",
            "completed": "✅"
        }.get(health.status, "⚪")

        parts = [
            f"[POP] {health.duration_formatted}",
            f"{status_emoji} {health.tool_calls} calls",
            f"{len(health.files_touched)} files"
        ]

        if health.stuck_indicators:
            parts.append(f"⚠️ {len(health.stuck_indicators)} warnings")

        return " | ".join(parts)

    def save_session_state(self) -> str:
        """
        Save complete session state to disk.

        Returns:
            Path to saved state file
        """
        state = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "tool_calls": self.tool_calls,
            "files_touched": self.files_touched,
            "heartbeat_count": len(self.heartbeats),
            "health": asdict(self.get_health()),
            "saved_at": datetime.now().isoformat()
        }

        state_file = self.session_dir / "session_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        return str(state_file)

    @classmethod
    def load_session(cls, session_id: str) -> Optional["HeartbeatMonitor"]:
        """
        Load existing session from disk.

        Args:
            session_id: Session ID to load

        Returns:
            HeartbeatMonitor instance or None if not found
        """
        session_dir = HEARTBEAT_DIR / session_id

        if not session_dir.exists():
            return None

        monitor = cls(session_id)

        # Load heartbeats
        heartbeat_file = session_dir / "heartbeats.jsonl"
        if heartbeat_file.exists():
            with open(heartbeat_file) as f:
                for line in f:
                    data = json.loads(line)
                    monitor.heartbeats.append(HeartbeatData(**data))

        # Load state
        state_file = session_dir / "session_state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                monitor.start_time = datetime.fromisoformat(state["start_time"])
                monitor.tool_calls = state["tool_calls"]
                monitor.files_touched = state["files_touched"]

        return monitor

    @classmethod
    def list_sessions(cls, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        List all sessions.

        Args:
            include_completed: Include completed sessions

        Returns:
            List of session summaries
        """
        sessions = []

        if not HEARTBEAT_DIR.exists():
            return sessions

        for session_dir in HEARTBEAT_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            latest_file = session_dir / "latest.json"
            if latest_file.exists():
                with open(latest_file) as f:
                    latest = json.load(f)

                if not include_completed and latest.get("status") == "completed":
                    continue

                sessions.append({
                    "session_id": session_dir.name,
                    "last_heartbeat": latest.get("timestamp"),
                    "status": latest.get("status", "unknown")
                })

        # Sort by recency
        sessions.sort(key=lambda s: s["last_heartbeat"], reverse=True)

        return sessions


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_current_monitor: Optional[HeartbeatMonitor] = None


def get_monitor() -> HeartbeatMonitor:
    """Get or create the current session monitor."""
    global _current_monitor
    if _current_monitor is None:
        _current_monitor = HeartbeatMonitor()
    return _current_monitor


def beat(tool_name: str = None, tool_input: Dict = None, progress: str = None) -> HeartbeatData:
    """Convenience function to record heartbeat."""
    return get_monitor().beat(tool_name, tool_input, progress)


def get_health() -> SessionHealth:
    """Convenience function to get health."""
    return get_monitor().get_health()


def is_stuck() -> bool:
    """Convenience function to check if stuck."""
    return get_monitor().detect_stuck().is_stuck


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Heartbeat monitor")
    parser.add_argument("command", choices=["status", "list", "beat"], default="status", nargs="?")
    parser.add_argument("--session", "-s", help="Session ID")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")

    args = parser.parse_args()

    if args.command == "list":
        sessions = HeartbeatMonitor.list_sessions(include_completed=True)
        if args.json:
            print(json.dumps(sessions, indent=2))
        else:
            print(f"Sessions ({len(sessions)}):")
            for s in sessions[:10]:
                print(f"  {s['session_id']} - {s['status']} - {s['last_heartbeat']}")

    elif args.command == "status":
        if args.session:
            monitor = HeartbeatMonitor.load_session(args.session)
        else:
            monitor = get_monitor()

        if monitor:
            health = monitor.get_health()
            if args.json:
                print(json.dumps(asdict(health), indent=2))
            else:
                print(monitor.format_status_line())
                if health.stuck_indicators:
                    print("\nWarnings:")
                    for ind in health.stuck_indicators:
                        print(f"  ⚠️ {ind}")
        else:
            print("No session found")

    elif args.command == "beat":
        monitor = get_monitor()
        heartbeat = monitor.beat()
        print(f"Heartbeat recorded: {heartbeat.timestamp}")
