#!/usr/bin/env python3
"""
Context Carrier for Stateless Hook Execution

Provides explicit context passing between hooks without external state.
Uses immutable dataclass to ensure context updates don't mutate originals.

Part of the popkit plugin stateless hook architecture.
"""

import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class HookContext:
    """Immutable context carrier for hook execution.

    All fields are explicit - no hidden state. Context can be
    serialized and passed between hooks or sessions.

    Attributes:
        session_id: Current session identifier
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters as dict
        message_history: List of messages for stateless composition
        tool_result: Result from tool execution (if any)
        tool_error: Error from tool execution (if any)
        created_at: ISO timestamp of context creation
        environment: Environment name (development, production)
        previous_hook: Name of previously executed hook
        hook_outputs: Dict of outputs from previous hooks in chain
    """
    session_id: str
    tool_name: str
    tool_input: Dict[str, Any]

    # Message history for stateless composition
    message_history: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

    # Tool execution state
    tool_result: Optional[str] = None
    tool_error: Optional[str] = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    environment: str = "development"

    # Chain context for multi-hook flows
    previous_hook: Optional[str] = None
    hook_outputs: Dict[str, Any] = field(default_factory=dict)


def create_context(
    session_id: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    message_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> HookContext:
    """Create a new hook context.

    Args:
        session_id: Current session identifier
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        message_history: Optional pre-existing message history
        **kwargs: Additional context fields (environment, previous_hook, etc.)

    Returns:
        New immutable HookContext

    Example:
        >>> ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
        >>> ctx.session_id
        'sess_123'
    """
    # Convert list to tuple for immutability
    history_tuple = tuple(message_history) if message_history else ()

    return HookContext(
        session_id=session_id,
        tool_name=tool_name,
        tool_input=tool_input,
        message_history=history_tuple,
        **kwargs
    )


def update_context(ctx: HookContext, **updates) -> HookContext:
    """Update context with new values (returns new context).

    The original context is never mutated. Updates are applied to
    create a new context instance.

    Special handling:
        - 'message': Appends to message_history (not replaces)
        - 'hook_output': Tuple of (name, output), merges into hook_outputs

    Args:
        ctx: Existing context
        **updates: Fields to update

    Returns:
        New context with updates applied

    Example:
        >>> ctx = create_context("sess_123", "Read", {})
        >>> updated = update_context(ctx, tool_result="file contents")
        >>> ctx.tool_result is None  # Original unchanged
        True
        >>> updated.tool_result
        'file contents'
    """
    # Handle message specially - append, don't replace
    if 'message' in updates:
        message = updates.pop('message')
        new_history = ctx.message_history + (message,)
        updates['message_history'] = new_history

    # Handle hook_outputs specially - merge, don't replace
    if 'hook_output' in updates:
        hook_name, output = updates.pop('hook_output')
        new_outputs = dict(ctx.hook_outputs)
        new_outputs[hook_name] = output
        updates['hook_outputs'] = new_outputs

    return replace(ctx, **updates)


def serialize_context(ctx: HookContext) -> str:
    """Serialize context to JSON string.

    Converts the immutable context to a JSON string that can be
    passed between hooks, stored, or sent over network.

    Args:
        ctx: Context to serialize

    Returns:
        JSON string representation

    Example:
        >>> ctx = create_context("sess_123", "Read", {})
        >>> json_str = serialize_context(ctx)
        >>> "sess_123" in json_str
        True
    """
    return json.dumps({
        'session_id': ctx.session_id,
        'tool_name': ctx.tool_name,
        'tool_input': ctx.tool_input,
        'message_history': list(ctx.message_history),  # Convert tuple to list for JSON
        'tool_result': ctx.tool_result,
        'tool_error': ctx.tool_error,
        'created_at': ctx.created_at,
        'environment': ctx.environment,
        'previous_hook': ctx.previous_hook,
        'hook_outputs': ctx.hook_outputs
    })


def deserialize_context(json_str: str) -> HookContext:
    """Deserialize context from JSON string.

    Restores a HookContext from its JSON representation.

    Args:
        json_str: JSON string to deserialize

    Returns:
        Restored HookContext

    Example:
        >>> ctx = create_context("sess_123", "Read", {})
        >>> json_str = serialize_context(ctx)
        >>> restored = deserialize_context(json_str)
        >>> restored.session_id
        'sess_123'
    """
    data = json.loads(json_str)
    return HookContext(
        session_id=data['session_id'],
        tool_name=data['tool_name'],
        tool_input=data['tool_input'],
        message_history=tuple(data.get('message_history', [])),
        tool_result=data.get('tool_result'),
        tool_error=data.get('tool_error'),
        created_at=data.get('created_at', datetime.now().isoformat()),
        environment=data.get('environment', 'development'),
        previous_hook=data.get('previous_hook'),
        hook_outputs=data.get('hook_outputs', {})
    )


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    # Quick manual test
    print("Testing context_carrier.py...")

    # Create context
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    print(f"Created: {ctx.session_id}, {ctx.tool_name}")

    # Update with message
    ctx = update_context(ctx, message={"role": "user", "content": "Hello"})
    print(f"History length: {len(ctx.message_history)}")

    # Update with tool result
    ctx = update_context(ctx, tool_result="file contents")
    print(f"Tool result: {ctx.tool_result}")

    # Serialize and deserialize
    serialized = serialize_context(ctx)
    restored = deserialize_context(serialized)
    print(f"Restored: {restored.session_id}, history={len(restored.message_history)}")

    print("\nAll tests passed!")
