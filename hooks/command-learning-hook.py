#!/usr/bin/env python3
"""
Command Learning Hook for PopKit

Part of Issue #89 - Platform-Aware Command Learning

PostToolUse hook that captures command failures and learns from them.
Also provides PreToolUse suggestions for commands that have known corrections.
"""

import os
import sys
import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))

from utils.platform_detector import (
    PlatformDetector,
    PlatformInfo,
    OSType,
    ShellType,
    get_platform_info
)
from utils.command_translator import (
    CommandTranslator,
    CommandTranslation,
    CommandCategory,
    translate_command
)
from utils.pattern_learner import (
    PatternLearner,
    CommandCorrection,
    CorrectionSuggestion,
    get_learner,
    learn_correction,
    suggest_correction
)


class CommandLearningHook:
    """
    Hook for learning command corrections from failures and successes.

    Events:
    - PostToolUse (Bash): Captures failures, learns from corrections
    - PreToolUse (Bash): Suggests corrections for known problematic commands
    """

    # Error patterns that indicate command failure
    ERROR_PATTERNS = [
        # Command not found
        (r"'(\w+)' is not recognized as an internal or external command",
         "command_not_found", "windows"),
        (r"(\w+): command not found", "command_not_found", "unix"),
        (r"bash: (\w+): command not found", "command_not_found", "unix"),

        # Path errors
        (r"The system cannot find the path specified", "path_not_found", "windows"),
        (r"No such file or directory", "path_not_found", "unix"),
        (r"cannot stat '(.+)': No such file", "path_not_found", "unix"),

        # Permission errors
        (r"Access is denied", "permission_denied", "windows"),
        (r"Permission denied", "permission_denied", "unix"),

        # Parameter errors
        (r"Invalid parameter", "invalid_params", "windows"),
        (r"Invalid switch", "invalid_params", "windows"),
        (r"invalid option", "invalid_params", "unix"),
        (r"unrecognized option", "invalid_params", "unix"),

        # Copy/directory errors
        (r"cannot copy a directory", "recursive_needed", "unix"),
        (r"omitting directory", "recursive_needed", "unix"),
        (r"xcopy.*Invalid number of parameters", "xcopy_syntax", "windows"),

        # Syntax errors
        (r"syntax error", "syntax_error", "any"),
        (r"unexpected token", "syntax_error", "unix"),
        (r"The syntax of the command is incorrect", "syntax_error", "windows"),
    ]

    # Exit codes that indicate failure
    FAILURE_EXIT_CODES = {1, 2, 126, 127, 128, 255}

    def __init__(self):
        self.learner = get_learner()
        self.platform_info = get_platform_info()

    def process_post_tool_use(self, hook_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PostToolUse event for Bash commands.

        Args:
            hook_input: The hook input from Claude Code

        Returns:
            Hook output with any messages or modifications
        """
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        tool_output = hook_input.get("tool_output", "")

        # Only process Bash tool
        if tool_name != "Bash":
            return {"continue": True}

        command = tool_input.get("command", "")
        if not command:
            return {"continue": True}

        # Check if command failed
        exit_code = self._extract_exit_code(tool_output)
        error_type, error_match = self._detect_error(tool_output)

        if error_type:
            # Command failed - try to learn and suggest
            return self._handle_failure(command, tool_output, error_type, error_match)

        elif exit_code == 0:
            # Command succeeded - record success if it was a learned correction
            self._record_success_if_learned(command)

        return {"continue": True}

    def process_pre_tool_use(self, hook_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PreToolUse event to suggest corrections before execution.

        Args:
            hook_input: The hook input from Claude Code

        Returns:
            Hook output with suggestions or modifications
        """
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})

        # Only process Bash tool
        if tool_name != "Bash":
            return {"continue": True}

        command = tool_input.get("command", "")
        if not command:
            return {"continue": True}

        # Check for known corrections
        suggestion = self.learner.get_best_suggestion(
            command,
            platform=self.platform_info.os_type.value,
            shell=self.platform_info.shell_type.value,
            min_confidence=0.7
        )

        if suggestion:
            # We have a high-confidence suggestion
            return {
                "continue": True,
                "message": (
                    f"[PopKit Learning] This command may need adjustment for your platform:\n"
                    f"  Original: {command}\n"
                    f"  Suggested: {suggestion.suggested}\n"
                    f"  Confidence: {suggestion.confidence:.0%}\n"
                    f"  Reason: {suggestion.reason or 'Learned from previous corrections'}"
                )
            }

        # Check if command translation is available
        translation = CommandTranslator.translate(
            command,
            self.platform_info.shell_type
        )

        if translation.translated != command and translation.confidence > 0.8:
            return {
                "continue": True,
                "message": (
                    f"[PopKit Learning] Command translated for {self.platform_info.shell_type.value}:\n"
                    f"  Original: {command}\n"
                    f"  Translated: {translation.translated}"
                )
            }

        return {"continue": True}

    def _extract_exit_code(self, output: str) -> int:
        """Extract exit code from tool output"""
        # Claude Code typically includes exit code in output
        match = re.search(r"Exit code:?\s*(\d+)", output, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Check for explicit error indicators
        if any(pattern in output.lower() for pattern in
               ["error", "failed", "not found", "denied", "invalid"]):
            return 1

        return 0

    def _detect_error(self, output: str) -> tuple[Optional[str], Optional[re.Match]]:
        """Detect error type from output"""
        for pattern, error_type, platform_hint in self.ERROR_PATTERNS:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                # Check if platform hint matches
                if platform_hint != "any":
                    if platform_hint == "windows" and self.platform_info.os_type != OSType.WINDOWS:
                        continue
                    if platform_hint == "unix" and self.platform_info.os_type == OSType.WINDOWS:
                        # Could be Git Bash on Windows
                        if self.platform_info.shell_type != ShellType.GIT_BASH:
                            continue
                return error_type, match
        return None, None

    def _handle_failure(
        self,
        command: str,
        output: str,
        error_type: str,
        error_match: Optional[re.Match]
    ) -> Dict[str, Any]:
        """Handle a command failure"""
        messages = []

        # Try to get a translation suggestion
        translation = CommandTranslator.suggest_for_error(
            command, output, self.platform_info
        )

        if translation and translation.translated != command:
            # Record this as a learned correction
            correction = self.learner.record_correction(
                original_command=command,
                corrected_command=translation.translated,
                error_pattern=error_type,
                source="auto"
            )

            messages.append(
                f"[PopKit Learning] Command failed. Learned correction:\n"
                f"  Failed: {command}\n"
                f"  Try: {translation.translated}\n"
                f"  Error type: {error_type}"
            )

        else:
            # No automatic translation - check for similar learned patterns
            suggestions = self.learner.find_suggestions(
                command,
                min_confidence=0.5
            )

            if suggestions:
                best = suggestions[0]
                messages.append(
                    f"[PopKit Learning] Command failed. Similar pattern found:\n"
                    f"  Failed: {command}\n"
                    f"  Try: {best.suggested}\n"
                    f"  Confidence: {best.confidence:.0%}"
                )
            else:
                # Log the failure for manual review
                messages.append(
                    f"[PopKit Learning] Command failed ({error_type}). "
                    f"No automatic correction available.\n"
                    f"  Command: {command}\n"
                    f"  Use '/popkit:learn' to teach a correction."
                )

        return {
            "continue": True,
            "message": "\n".join(messages) if messages else None
        }

    def _record_success_if_learned(self, command: str) -> None:
        """Record success if this command was a learned correction"""
        # Check if this command exists as a correction
        suggestions = self.learner.find_suggestions(command, min_confidence=0.0)

        for suggestion in suggestions:
            if suggestion.suggested == command:
                # This was a learned correction that succeeded
                # We need to find the correction ID and record success
                corrections = self.learner.get_all_corrections(
                    platform=self.platform_info.os_type.value,
                    shell=self.platform_info.shell_type.value
                )
                for correction in corrections:
                    if correction.corrected_command == command:
                        self.learner.record_success(correction.id)
                        break
                break


def main():
    """Main entry point for the hook"""
    # Read input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True, "error": "Invalid JSON input"}))
        return

    hook = CommandLearningHook()
    event_type = hook_input.get("event", "")

    if event_type == "PostToolUse":
        result = hook.process_post_tool_use(hook_input)
    elif event_type == "PreToolUse":
        result = hook.process_pre_tool_use(hook_input)
    else:
        result = {"continue": True}

    # Output result
    print(json.dumps(result))


if __name__ == "__main__":
    main()
