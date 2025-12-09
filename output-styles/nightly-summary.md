---
name: nightly-summary
description: End of day cleanup and status summary
---

# Nightly Summary Style

## Format

```
┌─────────────────────────────────────────────────────────────┐
│ 🌙 Nightly Summary - [Project Name]                         │
│ [Date] [Time]                                               │
├─────────────────────────────────────────────────────────────┤
│ Sleep Score: [XX/100]                                       │
├─────────────────────────────────────────────────────────────┤
│ Session Summary                                              │
│ Duration: 4h 32m                                            │
│ Commits: 8                                                  │
│ PRs: 1 created, 1 merged                                    │
│ Issues: 2 closed                                            │
├─────────────────────────────────────────────────────────────┤
│ Work Completed                                               │
│ ✓ Implemented user authentication                           │
│ ✓ Added OAuth support                                       │
│ ✓ Fixed login bug (#45)                                     │
├─────────────────────────────────────────────────────────────┤
│ Work In Progress                                             │
│ ⏳ Password reset flow (60%)                                 │
│ ⏳ Email templates (30%)                                     │
├─────────────────────────────────────────────────────────────┤
│ Uncommitted Changes                                          │
│ ⚠ 3 files with uncommitted changes                          │
│   - src/auth/reset.ts                                       │
│   - src/auth/reset.test.ts                                  │
│   - src/templates/reset-email.html                          │
├─────────────────────────────────────────────────────────────┤
│ Cleanup Performed                                            │
│ ✓ Logs rotated (removed 5 old files)                        │
│ ✓ Test artifacts cleaned                                    │
│ ✓ Git maintenance run                                       │
├─────────────────────────────────────────────────────────────┤
│ Tomorrow's Focus                                             │
│ 1. Complete password reset flow                             │
│ 2. Email template styling                                   │
│ 3. Integration testing                                      │
├─────────────────────────────────────────────────────────────┤
│ Safe to Close: [Yes/No]                                     │
│ [Reason if No]                                              │
└─────────────────────────────────────────────────────────────┘
```

## Sleep Score

### Point Breakdown (100 Total)

| Check | Points | Criteria |
|-------|--------|----------|
| No uncommitted changes | 30 | **Critical** - caps score at 49 if fails |
| Session state saved | 20 | STATUS.json updated within last hour |
| Git maintenance done | 15 | No orphans, gc run recently |
| Security audit clean | 15 | No critical/high vulnerabilities |
| Caches under limit | 10 | < 500MB total cache size |
| Logs rotated | 10 | No logs older than 7 days |

### Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 80-100 | Safe to Sleep | Everything is clean, safe to close |
| 60-79 | Minor Cleanup | Recommended cleanup before leaving |
| 40-59 | Cleanup Needed | Should cleanup before leaving |
| 0-39 | Do Not Leave | Uncommitted work or critical issues |

**Note:** Uncommitted changes automatically cap the score at 49.

## Checks Performed

### Session Summary
- Session duration
- Commits made
- PRs created/merged
- Issues closed

### Work Status
- Completed tasks
- In-progress tasks with %
- Blocked tasks

### Uncommitted Changes
- Files modified
- Nature of changes
- Risk assessment

### Cleanup
- Log rotation
- Artifact cleanup
- Cache pruning
- Git maintenance

## Tomorrow's Focus

Generated from:
- In-progress tasks
- STATUS.json nextAction
- Open issues assigned

## Safe to Close

Conditions for "Yes":
- No uncommitted changes
- No running processes that need data
- Session state saved to STATUS.json

Conditions for "No":
- Uncommitted changes exist
- Background processes running
- Unsaved work detected

## Quick Mode Format

One-line summary for `/popkit:nightly quick`:

```
Nightly: 85/100 | Uncommitted (clean) | State (saved) | Caches (234MB) | Security (ok)
Sleep safe - session captured, no blockers
```

Or with issues:

```
Nightly: 42/100 | Uncommitted (3 files!) | State (not saved) | Caches (1.2GB) | Security (2 high)
DO NOT LEAVE - uncommitted changes will be lost
```

## ASCII Dashboard Format (--dashboard)

```
+==================================================================+
|                    Nightly Development Status                     |
+==================================================================+
| Sleep Score: 85/100                                               |
+------------------------------------------------------------------+
| Uncommitted:         Clean                                        |
| Session State:       Saved (30m ago)                              |
| Git Maintenance:     Done                                         |
| Security:            0 critical, 0 high                           |
| Cache Size:          234 MB                                       |
| Old Logs:            0 files                                      |
+------------------------------------------------------------------+
| Tomorrow's Focus:                                                 |
| 1. Complete password reset flow                                   |
| 2. Email template styling                                         |
+==================================================================+
```

## Integration with Morning

The nightly report feeds into the next morning's report:

```
Morning Report - [Project Name]

From Last Night:
  Sleep Score: 85/100
  Session: Saved
  Focus: User authentication

Ready to Code Score: 90/100
...
```
