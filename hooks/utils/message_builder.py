#!/usr/bin/env python3
"""
Stateless Message Builder Utilities

Pure functions for composing Claude API messages without side effects.
These utilities create properly-formatted message objects for:
- User messages (simple text or content blocks)
- Assistant messages (responses, tool use)
- Tool result messages (from tool execution)

Part of the popkit plugin stateless hook architecture.
"""

from typing import Dict, List, Any, Union

# Type aliases for clarity
Content = Union[str, List[Dict[str, Any]]]
Message = Dict[str, Any]
ContentBlock = Dict[str, Any]


# =============================================================================
# Basic Message Builders
# =============================================================================

def build_user_message(content: Content) -> Message:
    """Create a user role message.

    Args:
        content: String or list of content blocks

    Returns:
        Message dict with role "user"

    Example:
        >>> build_user_message("Hello, Claude")
        {"role": "user", "content": "Hello, Claude"}

        >>> build_user_message([{"type": "text", "text": "Hello"}])
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
    """
    return {"role": "user", "content": content}


def build_assistant_message(content: Content) -> Message:
    """Create an assistant role message.

    Args:
        content: String or list of content blocks

    Returns:
        Message dict with role "assistant"

    Example:
        >>> build_assistant_message("I'll help you with that.")
        {"role": "assistant", "content": "I'll help you with that."}
    """
    return {"role": "assistant", "content": content}


# =============================================================================
# Tool Message Builders
# =============================================================================

def build_tool_use_message(tool_use_id: str, name: str, input: Dict[str, Any]) -> Message:
    """Create an assistant message containing a tool use block.

    This represents Claude deciding to use a tool. The message has role
    "assistant" with a content array containing a tool_use block.

    Args:
        tool_use_id: Unique identifier for this tool use (e.g., "toolu_123")
        name: Tool name (e.g., "Read", "Edit", "Bash")
        input: Tool input parameters as dict

    Returns:
        Message dict with assistant role and tool_use content block

    Example:
        >>> build_tool_use_message("toolu_123", "Read", {"file_path": "/test.py"})
        {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "toolu_123",
                "name": "Read",
                "input": {"file_path": "/test.py"}
            }]
        }
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
    """Create a user message containing a tool result block.

    This represents the result of tool execution. The message has role
    "user" with a content array containing a tool_result block.

    Args:
        tool_use_id: ID of the tool_use this is responding to
        content: Result content (string)
        is_error: Whether this result represents an error

    Returns:
        Message dict with user role and tool_result content block

    Example:
        >>> build_tool_result_message("toolu_123", "File contents here...")
        {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": "toolu_123",
                "content": "File contents here..."
            }]
        }

        >>> build_tool_result_message("toolu_123", "Error: Not found", is_error=True)
        {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": "toolu_123",
                "content": "Error: Not found",
                "is_error": True
            }]
        }
    """
    result_block: ContentBlock = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }

    if is_error:
        result_block["is_error"] = True

    return {"role": "user", "content": [result_block]}


# =============================================================================
# Conversation Composition
# =============================================================================

def compose_conversation(messages: List[Message]) -> List[Message]:
    """Compose a list of messages into a valid conversation.

    This function validates and returns the messages as a conversation array.
    Currently performs basic validation; can be extended for more checks.

    Args:
        messages: List of message dicts

    Returns:
        List of messages ready for API use

    Example:
        >>> msgs = [
        ...     build_user_message("Read this file"),
        ...     build_tool_use_message("toolu_1", "Read", {"file_path": "test.py"}),
        ...     build_tool_result_message("toolu_1", "print('hello')"),
        ... ]
        >>> compose_conversation(msgs)
        [
            {"role": "user", "content": "Read this file"},
            {"role": "assistant", "content": [{"type": "tool_use", ...}]},
            {"role": "user", "content": [{"type": "tool_result", ...}]}
        ]
    """
    # Return a copy to maintain immutability
    return list(messages)


# =============================================================================
# Advanced Composition Functions
# =============================================================================

def merge_tool_uses(tool_uses: List[Dict[str, Any]]) -> Message:
    """Merge multiple tool uses into a single assistant message.

    When Claude makes parallel tool calls, they should be in a single
    assistant message with multiple tool_use content blocks.

    Args:
        tool_uses: List of tool use dicts with id, name, input

    Returns:
        Single assistant message with all tool_use blocks

    Example:
        >>> merge_tool_uses([
        ...     {"id": "toolu_1", "name": "Read", "input": {"file_path": "a.py"}},
        ...     {"id": "toolu_2", "name": "Read", "input": {"file_path": "b.py"}}
        ... ])
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_1", ...},
                {"type": "tool_use", "id": "toolu_2", ...}
            ]
        }
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

    When responding to parallel tool calls, all results should be in
    a single user message with multiple tool_result content blocks.

    Args:
        results: List of result dicts with tool_use_id, content, optional is_error

    Returns:
        Single user message with all tool_result blocks

    Example:
        >>> merge_tool_results([
        ...     {"tool_use_id": "toolu_1", "content": "File A contents"},
        ...     {"tool_use_id": "toolu_2", "content": "File B contents"}
        ... ])
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "toolu_1", ...},
                {"type": "tool_result", "tool_use_id": "toolu_2", ...}
            ]
        }
    """
    content = []
    for result in results:
        block: ContentBlock = {
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
        List of tool use dicts (id, name, input), empty if none found

    Example:
        >>> msg = build_tool_use_message("toolu_1", "Read", {"file_path": "x.py"})
        >>> extract_tool_use(msg)
        [{"id": "toolu_1", "name": "Read", "input": {"file_path": "x.py"}}]
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


def rebuild_from_history(history: Dict[str, Any]) -> List[Message]:
    """Rebuild complete message array from a history dict.

    This enables stateless operation - given a history dict,
    we can reconstruct the exact message array for retry/debugging.

    Args:
        history: Dict with optional keys:
            - user_prompt: Original user message
            - tool_uses: List of tool use dicts
            - tool_results: List of tool result dicts

    Returns:
        Complete conversation array

    Example:
        >>> history = {
        ...     "user_prompt": "Read test.py",
        ...     "tool_uses": [{"id": "toolu_1", "name": "Read", "input": {...}}],
        ...     "tool_results": [{"tool_use_id": "toolu_1", "content": "..."}]
        ... }
        >>> rebuild_from_history(history)
        [user_message, tool_use_message, tool_result_message]
    """
    messages: List[Message] = []

    # User's original prompt
    if "user_prompt" in history and history["user_prompt"]:
        messages.append(build_user_message(history["user_prompt"]))

    # Tool uses (assistant turn)
    if "tool_uses" in history and history["tool_uses"]:
        messages.append(merge_tool_uses(history["tool_uses"]))

    # Tool results (user turn)
    if "tool_results" in history and history["tool_results"]:
        messages.append(merge_tool_results(history["tool_results"]))

    return messages


# =============================================================================
# Content Block Builders
# =============================================================================

def build_text_block(text: str) -> ContentBlock:
    """Create a text content block.

    Args:
        text: The text content

    Returns:
        Content block dict with type "text"

    Example:
        >>> build_text_block("Hello, world!")
        {"type": "text", "text": "Hello, world!"}
    """
    return {"type": "text", "text": text}


def build_tool_use_block(
    tool_use_id: str,
    name: str,
    input: Dict[str, Any]
) -> ContentBlock:
    """Create a tool_use content block.

    Args:
        tool_use_id: Unique identifier for this tool use
        name: Tool name
        input: Tool input parameters

    Returns:
        Content block dict with type "tool_use"
    """
    return {
        "type": "tool_use",
        "id": tool_use_id,
        "name": name,
        "input": input
    }


def build_tool_result_block(
    tool_use_id: str,
    content: str,
    is_error: bool = False
) -> ContentBlock:
    """Create a tool_result content block.

    Args:
        tool_use_id: ID of the tool_use this responds to
        content: Result content
        is_error: Whether this is an error result

    Returns:
        Content block dict with type "tool_result"
    """
    block: ContentBlock = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }

    if is_error:
        block["is_error"] = True

    return block


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    # Quick manual test
    print("Testing message_builder.py...")

    # Test basic messages
    user_msg = build_user_message("Hello")
    print(f"User message: {user_msg}")

    assistant_msg = build_assistant_message("Hi there!")
    print(f"Assistant message: {assistant_msg}")

    # Test tool messages
    tool_use = build_tool_use_message("toolu_1", "Read", {"file_path": "test.py"})
    print(f"Tool use: {tool_use}")

    tool_result = build_tool_result_message("toolu_1", "file contents")
    print(f"Tool result: {tool_result}")

    error_result = build_tool_result_message("toolu_1", "Error!", is_error=True)
    print(f"Error result: {error_result}")

    # Test composition
    conversation = compose_conversation([user_msg, tool_use, tool_result])
    print(f"Conversation ({len(conversation)} messages)")

    print("\nAll tests passed!")
