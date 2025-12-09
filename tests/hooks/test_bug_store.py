#!/usr/bin/env python3
"""
Tests for Bug Store module

Part of Issue #90 - Automatic Bug Reporting System
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.bug_store import (
    BugStore,
    CapturedBug,
    ShareStatus,
    ConsentLevel,
    get_bug_store,
)


class TestBugStoreInit(unittest.TestCase):
    """Tests for BugStore initialization"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

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

        self.assertIn("captured_bugs", tables)
        self.assertIn("consent_preferences", tables)
        self.assertIn("sharing_history", tables)
        self.assertIn("schema_version", tables)

    def test_default_consent_is_strict(self):
        """Should default to strict consent level"""
        level = self.store.get_consent_level()
        self.assertEqual(level, ConsentLevel.STRICT)

    def test_sharing_disabled_by_default(self):
        """Should have sharing disabled by default"""
        self.assertFalse(self.store.is_sharing_enabled())

    def test_auto_detect_enabled_by_default(self):
        """Should have auto-detection enabled by default"""
        self.assertTrue(self.store.is_auto_detect_enabled())


class TestBugCapture(unittest.TestCase):
    """Tests for capturing bugs"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_captures_bug(self):
        """Should capture a bug and return it"""
        bug = self.store.capture_bug(
            error_type="TypeError",
            context_summary="Agent encountered TypeError",
            error_message="Cannot read property 'token' of undefined",
            command_pattern="npm run build",
            detection_source="auto",
            confidence=0.85
        )

        self.assertIsNotNone(bug)
        self.assertIsNotNone(bug.id)
        self.assertTrue(bug.id.startswith("bug-"))
        self.assertEqual(bug.error_type, "TypeError")
        self.assertEqual(bug.confidence, 0.85)

    def test_generates_unique_ids(self):
        """Should generate unique IDs for each bug"""
        bug1 = self.store.capture_bug(
            error_type="Error1",
            context_summary="Test 1"
        )
        bug2 = self.store.capture_bug(
            error_type="Error2",
            context_summary="Test 2"
        )

        self.assertNotEqual(bug1.id, bug2.id)

    def test_hashes_error_message(self):
        """Should create hash of error message"""
        bug = self.store.capture_bug(
            error_type="TypeError",
            context_summary="Test",
            error_message="Some error message"
        )

        self.assertIsNotNone(bug.error_message_hash)
        self.assertEqual(len(bug.error_message_hash), 16)

    def test_default_share_status_is_pending(self):
        """Should default share status to pending"""
        bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test"
        )

        self.assertEqual(bug.share_status, "pending")

    def test_stores_raw_context(self):
        """Should store raw context as JSON"""
        raw_context = {
            "tool_name": "Bash",
            "command": "npm run build"
        }
        bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test",
            raw_context=raw_context
        )

        import json
        stored_context = json.loads(bug.raw_context)
        self.assertEqual(stored_context["tool_name"], "Bash")


class TestBugRetrieval(unittest.TestCase):
    """Tests for retrieving bugs"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

        # Seed some bugs
        self.bug1 = self.store.capture_bug(
            error_type="TypeError",
            context_summary="Type error test",
            confidence=0.9
        )
        self.bug2 = self.store.capture_bug(
            error_type="SyntaxError",
            context_summary="Syntax error test",
            confidence=0.7
        )
        self.bug3 = self.store.capture_bug(
            error_type="TypeError",
            context_summary="Another type error",
            confidence=0.8
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gets_bug_by_id(self):
        """Should retrieve bug by ID"""
        bug = self.store.get_bug(self.bug1.id)
        self.assertIsNotNone(bug)
        self.assertEqual(bug.id, self.bug1.id)

    def test_returns_none_for_missing_id(self):
        """Should return None for non-existent ID"""
        bug = self.store.get_bug("nonexistent-id")
        self.assertIsNone(bug)

    def test_lists_all_bugs(self):
        """Should list all bugs"""
        bugs = self.store.list_bugs()
        self.assertEqual(len(bugs), 3)

    def test_lists_bugs_with_limit(self):
        """Should respect limit parameter"""
        bugs = self.store.list_bugs(limit=2)
        self.assertEqual(len(bugs), 2)

    def test_filters_by_error_type(self):
        """Should filter by error type"""
        bugs = self.store.list_bugs(error_type="TypeError")
        self.assertEqual(len(bugs), 2)
        for bug in bugs:
            self.assertEqual(bug.error_type, "TypeError")

    def test_finds_similar_bugs(self):
        """Should find similar bugs by error type"""
        similar = self.store.find_similar("TypeError")
        self.assertEqual(len(similar), 2)


class TestShareStatus(unittest.TestCase):
    """Tests for share status management"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

        self.bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_updates_share_status(self):
        """Should update share status"""
        result = self.store.update_share_status(self.bug.id, ShareStatus.SHARED)
        self.assertTrue(result)

        updated = self.store.get_bug(self.bug.id)
        self.assertEqual(updated.share_status, "shared")

    def test_returns_false_for_nonexistent_bug(self):
        """Should return False for non-existent bug"""
        result = self.store.update_share_status("nonexistent", ShareStatus.SHARED)
        self.assertFalse(result)

    def test_filters_by_share_status(self):
        """Should filter bugs by share status"""
        # Update one bug to shared
        self.store.update_share_status(self.bug.id, ShareStatus.SHARED)

        pending = self.store.list_bugs(share_status="pending")
        shared = self.store.list_bugs(share_status="shared")

        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0].id, self.bug.id)


class TestConsentPreferences(unittest.TestCase):
    """Tests for consent preference management"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sets_consent_level(self):
        """Should set consent level"""
        self.store.set_consent_level(ConsentLevel.MODERATE)
        level = self.store.get_consent_level()
        self.assertEqual(level, ConsentLevel.MODERATE)

    def test_enables_sharing(self):
        """Should enable/disable sharing"""
        self.store.set_sharing_enabled(True)
        self.assertTrue(self.store.is_sharing_enabled())

        self.store.set_sharing_enabled(False)
        self.assertFalse(self.store.is_sharing_enabled())

    def test_sets_ask_before_share(self):
        """Should set ask before share preference"""
        self.store.set_ask_before_share(False)
        self.assertFalse(self.store.should_ask_before_share())

        self.store.set_ask_before_share(True)
        self.assertTrue(self.store.should_ask_before_share())

    def test_sets_auto_detect_enabled(self):
        """Should set auto-detection preference"""
        self.store.set_auto_detect_enabled(False)
        self.assertFalse(self.store.is_auto_detect_enabled())

        self.store.set_auto_detect_enabled(True)
        self.assertTrue(self.store.is_auto_detect_enabled())


class TestBugDeletion(unittest.TestCase):
    """Tests for bug deletion"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

        self.bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deletes_bug(self):
        """Should delete bug by ID"""
        result = self.store.delete_bug(self.bug.id)
        self.assertTrue(result)

        deleted = self.store.get_bug(self.bug.id)
        self.assertIsNone(deleted)

    def test_returns_false_for_nonexistent(self):
        """Should return False for non-existent ID"""
        result = self.store.delete_bug("nonexistent")
        self.assertFalse(result)


class TestStatistics(unittest.TestCase):
    """Tests for statistics"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.store = BugStore(self.db_path)

        # Seed some bugs
        self.store.capture_bug(error_type="TypeError", context_summary="Test 1")
        self.store.capture_bug(error_type="TypeError", context_summary="Test 2")
        self.store.capture_bug(error_type="SyntaxError", context_summary="Test 3")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_total_count(self):
        """Should return total bug count"""
        stats = self.store.get_stats()
        self.assertEqual(stats["total_bugs"], 3)

    def test_returns_by_error_type(self):
        """Should return counts by error type"""
        stats = self.store.get_stats()
        self.assertEqual(stats["by_error_type"].get("TypeError"), 2)
        self.assertEqual(stats["by_error_type"].get("SyntaxError"), 1)

    def test_returns_consent_info(self):
        """Should return consent information"""
        stats = self.store.get_stats()
        self.assertIn("consent_level", stats)
        self.assertIn("sharing_enabled", stats)


class TestGDPRCompliance(unittest.TestCase):
    """Tests for GDPR compliance features"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"
        self.export_path = Path(self.temp_dir) / "export.json"
        self.store = BugStore(self.db_path)

        # Seed some bugs
        self.store.capture_bug(error_type="Error1", context_summary="Test 1")
        self.store.capture_bug(error_type="Error2", context_summary="Test 2")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exports_all_data(self):
        """Should export all bug data"""
        count = self.store.export_all(self.export_path)
        self.assertEqual(count, 2)
        self.assertTrue(self.export_path.exists())

        import json
        with open(self.export_path) as f:
            data = json.load(f)

        self.assertIn("bugs", data)
        self.assertEqual(len(data["bugs"]), 2)
        self.assertIn("preferences", data)

    def test_deletes_all_data(self):
        """Should delete all user data (right to be forgotten)"""
        result = self.store.delete_all_data()

        self.assertEqual(result["bugs_deleted"], 2)

        # Verify deletion
        bugs = self.store.list_bugs()
        self.assertEqual(len(bugs), 0)

        # Verify consent reset to strict
        level = self.store.get_consent_level()
        self.assertEqual(level, ConsentLevel.STRICT)


class TestSingleton(unittest.TestCase):
    """Tests for singleton pattern"""

    def test_get_bug_store_returns_singleton(self):
        """get_bug_store should return singleton instance"""
        # Reset singleton
        import utils.bug_store as bs
        bs._store = None

        store1 = get_bug_store()
        store2 = get_bug_store()
        self.assertIs(store1, store2)


if __name__ == "__main__":
    unittest.main()
