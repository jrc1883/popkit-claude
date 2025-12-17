"""Tests for explicit context passing between hooks."""
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


def test_create_context():
    """Create a new hook context."""
    from context_carrier import create_context

    ctx = create_context(
        session_id="sess_123",
        tool_name="Read",
        tool_input={"file_path": "test.py"}
    )
    assert ctx.session_id == "sess_123"
    assert ctx.tool_name == "Read"
    assert ctx.tool_input == {"file_path": "test.py"}
    assert len(ctx.message_history) == 0  # Empty tuple for immutability


def test_create_context_with_history():
    """Create context with pre-existing message history."""
    from context_carrier import create_context

    history = [{"role": "user", "content": "Hello"}]
    ctx = create_context(
        session_id="sess_123",
        tool_name="Read",
        tool_input={},
        message_history=history
    )
    assert len(ctx.message_history) == 1


def test_update_context_with_message():
    """Update context with new message."""
    from context_carrier import create_context, update_context

    ctx = create_context("sess_123", "Read", {})
    updated = update_context(ctx, message={
        "role": "user",
        "content": "Read this file"
    })
    assert len(updated.message_history) == 1
    assert updated.message_history[0]["role"] == "user"


def test_update_context_appends_messages():
    """Multiple messages append to history."""
    from context_carrier import create_context, update_context

    ctx = create_context("sess_123", "Read", {})
    ctx = update_context(ctx, message={"role": "user", "content": "First"})
    ctx = update_context(ctx, message={"role": "assistant", "content": "Second"})

    assert len(ctx.message_history) == 2
    assert ctx.message_history[0]["content"] == "First"
    assert ctx.message_history[1]["content"] == "Second"


def test_update_context_with_tool_result():
    """Update context with tool result."""
    from context_carrier import create_context, update_context

    ctx = create_context("sess_123", "Read", {})
    updated = update_context(ctx, tool_result="file contents here")

    assert updated.tool_result == "file contents here"


def test_update_context_with_hook_output():
    """Update context with hook output."""
    from context_carrier import create_context, update_context

    ctx = create_context("sess_123", "Read", {})
    updated = update_context(ctx, hook_output=("pre_tool_use", {"action": "continue"}))

    assert "pre_tool_use" in updated.hook_outputs
    assert updated.hook_outputs["pre_tool_use"]["action"] == "continue"


def test_serialize_deserialize_context():
    """Context round-trips through JSON."""
    from context_carrier import (
        create_context,
        update_context,
        serialize_context,
        deserialize_context
    )

    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    ctx = update_context(ctx, message={"role": "user", "content": "test"})

    serialized = serialize_context(ctx)
    assert isinstance(serialized, str)

    restored = deserialize_context(serialized)
    assert restored.session_id == ctx.session_id
    assert len(restored.message_history) == 1


def test_context_immutability():
    """Updates return new context, don't mutate original."""
    from context_carrier import create_context, update_context

    original = create_context("sess_123", "Read", {})
    updated = update_context(original, tool_result="file contents")

    assert original.tool_result is None
    assert updated.tool_result == "file contents"


def test_context_preserves_all_fields():
    """Serialization preserves all fields."""
    from context_carrier import (
        create_context,
        update_context,
        serialize_context,
        deserialize_context
    )

    ctx = create_context(
        session_id="sess_123",
        tool_name="Read",
        tool_input={"file_path": "test.py"},
        environment="production"
    )
    ctx = update_context(ctx, tool_result="contents")
    ctx = update_context(ctx, tool_error="Warning: large file")
    ctx = update_context(ctx, previous_hook="safety_check")

    serialized = serialize_context(ctx)
    restored = deserialize_context(serialized)

    assert restored.session_id == "sess_123"
    assert restored.tool_name == "Read"
    assert restored.tool_result == "contents"
    assert restored.tool_error == "Warning: large file"
    assert restored.previous_hook == "safety_check"
    assert restored.environment == "production"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
