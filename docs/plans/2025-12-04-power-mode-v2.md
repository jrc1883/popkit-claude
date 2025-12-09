# Power Mode v2 Implementation Plan

**Created:** 2025-12-04
**Status:** Planning
**Priority:** High

## Goals

Based on brainstorming session, Power Mode v2 should:
1. **Auto-activate** based on task complexity, issue type, and phase
2. **Integrate seamlessly** via `-p` flag and auto-detection
3. **Provide visibility** through status line, dashboard URL, and log file

## Current State Analysis

### What's Working
- Redis check-in at 5-tool intervals
- Agent state pushed to Redis (`pop:state:{agent-id}`)
- Insight extraction and sharing via `pop:insights` list
- Redis Commander at http://localhost:18081
- File-based fallback for development

### Issues Found
| Issue | Description | Fix |
|-------|-------------|-----|
| State file location | Uses `Path.cwd()/.claude` which varies | Use project root detection |
| Session ID mismatch | State resets on mismatch | Auto-generate from git commit hash |
| No heartbeat subscribers | `pop:heartbeat` channel unused | Add coordinator subscription |
| None serialization | Python None → string "None" | Use JSON null properly |

## Phase 1: Bug Fixes (Week 1)

### 1.1 Fix State File Location
```python
def _get_project_root() -> Optional[Path]:
    """Find project root by looking for .claude/ or .git/"""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".claude").is_dir():
            return parent
        if (parent / ".git").is_dir():
            return parent
    return None
```

### 1.2 Fix Session ID Generation
```python
def _generate_session_id() -> str:
    """Generate session ID from git HEAD + timestamp"""
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True
        ).strip()
        return f"{git_hash}-{datetime.now().strftime('%H%M')}"
    except:
        return f"session-{datetime.now().strftime('%Y%m%d-%H%M')}"
```

### 1.3 Fix JSON Serialization
```python
# In push_state():
self.redis.hset(key, mapping={
    k: json.dumps(v) if v is not None else "null"
    for k, v in state.items()
})
```

## Phase 2: Visibility Enhancements (Week 2)

### 2.1 Dashboard URL in Status Line
Add to `statusline.py`:
```python
def format_status_line(state: dict) -> str:
    parts = [
        f"[POP] #{state.get('active_issue', 'N/A')}",
        f"Phase: {state.get('current_phase', 'init')}",
        f"({state.get('phase_index', 0)}/{state.get('total_phases', 0)})",
        f"Dashboard: http://localhost:18081"
    ]
    return " ".join(parts)
```

### 2.2 Log File
Create `power-mode/logs/session-{id}.log`:
```
[2025-12-04T20:30:00] STARTED session-abc123
[2025-12-04T20:30:05] AGENT code-reviewer joined
[2025-12-04T20:30:10] CHECKIN agent-001 tools=5 files=3
[2025-12-04T20:30:15] INSIGHT shared: "Tests at src/auth/"
```

### 2.3 Enhanced Status Command
```
/popkit:power status

=== Power Mode Status ===

Mode: ACTIVE (Redis)
Session: abc123-1430
Started: 2 minutes ago

Agents (2):
  - code-reviewer (5 tools, last check-in: 10s ago)
  - test-writer (3 tools, last check-in: 25s ago)

Phase: implement (2/5)
Progress: ████████░░ 40%

Visibility:
  - Dashboard: http://localhost:18081
  - Log: ~/.claude/power-mode/logs/abc123-1430.log

Recent Insights:
  - Tests at: src/auth/ (from test-writer)
  - Config pattern: .env.local (from code-reviewer)
```

## Phase 3: Auto-Activation (Week 3)

### 3.1 Activation Triggers

| Trigger | Detection | Action |
|---------|-----------|--------|
| Epic issue | `labels: ["epic"]` | Auto-enable with 4+ agents |
| Complex task | `>3 files mentioned` | Suggest Power Mode |
| Implementation phase | Phase 4+ in feature-dev | Enable if 2+ agents needed |
| Explicit flag | `-p` or `--power` | Force enable |

### 3.2 Auto-Detection in Commands
```python
# In command preprocessing hook
def should_suggest_power_mode(task: str, context: dict) -> bool:
    indicators = [
        len(context.get("files_mentioned", [])) > 3,
        "epic" in context.get("labels", []),
        "refactor" in task.lower(),
        "migrate" in task.lower(),
    ]
    return sum(indicators) >= 2
```

### 3.3 Phase-Aware Activation
```python
PHASE_POWER_RECOMMENDATIONS = {
    "explore": False,      # Single agent explores
    "design": False,       # Architect designs alone
    "implement": True,     # Multiple agents can parallelize
    "test": True,          # Test writer + code reviewer
    "document": False,     # Single agent documents
    "review": True,        # Multiple reviewers possible
}
```

## Phase 4: Integration Improvements (Week 4)

### 4.1 `-p` Flag on All Commands
Add to `hooks/utils/flag_parser.py`:
```python
def parse_power_flag(args: List[str]) -> Tuple[bool, List[str]]:
    """Extract -p/--power flag from arguments."""
    power = "-p" in args or "--power" in args
    remaining = [a for a in args if a not in ["-p", "--power"]]
    return power, remaining
```

### 4.2 Command Integration
```markdown
# /popkit:dev with Power Mode

Usage:
  /popkit:dev full -p           # Force Power Mode
  /popkit:dev work #42 -p       # Issue work with Power Mode
  /popkit:dev execute plan.md -p # Execute plan in parallel
```

### 4.3 Init-Time Setup
Add to `/popkit:project init`:
```
? Enable Power Mode for this project? (y/n)
  - Redis (recommended for teams)
  - File-based (single developer)
  - Skip
```

## File Changes Summary

| File | Change |
|------|--------|
| `power-mode/checkin-hook.py` | Fix state file location, session ID, serialization |
| `power-mode/statusline.py` | Add dashboard URL, enhanced status |
| `power-mode/logger.py` | NEW - Session logging |
| `commands/power.md` | Enhanced status command |
| `hooks/utils/flag_parser.py` | Add power flag parsing |
| `hooks/utils/power_detector.py` | NEW - Auto-activation logic |
| `commands/dev.md` | Add `-p` flag support |
| `commands/project.md` | Add Power Mode init option |

## Success Metrics

1. **Visibility**: User can see Power Mode activity in 3 places
2. **Automation**: 80% of Power Mode-appropriate tasks auto-suggest it
3. **Integration**: `-p` flag works on all relevant commands
4. **Reliability**: State persists correctly across sessions

## Next Steps

1. [ ] Fix checkin-hook.py bugs (Phase 1)
2. [ ] Add log file support
3. [ ] Enhance status command
4. [ ] Implement auto-detection triggers
5. [ ] Add `-p` flag to dev command
