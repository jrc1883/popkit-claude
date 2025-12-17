"""Integration tests for stateless hook chain."""
import pytest
import json
import sys
import os
from dataclasses import replace

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks'))

from context_carrier import create_context, serialize_context, deserialize_context
from message_builder import rebuild_from_history


def test_hook_chain_passes_context():
    """Context flows correctly through hook chain."""
    from pre_tool_use_stateless import PreToolUseStateless
    from post_tool_use_stateless import PostToolUseStateless

    # Simulate: pre-tool-use -> tool execution -> post-tool-use

    # 1. Pre-tool-use
    pre_hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    ctx = pre_hook.process(ctx)

    # Context should have pre_tool_use output
    assert "pre_tool_use" in ctx.hook_outputs
    assert ctx.hook_outputs["pre_tool_use"]["action"] == "continue"

    # 2. Simulate tool execution
    ctx = replace(ctx, tool_result="print('hello world')")

    # 3. Post-tool-use
    post_hook = PostToolUseStateless()
    ctx = post_hook.process(ctx)

    # Context should have both hook outputs
    assert "pre_tool_use" in ctx.hook_outputs
    assert "post_tool_use" in ctx.hook_outputs

    # Message history should have the tool result
    assert len(ctx.message_history) == 1


def test_blocked_command_stops_chain():
    """Blocked commands stop the hook chain early."""
    from pre_tool_use_stateless import PreToolUseStateless

    pre_hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Bash", {"command": "rm -rf /"})
    ctx = pre_hook.process(ctx)

    # Should be blocked
    assert ctx.hook_outputs["pre_tool_use"]["action"] == "block"
    assert ctx.hook_outputs["pre_tool_use"]["safety_check"]["passed"] is False


def test_context_survives_serialization():
    """Context can be serialized and restored between hooks."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Bash", {"command": "ls -la"})
    ctx = hook.process(ctx)

    # Serialize (as would happen between hook calls)
    serialized = serialize_context(ctx)
    assert isinstance(serialized, str)
    assert "sess_123" in serialized

    # Deserialize (as would happen in next hook)
    restored = deserialize_context(serialized)

    assert restored.session_id == "sess_123"
    assert restored.tool_name == "Bash"
    assert "pre_tool_use" in restored.hook_outputs


def test_message_rebuild_from_history():
    """Messages can be rebuilt for retry/debugging."""
    # Simulate a conversation history
    history = {
        "user_prompt": "Please read test.py",
        "tool_uses": [
            {"id": "toolu_1", "name": "Read", "input": {"file_path": "test.py"}}
        ],
        "tool_results": [
            {"tool_use_id": "toolu_1", "content": "print('hello')"}
        ]
    }

    # Rebuild messages
    messages = rebuild_from_history(history)

    # Should have 3 messages: user prompt, tool use, tool result
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"

    # Can be used for retry
    assert messages[0]["content"] == "Please read test.py"
    assert messages[2]["content"][0]["content"] == "print('hello')"


def test_full_workflow_simulation():
    """Simulate a complete tool use workflow."""
    from pre_tool_use_stateless import PreToolUseStateless
    from post_tool_use_stateless import PostToolUseStateless

    # 1. User wants to write a file
    ctx = create_context(
        session_id="workflow_123",
        tool_name="Write",
        tool_input={"file_path": "/project/src/app.tsx", "content": "..."}
    )

    # 2. Pre-tool-use check
    pre_hook = PreToolUseStateless()
    ctx = pre_hook.process(ctx)

    # Should pass and provide recommendations
    assert ctx.hook_outputs["pre_tool_use"]["action"] == "continue"
    assert len(ctx.hook_outputs["pre_tool_use"]["recommendations"]) > 0

    # 3. Simulate tool execution
    ctx = replace(ctx, tool_result="File written successfully")

    # 4. Post-tool-use processing
    post_hook = PostToolUseStateless()
    ctx = post_hook.process(ctx)

    # Should suggest code review
    assert "suggest_code_review" in ctx.hook_outputs["post_tool_use"]["followups"]

    # 5. Verify context is complete
    assert ctx.session_id == "workflow_123"
    assert ctx.tool_name == "Write"
    assert ctx.tool_result == "File written successfully"
    assert len(ctx.message_history) == 1


def test_multiple_tool_cycle():
    """Multiple tools in sequence maintain context."""
    from pre_tool_use_stateless import PreToolUseStateless
    from post_tool_use_stateless import PostToolUseStateless

    pre_hook = PreToolUseStateless()
    post_hook = PostToolUseStateless()

    # First tool: Read
    ctx1 = create_context("sess_multi", "Read", {"file_path": "config.json"})
    ctx1 = pre_hook.process(ctx1)
    ctx1 = replace(ctx1, tool_result='{"key": "value"}')
    ctx1 = post_hook.process(ctx1)

    # Serialize and deserialize (simulating between-turn persistence)
    serialized1 = serialize_context(ctx1)
    restored1 = deserialize_context(serialized1)

    # Second tool: Edit (using restored context's message history)
    ctx2 = create_context(
        session_id="sess_multi",
        tool_name="Edit",
        tool_input={"file_path": "config.json"},
        message_history=list(restored1.message_history)
    )
    ctx2 = pre_hook.process(ctx2)
    ctx2 = replace(ctx2, tool_result="File edited")
    ctx2 = post_hook.process(ctx2)

    # Should have accumulated message history
    assert len(ctx2.message_history) == 2


def test_error_handling_in_chain():
    """Errors in hooks are handled gracefully."""
    from stateless_hook import run_hook, StatelessHook
    from context_carrier import HookContext

    class BrokenHook(StatelessHook):
        def process(self, ctx: HookContext) -> HookContext:
            raise RuntimeError("Simulated hook failure")

    input_json = json.dumps({
        "session_id": "error_test",
        "tool_name": "Read",
        "tool_input": {}
    })

    output = run_hook(BrokenHook, input_json)
    output_data = json.loads(output)

    assert output_data["action"] == "error"
    assert "Simulated hook failure" in output_data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
