# Tiered Retention Policy - Content-Aware Context Management

> **Type**: Feature
> **Priority**: Medium
> **Epic**: Context Management
> **Depends On**: Context Boundary Hook
> **Estimated Complexity**: Medium

## Summary

Implement a tiered retention system where different content types have different lifespans in context, automatically expiring based on age, supersession, or relevance rather than just total token count.

## Problem Statement

Currently, all context is treated equally - file contents from 50 tool calls ago persist alongside the current task. This leads to:

1. **Stale context**: Old file reads no longer match current file state
2. **Superseded data**: Test output from 3 runs ago is irrelevant
3. **Noise accumulation**: Edit confirmations, search results for abandoned paths
4. **Inefficient compaction**: When `/compact` runs, it summarizes everything equally

## Solution

Assign **retention tiers** to different content types, with automatic expiration based on configurable rules.

### Retention Tiers

| Tier | Content Type | Default TTL | Expiry Trigger | Rationale |
|------|--------------|-------------|----------------|-----------|
| **Ephemeral** | Edit confirmations, mkdir results | 1 tool call | Next tool | Just acknowledgments |
| **Short** | Search results (Grep/Glob) | 5 tool calls | New search same pattern | Discovery phase ends |
| **Medium** | File contents (Read) | Until file edited/committed | Edit or commit | Need for reference |
| **Session** | Test output, build results | Until next run | Same command re-run | Superseded by new run |
| **Preserved** | Errors, decisions, STATUS.json | Never auto-expire | Manual clear only | Critical context |

### Visual Model

```
Tool Call Timeline:
──────────────────────────────────────────────────────────────────────►

T1: Read src/auth.ts          [████████████████░░░░] expires at T20 or edit
T2: Grep "login"              [████░░░░░░░░░░░░░░░░] expires at T7
T3: Read src/config.ts        [████████████████░░░░] expires at T23 or edit
T4: Edit src/auth.ts          [░] ephemeral - gone at T5
T5: npm test (fail)           [████████████████████] expires on next test
T6: Grep "login"              ← T2 results expire (same pattern searched)
T7: npm test (pass)           ← T5 results expire (superseded)
T8: git commit                ← T1, T3 expire (files committed)
```

## Integration with Existing Infrastructure

### 1. Hook Context Carrier Enhancement

Extend `hooks/utils/context_carrier.py`:

```python
@dataclass(frozen=True)
class ToolResultMeta:
    """Metadata for retention tracking."""
    tool_name: str
    tool_call_index: int
    timestamp: str
    retention_tier: str  # ephemeral, short, medium, session, preserved
    expiry_trigger: Optional[str]  # "tool_count:5", "supersede:npm test", "edit:file.ts"
    content_hash: str  # For deduplication
    token_estimate: int

@dataclass(frozen=True)
class HookContext:
    # ... existing fields ...
    tool_results_meta: Tuple[ToolResultMeta, ...]  # NEW: retention tracking
```

### 2. Retention Tracker Utility

New file `hooks/utils/retention_tracker.py`:

```python
class RetentionTracker:
    """Tracks tool results and their retention status."""

    TIER_CONFIG = {
        "ephemeral": {"ttl_tools": 1, "ttl_seconds": None},
        "short": {"ttl_tools": 5, "ttl_seconds": 300},
        "medium": {"ttl_tools": None, "ttl_seconds": None, "expiry_events": ["edit", "commit"]},
        "session": {"ttl_tools": None, "ttl_seconds": None, "expiry_events": ["supersede"]},
        "preserved": {"ttl_tools": None, "ttl_seconds": None, "expiry_events": ["manual"]}
    }

    TOOL_TIERS = {
        "Read": "medium",
        "Grep": "short",
        "Glob": "short",
        "Edit": "ephemeral",
        "Write": "ephemeral",
        "Bash": {
            "default": "session",
            "patterns": {
                "git commit": "ephemeral",
                "git push": "ephemeral",
                "npm test": "session",
                "npm run build": "session",
                "mkdir": "ephemeral",
                "rm": "ephemeral"
            }
        }
    }

    def get_tier(self, tool_name: str, tool_input: Dict) -> str:
        """Determine retention tier for a tool call."""
        ...

    def check_expirations(self, current_index: int, events: List[str]) -> List[str]:
        """Return list of expired content IDs."""
        ...

    def mark_superseded(self, pattern: str):
        """Mark all matching content as superseded."""
        ...
```

### 3. PostToolUse Hook Integration

Extend post-tool-use processing:

```python
# In hooks/post-tool-use.py or new hooks/retention-manager.py

def process_retention(ctx: HookContext, tool_result: str) -> Dict:
    """Process retention for completed tool call."""
    tracker = RetentionTracker.load(ctx.session_id)

    # Assign tier to new result
    tier = tracker.get_tier(ctx.tool_name, ctx.tool_input)
    meta = ToolResultMeta(
        tool_name=ctx.tool_name,
        tool_call_index=tracker.current_index,
        timestamp=datetime.now().isoformat(),
        retention_tier=tier,
        expiry_trigger=tracker.get_expiry_trigger(tier, ctx),
        content_hash=hash_content(tool_result),
        token_estimate=estimate_tokens(tool_result)
    )

    # Check for supersession events
    if ctx.tool_name == "Grep":
        tracker.mark_superseded(f"grep:{ctx.tool_input.get('pattern')}")
    elif ctx.tool_name == "Bash" and "npm test" in ctx.tool_input.get("command", ""):
        tracker.mark_superseded("bash:npm test")

    # Get expired content
    expired = tracker.check_expirations(
        current_index=tracker.current_index,
        events=detect_events(ctx)
    )

    tracker.save()

    return {
        "meta": meta,
        "expired_ids": expired,
        "tokens_reclaimable": sum(tracker.get_tokens(id) for id in expired)
    }
```

### 4. Context Monitor Integration

Extend `hooks/context-monitor.py`:

```python
def check_thresholds(self, model: str = None) -> Dict[str, Any]:
    # ... existing threshold logic ...

    # NEW: Add retention-aware suggestions
    if usage_ratio >= THRESHOLDS["warning"]:
        tracker = RetentionTracker.load(self.session_id)
        expired = tracker.get_all_expired()
        reclaimable = tracker.get_reclaimable_tokens()

        result["retention"] = {
            "expired_count": len(expired),
            "reclaimable_tokens": reclaimable,
            "suggestion": f"Clear {len(expired)} expired items to reclaim ~{reclaimable:,} tokens"
        }
```

### 5. Efficiency Tracker Integration

Update `hooks/utils/efficiency_tracker.py`:

```python
# Add retention metrics
@dataclass
class EfficiencyMetrics:
    # ... existing fields ...

    # Retention metrics
    items_expired: int = 0
    tokens_reclaimed: int = 0
    supersession_events: int = 0
    tier_distribution: Dict[str, int] = field(default_factory=dict)
```

## Configuration

```json
// In power-mode/config.json or hooks/retention-config.json
{
  "retention": {
    "enabled": true,
    "tiers": {
      "ephemeral": {
        "ttl_tools": 1,
        "description": "Immediate acknowledgments"
      },
      "short": {
        "ttl_tools": 5,
        "ttl_seconds": 300,
        "description": "Discovery/search results"
      },
      "medium": {
        "expiry_events": ["edit_file", "commit"],
        "description": "File contents for reference"
      },
      "session": {
        "expiry_events": ["supersede", "session_end"],
        "description": "Test/build output"
      },
      "preserved": {
        "expiry_events": ["manual"],
        "description": "Critical context"
      }
    },
    "tool_overrides": {
      "Read": {
        "tier": "medium",
        "patterns": {
          "*.md": "short",
          "*.json": "medium",
          "*.test.*": "session"
        }
      }
    },
    "preserved_patterns": [
      "error",
      "fail",
      "decision",
      "STATUS.json"
    ]
  }
}
```

## Command Integration

```bash
# View retention status
/popkit:context retention

# Output:
# Retention Status
# ────────────────
# Ephemeral: 0 items (auto-cleared)
# Short: 3 items (12 tool calls until expiry)
# Medium: 5 items (waiting for edit/commit)
# Session: 2 items (npm test, npm build)
# Preserved: 4 items (errors, decisions)
#
# Reclaimable: ~15,000 tokens from 8 expired items
#
# [1] Clear expired  [2] View details  [3] Adjust tiers

# Force clear specific tier
/popkit:context clear --tier short

# Adjust retention for current session
/popkit:context retention --aggressive  # Shorter TTLs
/popkit:context retention --conservative  # Longer TTLs
```

## Implementation Plan

### Phase 1: Retention Tracker Core

1. Create `hooks/utils/retention_tracker.py`
2. Define tier configuration schema
3. Implement TTL and supersession logic
4. Add state persistence

**Files:**
- `hooks/utils/retention_tracker.py` (new)
- `hooks/retention-config.json` (new)

### Phase 2: Hook Integration

1. Extend PostToolUse to track retention
2. Add expiration checking on each tool call
3. Generate clearing suggestions

**Files:**
- `hooks/post-tool-use.py` (modify)
- `hooks/utils/context_carrier.py` (extend)

### Phase 3: Context Monitor Enhancement

1. Add retention data to threshold checks
2. Generate retention-aware suggestions
3. Include in status output

**Files:**
- `hooks/context-monitor.py` (modify)

### Phase 4: Efficiency Metrics

1. Track retention events in efficiency tracker
2. Add to analytics dashboard
3. Calculate token savings from retention

**Files:**
- `hooks/utils/efficiency_tracker.py` (modify)

### Phase 5: Command Interface

1. Add `/popkit:context retention` subcommand
2. Implement clearing commands
3. Add adjustment flags

**Files:**
- `commands/context.md` (new or extend)
- `hooks/utils/flag_parser.py` (extend)

## Acceptance Criteria

- [ ] Retention tracker assigns tiers to all tool results
- [ ] TTL-based expiration works for ephemeral/short tiers
- [ ] Supersession detection works for session tier
- [ ] Edit/commit events expire medium tier content
- [ ] Context monitor shows retention suggestions
- [ ] `/popkit:context retention` command works
- [ ] Efficiency metrics track retention savings
- [ ] Configuration allows tier customization

## Testing

```bash
# Unit tests for retention tracker
python -m pytest tests/hooks/test_retention_tracker.py

# Integration test
python hooks/utils/retention_tracker.py --test

# Simulate session with mixed tool calls
python tests/hooks/retention_integration.py
```

## Metrics to Track

| Metric | Purpose |
|--------|---------|
| Items expired per tier | Validate tier configuration |
| Tokens reclaimed | Measure efficiency gains |
| Supersession events | Validate pattern detection |
| False expirations | Tune TTLs (user had to re-read) |

## Open Questions

1. **How to handle partial file reads?** - If user reads lines 1-100, then 50-150, are they related?
2. **Cross-file dependencies?** - If editing A requires reading B, should B's TTL extend?
3. **User override?** - Should users be able to "pin" content to preserved tier?
4. **Undo support?** - If content expires and user needs it, can we restore?

---

## PopKit Guidance

```yaml
workflow_type: direct
complexity: medium
power_mode: not_needed
phases:
  - implementation (retention tracker core)
  - implementation (hook integration)
  - testing (unit and integration)
  - documentation
agents:
  primary: code-architect
  supporting: test-writer-fixer
quality_gates:
  - python-lint
  - hook-tests
```
