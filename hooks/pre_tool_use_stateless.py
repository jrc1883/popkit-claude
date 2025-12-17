#!/usr/bin/env python3
"""
Stateless Pre-Tool-Use Hook

Safety checks and coordination using explicit context passing.
This is the stateless refactor of pre-tool-use.py following issue #22.

All state is explicit - no SQLite or environment variable dependencies.
"""

import os
import sys
import json
import re
from typing import Dict, List, Any

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from stateless_hook import StatelessHook
from context_carrier import HookContext


class PreToolUseStateless(StatelessHook):
    """Stateless pre-tool-use hook implementation.

    Performs safety checks before tool execution:
    - Blocks dangerous shell commands (rm -rf /, DROP DATABASE, etc.)
    - Blocks access to sensitive paths (.env, .ssh, .aws/credentials)
    - Provides recommendations for code modifications

    All checks are pure functions with no external state.
    """

    # Safety rules as class constants (no external state)
    BLOCKED_COMMANDS = [
        r"rm\s+-rf\s+/",           # rm -rf /
        r"sudo\s+rm\s+-rf",        # sudo rm -rf anything
        r"DROP\s+DATABASE",        # SQL DROP DATABASE
        r"TRUNCATE\s+TABLE",       # SQL TRUNCATE TABLE
        r">\s*/dev/sd[a-z]",       # Write to disk device
        r"mkfs\.",                 # Format filesystem
        r":(){:|:&};:",           # Fork bomb
    ]

    SENSITIVE_PATHS = [
        r"\.env",                  # Environment files
        r"\.ssh/",                 # SSH keys
        r"\.aws/credentials",      # AWS credentials
        r"\.gnupg/",              # GPG keys
        r"id_rsa",                # SSH private keys
        r"\.npmrc",               # NPM tokens
        r"\.pypirc",              # PyPI tokens
    ]

    CODE_EXTENSIONS = ['.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.java']

    def process(self, ctx: HookContext) -> HookContext:
        """Process pre-tool-use safety checks.

        Args:
            ctx: Hook context with tool_name, tool_input

        Returns:
            Updated context with safety_check results and recommendations
        """
        tool_name = ctx.tool_name
        tool_input = ctx.tool_input

        # Safety checks
        violations = self._check_safety_violations(tool_name, tool_input)

        # Build result
        safety_check = {
            "passed": len(violations) == 0,
            "violations": violations
        }

        # Coordination suggestions
        recommendations = self._get_recommendations(tool_name, tool_input)

        # Determine action
        action = "block" if violations else "continue"

        # Update context with results (immutable - returns new context)
        return self.update_context(
            ctx,
            hook_output=("pre_tool_use", {
                "action": action,
                "safety_check": safety_check,
                "recommendations": recommendations
            })
        )

    def _check_safety_violations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> List[str]:
        """Check for safety violations (pure function).

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Tool input parameters

        Returns:
            List of violation descriptions (empty if safe)
        """
        violations = []

        # Check Bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            for pattern in self.BLOCKED_COMMANDS:
                if re.search(pattern, command, re.IGNORECASE):
                    violations.append(f"Blocked command pattern: {pattern}")

        # Check file access
        if tool_name in ("Write", "Edit", "Read"):
            file_path = tool_input.get("file_path", "")
            for pattern in self.SENSITIVE_PATHS:
                if re.search(pattern, file_path):
                    violations.append(f"Sensitive path access: {pattern}")

        return violations

    def _get_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> List[str]:
        """Get recommendations for the tool use (pure function).

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Tool input parameters

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")

            # Check if it's a code file
            for ext in self.CODE_EXTENSIONS:
                if file_path.endswith(ext):
                    recommendations.append(
                        "Consider running code-reviewer after file modifications"
                    )
                    break

            # Check if it's a test file
            if "test" in file_path.lower() or "spec" in file_path.lower():
                recommendations.append(
                    "Consider running test-writer-fixer for test modifications"
                )

            # Check if it's a config file
            if file_path.endswith(('.json', '.yaml', '.yml', '.toml')):
                recommendations.append(
                    "Config file modified - verify no secrets exposed"
                )

        return recommendations


def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_json = sys.stdin.read()
        hook = PreToolUseStateless()
        output = hook.run(input_json)
        print(output)
    except Exception as e:
        print(json.dumps({"action": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
