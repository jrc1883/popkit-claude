"""Tests for stateless hook base class."""
import pytest
import json
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))

from context_carrier import create_context


def test_stateless_hook_process():
    """Hook processes context and returns new context."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        """Test implementation of stateless hook."""
        def process(self, ctx):
            return self.update_context(ctx, tool_result="processed")

    hook = TestHook()
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})

    result_ctx = hook.process(ctx)

    assert result_ctx.tool_result == "processed"
    assert ctx.tool_result is None  # Original unchanged


def test_hook_builds_user_message():
    """Hook can build user messages."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return ctx

    hook = TestHook()
    msg = hook.build_user_message("Hello")

    assert msg["role"] == "user"
    assert msg["content"] == "Hello"


def test_hook_builds_tool_use():
    """Hook can build tool use messages."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return ctx

    hook = TestHook()
    msg = hook.build_tool_use("toolu_1", "Read", {"file_path": "test.py"})

    assert msg["role"] == "assistant"
    assert msg["content"][0]["type"] == "tool_use"
    assert msg["content"][0]["name"] == "Read"


def test_hook_builds_tool_result():
    """Hook can build tool result messages."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return ctx

    hook = TestHook()
    msg = hook.build_tool_result("toolu_1", "file contents")

    assert msg["role"] == "user"
    assert msg["content"][0]["type"] == "tool_result"


def test_run_hook_from_json():
    """Run hook with JSON input/output."""
    from stateless_hook import StatelessHook, run_hook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return self.update_context(ctx, tool_result="processed")

    input_json = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "test.py"},
        "session_id": "sess_123"
    })

    output = run_hook(TestHook, input_json)
    output_data = json.loads(output)

    assert output_data["action"] == "continue"
    assert output_data["context"]["tool_result"] == "processed"


def test_run_hook_handles_errors():
    """Hook run returns error on exception."""
    from stateless_hook import StatelessHook, run_hook

    class BrokenHook(StatelessHook):
        def process(self, ctx):
            raise ValueError("Something went wrong")

    input_json = json.dumps({
        "tool_name": "Read",
        "tool_input": {},
        "session_id": "sess_123"
    })

    output = run_hook(BrokenHook, input_json)
    output_data = json.loads(output)

    assert output_data["action"] == "error"
    assert "Something went wrong" in output_data["error"]


def test_hook_compose_messages():
    """Hook can compose message arrays."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return ctx

    hook = TestHook()
    messages = [
        hook.build_user_message("Hello"),
        hook.build_tool_use("toolu_1", "Read", {}),
    ]
    composed = hook.compose_messages(messages)

    assert len(composed) == 2
    assert composed[0]["role"] == "user"
    assert composed[1]["role"] == "assistant"


def test_hook_rebuilds_from_history():
    """Hook can rebuild messages from history."""
    from stateless_hook import StatelessHook

    class TestHook(StatelessHook):
        def process(self, ctx):
            return ctx

    hook = TestHook()
    history = {
        "user_prompt": "Read file",
        "tool_uses": [{"id": "toolu_1", "name": "Read", "input": {}}],
        "tool_results": [{"tool_use_id": "toolu_1", "content": "contents"}]
    }
    messages = hook.rebuild_messages(history)

    assert len(messages) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
