#!/usr/bin/env python3
"""
Sandbox Analytics - Query and analyze test telemetry data.

Part of Issue #231: Analytics Dashboard & Comparison

Features:
- Session summary generation
- Tool call frequency analysis
- Duration percentile calculations
- Error pattern detection
- Token usage aggregation
- Local vs E2B comparison
- Trend analysis

Usage:
    python analytics.py --session <id>              # Analyze single session
    python analytics.py --compare <id1> <id2>       # Compare two sessions
    python analytics.py --recent 10                 # Analyze recent sessions
    python analytics.py --stats                     # Overall statistics
"""

import json
import argparse
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import re


@dataclass
class SessionSummary:
    """Summary of a test session."""
    session_id: str
    test_type: str
    test_name: str
    mode: str  # local, e2b
    status: str  # running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    tool_calls: int = 0
    decision_points: int = 0
    errors: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    outcome: str = "unknown"  # success, failure, partial
    tool_frequency: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    phases: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of comparing two sessions."""
    session_a: SessionSummary
    session_b: SessionSummary
    duration_diff_pct: float
    tool_calls_diff: int
    tokens_diff: int
    same_outcome: bool
    notable_differences: List[str] = field(default_factory=list)


class TelemetryAnalyzer:
    """Analyzes telemetry data from test sessions."""

    # Anthropic pricing (approximate, per 1K tokens)
    TOKEN_COSTS = {
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "default": {"input": 0.003, "output": 0.015}
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize analyzer with data directory."""
        if data_dir is None:
            # Default to .popkit-test in current dir or temp
            data_dir = Path(".popkit-test")
            if not data_dir.exists():
                data_dir = Path.home() / ".popkit-test"

        self.data_dir = data_dir
        self._sessions_cache: Dict[str, SessionSummary] = {}

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List available test sessions."""
        sessions = []

        if not self.data_dir.exists():
            return sessions

        for session_dir in sorted(self.data_dir.iterdir(), reverse=True):
            if session_dir.is_dir() and session_dir.name.startswith("test-"):
                meta_file = session_dir / "meta.jsonl"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            for line in f:
                                meta = json.loads(line)
                                if meta.get("event_type") == "session_start":
                                    sessions.append({
                                        "session_id": session_dir.name,
                                        "test_type": meta.get("data", {}).get("test_type", "unknown"),
                                        "test_name": meta.get("data", {}).get("test_name", "unknown"),
                                        "mode": meta.get("data", {}).get("mode", "local"),
                                        "timestamp": meta.get("timestamp")
                                    })
                                    break
                    except (json.JSONDecodeError, OSError):
                        pass

            if len(sessions) >= limit:
                break

        return sessions

    def load_session(self, session_id: str) -> Optional[SessionSummary]:
        """Load and analyze a single session."""
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]

        session_dir = self.data_dir / session_id
        if not session_dir.exists():
            return None

        summary = SessionSummary(
            session_id=session_id,
            test_type="unknown",
            test_name="unknown",
            mode="local"
        )

        # Load metadata
        meta_file = session_dir / "meta.jsonl"
        if meta_file.exists():
            self._parse_meta(meta_file, summary)

        # Load traces
        traces_file = session_dir / "traces.jsonl"
        if traces_file.exists():
            self._parse_traces(traces_file, summary)

        # Load decisions
        decisions_file = session_dir / "decisions.jsonl"
        if decisions_file.exists():
            self._parse_decisions(decisions_file, summary)

        # Load events
        events_file = session_dir / "events.jsonl"
        if events_file.exists():
            self._parse_events(events_file, summary)

        # Calculate derived metrics
        self._calculate_metrics(summary)

        self._sessions_cache[session_id] = summary
        return summary

    def _parse_meta(self, meta_file: Path, summary: SessionSummary) -> None:
        """Parse metadata file."""
        with open(meta_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    meta = json.loads(line)
                    event_type = meta.get("event_type")
                    data = meta.get("data", {})

                    if event_type == "session_start":
                        summary.test_type = data.get("test_type", "unknown")
                        summary.test_name = data.get("test_name", "unknown")
                        summary.mode = data.get("mode", "local")
                        summary.status = "running"
                        if meta.get("timestamp"):
                            summary.start_time = datetime.fromisoformat(
                                meta["timestamp"].replace("Z", "+00:00")
                            )

                    elif event_type == "session_end":
                        summary.status = data.get("status", "completed")
                        summary.outcome = data.get("outcome", "unknown")
                        if meta.get("timestamp"):
                            summary.end_time = datetime.fromisoformat(
                                meta["timestamp"].replace("Z", "+00:00")
                            )

                except json.JSONDecodeError:
                    pass

    def _parse_traces(self, traces_file: Path, summary: SessionSummary) -> None:
        """Parse tool traces file."""
        with open(traces_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    trace = json.loads(line)
                    summary.tool_calls += 1

                    tool_name = trace.get("tool_name", "unknown")
                    summary.tool_frequency[tool_name] = summary.tool_frequency.get(tool_name, 0) + 1

                    # Track errors
                    if trace.get("error"):
                        summary.errors += 1
                        error_type = self._classify_error(trace.get("error", ""))
                        summary.error_types[error_type] = summary.error_types.get(error_type, 0) + 1

                    # Track tokens
                    tokens = trace.get("tokens", {})
                    summary.tokens_in += tokens.get("input", 0)
                    summary.tokens_out += tokens.get("output", 0)

                    # Track duration
                    if trace.get("duration_ms"):
                        summary.duration_ms += trace["duration_ms"]

                except json.JSONDecodeError:
                    pass

    def _parse_decisions(self, decisions_file: Path, summary: SessionSummary) -> None:
        """Parse decision points file."""
        with open(decisions_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    json.loads(line)  # Validate JSON
                    summary.decision_points += 1
                except json.JSONDecodeError:
                    pass

    def _parse_events(self, events_file: Path, summary: SessionSummary) -> None:
        """Parse custom events file."""
        with open(events_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    event_type = event.get("event_type")

                    # Track phase changes
                    if event_type == "phase_change":
                        phase = event.get("data", {}).get("phase")
                        if phase and phase not in summary.phases:
                            summary.phases.append(phase)

                except json.JSONDecodeError:
                    pass

    def _classify_error(self, error_message: str) -> str:
        """Classify error into categories."""
        error_lower = error_message.lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission"
        elif "not found" in error_lower or "no such" in error_lower:
            return "not_found"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "syntax"
        elif "type" in error_lower and "error" in error_lower:
            return "type_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        else:
            return "other"

    def _calculate_metrics(self, summary: SessionSummary) -> None:
        """Calculate derived metrics."""
        # Calculate duration from timestamps if not set
        if summary.start_time and summary.end_time and summary.duration_ms == 0:
            delta = summary.end_time - summary.start_time
            summary.duration_ms = int(delta.total_seconds() * 1000)

        # Estimate cost
        model_costs = self.TOKEN_COSTS.get("default")
        summary.estimated_cost_usd = (
            (summary.tokens_in / 1000) * model_costs["input"] +
            (summary.tokens_out / 1000) * model_costs["output"]
        )

        # Determine outcome if not set
        if summary.outcome == "unknown" and summary.status == "completed":
            if summary.errors == 0:
                summary.outcome = "success"
            elif summary.errors < summary.tool_calls * 0.1:  # <10% error rate
                summary.outcome = "partial"
            else:
                summary.outcome = "failure"

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get formatted session summary."""
        summary = self.load_session(session_id)
        if not summary:
            return None

        return {
            "session_id": summary.session_id,
            "test_type": summary.test_type,
            "test_name": summary.test_name,
            "mode": summary.mode,
            "status": summary.status,
            "outcome": summary.outcome,
            "metrics": {
                "duration_ms": summary.duration_ms,
                "duration_human": self._format_duration(summary.duration_ms),
                "tool_calls": summary.tool_calls,
                "decision_points": summary.decision_points,
                "errors": summary.errors,
                "error_rate_pct": round(summary.errors / max(summary.tool_calls, 1) * 100, 1),
                "tokens_in": summary.tokens_in,
                "tokens_out": summary.tokens_out,
                "tokens_total": summary.tokens_in + summary.tokens_out,
                "estimated_cost_usd": round(summary.estimated_cost_usd, 4)
            },
            "tool_frequency": dict(sorted(
                summary.tool_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "error_types": summary.error_types,
            "phases": summary.phases
        }

    def _format_duration(self, duration_ms: int) -> str:
        """Format duration in human-readable form."""
        if duration_ms < 1000:
            return f"{duration_ms}ms"
        elif duration_ms < 60000:
            return f"{duration_ms / 1000:.1f}s"
        else:
            minutes = duration_ms // 60000
            seconds = (duration_ms % 60000) / 1000
            return f"{minutes}m {seconds:.0f}s"

    def compare_sessions(
        self,
        session_a_id: str,
        session_b_id: str
    ) -> Optional[ComparisonResult]:
        """Compare two test sessions."""
        summary_a = self.load_session(session_a_id)
        summary_b = self.load_session(session_b_id)

        if not summary_a or not summary_b:
            return None

        # Calculate differences
        duration_diff_pct = 0.0
        if summary_a.duration_ms > 0:
            duration_diff_pct = (
                (summary_b.duration_ms - summary_a.duration_ms) /
                summary_a.duration_ms * 100
            )

        tool_calls_diff = summary_b.tool_calls - summary_a.tool_calls
        tokens_diff = (
            (summary_b.tokens_in + summary_b.tokens_out) -
            (summary_a.tokens_in + summary_a.tokens_out)
        )

        result = ComparisonResult(
            session_a=summary_a,
            session_b=summary_b,
            duration_diff_pct=round(duration_diff_pct, 1),
            tool_calls_diff=tool_calls_diff,
            tokens_diff=tokens_diff,
            same_outcome=summary_a.outcome == summary_b.outcome
        )

        # Note significant differences
        if abs(duration_diff_pct) > 20:
            direction = "slower" if duration_diff_pct > 0 else "faster"
            result.notable_differences.append(
                f"Session B is {abs(duration_diff_pct):.0f}% {direction}"
            )

        if abs(tool_calls_diff) > 5:
            more_less = "more" if tool_calls_diff > 0 else "fewer"
            result.notable_differences.append(
                f"Session B has {abs(tool_calls_diff)} {more_less} tool calls"
            )

        if not result.same_outcome:
            result.notable_differences.append(
                f"Outcome changed: {summary_a.outcome} → {summary_b.outcome}"
            )

        # Check for new errors
        new_errors = set(summary_b.error_types.keys()) - set(summary_a.error_types.keys())
        if new_errors:
            result.notable_differences.append(
                f"New error types in B: {', '.join(new_errors)}"
            )

        return result

    def get_aggregate_stats(self, session_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get aggregate statistics across sessions."""
        if session_ids is None:
            sessions = self.list_sessions(limit=100)
            session_ids = [s["session_id"] for s in sessions]

        summaries = []
        for sid in session_ids:
            summary = self.load_session(sid)
            if summary:
                summaries.append(summary)

        if not summaries:
            return {"error": "No sessions found"}

        # Aggregate metrics
        durations = [s.duration_ms for s in summaries if s.duration_ms > 0]
        tool_counts = [s.tool_calls for s in summaries]
        token_totals = [s.tokens_in + s.tokens_out for s in summaries]
        costs = [s.estimated_cost_usd for s in summaries]

        # Count outcomes
        outcomes = Counter(s.outcome for s in summaries)
        modes = Counter(s.mode for s in summaries)

        # Aggregate tool frequency
        all_tools: Dict[str, int] = defaultdict(int)
        for s in summaries:
            for tool, count in s.tool_frequency.items():
                all_tools[tool] += count

        # Aggregate error types
        all_errors: Dict[str, int] = defaultdict(int)
        for s in summaries:
            for error, count in s.error_types.items():
                all_errors[error] += count

        return {
            "session_count": len(summaries),
            "outcomes": dict(outcomes),
            "modes": dict(modes),
            "duration": {
                "min_ms": min(durations) if durations else 0,
                "max_ms": max(durations) if durations else 0,
                "mean_ms": int(statistics.mean(durations)) if durations else 0,
                "median_ms": int(statistics.median(durations)) if durations else 0,
                "p95_ms": int(self._percentile(durations, 95)) if durations else 0
            },
            "tool_calls": {
                "total": sum(tool_counts),
                "mean": round(statistics.mean(tool_counts), 1) if tool_counts else 0,
                "top_tools": dict(sorted(all_tools.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            "tokens": {
                "total": sum(token_totals),
                "mean": int(statistics.mean(token_totals)) if token_totals else 0
            },
            "cost": {
                "total_usd": round(sum(costs), 4),
                "mean_usd": round(statistics.mean(costs), 4) if costs else 0
            },
            "errors": {
                "total": sum(s.errors for s in summaries),
                "sessions_with_errors": sum(1 for s in summaries if s.errors > 0),
                "types": dict(sorted(all_errors.items(), key=lambda x: x[1], reverse=True))
            }
        }

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[-1]
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def detect_regressions(
        self,
        baseline_ids: List[str],
        current_ids: List[str],
        threshold_pct: float = 20.0
    ) -> Dict[str, Any]:
        """Detect performance regressions between baseline and current."""
        baseline_stats = self.get_aggregate_stats(baseline_ids)
        current_stats = self.get_aggregate_stats(current_ids)

        regressions = []
        improvements = []

        # Check duration regression
        baseline_duration = baseline_stats.get("duration", {}).get("median_ms", 0)
        current_duration = current_stats.get("duration", {}).get("median_ms", 0)

        if baseline_duration > 0:
            duration_change = ((current_duration - baseline_duration) / baseline_duration) * 100
            if duration_change > threshold_pct:
                regressions.append({
                    "metric": "duration",
                    "baseline": baseline_duration,
                    "current": current_duration,
                    "change_pct": round(duration_change, 1),
                    "severity": "high" if duration_change > 50 else "medium"
                })
            elif duration_change < -threshold_pct:
                improvements.append({
                    "metric": "duration",
                    "baseline": baseline_duration,
                    "current": current_duration,
                    "change_pct": round(duration_change, 1)
                })

        # Check error rate regression
        baseline_errors = baseline_stats.get("errors", {}).get("total", 0)
        baseline_calls = baseline_stats.get("tool_calls", {}).get("total", 1)
        baseline_error_rate = baseline_errors / baseline_calls

        current_errors = current_stats.get("errors", {}).get("total", 0)
        current_calls = current_stats.get("tool_calls", {}).get("total", 1)
        current_error_rate = current_errors / current_calls

        if baseline_error_rate > 0:
            error_change = ((current_error_rate - baseline_error_rate) / baseline_error_rate) * 100
            if error_change > threshold_pct:
                regressions.append({
                    "metric": "error_rate",
                    "baseline": round(baseline_error_rate * 100, 2),
                    "current": round(current_error_rate * 100, 2),
                    "change_pct": round(error_change, 1),
                    "severity": "high"
                })

        # Check outcome regression
        baseline_success = baseline_stats.get("outcomes", {}).get("success", 0)
        baseline_total = baseline_stats.get("session_count", 1)
        baseline_success_rate = baseline_success / baseline_total

        current_success = current_stats.get("outcomes", {}).get("success", 0)
        current_total = current_stats.get("session_count", 1)
        current_success_rate = current_success / current_total

        if baseline_success_rate > 0:
            success_change = ((current_success_rate - baseline_success_rate) / baseline_success_rate) * 100
            if success_change < -threshold_pct:
                regressions.append({
                    "metric": "success_rate",
                    "baseline": round(baseline_success_rate * 100, 1),
                    "current": round(current_success_rate * 100, 1),
                    "change_pct": round(success_change, 1),
                    "severity": "critical" if success_change < -30 else "high"
                })

        return {
            "has_regressions": len(regressions) > 0,
            "regressions": regressions,
            "improvements": improvements,
            "baseline_sessions": len(baseline_ids),
            "current_sessions": len(current_ids)
        }


class ReportGenerator:
    """Generates reports from analytics data."""

    def __init__(self, analyzer: TelemetryAnalyzer):
        self.analyzer = analyzer

    def generate_session_report(self, session_id: str) -> str:
        """Generate markdown report for a session."""
        summary = self.analyzer.get_session_summary(session_id)
        if not summary:
            return f"# Session Not Found: {session_id}"

        metrics = summary["metrics"]
        outcome_emoji = {"success": "✅", "failure": "❌", "partial": "⚠️"}.get(
            summary["outcome"], "❓"
        )

        report = f"""# Test Session Report: {session_id}

## Overview

| Property | Value |
|----------|-------|
| Test Type | {summary['test_type']} |
| Test Name | {summary['test_name']} |
| Mode | {summary['mode']} |
| Status | {summary['status']} |
| Outcome | {outcome_emoji} {summary['outcome']} |

## Metrics

| Metric | Value |
|--------|-------|
| Duration | {metrics['duration_human']} |
| Tool Calls | {metrics['tool_calls']} |
| Decision Points | {metrics['decision_points']} |
| Errors | {metrics['errors']} ({metrics['error_rate_pct']}%) |
| Tokens (in/out) | {metrics['tokens_in']:,} / {metrics['tokens_out']:,} |
| Est. Cost | ${metrics['estimated_cost_usd']:.4f} |

## Tool Usage

| Tool | Count |
|------|-------|
"""
        for tool, count in list(summary["tool_frequency"].items())[:10]:
            report += f"| {tool} | {count} |\n"

        if summary["error_types"]:
            report += "\n## Error Types\n\n| Type | Count |\n|------|-------|\n"
            for error_type, count in summary["error_types"].items():
                report += f"| {error_type} | {count} |\n"

        if summary["phases"]:
            report += f"\n## Phases\n\n{' → '.join(summary['phases'])}\n"

        report += f"\n---\n*Generated: {datetime.now().isoformat()}*\n"

        return report

    def generate_comparison_report(
        self,
        session_a_id: str,
        session_b_id: str
    ) -> str:
        """Generate comparison report between two sessions."""
        result = self.analyzer.compare_sessions(session_a_id, session_b_id)
        if not result:
            return "# Comparison Failed\n\nOne or both sessions not found."

        a = result.session_a
        b = result.session_b

        outcome_match = "✅ Same" if result.same_outcome else "❌ Different"

        report = f"""# Session Comparison Report

## Sessions

| Property | Session A | Session B |
|----------|-----------|-----------|
| ID | {a.session_id} | {b.session_id} |
| Test | {a.test_name} | {b.test_name} |
| Mode | {a.mode} | {b.mode} |
| Outcome | {a.outcome} | {b.outcome} |

## Comparison Summary

| Metric | Session A | Session B | Difference |
|--------|-----------|-----------|------------|
| Duration | {a.duration_ms:,}ms | {b.duration_ms:,}ms | {result.duration_diff_pct:+.1f}% |
| Tool Calls | {a.tool_calls} | {b.tool_calls} | {result.tool_calls_diff:+d} |
| Tokens | {a.tokens_in + a.tokens_out:,} | {b.tokens_in + b.tokens_out:,} | {result.tokens_diff:+,} |
| Errors | {a.errors} | {b.errors} | {b.errors - a.errors:+d} |
| Outcome Match | {outcome_match} | | |

"""

        if result.notable_differences:
            report += "## Notable Differences\n\n"
            for diff in result.notable_differences:
                report += f"- ⚠️ {diff}\n"

        report += f"\n---\n*Generated: {datetime.now().isoformat()}*\n"

        return report

    def generate_aggregate_report(
        self,
        session_ids: Optional[List[str]] = None,
        title: str = "Aggregate Statistics"
    ) -> str:
        """Generate aggregate statistics report."""
        stats = self.analyzer.get_aggregate_stats(session_ids)

        if "error" in stats:
            return f"# {title}\n\n{stats['error']}"

        success_rate = stats["outcomes"].get("success", 0) / max(stats["session_count"], 1) * 100

        report = f"""# {title}

## Overview

| Metric | Value |
|--------|-------|
| Sessions Analyzed | {stats['session_count']} |
| Success Rate | {success_rate:.1f}% |
| Total Tool Calls | {stats['tool_calls']['total']:,} |
| Total Tokens | {stats['tokens']['total']:,} |
| Total Cost | ${stats['cost']['total_usd']:.4f} |

## Outcome Distribution

| Outcome | Count |
|---------|-------|
"""
        for outcome, count in stats["outcomes"].items():
            emoji = {"success": "✅", "failure": "❌", "partial": "⚠️"}.get(outcome, "❓")
            report += f"| {emoji} {outcome} | {count} |\n"

        report += f"""
## Duration Statistics

| Metric | Value |
|--------|-------|
| Minimum | {stats['duration']['min_ms']:,}ms |
| Maximum | {stats['duration']['max_ms']:,}ms |
| Mean | {stats['duration']['mean_ms']:,}ms |
| Median | {stats['duration']['median_ms']:,}ms |
| P95 | {stats['duration']['p95_ms']:,}ms |

## Top Tools

| Tool | Count |
|------|-------|
"""
        for tool, count in list(stats["tool_calls"]["top_tools"].items())[:10]:
            report += f"| {tool} | {count:,} |\n"

        if stats["errors"]["types"]:
            report += "\n## Error Distribution\n\n| Type | Count |\n|------|-------|\n"
            for error_type, count in stats["errors"]["types"].items():
                report += f"| {error_type} | {count} |\n"

        report += f"\n---\n*Generated: {datetime.now().isoformat()}*\n"

        return report

    def generate_ci_report(
        self,
        session_ids: List[str],
        baseline_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate CI-friendly JSON report."""
        stats = self.analyzer.get_aggregate_stats(session_ids)

        report = {
            "timestamp": datetime.now().isoformat(),
            "session_count": stats.get("session_count", 0),
            "success_rate": 0.0,
            "pass": False,
            "metrics": {},
            "regressions": []
        }

        if stats.get("session_count", 0) > 0:
            report["success_rate"] = (
                stats["outcomes"].get("success", 0) /
                stats["session_count"] * 100
            )
            report["pass"] = report["success_rate"] >= 80  # 80% threshold

            report["metrics"] = {
                "duration_median_ms": stats["duration"]["median_ms"],
                "duration_p95_ms": stats["duration"]["p95_ms"],
                "tool_calls_total": stats["tool_calls"]["total"],
                "tokens_total": stats["tokens"]["total"],
                "cost_total_usd": stats["cost"]["total_usd"],
                "errors_total": stats["errors"]["total"]
            }

        # Check for regressions if baseline provided
        if baseline_ids:
            regression_result = self.analyzer.detect_regressions(
                baseline_ids, session_ids
            )
            report["regressions"] = regression_result["regressions"]
            if regression_result["has_regressions"]:
                # Fail CI if critical regressions
                critical = any(
                    r.get("severity") == "critical"
                    for r in regression_result["regressions"]
                )
                if critical:
                    report["pass"] = False

        return report

    def generate_badge(self, session_ids: List[str]) -> Dict[str, str]:
        """Generate badge data for README/CI."""
        stats = self.analyzer.get_aggregate_stats(session_ids)

        if stats.get("error"):
            return {
                "label": "tests",
                "message": "error",
                "color": "lightgrey"
            }

        success = stats["outcomes"].get("success", 0)
        total = stats["session_count"]
        success_rate = success / max(total, 1) * 100

        if success_rate >= 95:
            color = "brightgreen"
        elif success_rate >= 80:
            color = "green"
        elif success_rate >= 60:
            color = "yellow"
        else:
            color = "red"

        return {
            "label": "sandbox tests",
            "message": f"{success}/{total} passed",
            "color": color,
            "schemaVersion": 1
        }


def main():
    """CLI for analytics."""
    parser = argparse.ArgumentParser(description="Sandbox Test Analytics")
    parser.add_argument("--session", help="Analyze specific session")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), help="Compare two sessions")
    parser.add_argument("--recent", type=int, help="Analyze N recent sessions")
    parser.add_argument("--stats", action="store_true", help="Show aggregate statistics")
    parser.add_argument("--ci", action="store_true", help="Generate CI report (JSON)")
    parser.add_argument("--badge", action="store_true", help="Generate badge data")
    parser.add_argument("--list", action="store_true", help="List available sessions")
    parser.add_argument("--data-dir", type=Path, help="Data directory path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    analyzer = TelemetryAnalyzer(args.data_dir)
    reporter = ReportGenerator(analyzer)

    if args.list:
        sessions = analyzer.list_sessions()
        if args.json:
            print(json.dumps(sessions, indent=2))
        else:
            print(f"Available Sessions ({len(sessions)}):")
            print("-" * 60)
            for s in sessions:
                print(f"  {s['session_id']}")
                print(f"    Test: {s['test_type']}/{s['test_name']} ({s['mode']})")
        return

    if args.session:
        if args.json:
            summary = analyzer.get_session_summary(args.session)
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(reporter.generate_session_report(args.session))
        return

    if args.compare:
        if args.json:
            result = analyzer.compare_sessions(args.compare[0], args.compare[1])
            if result:
                print(json.dumps({
                    "duration_diff_pct": result.duration_diff_pct,
                    "tool_calls_diff": result.tool_calls_diff,
                    "tokens_diff": result.tokens_diff,
                    "same_outcome": result.same_outcome,
                    "notable_differences": result.notable_differences
                }, indent=2))
        else:
            print(reporter.generate_comparison_report(args.compare[0], args.compare[1]))
        return

    # Default to aggregate stats
    session_ids = None
    if args.recent:
        sessions = analyzer.list_sessions(limit=args.recent)
        session_ids = [s["session_id"] for s in sessions]

    if args.ci:
        print(json.dumps(reporter.generate_ci_report(session_ids or []), indent=2))
    elif args.badge:
        print(json.dumps(reporter.generate_badge(session_ids or []), indent=2))
    elif args.stats or args.recent:
        if args.json:
            print(json.dumps(analyzer.get_aggregate_stats(session_ids), indent=2))
        else:
            print(reporter.generate_aggregate_report(session_ids))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
