"""Tests for stateless message builder utilities."""
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


def test_build_user_message_with_string():
    """User message with simple string content."""
    from message_builder import build_user_message
    result = build_user_message("Hello, Claude")
    assert result == {"role": "user", "content": "Hello, Claude"}


def test_build_user_message_with_list():
    """User message with content blocks."""
    from message_builder import build_user_message
    content = [{"type": "text", "text": "Hello"}]
    result = build_user_message(content)
    assert result == {"role": "user", "content": content}


def test_build_assistant_message():
    """Assistant message composition."""
    from message_builder import build_assistant_message
    result = build_assistant_message("I'll help you with that.")
    assert result == {"role": "assistant", "content": "I'll help you with that."}


def test_build_tool_use_message():
    """Tool use message for assistant."""
    from message_builder import build_tool_use_message
    result = build_tool_use_message(
        tool_use_id="toolu_123",
        name="Read",
        input={"file_path": "/path/to/file.py"}
    )
    expected = {
        "role": "assistant",
        "content": [{
            "type": "tool_use",
            "id": "toolu_123",
            "name": "Read",
            "input": {"file_path": "/path/to/file.py"}
        }]
    }
    assert result == expected


def test_build_tool_result_message():
    """Tool result message for user turn."""
    from message_builder import build_tool_result_message
    result = build_tool_result_message(
        tool_use_id="toolu_123",
        content="File contents here..."
    )
    expected = {
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": "toolu_123",
            "content": "File contents here..."
        }]
    }
    assert result == expected


def test_build_tool_result_with_error():
    """Tool result with error flag."""
    from message_builder import build_tool_result_message
    result = build_tool_result_message(
        tool_use_id="toolu_123",
        content="Error: File not found",
        is_error=True
    )
    assert result["content"][0]["is_error"] is True


def test_compose_conversation():
    """Compose full conversation from message list."""
    from message_builder import (
        build_user_message,
        build_tool_use_message,
        build_tool_result_message,
        compose_conversation
    )
    messages = [
        build_user_message("Read this file"),
        build_tool_use_message("toolu_1", "Read", {"file_path": "test.py"}),
        build_tool_result_message("toolu_1", "print('hello')"),
    ]
    result = compose_conversation(messages)
    assert len(result) == 3
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[2]["role"] == "user"


# =============================================================================
# Advanced Message Builder Tests
# =============================================================================

def test_merge_tool_uses():
    """Merge multiple tool uses into single assistant message."""
    from message_builder import merge_tool_uses

    tool_uses = [
        {"id": "toolu_1", "name": "Read", "input": {"file_path": "a.py"}},
        {"id": "toolu_2", "name": "Read", "input": {"file_path": "b.py"}},
    ]
    result = merge_tool_uses(tool_uses)
    assert result["role"] == "assistant"
    assert len(result["content"]) == 2
    assert result["content"][0]["type"] == "tool_use"
    assert result["content"][1]["type"] == "tool_use"


def test_merge_tool_results():
    """Merge multiple tool results into single user message."""
    from message_builder import merge_tool_results

    results = [
        {"tool_use_id": "toolu_1", "content": "Content A"},
        {"tool_use_id": "toolu_2", "content": "Content B"},
    ]
    result = merge_tool_results(results)
    assert result["role"] == "user"
    assert len(result["content"]) == 2


def test_extract_tool_use_from_message():
    """Extract tool use info from assistant message."""
    from message_builder import build_tool_use_message, extract_tool_use

    msg = build_tool_use_message("toolu_1", "Read", {"file_path": "test.py"})
    tool_uses = extract_tool_use(msg)
    assert len(tool_uses) == 1
    assert tool_uses[0]["name"] == "Read"


def test_extract_tool_use_from_string_content():
    """Extract returns empty list for string content."""
    from message_builder import extract_tool_use

    msg = {"role": "assistant", "content": "Just text, no tools"}
    tool_uses = extract_tool_use(msg)
    assert tool_uses == []


def test_extract_tool_use_from_user_message():
    """Extract returns empty list for user messages."""
    from message_builder import extract_tool_use

    msg = {"role": "user", "content": "user message"}
    tool_uses = extract_tool_use(msg)
    assert tool_uses == []


def test_rebuild_from_history():
    """Rebuild complete message array from history dict."""
    from message_builder import rebuild_from_history

    history = {
        "user_prompt": "Help me read a file",
        "tool_uses": [
            {"id": "toolu_1", "name": "Read", "input": {"file_path": "test.py"}}
        ],
        "tool_results": [
            {"tool_use_id": "toolu_1", "content": "File contents"}
        ]
    }
    messages = rebuild_from_history(history)
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"


def test_rebuild_from_history_empty():
    """Rebuild handles empty history."""
    from message_builder import rebuild_from_history

    messages = rebuild_from_history({})
    assert len(messages) == 0


def test_rebuild_from_history_partial():
    """Rebuild handles partial history (no tool results)."""
    from message_builder import rebuild_from_history

    history = {
        "user_prompt": "Hello",
        "tool_uses": []
    }
    messages = rebuild_from_history(history)
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
