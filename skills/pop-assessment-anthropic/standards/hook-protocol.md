# Hook Protocol Standard

## Overview

All Claude Code hooks MUST follow the JSON stdin/stdout protocol. This standard defines the exact requirements.

## Required Elements

### 1. Shebang Line

Every Python hook MUST start with:

```python
#!/usr/bin/env python3
```

### 2. JSON Input Parsing

Hooks MUST read JSON from stdin:

```python
import json
import sys

# REQUIRED: Parse JSON from stdin
data = json.load(sys.stdin)
```

**Acceptable Patterns:**
- `json.load(sys.stdin)`
- `json.loads(sys.stdin.read())`

**NOT Acceptable:**
- `input()`
- `sys.argv` for data (args OK for flags)
- Reading from files instead of stdin

### 3. JSON Output

Hooks MUST output JSON to stdout:

```python
# REQUIRED: Output JSON to stdout
result = {"action": "continue"}
print(json.dumps(result))
```

**Required Output Fields:**

| Field | Type | Values | Required |
|-------|------|--------|----------|
| `action` | string | "continue", "block" | Yes |
| `message` | string | User-visible message | If blocking |
| `reason` | string | Internal reason | Optional |

### 4. Error Handling

Hooks MUST NOT crash on errors. Use try/except with graceful exit:

```python
try:
    data = json.load(sys.stdin)
    # ... processing ...
    print(json.dumps({"action": "continue"}))
except Exception as e:
    # Log to stderr (not stdout!)
    print(f"Error: {e}", file=sys.stderr)
    # ALWAYS exit 0 - don't break the pipeline
    sys.exit(0)
```

**CRITICAL**: Use `sys.exit(0)` even on error. Using `sys.exit(1)` or allowing exceptions to propagate will break Claude Code's tool execution pipeline.

### 5. Stderr for User Messages

Use stderr for messages that should appear to the user but aren't part of the JSON protocol:

```python
import sys

# Messages to user
print("Processing...", file=sys.stderr)

# JSON response to stdout
print(json.dumps({"action": "continue"}))
```

## Timeout Requirements

| Hook Type | Max Timeout | Recommended |
|-----------|-------------|-------------|
| PreToolUse | 30000ms | 3000-10000ms |
| PostToolUse | 30000ms | 3000-10000ms |
| SessionStart | 10000ms | 3000-5000ms |
| Stop | 5000ms | 1000-3000ms |
| Notification | 5000ms | 1000-3000ms |

**Warning**: Timeouts over 60000ms (1 minute) are excessive and should be reviewed.

## Event Types

Valid event types in hooks.json:

| Event | When Triggered |
|-------|----------------|
| `PreToolUse` | Before a tool is executed |
| `PostToolUse` | After a tool completes |
| `SessionStart` | When Claude Code session begins |
| `Stop` | When session is ending |
| `SubagentStop` | When a subagent completes |
| `Notification` | System notifications |
| `UserPromptSubmit` | User submits a prompt |

## Input Schema by Event Type

### PreToolUse Input

```json
{
  "tool_name": "string",
  "tool_input": { ... },
  "session_id": "string",
  "conversation_id": "string"
}
```

### PostToolUse Input

```json
{
  "tool_name": "string",
  "tool_input": { ... },
  "tool_output": "string",
  "session_id": "string",
  "conversation_id": "string"
}
```

### SessionStart Input

```json
{
  "session_id": "string",
  "working_directory": "string"
}
```

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| HP-001 | Has `#!/usr/bin/env python3` shebang | critical |
| HP-002 | Uses `json.load(sys.stdin)` or equivalent | critical |
| HP-003 | Outputs JSON to stdout | critical |
| HP-004 | Has try/except error handling | high |
| HP-005 | Uses `sys.exit(0)` on error | high |
| HP-006 | Uses stderr for messages | medium |
| HP-007 | Timeout under 60000ms | medium |
| HP-008 | Output includes `action` field | critical |

## References

- Claude Code Documentation: Hook Protocol
- Source: packages/plugin/hooks/*.py
