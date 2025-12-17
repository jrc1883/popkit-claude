---
description: Morning health check via MCP (Ready to Code score 0-100)
---

# /$PREFIX$:morning - $PROJECT$ Morning Check

Run the MCP-based morning health check.

## Usage

```
/$PREFIX$:morning           # Full morning report
/$PREFIX$:morning quick     # Compact summary
```

## Implementation

This command uses the project's MCP server tools for health checks.

### Primary Check

Run the `mcp__$SERVER$__morning_routine` MCP tool if available.

This returns structured JSON with:
- Service status (API, database, cache)
- Connectivity checks
- Ready to Code score (0-100)
- Any issues or warnings

### Fallback Checks

If `morning_routine` is unavailable, run individual health tools:

$HEALTH_TOOLS_LIST$

### Display Format

```
$PROJECT$ Morning Health Check
==============================

Services:
$SERVICE_STATUS$

Ready to Code: $SCORE$/100

$RECOMMENDATIONS$
```

## MCP Tools Reference

| Tool | Purpose |
|------|---------|
$TOOLS_TABLE$

## Notes

- This is an MCP wrapper command (lightweight, auto-syncs with server)
- Health checks run through `mcp__$SERVER$__*` tools
- Structured JSON responses enable automation
- Update MCP server to add new health checks (no command changes needed)
