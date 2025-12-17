# Automated Context Management Research

> **Status**: Research & Planning
> **Date**: 2025-12-05
> **Issue**: TBD (to be created after approval)

## Executive Summary

Claude Code's "Esc twice" rewind feature provides manual conversation/code restoration, but this research explores **automating context clearing** for PopKit's programmatic workflows where state is externally documented (GitHub issues, STATUS.json, etc.).

---

## Part 1: Claude Code Rewind Feature

### What It Does

Pressing **Esc twice** opens the **rewind menu** showing conversation history with Git-style diff notation:

```
"Restore the code and/or conversation to the point before..."
```

### Three Restoration Modes

| Mode | Effect | Use Case |
|------|--------|----------|
| **Conversation only** | Keep code changes, rewind chat | Want edits but retry the approach |
| **Code only** | Keep conversation, revert files | Keep context but undo file changes |
| **Both** | Full restore to prior point | Complete do-over |

### Related Commands

| Command | Effect |
|---------|--------|
| `/rewind` | Opens rewind menu (same as Esc twice) |
| `/clear` | Wipes conversation history completely |
| `/compact` | Summarizes conversation to save tokens |
| `/context` | Shows current token usage |

### Programmatic Access

**Available:**
- CLI: `claude --continue` / `claude --resume <session-id>`
- Session files: `~/.claude/history.jsonl`, `~/.claude/projects/`
- Auto-compaction at ~200K tokens

**Claude API Beta (context-management-2025-06-27):**
- `clear_tool_uses_20250919`: Clears oldest tool results beyond threshold
- `clear_thinking_20251015`: Clears older thinking blocks

### Limitations

- Cannot undo Bash-executed commands (`rm`, `mv`, etc.)
- Network operations cannot be reverted
- Time-sensitive operations cannot be reset

---

## Part 2: The Opportunity

### User's Insight

> "We're doing everything through GitHub, documenting issues then solving them. If everything is documented externally, can we clear context more aggressively after tool calls?"

### Current State: Everything Persists

```
┌─────────────────────────────────────────────────────────────────┐
│ Conversation Context (grows indefinitely until compaction)      │
├─────────────────────────────────────────────────────────────────┤
│ Turn 1: User asks to fix bug #123                               │
│ Turn 2: Claude reads 5 files                    ← Still here    │
│ Turn 3: Claude searches with Grep               ← Still here    │
│ Turn 4: Claude edits 2 files                    ← Still here    │
│ Turn 5: Claude runs tests                       ← Still here    │
│ Turn 6: Claude commits with message             ← Still here    │
│ Turn 7: Claude pushes to branch                 ← Still here    │
│ Turn 8: Claude creates PR                       ← Still here    │
│ ...                                                             │
│ Turn 50: Context is now 150K tokens            ← Expensive!     │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed State: Smart Clearing

```
┌─────────────────────────────────────────────────────────────────┐
│ Active Context (minimal, focused)                               │
├─────────────────────────────────────────────────────────────────┤
│ Issue #456 metadata (from GitHub)                               │
│ Current file being edited                                       │
│ Last test result                                                │
│ STATUS.json snapshot                                            │
├─────────────────────────────────────────────────────────────────┤
│ Cleared (documented externally):                                │
│ ✓ File reads → documented in commit                             │
│ ✓ Search results → issue has context                            │
│ ✓ Previous edits → committed to git                             │
│ ✓ Test runs → CI will rerun                                     │
│ ✓ PR creation → PR exists on GitHub                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 3: PopKit's Current Infrastructure

### External State Already Tracked

| Location | Contents | Persistence |
|----------|----------|-------------|
| `STATUS.json` | Task state, git info, focus area | Per-session |
| GitHub Issues | Task description, acceptance criteria | Permanent |
| Git commits | What changed, why | Permanent |
| Power Mode state | Agent coordination, insights | Per-session |
| Efficiency metrics | Tokens saved, patterns matched | Per-session |

### Existing Session Skills

```
pop-session-capture  → Saves to STATUS.json
pop-session-resume   → Restores from STATUS.json
pop-context-restore  → Full context restoration
```

### Power Mode Check-in Hook

Already extracts insights and pushes to Redis/file:
- Files touched
- Tools used
- Decisions made
- Insights shared/received

---

## Part 4: Proposed Solutions

### Solution A: Smart Context Boundaries (Recommended)

**Concept**: Define "context boundaries" at logical workflow points where clearing is safe.

```python
# Context boundaries for PopKit workflows
CONTEXT_BOUNDARIES = {
    "issue_resolved": {
        "trigger": "PR merged or issue closed",
        "action": "clear_all_except_status",
        "restore_from": ["STATUS.json", "GitHub issue"]
    },
    "phase_complete": {
        "trigger": "Power Mode phase transition",
        "action": "compact_and_summarize",
        "preserve": ["current_phase_context", "decisions"]
    },
    "commit_pushed": {
        "trigger": "git push succeeds",
        "action": "clear_file_contents",
        "preserve": ["commit_message", "changed_files_list"]
    },
    "test_passed": {
        "trigger": "test suite passes",
        "action": "clear_test_output",
        "preserve": ["pass/fail_summary"]
    }
}
```

**Implementation**:
1. New hook: `hooks/context-boundary.py`
2. Triggers on PostToolUse for boundary-defining tools
3. Calls `/compact` programmatically or uses API context editing
4. Logs what was cleared and why

### Solution B: Tiered Retention Policy

**Concept**: Different content types have different retention TTLs.

| Content Type | Retention | Rationale |
|--------------|-----------|-----------|
| File contents (Read) | Until edited/committed | Need for edits |
| Search results (Grep/Glob) | 3 tool calls | Initial discovery |
| Test output | Until next test run | Superseded |
| Bash output | Until success | For debugging |
| Edit confirmations | 1 tool call | Just acknowledgment |
| Thinking blocks | Never retain | API handles this |

**Implementation**:
1. Track tool results with timestamps
2. Hook clears aged-out content via `/compact` heuristics
3. CONFIG option: `context.retention_policy`

### Solution C: Checkpoint-Based Restoration

**Concept**: Automatically create restoration points and offer quick restore.

```
┌─────────────────────────────────────────────────────────────────┐
│ Checkpoint: Issue #123 Started                                  │
│   └── Checkpoint: Files Discovered                              │
│         └── Checkpoint: Implementation Done                     │
│               └── Checkpoint: Tests Passing                     │
│                     └── Checkpoint: PR Created    ← Current     │
└─────────────────────────────────────────────────────────────────┘
```

**On next session**:
```
Which checkpoint to restore from?
1. PR Created (most recent) - minimal context
2. Tests Passing - has test details
3. Implementation Done - has full file context
4. Fresh start - just STATUS.json
```

**Implementation**:
1. Extend `pop-session-capture` with checkpoint naming
2. Store checkpoint metadata (not full context)
3. `/popkit:restore <checkpoint>` command
4. Integration with `/rewind` mental model

### Solution D: External Brain Pattern

**Concept**: Move more state out of context into structured storage.

```
~/.claude/popkit/brain/
├── issues/
│   └── 123/
│       ├── discovery.md      # What we learned
│       ├── decisions.md      # Why we chose X
│       ├── files.json        # Relevant files list
│       └── progress.md       # Current status
├── patterns/
│   └── auth-pattern.md       # Reusable knowledge
└── sessions/
    └── 2025-12-05/
        └── session.jsonl     # Compressed history
```

**In-context only**:
- Current objective
- Active file being edited
- Last tool result

**Retrieved on demand**:
- Everything else via Read tool

**Implementation**:
1. New skill: `pop-externalize-context`
2. Modify Power Mode check-in to auto-externalize
3. Retrieval skill: `pop-recall <topic>`

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (1-2 Issues)

1. **Context Boundary Detection** (`hooks/context-boundary.py`)
   - Define boundary types
   - Detect when boundaries are crossed
   - Log boundary events

2. **Programmatic Compact Integration**
   - Research how to trigger `/compact` from hooks
   - Alternative: Use Context Editing API if available

### Phase 2: Smart Clearing (2-3 Issues)

3. **Tiered Retention Implementation**
   - Add retention metadata to hook tracking
   - Implement TTL-based clearing
   - Config: `power-mode/config.json` → `context_retention`

4. **Checkpoint System**
   - Extend STATUS.json schema for checkpoints
   - `/popkit:checkpoint <name>` command
   - Integrate with session-resume

### Phase 3: External Brain (2-3 Issues)

5. **Brain Storage Structure**
   - Define schema for externalized knowledge
   - Migration from STATUS.json

6. **Auto-Externalization Hook**
   - PostToolUse hook to externalize discoveries
   - Pattern detection for reusable knowledge

7. **Retrieval Skill**
   - Semantic search over brain storage
   - Integration with existing embeddings

---

## Part 6: Technical Considerations

### Claude API Integration

The Context Editing API (beta) provides:

```python
# API-level context management
{
    "betas": ["context-management-2025-06-27"],
    "context_management": {
        "clear_tool_uses_20250919": {
            "threshold_tokens": 100000  # Clear when exceeded
        },
        "clear_thinking_20251015": {}
    }
}
```

**Question**: Can Claude Code use this API feature? Need to investigate.

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Clearing needed context | Conservative defaults, user override |
| Breaking mid-task | Only clear at boundaries |
| Loss of debugging info | Always preserve last error |
| User confusion | Clear status line indicator |

### Metrics to Track

| Metric | Purpose |
|--------|---------|
| Tokens before/after clear | Measure savings |
| Context retrievals needed | Measure over-clearing |
| Boundary hit frequency | Tune timing |
| User override frequency | Tune aggressiveness |

---

## Part 7: Open Questions

1. **Can we trigger `/compact` from a hook?**
   - Need to test if output can include command suggestion
   - Alternative: Direct Claude API context editing

2. **What's the minimum viable context for task resumption?**
   - STATUS.json seems sufficient for basic tasks
   - Complex tasks may need more

3. **Should clearing be automatic or user-confirmed?**
   - Power Mode: Automatic (users expect efficiency)
   - Normal mode: Prompt or suggest

4. **How does this interact with git checkpointing?**
   - Claude Code tracks file changes
   - Our clearing is about conversation, not code

5. **Can we access `~/.claude/history.jsonl` from hooks?**
   - Would allow smarter compaction decisions
   - Privacy/security considerations

---

## Recommendations

### Immediate (Low Risk)

1. **Add context metrics to status line**
   - Show current context size
   - Indicate when nearing limits

2. **Document `/compact` usage in PopKit**
   - Add to morning/nightly routines
   - Suggest after major milestones

### Short Term (Medium Risk)

3. **Implement Context Boundary Hook**
   - Start with commit/PR boundaries
   - Suggest `/compact` rather than force

4. **Extend STATUS.json for Checkpoints**
   - Named restore points
   - `/popkit:checkpoint` command

### Long Term (Higher Risk, Higher Reward)

5. **External Brain Pattern**
   - Full externalization of discoveries
   - Semantic retrieval integration

6. **API Context Editing Integration**
   - If Claude Code exposes this feature
   - Automatic tool result clearing

---

## Next Steps

1. [ ] Create GitHub issue for Context Boundary Hook
2. [ ] Investigate `/compact` triggering from hooks
3. [ ] Test Context Editing API with Claude Code
4. [ ] Prototype checkpoint extension to STATUS.json
5. [ ] Gather user feedback on aggressiveness preferences

---

## Appendix: Related Files

- `skills/pop-session-capture/SKILL.md` - Current session saving
- `skills/pop-session-resume/SKILL.md` - Current session restoration
- `skills/pop-context-restore/SKILL.md` - Full context restoration
- `power-mode/checkin-hook.py` - Power Mode state tracking
- `hooks/utils/efficiency_tracker.py` - Token savings tracking
