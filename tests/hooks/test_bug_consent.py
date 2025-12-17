#!/usr/bin/env python3
"""
Tests for Bug Consent Handler module

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

from utils.bug_store import BugStore, ShareStatus, ConsentLevel
from utils.bug_consent import (
    ConsentQuestion,
    ConsentAction,
    get_share_consent_question,
    get_first_time_consent_question,
    get_auto_detect_consent_question,
    process_share_response,
    process_consent_level_response,
    process_auto_detect_response,
    should_ask_for_sharing,
    get_pending_bugs_for_consent,
    format_consent_summary,
)


class TestConsentQuestionGeneration(unittest.TestCase):
    """Tests for generating consent questions"""

    def test_share_question_structure(self):
        """Should generate properly structured share consent question"""
        question = get_share_consent_question("TypeError in auth module")

        self.assertIsInstance(question, ConsentQuestion)
        self.assertIn("TypeError", question.question)
        self.assertEqual(question.header, "Bug sharing")
        self.assertEqual(len(question.options), 4)
        self.assertFalse(question.multi_select)

    def test_share_question_has_required_options(self):
        """Should have all required sharing options"""
        question = get_share_consent_question("Test error")

        labels = [opt["label"] for opt in question.options]
        self.assertIn("Share this bug", labels)
        self.assertIn("Always share", labels)
        self.assertIn("Keep local", labels)
        self.assertIn("Never ask", labels)

    def test_first_time_question_structure(self):
        """Should generate properly structured first-time question"""
        question = get_first_time_consent_question()

        self.assertEqual(question.header, "Bug privacy")
        self.assertEqual(len(question.options), 3)

    def test_first_time_question_has_privacy_levels(self):
        """Should have all privacy level options"""
        question = get_first_time_consent_question()

        labels = [opt["label"] for opt in question.options]
        self.assertTrue(any("Strict" in l for l in labels))
        self.assertTrue(any("Moderate" in l for l in labels))
        self.assertTrue(any("Minimal" in l for l in labels))

    def test_auto_detect_question_structure(self):
        """Should generate properly structured auto-detect question"""
        question = get_auto_detect_consent_question()

        self.assertEqual(question.header, "Auto-detect")
        self.assertEqual(len(question.options), 2)

    def test_to_dict_conversion(self):
        """Should convert to dictionary for AskUserQuestion"""
        question = get_share_consent_question("Test")
        d = question.to_dict()

        self.assertIn("question", d)
        self.assertIn("header", d)
        self.assertIn("options", d)
        self.assertIn("multiSelect", d)


class TestShareResponseProcessing(unittest.TestCase):
    """Tests for processing share consent responses"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        # Patch the default path and reset singleton
        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None  # Reset singleton

        # Now get_bug_store() will create with the new path
        from utils.bug_store import get_bug_store
        self.store = get_bug_store()
        self.bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test bug"
        )

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_share_this_bug(self):
        """Should mark bug as shared when 'Share this bug' selected"""
        result = process_share_response("Share this bug", self.bug.id)

        self.assertEqual(result["action"], "shared")
        updated = self.store.get_bug(self.bug.id)
        self.assertEqual(updated.share_status, "shared")

    def test_always_share_enables_auto_sharing(self):
        """Should enable auto-sharing when 'Always share' selected"""
        result = process_share_response("Always share", self.bug.id)

        self.assertEqual(result["action"], "shared")
        self.assertTrue(result["sharing_enabled"])
        self.assertFalse(result["ask_before_share"])
        self.assertTrue(self.store.is_sharing_enabled())

    def test_keep_local_marks_local_only(self):
        """Should mark bug as local only when 'Keep local' selected"""
        result = process_share_response("Keep local", self.bug.id)

        self.assertEqual(result["action"], "local_only")
        updated = self.store.get_bug(self.bug.id)
        self.assertEqual(updated.share_status, "local_only")

    def test_never_ask_disables_prompts(self):
        """Should disable prompts when 'Never ask' selected"""
        result = process_share_response("Never ask", self.bug.id)

        self.assertEqual(result["action"], "never_ask")
        self.assertFalse(result["ask_before_share"])
        self.assertFalse(self.store.should_ask_before_share())


class TestConsentLevelProcessing(unittest.TestCase):
    """Tests for processing consent level responses"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None

        from utils.bug_store import get_bug_store
        self.store = get_bug_store()

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_strict_level(self):
        """Should set strict consent level"""
        result = process_consent_level_response("Strict (default)")

        self.assertEqual(result["consent_level"], "strict")
        self.assertFalse(result["sharing_enabled"])
        self.assertEqual(self.store.get_consent_level(), ConsentLevel.STRICT)

    def test_moderate_level(self):
        """Should set moderate consent level with ask before share"""
        result = process_consent_level_response("Moderate")

        self.assertEqual(result["consent_level"], "moderate")
        self.assertTrue(result["sharing_enabled"])
        self.assertTrue(result["ask_before_share"])

    def test_minimal_level(self):
        """Should set minimal consent level without asking"""
        result = process_consent_level_response("Minimal")

        self.assertEqual(result["consent_level"], "minimal")
        self.assertTrue(result["sharing_enabled"])
        self.assertFalse(result["ask_before_share"])


class TestAutoDetectProcessing(unittest.TestCase):
    """Tests for processing auto-detect responses"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None

        from utils.bug_store import get_bug_store
        self.store = get_bug_store()

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enable_auto_detect(self):
        """Should enable auto-detection"""
        result = process_auto_detect_response("Enable")
        self.assertTrue(result["auto_detect_enabled"])
        self.assertTrue(self.store.is_auto_detect_enabled())

    def test_disable_auto_detect(self):
        """Should disable auto-detection"""
        result = process_auto_detect_response("Disable")
        self.assertFalse(result["auto_detect_enabled"])
        self.assertFalse(self.store.is_auto_detect_enabled())


class TestShouldAskForSharing(unittest.TestCase):
    """Tests for should_ask_for_sharing logic"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None

        from utils.bug_store import get_bug_store
        self.store = get_bug_store()
        self.bug = self.store.capture_bug(
            error_type="Error",
            context_summary="Test"
        )

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_false_when_sharing_disabled(self):
        """Should not ask when sharing is disabled"""
        self.store.set_sharing_enabled(False)
        self.assertFalse(should_ask_for_sharing(self.bug.id))

    def test_returns_false_when_dont_ask(self):
        """Should not ask when user said don't ask"""
        self.store.set_sharing_enabled(True)
        self.store.set_ask_before_share(False)
        self.assertFalse(should_ask_for_sharing(self.bug.id))

    def test_returns_true_for_pending_bug(self):
        """Should ask for pending bugs when sharing enabled"""
        self.store.set_sharing_enabled(True)
        self.store.set_ask_before_share(True)
        self.assertTrue(should_ask_for_sharing(self.bug.id))


class TestPendingBugsRetrieval(unittest.TestCase):
    """Tests for getting pending bugs for consent"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None

        from utils.bug_store import get_bug_store
        self.store = get_bug_store()
        self.store.capture_bug(error_type="Error1", context_summary="Test 1")
        self.store.capture_bug(error_type="Error2", context_summary="Test 2")

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_empty_when_sharing_disabled(self):
        """Should return empty list when sharing disabled"""
        self.store.set_sharing_enabled(False)
        bugs = get_pending_bugs_for_consent()
        self.assertEqual(len(bugs), 0)

    def test_returns_pending_bugs_when_enabled(self):
        """Should return pending bugs when sharing enabled and ask=true"""
        self.store.set_sharing_enabled(True)
        self.store.set_ask_before_share(True)
        bugs = get_pending_bugs_for_consent()
        self.assertEqual(len(bugs), 2)


class TestFormatConsentSummary(unittest.TestCase):
    """Tests for consent summary formatting"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_bugs.db"

        import utils.bug_store as bs
        self._original_path = bs.BugStore.DEFAULT_DB_PATH
        bs.BugStore.DEFAULT_DB_PATH = self.db_path
        bs._store = None

        from utils.bug_store import get_bug_store
        self.store = get_bug_store()

    def tearDown(self):
        import shutil
        import utils.bug_store as bs
        bs.BugStore.DEFAULT_DB_PATH = self._original_path
        bs._store = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_formatted_string(self):
        """Should return formatted consent summary"""
        summary = format_consent_summary()

        self.assertIn("Bug Reporting Preferences", summary)
        self.assertIn("Consent Level:", summary)
        self.assertIn("Sharing Enabled:", summary)
        self.assertIn("Auto-Detect:", summary)


if __name__ == "__main__":
    unittest.main()
