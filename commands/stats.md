# /popkit:stats - Efficiency Metrics

Display PopKit efficiency metrics showing token savings, collaboration stats, and overall value.

## Usage

```
/popkit:stats [subcommand] [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| (default) | Show current session stats |
| `session` | Current session efficiency (default) |
| `today` | Today's aggregate stats |
| `week` | Last 7 days summary |
| `cloud` | Fetch stats from PopKit Cloud |
| `reset` | Reset session metrics |

## Options

| Option | Description |
|--------|-------------|
| `--compact` | One-line summary for scripts |
| `--json` | Output as JSON |
| `--detailed` | Show full breakdown |

---

## Examples

### Default (Current Session)
```
/popkit:stats
```

Output:
```
+==================================================================+
|                     Session Efficiency Report                     |
+==================================================================+
| Tokens Saved: ~2,450                                              |
| Efficiency Score: 73/100                                          |
+------------------------------------------------------------------+
| Token Savings Breakdown:                                          |
|   Duplicates skipped: 8 (~800 tokens)                             |
|   Pattern matches: 2 (~1,000 tokens)                              |
|   Context reuse: 3 (~600 tokens)                                  |
|   Bug detection: 0 (~0 tokens)                                    |
+------------------------------------------------------------------+
| Collaboration:                                                    |
|   Insights shared: 12                                             |
|   Insights received: 5                                            |
|   Insight efficiency: 42%                                         |
+------------------------------------------------------------------+
| Session Stats:                                                    |
|   Tool calls: 47                                                  |
|   Session started: 2 hours ago                                    |
+==================================================================+
```

### Compact Mode
```
/popkit:stats --compact
```

Output:
```
~2.4k tokens saved | 73% efficient | 8 dedup, 2 patterns
```

### Weekly Summary
```
/popkit:stats week
```

Output:
```
+==================================================================+
|                   Weekly Efficiency Summary                       |
+==================================================================+
| Period: Dec 1 - Dec 7, 2025                                       |
+------------------------------------------------------------------+
| Total Tokens Saved: ~18,750                                       |
| Total Sessions: 23                                                |
| Avg Tokens/Session: ~815                                          |
+------------------------------------------------------------------+
| Highlights:                                                       |
|   Best day: Dec 5 (5,200 tokens saved)                            |
|   Most patterns: Dec 3 (7 matches)                                |
|   Total duplicates prevented: 42                                  |
+------------------------------------------------------------------+
| Agent Usage (Top 5):                                              |
|   code-reviewer: 34 invocations                                   |
|   bug-whisperer: 12 invocations                                   |
|   test-writer-fixer: 8 invocations                                |
|   api-designer: 5 invocations                                     |
|   security-auditor: 3 invocations                                 |
+==================================================================+
```

### Cloud Stats (Requires API Key)
```
/popkit:stats cloud
```

Output:
```
PopKit Cloud Analytics
----------------------
Account: joseph@example.com
Tier: Pro

This Month:
  Sessions: 87
  Tokens Saved: ~45,000
  Patterns Contributed: 12
  Patterns Used: 34

Collective Learning:
  Total Patterns: 1,247
  Your Contributions: 12 (0.96%)
  Patterns Matched: 34 (2.73%)
```

### JSON Output
```
/popkit:stats --json
```

Output:
```json
{
  "session_id": "abc12345",
  "started_at": "2025-12-05T10:30:00Z",
  "tokens_estimated_saved": 2450,
  "efficiency_score": 73,
  "duplicates_skipped": 8,
  "patterns_matched": 2,
  "insights_shared": 12,
  "insights_received": 5,
  "tool_calls": 47
}
```

---

## Executable Commands

### Session Stats (Default)

```python
# Load efficiency tracker
from hooks.utils.efficiency_tracker import get_tracker

tracker = get_tracker()
summary = tracker.get_summary()

# Display formatted output
print(format_efficiency_summary(summary))
```

### Cloud Stats

```bash
# Fetch from PopKit Cloud (requires POPKIT_API_KEY)
curl -H "Authorization: Bearer $POPKIT_API_KEY" \
  "https://popkit-cloud-api.joseph-cannon.workers.dev/v1/analytics/overview?days=7"
```

### Reset Session

```python
from hooks.utils.efficiency_tracker import get_tracker

tracker = get_tracker()
tracker.reset()
print("Session metrics reset")
```

---

## Token Estimation

PopKit estimates token savings using these constants:

| Event | Est. Tokens Saved | Reasoning |
|-------|-------------------|-----------|
| Duplicate skipped | 100 | Insight not reprocessed |
| Pattern matched | 500 | Avoided debugging time |
| Context reuse | 200 | Semantic vs brute force |
| Bug detected | 300 | Early detection savings |
| Stuck prevented | 800 | Avoided loop iterations |

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Efficiency Tracker | `hooks/utils/efficiency_tracker.py` |
| Check-in Hook | `power-mode/checkin-hook.py` |
| Cloud API | `cloud-api/src/routes/analytics.ts` |
| Output Style | `output-styles/efficiency-summary.md` |
| Status Line | `power-mode/statusline.py` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:power status` | Power Mode status (includes efficiency) |
| `/popkit:routine morning` | Morning report includes efficiency |
| `/popkit:routine nightly` | Nightly report includes efficiency |
