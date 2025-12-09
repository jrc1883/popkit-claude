#!/usr/bin/env python3
"""
Power Mode Metrics - Quantifiable value proposition (#108)

Tracks time savings, quality improvements, and coordination benefits
to demonstrate the value of multi-agent orchestration.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class MetricType(Enum):
    """Categories of metrics we track."""
    TIME = "time"
    QUALITY = "quality"
    COORDINATION = "coordination"
    RESOURCE = "resource"


@dataclass
class TimingMetric:
    """Track time-based metrics."""
    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    phase: Optional[str] = None
    agent_id: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def duration_formatted(self) -> str:
        """Get human-readable duration."""
        secs = self.duration_seconds
        if secs < 60:
            return f"{secs:.1f}s"
        elif secs < 3600:
            return f"{secs/60:.1f}m"
        else:
            return f"{secs/3600:.1f}h"


@dataclass
class QualityMetric:
    """Track quality-based metrics."""
    name: str
    value: float
    max_value: float = 100.0
    phase: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def percentage(self) -> float:
        """Get value as percentage."""
        return (self.value / self.max_value) * 100 if self.max_value > 0 else 0


@dataclass
class CoordinationMetric:
    """Track coordination-based metrics."""
    name: str
    count: int = 0
    total_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def average_time(self) -> float:
        """Get average time per event."""
        return self.total_time_seconds / self.count if self.count > 0 else 0


@dataclass
class SessionMetrics:
    """All metrics for a Power Mode session."""
    session_id: str
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    # Time metrics
    phase_times: Dict[str, TimingMetric] = field(default_factory=dict)
    task_times: Dict[str, TimingMetric] = field(default_factory=dict)
    agent_active_times: Dict[str, float] = field(default_factory=dict)

    # Quality metrics
    code_review_scores: List[float] = field(default_factory=list)
    test_coverage_start: float = 0.0
    test_coverage_end: float = 0.0
    bugs_detected: int = 0
    rework_count: int = 0

    # Coordination metrics
    insights_shared: int = 0
    context_reuses: int = 0
    sync_barrier_waits: List[float] = field(default_factory=list)
    conflicts_resolved: int = 0

    # Resource metrics
    total_tokens: int = 0
    agent_count: int = 0
    peak_concurrent_agents: int = 0

    @property
    def total_duration_seconds(self) -> float:
        """Total session duration."""
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def average_code_review_score(self) -> float:
        """Average confidence score from code reviews."""
        return sum(self.code_review_scores) / len(self.code_review_scores) if self.code_review_scores else 0

    @property
    def test_coverage_delta(self) -> float:
        """Change in test coverage."""
        return self.test_coverage_end - self.test_coverage_start

    @property
    def first_pass_success_rate(self) -> float:
        """Percentage of tasks completed without rework."""
        total_tasks = len(self.task_times)
        if total_tasks == 0:
            return 100.0
        return ((total_tasks - self.rework_count) / total_tasks) * 100

    @property
    def average_sync_wait(self) -> float:
        """Average time spent waiting at sync barriers."""
        return sum(self.sync_barrier_waits) / len(self.sync_barrier_waits) if self.sync_barrier_waits else 0

    @property
    def agent_utilization(self) -> float:
        """Percentage of time agents were active vs total time."""
        if not self.agent_active_times or self.total_duration_seconds == 0:
            return 0
        total_active = sum(self.agent_active_times.values())
        max_possible = self.total_duration_seconds * self.agent_count
        return (total_active / max_possible) * 100 if max_possible > 0 else 0

    @property
    def token_efficiency(self) -> float:
        """Tokens per task completed."""
        task_count = len(self.task_times)
        return self.total_tokens / task_count if task_count > 0 else 0


class MetricsCollector:
    """
    Collects and stores Power Mode metrics.

    Usage:
        collector = MetricsCollector(session_id)
        collector.start_phase("implementation")
        collector.record_insight_shared()
        collector.end_phase("implementation")
        report = collector.generate_report()
    """

    def __init__(self, session_id: str):
        self.metrics = SessionMetrics(session_id=session_id)
        self._current_phase: Optional[str] = None
        self._phase_start_time: Optional[datetime] = None
        self._agent_start_times: Dict[str, datetime] = {}

    # =========================================================================
    # PHASE TRACKING
    # =========================================================================

    def start_phase(self, phase_name: str):
        """Start timing a phase."""
        self._current_phase = phase_name
        self._phase_start_time = datetime.now()
        self.metrics.phase_times[phase_name] = TimingMetric(
            name=phase_name,
            started_at=self._phase_start_time,
            phase=phase_name
        )

    def end_phase(self, phase_name: str):
        """End timing a phase."""
        if phase_name in self.metrics.phase_times:
            self.metrics.phase_times[phase_name].ended_at = datetime.now()
        self._current_phase = None
        self._phase_start_time = None

    # =========================================================================
    # TASK TRACKING
    # =========================================================================

    def start_task(self, task_id: str, agent_id: Optional[str] = None):
        """Start timing a task."""
        self.metrics.task_times[task_id] = TimingMetric(
            name=task_id,
            started_at=datetime.now(),
            phase=self._current_phase,
            agent_id=agent_id
        )

    def end_task(self, task_id: str, rework: bool = False):
        """End timing a task."""
        if task_id in self.metrics.task_times:
            self.metrics.task_times[task_id].ended_at = datetime.now()
        if rework:
            self.metrics.rework_count += 1

    # =========================================================================
    # AGENT TRACKING
    # =========================================================================

    def agent_started(self, agent_id: str):
        """Record agent becoming active."""
        self._agent_start_times[agent_id] = datetime.now()
        self.metrics.agent_count = max(self.metrics.agent_count, len(self._agent_start_times))
        self.metrics.peak_concurrent_agents = max(
            self.metrics.peak_concurrent_agents,
            len(self._agent_start_times)
        )

    def agent_stopped(self, agent_id: str):
        """Record agent becoming inactive."""
        if agent_id in self._agent_start_times:
            active_time = (datetime.now() - self._agent_start_times[agent_id]).total_seconds()
            self.metrics.agent_active_times[agent_id] = \
                self.metrics.agent_active_times.get(agent_id, 0) + active_time
            del self._agent_start_times[agent_id]

    # =========================================================================
    # COORDINATION TRACKING
    # =========================================================================

    def record_insight_shared(self):
        """Record an insight being shared between agents."""
        self.metrics.insights_shared += 1

    def record_context_reuse(self):
        """Record context being reused to avoid duplicate work."""
        self.metrics.context_reuses += 1

    def record_sync_barrier_wait(self, wait_seconds: float):
        """Record time spent waiting at a sync barrier."""
        self.metrics.sync_barrier_waits.append(wait_seconds)

    def record_conflict_resolved(self):
        """Record a conflict between agents being resolved."""
        self.metrics.conflicts_resolved += 1

    # =========================================================================
    # QUALITY TRACKING
    # =========================================================================

    def record_code_review_score(self, score: float):
        """Record a code review confidence score."""
        self.metrics.code_review_scores.append(score)

    def record_bug_detected(self):
        """Record a bug being detected before commit."""
        self.metrics.bugs_detected += 1

    def set_test_coverage(self, start: float = None, end: float = None):
        """Set test coverage values."""
        if start is not None:
            self.metrics.test_coverage_start = start
        if end is not None:
            self.metrics.test_coverage_end = end

    # =========================================================================
    # RESOURCE TRACKING
    # =========================================================================

    def add_tokens(self, count: int):
        """Add to token count."""
        self.metrics.total_tokens += count

    # =========================================================================
    # SESSION LIFECYCLE
    # =========================================================================

    def end_session(self):
        """Mark session as ended."""
        self.metrics.ended_at = datetime.now()
        # Close any open agent times
        for agent_id in list(self._agent_start_times.keys()):
            self.agent_stopped(agent_id)

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive metrics report."""
        m = self.metrics

        return {
            "session": {
                "id": m.session_id,
                "started_at": m.started_at.isoformat(),
                "ended_at": m.ended_at.isoformat() if m.ended_at else None,
                "total_duration": m.total_duration_seconds,
                "total_duration_formatted": self._format_duration(m.total_duration_seconds)
            },
            "time_metrics": {
                "phases": {
                    name: {
                        "duration_seconds": t.duration_seconds,
                        "duration_formatted": t.duration_formatted
                    }
                    for name, t in m.phase_times.items()
                },
                "tasks_completed": len(m.task_times),
                "average_task_time": self._average_task_time()
            },
            "quality_metrics": {
                "first_pass_success_rate": round(m.first_pass_success_rate, 1),
                "average_code_review_score": round(m.average_code_review_score, 1),
                "test_coverage_delta": round(m.test_coverage_delta, 1),
                "bugs_detected": m.bugs_detected,
                "rework_count": m.rework_count
            },
            "coordination_metrics": {
                "insights_shared": m.insights_shared,
                "context_reuses": m.context_reuses,
                "average_sync_wait_seconds": round(m.average_sync_wait, 2),
                "conflicts_resolved": m.conflicts_resolved
            },
            "resource_metrics": {
                "total_tokens": m.total_tokens,
                "token_efficiency": round(m.token_efficiency, 0),
                "agent_count": m.agent_count,
                "peak_concurrent_agents": m.peak_concurrent_agents,
                "agent_utilization_percent": round(m.agent_utilization, 1)
            },
            "value_summary": self._calculate_value_summary()
        }

    def _average_task_time(self) -> float:
        """Calculate average task completion time."""
        if not self.metrics.task_times:
            return 0
        total = sum(t.duration_seconds for t in self.metrics.task_times.values())
        return total / len(self.metrics.task_times)

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def _calculate_value_summary(self) -> Dict[str, Any]:
        """Calculate the overall value proposition."""
        m = self.metrics

        # Value score (0-100) based on key metrics
        scores = []

        # First-pass success contributes to value
        if m.first_pass_success_rate > 0:
            scores.append(min(m.first_pass_success_rate, 100))

        # Code review score
        if m.average_code_review_score > 0:
            scores.append(m.average_code_review_score)

        # Agent utilization
        if m.agent_utilization > 0:
            scores.append(m.agent_utilization)

        # Coordination benefits (normalize to 0-100)
        coord_score = min((m.insights_shared + m.context_reuses) * 5, 100)
        if coord_score > 0:
            scores.append(coord_score)

        overall_score = sum(scores) / len(scores) if scores else 0

        return {
            "overall_score": round(overall_score, 1),
            "rating": self._score_to_rating(overall_score),
            "highlights": self._generate_highlights()
        }

    def _score_to_rating(self, score: float) -> str:
        """Convert score to rating."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        else:
            return "Needs Improvement"

    def _generate_highlights(self) -> List[str]:
        """Generate highlight bullet points."""
        m = self.metrics
        highlights = []

        if m.first_pass_success_rate >= 90:
            highlights.append(f"{m.first_pass_success_rate:.0f}% first-pass success rate")

        if m.insights_shared >= 5:
            highlights.append(f"{m.insights_shared} insights shared between agents")

        if m.bugs_detected > 0:
            highlights.append(f"{m.bugs_detected} bugs caught before commit")

        if m.test_coverage_delta > 0:
            highlights.append(f"+{m.test_coverage_delta:.1f}% test coverage improvement")

        if m.peak_concurrent_agents > 1:
            highlights.append(f"Up to {m.peak_concurrent_agents} agents working in parallel")

        return highlights

    def format_cli_report(self) -> str:
        """Format report for CLI output."""
        report = self.generate_report()

        lines = [
            "",
            "=" * 60,
            "  POWER MODE METRICS REPORT",
            "=" * 60,
            "",
            f"Session: {report['session']['id']}",
            f"Duration: {report['session']['total_duration_formatted']}",
            "",
            "--- TIME METRICS ---",
            f"  Tasks completed: {report['time_metrics']['tasks_completed']}",
            f"  Average task time: {self._format_duration(report['time_metrics']['average_task_time'])}",
        ]

        if report['time_metrics']['phases']:
            lines.append("  Phase breakdown:")
            for phase, data in report['time_metrics']['phases'].items():
                lines.append(f"    - {phase}: {data['duration_formatted']}")

        lines.extend([
            "",
            "--- QUALITY METRICS ---",
            f"  First-pass success: {report['quality_metrics']['first_pass_success_rate']}%",
            f"  Avg code review score: {report['quality_metrics']['average_code_review_score']}",
            f"  Bugs detected: {report['quality_metrics']['bugs_detected']}",
            f"  Rework needed: {report['quality_metrics']['rework_count']} tasks",
        ])

        lines.extend([
            "",
            "--- COORDINATION METRICS ---",
            f"  Insights shared: {report['coordination_metrics']['insights_shared']}",
            f"  Context reuses: {report['coordination_metrics']['context_reuses']}",
            f"  Avg sync wait: {report['coordination_metrics']['average_sync_wait_seconds']}s",
            f"  Conflicts resolved: {report['coordination_metrics']['conflicts_resolved']}",
        ])

        lines.extend([
            "",
            "--- RESOURCE METRICS ---",
            f"  Agents used: {report['resource_metrics']['agent_count']}",
            f"  Peak concurrent: {report['resource_metrics']['peak_concurrent_agents']}",
            f"  Agent utilization: {report['resource_metrics']['agent_utilization_percent']}%",
            f"  Total tokens: {report['resource_metrics']['total_tokens']:,}",
            f"  Token efficiency: {report['resource_metrics']['token_efficiency']:.0f} tokens/task",
        ])

        vs = report['value_summary']
        lines.extend([
            "",
            "--- VALUE SUMMARY ---",
            f"  Overall Score: {vs['overall_score']}/100 ({vs['rating']})",
            "",
            "  Highlights:",
        ])

        for highlight in vs['highlights']:
            lines.append(f"    + {highlight}")

        if not vs['highlights']:
            lines.append("    (No significant highlights yet)")

        lines.extend([
            "",
            "=" * 60,
        ])

        return "\n".join(lines)


def load_session_metrics(session_id: str, redis_client=None) -> Optional[SessionMetrics]:
    """Load metrics for a session from Redis."""
    if redis_client is None:
        return None

    try:
        data = redis_client.get(f"popkit:metrics:{session_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass

    return None


def save_session_metrics(metrics: SessionMetrics, redis_client=None):
    """Save metrics to Redis."""
    if redis_client is None:
        return

    try:
        data = json.dumps(asdict(metrics), default=str)
        redis_client.setex(
            f"popkit:metrics:{metrics.session_id}",
            timedelta(days=7),  # Keep for 7 days
            data
        )
    except Exception:
        pass


if __name__ == "__main__":
    # Demo/test
    collector = MetricsCollector("demo-session")

    # Simulate some activity
    collector.start_phase("implementation")
    collector.agent_started("code-architect")
    collector.agent_started("test-writer-fixer")

    collector.start_task("task-1", "code-architect")
    time.sleep(0.1)  # Simulate work
    collector.record_insight_shared()
    collector.end_task("task-1")

    collector.start_task("task-2", "test-writer-fixer")
    time.sleep(0.1)
    collector.record_code_review_score(85)
    collector.end_task("task-2")

    collector.agent_stopped("code-architect")
    collector.agent_stopped("test-writer-fixer")
    collector.end_phase("implementation")

    collector.end_session()

    print(collector.format_cli_report())
