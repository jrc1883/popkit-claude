#!/usr/bin/env python3
"""
Stateless Hook Base Class

Provides a foundation for building hooks that follow stateless message composition.
Hooks extending this class receive explicit context, use message builder utilities,
and return complete output including updated context.

Part of the popkit plugin stateless hook architecture.
"""

import json
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from context_carrier import (
    HookContext,
    create_context,
    update_context,
    serialize_context,
    deserialize_context
)
from message_builder import (
    build_user_message,
    build_assistant_message,
    build_tool_use_message,
    build_tool_result_message,
    compose_conversation,
    rebuild_from_history
)


class StatelessHook(ABC):
    """Base class for stateless hooks.

    Hooks extending this class:
    - Receive explicit context (no hidden state)
    - Use message builder utilities for composition
    - Return complete output including updated context

    Example:
        class MyHook(StatelessHook):
            def process(self, ctx: HookContext) -> HookContext:
                # Do processing
                return self.update_context(ctx, tool_result="done")

    The hook can then be run via JSON protocol:
        output = run_hook(MyHook, input_json)
    """

    def __init__(self):
        """Initialize hook - no external state."""
        pass

    @abstractmethod
    def process(self, ctx: HookContext) -> HookContext:
        """Process the hook with given context.

        This is the main method to implement. Receive context,
        do processing, return updated context.

        Args:
            ctx: Immutable hook context

        Returns:
            New context with updates (original unchanged)
        """
        pass

    # =========================================================================
    # Context Helpers
    # =========================================================================

    def create_context(self, **kwargs) -> HookContext:
        """Create a new hook context.

        Args:
            **kwargs: Context fields (session_id, tool_name, tool_input, etc.)

        Returns:
            New HookContext instance
        """
        return create_context(**kwargs)

    def update_context(self, ctx: HookContext, **updates) -> HookContext:
        """Update context with new values (returns new context).

        Args:
            ctx: Existing context
            **updates: Fields to update

        Returns:
            New context with updates applied
        """
        return update_context(ctx, **updates)

    # =========================================================================
    # Message Builder Helpers
    # =========================================================================

    def build_user_message(self, content):
        """Build a user role message.

        Args:
            content: String or list of content blocks

        Returns:
            Message dict with role="user"
        """
        return build_user_message(content)

    def build_assistant_message(self, content):
        """Build an assistant role message.

        Args:
            content: String or list of content blocks

        Returns:
            Message dict with role="assistant"
        """
        return build_assistant_message(content)

    def build_tool_use(self, tool_use_id, name, input):
        """Build an assistant message with tool use.

        Args:
            tool_use_id: Unique ID for this tool use
            name: Tool name
            input: Tool input parameters

        Returns:
            Message dict with tool_use content block
        """
        return build_tool_use_message(tool_use_id, name, input)

    def build_tool_result(self, tool_use_id, content, is_error=False):
        """Build a user message with tool result.

        Args:
            tool_use_id: ID matching the tool_use
            content: Result content
            is_error: Whether this is an error result

        Returns:
            Message dict with tool_result content block
        """
        return build_tool_result_message(tool_use_id, content, is_error)

    def compose_messages(self, messages):
        """Compose a conversation from a list of messages.

        Args:
            messages: List of message dicts

        Returns:
            Validated conversation array
        """
        return compose_conversation(messages)

    def rebuild_messages(self, history):
        """Rebuild message array from history dict.

        Args:
            history: Dict with user_prompt, tool_uses, tool_results

        Returns:
            Complete conversation array
        """
        return rebuild_from_history(history)

    # =========================================================================
    # JSON Protocol
    # =========================================================================

    def run(self, input_json: str) -> str:
        """Run the hook with JSON input.

        This implements the Claude Code hook JSON protocol:
        - Receive JSON on stdin with tool_name, tool_input, session_id
        - Process the hook
        - Return JSON with action, context, and any output

        Args:
            input_json: JSON string with hook input

        Returns:
            JSON string with action and context

        Example:
            >>> input_json = '{"tool_name": "Read", "tool_input": {...}}'
            >>> output = hook.run(input_json)
            >>> # output: '{"action": "continue", "context": {...}}'
        """
        try:
            input_data = json.loads(input_json)

            # Create context from input
            ctx = create_context(
                session_id=input_data.get('session_id', 'unknown'),
                tool_name=input_data.get('tool_name', ''),
                tool_input=input_data.get('tool_input', {}),
                message_history=input_data.get('message_history', [])
            )

            # Process
            result_ctx = self.process(ctx)

            # Build output
            output = {
                "action": "continue",
                "context": json.loads(serialize_context(result_ctx))
            }

            return json.dumps(output)

        except Exception as e:
            return json.dumps({
                "action": "error",
                "error": str(e)
            })


def run_hook(hook_class: Type[StatelessHook], input_json: str) -> str:
    """Run a hook class with JSON input.

    Convenience function that instantiates the hook class and runs it.

    Args:
        hook_class: StatelessHook subclass to instantiate
        input_json: JSON input string

    Returns:
        JSON output string

    Example:
        >>> output = run_hook(MyHook, '{"tool_name": "Read", ...}')
    """
    hook = hook_class()
    return hook.run(input_json)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    # Quick manual test
    print("Testing stateless_hook.py...")

    class TestHook(StatelessHook):
        def process(self, ctx):
            return self.update_context(ctx, tool_result="test passed")

    # Test direct processing
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    hook = TestHook()
    result = hook.process(ctx)
    print(f"Direct process: {result.tool_result}")

    # Test JSON protocol
    input_json = json.dumps({
        "session_id": "sess_456",
        "tool_name": "Read",
        "tool_input": {"file_path": "test.py"}
    })
    output = run_hook(TestHook, input_json)
    output_data = json.loads(output)
    print(f"JSON protocol: {output_data['action']}, {output_data['context']['tool_result']}")

    print("\nAll tests passed!")
