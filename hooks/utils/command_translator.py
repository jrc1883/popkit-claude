#!/usr/bin/env python3
"""
Command Translator for PopKit Command Learning

Part of Issue #89 - Platform-Aware Command Learning

Translates commands between different platforms and shells,
providing cross-platform equivalents for common operations.
"""

import re
import shlex
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .platform_detector import (
    PlatformDetector,
    OSType,
    ShellType,
    PlatformInfo,
    get_platform_info
)


class CommandCategory(Enum):
    """Categories of commands"""
    FILE_COPY = "file_copy"
    FILE_MOVE = "file_move"
    FILE_DELETE = "file_delete"
    DIR_LIST = "dir_list"
    FILE_READ = "file_read"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    FILE_FIND = "file_find"
    TEXT_SEARCH = "text_search"
    PERMISSIONS = "permissions"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


@dataclass
class CommandTranslation:
    """A translation result for a command"""
    original: str
    translated: str
    target_shell: ShellType
    category: CommandCategory
    confidence: float  # 0.0 to 1.0
    notes: Optional[str] = None
    requires_quoting: bool = False


class CommandTranslator:
    """Translates commands between platforms and shells"""

    # Command translation maps
    # Format: {category: {source_pattern: {target_shell: translation_template}}}
    TRANSLATION_MAP: Dict[CommandCategory, Dict[str, Dict[ShellType, str]]] = {
        CommandCategory.FILE_COPY: {
            "cp": {
                ShellType.CMD: "copy",
                ShellType.POWERSHELL: "Copy-Item",
                ShellType.POWERSHELL_CORE: "Copy-Item",
            },
            "cp -r": {
                ShellType.CMD: "xcopy /E /I /Y",
                ShellType.POWERSHELL: "Copy-Item -Recurse",
                ShellType.POWERSHELL_CORE: "Copy-Item -Recurse",
            },
            "xcopy": {
                ShellType.BASH: "cp -r",
                ShellType.ZSH: "cp -r",
                ShellType.GIT_BASH: "cp -r",
            },
            "copy": {
                ShellType.BASH: "cp",
                ShellType.ZSH: "cp",
                ShellType.GIT_BASH: "cp",
            },
            "Copy-Item": {
                ShellType.BASH: "cp",
                ShellType.CMD: "copy",
            },
        },
        CommandCategory.FILE_MOVE: {
            "mv": {
                ShellType.CMD: "move",
                ShellType.POWERSHELL: "Move-Item",
                ShellType.POWERSHELL_CORE: "Move-Item",
            },
            "move": {
                ShellType.BASH: "mv",
                ShellType.ZSH: "mv",
                ShellType.GIT_BASH: "mv",
            },
            "Move-Item": {
                ShellType.BASH: "mv",
                ShellType.CMD: "move",
            },
        },
        CommandCategory.FILE_DELETE: {
            "rm": {
                ShellType.CMD: "del",
                ShellType.POWERSHELL: "Remove-Item",
                ShellType.POWERSHELL_CORE: "Remove-Item",
            },
            "rm -rf": {
                ShellType.CMD: "rmdir /S /Q",
                ShellType.POWERSHELL: "Remove-Item -Recurse -Force",
                ShellType.POWERSHELL_CORE: "Remove-Item -Recurse -Force",
            },
            "rm -r": {
                ShellType.CMD: "rmdir /S /Q",
                ShellType.POWERSHELL: "Remove-Item -Recurse",
                ShellType.POWERSHELL_CORE: "Remove-Item -Recurse",
            },
            "del": {
                ShellType.BASH: "rm",
                ShellType.ZSH: "rm",
                ShellType.GIT_BASH: "rm",
            },
            "rmdir": {
                ShellType.BASH: "rm -r",
                ShellType.ZSH: "rm -r",
                ShellType.GIT_BASH: "rm -r",
            },
            "Remove-Item": {
                ShellType.BASH: "rm",
                ShellType.CMD: "del",
            },
        },
        CommandCategory.DIR_LIST: {
            "ls": {
                ShellType.CMD: "dir",
                ShellType.POWERSHELL: "Get-ChildItem",
                ShellType.POWERSHELL_CORE: "Get-ChildItem",
            },
            "ls -la": {
                ShellType.CMD: "dir /A",
                ShellType.POWERSHELL: "Get-ChildItem -Force",
                ShellType.POWERSHELL_CORE: "Get-ChildItem -Force",
            },
            "ls -l": {
                ShellType.CMD: "dir",
                ShellType.POWERSHELL: "Get-ChildItem | Format-List",
                ShellType.POWERSHELL_CORE: "Get-ChildItem | Format-List",
            },
            "dir": {
                ShellType.BASH: "ls",
                ShellType.ZSH: "ls",
                ShellType.GIT_BASH: "ls",
            },
            "Get-ChildItem": {
                ShellType.BASH: "ls",
                ShellType.CMD: "dir",
            },
        },
        CommandCategory.FILE_READ: {
            "cat": {
                ShellType.CMD: "type",
                ShellType.POWERSHELL: "Get-Content",
                ShellType.POWERSHELL_CORE: "Get-Content",
            },
            "type": {
                ShellType.BASH: "cat",
                ShellType.ZSH: "cat",
                ShellType.GIT_BASH: "cat",
            },
            "Get-Content": {
                ShellType.BASH: "cat",
                ShellType.CMD: "type",
            },
            "head": {
                ShellType.CMD: "more",
                ShellType.POWERSHELL: "Get-Content -Head",
                ShellType.POWERSHELL_CORE: "Get-Content -Head",
            },
            "tail": {
                ShellType.CMD: "more",
                ShellType.POWERSHELL: "Get-Content -Tail",
                ShellType.POWERSHELL_CORE: "Get-Content -Tail",
            },
        },
        CommandCategory.DIR_CREATE: {
            "mkdir": {
                ShellType.CMD: "mkdir",  # Same on both
                ShellType.POWERSHELL: "New-Item -ItemType Directory",
                ShellType.POWERSHELL_CORE: "New-Item -ItemType Directory",
            },
            "mkdir -p": {
                ShellType.CMD: "mkdir",  # CMD creates intermediate dirs
                ShellType.POWERSHELL: "New-Item -ItemType Directory -Force",
                ShellType.POWERSHELL_CORE: "New-Item -ItemType Directory -Force",
            },
            "New-Item": {
                ShellType.BASH: "mkdir",
                ShellType.CMD: "mkdir",
            },
        },
        CommandCategory.TEXT_SEARCH: {
            "grep": {
                ShellType.CMD: "findstr",
                ShellType.POWERSHELL: "Select-String",
                ShellType.POWERSHELL_CORE: "Select-String",
            },
            "grep -r": {
                ShellType.CMD: "findstr /S",
                ShellType.POWERSHELL: "Select-String -Recurse",
                ShellType.POWERSHELL_CORE: "Select-String -Recurse",
            },
            "findstr": {
                ShellType.BASH: "grep",
                ShellType.ZSH: "grep",
                ShellType.GIT_BASH: "grep",
            },
            "Select-String": {
                ShellType.BASH: "grep",
                ShellType.CMD: "findstr",
            },
        },
        CommandCategory.FILE_FIND: {
            "find": {
                ShellType.CMD: "dir /S /B",
                ShellType.POWERSHELL: "Get-ChildItem -Recurse",
                ShellType.POWERSHELL_CORE: "Get-ChildItem -Recurse",
            },
            "find . -name": {
                ShellType.CMD: "dir /S /B",
                ShellType.POWERSHELL: "Get-ChildItem -Recurse -Filter",
                ShellType.POWERSHELL_CORE: "Get-ChildItem -Recurse -Filter",
            },
        },
    }

    # Regex patterns to identify commands
    COMMAND_PATTERNS = [
        (r'^cp\s+-r\s+', CommandCategory.FILE_COPY, "cp -r"),
        (r'^cp\s+', CommandCategory.FILE_COPY, "cp"),
        (r'^xcopy\s+', CommandCategory.FILE_COPY, "xcopy"),
        (r'^copy\s+', CommandCategory.FILE_COPY, "copy"),
        (r'^Copy-Item\s+', CommandCategory.FILE_COPY, "Copy-Item"),
        (r'^mv\s+', CommandCategory.FILE_MOVE, "mv"),
        (r'^move\s+', CommandCategory.FILE_MOVE, "move"),
        (r'^Move-Item\s+', CommandCategory.FILE_MOVE, "Move-Item"),
        (r'^rm\s+-rf\s+', CommandCategory.FILE_DELETE, "rm -rf"),
        (r'^rm\s+-r\s+', CommandCategory.FILE_DELETE, "rm -r"),
        (r'^rm\s+', CommandCategory.FILE_DELETE, "rm"),
        (r'^del\s+', CommandCategory.FILE_DELETE, "del"),
        (r'^rmdir\s+', CommandCategory.DIR_DELETE, "rmdir"),
        (r'^Remove-Item\s+', CommandCategory.FILE_DELETE, "Remove-Item"),
        (r'^ls\s+-la\s*', CommandCategory.DIR_LIST, "ls -la"),
        (r'^ls\s+-l\s*', CommandCategory.DIR_LIST, "ls -l"),
        (r'^ls\s*', CommandCategory.DIR_LIST, "ls"),
        (r'^dir\s*', CommandCategory.DIR_LIST, "dir"),
        (r'^Get-ChildItem\s*', CommandCategory.DIR_LIST, "Get-ChildItem"),
        (r'^cat\s+', CommandCategory.FILE_READ, "cat"),
        (r'^type\s+', CommandCategory.FILE_READ, "type"),
        (r'^Get-Content\s+', CommandCategory.FILE_READ, "Get-Content"),
        (r'^head\s+', CommandCategory.FILE_READ, "head"),
        (r'^tail\s+', CommandCategory.FILE_READ, "tail"),
        (r'^mkdir\s+-p\s+', CommandCategory.DIR_CREATE, "mkdir -p"),
        (r'^mkdir\s+', CommandCategory.DIR_CREATE, "mkdir"),
        (r'^New-Item\s+', CommandCategory.DIR_CREATE, "New-Item"),
        (r'^grep\s+-r\s+', CommandCategory.TEXT_SEARCH, "grep -r"),
        (r'^grep\s+', CommandCategory.TEXT_SEARCH, "grep"),
        (r'^findstr\s+', CommandCategory.TEXT_SEARCH, "findstr"),
        (r'^Select-String\s+', CommandCategory.TEXT_SEARCH, "Select-String"),
        (r'^find\s+\.\s+-name\s+', CommandCategory.FILE_FIND, "find . -name"),
        (r'^find\s+', CommandCategory.FILE_FIND, "find"),
    ]

    @classmethod
    def identify_command(cls, command: str) -> Tuple[CommandCategory, str, str]:
        """
        Identify a command's category and base form.

        Args:
            command: The command string to identify

        Returns:
            Tuple of (category, base_command, arguments)
        """
        command = command.strip()

        for pattern, category, base_cmd in cls.COMMAND_PATTERNS:
            match = re.match(pattern, command, re.IGNORECASE)
            if match:
                # Extract arguments after the matched command
                args = command[match.end():].strip()
                return category, base_cmd, args

        return CommandCategory.UNKNOWN, command.split()[0] if command else "", ""

    @classmethod
    def translate(
        cls,
        command: str,
        target_shell: Optional[ShellType] = None,
        source_shell: Optional[ShellType] = None
    ) -> CommandTranslation:
        """
        Translate a command to the target shell.

        Args:
            command: The command to translate
            target_shell: Target shell type (defaults to current shell)
            source_shell: Source shell type (auto-detected if not specified)

        Returns:
            CommandTranslation with the translated command
        """
        platform_info = get_platform_info()

        if target_shell is None:
            target_shell = platform_info.shell_type

        # Identify the command
        category, base_cmd, args = cls.identify_command(command)

        if category == CommandCategory.UNKNOWN:
            return CommandTranslation(
                original=command,
                translated=command,
                target_shell=target_shell,
                category=category,
                confidence=0.0,
                notes="Unknown command - no translation available"
            )

        # Look up translation
        category_map = cls.TRANSLATION_MAP.get(category, {})
        command_map = category_map.get(base_cmd, {})
        translation_template = command_map.get(target_shell)

        if translation_template is None:
            # No translation needed or available
            return CommandTranslation(
                original=command,
                translated=command,
                target_shell=target_shell,
                category=category,
                confidence=1.0 if cls._is_native_for_shell(base_cmd, target_shell) else 0.5,
                notes="No translation needed" if cls._is_native_for_shell(base_cmd, target_shell)
                      else "No translation available"
            )

        # Build translated command with arguments
        translated = cls._build_translated_command(
            translation_template, args, target_shell
        )

        return CommandTranslation(
            original=command,
            translated=translated,
            target_shell=target_shell,
            category=category,
            confidence=0.9,
            requires_quoting=cls._needs_quoting(args, target_shell)
        )

    @classmethod
    def _is_native_for_shell(cls, command: str, shell_type: ShellType) -> bool:
        """Check if a command is native to the given shell"""
        unix_shells = {ShellType.BASH, ShellType.ZSH, ShellType.FISH,
                      ShellType.SH, ShellType.GIT_BASH, ShellType.WSL}
        windows_shells = {ShellType.CMD, ShellType.POWERSHELL, ShellType.POWERSHELL_CORE}

        unix_commands = {"cp", "mv", "rm", "ls", "cat", "grep", "find", "mkdir", "head", "tail"}
        cmd_commands = {"copy", "move", "del", "dir", "type", "findstr", "mkdir", "xcopy", "robocopy"}
        ps_commands = {"Copy-Item", "Move-Item", "Remove-Item", "Get-ChildItem",
                      "Get-Content", "Select-String", "New-Item"}

        base = command.split()[0].lower()

        if shell_type in unix_shells and base in unix_commands:
            return True
        if shell_type == ShellType.CMD and base in cmd_commands:
            return True
        if shell_type in {ShellType.POWERSHELL, ShellType.POWERSHELL_CORE}:
            # PowerShell is case-insensitive
            if any(base == ps.lower() for ps in ps_commands):
                return True
        return False

    @classmethod
    def _build_translated_command(
        cls,
        template: str,
        args: str,
        target_shell: ShellType
    ) -> str:
        """Build the translated command with arguments"""
        if not args:
            return template

        # Handle path arguments with proper quoting
        args = cls._translate_paths(args, target_shell)

        return f"{template} {args}"

    @classmethod
    def _translate_paths(cls, args: str, target_shell: ShellType) -> str:
        """Translate path separators and quoting for the target shell"""
        if target_shell in {ShellType.CMD, ShellType.POWERSHELL, ShellType.POWERSHELL_CORE}:
            # Convert forward slashes to backslashes for Windows
            # But be careful not to convert flags
            parts = args.split()
            translated_parts = []
            for part in parts:
                if part.startswith('-') or part.startswith('/'):
                    # It's a flag, keep as-is
                    translated_parts.append(part)
                elif '/' in part and not part.startswith('http'):
                    # It's likely a path, convert
                    translated_parts.append(part.replace('/', '\\'))
                else:
                    translated_parts.append(part)
            return ' '.join(translated_parts)
        else:
            # Convert backslashes to forward slashes for Unix
            parts = args.split()
            translated_parts = []
            for part in parts:
                if '\\' in part:
                    translated_parts.append(part.replace('\\', '/'))
                else:
                    translated_parts.append(part)
            return ' '.join(translated_parts)

    @classmethod
    def _needs_quoting(cls, args: str, target_shell: ShellType) -> bool:
        """Check if arguments need quoting for the target shell"""
        # Check for spaces in paths
        if ' ' in args:
            return True
        # Check for special characters
        special_chars = {'&', '|', '<', '>', '^', '%', '$', '!', '`'}
        return any(c in args for c in special_chars)

    @classmethod
    def get_all_translations(
        cls,
        command: str
    ) -> Dict[ShellType, CommandTranslation]:
        """
        Get translations for all shell types.

        Args:
            command: The command to translate

        Returns:
            Dictionary mapping shell types to their translations
        """
        translations = {}
        for shell_type in ShellType:
            if shell_type != ShellType.UNKNOWN:
                translations[shell_type] = cls.translate(command, shell_type)
        return translations

    @classmethod
    def suggest_for_error(
        cls,
        command: str,
        error_message: str,
        platform_info: Optional[PlatformInfo] = None
    ) -> Optional[CommandTranslation]:
        """
        Suggest a translation based on an error message.

        Args:
            command: The command that failed
            error_message: The error message received
            platform_info: Platform info (auto-detected if not provided)

        Returns:
            Suggested translation or None
        """
        if platform_info is None:
            platform_info = get_platform_info()

        # Common error patterns
        error_patterns = [
            # Unix command not found on Windows
            (r"'(\w+)' is not recognized", ShellType.CMD),
            (r"(\w+): command not found", None),  # Need to translate to native
            # Permission errors
            (r"Access is denied", None),
            (r"Permission denied", None),
            # Path errors
            (r"cannot find path", None),
            (r"No such file or directory", None),
        ]

        for pattern, suggested_shell in error_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                # Determine target shell
                if suggested_shell:
                    target = suggested_shell
                else:
                    target = platform_info.shell_type

                translation = cls.translate(command, target)
                if translation.translated != command:
                    return translation

        return None


def translate_command(command: str, target_shell: Optional[ShellType] = None) -> str:
    """Convenience function to translate a command"""
    result = CommandTranslator.translate(command, target_shell)
    return result.translated


def get_translation_suggestions(command: str) -> List[str]:
    """Get all possible translations for a command"""
    translations = CommandTranslator.get_all_translations(command)
    return [t.translated for t in translations.values() if t.translated != command]


if __name__ == "__main__":
    # Test the translator
    test_commands = [
        "cp -r source/ dest/",
        "rm -rf /tmp/test",
        "ls -la",
        "cat file.txt",
        "mkdir -p deep/nested/dir",
        "grep -r 'pattern' .",
    ]

    info = get_platform_info()
    print(f"Current shell: {info.shell_type.value}")
    print("\nCommand Translations:")
    print("=" * 60)

    for cmd in test_commands:
        print(f"\nOriginal: {cmd}")
        for shell_type in [ShellType.BASH, ShellType.CMD, ShellType.POWERSHELL]:
            result = CommandTranslator.translate(cmd, shell_type)
            print(f"  {shell_type.value}: {result.translated} (confidence: {result.confidence})")
