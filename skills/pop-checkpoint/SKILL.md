---
description: Create and restore checkpoints for long-running sessions with git-based state persistence
---

# Checkpoint Management

Save and restore session state for long-running development sessions. Enables recovery from crashes and continuation across sessions.

## When to Use

- Before risky operations (major refactors, complex merges)
- At phase boundaries in multi-step workflows
- When the session detects potential stuck patterns
- Before taking breaks in long development sessions
- To create restore points for experimental changes

## Input

User provides:
- Optional subcommand: `create`, `list`, `restore`, `show`, `auto`
- Optional flags: `--description`, `--checkpoint`, `--json`

## Process

### 1. Create Checkpoint

Save current session state with git-based file backup:

```python
from checkpoint import CheckpointManager

manager = CheckpointManager(session_id)
metadata = manager.create(
    description="Before major refactor",
    session_state={"tool_calls": 127, "phase": "implementation"},
    context={"current_file": "src/auth.ts", "task": "Add OAuth"}
)
```

This will:
1. Get list of modified files from `git status`
2. Create git stash as backup (then immediately pop to keep changes)
3. Save session state, file hashes, and context to JSON
4. Auto-cleanup old checkpoints (keeps last 10)

### 2. List Checkpoints

Show available checkpoints for the session:

```
/checkpoint list

Checkpoints for session session-20241209-143022-abc123:
  checkpoint-003-153045
    Before major refactor
    Created: 2024-12-09T15:30:45
    Files: 3

  checkpoint-002-142530 [auto]
    Auto-checkpoint after test failure
    Created: 2024-12-09T14:25:30
    Files: 5

  checkpoint-001-140015
    Initial state
    Created: 2024-12-09T14:00:15
    Files: 0
```

### 3. Restore Checkpoint

Restore to a previous checkpoint:

```
/checkpoint restore --checkpoint checkpoint-002-142530

Restored checkpoint: checkpoint-002-142530
  Files restored: 5
  Warnings:
    - Current uncommitted changes in 2 files
```

### 4. Auto-Checkpoint Triggers

Automatic checkpoints are created on certain events:

| Trigger | Description |
|---------|-------------|
| `build_failure` | After build command fails |
| `test_failure` | After tests fail |
| `stuck_detected` | When heartbeat detects stuck pattern |
| `phase_complete` | After completing a phase in workflows |
| `many_changes` | After significant file changes (10+ files) |

### 5. Show Checkpoint Details

View full details of a checkpoint:

```
/checkpoint show --checkpoint checkpoint-002-142530

Checkpoint: checkpoint-002-142530
  Description: Auto-checkpoint after test failure
  Created: 2024-12-09T14:25:30
  Tool calls: 85
  Files modified: ['src/auth.ts', 'src/api/routes.ts', ...]
  Git ref: stash@{0}
```

## Subcommand Reference

| Subcommand | Description |
|------------|-------------|
| `create` (default) | Create new checkpoint |
| `list` | List all checkpoints for session |
| `restore` | Restore to a checkpoint |
| `show` | Show checkpoint details |
| `auto` | Trigger auto-checkpoint |

## Flags

| Flag | Description |
|------|-------------|
| `--description`, `-d` | Checkpoint description |
| `--checkpoint`, `-c` | Checkpoint ID (for restore/show) |
| `--session`, `-s` | Session ID (default: current) |
| `--json`, `-j` | JSON output |

## Example Flows

### Manual Checkpoint Before Risky Change

```
User: Create a checkpoint before I start this refactor

Creating checkpoint...

Checkpoint Created: checkpoint-004-160230
  Description: Manual checkpoint
  Files tracked: 3
    - src/components/Auth.tsx
    - src/hooks/useAuth.ts
    - package.json
  Git backup: stash@{0}

You can restore with: /checkpoint restore --checkpoint checkpoint-004-160230
```

### Restore After Mistake

```
User: Restore to the checkpoint before my refactor

Analyzing current state...
  You have 5 uncommitted changes

Restoring checkpoint-004-160230...

Restored Successfully:
  Files restored: 3
  Warnings:
    - Created backup of current changes at stash@{1}

Your workspace is now at the state before the refactor.
```

### Auto-Checkpoint on Failure

```
[Build failed - TypeScript errors]

Auto-checkpoint created: checkpoint-005-161545
  Trigger: build_failure
  Description: Auto-checkpoint after build failure
  Files: 4

This checkpoint was created automatically. You can restore with:
/checkpoint restore --checkpoint checkpoint-005-161545
```

## Integration with Heartbeat

Checkpoints integrate with the heartbeat monitor for intelligent auto-checkpointing:

```python
from heartbeat import get_monitor
from checkpoint import CheckpointManager

monitor = get_monitor()
if monitor.detect_stuck().is_stuck:
    # Auto-create checkpoint when stuck detected
    manager = CheckpointManager(monitor.session_id)
    manager.auto_checkpoint(
        trigger="stuck_detected",
        session_state={"tool_calls": monitor.tool_calls},
        context={"stuck_indicators": monitor.detect_stuck().indicators}
    )
```

## Storage Location

Checkpoints are stored in:
```
~/.claude/popkit/checkpoints/{session_id}/
  checkpoint-001-HHMMSS.json
  checkpoint-002-HHMMSS.json
  ...
```

Each checkpoint JSON contains:
- `metadata`: ID, session, timestamp, description, files
- `session_state`: Tool calls, phase, progress
- `file_snapshots`: SHA-256 hashes of modified files
- `context`: Agent memory, current task info

## Best Practices

1. **Name checkpoints descriptively**: "Before OAuth integration" is better than "Checkpoint 1"
2. **Create checkpoints at natural boundaries**: End of phases, before merges
3. **Don't ignore auto-checkpoints**: They indicate potential issues
4. **Review checkpoint history**: Understanding past states helps debugging
5. **Clean up manually**: Though auto-cleanup exists, remove unnecessary checkpoints

## Architecture

| Component | Purpose |
|-----------|---------|
| `checkpoint.py` | Core checkpoint manager |
| `heartbeat.py` | Session health monitoring |
| Git stash | File backup mechanism |
| JSON files | State persistence |
| Session ID | Checkpoint grouping |
