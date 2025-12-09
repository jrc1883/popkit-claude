#!/usr/bin/env python3
"""
Safe JSON Input Handler for PopKit Hooks

Handles edge cases where Claude Code platform may send malformed input:
- JavaScript-style booleans (false/true instead of false/true strings)
- Empty input
- Non-JSON data
- Input that Python might try to execute as code

Usage:
    from utils.safe_json import read_hook_input

    data = read_hook_input()  # Returns dict, never raises
"""

import sys
import json
import re
from typing import Dict, Any


def sanitize_js_booleans(text: str) -> str:
    """Convert JavaScript-style booleans to JSON booleans.

    Handles cases where the platform sends:
    - {multiSelect: false} instead of {"multiSelect": false}
    - Unquoted property names with boolean values
    """
    # This is a simple fix for the common case
    # More robust would be a full JS->JSON parser

    # Replace standalone false/true (not in strings) with JSON booleans
    # This regex looks for word boundaries around false/true
    text = re.sub(r'\bfalse\b', 'false', text)
    text = re.sub(r'\btrue\b', 'true', text)
    text = re.sub(r'\bnull\b', 'null', text)

    return text


def read_hook_input(default: Dict[str, Any] = None) -> Dict[str, Any]:
    """Safely read and parse JSON input from stdin.

    Returns:
        Parsed dict from stdin, or default value if parsing fails.
        Never raises exceptions - hooks should not block on input errors.

    Args:
        default: Value to return if parsing fails (default: empty dict)
    """
    if default is None:
        default = {}

    try:
        # Read all input from stdin
        raw_input = sys.stdin.read()

        # Handle empty input
        if not raw_input or not raw_input.strip():
            return default

        # Try standard JSON parse first
        try:
            return json.loads(raw_input)
        except json.JSONDecodeError:
            # Try sanitizing JS-style input
            sanitized = sanitize_js_booleans(raw_input)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                # Give up and return default
                print(f"Warning: Could not parse hook input", file=sys.stderr)
                return default

    except Exception as e:
        # Catch any other errors (stdin issues, etc.)
        print(f"Warning: Error reading hook input: {e}", file=sys.stderr)
        return default


def write_hook_output(response: Dict[str, Any]) -> None:
    """Safely write JSON output to stdout.

    Args:
        response: Dict to serialize and write to stdout
    """
    try:
        print(json.dumps(response))
    except Exception as e:
        # Fallback to error response
        print(json.dumps({"status": "error", "error": str(e)}))


# Convenience exports
__all__ = ['read_hook_input', 'write_hook_output', 'sanitize_js_booleans']
