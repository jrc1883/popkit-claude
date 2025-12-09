# Context Boundary Hook - Automated Context Clearing

> **Type**: Feature
> **Priority**: High
> **Epic**: Context Management
> **Estimated Complexity**: Medium

## Summary

Implement a Context Boundary system that automatically triggers context clearing (via `/compact` suggestions or direct API integration) at logical workflow milestones where state is already documented externally.

## Problem Statement

PopKit workflows document state externally:
- **GitHub Issues**: Task descriptions, acceptance criteria
- **Git commits**: What changed, why
- **STATUS.json**: Current focus, tasks, decisions
- **Power Mode state**: Agent coordination, insights

Despite this external documentation, conversation context grows indefinitely until Claude Code's auto-compaction at ~200K tokens. This is inefficient because:

1. Redundant context persists (file contents already committed)
2. Token costs increase unnecessarily
3. Context can become stale or conflicting
4. Users hit context limits during long sessions

## Solution

Create **Context Boundaries** - logical workflow points where aggressive context clearing is safe because state is externalized.

### Boundary Types

| Boundary | Trigger | Safe to Clear | Preserve |
|----------|---------|---------------|----------|
| `phase_complete` | `issue-workflow.py` phase transition | Full file contents from Read, old search results | Phase summary, decisions, next action |
| `commit_pushed` | `git push` succeeds | File diffs, edit confirmations | Commit hash, changed files list |
| `pr_created` | `gh pr create` succeeds | All implementation context | PR URL, summary |
| `issue_closed` | Issue state → closed | Everything except learnings | Patterns learned, final summary |
| `test_passed` | Test suite passes | Test output, debug traces | Pass/fail summary |
| `token_threshold` | 60%+ context usage | Aged tool results | Recent context, active task |

## Integration Points

### 1. Extend `issue-workflow.py` (Primary)

```python
# In complete_phase()
def complete_phase(self, phase_name: str, force: bool = False) -> Dict[str, Any]:
    # ... existing quality gate logic ...

    # NEW: Context boundary at phase transition
    if self.context_boundary_enabled():
        boundary_result = self.trigger_context_boundary(
            boundary_type="phase_complete",
            completed_phase=phase_name,
            next_phase=next_phase
        )
        result["context_boundary"] = boundary_result
```

### 2. Extend `context-monitor.py`

```python
# Add to threshold check
if usage_ratio >= THRESHOLDS["warning"]:
    result["context_boundary"] = {
        "type": "token_threshold",
        "action": "suggest_compact",
        "safe_to_clear": self.get_safe_to_clear_items()
    }
```

### 3. New Hook: `context-boundary.py`

```python
class ContextBoundaryHook:
    """PostToolUse hook that detects context boundary events."""

    BOUNDARY_TRIGGERS = {
        "Bash": {
            "git push": "commit_pushed",
            "gh pr create": "pr_created",
            "gh issue close": "issue_closed",
        },
        "Read": {
            # No boundary - accumulates context
        },
        "Edit": {
            # Track for potential commit boundary
        }
    }

    def detect_boundary(self, tool_name: str, tool_input: Dict, tool_result: str) -> Optional[str]:
        """Detect if this tool call crossed a context boundary."""
        ...

    def suggest_clear(self, boundary_type: str) -> Dict:
        """Generate clearing suggestion based on boundary type."""
        ...
```

### 4. Command Flag Integration

```yaml
# In commands that support context boundaries:
description: "... [--context-clear, --preserve-context]"
```

```python
# Flag parser addition
def parse_context_flags(args: str) -> Dict:
    """Parse context boundary flags."""
    return {
        "auto_clear": "--context-clear" in args,
        "preserve": "--preserve-context" in args,
        "clear_level": extract_clear_level(args)  # aggressive, moderate, conservative
    }
```

## Implementation Plan

### Phase 1: Boundary Detection (hooks/context-boundary.py)

1. Create new PostToolUse hook
2. Detect boundary-crossing tool calls (push, PR, issue close)
3. Output suggestions (no forced clearing yet)
4. Add to `hooks/hooks.json` configuration

**Files to create/modify:**
- `hooks/context-boundary.py` (new)
- `hooks/hooks.json` (add hook entry)

### Phase 2: Phase Transition Integration

1. Extend `issue-workflow.py` `complete_phase()`
2. Add context clearing suggestion after quality gates pass
3. Create phase transition summary for preservation
4. Store what was cleared for debugging

**Files to modify:**
- `hooks/issue-workflow.py`

### Phase 3: Token Threshold Integration

1. Extend `context-monitor.py` threshold logic
2. Add `context_boundary` field to threshold results
3. Suggest clearing based on content age, not just total tokens
4. Track what was cleared and when

**Files to modify:**
- `hooks/context-monitor.py`

### Phase 4: Command Flags

1. Add `--context-clear` / `--preserve-context` to flag parser
2. Apply to `/popkit:dev`, `/popkit:issue`, `/popkit:power` commands
3. Pass through to hooks via context carrier

**Files to modify:**
- `hooks/utils/flag_parser.py`
- `commands/dev.md`, `commands/issue.md`, `commands/power.md`

### Phase 5: External Brain (Optional Future)

1. Move discoveries to `~/.claude/popkit/brain/`
2. Auto-externalize at boundaries
3. Retrieval via semantic search

## Configuration

```json
// In power-mode/config.json or new context-config.json
{
  "context_boundaries": {
    "enabled": true,
    "default_level": "moderate",
    "levels": {
      "aggressive": {
        "clear_at": ["phase_complete", "commit_pushed", "test_passed"],
        "token_threshold": 0.5,
        "preserve_last_n_tools": 3
      },
      "moderate": {
        "clear_at": ["pr_created", "issue_closed"],
        "token_threshold": 0.7,
        "preserve_last_n_tools": 5
      },
      "conservative": {
        "clear_at": ["issue_closed"],
        "token_threshold": 0.85,
        "preserve_last_n_tools": 10
      }
    },
    "always_preserve": [
      "current_task",
      "active_file",
      "last_error",
      "key_decisions"
    ]
  }
}
```

## User Experience

### Status Line Integration

```
[POP] #57 Phase: impl (2/4) [##--] 45% | CTX: 62k/200k [boundary: commit_pushed]
```

### Suggested Actions

When a boundary is detected:

```
✓ Commit pushed to origin/feature-auth

Context Boundary Reached: commit_pushed
  Safe to clear: 15 file reads, 8 search results, 3 test outputs
  Preserved: commit abc123, STATUS.json, current task

  Options:
  1. Clear now (recommended) - saves ~45k tokens
  2. Keep context (continue without clearing)
  3. Review what will be cleared first
```

### Command Example

```bash
# Automatic clearing at boundaries
/popkit:dev work #57 --context-clear

# Preserve context explicitly
/popkit:dev work #57 --preserve-context

# Check current context status
/popkit:context status
```

## Acceptance Criteria

- [ ] `hooks/context-boundary.py` detects boundary events
- [ ] Phase transitions suggest/trigger context clearing
- [ ] Token thresholds enhanced with smart clearing
- [ ] Flags `--context-clear` / `--preserve-context` work
- [ ] Status line shows boundary events
- [ ] Configuration allows customization
- [ ] Documentation updated

## Testing

```bash
# Test boundary detection
python hooks/context-boundary.py < test-inputs/git-push.json

# Test phase transition
python hooks/issue-workflow.py complete implementation

# Test threshold integration
python hooks/context-monitor.py < test-inputs/high-usage.json
```

## Related

- **Extends**: `context-monitor.py` (Issue #16)
- **Extends**: `issue-workflow.py` (Issue #11)
- **Relates to**: Power Mode phase transitions
- **Relates to**: `pop-session-capture` skill
- **Research**: `docs/research/automated-context-management.md`

## Open Questions

1. **How to trigger `/compact`?** - Can hooks suggest commands? Or need API integration?
2. **What's the minimum preservation set?** - STATUS.json alone sufficient?
3. **Should clearing be automatic or prompted?** - Aggressive in Power Mode, prompted otherwise?
4. **How to handle mid-task boundaries?** - Only clear at natural pause points?

---

## PopKit Guidance

```yaml
workflow_type: brainstorm_first
complexity: medium
power_mode: optional
phases:
  - discovery (understand existing context-monitor, issue-workflow)
  - architecture (design hook integration)
  - implementation (create context-boundary.py)
  - testing (validate boundary detection)
  - documentation (update CLAUDE.md)
agents:
  primary: code-architect
  supporting: test-writer-fixer
quality_gates:
  - python-lint
  - hook-tests
```
