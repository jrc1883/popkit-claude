#!/usr/bin/env python3
"""
Tests for Vote Fetcher module

Part of Issue #92 - Vote-Based Feature Prioritization
"""

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.vote_fetcher import (
    VoteResult,
    VoteCache,
    VoteFetcher,
    DEFAULT_WEIGHTS,
)


class TestVoteResult(unittest.TestCase):
    """Tests for VoteResult dataclass"""

    def test_to_dict(self):
        """Should convert to dictionary"""
        result = VoteResult(
            issue_number=42,
            score=10,
            breakdown={'+1': 5, 'heart': 2, 'rocket': 1},
            total_reactions=8,
            fetched_at="2025-01-15T10:00:00Z"
        )

        d = result.to_dict()

        self.assertEqual(d['issue_number'], 42)
        self.assertEqual(d['score'], 10)
        self.assertEqual(d['total_reactions'], 8)
        self.assertIn('+1', d['breakdown'])

    def test_cached_flag(self):
        """Should track cached status"""
        fresh = VoteResult(
            issue_number=1,
            score=5,
            breakdown={},
            total_reactions=5,
            fetched_at="2025-01-15T10:00:00Z",
            cached=False
        )
        self.assertFalse(fresh.cached)

        cached = VoteResult(
            issue_number=1,
            score=5,
            breakdown={},
            total_reactions=5,
            fetched_at="2025-01-15T10:00:00Z",
            cached=True
        )
        self.assertTrue(cached.cached)


class TestDefaultWeights(unittest.TestCase):
    """Tests for default reaction weights"""

    def test_positive_reactions_have_positive_weight(self):
        """Positive reactions should increase score"""
        self.assertGreater(DEFAULT_WEIGHTS['+1'], 0)
        self.assertGreater(DEFAULT_WEIGHTS['heart'], 0)
        self.assertGreater(DEFAULT_WEIGHTS['rocket'], 0)

    def test_rocket_highest_weight(self):
        """Rocket should have highest weight"""
        self.assertGreater(DEFAULT_WEIGHTS['rocket'], DEFAULT_WEIGHTS['heart'])
        self.assertGreater(DEFAULT_WEIGHTS['heart'], DEFAULT_WEIGHTS['+1'])

    def test_negative_reactions_have_negative_weight(self):
        """Negative reactions should decrease score"""
        self.assertLess(DEFAULT_WEIGHTS['-1'], 0)
        self.assertLess(DEFAULT_WEIGHTS['confused'], 0)

    def test_neutral_reactions_have_zero_weight(self):
        """Neutral reactions should have zero weight"""
        self.assertEqual(DEFAULT_WEIGHTS['eyes'], 0)
        self.assertEqual(DEFAULT_WEIGHTS['laugh'], 0)


class TestVoteCache(unittest.TestCase):
    """Tests for VoteCache SQLite storage"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_votes.db"
        self.cache = VoteCache(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_database(self):
        """Should create database file"""
        self.assertTrue(self.db_path.exists())

    def test_creates_table(self):
        """Should create vote_cache table"""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        self.assertIn("vote_cache", tables)

    def test_set_stores_data(self):
        """Should store vote results in database"""
        import sqlite3

        result = VoteResult(
            issue_number=42,
            score=15,
            breakdown={'+1': 10, 'rocket': 1},
            total_reactions=11,
            fetched_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        self.cache.set("owner/repo", result)

        # Verify data is stored
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT * FROM vote_cache WHERE repo = ? AND issue_number = ?",
            ("owner/repo", 42)
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], 42)  # issue_number
        self.assertEqual(row[2], 15)  # score

    def test_get_returns_none_for_missing(self):
        """Should return None for missing entries"""
        result = self.cache.get("owner/repo", 999)
        self.assertIsNone(result)

    def test_get_returns_none_for_expired(self):
        """Should return None for expired entries"""
        import sqlite3

        # Insert expired entry directly
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT INTO vote_cache
            (repo, issue_number, score, breakdown, total_reactions, fetched_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', '-2 hours'))
        """, ("owner/repo", 42, 10, '{}', 10))
        conn.commit()
        conn.close()

        result = self.cache.get("owner/repo", 42)
        self.assertIsNone(result)

    def test_clear_all(self):
        """Should clear all cached entries"""
        result = VoteResult(
            issue_number=1,
            score=5,
            breakdown={},
            total_reactions=5,
            fetched_at=datetime.now().isoformat()
        )
        self.cache.set("repo", result)

        cleared = self.cache.clear_all()
        self.assertGreater(cleared, 0)

        retrieved = self.cache.get("repo", 1)
        self.assertIsNone(retrieved)


class TestVoteFetcher(unittest.TestCase):
    """Tests for VoteFetcher"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_votes.db"
        self.cache = VoteCache(self.db_path)
        self.fetcher = VoteFetcher(cache=self.cache)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_reactions(self, counts):
        """Helper to create reaction list from counts dict"""
        reactions = []
        for content, count in counts.items():
            for _ in range(count):
                reactions.append({'content': content})
        return reactions

    def test_calculate_score_basic(self):
        """Should calculate score from reactions"""
        reactions = self._make_reactions({'+1': 5, 'heart': 2, 'rocket': 1})
        score, breakdown, total = self.fetcher.calculate_score(reactions)

        expected = (5 * 1) + (2 * 2) + (1 * 3)  # 5 + 4 + 3 = 12
        self.assertEqual(score, expected)
        self.assertEqual(total, 8)

    def test_calculate_score_with_negative(self):
        """Should handle negative reactions"""
        reactions = self._make_reactions({'+1': 10, '-1': 3})
        score, breakdown, total = self.fetcher.calculate_score(reactions)

        expected = (10 * 1) + (3 * -1)  # 10 - 3 = 7
        self.assertEqual(score, expected)

    def test_calculate_score_ignores_neutral(self):
        """Should ignore neutral reactions"""
        reactions = self._make_reactions({'+1': 5, 'eyes': 100, 'laugh': 50})
        score, breakdown, total = self.fetcher.calculate_score(reactions)

        expected = 5 * 1  # Only +1 counts
        self.assertEqual(score, expected)
        self.assertEqual(total, 155)  # All reactions counted

    def test_calculate_score_empty(self):
        """Should return 0 for empty reactions"""
        score, breakdown, total = self.fetcher.calculate_score([])
        self.assertEqual(score, 0)
        self.assertEqual(total, 0)

    def test_custom_weights(self):
        """Should use custom weights"""
        custom_weights = {'+1': 10, 'heart': 5}
        fetcher = VoteFetcher(weights=custom_weights, cache=self.cache)

        reactions = self._make_reactions({'+1': 2, 'heart': 1})
        score, breakdown, total = fetcher.calculate_score(reactions)

        expected = (2 * 10) + (1 * 5)  # 20 + 5 = 25
        self.assertEqual(score, expected)

    def test_custom_weights_initialization(self):
        """Should accept custom weights at initialization"""
        custom_weights = {'+1': 100}
        fetcher = VoteFetcher(weights=custom_weights, cache=self.cache)

        self.assertEqual(fetcher.weights['+1'], 100)


class TestScoreCalculation(unittest.TestCase):
    """Tests for score calculation edge cases"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_votes.db"
        self.cache = VoteCache(self.db_path)
        self.fetcher = VoteFetcher(cache=self.cache)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_reactions(self, counts):
        """Helper to create reaction list from counts dict"""
        reactions = []
        for content, count in counts.items():
            for _ in range(count):
                reactions.append({'content': content})
        return reactions

    def test_all_reaction_types(self):
        """Should handle all reaction types"""
        reactions = self._make_reactions({
            '+1': 10,
            '-1': 2,
            'heart': 5,
            'rocket': 3,
            'hooray': 4,
            'confused': 1,
            'eyes': 20,
            'laugh': 15
        })

        score, breakdown, total = self.fetcher.calculate_score(reactions)

        # +1: 10*1=10, -1: 2*-1=-2, heart: 5*2=10, rocket: 3*3=9
        # hooray: 4*1=4, confused: 1*-1=-1, eyes: 0, laugh: 0
        expected = 10 - 2 + 10 + 9 + 4 - 1
        self.assertEqual(score, expected)

    def test_large_numbers(self):
        """Should handle large reaction counts"""
        reactions = self._make_reactions({'+1': 1000, 'rocket': 500})
        score, breakdown, total = self.fetcher.calculate_score(reactions)

        expected = 1000 + (500 * 3)
        self.assertEqual(score, expected)

    def test_negative_score_possible(self):
        """Should allow negative total score"""
        reactions = self._make_reactions({'-1': 100, 'confused': 50})
        score, breakdown, total = self.fetcher.calculate_score(reactions)

        expected = -100 - 50
        self.assertEqual(score, expected)


if __name__ == "__main__":
    unittest.main()
