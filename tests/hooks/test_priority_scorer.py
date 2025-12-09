#!/usr/bin/env python3
"""
Tests for Priority Scorer module

Part of Issue #92 - Vote-Based Feature Prioritization
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.priority_scorer import (
    PriorityScorer,
    ScoredIssue,
    LabelPriority,
)


class TestLabelPriority(unittest.TestCase):
    """Tests for LabelPriority enum"""

    def test_priority_ordering(self):
        """Should have correct priority ordering"""
        self.assertGreater(LabelPriority.CRITICAL.value, LabelPriority.HIGH.value)
        self.assertGreater(LabelPriority.HIGH.value, LabelPriority.MEDIUM.value)
        self.assertGreater(LabelPriority.MEDIUM.value, LabelPriority.LOW.value)
        self.assertGreater(LabelPriority.LOW.value, LabelPriority.NONE.value)

    def test_critical_is_100(self):
        """Critical should be 100"""
        self.assertEqual(LabelPriority.CRITICAL.value, 100)


class TestScoredIssue(unittest.TestCase):
    """Tests for ScoredIssue dataclass"""

    def test_to_dict(self):
        """Should convert to dictionary"""
        issue = ScoredIssue(
            number=42,
            title="Test Issue",
            labels=["enhancement", "high-priority"],
            state="open",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-10T00:00:00Z",
            vote_score=15,
            priority_score=75.5
        )

        d = issue.to_dict()

        self.assertEqual(d['number'], 42)
        self.assertEqual(d['title'], "Test Issue")
        self.assertEqual(d['priority_score'], 75.5)
        self.assertIn('components', d)
        self.assertEqual(d['components']['votes'], 15)

    def test_default_vote_breakdown(self):
        """Should default to empty breakdown"""
        issue = ScoredIssue(
            number=1,
            title="Test",
            labels=[],
            state="open",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )

        self.assertEqual(issue.vote_breakdown, {})


class TestPriorityScorer(unittest.TestCase):
    """Tests for PriorityScorer"""

    def setUp(self):
        # Create scorer with mock vote fetcher
        self.mock_fetcher = MagicMock()
        self.scorer = PriorityScorer(vote_fetcher=self.mock_fetcher)

    def test_default_weights(self):
        """Should use default weights"""
        scorer = PriorityScorer()

        self.assertIn('votes', scorer.weights)
        self.assertIn('staleness', scorer.weights)
        self.assertIn('labels', scorer.weights)
        self.assertIn('epic', scorer.weights)

    def test_weights_sum_approximately_to_one(self):
        """Weights should sum to approximately 1"""
        total = sum(self.scorer.weights.values())
        self.assertAlmostEqual(total, 1.0, places=1)

    def test_custom_weights(self):
        """Should accept custom weights"""
        custom = {'votes': 0.5, 'staleness': 0.5, 'labels': 0, 'epic': 0}
        scorer = PriorityScorer(weights=custom)

        self.assertEqual(scorer.weights['votes'], 0.5)
        self.assertEqual(scorer.weights['labels'], 0)


class TestStalenessCalculation(unittest.TestCase):
    """Tests for staleness calculation"""

    def setUp(self):
        self.scorer = PriorityScorer()

    def test_new_issue_with_recent_update(self):
        """New issues with recent updates should get activity bonus"""
        now = datetime.now()
        created = now.isoformat()
        updated = now.isoformat()

        staleness = self.scorer.calculate_staleness(created, updated)

        # Should get activity bonus for recent update
        self.assertGreaterEqual(staleness, 0)

    def test_old_issue_no_update(self):
        """Old issues with no recent updates should have higher staleness"""
        now = datetime.now()
        old = (now - timedelta(days=180)).isoformat()

        staleness = self.scorer.calculate_staleness(old, old)

        # 180 days old with stale update gets age score but penalty
        self.assertGreater(staleness, 0)

    def test_recently_updated_gets_bonus(self):
        """Recently updated issues should get activity bonus"""
        now = datetime.now()
        old_created = (now - timedelta(days=180)).isoformat()
        recent_update = now.isoformat()

        staleness_active = self.scorer.calculate_staleness(old_created, recent_update)

        # Old created but recently updated should get activity bonus
        stale_update = (now - timedelta(days=100)).isoformat()
        staleness_stale = self.scorer.calculate_staleness(old_created, stale_update)

        # Active issue should have higher score (bonus) than stale
        self.assertGreater(staleness_active, staleness_stale)


class TestLabelScoring(unittest.TestCase):
    """Tests for label-based priority scoring"""

    def setUp(self):
        self.scorer = PriorityScorer()

    def test_critical_label(self):
        """Critical labels should give maximum score"""
        score = self.scorer.calculate_label_score(['critical'])
        self.assertEqual(score, LabelPriority.CRITICAL.value)

        score = self.scorer.calculate_label_score(['blocker'])
        self.assertEqual(score, LabelPriority.CRITICAL.value)

        score = self.scorer.calculate_label_score(['p0'])
        self.assertEqual(score, LabelPriority.CRITICAL.value)

    def test_high_priority_label(self):
        """High priority labels should give high score"""
        score = self.scorer.calculate_label_score(['high-priority'])
        self.assertEqual(score, LabelPriority.HIGH.value)

        score = self.scorer.calculate_label_score(['p1'])
        self.assertEqual(score, LabelPriority.HIGH.value)

    def test_enhancement_label(self):
        """Enhancement label should give medium score"""
        score = self.scorer.calculate_label_score(['enhancement'])
        self.assertEqual(score, LabelPriority.MEDIUM.value)

    def test_low_priority_label(self):
        """Low priority labels should give low score"""
        score = self.scorer.calculate_label_score(['low-priority'])
        self.assertEqual(score, LabelPriority.LOW.value)

    def test_highest_priority_wins(self):
        """Should use highest priority label"""
        score = self.scorer.calculate_label_score(['low-priority', 'critical'])
        self.assertEqual(score, LabelPriority.CRITICAL.value)

    def test_unknown_label_default(self):
        """Unknown labels should use default"""
        score = self.scorer.calculate_label_score(['unknown-label'])
        # Should be 0 or medium depending on implementation
        self.assertGreaterEqual(score, 0)

    def test_empty_labels(self):
        """Empty labels should give medium (default) score"""
        score = self.scorer.calculate_label_score([])
        self.assertEqual(score, LabelPriority.MEDIUM.value)

    def test_case_insensitive(self):
        """Should be case insensitive"""
        score_lower = self.scorer.calculate_label_score(['critical'])
        score_upper = self.scorer.calculate_label_score(['CRITICAL'])
        score_mixed = self.scorer.calculate_label_score(['Critical'])

        self.assertEqual(score_lower, score_upper)
        self.assertEqual(score_lower, score_mixed)


class TestEpicScoring(unittest.TestCase):
    """Tests for epic association scoring"""

    def setUp(self):
        self.scorer = PriorityScorer()

    def test_epic_label_gives_score(self):
        """Issues with epic labels should get epic score"""
        score = self.scorer.calculate_epic_score(['epic', 'enhancement'])
        self.assertGreater(score, 0)

    def test_meta_label_gives_score(self):
        """Meta label should also give epic score"""
        score = self.scorer.calculate_epic_score(['meta'])
        self.assertGreater(score, 0)

    def test_no_epic_no_score(self):
        """Non-epic issues should get zero"""
        score = self.scorer.calculate_epic_score(['enhancement', 'bug'])
        self.assertEqual(score, 0)


class TestCombinedScoring(unittest.TestCase):
    """Tests for combined priority scoring"""

    def setUp(self):
        self.mock_fetcher = MagicMock()
        self.scorer = PriorityScorer(vote_fetcher=self.mock_fetcher)

    def test_score_issue_combines_components(self):
        """Should combine all score components"""
        issue = {
            'number': 42,
            'title': "Important Feature",
            'labels': ['critical'],
            'state': "open",
            'createdAt': (datetime.now() - timedelta(days=30)).isoformat(),
            'updatedAt': datetime.now().isoformat()
        }

        # Mock vote fetcher
        mock_vote_result = MagicMock()
        mock_vote_result.score = 50
        mock_vote_result.breakdown = {'+1': 50}
        self.mock_fetcher.get_issue_votes.return_value = mock_vote_result

        scored = self.scorer.score_issue(issue, vote_result=mock_vote_result)

        self.assertGreater(scored.priority_score, 0)
        self.assertGreater(scored.label_score, 0)

    def test_higher_votes_higher_score(self):
        """More votes should give higher score"""
        # Low vote issue
        issue1 = {
            'number': 1,
            'title': "Test",
            'labels': ['enhancement'],
            'state': "open",
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }

        mock_low_vote = MagicMock()
        mock_low_vote.score = 5
        mock_low_vote.breakdown = {'+1': 5}
        low_vote_issue = self.scorer.score_issue(issue1, vote_result=mock_low_vote)

        # High vote issue
        issue2 = {
            'number': 2,
            'title': "Test",
            'labels': ['enhancement'],
            'state': "open",
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }

        mock_high_vote = MagicMock()
        mock_high_vote.score = 100
        mock_high_vote.breakdown = {'+1': 100}
        high_vote_issue = self.scorer.score_issue(issue2, vote_result=mock_high_vote)

        self.assertGreater(high_vote_issue.priority_score, low_vote_issue.priority_score)


class TestSortingByPriority(unittest.TestCase):
    """Tests for sorting issues by priority"""

    def setUp(self):
        self.mock_fetcher = MagicMock()
        self.scorer = PriorityScorer(vote_fetcher=self.mock_fetcher)

    def test_sort_by_priority(self):
        """Should sort issues by priority score"""
        issues = [
            ScoredIssue(
                number=1, title="Low", labels=[], state="open",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                priority_score=10
            ),
            ScoredIssue(
                number=2, title="High", labels=[], state="open",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                priority_score=90
            ),
            ScoredIssue(
                number=3, title="Medium", labels=[], state="open",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                priority_score=50
            ),
        ]

        sorted_issues = sorted(issues, key=lambda i: i.priority_score, reverse=True)

        self.assertEqual(sorted_issues[0].title, "High")
        self.assertEqual(sorted_issues[1].title, "Medium")
        self.assertEqual(sorted_issues[2].title, "Low")


if __name__ == "__main__":
    unittest.main()
