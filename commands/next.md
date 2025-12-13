---
description: "[quick|verbose] - Analyze project state and recommend next actions"
argument-hint: "[quick|verbose]"
---

# /popkit:next

Analyzes current project state and recommends specific popkit commands based on what actually needs attention.

## Usage

```bash
/popkit:next                # Full analysis with recommendations
/popkit:next quick          # Condensed output
/popkit:next verbose        # Include all context sources
```

## Architecture Integration

| Component | Role |
|-----------|------|
| **Skill** | `pop-next-action` - Core analysis and recommendation logic |
| **Output Style** | `next-action-report` - Standardized output format |
| **Hook** | `user-prompt-submit.py` - Uncertainty trigger detection |
| **Related** | `/popkit:morning` - Shares state analysis |

## Instructions

You are the context-aware recommendation engine. Invoke the `pop-next-action` skill to analyze and recommend.

### Step 0: Parse Arguments

- No args → Full analysis mode
- `quick` → Condensed output
- `verbose` → Include raw context data

### Step 1: Invoke Skill

Use the `pop-next-action` skill following its analysis process:
1. Gather project state (git, TypeScript, issues, etc.)
2. Detect project context
3. Score recommendations
4. Generate prioritized actions

### Step 2: Format Output

Use the `next-action-report` output style for consistent formatting.

**Full Mode Output:**
```
## Current State

| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | 5 files | HIGH |
| Branch Sync | 2 ahead | MEDIUM |
| TypeScript | Clean | OK |
| Open Issues | 3 open | MEDIUM |

## Recommended Actions

### 1. Commit Your Current Work
**Command:** `/popkit:git commit`
**Why:** You have 5 uncommitted files including auth.ts and routes/
**What it does:** Auto-generates commit message matching repo style
**Benefit:** Clean working directory, changes safely versioned

### 2. Push to Remote
**Command:** `/popkit:git push` or `/popkit:git pr`
**Why:** Branch is 2 commits ahead of origin
**What it does:** Syncs local work to remote
**Benefit:** Backup, collaboration, CI triggers

### 3. Review Open Issue #42
**Command:** `/popkit:issue view 42` then `/popkit:feature-dev`
**Why:** "Add user authentication" is high priority
**What it does:** 7-phase feature workflow
**Benefit:** Structured progress on known work

## Quick Reference

| If you want to... | Use this command |
|-------------------|------------------|
| Commit changes | `/popkit:git commit` |
| Review code | `/popkit:git review` |
| Get project health | `/popkit:morning` |
| Plan a feature | `/popkit:design` |
| Debug an issue | `/popkit:debug` |
```

**Quick Mode Output:**
```
## /popkit:next (quick)

**State:** 5 uncommitted | 2 ahead | TS clean | 3 issues

**Top 3:**
1. `/popkit:commit` - Commit 5 files (HIGH)
2. `/popkit:commit-push-pr` - Push 2 commits (MEDIUM)
3. `/popkit:issue view 42` - Work on auth (MEDIUM)
```

---

## Context Sources

The skill checks these sources (when available):

| Source | What We Learn |
|--------|---------------|
| `git status` | Uncommitted changes, staging state |
| `git branch -vv` | Ahead/behind remote, current branch |
| `git log --oneline -5` | Recent activity |
| `npx tsc --noEmit` | TypeScript health (if tsconfig exists) |
| `gh issue list` | Open issues (if gh CLI available) |
| `TECHNICAL_DEBT.md` | Known debt items |
| `STATUS.json` | Previous session context |

---

## Recommendation Priority

| Priority | Condition | Why |
|----------|-----------|-----|
| 1 (Highest) | TypeScript errors | Blocks all development |
| 2 | Uncommitted changes | Risk of lost work |
| 3 | Ahead of remote | Share work with team |
| 4 | Open HIGH issues | Known important work |
| 5 | Technical debt | Preventative maintenance |
| 6 | No urgent items | Health check or exploration |

---

## Examples

### Example 1: Active Development
```
User: "what should I do next?"

## Current State
| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | 8 files | HIGH |
| TypeScript | 2 errors | HIGH |

## Recommended Actions

### 1. Fix TypeScript Errors
**Command:** `/popkit:debug`
**Why:** 2 TypeScript errors blocking build
...
```

### Example 2: Clean State
```
User: "/popkit:next"

## Current State
| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | 0 files | OK |
| TypeScript | Clean | OK |
| Open Issues | 5 open | MEDIUM |

## Recommended Actions

### 1. Work on Open Issue
**Command:** `/popkit:issue view 12`
**Why:** Issue #12 "Add dark mode" is high priority
...
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| Not a git repo | Skip git analysis, note in output |
| No package.json | Skip Node checks |
| gh CLI unavailable | Skip issue recommendations |
| Empty project | Recommend `/popkit:init-project` |
| All green | Recommend exploration or new feature |

---

## Related Commands

- `/popkit:morning` - Full health check with "Ready to Code" score
- `/popkit:brainstorm` - When you need to explore ideas
- `/popkit:feature-dev` - Start working on a feature
- `/popkit:debug` - Systematic debugging
- `/popkit:commit` - Commit current work
