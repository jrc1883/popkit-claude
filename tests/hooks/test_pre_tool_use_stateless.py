"""Tests for stateless pre-tool-use hook."""
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks'))

from context_carrier import create_context


def test_safe_command_passes():
    """Safe commands pass safety check."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "ls -la"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "continue"
    assert output["safety_check"]["passed"] is True


def test_dangerous_rm_command_blocked():
    """Dangerous rm -rf / commands are blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "rm -rf /"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"
    assert output["safety_check"]["passed"] is False
    assert len(output["safety_check"]["violations"]) > 0


def test_sudo_rm_blocked():
    """Sudo rm -rf commands are blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "sudo rm -rf /important"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"


def test_drop_database_blocked():
    """SQL DROP DATABASE commands are blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "psql -c 'DROP DATABASE production'"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"


def test_sensitive_env_path_blocked():
    """Sensitive .env path access is blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "/home/user/.env"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"


def test_sensitive_ssh_path_blocked():
    """Sensitive .ssh path access is blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "/home/user/.ssh/id_rsa"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"


def test_sensitive_aws_credentials_blocked():
    """Sensitive AWS credentials path access is blocked."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "/home/user/.aws/credentials"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"


def test_normal_file_read_passes():
    """Normal file reads pass."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "/project/src/main.py"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "continue"


def test_write_provides_recommendations():
    """Write tool provides code review recommendation for code files."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Write", {"file_path": "/project/src/app.tsx"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "continue"
    assert len(output["recommendations"]) > 0


def test_context_preserved_through_hook():
    """Original context fields preserved after hook."""
    from pre_tool_use_stateless import PreToolUseStateless

    hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Bash", {"command": "echo hello"})

    result = hook.process(ctx)

    assert result.session_id == "sess_123"
    assert result.tool_name == "Bash"
    assert result.tool_input == {"command": "echo hello"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
