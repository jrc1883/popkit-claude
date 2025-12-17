#!/usr/bin/env python3
"""
Stateless Post-Tool-Use Hook

Result processing and coordination using explicit context passing.
This is the stateless refactor of post-tool-use.py following issue #22.

All state is explicit - no SQLite or environment variable dependencies.
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from stateless_hook import StatelessHook
from context_carrier import HookContext


class PostToolUseStateless(StatelessHook):
    """Stateless post-tool-use hook implementation.

    Processes tool results and provides coordination:
    - Suggests followup actions based on tool type
    - Detects result truncation
    - Adds tool results to message history

    All processing is pure functions with no external state.
    """

    # Followup rules as class constants
    FOLLOWUP_RULES = {
        "Write": ["suggest_code_review", "check_for_tests"],
        "Edit": ["suggest_code_review", "run_linter"],
        "Bash": ["validate_output", "check_side_effects"],
        "Read": [],
        "Glob": [],
        "Grep": [],
    }

    # Truncation threshold in characters
    TRUNCATION_THRESHOLD = 50000

    def process(self, ctx: HookContext) -> HookContext:
        """Process post-tool-use actions.

        Args:
            ctx: Hook context with tool result

        Returns:
            Updated context with followup suggestions and message history
        """
        tool_name = ctx.tool_name
        tool_result = ctx.tool_result

        # Get followup suggestions
        followups = self._get_followups(tool_name, tool_result)

        # Detect truncation
        truncation_warning = self._check_truncation(tool_result)

        # Build message for context if we have a result
        if tool_result:
            message = self.build_tool_result(
                tool_use_id=f"toolu_{ctx.session_id}",
                content=tool_result
            )
            ctx = self.update_context(ctx, message=message)

        # Update context with hook output
        return self.update_context(
            ctx,
            hook_output=("post_tool_use", {
                "action": "continue",
                "followups": followups,
                "truncation_warning": truncation_warning
            })
        )

    def _get_followups(
        self,
        tool_name: str,
        tool_result: Optional[str]
    ) -> List[str]:
        """Get followup suggestions (pure function).

        Args:
            tool_name: Name of the tool that was executed
            tool_result: Result from tool execution

        Returns:
            List of followup action suggestions
        """
        return self.FOLLOWUP_RULES.get(tool_name, [])

    def _check_truncation(self, result: Optional[str]) -> str:
        """Check for result truncation (pure function).

        Args:
            result: Tool result string

        Returns:
            Warning message if truncated, empty string otherwise
        """
        if result and len(result) > self.TRUNCATION_THRESHOLD:
            return "Result may be truncated. Consider streaming or pagination."
        return ""


def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_json = sys.stdin.read()
        hook = PostToolUseStateless()
        output = hook.run(input_json)
        print(output)
    except Exception as e:
        print(json.dumps({"action": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
