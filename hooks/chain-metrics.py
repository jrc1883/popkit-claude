#!/usr/bin/env python3
"""
Chain Metrics Hook
Tracks workflow execution metrics including timing, success rates, and bottlenecks.

Persists to .claude/chain-metrics.json for persistence across sessions.
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Path resolution
METRICS_FILE = Path.home() / ".claude" / "chain-metrics.json"
MAX_RUNS_HISTORY = 100  # Keep last 100 runs per workflow


class ChainMetrics:
    """Manages workflow execution metrics."""

    def __init__(self):
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Any]:
        """Load metrics from JSON file."""
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "version": "1.0.0",
            "runs": [],
            "aggregates": {}
        }

    def _save_metrics(self) -> bool:
        """Save metrics to JSON file."""
        try:
            METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(METRICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2)
            return True
        except IOError:
            return False

    def start_run(self, workflow_id: str, workflow_name: str = None) -> str:
        """Record the start of a workflow run.

        Returns:
            run_id for tracking this execution
        """
        run_id = str(uuid.uuid4())[:8]

        run = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name or workflow_id,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "status": "running",
            "steps": [],
            "total_duration_ms": None
        }

        self.metrics['runs'].append(run)
        self._save_metrics()

        return run_id

    def record_step(self, run_id: str, step_id: str, step_name: str,
                   agent: str = None, status: str = "completed",
                   duration_ms: int = None, confidence: int = None) -> bool:
        """Record a step execution in a workflow run."""
        for run in self.metrics['runs']:
            if run['run_id'] == run_id:
                step = {
                    "step_id": step_id,
                    "step_name": step_name,
                    "agent": agent,
                    "status": status,
                    "duration_ms": duration_ms,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat()
                }
                run['steps'].append(step)
                self._save_metrics()
                return True
        return False

    def complete_run(self, run_id: str, status: str = "completed") -> bool:
        """Mark a workflow run as complete and update aggregates."""
        for run in self.metrics['runs']:
            if run['run_id'] == run_id:
                run['ended_at'] = datetime.now().isoformat()
                run['status'] = status

                # Calculate total duration
                try:
                    start = datetime.fromisoformat(run['started_at'])
                    end = datetime.fromisoformat(run['ended_at'])
                    run['total_duration_ms'] = int((end - start).total_seconds() * 1000)
                except ValueError:
                    pass

                self._update_aggregates(run)
                self._prune_old_runs(run['workflow_id'])
                self._save_metrics()
                return True
        return False

    def _update_aggregates(self, run: Dict[str, Any]):
        """Update aggregate statistics for a workflow."""
        workflow_id = run['workflow_id']

        if workflow_id not in self.metrics['aggregates']:
            self.metrics['aggregates'][workflow_id] = {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "total_duration_ms": 0,
                "step_metrics": {},
                "bottlenecks": []
            }

        agg = self.metrics['aggregates'][workflow_id]

        # Update counts
        agg['total_runs'] += 1
        if run['status'] == 'completed':
            agg['successful_runs'] += 1
        else:
            agg['failed_runs'] += 1

        # Update rates
        agg['success_rate'] = round(
            (agg['successful_runs'] / agg['total_runs']) * 100, 1
        )

        # Update duration averages
        if run.get('total_duration_ms'):
            agg['total_duration_ms'] += run['total_duration_ms']
            agg['avg_duration_ms'] = int(agg['total_duration_ms'] / agg['total_runs'])

        # Update step metrics
        for step in run.get('steps', []):
            step_id = step.get('step_id', 'unknown')
            if step_id not in agg['step_metrics']:
                agg['step_metrics'][step_id] = {
                    "total_runs": 0,
                    "successful": 0,
                    "total_duration_ms": 0,
                    "avg_duration_ms": 0
                }

            sm = agg['step_metrics'][step_id]
            sm['total_runs'] += 1
            if step.get('status') == 'completed':
                sm['successful'] += 1
            if step.get('duration_ms'):
                sm['total_duration_ms'] += step['duration_ms']
                sm['avg_duration_ms'] = int(sm['total_duration_ms'] / sm['total_runs'])

        # Identify bottlenecks (steps with highest avg duration)
        step_durations = [
            {"step_id": sid, "avg_ms": sm['avg_duration_ms']}
            for sid, sm in agg['step_metrics'].items()
            if sm['avg_duration_ms'] > 0
        ]
        step_durations.sort(key=lambda x: x['avg_ms'], reverse=True)
        agg['bottlenecks'] = step_durations[:3]  # Top 3 bottlenecks

    def _prune_old_runs(self, workflow_id: str):
        """Keep only the last MAX_RUNS_HISTORY runs per workflow."""
        workflow_runs = [r for r in self.metrics['runs'] if r['workflow_id'] == workflow_id]
        other_runs = [r for r in self.metrics['runs'] if r['workflow_id'] != workflow_id]

        if len(workflow_runs) > MAX_RUNS_HISTORY:
            # Sort by started_at and keep most recent
            workflow_runs.sort(key=lambda r: r.get('started_at', ''), reverse=True)
            workflow_runs = workflow_runs[:MAX_RUNS_HISTORY]

        self.metrics['runs'] = other_runs + workflow_runs

    def get_workflow_stats(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregate statistics for a workflow."""
        return self.metrics['aggregates'].get(workflow_id)

    def get_recent_runs(self, workflow_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent runs, optionally filtered by workflow."""
        runs = self.metrics['runs']

        if workflow_id:
            runs = [r for r in runs if r['workflow_id'] == workflow_id]

        # Sort by started_at descending
        runs.sort(key=lambda r: r.get('started_at', ''), reverse=True)

        return runs[:limit]

    def format_stats_report(self, workflow_id: str) -> str:
        """Generate a formatted stats report for a workflow."""
        stats = self.get_workflow_stats(workflow_id)

        if not stats:
            return f"No metrics available for workflow '{workflow_id}'"

        lines = [
            f"Workflow: {workflow_id} - Metrics",
            "=" * 40,
            "",
            "Overall Stats:",
            f"  Total runs:     {stats['total_runs']}",
            f"  Success rate:   {stats['success_rate']}%",
            f"  Avg duration:   {self._format_duration(stats['avg_duration_ms'])}",
            ""
        ]

        if stats.get('step_metrics'):
            lines.append("Step Performance:")
            lines.append(f"  {'Step':<20} {'Avg Time':<12} {'Success':<10}")
            lines.append(f"  {'-'*20} {'-'*12} {'-'*10}")

            for step_id, sm in stats['step_metrics'].items():
                success_rate = round((sm['successful'] / sm['total_runs']) * 100) if sm['total_runs'] > 0 else 0
                lines.append(
                    f"  {step_id:<20} {self._format_duration(sm['avg_duration_ms']):<12} {success_rate}%"
                )
            lines.append("")

        if stats.get('bottlenecks'):
            lines.append("Top Bottlenecks:")
            for i, b in enumerate(stats['bottlenecks'], 1):
                lines.append(f"  {i}. {b['step_id']} ({self._format_duration(b['avg_ms'])})")

        return "\n".join(lines)

    def _format_duration(self, ms: int) -> str:
        """Format milliseconds as human-readable duration."""
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return f"{ms/1000:.1f}s"
        else:
            minutes = ms // 60000
            seconds = (ms % 60000) // 1000
            return f"{minutes}m {seconds}s"


def main():
    """Main entry point for the hook - JSON stdin/stdout protocol."""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Initialize metrics
        metrics = ChainMetrics()

        # Handle different operations based on input
        operation = data.get('operation', 'status')

        if operation == 'start_run':
            run_id = metrics.start_run(
                data.get('workflow_id', 'unknown'),
                data.get('workflow_name')
            )
            response = {"status": "success", "run_id": run_id}

        elif operation == 'record_step':
            success = metrics.record_step(
                data.get('run_id'),
                data.get('step_id'),
                data.get('step_name'),
                data.get('agent'),
                data.get('step_status', 'completed'),
                data.get('duration_ms'),
                data.get('confidence')
            )
            response = {"status": "success" if success else "error"}

        elif operation == 'complete_run':
            success = metrics.complete_run(
                data.get('run_id'),
                data.get('run_status', 'completed')
            )
            response = {"status": "success" if success else "error"}

        elif operation == 'get_stats':
            workflow_id = data.get('workflow_id')
            stats = metrics.get_workflow_stats(workflow_id)
            response = {"status": "success", "stats": stats}

        elif operation == 'get_recent':
            runs = metrics.get_recent_runs(
                data.get('workflow_id'),
                data.get('limit', 10)
            )
            response = {"status": "success", "runs": runs}

        else:
            # Default: return current aggregates
            response = {
                "status": "success",
                "aggregates": metrics.metrics.get('aggregates', {}),
                "total_runs": len(metrics.metrics.get('runs', []))
            }

        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in chain-metrics hook: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    # If run directly, show current metrics
    metrics = ChainMetrics()
    print(json.dumps(metrics.metrics, indent=2))
