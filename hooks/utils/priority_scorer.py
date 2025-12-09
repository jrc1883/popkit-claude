#!/usr/bin/env python3
"""
Priority Scorer - Combined Priority Calculation

Part of Issue #92 (Vote-Based Feature Prioritization)
Parent: Epic #88 (Self-Improvement & Learning System)

Calculates combined priority scores for GitHub issues using:
- Community votes (GitHub reactions)
- Staleness (how long the issue has been open)
- Labels (priority labels like P0, P1, critical)
- Epic association (child issues of epics)
"""

import subprocess
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class LabelPriority(Enum):
    """Priority levels from labels"""
    CRITICAL = 100    # critical, blocker, P0
    HIGH = 75         # high-priority, P1, important
    MEDIUM = 50       # enhancement, P2 (default)
    LOW = 25          # low-priority, P3, nice-to-have
    NONE = 0


@dataclass
class ScoredIssue:
    """An issue with calculated priority score"""
    number: int
    title: str
    labels: List[str]
    state: str
    created_at: str
    updated_at: str

    # Component scores
    vote_score: int = 0
    staleness_score: float = 0.0
    label_score: float = 0.0
    epic_score: float = 0.0

    # Final combined score
    priority_score: float = 0.0

    # Vote breakdown for display
    vote_breakdown: Dict[str, int] = None

    def __post_init__(self):
        if self.vote_breakdown is None:
            self.vote_breakdown = {}

    def to_dict(self) -> dict:
        return {
            'number': self.number,
            'title': self.title,
            'labels': self.labels,
            'state': self.state,
            'priority_score': round(self.priority_score, 2),
            'components': {
                'votes': self.vote_score,
                'staleness': round(self.staleness_score, 2),
                'labels': round(self.label_score, 2),
                'epic': round(self.epic_score, 2)
            },
            'vote_breakdown': self.vote_breakdown
        }


class PriorityScorer:
    """
    Calculates combined priority scores for issues.

    Score = (vote_weight × votes) + (staleness_weight × staleness)
          + (label_weight × labels) + (epic_weight × epic)
    """

    # Default weights (should sum to ~1.0 for normalization)
    DEFAULT_WEIGHTS = {
        'votes': 0.35,      # Community interest
        'staleness': 0.20,  # How long waiting
        'labels': 0.30,     # Explicit priority
        'epic': 0.15        # Part of epic
    }

    # Label priority mappings
    LABEL_PRIORITIES = {
        # Critical (100)
        'critical': LabelPriority.CRITICAL,
        'blocker': LabelPriority.CRITICAL,
        'p0': LabelPriority.CRITICAL,
        'urgent': LabelPriority.CRITICAL,

        # High (75)
        'high-priority': LabelPriority.HIGH,
        'high': LabelPriority.HIGH,
        'p1': LabelPriority.HIGH,
        'important': LabelPriority.HIGH,

        # Medium (50) - default for enhancement
        'enhancement': LabelPriority.MEDIUM,
        'feature': LabelPriority.MEDIUM,
        'p2': LabelPriority.MEDIUM,

        # Low (25)
        'low-priority': LabelPriority.LOW,
        'low': LabelPriority.LOW,
        'p3': LabelPriority.LOW,
        'nice-to-have': LabelPriority.LOW,
        'wontfix': LabelPriority.NONE,
    }

    # Epic labels
    EPIC_LABELS = {'epic', 'meta', 'umbrella', 'parent'}

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        vote_fetcher=None
    ):
        """
        Initialize the priority scorer.

        Args:
            weights: Custom component weights
            vote_fetcher: VoteFetcher instance for getting vote scores
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._vote_fetcher = vote_fetcher

    @property
    def vote_fetcher(self):
        """Lazy-load vote fetcher"""
        if self._vote_fetcher is None:
            from vote_fetcher import get_vote_fetcher
            self._vote_fetcher = get_vote_fetcher()
        return self._vote_fetcher

    def calculate_staleness(self, created_at: str, updated_at: str) -> float:
        """
        Calculate staleness score based on age and activity.

        Args:
            created_at: ISO timestamp of issue creation
            updated_at: ISO timestamp of last update

        Returns:
            Staleness score (0-100)
        """
        now = datetime.now()

        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return 50.0  # Default middle score

        # Make datetimes offset-naive for comparison
        if created.tzinfo:
            created = created.replace(tzinfo=None)
        if updated.tzinfo:
            updated = updated.replace(tzinfo=None)

        # Age in days
        age_days = (now - created).days

        # Days since last update
        stale_days = (now - updated).days

        # Score formula:
        # - Older issues get higher base score (up to 50)
        # - Recently updated issues get bonus (up to 30)
        # - Very stale issues (>90 days no update) get penalty

        age_score = min(age_days / 30 * 10, 50)  # Max 50 for age

        if stale_days < 7:
            activity_bonus = 30  # Very active
        elif stale_days < 30:
            activity_bonus = 20  # Moderately active
        elif stale_days < 90:
            activity_bonus = 10  # Somewhat active
        else:
            activity_bonus = -10  # Stale penalty

        return max(0, min(100, age_score + activity_bonus))

    def calculate_label_score(self, labels: List[str]) -> float:
        """
        Calculate priority score from labels.

        Args:
            labels: List of label names

        Returns:
            Label score (0-100)
        """
        if not labels:
            return LabelPriority.MEDIUM.value  # Default

        # Find highest priority label
        max_priority = LabelPriority.NONE

        for label in labels:
            label_lower = label.lower()
            priority = self.LABEL_PRIORITIES.get(label_lower)
            if priority and priority.value > max_priority.value:
                max_priority = priority

        # If no priority label found, default to medium for enhancements
        if max_priority == LabelPriority.NONE:
            if any('bug' in l.lower() for l in labels):
                return LabelPriority.HIGH.value  # Bugs are high priority
            return LabelPriority.MEDIUM.value

        return max_priority.value

    def calculate_epic_score(self, labels: List[str], parent_issue: Optional[int] = None) -> float:
        """
        Calculate epic association score.

        Args:
            labels: Issue labels
            parent_issue: Parent epic issue number if known

        Returns:
            Epic score (0 or bonus)
        """
        # Is this issue itself an epic?
        is_epic = any(l.lower() in self.EPIC_LABELS for l in labels)
        if is_epic:
            return 100.0  # Epics are high priority

        # Is this a child of an epic?
        if parent_issue:
            return 75.0  # Part of tracked epic

        return 0.0

    def score_issue(
        self,
        issue: Dict[str, Any],
        vote_result=None,
        parent_epic: Optional[int] = None
    ) -> ScoredIssue:
        """
        Calculate complete priority score for an issue.

        Args:
            issue: Issue dict from GitHub API
            vote_result: Pre-fetched VoteResult (optional)
            parent_epic: Parent epic issue number (optional)

        Returns:
            ScoredIssue with all scores calculated
        """
        number = issue.get('number', 0)
        title = issue.get('title', '')
        labels = [l.get('name', l) if isinstance(l, dict) else l
                  for l in issue.get('labels', [])]
        state = issue.get('state', 'open')
        created_at = issue.get('createdAt', issue.get('created_at', ''))
        updated_at = issue.get('updatedAt', issue.get('updated_at', created_at))

        # Get vote score
        if vote_result:
            vote_score = vote_result.score
            vote_breakdown = vote_result.breakdown
        else:
            try:
                vote_result = self.vote_fetcher.get_issue_votes(number)
                vote_score = vote_result.score
                vote_breakdown = vote_result.breakdown
            except Exception:
                vote_score = 0
                vote_breakdown = {}

        # Calculate component scores
        staleness_score = self.calculate_staleness(created_at, updated_at)
        label_score = self.calculate_label_score(labels)
        epic_score = self.calculate_epic_score(labels, parent_epic)

        # Normalize vote score to 0-100 range (cap at 50 votes worth)
        normalized_vote = min(vote_score * 2, 100) if vote_score > 0 else max(vote_score * 2, -50)

        # Calculate weighted final score
        priority_score = (
            self.weights['votes'] * normalized_vote +
            self.weights['staleness'] * staleness_score +
            self.weights['labels'] * label_score +
            self.weights['epic'] * epic_score
        )

        return ScoredIssue(
            number=number,
            title=title,
            labels=labels,
            state=state,
            created_at=created_at,
            updated_at=updated_at,
            vote_score=vote_score,
            staleness_score=staleness_score,
            label_score=label_score,
            epic_score=epic_score,
            priority_score=priority_score,
            vote_breakdown=vote_breakdown
        )

    def rank_issues(
        self,
        issues: List[Dict[str, Any]],
        vote_results: Optional[Dict[int, Any]] = None,
        epic_map: Optional[Dict[int, int]] = None
    ) -> List[ScoredIssue]:
        """
        Rank a list of issues by priority score.

        Args:
            issues: List of issue dicts from GitHub API
            vote_results: Pre-fetched vote results keyed by issue number
            epic_map: Map of issue number to parent epic number

        Returns:
            List of ScoredIssues sorted by priority (highest first)
        """
        vote_results = vote_results or {}
        epic_map = epic_map or {}

        scored = []
        for issue in issues:
            number = issue.get('number', 0)
            vote_result = vote_results.get(number)
            parent_epic = epic_map.get(number)

            scored_issue = self.score_issue(issue, vote_result, parent_epic)
            scored.append(scored_issue)

        # Sort by priority score (highest first)
        return sorted(scored, key=lambda x: -x.priority_score)

    def format_ranked_list(
        self,
        scored_issues: List[ScoredIssue],
        show_components: bool = False,
        max_items: int = 10
    ) -> str:
        """
        Format ranked issues for display.

        Args:
            scored_issues: List of scored issues
            show_components: Whether to show score breakdown
            max_items: Maximum items to show

        Returns:
            Formatted string
        """
        lines = []

        for i, issue in enumerate(scored_issues[:max_items], 1):
            # Vote display
            vote_parts = []
            if issue.vote_breakdown.get('+1', 0):
                vote_parts.append(f"👍{issue.vote_breakdown['+1']}")
            if issue.vote_breakdown.get('heart', 0):
                vote_parts.append(f"❤️{issue.vote_breakdown['heart']}")
            if issue.vote_breakdown.get('rocket', 0):
                vote_parts.append(f"🚀{issue.vote_breakdown['rocket']}")
            vote_str = ' '.join(vote_parts) if vote_parts else ''

            # Main line
            title_truncated = issue.title[:40] + ('...' if len(issue.title) > 40 else '')
            line = f"#{issue.number} {title_truncated}"
            if vote_str:
                line += f"  {vote_str}"
            line += f"  Score: {issue.priority_score:.1f}"

            lines.append(line)

            # Component breakdown
            if show_components:
                lines.append(f"   Votes: {issue.vote_score} | Staleness: {issue.staleness_score:.0f} | "
                           f"Labels: {issue.label_score:.0f} | Epic: {issue.epic_score:.0f}")

        return '\n'.join(lines)


# Singleton instance
_scorer: Optional[PriorityScorer] = None


def get_priority_scorer() -> PriorityScorer:
    """Get the singleton PriorityScorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = PriorityScorer()
    return _scorer


def fetch_open_issues(limit: int = 20) -> List[Dict]:
    """Fetch open issues from current repository using gh CLI"""
    try:
        result = subprocess.run(
            ['gh', 'issue', 'list', '--limit', str(limit), '--state', 'open',
             '--json', 'number,title,labels,state,createdAt,updatedAt'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


if __name__ == "__main__":
    # Test the priority scorer
    scorer = PriorityScorer()

    print("Fetching open issues...")
    issues = fetch_open_issues(10)

    if issues:
        print(f"\nFound {len(issues)} issues. Scoring...\n")

        ranked = scorer.rank_issues(issues)

        print("=== Ranked Issues ===\n")
        print(scorer.format_ranked_list(ranked, show_components=True))
    else:
        print("No issues found or not in a git repository")
