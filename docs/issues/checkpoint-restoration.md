# Checkpoint-Based Restoration - Named Recovery Points

> **Type**: Feature
> **Priority**: Medium
> **Epic**: Context Management
> **Depends On**: Context Boundary Hook
> **Estimated Complexity**: Low-Medium

## Summary

Extend PopKit's session management with **named checkpoints** that capture context state at meaningful moments, allowing users to restore to specific points rather than just "most recent" or "start fresh".

## Problem Statement

Current session restoration (`pop-session-resume`) offers three modes based on time:
- **Continuation** (< 30 min): Quick restore
- **Resume** (30 min - 4 hours): Restore with refresh
- **Fresh Start** (> 4 hours): Full context load

This is limiting because:

1. **Time-based isn't semantic** - A commit 5 minutes ago may be a better restore point than the session start
2. **No granularity** - Can't restore to "after tests passed" vs "after architecture decided"
3. **Lost decision points** - Important milestones aren't captured for later reference
4. **Mismatch with rewind** - Claude Code's Esc-twice shows conversation turns, not workflow milestones

## Solution

Add **named checkpoints** that capture:
- STATUS.json snapshot
- Git state (branch, last commit, uncommitted files)
- Active task and phase
- Key decisions made since last checkpoint
- Token usage at checkpoint time

### Checkpoint Model

```
Session Timeline with Checkpoints:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━►

[START]──[discovery]──[arch-decided]──[impl-v1]──[tests-pass]──[pr-ready]
    │         │             │             │           │            │
    ▼         ▼             ▼             ▼           ▼            ▼
 auto     auto          manual        auto       auto         auto
         (phase)      (user)       (commit)   (tests)       (PR)
```

### Checkpoint Types

| Type | Trigger | Contents | Use Case |
|------|---------|----------|----------|
| **Auto: Phase** | Phase transition | Phase summary, decisions | Restore to phase start |
| **Auto: Commit** | Git commit | Commit info, files changed | Restore to clean state |
| **Auto: Test Pass** | Test suite passes | Test summary, coverage | Restore to known-good |
| **Auto: PR** | PR created/merged | PR URL, review status | Restore to PR state |
| **Manual** | User command | User-provided name/note | Custom restore points |

## Integration with Existing Infrastructure

### 1. Extend STATUS.json Schema

```json
{
  "lastUpdate": "2025-01-15T14:30:00Z",
  "project": "my-app",
  "sessionType": "Resume",

  "checkpoints": [
    {
      "id": "cp_abc123",
      "name": "architecture-decided",
      "type": "manual",
      "timestamp": "2025-01-15T10:30:00Z",
      "trigger": "user",
      "git": {
        "branch": "feature/auth",
        "commit": "a7f3c2e",
        "uncommitted": 0
      },
      "context": {
        "phase": "architecture",
        "task": "Design auth flow",
        "tokenUsage": 45000,
        "decisions": [
          "Using JWT for authentication",
          "Session expiry: 1 hour"
        ]
      },
      "note": "Architecture approved, ready for implementation"
    },
    {
      "id": "cp_def456",
      "name": "tests-passing",
      "type": "auto:test_pass",
      "timestamp": "2025-01-15T12:15:00Z",
      "trigger": "npm test (45 passing)",
      "git": {
        "branch": "feature/auth",
        "commit": "b8c4d3f",
        "uncommitted": 2
      },
      "context": {
        "phase": "testing",
        "task": "Verify auth implementation",
        "tokenUsage": 82000,
        "testSummary": "45 passing, 0 failing, 92% coverage"
      }
    }
  ],

  "activeCheckpoint": "cp_def456",

  // ... existing fields ...
}
```

### 2. Checkpoint Manager Utility

New file `hooks/utils/checkpoint_manager.py`:

```python
@dataclass
class Checkpoint:
    id: str
    name: str
    type: str  # manual, auto:phase, auto:commit, auto:test, auto:pr
    timestamp: str
    trigger: str
    git: Dict[str, Any]
    context: Dict[str, Any]
    note: Optional[str] = None

class CheckpointManager:
    """Manages session checkpoints for restoration."""

    MAX_CHECKPOINTS = 20  # Rolling window

    def __init__(self, status_file: Path):
        self.status_file = status_file
        self.checkpoints: List[Checkpoint] = []
        self._load()

    def create(
        self,
        name: str,
        checkpoint_type: str,
        trigger: str,
        note: Optional[str] = None
    ) -> Checkpoint:
        """Create a new checkpoint."""
        cp = Checkpoint(
            id=f"cp_{generate_id()}",
            name=name,
            type=checkpoint_type,
            timestamp=datetime.now().isoformat(),
            trigger=trigger,
            git=self._capture_git_state(),
            context=self._capture_context(),
            note=note
        )
        self.checkpoints.append(cp)
        self._prune_old()
        self._save()
        return cp

    def restore(self, checkpoint_id: str) -> Dict[str, Any]:
        """Restore context to a checkpoint."""
        cp = self.get(checkpoint_id)
        if not cp:
            return {"error": f"Checkpoint {checkpoint_id} not found"}

        return {
            "checkpoint": cp,
            "actions": self._generate_restore_actions(cp),
            "context_to_load": cp.context
        }

    def list_for_selection(self) -> List[Dict]:
        """Format checkpoints for AskUserQuestion selection."""
        return [
            {
                "label": cp.name,
                "description": f"{cp.type} - {cp.timestamp[:10]} - {cp.note or cp.trigger}"
            }
            for cp in reversed(self.checkpoints)  # Most recent first
        ]

    def _capture_git_state(self) -> Dict:
        """Capture current git state."""
        ...

    def _capture_context(self) -> Dict:
        """Capture current context state."""
        ...
```

### 3. Issue Workflow Integration

Extend `hooks/issue-workflow.py`:

```python
def complete_phase(self, phase_name: str, force: bool = False) -> Dict[str, Any]:
    # ... existing logic ...

    # Create checkpoint at phase transition
    if next_phase:
        checkpoint_mgr = CheckpointManager(self.status_file)
        cp = checkpoint_mgr.create(
            name=f"phase-{phase_name}-complete",
            checkpoint_type="auto:phase",
            trigger=f"Completed phase: {phase_name}",
            note=f"Transitioning to {next_phase}"
        )
        result["checkpoint_created"] = cp.id
```

### 4. Context Boundary Integration

When context boundaries are crossed, auto-checkpoint:

```python
# In hooks/context-boundary.py
def on_boundary_crossed(self, boundary_type: str, details: Dict) -> Dict:
    checkpoint_mgr = CheckpointManager(self.status_file)

    if boundary_type == "commit_pushed":
        cp = checkpoint_mgr.create(
            name=f"commit-{details['commit_hash'][:7]}",
            checkpoint_type="auto:commit",
            trigger=f"git push: {details['commit_message'][:50]}"
        )
    elif boundary_type == "test_passed":
        cp = checkpoint_mgr.create(
            name="tests-passing",
            checkpoint_type="auto:test",
            trigger=details['test_summary']
        )
    elif boundary_type == "pr_created":
        cp = checkpoint_mgr.create(
            name=f"pr-{details['pr_number']}",
            checkpoint_type="auto:pr",
            trigger=f"PR #{details['pr_number']}: {details['pr_title'][:40]}"
        )
```

### 5. Session Resume Enhancement

Extend `skills/pop-session-resume/SKILL.md`:

```markdown
## Checkpoint-Aware Resume

When checkpoints are available, offer selection:

### Step 2b: Checkpoint Selection (if available)

If STATUS.json contains checkpoints:

Use AskUserQuestion tool with:
- question: "Which point would you like to restore to?"
- header: "Checkpoints"
- options: [checkpoint list from CheckpointManager.list_for_selection()]
- multiSelect: false

Based on selection:
- Load checkpoint's context snapshot
- Restore git state if different
- Set current phase from checkpoint
- Display checkpoint note/summary
```

## Command Interface

### Create Manual Checkpoint

```bash
/popkit:checkpoint "architecture finalized"

# Output:
# ✓ Checkpoint created: cp_abc123
#
# Name: architecture finalized
# Git: feature/auth @ a7f3c2e (0 uncommitted)
# Phase: architecture
# Tokens: 45,000 / 200,000
#
# Restore with: /popkit:restore cp_abc123
```

### List Checkpoints

```bash
/popkit:checkpoint list

# Output:
# Session Checkpoints (5)
# ───────────────────────
#
# 1. [cp_ghi789] pr-42 (auto:pr)
#    2 hours ago | PR #42: Add user authentication
#
# 2. [cp_def456] tests-passing (auto:test)
#    3 hours ago | 45 passing, 92% coverage
#
# 3. [cp_abc123] architecture finalized (manual)
#    5 hours ago | Architecture approved, ready for implementation
#
# 4. [cp_xyz000] phase-discovery-complete (auto:phase)
#    6 hours ago | Transitioning to architecture
#
# 5. [cp_start] session-start (auto)
#    8 hours ago | Fresh session started
```

### Restore to Checkpoint

```bash
/popkit:restore cp_abc123

# Output:
# Restoring to checkpoint: architecture finalized
# ───────────────────────────────────────────────
#
# Context:
# - Phase: architecture
# - Task: Design auth flow
# - Decisions loaded: 2
#
# Git state:
# - Current: feature/auth @ b8c4d3f (2 uncommitted)
# - Checkpoint: feature/auth @ a7f3c2e (0 uncommitted)
#
# ⚠️  Git state differs from checkpoint.
#
# Options:
# [1] Restore context only (keep current code)
# [2] Restore context + reset to commit a7f3c2e
# [3] Cancel
```

### Interactive Restore (on session start)

When `pop-session-resume` detects checkpoints:

```
🔄 Resume Session
Last: 4 hours ago

Checkpoints available:
┌─────────────────────────────────────────────────────────┐
│ 1. tests-passing (3h ago)                               │
│    45 passing, 92% coverage                             │
│                                                         │
│ 2. architecture finalized (5h ago)                      │
│    Architecture approved, ready for implementation      │
│                                                         │
│ 3. Start fresh (ignore checkpoints)                     │
└─────────────────────────────────────────────────────────┘

Which checkpoint to restore from? [1/2/3]
```

## Implementation Plan

### Phase 1: Checkpoint Manager Core

1. Create `hooks/utils/checkpoint_manager.py`
2. Define Checkpoint dataclass
3. Implement create, list, get, restore methods
4. Add STATUS.json persistence

**Files:**
- `hooks/utils/checkpoint_manager.py` (new)

### Phase 2: Auto-Checkpoint Triggers

1. Integrate with `issue-workflow.py` phase transitions
2. Integrate with `context-boundary.py` boundary events
3. Add test pass detection

**Files:**
- `hooks/issue-workflow.py` (modify)
- `hooks/context-boundary.py` (modify)

### Phase 3: Command Interface

1. Create `/popkit:checkpoint` command
2. Create `/popkit:restore` command
3. Add to flag parser

**Files:**
- `commands/checkpoint.md` (new)
- `commands/restore.md` (new)

### Phase 4: Session Resume Enhancement

1. Extend `pop-session-resume` skill
2. Add checkpoint selection UI
3. Implement restore actions

**Files:**
- `skills/pop-session-resume/SKILL.md` (modify)

### Phase 5: Status Line Integration

1. Show current checkpoint in status line
2. Add checkpoint indicator

**Files:**
- `power-mode/statusline.py` (modify)

## Acceptance Criteria

- [ ] Manual checkpoints can be created via command
- [ ] Auto-checkpoints created at phase transitions
- [ ] Auto-checkpoints created at context boundaries
- [ ] Checkpoint list shows in session resume
- [ ] Restore loads checkpoint context correctly
- [ ] Git state comparison shown on restore
- [ ] Rolling window maintains max 20 checkpoints
- [ ] STATUS.json schema extended correctly

## Testing

```bash
# Unit tests
python -m pytest tests/hooks/test_checkpoint_manager.py

# Integration test
python hooks/utils/checkpoint_manager.py --test

# Manual test flow
/popkit:checkpoint "test checkpoint"
/popkit:checkpoint list
/popkit:restore <id>
```

## Relation to Claude Code Rewind

This feature **complements** Claude Code's Esc-twice rewind:

| Feature | Claude Code Rewind | PopKit Checkpoints |
|---------|-------------------|-------------------|
| Granularity | Every conversation turn | Semantic milestones |
| Scope | Conversation + code | Context + git + phase |
| Trigger | Manual (Esc twice) | Auto + manual |
| Persistence | Session only | Across sessions |
| Selection | Visual timeline | Named list |

Users can use both:
- **Rewind** for "undo last few exchanges"
- **Checkpoints** for "go back to when tests were passing"

## Open Questions

1. **Git restore scope?** - Full reset or just show diff?
2. **Cross-session checkpoints?** - Persist beyond session end?
3. **Checkpoint diffing?** - Show what changed between checkpoints?
4. **Checkpoint sharing?** - Export/import for team workflows?

---

## PopKit Guidance

```yaml
workflow_type: direct
complexity: low
power_mode: not_needed
phases:
  - implementation (checkpoint manager)
  - implementation (auto triggers)
  - implementation (commands)
  - testing
agents:
  primary: code-architect
  supporting: documentation-maintainer
quality_gates:
  - python-lint
  - hook-tests
```
