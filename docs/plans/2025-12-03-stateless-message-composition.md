# Stateless Message Composition Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** Refactor hooks to use stateless message composition with explicit utilities, enabling better error recovery, debugging, and testability.

**Architecture:** Create a `message_builder.py` utility module with pure functions for composing Claude API message arrays. Add a `context_carrier.py` module for explicit context passing between hooks. Update key hooks to use these utilities instead of relying on SQLite state or environment variables. The pattern is: hooks receive explicit input, compose messages using utilities, and return complete output including any context for downstream hooks.

**Tech Stack:** Python 3.x, JSON protocol, existing hook infrastructure

**Estimated Tasks:** 8 tasks

---

## Task 1: Create Message Builder Utility Module

**Files:**
- Create: `hooks/utils/message_builder.py`
- Test: `tests/hooks/test_message_builder.py`

**Step 1: Write the failing test**

```python
# tests/hooks/test_message_builder.py
"""Tests for stateless message builder utilities."""
import pytest
import sys
sys.path.insert(0, 'hooks/utils')

from message_builder import (
    build_user_message,
    build_assistant_message,
    build_tool_use_message,
    build_tool_result_message,
    compose_conversation
)


def test_build_user_message_with_string():
    """User message with simple string content."""
    result = build_user_message("Hello, Claude")
    assert result == {"role": "user", "content": "Hello, Claude"}


def test_build_user_message_with_list():
    """User message with content blocks."""
    content = [{"type": "text", "text": "Hello"}]
    result = build_user_message(content)
    assert result == {"role": "user", "content": content}


def test_build_assistant_message():
    """Assistant message composition."""
    result = build_assistant_message("I'll help you with that.")
    assert result == {"role": "assistant", "content": "I'll help you with that."}


def test_build_tool_use_message():
    """Tool use message for assistant."""
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
    result = build_tool_result_message(
        tool_use_id="toolu_123",
        content="Error: File not found",
        is_error=True
    )
    assert result["content"][0]["is_error"] is True


def test_compose_conversation():
    """Compose full conversation from message list."""
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hooks/test_message_builder.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'message_builder'"

**Step 3: Write minimal implementation**

```python
# hooks/utils/message_builder.py
#!/usr/bin/env python3
"""
Stateless Message Builder Utilities
Pure functions for composing Claude API message arrays.

Part of the popkit plugin system.
Implements stateless message composition per Claude API best practices.
"""

from typing import Any, Dict, List, Union

# Type aliases
Content = Union[str, List[Dict[str, Any]]]
Message = Dict[str, Any]
Conversation = List[Message]


def build_user_message(content: Content) -> Message:
    """Build a user role message.

    Args:
        content: String or list of content blocks

    Returns:
        Message dict with role="user"
    """
    return {"role": "user", "content": content}


def build_assistant_message(content: Content) -> Message:
    """Build an assistant role message.

    Args:
        content: String or list of content blocks

    Returns:
        Message dict with role="assistant"
    """
    return {"role": "assistant", "content": content}


def build_tool_use_message(
    tool_use_id: str,
    name: str,
    input: Dict[str, Any]
) -> Message:
    """Build an assistant message with tool use.

    Args:
        tool_use_id: Unique ID for this tool use
        name: Tool name (e.g., "Read", "Write", "Bash")
        input: Tool input parameters

    Returns:
        Message dict with tool_use content block
    """
    return {
        "role": "assistant",
        "content": [{
            "type": "tool_use",
            "id": tool_use_id,
            "name": name,
            "input": input
        }]
    }


def build_tool_result_message(
    tool_use_id: str,
    content: str,
    is_error: bool = False
) -> Message:
    """Build a user message with tool result.

    Args:
        tool_use_id: ID matching the tool_use this responds to
        content: Result content (string)
        is_error: Whether this result indicates an error

    Returns:
        Message dict with tool_result content block
    """
    result_block = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }
    if is_error:
        result_block["is_error"] = True

    return {"role": "user", "content": [result_block]}


def compose_conversation(messages: List[Message]) -> Conversation:
    """Compose a conversation from a list of messages.

    Validates message structure and returns a clean conversation array.

    Args:
        messages: List of message dicts

    Returns:
        Validated conversation array ready for Claude API
    """
    conversation = []
    for msg in messages:
        if not isinstance(msg, dict):
            raise ValueError(f"Message must be dict, got {type(msg)}")
        if "role" not in msg or "content" not in msg:
            raise ValueError("Message must have 'role' and 'content' keys")
        conversation.append(msg)
    return conversation
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hooks/test_message_builder.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add hooks/utils/message_builder.py tests/hooks/test_message_builder.py
git commit -m "feat(hooks): add stateless message builder utilities

Implements pure functions for composing Claude API message arrays:
- build_user_message: User role messages
- build_assistant_message: Assistant role messages
- build_tool_use_message: Tool use content blocks
- build_tool_result_message: Tool result content blocks
- compose_conversation: Validate and compose full conversation

Part of #22 Stateless Message Composition"
```

---

## Task 2: Add Advanced Message Builder Functions

**Files:**
- Modify: `hooks/utils/message_builder.py:80-150`
- Modify: `tests/hooks/test_message_builder.py`

**Step 1: Write the failing tests**

```python
# Add to tests/hooks/test_message_builder.py

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
    from message_builder import extract_tool_use

    msg = build_tool_use_message("toolu_1", "Read", {"file_path": "test.py"})
    tool_uses = extract_tool_use(msg)
    assert len(tool_uses) == 1
    assert tool_uses[0]["name"] == "Read"


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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hooks/test_message_builder.py::test_merge_tool_uses -v`
Expected: FAIL with "cannot import name 'merge_tool_uses'"

**Step 3: Write implementation**

```python
# Add to hooks/utils/message_builder.py after compose_conversation

def merge_tool_uses(tool_uses: List[Dict[str, Any]]) -> Message:
    """Merge multiple tool uses into a single assistant message.

    Args:
        tool_uses: List of tool use dicts with id, name, input

    Returns:
        Single assistant message with all tool_use blocks
    """
    content = []
    for tool in tool_uses:
        content.append({
            "type": "tool_use",
            "id": tool["id"],
            "name": tool["name"],
            "input": tool.get("input", {})
        })
    return {"role": "assistant", "content": content}


def merge_tool_results(results: List[Dict[str, Any]]) -> Message:
    """Merge multiple tool results into a single user message.

    Args:
        results: List of result dicts with tool_use_id, content

    Returns:
        Single user message with all tool_result blocks
    """
    content = []
    for result in results:
        block = {
            "type": "tool_result",
            "tool_use_id": result["tool_use_id"],
            "content": result.get("content", "")
        }
        if result.get("is_error"):
            block["is_error"] = True
        content.append(block)
    return {"role": "user", "content": content}


def extract_tool_use(message: Message) -> List[Dict[str, Any]]:
    """Extract tool use information from an assistant message.

    Args:
        message: Assistant message potentially containing tool_use blocks

    Returns:
        List of tool use dicts (id, name, input)
    """
    if message.get("role") != "assistant":
        return []

    content = message.get("content", [])
    if isinstance(content, str):
        return []

    tool_uses = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            tool_uses.append({
                "id": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input", {})
            })
    return tool_uses


def rebuild_from_history(history: Dict[str, Any]) -> Conversation:
    """Rebuild complete message array from a history dict.

    This enables stateless operation - given a history dict,
    we can reconstruct the exact message array for retry/debugging.

    Args:
        history: Dict with user_prompt, tool_uses, tool_results

    Returns:
        Complete conversation array
    """
    messages = []

    # User's original prompt
    if "user_prompt" in history:
        messages.append(build_user_message(history["user_prompt"]))

    # Tool uses (assistant turn)
    if "tool_uses" in history and history["tool_uses"]:
        messages.append(merge_tool_uses(history["tool_uses"]))

    # Tool results (user turn)
    if "tool_results" in history and history["tool_results"]:
        messages.append(merge_tool_results(history["tool_results"]))

    return messages
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hooks/test_message_builder.py -v`
Expected: PASS (11 tests)

**Step 5: Commit**

```bash
git add hooks/utils/message_builder.py tests/hooks/test_message_builder.py
git commit -m "feat(hooks): add advanced message builder functions

- merge_tool_uses: Combine multiple tool uses into one message
- merge_tool_results: Combine multiple results into one message
- extract_tool_use: Parse tool uses from assistant message
- rebuild_from_history: Reconstruct messages from history dict

Enables stateless retry and debugging. Part of #22"
```

---

## Task 3: Create Context Carrier Module

**Files:**
- Create: `hooks/utils/context_carrier.py`
- Test: `tests/hooks/test_context_carrier.py`

**Step 1: Write the failing test**

```python
# tests/hooks/test_context_carrier.py
"""Tests for explicit context passing between hooks."""
import pytest
import sys
sys.path.insert(0, 'hooks/utils')

from context_carrier import (
    HookContext,
    create_context,
    update_context,
    serialize_context,
    deserialize_context
)


def test_create_context():
    """Create a new hook context."""
    ctx = create_context(
        session_id="sess_123",
        tool_name="Read",
        tool_input={"file_path": "test.py"}
    )
    assert ctx.session_id == "sess_123"
    assert ctx.tool_name == "Read"
    assert ctx.tool_input == {"file_path": "test.py"}
    assert ctx.message_history == []


def test_update_context_with_message():
    """Update context with new message."""
    ctx = create_context("sess_123", "Read", {})
    updated = update_context(ctx, message={
        "role": "user",
        "content": "Read this file"
    })
    assert len(updated.message_history) == 1
    assert updated.message_history[0]["role"] == "user"


def test_serialize_deserialize_context():
    """Context round-trips through JSON."""
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    ctx = update_context(ctx, message={"role": "user", "content": "test"})

    serialized = serialize_context(ctx)
    assert isinstance(serialized, str)

    restored = deserialize_context(serialized)
    assert restored.session_id == ctx.session_id
    assert len(restored.message_history) == 1


def test_context_immutability():
    """Updates return new context, don't mutate original."""
    original = create_context("sess_123", "Read", {})
    updated = update_context(original, tool_result="file contents")

    assert original.tool_result is None
    assert updated.tool_result == "file contents"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hooks/test_context_carrier.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# hooks/utils/context_carrier.py
#!/usr/bin/env python3
"""
Context Carrier for Stateless Hook Execution
Provides explicit context passing between hooks without external state.

Part of the popkit plugin system.
"""

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass(frozen=True)
class HookContext:
    """Immutable context carrier for hook execution.

    All fields are explicit - no hidden state. Context can be
    serialized and passed between hooks or sessions.
    """
    session_id: str
    tool_name: str
    tool_input: Dict[str, Any]

    # Message history for stateless composition
    message_history: List[Dict[str, Any]] = field(default_factory=list)

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
    **kwargs
) -> HookContext:
    """Create a new hook context.

    Args:
        session_id: Current session identifier
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        **kwargs: Additional context fields

    Returns:
        New immutable HookContext
    """
    return HookContext(
        session_id=session_id,
        tool_name=tool_name,
        tool_input=tool_input,
        **kwargs
    )


def update_context(ctx: HookContext, **updates) -> HookContext:
    """Update context with new values (returns new context).

    Args:
        ctx: Existing context
        **updates: Fields to update

    Returns:
        New context with updates applied
    """
    # Handle message_history specially - append, don't replace
    if 'message' in updates:
        new_history = list(ctx.message_history) + [updates.pop('message')]
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

    Args:
        ctx: Context to serialize

    Returns:
        JSON string representation
    """
    return json.dumps({
        'session_id': ctx.session_id,
        'tool_name': ctx.tool_name,
        'tool_input': ctx.tool_input,
        'message_history': ctx.message_history,
        'tool_result': ctx.tool_result,
        'tool_error': ctx.tool_error,
        'created_at': ctx.created_at,
        'environment': ctx.environment,
        'previous_hook': ctx.previous_hook,
        'hook_outputs': ctx.hook_outputs
    })


def deserialize_context(json_str: str) -> HookContext:
    """Deserialize context from JSON string.

    Args:
        json_str: JSON string to deserialize

    Returns:
        Restored HookContext
    """
    data = json.loads(json_str)
    return HookContext(
        session_id=data['session_id'],
        tool_name=data['tool_name'],
        tool_input=data['tool_input'],
        message_history=data.get('message_history', []),
        tool_result=data.get('tool_result'),
        tool_error=data.get('tool_error'),
        created_at=data.get('created_at', datetime.now().isoformat()),
        environment=data.get('environment', 'development'),
        previous_hook=data.get('previous_hook'),
        hook_outputs=data.get('hook_outputs', {})
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hooks/test_context_carrier.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add hooks/utils/context_carrier.py tests/hooks/test_context_carrier.py
git commit -m "feat(hooks): add context carrier for explicit state passing

Implements immutable HookContext dataclass for stateless hook execution:
- create_context: Initialize new context
- update_context: Immutable updates (returns new context)
- serialize/deserialize_context: JSON round-tripping

Enables context to be passed explicitly between hooks. Part of #22"
```

---

## Task 4: Create Hook Base Class with Stateless Pattern

**Files:**
- Create: `hooks/utils/stateless_hook.py`
- Test: `tests/hooks/test_stateless_hook.py`

**Step 1: Write the failing test**

```python
# tests/hooks/test_stateless_hook.py
"""Tests for stateless hook base class."""
import pytest
import json
import sys
sys.path.insert(0, 'hooks/utils')

from stateless_hook import StatelessHook, run_hook
from context_carrier import create_context


class TestHook(StatelessHook):
    """Test implementation of stateless hook."""

    def process(self, ctx):
        # Simple processing that modifies context
        return self.update_context(ctx, tool_result="processed")


def test_stateless_hook_process():
    """Hook processes context and returns new context."""
    hook = TestHook()
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})

    result_ctx = hook.process(ctx)

    assert result_ctx.tool_result == "processed"
    assert ctx.tool_result is None  # Original unchanged


def test_hook_builds_messages():
    """Hook can build messages using utilities."""
    hook = TestHook()

    msg = hook.build_user_message("Hello")
    assert msg["role"] == "user"

    msg = hook.build_tool_use("toolu_1", "Read", {})
    assert msg["content"][0]["type"] == "tool_use"


def test_run_hook_from_json():
    """Run hook with JSON input/output."""
    input_json = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "test.py"},
        "session_id": "sess_123"
    })

    output = run_hook(TestHook, input_json)
    output_data = json.loads(output)

    assert output_data["action"] == "continue"
    assert output_data["context"]["tool_result"] == "processed"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hooks/test_stateless_hook.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# hooks/utils/stateless_hook.py
#!/usr/bin/env python3
"""
Stateless Hook Base Class
Provides a foundation for building hooks that follow stateless message composition.

Part of the popkit plugin system.
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
    """

    def __init__(self):
        """Initialize hook - no external state."""
        pass

    @abstractmethod
    def process(self, ctx: HookContext) -> HookContext:
        """Process the hook with given context.

        Args:
            ctx: Immutable hook context

        Returns:
            New context with updates (original unchanged)
        """
        pass

    # Context helpers
    def create_context(self, **kwargs) -> HookContext:
        return create_context(**kwargs)

    def update_context(self, ctx: HookContext, **updates) -> HookContext:
        return update_context(ctx, **updates)

    # Message builder helpers
    def build_user_message(self, content):
        return build_user_message(content)

    def build_assistant_message(self, content):
        return build_assistant_message(content)

    def build_tool_use(self, tool_use_id, name, input):
        return build_tool_use_message(tool_use_id, name, input)

    def build_tool_result(self, tool_use_id, content, is_error=False):
        return build_tool_result_message(tool_use_id, content, is_error)

    def compose_messages(self, messages):
        return compose_conversation(messages)

    def rebuild_messages(self, history):
        return rebuild_from_history(history)

    def run(self, input_json: str) -> str:
        """Run the hook with JSON input.

        Args:
            input_json: JSON string with tool_name, tool_input, etc.

        Returns:
            JSON string with action, context, and any output
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

    Args:
        hook_class: StatelessHook subclass to instantiate
        input_json: JSON input string

    Returns:
        JSON output string
    """
    hook = hook_class()
    return hook.run(input_json)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hooks/test_stateless_hook.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add hooks/utils/stateless_hook.py tests/hooks/test_stateless_hook.py
git commit -m "feat(hooks): add stateless hook base class

Provides StatelessHook ABC for building hooks that:
- Receive explicit context (no hidden state)
- Use message builder utilities for composition
- Return complete output with updated context

run_hook() function handles JSON protocol. Part of #22"
```

---

## Task 5: Refactor Pre-Tool-Use Hook to Stateless Pattern

**Files:**
- Modify: `hooks/pre-tool-use.py`
- Create: `hooks/pre_tool_use_stateless.py` (new implementation)

**Step 1: Create new stateless version**

```python
# hooks/pre_tool_use_stateless.py
#!/usr/bin/env python3
"""
Stateless Pre-Tool-Use Hook
Safety checks and coordination using explicit context passing.

This is the stateless refactor of pre-tool-use.py following #22.
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Tuple

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from stateless_hook import StatelessHook
from context_carrier import HookContext


class PreToolUseStateless(StatelessHook):
    """Stateless pre-tool-use hook implementation."""

    # Safety rules as class constants (no external state)
    BLOCKED_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"sudo\s+rm\s+-rf",
        r"DROP\s+DATABASE",
        r"TRUNCATE\s+TABLE",
    ]

    SENSITIVE_PATHS = [
        r"\.env",
        r"\.ssh\/",
        r"\.aws\/credentials",
    ]

    def process(self, ctx: HookContext) -> HookContext:
        """Process pre-tool-use safety checks.

        Args:
            ctx: Hook context with tool_name, tool_input

        Returns:
            Updated context with safety_check results
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

        # Update context with results (immutable - returns new context)
        return self.update_context(
            ctx,
            hook_output=("pre_tool_use", {
                "action": "block" if violations else "continue",
                "safety_check": safety_check,
                "recommendations": recommendations
            })
        )

    def _check_safety_violations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> List[str]:
        """Check for safety violations (pure function)."""
        violations = []

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            for pattern in self.BLOCKED_COMMANDS:
                if re.search(pattern, command, re.IGNORECASE):
                    violations.append(f"Blocked command pattern: {pattern}")

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
        """Get recommendations for the tool use (pure function)."""
        recommendations = []

        if tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            if file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                recommendations.append(
                    "Consider running code-reviewer after file modifications"
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
```

**Step 2: Add integration test**

```python
# tests/hooks/test_pre_tool_use_stateless.py
import json
import sys
sys.path.insert(0, 'hooks')

from pre_tool_use_stateless import PreToolUseStateless
from hooks.utils.context_carrier import create_context


def test_safe_command_passes():
    """Safe commands pass safety check."""
    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "ls -la"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "continue"
    assert output["safety_check"]["passed"] is True


def test_dangerous_command_blocked():
    """Dangerous commands are blocked."""
    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Bash", {"command": "rm -rf /"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"
    assert output["safety_check"]["passed"] is False
    assert len(output["safety_check"]["violations"]) > 0


def test_sensitive_path_blocked():
    """Sensitive path access is blocked."""
    hook = PreToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "/home/user/.env"})

    result = hook.process(ctx)
    output = result.hook_outputs["pre_tool_use"]

    assert output["action"] == "block"
```

**Step 3: Run tests**

Run: `python -m pytest tests/hooks/test_pre_tool_use_stateless.py -v`
Expected: PASS (3 tests)

**Step 4: Commit**

```bash
git add hooks/pre_tool_use_stateless.py tests/hooks/test_pre_tool_use_stateless.py
git commit -m "feat(hooks): add stateless pre-tool-use implementation

Refactors pre-tool-use hook to follow stateless pattern:
- Pure functions for safety checks
- No SQLite or environment variable dependencies
- Context passed explicitly, updated immutably

Original pre-tool-use.py preserved for compatibility. Part of #22"
```

---

## Task 6: Refactor Post-Tool-Use Hook to Stateless Pattern

**Files:**
- Create: `hooks/post_tool_use_stateless.py`
- Test: `tests/hooks/test_post_tool_use_stateless.py`

**Step 1: Create new stateless version**

```python
# hooks/post_tool_use_stateless.py
#!/usr/bin/env python3
"""
Stateless Post-Tool-Use Hook
Result processing and coordination using explicit context passing.

This is the stateless refactor of post-tool-use.py following #22.
"""

import os
import sys
import json
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from stateless_hook import StatelessHook
from context_carrier import HookContext


class PostToolUseStateless(StatelessHook):
    """Stateless post-tool-use hook implementation."""

    # Followup rules as class constants
    FOLLOWUP_RULES = {
        "Write": ["suggest_code_review", "check_for_tests"],
        "Edit": ["suggest_code_review", "run_linter"],
        "Bash": ["validate_output", "check_side_effects"],
    }

    def process(self, ctx: HookContext) -> HookContext:
        """Process post-tool-use actions.

        Args:
            ctx: Hook context with tool result

        Returns:
            Updated context with followup suggestions
        """
        tool_name = ctx.tool_name
        tool_result = ctx.tool_result

        # Get followup suggestions
        followups = self._get_followups(tool_name, tool_result)

        # Detect truncation
        truncation_warning = self._check_truncation(tool_result)

        # Build message for context
        if tool_result:
            message = self.build_tool_result(
                tool_use_id=f"toolu_{ctx.session_id}",
                content=tool_result
            )
            ctx = self.update_context(ctx, message=message)

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
        tool_result: str
    ) -> List[str]:
        """Get followup suggestions (pure function)."""
        return self.FOLLOWUP_RULES.get(tool_name, [])

    def _check_truncation(self, result: str) -> str:
        """Check for result truncation (pure function)."""
        if result and len(result) > 50000:
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
```

**Step 2: Add test**

```python
# tests/hooks/test_post_tool_use_stateless.py
import sys
sys.path.insert(0, 'hooks')

from post_tool_use_stateless import PostToolUseStateless
from hooks.utils.context_carrier import create_context


def test_write_suggests_code_review():
    """Write tool suggests code review."""
    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Write", {"file_path": "test.py"})
    ctx = ctx._replace(tool_result="File written successfully")

    result = hook.process(ctx)
    output = result.hook_outputs["post_tool_use"]

    assert "suggest_code_review" in output["followups"]


def test_message_history_updated():
    """Tool result added to message history."""
    hook = PostToolUseStateless()
    ctx = create_context("sess_1", "Read", {"file_path": "test.py"})
    ctx = ctx._replace(tool_result="file contents")

    result = hook.process(ctx)

    assert len(result.message_history) == 1
    assert result.message_history[0]["role"] == "user"
```

**Step 3: Run tests and commit**

Run: `python -m pytest tests/hooks/test_post_tool_use_stateless.py -v`

```bash
git add hooks/post_tool_use_stateless.py tests/hooks/test_post_tool_use_stateless.py
git commit -m "feat(hooks): add stateless post-tool-use implementation

Refactors post-tool-use hook to follow stateless pattern:
- Pure functions for followup suggestions
- Automatic message history composition
- Truncation detection

Part of #22 Stateless Message Composition"
```

---

## Task 7: Add Integration Tests

**Files:**
- Create: `tests/hooks/test_stateless_integration.py`

**Step 1: Write integration tests**

```python
# tests/hooks/test_stateless_integration.py
"""Integration tests for stateless hook chain."""
import json
import sys
sys.path.insert(0, 'hooks')
sys.path.insert(0, 'hooks/utils')

from context_carrier import create_context, serialize_context, deserialize_context
from pre_tool_use_stateless import PreToolUseStateless
from post_tool_use_stateless import PostToolUseStateless
from message_builder import rebuild_from_history


def test_hook_chain_passes_context():
    """Context flows correctly through hook chain."""
    # Simulate: pre-tool-use -> tool execution -> post-tool-use

    # 1. Pre-tool-use
    pre_hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Read", {"file_path": "test.py"})
    ctx = pre_hook.process(ctx)

    # Context should have pre_tool_use output
    assert "pre_tool_use" in ctx.hook_outputs
    assert ctx.hook_outputs["pre_tool_use"]["action"] == "continue"

    # 2. Simulate tool execution
    ctx = ctx._replace(tool_result="print('hello world')")

    # 3. Post-tool-use
    post_hook = PostToolUseStateless()
    ctx = post_hook.process(ctx)

    # Context should have both hook outputs
    assert "pre_tool_use" in ctx.hook_outputs
    assert "post_tool_use" in ctx.hook_outputs

    # Message history should have the tool result
    assert len(ctx.message_history) == 1


def test_context_survives_serialization():
    """Context can be serialized and restored between hooks."""
    hook = PreToolUseStateless()
    ctx = create_context("sess_123", "Bash", {"command": "ls -la"})
    ctx = hook.process(ctx)

    # Serialize (as would happen between hook calls)
    serialized = serialize_context(ctx)

    # Deserialize (as would happen in next hook)
    restored = deserialize_context(serialized)

    assert restored.session_id == "sess_123"
    assert restored.tool_name == "Bash"
    assert "pre_tool_use" in restored.hook_outputs


def test_message_rebuild_from_history():
    """Messages can be rebuilt for retry/debugging."""
    # Simulate a conversation
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
```

**Step 2: Run and commit**

Run: `python -m pytest tests/hooks/test_stateless_integration.py -v`

```bash
git add tests/hooks/test_stateless_integration.py
git commit -m "test(hooks): add integration tests for stateless hook chain

Verifies:
- Context flows correctly through pre -> post hook chain
- Context survives JSON serialization/deserialization
- Messages can be rebuilt from history for retry

Part of #22"
```

---

## Task 8: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `hooks/README.md` (create if needed)

**Step 1: Update CLAUDE.md**

Add section under "Key Architectural Patterns":

```markdown
### Stateless Message Composition

Hooks follow a stateless pattern for reliability and testability:

**Message Builder** (`hooks/utils/message_builder.py`):
- Pure functions for composing Claude API messages
- `build_user_message()`, `build_tool_use_message()`, etc.
- `rebuild_from_history()` for retry/debugging

**Context Carrier** (`hooks/utils/context_carrier.py`):
- Immutable `HookContext` dataclass
- Explicit state passing between hooks
- JSON serialization for persistence

**Stateless Hook Base** (`hooks/utils/stateless_hook.py`):
- `StatelessHook` ABC for building hooks
- No hidden state or external dependencies
- Full context in, full context out

Example:
```python
class MyHook(StatelessHook):
    def process(self, ctx: HookContext) -> HookContext:
        result = self.build_tool_result(ctx.tool_use_id, "done")
        return self.update_context(ctx, message=result)
```
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add stateless message composition documentation

Documents the new hook architecture:
- Message builder utilities
- Context carrier pattern
- StatelessHook base class

Closes #22"
```

---

## Verification

After all tasks complete:

```bash
# Run full test suite
python -m pytest tests/hooks/ -v

# Verify imports work
python -c "from hooks.utils.message_builder import build_user_message; print('OK')"
python -c "from hooks.utils.context_carrier import HookContext; print('OK')"
python -c "from hooks.utils.stateless_hook import StatelessHook; print('OK')"
```

## Rollback Plan

If issues arise:
1. Stateless versions are NEW files - original hooks preserved
2. `git log` to find last good commit
3. `git revert HEAD~N` to undo commits
4. Or delete new files and restore originals

---

**Plan Confidence:** 85%

This plan provides a clear path to stateless message composition while:
- Preserving existing hook functionality
- Adding new capabilities incrementally
- Maintaining full test coverage
- Keeping rollback simple
