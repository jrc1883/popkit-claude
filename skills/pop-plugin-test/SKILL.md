---
name: plugin-test
description: "Use when verifying plugin integrity, testing hooks, or validating agent routing - runs comprehensive self-tests to ensure all plugin components function correctly. Tests structure, hooks, agents, skills, and commands against their schemas. Do NOT use for application testing or runtime validation - this is specifically for popkit plugin component verification."
---

# Plugin Self-Testing

## Overview

Comprehensive testing framework for validating plugin components. Tests hooks, agents, skills, commands, and routing logic to ensure everything works as expected.

**Announce at start:** "I'm using the plugin-test skill to run self-tests."

## Test Categories

### 1. Structure Tests
- All referenced files exist
- YAML frontmatter is valid
- Required fields present
- No broken references

### 2. Hook Tests
- JSON stdin/stdout protocol works
- Hooks respond without blocking
- Error handling is graceful
- Timeout behavior correct

### 3. Agent Tests
- Agent definitions load correctly
- Tool permissions are valid
- Routing keywords resolve properly
- Confidence scoring works

### 4. Skill Tests
- SKILL.md format valid
- Description includes "Use when..."
- Referenced skills exist
- No circular dependencies

### 5. Command Tests
- Commands resolve to skills
- Arguments parsed correctly
- Help text present
- Output format valid

## Test Protocol

### Running Tests

```bash
# All tests
/plugin-test

# Specific category
/plugin-test hooks
/plugin-test agents
/plugin-test skills
/plugin-test routing
```

### Test Output Format

```
[PASS] hook/pre-tool-use - JSON response valid
[PASS] hook/post-tool-use - JSON response valid
[FAIL] hook/notification - Missing timestamp field
[SKIP] agent/rapid-prototyper - No test file

Summary: 42 passed, 1 failed, 3 skipped
```

## Test File Format

Tests live in `tests/` directory:

```
tests/
  hooks/
    test-pre-tool-use.json     # Input/expected output pairs
    test-post-tool-use.json
  agents/
    test-routing.json          # Routing verification
  skills/
    test-structure.json        # Structure validation
```

### Hook Test Format

```json
{
  "name": "pre-tool-use",
  "tests": [
    {
      "name": "blocks dangerous commands",
      "input": {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"}
      },
      "expected": {
        "decision": "block"
      }
    },
    {
      "name": "allows safe reads",
      "input": {
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"}
      },
      "expected": {
        "decision": "allow"
      }
    }
  ]
}
```

### Routing Test Format

```json
{
  "name": "agent-routing",
  "tests": [
    {
      "name": "bug keyword routes to bug-whisperer",
      "prompt": "fix this bug in the authentication code",
      "expected_agent": "bug-whisperer",
      "min_confidence": 0.6
    }
  ]
}
```

## Execution

1. **Load test files** from tests/ directory
2. **Execute each test:**
   - Prepare input
   - Run component (hook/agent/skill)
   - Compare output to expected
3. **Report results** with pass/fail counts
4. **Save report** to tests/results/latest.json

## Key Principles

- **Non-destructive** - Tests must not modify production state
- **Isolated** - Each test runs independently
- **Deterministic** - Same input = same output
- **Fast** - Complete suite under 30 seconds
- **Informative** - Clear failure messages

## Integration

**Called by:**
- CI/CD pipeline
- Pre-commit hook (optional)
- Manual validation

**Outputs:**
- Console test results
- tests/results/latest.json
- tests/results/history.json (append)
