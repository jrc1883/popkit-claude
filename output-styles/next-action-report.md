---
name: next-action-report
description: Standardized format for context-aware next action recommendations
---

# Output Style: Next Action Report

## Purpose

Provides a consistent, actionable format for presenting context-aware recommendations from `/popkit:next`.

## Full Format

```markdown
+------------------------------------------------------------------+
|  POPKIT NEXT - Context-Aware Recommendations                      |
|  Project: [name] | Branch: [branch] | [timestamp]                |
+------------------------------------------------------------------+

## Current State

| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | [X files / None] | [HIGH/MEDIUM/LOW/OK] |
| Branch Sync | [X ahead/behind / Synced] | [HIGH/MEDIUM/LOW/OK] |
| TypeScript | [X errors / Clean] | [HIGH/MEDIUM/LOW/OK] |
| Open Issues | [X open / None] | [HIGH/MEDIUM/LOW/OK] |
| Technical Debt | [X HIGH items / None] | [HIGH/MEDIUM/LOW/OK] |

## Recommended Actions

### 1. [Primary Recommendation]
**Command:** `/popkit:[command]`
**Why:** [Context-specific reason based on detected state]
**What it does:** [Brief description of command behavior]
**Benefit:** [What user gains from this action]

### 2. [Secondary Recommendation]
**Command:** `/popkit:[command]`
**Why:** [Context-specific reason]
**What it does:** [Brief description]
**Benefit:** [User benefit]

### 3. [Tertiary Recommendation]
**Command:** `/popkit:[command]`
**Why:** [Context-specific reason]
**What it does:** [Brief description]
**Benefit:** [User benefit]

## Quick Reference

| If you want to... | Use this command |
|-------------------|------------------|
| Commit current changes | `/popkit:commit` |
| Review before committing | `/popkit:review` |
| Get project health score | `/popkit:morning` |
| Brainstorm next direction | `/popkit:brainstorm` |
| Start feature development | `/popkit:feature-dev` |
| Debug an issue | `/popkit:debug` |
| Work on a GitHub issue | `/popkit:issue` |

## Alternative Paths

Based on your context, you could also:
- [Alternative action 1 with brief explanation]
- [Alternative action 2 with brief explanation]
- [Alternative action 3 with brief explanation]
```

## Quick Format

For condensed output (when `quick` argument is used):

```markdown
## /popkit:next (quick)

**State:** [X] uncommitted | [branch status] | [TS status] | [X] issues

**Top 3:**
1. `/popkit:[cmd]` - [brief reason] ([urgency])
2. `/popkit:[cmd]` - [brief reason] ([urgency])
3. `/popkit:[cmd]` - [brief reason] ([urgency])
```

## Urgency Indicators

| Urgency | When to Use | Color Hint |
|---------|-------------|------------|
| HIGH | Blocks development (errors, uncommitted critical files) | Red |
| MEDIUM | Should address soon (ahead of remote, open issues) | Yellow |
| LOW | Nice to have (tech debt, optimizations) | Blue |
| OK | No action needed | Green |

## Example: Active Development

```markdown
+------------------------------------------------------------------+
|  POPKIT NEXT - Context-Aware Recommendations                      |
|  Project: genesis | Branch: main | 2025-11-29 15:30              |
+------------------------------------------------------------------+

## Current State

| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | 8 files | HIGH |
| Branch Sync | 3 ahead | MEDIUM |
| TypeScript | Clean | OK |
| Open Issues | 5 open | MEDIUM |
| Technical Debt | 2 HIGH items | MEDIUM |

## Recommended Actions

### 1. Commit Your Current Work
**Command:** `/popkit:commit`
**Why:** You have 8 uncommitted files including auth.ts and dashboard components
**What it does:** Auto-generates commit message matching conventional commit style
**Benefit:** Clean working directory, changes safely versioned, ready to share

### 2. Push and Create PR
**Command:** `/popkit:commit-push-pr`
**Why:** Branch is 3 commits ahead of origin/main
**What it does:** Stages, commits, pushes, and creates pull request
**Benefit:** Team visibility, CI triggers, code review

### 3. Address High-Priority Issue
**Command:** `/popkit:issue view 42` then `/popkit:feature-dev`
**Why:** Issue #42 "Add OAuth refresh" has HIGH priority label
**What it does:** 7-phase feature workflow with code review
**Benefit:** Structured progress on critical functionality

## Quick Reference

| If you want to... | Use this command |
|-------------------|------------------|
| Commit current changes | `/popkit:commit` |
| Review before committing | `/popkit:review` |
| Get project health score | `/popkit:morning` |
| Brainstorm next direction | `/popkit:brainstorm` |

## Alternative Paths

Based on your context, you could also:
- Run `/popkit:review` to check code quality before committing
- Use `/popkit:morning` to get a full health check with Ready to Code score
- Try `/popkit:sync` to validate popkit plugin state
```

## Example: Clean State

```markdown
+------------------------------------------------------------------+
|  POPKIT NEXT - Context-Aware Recommendations                      |
|  Project: reseller-central | Branch: master | 2025-11-29 10:00   |
+------------------------------------------------------------------+

## Current State

| Indicator | Status | Urgency |
|-----------|--------|---------|
| Uncommitted | None | OK |
| Branch Sync | Synced | OK |
| TypeScript | Clean | OK |
| Open Issues | 3 open | MEDIUM |
| Technical Debt | 1 MEDIUM item | LOW |

## Recommended Actions

### 1. Check Project Health
**Command:** `/popkit:morning`
**Why:** No urgent items - good time for a comprehensive health check
**What it does:** Analyzes git, tests, lint, dependencies, generates "Ready to Code" score
**Benefit:** Identify hidden issues before they become urgent

### 2. Work on Open Issue
**Command:** `/popkit:issue view 15`
**Why:** Issue #15 "Improve error handling" is medium priority
**What it does:** View issue details, optionally start feature workflow
**Benefit:** Chip away at backlog

### 3. Brainstorm New Feature
**Command:** `/popkit:brainstorm`
**Why:** Clean state is ideal for exploration
**What it does:** Socratic questioning to refine ideas into designs
**Benefit:** Well-thought-out feature before coding

## Alternative Paths

Based on your context, you could also:
- Review TECHNICAL_DEBT.md and tackle a debt item
- Run `/popkit:sync` to validate plugin integrity
- Use `/popkit:feature-dev` if you have a feature in mind
```

## Schema

```json
{
  "type": "next-action-report",
  "sections": {
    "header": {
      "project": "string",
      "branch": "string",
      "timestamp": "ISO8601"
    },
    "currentState": {
      "indicators": [
        {
          "name": "string",
          "status": "string",
          "urgency": "HIGH | MEDIUM | LOW | OK"
        }
      ]
    },
    "recommendations": [
      {
        "rank": "number",
        "title": "string",
        "command": "string",
        "why": "string",
        "whatItDoes": "string",
        "benefit": "string"
      }
    ],
    "quickReference": [
      {
        "want": "string",
        "command": "string"
      }
    ],
    "alternatives": ["string"]
  }
}
```

## Related

- `/popkit:next` - Command that uses this style
- `pop-next-action` - Skill that generates content
- `/popkit:morning` - Uses similar state analysis
