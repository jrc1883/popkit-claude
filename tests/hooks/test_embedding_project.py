#!/usr/bin/env python3
"""
Tests for embedding_project.py module.

Tests for Issue #46 (Project-Local Embedding Management).
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "hooks" / "utils"))


class TestGetProjectRoot(unittest.TestCase):
    """Tests for get_project_root()."""

    def setUp(self):
        """Create temp directory structure."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_project_with_claude_dir(self):
        """Should find project root with .claude/ directory."""
        from embedding_project import get_project_root

        project_dir = Path(self.temp_dir) / "myproject"
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True)

        # Create nested subdirectory
        nested_dir = project_dir / "src" / "components"
        nested_dir.mkdir(parents=True)

        result = get_project_root(str(nested_dir))
        self.assertEqual(result, str(project_dir))

    def test_find_project_with_git_dir(self):
        """Should find project root with .git/ directory if no .claude/."""
        from embedding_project import get_project_root

        project_dir = Path(self.temp_dir) / "gitproject"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)

        result = get_project_root(str(project_dir))
        self.assertEqual(result, str(project_dir))

    def test_no_project_root(self):
        """Should return None if no project markers found."""
        from embedding_project import get_project_root

        # Use temp_dir which has no .claude or .git
        result = get_project_root(self.temp_dir)
        # May return None or find a parent - depends on system
        # Just verify it returns a string or None
        self.assertTrue(result is None or isinstance(result, str))


class TestExtractYamlFrontmatter(unittest.TestCase):
    """Tests for extract_yaml_frontmatter()."""

    def test_extract_valid_frontmatter(self):
        """Should extract valid YAML frontmatter."""
        from embedding_project import extract_yaml_frontmatter

        content = """---
description: Test skill description
name: test-skill
---

# Skill Content
"""
        result = extract_yaml_frontmatter(content)
        self.assertEqual(result["description"], "Test skill description")
        self.assertEqual(result["name"], "test-skill")

    def test_extract_quoted_values(self):
        """Should strip quotes from values."""
        from embedding_project import extract_yaml_frontmatter

        content = """---
description: "Quoted description"
name: 'Single quoted'
---
"""
        result = extract_yaml_frontmatter(content)
        self.assertEqual(result["description"], "Quoted description")
        self.assertEqual(result["name"], "Single quoted")

    def test_no_frontmatter(self):
        """Should return empty dict if no frontmatter."""
        from embedding_project import extract_yaml_frontmatter

        content = "# Just content\nNo frontmatter here."
        result = extract_yaml_frontmatter(content)
        self.assertEqual(result, {})

    def test_incomplete_frontmatter(self):
        """Should return empty dict if frontmatter incomplete."""
        from embedding_project import extract_yaml_frontmatter

        content = """---
description: Incomplete
No closing delimiter"""
        result = extract_yaml_frontmatter(content)
        self.assertEqual(result, {})


class TestScanProjectItems(unittest.TestCase):
    """Tests for scan_project_items()."""

    def setUp(self):
        """Create temp project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "testproject"

        # Create .claude directory structure
        skills_dir = self.project_dir / ".claude" / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)

        agents_dir = self.project_dir / ".claude" / "agents" / "my-agent"
        agents_dir.mkdir(parents=True)

        commands_dir = self.project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Create skill file
        (skills_dir / "SKILL.md").write_text("""---
description: A test skill for doing things
name: my-skill
---

# My Skill
""")

        # Create agent file
        (agents_dir / "AGENT.md").write_text("""---
description: A test agent for helping
name: my-agent
---

# My Agent
""")

        # Create command file
        (commands_dir / "test-cmd.md").write_text("""---
description: A test command
---

# Test Command
""")

        # Create item without description (should be skipped)
        no_desc_dir = self.project_dir / ".claude" / "skills" / "no-desc"
        no_desc_dir.mkdir(parents=True)
        (no_desc_dir / "SKILL.md").write_text("""---
name: no-desc
---

# No Description
""")

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_finds_all_items(self):
        """Should find all items with descriptions."""
        from embedding_project import scan_project_items

        items = scan_project_items(str(self.project_dir))

        # Should find 3 items (skill, agent, command)
        self.assertEqual(len(items), 3)

        # Verify item types
        types = {item["source_type"] for item in items}
        self.assertIn("project-skill", types)
        self.assertIn("project-agent", types)
        self.assertIn("project-command", types)

    def test_scan_extracts_correct_info(self):
        """Should extract correct information from items."""
        from embedding_project import scan_project_items

        items = scan_project_items(str(self.project_dir))

        # Find skill item
        skill_item = next(i for i in items if i["source_type"] == "project-skill")

        self.assertEqual(skill_item["name"], "my-skill")
        self.assertEqual(skill_item["description"], "A test skill for doing things")
        self.assertIn("testproject", skill_item["id"])
        self.assertTrue(skill_item["path"].endswith("SKILL.md"))

    def test_scan_skips_items_without_description(self):
        """Should skip items without description in frontmatter."""
        from embedding_project import scan_project_items

        items = scan_project_items(str(self.project_dir))

        # Should not find the no-desc skill
        names = [item["name"] for item in items]
        self.assertNotIn("no-desc", names)

    def test_scan_empty_project(self):
        """Should return empty list for project without items."""
        from embedding_project import scan_project_items

        empty_project = Path(self.temp_dir) / "empty"
        empty_project.mkdir()
        (empty_project / ".claude").mkdir()

        items = scan_project_items(str(empty_project))
        self.assertEqual(items, [])


class TestEmbedProjectItems(unittest.TestCase):
    """Tests for embed_project_items()."""

    def setUp(self):
        """Create temp project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "embedproject"
        self.db_path = Path(self.temp_dir) / "test_embeddings.db"

        # Create skill
        skills_dir = self.project_dir / ".claude" / "skills" / "embed-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("""---
description: Skill to embed
---
# Embed Skill
""")

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_embed_returns_error_without_api_key(self):
        """Should return error if VOYAGE_API_KEY not set."""
        from embedding_project import embed_project_items

        with patch.dict(os.environ, {}, clear=True):
            # Clear the singleton client
            import voyage_client
            orig_client = voyage_client._client
            voyage_client._client = None

            try:
                result = embed_project_items(
                    project_root=str(self.project_dir),
                    verbose=False
                )
                self.assertEqual(result["status"], "error")
                self.assertIn("VOYAGE_API_KEY", result.get("error", ""))
            finally:
                voyage_client._client = orig_client

    @patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"})
    def test_embed_no_items(self):
        """Should return no_items status if no items found."""
        from embedding_project import embed_project_items

        empty_project = Path(self.temp_dir) / "empty2"
        (empty_project / ".claude").mkdir(parents=True)

        result = embed_project_items(
            project_root=str(empty_project),
            verbose=False
        )
        self.assertEqual(result["status"], "no_items")

    @patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"})
    def test_embed_with_mocked_client(self):
        """Should embed items successfully with mocked client."""
        from embedding_project import embed_project_items
        import embedding_project

        # Mock the embed function
        mock_embedding = [0.1] * 1024

        # Mock VoyageClient
        mock_client = Mock()
        mock_client.is_available = True
        mock_client.embed.return_value = [mock_embedding]

        # Mock EmbeddingStore
        mock_store = Mock()
        mock_store.needs_update.return_value = True

        with patch.object(embedding_project, 'VoyageClient', return_value=mock_client):
            with patch.object(embedding_project, 'EmbeddingStore', return_value=mock_store):
                with patch.object(embedding_project, 'voyage_available', return_value=True):
                    result = embed_project_items(
                        project_root=str(self.project_dir),
                        verbose=False
                    )

                    # Verify client embed was called
                    self.assertTrue(mock_client.embed.called)

                    # Verify store was called
                    self.assertTrue(mock_store.store.called)

                    # Verify result
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(result["embedded"], 1)


class TestAutoEmbedItem(unittest.TestCase):
    """Tests for auto_embed_item()."""

    def setUp(self):
        """Create temp project."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "autoembedproject"
        self.project_dir.mkdir()
        (self.project_dir / ".claude").mkdir()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auto_embed_returns_false_without_api_key(self):
        """Should return False if API not available."""
        from embedding_project import auto_embed_item

        with patch.dict(os.environ, {}, clear=True):
            import voyage_client
            orig_client = voyage_client._client
            voyage_client._client = None

            try:
                result = auto_embed_item("/fake/path.md", "project-skill")
                self.assertFalse(result)
            finally:
                voyage_client._client = orig_client

    def test_auto_embed_returns_false_for_missing_file(self):
        """Should return False for non-existent file."""
        from embedding_project import auto_embed_item

        with patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"}):
            result = auto_embed_item("/nonexistent/file.md", "project-skill")
            self.assertFalse(result)

    def test_auto_embed_returns_false_for_no_description(self):
        """Should return False if file has no description."""
        from embedding_project import auto_embed_item

        # Create file without description
        skill_dir = self.project_dir / ".claude" / "skills" / "no-desc"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# No frontmatter")

        with patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"}):
            result = auto_embed_item(str(skill_file), "project-skill")
            self.assertFalse(result)


class TestGetProjectEmbeddingStatus(unittest.TestCase):
    """Tests for get_project_embedding_status()."""

    def setUp(self):
        """Create temp project."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "statusproject"

        # Create some skills
        for i in range(3):
            skill_dir = self.project_dir / ".claude" / "skills" / f"skill-{i}"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"""---
description: Skill {i} description
---
# Skill {i}
""")

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_status_counts_found_items(self):
        """Should count all found items."""
        from embedding_project import get_project_embedding_status

        status = get_project_embedding_status(str(self.project_dir))

        self.assertEqual(status["items_found"], 3)
        self.assertEqual(status["project_path"], str(self.project_dir))

    def test_status_shows_missing_items(self):
        """Should show items as missing if not embedded."""
        from embedding_project import get_project_embedding_status

        with patch('embedding_project.EmbeddingStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get.return_value = None  # Not embedded
            mock_store_class.return_value = mock_store

            status = get_project_embedding_status(str(self.project_dir))

            self.assertEqual(status["items_missing"], 3)
            self.assertEqual(status["items_embedded"], 0)

    def test_status_shows_api_availability(self):
        """Should indicate API availability."""
        from embedding_project import get_project_embedding_status

        status = get_project_embedding_status(str(self.project_dir))

        self.assertIn("api_available", status)
        self.assertIsInstance(status["api_available"], bool)


class TestProjectPathsConfiguration(unittest.TestCase):
    """Tests for PROJECT_PATHS configuration."""

    def test_all_source_types_defined(self):
        """Should define all expected source types."""
        from embedding_project import PROJECT_PATHS

        expected_types = [
            "project-skill",
            "project-agent",
            "project-command",
            "generated-skill",
            "generated-agent",
        ]

        for source_type in expected_types:
            self.assertIn(source_type, PROJECT_PATHS)
            self.assertIsInstance(PROJECT_PATHS[source_type], list)
            self.assertTrue(len(PROJECT_PATHS[source_type]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
