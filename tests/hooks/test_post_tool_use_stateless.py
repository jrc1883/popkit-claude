"""Tests for stateless post-tool-use hook."""
import pytest
import sys
import os
from dataclasses import replace

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks'))

from context_carrier import create_context


def test_write_suggests_code_review():
    """Write tool suggests code review."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Write", {"file_path": "test.py"})
    ctx = replace(ctx, tool_result="File written successfully")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert "suggest_code_review" in output["followups"]


def test_edit_suggests_linter():
    """Edit tool suggests running linter."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Edit", {"file_path": "app.tsx"})
    ctx = replace(ctx, tool_result="File edited successfully")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert "run_linter" in output["followups"]


def test_bash_suggests_validation():
    """Bash tool suggests validating output."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "npm install"})
    ctx = replace(ctx, tool_result="Packages installed")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert "validate_output" in output["followups"]


def test_message_history_updated():
    """Tool result added to message history."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "test.py"})
    ctx = replace(ctx, tool_result="file contents here")

    result = hook.process(ctx)

    assert len(result.message_history) == 1
    assert result.message_history[0]["role"] == "user"


def test_truncation_warning_for_large_results():
    """Large results trigger truncation warning."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "huge.log"})
    # Create a result larger than 50000 chars
    ctx = replace(ctx, tool_result="x" * 60000)

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert "truncat" in output["truncation_warning"].lower()


def test_no_truncation_warning_for_small_results():
    """Small results have no truncation warning."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "small.txt"})
    ctx = replace(ctx, tool_result="Small content")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert output["truncation_warning"] == ""


def test_context_preserved_through_hook():
    """Original context fields preserved after hook."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    ctx = replace(ctx, tool_result="contents")

    result = hook.process(ctx)

    assert result.session_id == "sess_123"
    assert result.tool_name == "Read"


def test_action_is_always_continue():
    """Post-tool-use always continues (no blocking)."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Write", {"file_path": "test.py"})
    ctx = replace(ctx, tool_result="done")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert output["action"] == "continue"


def test_no_tool_result_skips_message_history():
    """No tool result means no message added."""
    from post_tool_use_stateless import PostToolUseStateless

    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "test.py"})
    # No tool_result set

    result = hook.process(ctx)

    assert len(result.message_history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
