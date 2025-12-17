#!/usr/bin/env python3
"""
Tests for Pattern Learner module

Part of Issue #89 - Platform-Aware Command Learning
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.pattern_learner import (
    PatternLearner,
    CommandCorrection,
    CorrectionSuggestion,
    get_learner,
    learn_correction,
    suggest_correction
)


class TestPatternLearnerInit(unittest.TestCase):
    """Tests for PatternLearner initialization"""

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

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

        self.assertIn("command_corrections", tables)
        self.assertIn("error_patterns", tables)
        self.assertIn("learning_history", tables)

    def test_seeds_error_patterns(self):
        """Should seed common error patterns"""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        count = conn.execute(
            "SELECT COUNT(*) FROM error_patterns"
        ).fetchone()[0]
        conn.close()

        self.assertGreater(count, 0)


class TestRecordCorrection(unittest.TestCase):
    """Tests for recording corrections"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_records_correction(self):
        """Should record a correction"""
        correction = self.learner.record_correction(
            original_command="cp -r source/ dest/",
            corrected_command="xcopy /E /I source\\ dest\\",
            platform="windows",
            shell="cmd",
            error_pattern="command_not_found"
        )

        self.assertIsNotNone(correction)
        self.assertIsNotNone(correction.id)
        self.assertEqual(correction.original_command, "cp -r source/ dest/")
        self.assertEqual(correction.corrected_command, "xcopy /E /I source\\ dest\\")

    def test_updates_existing_correction(self):
        """Should update existing correction for same command"""
        # Record first correction
        c1 = self.learner.record_correction(
            original_command="cp file.txt file2.txt",
            corrected_command="copy file.txt file2.txt",
            platform="windows",
            shell="cmd"
        )

        # Record same command with different correction
        c2 = self.learner.record_correction(
            original_command="cp file.txt file2.txt",
            corrected_command="xcopy file.txt file2.txt",
            platform="windows",
            shell="cmd"
        )

        # Should be same ID (updated, not new)
        self.assertEqual(c1.id, c2.id)
        # Corrected command should be updated
        self.assertEqual(c2.corrected_command, "xcopy file.txt file2.txt")

    def test_records_history(self):
        """Should record to learning history"""
        import sqlite3

        self.learner.record_correction(
            original_command="ls",
            corrected_command="dir",
            platform="windows",
            shell="cmd"
        )

        conn = sqlite3.connect(str(self.db_path))
        count = conn.execute(
            "SELECT COUNT(*) FROM learning_history WHERE action='record'"
        ).fetchone()[0]
        conn.close()

        self.assertGreater(count, 0)


class TestSuccessFailureTracking(unittest.TestCase):
    """Tests for tracking successes and failures"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_success_increments_count(self):
        """record_success should increment success_count"""
        correction = self.learner.record_correction(
            original_command="cp file.txt file2.txt",
            corrected_command="copy file.txt file2.txt",
            platform="windows",
            shell="cmd"
        )

        self.learner.record_success(correction.id)
        updated = self.learner.get_correction(correction.id)

        self.assertEqual(updated.success_count, 1)

    def test_record_failure_increments_count(self):
        """record_failure should increment failure_count"""
        correction = self.learner.record_correction(
            original_command="cp file.txt file2.txt",
            corrected_command="copy file.txt file2.txt",
            platform="windows",
            shell="cmd"
        )

        self.learner.record_failure(correction.id)
        updated = self.learner.get_correction(correction.id)

        self.assertEqual(updated.failure_count, 1)

    def test_confidence_calculation(self):
        """Confidence should be calculated from success/failure ratio"""
        correction = self.learner.record_correction(
            original_command="cp file.txt file2.txt",
            corrected_command="copy file.txt file2.txt",
            platform="windows",
            shell="cmd"
        )

        # Record 3 successes and 1 failure
        for _ in range(3):
            self.learner.record_success(correction.id)
        self.learner.record_failure(correction.id)

        updated = self.learner.get_correction(correction.id)
        # Confidence should be 3/4 = 0.75
        self.assertAlmostEqual(updated.confidence, 0.75, places=2)


class TestFindSuggestions(unittest.TestCase):
    """Tests for finding suggestions"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

        # Seed some corrections
        correction = self.learner.record_correction(
            original_command="cp -r source/ dest/",
            corrected_command="xcopy /E /I source\\ dest\\",
            platform="windows",
            shell="cmd"
        )
        # Add some successes to build confidence
        for _ in range(5):
            self.learner.record_success(correction.id)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_finds_exact_match(self):
        """Should find exact matching correction"""
        suggestions = self.learner.find_suggestions(
            "cp -r source/ dest/",
            platform="windows",
            shell="cmd"
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].suggested, "xcopy /E /I source\\ dest\\")

    def test_respects_min_confidence(self):
        """Should respect min_confidence filter"""
        # This has high confidence from setUp
        suggestions = self.learner.find_suggestions(
            "cp -r source/ dest/",
            platform="windows",
            shell="cmd",
            min_confidence=0.9
        )

        self.assertEqual(len(suggestions), 1)

        # Should not find if we set impossible threshold
        suggestions = self.learner.find_suggestions(
            "cp -r source/ dest/",
            platform="windows",
            shell="cmd",
            min_confidence=1.1
        )

        self.assertEqual(len(suggestions), 0)

    def test_get_best_suggestion(self):
        """Should return best suggestion above threshold"""
        suggestion = self.learner.get_best_suggestion(
            "cp -r source/ dest/",
            platform="windows",
            shell="cmd",
            min_confidence=0.5
        )

        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.suggested, "xcopy /E /I source\\ dest\\")


class TestGetAllCorrections(unittest.TestCase):
    """Tests for getting all corrections"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

        # Seed some corrections
        self.learner.record_correction("cp a b", "copy a b", "windows", "cmd")
        self.learner.record_correction("ls", "dir", "windows", "cmd")
        self.learner.record_correction("cat f", "type f", "windows", "powershell")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_all_corrections(self):
        """Should return all corrections"""
        corrections = self.learner.get_all_corrections()
        self.assertEqual(len(corrections), 3)

    def test_filters_by_platform(self):
        """Should filter by platform"""
        corrections = self.learner.get_all_corrections(platform="windows")
        self.assertEqual(len(corrections), 3)

    def test_filters_by_shell(self):
        """Should filter by shell"""
        corrections = self.learner.get_all_corrections(shell="cmd")
        self.assertEqual(len(corrections), 2)


class TestDeleteCorrection(unittest.TestCase):
    """Tests for deleting corrections"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deletes_correction(self):
        """Should delete correction by ID"""
        correction = self.learner.record_correction(
            "cp a b", "copy a b", "windows", "cmd"
        )

        result = self.learner.delete_correction(correction.id)
        self.assertTrue(result)

        # Should be gone
        deleted = self.learner.get_correction(correction.id)
        self.assertIsNone(deleted)

    def test_returns_false_for_nonexistent(self):
        """Should return False for nonexistent ID"""
        result = self.learner.delete_correction(99999)
        self.assertFalse(result)


class TestStats(unittest.TestCase):
    """Tests for statistics"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.learner = PatternLearner(self.db_path)

        # Seed some corrections
        c1 = self.learner.record_correction("cp a b", "copy a b", "windows", "cmd")
        c2 = self.learner.record_correction("ls", "dir", "windows", "cmd")

        # Add some successes to c1
        for _ in range(5):
            self.learner.record_success(c1.id)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_stats_dict(self):
        """Should return statistics dictionary"""
        stats = self.learner.get_stats()

        self.assertIn("total_corrections", stats)
        self.assertIn("by_platform", stats)
        self.assertIn("by_shell", stats)
        self.assertIn("high_confidence_count", stats)

    def test_counts_correctly(self):
        """Should count corrections correctly"""
        stats = self.learner.get_stats()

        self.assertEqual(stats["total_corrections"], 2)
        self.assertEqual(stats["by_platform"].get("windows", 0), 2)


class TestExportImport(unittest.TestCase):
    """Tests for export/import functionality"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"
        self.export_path = Path(self.temp_dir) / "export.json"
        self.learner = PatternLearner(self.db_path)

        # Seed some corrections
        self.learner.record_correction("cp a b", "copy a b", "windows", "cmd")
        self.learner.record_correction("ls", "dir", "windows", "cmd")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exports_to_json(self):
        """Should export to JSON file"""
        count = self.learner.export_patterns(self.export_path)

        self.assertEqual(count, 2)
        self.assertTrue(self.export_path.exists())

        # Verify JSON content
        import json
        with open(self.export_path) as f:
            data = json.load(f)
        self.assertIn("patterns", data)
        self.assertEqual(len(data["patterns"]), 2)

    def test_imports_from_json(self):
        """Should import from JSON file"""
        # Export first
        self.learner.export_patterns(self.export_path)

        # Create new learner with fresh database
        new_db = Path(self.temp_dir) / "new_patterns.db"
        new_learner = PatternLearner(new_db)

        # Import
        count = new_learner.import_patterns(self.export_path)

        self.assertEqual(count, 2)
        corrections = new_learner.get_all_corrections()
        self.assertEqual(len(corrections), 2)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions"""

    def setUp(self):
        # Reset singleton
        import utils.pattern_learner as pl
        pl._learner = None

        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_patterns.db"

    def tearDown(self):
        import shutil
        import utils.pattern_learner as pl
        pl._learner = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_learner_returns_singleton(self):
        """get_learner should return singleton"""
        l1 = get_learner()
        l2 = get_learner()
        self.assertIs(l1, l2)

    def test_learn_correction(self):
        """learn_correction should record a correction"""
        correction = learn_correction(
            original="cp file.txt file2.txt",
            corrected="copy file.txt file2.txt"
        )

        self.assertIsNotNone(correction)
        self.assertIsNotNone(correction.id)


if __name__ == "__main__":
    unittest.main()
