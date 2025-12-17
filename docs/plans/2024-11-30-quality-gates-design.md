# Quality Gates Hook Design

**Date:** 2024-11-30
**Issue:** #11 (Unified Orchestration System)
**Status:** Approved via brainstorming session

## Overview

PostToolUse hook that validates code integrity after file modifications, preventing broken builds and catching errors early.

## Core Behavior

### Trigger Conditions

```
Trigger Conditions:
├── High-risk action detected (immediate)
│   ├── Delete file
│   ├── Modify config (tsconfig, package.json, *.config.*)
│   ├── Change imports/exports
│   └── 3+ files modified rapidly
├── Batch threshold reached (5 file edits)
└── Agent completion (safety net)
```

### Detection (Hybrid)

Auto-detect from project files with config override capability:

| Detection | Condition | Command |
|-----------|-----------|---------|
| TypeScript | `tsconfig.json` exists | `npx tsc --noEmit` |
| Build | `package.json` has "build" script | `npm run build` |
| Lint | `package.json` has "lint" script | `npm run lint` |
| Test | `package.json` has "test" script | `npm test` (optional) |

Override via `.claude/quality-gates.json` if user needs custom gates.

### State Tracking

State stored in `.claude/quality-gate-state.json`:
- `file_edit_count`: Counter toward batch threshold
- `last_checkpoint`: Timestamp of last successful gate pass
- `high_risk_files`: Set of config files to watch

## Failure Handling

### Interactive Menu

When gates fail, present options:

```
┌─────────────────────────────────────────────────────────┐
│ Quality Gate Failed: TypeScript (3 errors)              │
├─────────────────────────────────────────────────────────┤
│ src/hooks/quality-gate.py:45                            │
│   Type 'string' is not assignable to type 'number'      │
│                                                         │
│ src/utils/parser.ts:12                                  │
│   Cannot find module './missing'                        │
├─────────────────────────────────────────────────────────┤
│ Options:                                                │
│   1. Fix now      - Address these errors (default)      │
│   2. Rollback     - Revert to last checkpoint           │
│   3. Continue     - Proceed despite errors              │
│   4. Pause        - Stop for manual review              │
└─────────────────────────────────────────────────────────┘
```

### Option Behaviors

| Option | Action | Next State |
|--------|--------|------------|
| Fix now | Log errors to context, continue session | Errors added to agent's awareness |
| Rollback | Save patch, git stash, restore checkpoint | Clean state, patch saved for recovery |
| Continue | Log warning, proceed | Errors may compound |
| Pause | Exit hook with "stop" signal | User takes manual control |

## Rollback Mechanism

### Checkpoint System

```
.claude/
├── checkpoints/
│   ├── 2024-11-30-143022.patch    # Saved diff from rollback
│   ├── 2024-11-30-141500.patch    # Previous rollback
│   └── manifest.json              # Checkpoint metadata
└── quality-gate-state.json        # Current hook state
```

### Rollback Flow

```python
def rollback():
    # 1. Capture current work (don't lose it)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    patch_path = f".claude/checkpoints/{timestamp}.patch"

    # Generate patch of all uncommitted changes
    run("git diff HEAD > {patch_path}")
    run("git diff --staged >> {patch_path}")

    # 2. Restore clean state
    run("git checkout .")        # Discard unstaged changes
    run("git reset HEAD .")      # Unstage any staged changes

    # 3. Inform user
    print(f"Rolled back. Changes saved to: {patch_path}")
    print(f"To recover: git apply {patch_path}")
```

### Manifest Tracking

```json
{
  "checkpoints": [
    {
      "timestamp": "2024-11-30-143022",
      "trigger": "rollback_requested",
      "files_affected": ["src/foo.ts", "src/bar.ts"],
      "gate_that_failed": "typescript",
      "error_count": 3
    }
  ],
  "retention_days": 7
}
```

Checkpoints older than 7 days auto-deleted on hook initialization.

## Configuration

### Auto-Detection Logic

```python
def detect_gates():
    gates = []

    if Path("tsconfig.json").exists():
        gates.append({
            "name": "typescript",
            "command": "npx tsc --noEmit",
            "timeout": 60
        })

    if Path("package.json").exists():
        pkg = json.load(open("package.json"))
        scripts = pkg.get("scripts", {})

        if "build" in scripts:
            gates.append({"name": "build", "command": "npm run build", "timeout": 120})
        if "lint" in scripts:
            gates.append({"name": "lint", "command": "npm run lint", "timeout": 60})
        if "test" in scripts:
            gates.append({"name": "test", "command": "npm test", "timeout": 300, "optional": True})

    return gates
```

### Override Configuration

`.claude/quality-gates.json`:

```json
{
  "gates": [
    {"name": "typescript", "command": "npx tsc --noEmit", "enabled": true},
    {"name": "build", "command": "npm run build", "enabled": true},
    {"name": "lint", "command": "npm run lint", "enabled": false},
    {"name": "custom", "command": "./scripts/validate.sh", "enabled": true}
  ],
  "triggers": {
    "batch_threshold": 5,
    "high_risk_patterns": ["tsconfig.json", "package.json", "*.config.*"]
  },
  "options": {
    "run_tests": false,
    "fail_fast": true,
    "timeout_multiplier": 1.0
  }
}
```

## Power Mode Integration

### Single Agent Mode (Default)

Standard flow - batched + high-risk triggers, full validation.

### Power Mode Active

When coordinator is running:

```python
def run_gate_check():
    if is_power_mode_active():
        # Lightweight check only - coordinator handles full validation
        return run_syntax_check_only()
    else:
        # Full validation
        return run_all_gates()

def run_syntax_check_only():
    """Fast check that doesn't block parallel agents."""
    if Path("tsconfig.json").exists():
        result = run("npx tsc --noEmit --skipLibCheck", timeout=15)
        if result.failed:
            publish_to_channel("pop:insights", {
                "type": "syntax_error",
                "agent_id": get_agent_id(),
                "errors": result.errors
            })
    return {"status": "continue"}  # Never blocks in Power Mode
```

### Coordinator Sync Points

Full validation at phase boundaries:

```python
async def on_phase_complete(phase_name):
    print(f"Phase '{phase_name}' complete. Running full validation...")

    result = run_all_gates()

    if result.failed:
        blame = analyze_git_blame(result.errors)
        broadcast("pop:broadcast", {
            "type": "gate_failure",
            "phase": phase_name,
            "errors": result.errors,
            "blame": blame
        })
        return await request_human_decision(result)

    return {"proceed": True}
```

## File Structure

```
hooks/
├── quality-gate.py           # NEW - Main PostToolUse hook
├── quality-gate-utils.py     # NEW - Detection, rollback helpers
└── hooks.json                # MODIFY - Register new hook

power-mode/
├── coordinator.py            # MODIFY - Add gate checks at sync points
└── config.json               # MODIFY - Add gate configuration

.claude/
├── quality-gates.json        # NEW (user-created) - Override config
├── quality-gate-state.json   # NEW (auto-generated) - Hook state
└── checkpoints/              # NEW (auto-generated) - Rollback patches
    └── manifest.json
```

## Implementation Order

| Step | Task | Depends On |
|------|------|------------|
| 1 | Create `quality-gate.py` skeleton with PostToolUse protocol | - |
| 2 | Implement auto-detection logic | Step 1 |
| 3 | Implement trigger logic (batched + high-risk) | Step 1 |
| 4 | Implement interactive menu on failure | Step 3 |
| 5 | Implement rollback mechanism | Step 4 |
| 6 | Add config override support | Step 2 |
| 7 | Integrate with Power Mode coordinator | Steps 1-5 |
| 8 | Register hook in `hooks.json` | Step 1 |
| 9 | Test end-to-end | All |

## Estimated Scope

~400-500 lines of Python across 2 files.
