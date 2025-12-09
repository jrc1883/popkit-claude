#!/usr/bin/env python3
"""
Efficiency Tracker Utility

Part of Issue #78 (Efficiency Metrics: Track Token & Context Savings)

Tracks and calculates PopKit efficiency metrics to prove value:
- Token savings from deduplication
- Pattern matches that helped
- Context reuse from semantic search
- Tool call efficiency
"""

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# =============================================================================
# ESTIMATION CONSTANTS
# =============================================================================

# Average tokens for different operations
TOKENS_PER_DUPLICATE_INSIGHT = 100  # Tokens saved by not reprocessing duplicate
TOKENS_PER_PATTERN_MATCH = 500      # Tokens saved by pattern-based hint (avoided debugging)
TOKENS_PER_INSIGHT_CHAR = 0.25      # ~4 chars per token
TOKENS_PER_CONTEXT_REUSE = 200      # Tokens saved by semantic vs brute force search

# Bug detection savings
TOKENS_PER_BUG_DETECTION = 300      # Tokens saved by early bug detection
TOKENS_PER_STUCK_DETECTION = 800    # Tokens saved by stuck pattern detection (avoided loops)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EfficiencyMetrics:
    """Efficiency metrics for a session."""

    # Session info
    session_id: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Token savings
    duplicates_skipped: int = 0
    patterns_matched: int = 0
    insights_shared: int = 0
    insights_received: int = 0
    context_reuse_count: int = 0
    bugs_detected: int = 0
    stuck_patterns_detected: int = 0

    # Raw data for detailed calculation
    insight_lengths: List[int] = field(default_factory=list)

    # Efficiency gains
    tool_calls: int = 0
    resolution_times_ms: List[int] = field(default_factory=list)

    # Power Mode specific
    sync_barriers_hit: int = 0
    duplicate_work_prevented: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'EfficiencyMetrics':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# EFFICIENCY TRACKER
# =============================================================================

class EfficiencyTracker:
    """
    Tracks efficiency metrics throughout a session.

    Usage:
        tracker = EfficiencyTracker(session_id="abc123")

        # Record events
        tracker.record_duplicate_skipped()
        tracker.record_pattern_match()
        tracker.record_insight_received(insight_content)

        # Get summary
        summary = tracker.get_summary()
        print(f"Tokens saved: {summary['tokens_estimated_saved']}")
    """

    STATE_FILE_NAME = "efficiency-metrics.json"

    def __init__(self, session_id: str = ""):
        """
        Initialize efficiency tracker.

        Args:
            session_id: Session identifier for grouping metrics
        """
        self.session_id = session_id or self._generate_session_id()
        self.metrics = EfficiencyMetrics(session_id=self.session_id)
        self.state_file = self._get_state_file_path()

        # Load existing metrics if resuming session
        self._load_state()

    def _generate_session_id(self) -> str:
        """Generate a session ID."""
        import hashlib
        return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]

    def _get_state_file_path(self) -> Path:
        """Get path to state file."""
        # Try project-local first
        local_dir = Path.cwd() / ".claude" / "popkit"
        if local_dir.exists():
            return local_dir / self.STATE_FILE_NAME

        # Fall back to home directory
        home_dir = Path.home() / ".claude" / "popkit"
        home_dir.mkdir(parents=True, exist_ok=True)
        return home_dir / self.STATE_FILE_NAME

    def _load_state(self):
        """Load existing state if present."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    # Only load if same session
                    if data.get("session_id") == self.session_id:
                        self.metrics = EfficiencyMetrics.from_dict(data)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_state(self):
        """Save current state."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except IOError:
            pass

    # =========================================================================
    # RECORDING METHODS
    # =========================================================================

    def record_duplicate_skipped(self, similarity: float = 0.0):
        """
        Record that a duplicate insight was skipped.

        Args:
            similarity: Similarity score of the duplicate (0.0-1.0)
        """
        self.metrics.duplicates_skipped += 1
        self._save_state()

    def record_pattern_match(self, pattern_id: str = "", similarity: float = 0.0):
        """
        Record that a collective pattern was matched.

        Args:
            pattern_id: ID of the matched pattern
            similarity: Similarity score
        """
        self.metrics.patterns_matched += 1
        self._save_state()

    def record_insight_shared(self, content: str = ""):
        """
        Record that an insight was shared.

        Args:
            content: Insight content (for length tracking)
        """
        self.metrics.insights_shared += 1
        if content:
            self.metrics.insight_lengths.append(len(content))
        self._save_state()

    def record_insight_received(self, content: str = ""):
        """
        Record that an insight was received.

        Args:
            content: Insight content (for length tracking)
        """
        self.metrics.insights_received += 1
        if content:
            self.metrics.insight_lengths.append(len(content))
        self._save_state()

    def record_context_reuse(self):
        """Record that semantic search was used for context."""
        self.metrics.context_reuse_count += 1
        self._save_state()

    def record_bug_detected(self, bug_type: str = ""):
        """
        Record that a bug was detected.

        Args:
            bug_type: Type of bug detected
        """
        self.metrics.bugs_detected += 1
        self._save_state()

    def record_stuck_pattern(self):
        """Record that a stuck pattern was detected."""
        self.metrics.stuck_patterns_detected += 1
        self._save_state()

    def record_tool_call(self):
        """Record a tool call."""
        self.metrics.tool_calls += 1
        self._save_state()

    def record_resolution_time(self, ms: int):
        """
        Record bug resolution time.

        Args:
            ms: Time in milliseconds from detection to fix
        """
        self.metrics.resolution_times_ms.append(ms)
        self._save_state()

    def record_sync_barrier(self):
        """Record a Power Mode sync barrier."""
        self.metrics.sync_barriers_hit += 1
        self._save_state()

    def record_duplicate_work_prevented(self):
        """Record that duplicate work was prevented in Power Mode."""
        self.metrics.duplicate_work_prevented += 1
        self._save_state()

    # =========================================================================
    # CALCULATION METHODS
    # =========================================================================

    def estimate_tokens_saved(self) -> int:
        """
        Estimate total tokens saved by PopKit.

        Returns:
            Estimated tokens saved
        """
        # Duplicate insight savings
        duplicate_savings = self.metrics.duplicates_skipped * TOKENS_PER_DUPLICATE_INSIGHT

        # Pattern match savings (avoided debugging)
        pattern_savings = self.metrics.patterns_matched * TOKENS_PER_PATTERN_MATCH

        # Context reuse savings (semantic search vs brute force)
        context_savings = self.metrics.context_reuse_count * TOKENS_PER_CONTEXT_REUSE

        # Insight reuse (actual content length)
        insight_savings = int(sum(self.metrics.insight_lengths) * TOKENS_PER_INSIGHT_CHAR)

        # Bug detection savings
        bug_savings = self.metrics.bugs_detected * TOKENS_PER_BUG_DETECTION
        stuck_savings = self.metrics.stuck_patterns_detected * TOKENS_PER_STUCK_DETECTION

        return (
            duplicate_savings +
            pattern_savings +
            context_savings +
            insight_savings +
            bug_savings +
            stuck_savings
        )

    def get_efficiency_score(self) -> float:
        """
        Calculate an overall efficiency score (0-100).

        Returns:
            Efficiency score
        """
        if self.metrics.tool_calls == 0:
            return 0.0

        # Factors that contribute to efficiency
        factors = []

        # Dedup rate (higher = more efficient)
        if self.metrics.insights_shared > 0:
            dedup_rate = self.metrics.duplicates_skipped / self.metrics.insights_shared
            factors.append(min(dedup_rate * 100, 25))  # Max 25 points

        # Pattern match rate (higher = more helpful patterns)
        if self.metrics.tool_calls > 0:
            pattern_rate = self.metrics.patterns_matched / self.metrics.tool_calls
            factors.append(min(pattern_rate * 500, 25))  # Max 25 points

        # Bug detection (higher = caught more issues early)
        total_bugs = self.metrics.bugs_detected + self.metrics.stuck_patterns_detected
        factors.append(min(total_bugs * 5, 25))  # Max 25 points

        # Insight sharing (collaboration)
        if self.metrics.insights_shared > 0 and self.metrics.insights_received > 0:
            collab_ratio = min(
                self.metrics.insights_received / self.metrics.insights_shared,
                self.metrics.insights_shared / self.metrics.insights_received
            )
            factors.append(collab_ratio * 25)  # Max 25 points

        return min(sum(factors), 100.0)

    def get_summary(self) -> Dict:
        """
        Get a summary of efficiency metrics.

        Returns:
            Summary dictionary
        """
        tokens_saved = self.estimate_tokens_saved()
        efficiency_score = self.get_efficiency_score()

        return {
            "session_id": self.session_id,
            "started_at": self.metrics.started_at,

            # Raw metrics
            "duplicates_skipped": self.metrics.duplicates_skipped,
            "patterns_matched": self.metrics.patterns_matched,
            "insights_shared": self.metrics.insights_shared,
            "insights_received": self.metrics.insights_received,
            "context_reuse_count": self.metrics.context_reuse_count,
            "bugs_detected": self.metrics.bugs_detected,
            "stuck_patterns_detected": self.metrics.stuck_patterns_detected,
            "tool_calls": self.metrics.tool_calls,

            # Calculated
            "tokens_estimated_saved": tokens_saved,
            "efficiency_score": round(efficiency_score, 1),

            # Power Mode specific
            "sync_barriers_hit": self.metrics.sync_barriers_hit,
            "duplicate_work_prevented": self.metrics.duplicate_work_prevented,

            # Derived
            "avg_resolution_time_ms": (
                int(sum(self.metrics.resolution_times_ms) / len(self.metrics.resolution_times_ms))
                if self.metrics.resolution_times_ms else None
            )
        }

    def get_compact_summary(self) -> str:
        """
        Get a one-line summary for status line.

        Returns:
            Compact summary string
        """
        summary = self.get_summary()
        tokens = summary["tokens_estimated_saved"]

        # Format tokens nicely
        if tokens >= 1000:
            tokens_str = f"{tokens/1000:.1f}k"
        else:
            tokens_str = str(tokens)

        return f"~{tokens_str} tokens saved | {summary['efficiency_score']}% efficient"

    # =========================================================================
    # CLOUD SYNC
    # =========================================================================

    def sync_to_cloud(self, cloud_client: Any) -> bool:
        """
        Sync metrics to PopKit Cloud.

        Args:
            cloud_client: PopKit Cloud client instance

        Returns:
            True if synced successfully
        """
        if not cloud_client or not hasattr(cloud_client, 'connected') or not cloud_client.connected:
            return False

        try:
            summary = self.get_summary()

            # Use the analytics endpoint
            response = cloud_client._request("POST", "/analytics/efficiency", {
                "session_id": summary["session_id"],
                "duplicates_skipped": summary["duplicates_skipped"],
                "patterns_matched": summary["patterns_matched"],
                "insights_shared": summary["insights_shared"],
                "insights_received": summary["insights_received"],
                "tokens_estimated_saved": summary["tokens_estimated_saved"],
                "tool_calls": summary["tool_calls"],
                "resolution_time_ms": summary.get("avg_resolution_time_ms")
            })

            return response.get("status") == "recorded"

        except Exception:
            return False

    def reset(self):
        """Reset metrics for a new session."""
        self.session_id = self._generate_session_id()
        self.metrics = EfficiencyMetrics(session_id=self.session_id)
        self._save_state()


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_tracker_instance: Optional[EfficiencyTracker] = None


def get_tracker(session_id: str = "") -> EfficiencyTracker:
    """
    Get or create the global efficiency tracker.

    Args:
        session_id: Session ID (creates new if different from current)

    Returns:
        EfficiencyTracker instance
    """
    global _tracker_instance

    if _tracker_instance is None:
        _tracker_instance = EfficiencyTracker(session_id)
    elif session_id and session_id != _tracker_instance.session_id:
        _tracker_instance = EfficiencyTracker(session_id)

    return _tracker_instance


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    print("Efficiency Tracker Test")
    print("=" * 40)

    tracker = EfficiencyTracker(session_id="test-session")

    # Simulate some events
    tracker.record_duplicate_skipped()
    tracker.record_duplicate_skipped()
    tracker.record_pattern_match()
    tracker.record_insight_shared("Found auth configuration in src/config/auth.ts")
    tracker.record_insight_received("Using JWT for authentication")
    tracker.record_context_reuse()
    tracker.record_bug_detected("TypeError")
    tracker.record_tool_call()
    tracker.record_tool_call()
    tracker.record_tool_call()

    # Get summary
    summary = tracker.get_summary()

    print("\nMetrics Summary:")
    print(f"  Duplicates skipped: {summary['duplicates_skipped']}")
    print(f"  Patterns matched: {summary['patterns_matched']}")
    print(f"  Insights shared: {summary['insights_shared']}")
    print(f"  Insights received: {summary['insights_received']}")
    print(f"  Bugs detected: {summary['bugs_detected']}")
    print(f"  Tool calls: {summary['tool_calls']}")

    print(f"\nEstimated tokens saved: {summary['tokens_estimated_saved']}")
    print(f"Efficiency score: {summary['efficiency_score']}%")

    print(f"\nCompact: {tracker.get_compact_summary()}")
