#!/usr/bin/env python3
"""
Tests for Command Translator module

Part of Issue #89 - Platform-Aware Command Learning
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.platform_detector import OSType, ShellType, PlatformInfo, ShellCapabilities
from utils.command_translator import (
    CommandTranslator,
    CommandTranslation,
    CommandCategory,
    translate_command,
    get_translation_suggestions
)


class TestCommandIdentification(unittest.TestCase):
    """Tests for command identification"""

    def test_identify_cp(self):
        """Should identify cp as FILE_COPY"""
        category, base_cmd, args = CommandTranslator.identify_command("cp file1.txt file2.txt")
        self.assertEqual(category, CommandCategory.FILE_COPY)
        self.assertEqual(base_cmd, "cp")
        self.assertEqual(args, "file1.txt file2.txt")

    def test_identify_cp_recursive(self):
        """Should identify cp -r as FILE_COPY"""
        category, base_cmd, args = CommandTranslator.identify_command("cp -r source/ dest/")
        self.assertEqual(category, CommandCategory.FILE_COPY)
        self.assertEqual(base_cmd, "cp -r")
        self.assertEqual(args, "source/ dest/")

    def test_identify_rm_rf(self):
        """Should identify rm -rf as FILE_DELETE"""
        category, base_cmd, args = CommandTranslator.identify_command("rm -rf /tmp/test")
        self.assertEqual(category, CommandCategory.FILE_DELETE)
        self.assertEqual(base_cmd, "rm -rf")

    def test_identify_ls(self):
        """Should identify ls as DIR_LIST"""
        category, base_cmd, args = CommandTranslator.identify_command("ls")
        self.assertEqual(category, CommandCategory.DIR_LIST)
        self.assertEqual(base_cmd, "ls")

    def test_identify_cat(self):
        """Should identify cat as FILE_READ"""
        category, base_cmd, args = CommandTranslator.identify_command("cat file.txt")
        self.assertEqual(category, CommandCategory.FILE_READ)
        self.assertEqual(base_cmd, "cat")

    def test_identify_mkdir(self):
        """Should identify mkdir as DIR_CREATE"""
        category, base_cmd, args = CommandTranslator.identify_command("mkdir newdir")
        self.assertEqual(category, CommandCategory.DIR_CREATE)
        self.assertEqual(base_cmd, "mkdir")

    def test_identify_grep(self):
        """Should identify grep as TEXT_SEARCH"""
        category, base_cmd, args = CommandTranslator.identify_command("grep pattern file.txt")
        self.assertEqual(category, CommandCategory.TEXT_SEARCH)
        self.assertEqual(base_cmd, "grep")

    def test_identify_unknown(self):
        """Should return UNKNOWN for unrecognized commands"""
        category, base_cmd, args = CommandTranslator.identify_command("someunknowncommand arg1")
        self.assertEqual(category, CommandCategory.UNKNOWN)


class TestTranslationToCMD(unittest.TestCase):
    """Tests for translating Unix commands to CMD"""

    def test_translate_cp_to_cmd(self):
        """cp should translate to copy for CMD"""
        result = CommandTranslator.translate("cp file1.txt file2.txt", ShellType.CMD)
        self.assertEqual(result.translated, "copy file1.txt file2.txt")
        self.assertEqual(result.category, CommandCategory.FILE_COPY)

    def test_translate_cp_r_to_cmd(self):
        """cp -r should translate to xcopy for CMD"""
        result = CommandTranslator.translate("cp -r source/ dest/", ShellType.CMD)
        self.assertIn("xcopy", result.translated)
        self.assertIn("/E", result.translated)

    def test_translate_rm_to_cmd(self):
        """rm should translate to del for CMD"""
        result = CommandTranslator.translate("rm file.txt", ShellType.CMD)
        self.assertEqual(result.translated, "del file.txt")

    def test_translate_rm_rf_to_cmd(self):
        """rm -rf should translate to rmdir /S /Q for CMD"""
        result = CommandTranslator.translate("rm -rf directory", ShellType.CMD)
        self.assertIn("rmdir", result.translated)
        self.assertIn("/S", result.translated)
        self.assertIn("/Q", result.translated)

    def test_translate_ls_to_cmd(self):
        """ls should translate to dir for CMD"""
        result = CommandTranslator.translate("ls", ShellType.CMD)
        self.assertEqual(result.translated, "dir")

    def test_translate_cat_to_cmd(self):
        """cat should translate to type for CMD"""
        result = CommandTranslator.translate("cat file.txt", ShellType.CMD)
        self.assertEqual(result.translated, "type file.txt")


class TestTranslationToPowerShell(unittest.TestCase):
    """Tests for translating Unix commands to PowerShell"""

    def test_translate_cp_to_ps(self):
        """cp should translate to Copy-Item for PowerShell"""
        result = CommandTranslator.translate("cp file1.txt file2.txt", ShellType.POWERSHELL)
        self.assertIn("Copy-Item", result.translated)

    def test_translate_cp_r_to_ps(self):
        """cp -r should translate to Copy-Item -Recurse for PowerShell"""
        result = CommandTranslator.translate("cp -r source/ dest/", ShellType.POWERSHELL)
        self.assertIn("Copy-Item", result.translated)
        self.assertIn("-Recurse", result.translated)

    def test_translate_rm_to_ps(self):
        """rm should translate to Remove-Item for PowerShell"""
        result = CommandTranslator.translate("rm file.txt", ShellType.POWERSHELL)
        self.assertIn("Remove-Item", result.translated)

    def test_translate_ls_to_ps(self):
        """ls should translate to Get-ChildItem for PowerShell"""
        result = CommandTranslator.translate("ls", ShellType.POWERSHELL)
        self.assertEqual(result.translated, "Get-ChildItem")

    def test_translate_cat_to_ps(self):
        """cat should translate to Get-Content for PowerShell"""
        result = CommandTranslator.translate("cat file.txt", ShellType.POWERSHELL)
        self.assertIn("Get-Content", result.translated)


class TestTranslationToBash(unittest.TestCase):
    """Tests for translating Windows commands to Bash"""

    def test_translate_xcopy_to_bash(self):
        """xcopy should translate to cp -r for Bash"""
        result = CommandTranslator.translate("xcopy source dest", ShellType.BASH)
        self.assertIn("cp -r", result.translated)

    def test_translate_dir_to_bash(self):
        """dir should translate to ls for Bash"""
        result = CommandTranslator.translate("dir", ShellType.BASH)
        self.assertEqual(result.translated, "ls")

    def test_translate_type_to_bash(self):
        """type should translate to cat for Bash"""
        result = CommandTranslator.translate("type file.txt", ShellType.BASH)
        self.assertIn("cat", result.translated)


class TestTranslationConfidence(unittest.TestCase):
    """Tests for translation confidence scores"""

    def test_exact_translation_has_high_confidence(self):
        """Exact translations should have high confidence"""
        result = CommandTranslator.translate("cp file.txt file2.txt", ShellType.CMD)
        self.assertGreater(result.confidence, 0.8)

    def test_no_translation_needed_has_full_confidence(self):
        """Native commands should have full confidence"""
        result = CommandTranslator.translate("dir", ShellType.CMD)
        self.assertEqual(result.confidence, 1.0)

    def test_unknown_command_has_zero_confidence(self):
        """Unknown commands should have zero confidence"""
        result = CommandTranslator.translate("unknowncommand arg", ShellType.CMD)
        self.assertEqual(result.confidence, 0.0)


class TestPathTranslation(unittest.TestCase):
    """Tests for path translation"""

    def test_forward_slash_to_backslash_for_windows(self):
        """Forward slashes should be converted to backslashes for Windows"""
        result = CommandTranslator.translate("cp source/file.txt dest/", ShellType.CMD)
        self.assertIn("\\", result.translated)

    def test_backslash_to_forward_slash_for_unix(self):
        """Backslashes should be converted to forward slashes for Unix"""
        result = CommandTranslator.translate("xcopy source\\file.txt dest\\", ShellType.BASH)
        # After translation to cp, paths should have forward slashes
        self.assertIn("/", result.translated)


class TestGetAllTranslations(unittest.TestCase):
    """Tests for getting all translations"""

    def test_returns_dict_of_translations(self):
        """Should return dictionary of translations"""
        translations = CommandTranslator.get_all_translations("cp file.txt file2.txt")
        self.assertIsInstance(translations, dict)
        self.assertIn(ShellType.CMD, translations)
        self.assertIn(ShellType.POWERSHELL, translations)
        self.assertIn(ShellType.BASH, translations)

    def test_each_translation_is_command_translation(self):
        """Each translation should be a CommandTranslation"""
        translations = CommandTranslator.get_all_translations("ls")
        for shell_type, translation in translations.items():
            self.assertIsInstance(translation, CommandTranslation)


class TestErrorBasedSuggestion(unittest.TestCase):
    """Tests for error-based suggestions"""

    def test_suggests_for_command_not_found(self):
        """Should suggest translation for 'command not found' error"""
        mock_info = PlatformInfo(
            os_type=OSType.WINDOWS,
            os_version="Windows 10",
            shell_type=ShellType.CMD,
            shell_path="cmd.exe",
            shell_version="10.0",
            capabilities=ShellCapabilities(cmd_commands=True)
        )

        result = CommandTranslator.suggest_for_error(
            "cp file.txt file2.txt",
            "'cp' is not recognized as an internal or external command",
            mock_info
        )

        self.assertIsNotNone(result)
        self.assertIn("copy", result.translated)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions"""

    def test_translate_command(self):
        """translate_command should return translated string"""
        result = translate_command("ls", ShellType.CMD)
        self.assertEqual(result, "dir")

    def test_get_translation_suggestions(self):
        """get_translation_suggestions should return list of alternatives"""
        suggestions = get_translation_suggestions("cp file.txt file2.txt")
        self.assertIsInstance(suggestions, list)
        # Should have at least one suggestion (for other shells)
        self.assertGreater(len(suggestions), 0)


if __name__ == "__main__":
    unittest.main()
