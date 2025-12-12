---
name: pop-heartbeat
description: Monitor session health with heartbeat tracking, stuck detection, and progress visibility
---

# Heartbeat Monitoring

Track session health through periodic heartbeats. Detects stuck sessions, monitors progress, and enables recovery recommendations.

## When to Use

- During long-running development sessions
- When debugging complex issues that might get stuck
- To track progress across multi-phase workflows
- For visibility into agent performance
- To detect circular edit patterns or repeated failures

## Input

User provides:
- Optional subcommand: `status`, `list`, `beat`, `stuck`
- Optional flags: `--session`, `--json`

## Process

### 1. Session Status

Get current session health indicators:

```
/heartbeat status

[POP] 1h 23m | 🟢 127 calls | 8 files

Session: session-20241209-143022-abc123
Status: active
Duration: 1h 23m
Tool Calls: 127
Files Touched: 8
```

### 2. Stuck Detection

Check if the session shows stuck patterns:

```
/heartbeat stuck

Stuck Detection Analysis
========================

Status: ⚠️ Potentially Stuck
Confidence: 0.65

Indicators:
  ⚠️ File 'auth.ts' edited 7 times
  ⚠️ Circular edit pattern detected (auth.ts → routes.ts → auth.ts)

Recommendations:
  1. Step back from auth.ts - consider different approach
  2. Breaking circular pattern - try different approach
  3. Consider creating a checkpoint before continuing
```

### 3. List Sessions

Show all recent sessions:

```
/heartbeat list

Sessions (5):
  session-20241209-143022-abc123 - active - 2024-12-09T15:23:45
  session-20241209-102015-def456 - completed - 2024-12-09T12:45:30
  session-20241208-163022-ghi789 - idle - 2024-12-08T18:30:15
  ...
```

### 4. Manual Heartbeat

Record a manual heartbeat (normally automatic):

```
/heartbeat beat --progress "Implementing OAuth flow"

Heartbeat recorded: 2024-12-09T15:30:45
Session: session-20241209-143022-abc123
Progress: Implementing OAuth flow
```

## Stuck Detection Patterns

The heartbeat monitor detects these stuck patterns:

| Pattern | Description | Confidence |
|---------|-------------|------------|
| Heartbeat Age | No heartbeat for 3+ minutes | +0.4 |
| Repeated Edits | Same file edited 5+ times | +0.2 |
| Bash Failures | 3+ consecutive command failures | +0.3 |
| Circular Edits | A→B→A→B pattern in recent files | +0.3 |

**Stuck threshold**: Confidence ≥ 0.5 triggers stuck status.

## Subcommand Reference

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Show current session health |
| `list` | List all sessions |
| `beat` | Record manual heartbeat |
| `stuck` | Run stuck detection analysis |

## Flags

| Flag | Description |
|------|-------------|
| `--session`, `-s` | Session ID (default: current) |
| `--json`, `-j` | JSON output |
| `--progress`, `-p` | Progress description (for beat) |

## Status Line Format

The heartbeat provides a compact status line:

```
[POP] 45m | 🟢 127 calls | 5 files
[POP] 2h 15m | 🔴 342 calls | 12 files | ⚠️ 2 warnings
```

Components:
- `[POP]`: PopKit identifier
- Duration: Session runtime
- Status emoji: 🟢 active, 🔴 stuck, 🟡 idle, ✅ completed
- Tool calls: Total tools invoked
- Files: Unique files touched
- Warnings: Stuck indicators (if any)

## Example Flows

### Health Check During Long Session

```
User: How is my session doing?

Session Health Check
====================

[POP] 2h 45m | 🟢 256 calls | 15 files

Status: Active (Healthy)
Started: 2024-12-09T10:30:00
Tool Calls: 256
Files Modified: 15

Recent Activity:
  - Last tool: Edit (src/auth.ts)
  - Last heartbeat: 2 seconds ago

No stuck indicators detected.
```

### Stuck Session Detected

```
User: /heartbeat stuck

Stuck Detection Analysis
========================

Status: 🔴 STUCK
Confidence: 0.70

Indicators:
  ⚠️ File 'components/Auth.tsx' edited 8 times
  ⚠️ 4 Bash failures in recent calls
  ⚠️ Circular edit pattern detected

Recommendations:
  1. Step back from components/Auth.tsx
  2. Review approach - multiple command failures suggest wrong path
  3. Breaking circular pattern - try different approach

Suggested Actions:
  - Create checkpoint: /checkpoint create -d "Before trying new approach"
  - Review recent changes: git diff HEAD~5
  - Consider asking for help or taking a break
```

### Session Recovery

```
User: Resume my session from yesterday

Loading session session-20241208-163022-ghi789...

Session Restored
================

Previous State:
  Duration: 3h 15m
  Tool Calls: 412
  Last Activity: src/api/routes.ts

Files You Were Working On:
  - src/api/routes.ts (12 edits)
  - src/models/User.ts (5 edits)
  - tests/api.test.ts (8 edits)

Last Progress Note:
  "Implementing user authentication endpoint"

Ready to continue from where you left off.
```

## Integration with Other Tools

### With Checkpoints

```python
from heartbeat import get_monitor
from checkpoint import CheckpointManager

monitor = get_monitor()
detection = monitor.detect_stuck()

if detection.is_stuck:
    # Auto-checkpoint when stuck
    manager = CheckpointManager(monitor.session_id)
    manager.auto_checkpoint("stuck_detected")
```

### With Power Mode

In Power Mode, each agent maintains its own heartbeat:

```python
# Agent check-in includes heartbeat
{
    "agent_id": "code-reviewer-001",
    "session_id": "power-session-xyz",
    "heartbeat": {
        "tool_calls": 45,
        "files_touched": ["src/auth.ts"],
        "status": "active"
    }
}
```

### With Routines

Morning routine includes session health check:

```
Ready to Code Checklist
=======================

Session Health:
  ✅ No stuck sessions detected
  ⚠️ Found 1 session from yesterday (resume?)
    session-20241208-163022-ghi789
    Last activity: 3h ago
```

## Storage Location

Heartbeat data is stored in:
```
~/.claude/popkit/heartbeats/{session_id}/
  heartbeats.jsonl      # All heartbeats (append-only)
  latest.json           # Most recent heartbeat
  session_state.json    # Full session state
```

## Best Practices

1. **Monitor long sessions**: Check status periodically during complex work
2. **Heed stuck warnings**: They indicate potential issues
3. **Use progress notes**: Add context with `--progress` flag
4. **Review before resuming**: Check session state before continuing old work
5. **Create checkpoints when stuck**: Before trying a new approach

## Architecture

| Component | Purpose |
|-----------|---------|
| `heartbeat.py` | Core monitoring logic |
| `checkpoint.py` | State persistence |
| `.jsonl` files | Append-only heartbeat log |
| Session ID | Unique session identification |
| Status line | Compact health visualization |
