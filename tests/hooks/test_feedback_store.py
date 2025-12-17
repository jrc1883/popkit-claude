#!/usr/bin/env python3
"""
Tests for Feedback Store module

Part of Issue #91 - User Feedback Collection System
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.feedback_store import (
    FeedbackStore,
    FeedbackEntry,
    FeedbackAggregate,
    FeedbackRating,
    ContextType,
    get_feedback_store,
)


class TestFeedbackStoreInit(unittest.TestCase):
    """Tests for FeedbackStore initialization"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_database(self):
        """Should create database file"""
        self.assertTrue(self.db_path.exists())

    def test_creates_tables(self):
        """Should create required tables"""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        self.assertIn("feedback", tables)
        self.assertIn("feedback_aggregates", tables)
        self.assertIn("session_state", tables)
        self.assertIn("feedback_preferences", tables)
        self.assertIn("schema_version", tables)

    def test_feedback_enabled_by_default(self):
        """Should have feedback enabled by default"""
        self.assertTrue(self.store.is_feedback_enabled())

    def test_set_feedback_enabled(self):
        """Should be able to disable feedback"""
        self.store.set_feedback_enabled(False)
        self.assertFalse(self.store.is_feedback_enabled())

        self.store.set_feedback_enabled(True)
        self.assertTrue(self.store.is_feedback_enabled())


class TestFeedbackRecording(unittest.TestCase):
    """Tests for recording feedback"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_feedback_returns_entry(self):
        """Should return a FeedbackEntry when recording"""
        entry = self.store.record_feedback(
            rating=FeedbackRating.VERY_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer"
        )

        self.assertIsInstance(entry, FeedbackEntry)
        self.assertEqual(entry.rating, FeedbackRating.VERY_HELPFUL)
        self.assertEqual(entry.context_type, ContextType.AGENT)
        self.assertEqual(entry.agent_name, "code-reviewer")

    def test_record_feedback_generates_id(self):
        """Should generate unique ID starting with fb-"""
        entry = self.store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.COMMAND,
            command_name="/popkit:git commit"
        )

        self.assertTrue(entry.id.startswith("fb-"))
        self.assertGreater(len(entry.id), 10)

    def test_record_feedback_with_comment(self):
        """Should store user comment"""
        entry = self.store.record_feedback(
            rating=FeedbackRating.VERY_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="bug-whisperer",
            user_comment="Found the bug quickly!"
        )

        self.assertEqual(entry.user_comment, "Found the bug quickly!")

    def test_record_feedback_with_session(self):
        """Should track session ID"""
        entry = self.store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.WORKFLOW,
            workflow_phase="implementation",
            session_id="test-session-001"
        )

        self.assertEqual(entry.session_id, "test-session-001")

    def test_invalid_rating_raises_error(self):
        """Should raise error for invalid rating"""
        with self.assertRaises(ValueError):
            self.store.record_feedback(
                rating=5,
                context_type=ContextType.AGENT,
                agent_name="test-agent"
            )

    def test_rating_boundaries(self):
        """Should accept ratings 0-3"""
        for rating in [0, 1, 2, 3]:
            entry = self.store.record_feedback(
                rating=rating,
                context_type=ContextType.AGENT,
                agent_name=f"agent-{rating}"
            )
            self.assertEqual(entry.rating, rating)


class TestFeedbackListing(unittest.TestCase):
    """Tests for listing feedback"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

        # Add some test data
        self.store.record_feedback(
            rating=FeedbackRating.VERY_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer",
            session_id="session-1"
        )
        self.store.record_feedback(
            rating=FeedbackRating.NOT_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer",
            session_id="session-1"
        )
        self.store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.COMMAND,
            command_name="/popkit:dev",
            session_id="session-2"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_all_feedback(self):
        """Should list all feedback entries"""
        feedback = self.store.list_feedback()
        self.assertEqual(len(feedback), 3)

    def test_list_feedback_with_limit(self):
        """Should respect limit parameter"""
        feedback = self.store.list_feedback(limit=2)
        self.assertEqual(len(feedback), 2)

    def test_filter_by_context_type(self):
        """Should filter by context type"""
        feedback = self.store.list_feedback(context_type=ContextType.AGENT)
        self.assertEqual(len(feedback), 2)

        feedback = self.store.list_feedback(context_type=ContextType.COMMAND)
        self.assertEqual(len(feedback), 1)

    def test_filter_by_agent_name(self):
        """Should filter by agent name"""
        feedback = self.store.list_feedback(agent_name="code-reviewer")
        self.assertEqual(len(feedback), 2)

    def test_filter_by_rating_range(self):
        """Should filter by rating range"""
        feedback = self.store.list_feedback(min_rating=2)
        self.assertEqual(len(feedback), 2)

        feedback = self.store.list_feedback(max_rating=1)
        self.assertEqual(len(feedback), 1)

    def test_filter_by_session(self):
        """Should filter by session ID"""
        feedback = self.store.list_feedback(session_id="session-1")
        self.assertEqual(len(feedback), 2)


class TestFeedbackAggregates(unittest.TestCase):
    """Tests for feedback aggregation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

        # Record multiple feedback for same agent
        for rating in [3, 3, 2, 1]:
            self.store.record_feedback(
                rating=rating,
                context_type=ContextType.AGENT,
                context_id="code-reviewer",
                agent_name="code-reviewer"
            )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_aggregate(self):
        """Should return aggregate statistics"""
        agg = self.store.get_aggregate(ContextType.AGENT, "code-reviewer")

        self.assertIsInstance(agg, FeedbackAggregate)
        self.assertEqual(agg.total_count, 4)
        self.assertAlmostEqual(agg.avg_rating, 2.25, places=2)

    def test_aggregate_rating_distribution(self):
        """Should track rating distribution"""
        agg = self.store.get_aggregate(ContextType.AGENT, "code-reviewer")

        self.assertEqual(agg.rating_distribution[3], 2)
        self.assertEqual(agg.rating_distribution[2], 1)
        self.assertEqual(agg.rating_distribution[1], 1)
        self.assertEqual(agg.rating_distribution[0], 0)

    def test_get_low_rated_items(self):
        """Should identify low-rated items"""
        # Add a low-rated agent
        for _ in range(3):
            self.store.record_feedback(
                rating=FeedbackRating.NOT_HELPFUL,
                context_type=ContextType.AGENT,
                context_id="bad-agent",
                agent_name="bad-agent"
            )

        low_rated = self.store.get_low_rated_items(max_avg_rating=1.5, min_count=3)
        agent_ids = [item.context_id for item in low_rated]

        self.assertIn("bad-agent", agent_ids)
        self.assertNotIn("code-reviewer", agent_ids)


class TestSessionState(unittest.TestCase):
    """Tests for session state and feedback fatigue prevention"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_or_create_session(self):
        """Should create new session if doesn't exist"""
        session = self.store.get_or_create_session("new-session")

        self.assertEqual(session['session_id'], "new-session")
        self.assertEqual(session['tool_calls_since_feedback'], 0)
        self.assertEqual(session['feedback_count'], 0)
        self.assertEqual(session['dismissed_count'], 0)

    def test_increment_tool_calls(self):
        """Should increment tool call counter"""
        self.store.get_or_create_session("test-session")

        count = self.store.increment_tool_calls("test-session")
        self.assertEqual(count, 1)

        count = self.store.increment_tool_calls("test-session")
        self.assertEqual(count, 2)

    def test_should_ask_feedback_respects_threshold(self):
        """Should not ask until threshold reached"""
        session_id = "test-session"
        self.store.get_or_create_session(session_id)

        # Below threshold
        for _ in range(5):
            self.store.increment_tool_calls(session_id)
        self.assertFalse(self.store.should_ask_feedback(session_id))

        # Above threshold
        for _ in range(10):
            self.store.increment_tool_calls(session_id)
        self.assertTrue(self.store.should_ask_feedback(session_id))

    def test_record_dismissed(self):
        """Should track dismissed count"""
        session_id = "test-session"
        self.store.get_or_create_session(session_id)

        count = self.store.record_dismissed(session_id)
        self.assertEqual(count, 1)

        count = self.store.record_dismissed(session_id)
        self.assertEqual(count, 2)

    def test_should_ask_respects_dismiss_limit(self):
        """Should stop asking after max dismissals"""
        session_id = "test-session"
        self.store.get_or_create_session(session_id)

        # Get above tool call threshold
        for _ in range(15):
            self.store.increment_tool_calls(session_id)

        # Dismiss 3 times
        for _ in range(3):
            self.store.record_dismissed(session_id)

        self.assertFalse(self.store.should_ask_feedback(session_id))

    def test_set_never_ask_session(self):
        """Should respect never ask flag"""
        session_id = "test-session"
        self.store.get_or_create_session(session_id)

        # Get above threshold
        for _ in range(15):
            self.store.increment_tool_calls(session_id)

        self.assertTrue(self.store.should_ask_feedback(session_id))

        self.store.set_never_ask_session(session_id)
        self.assertFalse(self.store.should_ask_feedback(session_id))

    def test_feedback_resets_counter(self):
        """Recording feedback should reset tool call counter"""
        session_id = "test-session"
        self.store.get_or_create_session(session_id)

        for _ in range(15):
            self.store.increment_tool_calls(session_id)

        self.store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="test-agent",
            session_id=session_id
        )

        session = self.store.get_or_create_session(session_id)
        self.assertEqual(session['tool_calls_since_feedback'], 0)


class TestStatistics(unittest.TestCase):
    """Tests for statistics"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

        # Add test data
        self.store.record_feedback(
            rating=FeedbackRating.VERY_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer"
        )
        self.store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer"
        )
        self.store.record_feedback(
            rating=FeedbackRating.NOT_HELPFUL,
            context_type=ContextType.COMMAND,
            command_name="/popkit:dev"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_stats(self):
        """Should return overall statistics"""
        stats = self.store.get_stats()

        self.assertEqual(stats['total_feedback'], 3)
        self.assertIn('avg_rating', stats)
        self.assertIn('by_context_type', stats)
        self.assertIn('by_rating', stats)

    def test_get_agent_stats(self):
        """Should return per-agent statistics"""
        stats = self.store.get_agent_stats()

        self.assertTrue(len(stats) >= 1)
        reviewer_stats = [s for s in stats if s['agent'] == 'code-reviewer']
        self.assertEqual(len(reviewer_stats), 1)
        self.assertEqual(reviewer_stats[0]['count'], 2)


class TestGDPRCompliance(unittest.TestCase):
    """Tests for GDPR compliance features"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.store = FeedbackStore(self.db_path)

        # Add test data
        for i in range(5):
            self.store.record_feedback(
                rating=i % 4,
                context_type=ContextType.AGENT,
                agent_name=f"agent-{i}"
            )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_all(self):
        """Should export all data to JSON file"""
        export_path = Path(self.temp_dir) / "export.json"
        count = self.store.export_all(export_path)

        self.assertEqual(count, 5)
        self.assertTrue(export_path.exists())

        import json
        with open(export_path) as f:
            data = json.load(f)

        self.assertIn('feedback', data)
        self.assertEqual(len(data['feedback']), 5)

    def test_delete_all_data(self):
        """Should delete all data"""
        result = self.store.delete_all_data()

        self.assertEqual(result['feedback_deleted'], 5)

        # Verify deletion
        feedback = self.store.list_feedback()
        self.assertEqual(len(feedback), 0)


if __name__ == "__main__":
    unittest.main()
