# Plugin Schema Standard

## Overview

Claude Code plugins require specific configuration files with defined schemas. This standard defines the exact requirements.

## Required Files

| File | Purpose | Required |
|------|---------|----------|
| `.claude-plugin/plugin.json` | Plugin manifest | Yes |
| `hooks/hooks.json` | Hook configuration | If using hooks |
| `.mcp.json` | MCP server config | If using MCP |
| `agents/config.json` | Agent routing | If using agents |

## plugin.json Schema

### Required Fields

```json
{
  "name": "string",           // Plugin identifier (lowercase, hyphens)
  "description": "string",    // Human-readable description
  "version": "string",        // Semantic version (x.y.z)
  "author": "string"          // Author name or GitHub username
}
```

### Optional Fields

```json
{
  "repository": "string",     // GitHub repo URL
  "homepage": "string",       // Documentation URL
  "license": "string",        // License identifier (MIT, Apache-2.0, etc.)
  "keywords": ["string"],     // Discovery keywords
  "engines": {                // Compatibility
    "claude-code": ">=1.0.0"
  }
}
```

### Validation Rules

| Field | Rule | Severity |
|-------|------|----------|
| name | Must match `/^[a-z][a-z0-9-]*$/` | critical |
| version | Must be valid semver | critical |
| description | Must be non-empty | high |
| author | Must be non-empty | high |

## hooks.json Schema

### Structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "hooks": [
    {
      "event": "string",      // Event type
      "command": "string",    // Script to run
      "timeout": number,      // Timeout in ms
      "working_dir": "string" // Optional working directory
    }
  ]
}
```

### Valid Event Types

- `PreToolUse`
- `PostToolUse`
- `SessionStart`
- `Stop`
- `SubagentStop`
- `Notification`
- `UserPromptSubmit`

### Validation Rules

| Check | Rule | Severity |
|-------|------|----------|
| Schema reference | Should include `$schema` | low |
| Event type | Must be valid event | critical |
| Command | Script must exist | critical |
| Timeout | Must be positive number | high |
| Timeout | Should be < 60000ms | medium |

## .mcp.json Schema

### Structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "mcpServers": {
    "server-name": {
      "command": "string",
      "args": ["string"],
      "env": { "KEY": "value" }
    }
  },
  "tools": { ... },
  "resources": { ... },
  "settings": { ... }
}
```

### Validation Rules

| Check | Rule | Severity |
|-------|------|----------|
| Schema reference | Should include `$schema` | low |
| Server command | Must be valid executable | critical |
| Server args | Must be array of strings | high |

## agents/config.json Schema

### Structure

```json
{
  "routing": {
    "keywords": {
      "keyword": ["agent-name"]
    },
    "filePatterns": {
      "*.ext": ["agent-name"]
    },
    "errorPatterns": {
      "ErrorType": ["agent-name"]
    }
  },
  "tiers": {
    "tier-1-always-active": ["agent-name"],
    "tier-2-on-demand": ["agent-name"]
  },
  "agents": {
    "agent-name": {
      "effort": "high|medium|low",
      "model": "sonnet|opus|haiku",
      "thinking": { ... }
    }
  }
}
```

### Validation Rules

| Check | Rule | Severity |
|-------|------|----------|
| Agent exists | Referenced agents must have AGENT.md | critical |
| Keywords unique | No duplicate mappings | high |
| Model valid | Must be sonnet, opus, or haiku | high |
| Effort valid | Must be high, medium, or low | medium |

## File Existence Checks

| File | Must Exist | Severity |
|------|------------|----------|
| `.claude-plugin/plugin.json` | Yes | critical |
| `hooks/hooks.json` | If hooks dir exists | critical |
| Referenced hook scripts | Yes | critical |
| Referenced agent AGENT.md | Yes | critical |
| `.mcp.json` | If MCP used | high |

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| PS-001 | plugin.json exists | critical |
| PS-002 | plugin.json has name field | critical |
| PS-003 | plugin.json has version field | critical |
| PS-004 | plugin.json has description field | high |
| PS-005 | plugin.json has author field | high |
| PS-006 | hooks.json has valid event types | critical |
| PS-007 | All referenced scripts exist | critical |
| PS-008 | All referenced agents exist | critical |
| PS-009 | Timeout values are reasonable | medium |
| PS-010 | Schema references included | low |

## References

- Claude Code Plugin Documentation
- Source: packages/plugin/.claude-plugin/plugin.json
