#!/usr/bin/env python3
"""
TDD Cycle Tracker for PopKit.

Tracks RED-GREEN-REFACTOR cycles to ensure proper TDD discipline.
Part of pop-test-driven-development skill.

Usage:
    python tdd_cycle_tracker.py start <test_file>     # Start tracking a test
    python tdd_cycle_tracker.py red <test_file>       # Record RED phase (test fails)
    python tdd_cycle_tracker.py green <test_file>     # Record GREEN phase (test passes)
    python tdd_cycle_tracker.py refactor <test_file>  # Record REFACTOR phase
    python tdd_cycle_tracker.py status                # Show current cycle status
    python tdd_cycle_tracker.py report                # Generate summary report
"""

import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TDDPhase:
    """A single phase in the TDD cycle."""
    phase: str  # "red", "green", "refactor"
    test_file: str
    timestamp: str
    duration_seconds: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class TDDCycle:
    """A complete TDD cycle (RED -> GREEN -> REFACTOR)."""
    test_file: str
    started_at: str
    phases: List[TDDPhase] = field(default_factory=list)
    completed: bool = False
    violations: List[str] = field(default_factory=list)

    def current_phase(self) -> Optional[str]:
        """Get the current phase name."""
        if not self.phases:
            return None
        return self.phases[-1].phase

    def expected_next_phase(self) -> str:
        """What phase should come next."""
        current = self.current_phase()
        if current is None:
            return "red"
        elif current == "red":
            return "green"
        elif current == "green":
            return "refactor"
        else:
            return "red"  # Start new cycle


@dataclass
class TDDSession:
    """A TDD session with multiple cycles."""
    started_at: str
    cycles: List[TDDCycle] = field(default_factory=list)
    total_violations: int = 0

    def get_current_cycle(self, test_file: str) -> Optional[TDDCycle]:
        """Get the current incomplete cycle for a test file."""
        for cycle in reversed(self.cycles):
            if cycle.test_file == test_file and not cycle.completed:
                return cycle
        return None


STATE_FILE = Path(".popkit/tdd-state.json")


def load_session() -> TDDSession:
    """Load or create a TDD session."""
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        cycles = [
            TDDCycle(
                test_file=c["test_file"],
                started_at=c["started_at"],
                phases=[TDDPhase(**p) for p in c.get("phases", [])],
                completed=c.get("completed", False),
                violations=c.get("violations", [])
            )
            for c in data.get("cycles", [])
        ]
        return TDDSession(
            started_at=data["started_at"],
            cycles=cycles,
            total_violations=data.get("total_violations", 0)
        )
    return TDDSession(started_at=datetime.now().isoformat())


def save_session(session: TDDSession) -> None:
    """Save session state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "started_at": session.started_at,
        "total_violations": session.total_violations,
        "cycles": [
            {
                "test_file": c.test_file,
                "started_at": c.started_at,
                "completed": c.completed,
                "violations": c.violations,
                "phases": [asdict(p) for p in c.phases]
            }
            for c in session.cycles
        ]
    }
    STATE_FILE.write_text(json.dumps(data, indent=2))


def start_cycle(test_file: str) -> Dict[str, Any]:
    """Start a new TDD cycle for a test file."""
    session = load_session()

    # Check if there's an incomplete cycle
    existing = session.get_current_cycle(test_file)
    if existing:
        return {
            "success": False,
            "error": f"Incomplete cycle exists for {test_file}",
            "current_phase": existing.current_phase(),
            "expected_next": existing.expected_next_phase()
        }

    # Create new cycle
    cycle = TDDCycle(
        test_file=test_file,
        started_at=datetime.now().isoformat()
    )
    session.cycles.append(cycle)
    save_session(session)

    return {
        "success": True,
        "message": f"Started TDD cycle for {test_file}",
        "expected_next": "red"
    }


def record_phase(test_file: str, phase: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Record a TDD phase."""
    session = load_session()
    cycle = session.get_current_cycle(test_file)

    if not cycle:
        # Auto-start a cycle if none exists
        cycle = TDDCycle(
            test_file=test_file,
            started_at=datetime.now().isoformat()
        )
        session.cycles.append(cycle)

    # Check for violations
    expected = cycle.expected_next_phase()
    violation = None

    if phase != expected:
        violation = f"Expected {expected.upper()}, got {phase.upper()}"
        cycle.violations.append(violation)
        session.total_violations += 1

    # Record the phase
    now = datetime.now()
    duration = None
    if cycle.phases:
        last_time = datetime.fromisoformat(cycle.phases[-1].timestamp)
        duration = (now - last_time).total_seconds()

    cycle.phases.append(TDDPhase(
        phase=phase,
        test_file=test_file,
        timestamp=now.isoformat(),
        duration_seconds=duration,
        notes=notes
    ))

    # Check if cycle is complete
    if phase == "refactor":
        cycle.completed = True

    save_session(session)

    result = {
        "success": True,
        "phase": phase,
        "cycle_complete": cycle.completed,
        "expected_next": cycle.expected_next_phase() if not cycle.completed else "start new cycle"
    }

    if violation:
        result["violation"] = violation
        result["warning"] = "TDD discipline violated!"

    return result


def get_status() -> Dict[str, Any]:
    """Get current TDD status."""
    session = load_session()

    active_cycles = [c for c in session.cycles if not c.completed]
    completed_cycles = [c for c in session.cycles if c.completed]

    status = {
        "session_started": session.started_at,
        "total_cycles": len(session.cycles),
        "completed_cycles": len(completed_cycles),
        "active_cycles": len(active_cycles),
        "total_violations": session.total_violations
    }

    if active_cycles:
        current = active_cycles[-1]
        status["current"] = {
            "test_file": current.test_file,
            "phase": current.current_phase(),
            "expected_next": current.expected_next_phase(),
            "violations_in_cycle": len(current.violations)
        }

    return status


def generate_report() -> Dict[str, Any]:
    """Generate a summary report."""
    session = load_session()

    completed = [c for c in session.cycles if c.completed]

    # Calculate average cycle time
    cycle_times = []
    for cycle in completed:
        if len(cycle.phases) >= 3:
            start = datetime.fromisoformat(cycle.started_at)
            end = datetime.fromisoformat(cycle.phases[-1].timestamp)
            cycle_times.append((end - start).total_seconds())

    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0

    # Phase time analysis
    phase_times = {"red": [], "green": [], "refactor": []}
    for cycle in completed:
        for phase in cycle.phases:
            if phase.duration_seconds and phase.phase in phase_times:
                phase_times[phase.phase].append(phase.duration_seconds)

    avg_phase_times = {
        phase: sum(times) / len(times) if times else 0
        for phase, times in phase_times.items()
    }

    # Violation analysis
    all_violations = []
    for cycle in session.cycles:
        all_violations.extend(cycle.violations)

    return {
        "summary": {
            "total_cycles": len(session.cycles),
            "completed_cycles": len(completed),
            "completion_rate": len(completed) / len(session.cycles) * 100 if session.cycles else 0,
            "total_violations": session.total_violations,
            "discipline_score": max(0, 100 - session.total_violations * 10)
        },
        "timing": {
            "average_cycle_seconds": avg_cycle_time,
            "average_phase_seconds": avg_phase_times
        },
        "violations": {
            "count": len(all_violations),
            "details": all_violations[:10]  # Last 10
        }
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: tdd_cycle_tracker.py <command> [args]")
        print("Commands: start, red, green, refactor, status, report")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        if len(sys.argv) < 3:
            print("Usage: tdd_cycle_tracker.py start <test_file>")
            sys.exit(1)
        result = start_cycle(sys.argv[2])

    elif command in ("red", "green", "refactor"):
        if len(sys.argv) < 3:
            print(f"Usage: tdd_cycle_tracker.py {command} <test_file>")
            sys.exit(1)
        notes = sys.argv[3] if len(sys.argv) > 3 else None
        result = record_phase(sys.argv[2], command, notes)

    elif command == "status":
        result = get_status()

    elif command == "report":
        result = generate_report()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

    # Exit with error if there was a violation
    if isinstance(result, dict) and result.get("violation"):
        sys.exit(1)


if __name__ == "__main__":
    main()
