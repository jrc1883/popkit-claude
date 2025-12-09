---
name: pop-next-action
description: "Context-aware recommendation engine that analyzes git status, TypeScript errors, GitHub issues, and technical debt to suggest prioritized next actions. Returns specific popkit commands with explanations of why each is relevant. Use when unsure what to work on next, starting a session, or feeling stuck. Do NOT use when you already know what to do - just proceed with that task directly."
---

# Next Action Recommendation

## Overview

Analyzes current project state and provides prioritized, context-aware recommendations for what to work on next. Returns actionable popkit commands with explanations.

**Core principle:** Don't just list commands - recommend the RIGHT command based on actual project state.

**Trigger:** When user expresses uncertainty ("what should I do", "where to go", "stuck") or runs `/popkit:next`.

## When to Use

Invoke this skill when:
- User asks "what should I do next?"
- User seems stuck or unsure of direction
- User mentions "popkit" and needs guidance
- Starting a new session and need orientation
- Returning to a project after time away

## Analysis Process

### Step 1: Gather Project State

Collect information from multiple sources:

```bash
# Git status
git status --short 2>/dev/null

# Branch info
git branch -vv 2>/dev/null | head -5

# Recent commits
git log --oneline -5 2>/dev/null

# Check for TypeScript errors (if tsconfig exists)
if [ -f "tsconfig.json" ]; then
  npx tsc --noEmit 2>&1 | tail -10
fi

# Check for package.json (Node project)
if [ -f "package.json" ]; then
  echo "Node project detected"
fi

# Check for TECHNICAL_DEBT.md
if [ -f "TECHNICAL_DEBT.md" ]; then
  head -50 TECHNICAL_DEBT.md
fi

# Check for open GitHub issues
gh issue list --limit 5 2>/dev/null || echo "No gh CLI or not a repo"
```

### Step 2: Detect Project Context

Identify what kind of project and what state it's in:

| Indicator | What It Means | Weight |
|-----------|---------------|--------|
| Uncommitted changes | Active work in progress | HIGH |
| Ahead of remote | Ready to push/PR | MEDIUM |
| TypeScript errors | Build broken | HIGH |
| Open issues | Known work items | MEDIUM |
| **Issue votes** | Community priority | MEDIUM |
| TECHNICAL_DEBT.md | Documented debt | MEDIUM |
| Recent commits | Active development | LOW |

### Step 2.5: Fetch Issue Votes (NEW)

If GitHub issues exist, fetch community votes to prioritize:

```python
from priority_scorer import get_priority_scorer, fetch_open_issues

# Fetch and rank issues by combined priority score
scorer = get_priority_scorer()
issues = fetch_open_issues(limit=10)
ranked = scorer.rank_issues(issues)

# Top-voted issues get recommendation priority
for issue in ranked[:3]:
    # issue.priority_score combines votes, staleness, labels, epic status
    print(f"#{issue.number} {issue.title} - Score: {issue.priority_score}")
```

**Vote Weights:**
- 👍 (+1) = 1 point (community interest)
- ❤️ (heart) = 2 points (strong support)
- 🚀 (rocket) = 3 points (approved/prioritized)
- 👎 (-1) = -1 point (deprioritize)

### Step 3: Score Recommendations

For each potential recommendation, calculate a relevance score:

```
Score = Base Priority + Context Multipliers

Base Priorities:
- Commit uncommitted work: 80
- Fix build errors: 90
- Push ahead commits: 60
- Address open issues: 50
- Tackle tech debt: 40
- Start new feature: 30

Context Multipliers:
- Has uncommitted changes: +20 to commit
- TypeScript errors: +30 to fix
- Many open issues: +10 to issue work
- Long time since commit: +15 to commit
```

### Step 4: Generate Recommendations

Create 3-5 prioritized recommendations based on scores.

For each recommendation, provide:
1. **Command** - The exact popkit command to run
2. **Why** - Context-specific reason (not generic)
3. **What it does** - Brief description
4. **Benefit** - What user gains

## Output Format

Use the `next-action-report` output style:

```markdown
## Current State

| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | X files | [HIGH/MEDIUM/LOW] |
| Branch Sync | [status] | [urgency] |
| TypeScript | [clean/errors] | [urgency] |
| Open Issues | X open | [urgency] |

## Recommended Actions

### 1. [Primary Action] (Score: XX)
**Command:** `/popkit:[command]`
**Why:** [Specific reason based on detected state]
**What it does:** [Brief description]
**Benefit:** [What you gain]

### 2. [Secondary Action] (Score: XX)
...

### 3. [Tertiary Action] (Score: XX)
...

## Quick Reference

| If you want to... | Use this command |
|-------------------|------------------|
| Commit changes | `/popkit:git commit` |
| Review code | `/popkit:git review` |
| Get project health | `/popkit:routine morning` |
| Plan a feature | `/popkit:dev brainstorm` |
| Debug an issue | `/popkit:debug` |

## Alternative Paths

Based on your context, you could also:
- [Alternative 1]
- [Alternative 2]
```

## Recommendation Logic

### If Uncommitted Changes Detected

```markdown
### 1. Commit Your Current Work
**Command:** `/popkit:commit`
**Why:** You have [X] uncommitted files including [key files]
**What it does:** Auto-generates commit message matching repo style
**Benefit:** Clean working directory, changes safely versioned
```

### If TypeScript Errors

```markdown
### 1. Fix Build Errors
**Command:** `/popkit:debug`
**Why:** TypeScript has [X] errors blocking build
**What it does:** Systematic debugging with root cause analysis
**Benefit:** Unblocked development, passing CI
```

### If Open Issues Exist

```markdown
### 2. Work on Open Issue
**Command:** `/popkit:dev work #[number]`
**Why:** Issue #[X] "[title]" is high priority (Score: XX)
**Votes:** 👍5 ❤️2 🚀1
**What it does:** Issue-driven development workflow
**Benefit:** Structured progress on community-prioritized work
```

When multiple issues exist, use priority scoring to recommend the best one:

```python
from priority_scorer import get_priority_scorer

scorer = get_priority_scorer()
ranked = scorer.rank_issues(issues)

# Recommend highest-scored issue
top = ranked[0]
print(f"Work on #{top.number} '{top.title}' (Score: {top.priority_score:.1f})")
if top.vote_breakdown:
    print(f"Community votes: {scorer.vote_fetcher.format_vote_display(top, compact=True)}")
```

### If No Urgent Items

```markdown
### 1. Check Project Health
**Command:** `/popkit:routine morning`
**Why:** No urgent items - good time for health check
**What it does:** Comprehensive project status with "Ready to Code" score
**Benefit:** Identify hidden issues before they become urgent
```

## Quick Mode

When called with `quick` argument, provide condensed output:

```markdown
## /popkit:next (quick)

**State:** 5 uncommitted | branch synced | TS clean | 3 issues

**Top 3:**
1. `/popkit:git commit` - Commit 5 files (HIGH)
2. `/popkit:dev work #42` - Work on "Add auth" (MEDIUM)
3. `/popkit:routine morning` - Health check (LOW)
```

## Error Handling

| Situation | Response |
|-----------|----------|
| Not a git repo | Note it, skip git-based recommendations |
| No package.json | Skip Node-specific checks |
| gh CLI not available | Skip issue recommendations |
| Empty project | Recommend `/popkit:project init` |

## Related

- `/popkit:next` command - User-facing wrapper
- `/popkit:routine morning` - Detailed health check
- `/popkit:dev brainstorm` - For when direction is truly unclear
- `user-prompt-submit.py` - Uncertainty trigger patterns
- `hooks/utils/vote_fetcher.py` - GitHub reaction fetching
- `hooks/utils/priority_scorer.py` - Combined priority calculation
