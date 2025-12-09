---
name: code-review
description: "Confidence-based code review that filters issues to 80+ threshold, eliminating false positives and noise. Reviews implementation against plan or requirements for bugs, quality issues, and project conventions. Use after completing major features, before merging to main, or after each task in multi-step workflows. Do NOT use for quick fixes, single-line changes, or when you need immediate feedback - the thorough review adds overhead best reserved for significant changes."
---

# Code Review with Confidence Filtering

## Overview

Review code for bugs, quality issues, and project conventions with confidence-based filtering. Only reports HIGH confidence issues to reduce noise.

**Core principle:** Review early, review often. Filter out false positives.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## Confidence Scoring

Each identified issue receives a confidence score (0-100):

| Score | Meaning | Action |
|-------|---------|--------|
| 0 | Not a real problem | Ignore |
| 25 | Possibly valid | Ignore |
| 50 | Moderately confident | Note for reference |
| 75 | Highly confident | Report |
| 100 | Absolutely certain | Report as critical |

**Threshold: 80+** - Only issues scoring 80 or higher are reported.

## Filter Out

- Pre-existing problems (not introduced in this change)
- Linter-catchable issues (let the linter handle it)
- Pedantic nitpicks (style preferences without substance)
- Hypothetical edge cases (unlikely to occur in practice)

## Review Categories

### 1. Simplicity/DRY/Elegance
- Code duplication
- Unnecessary complexity
- Missed abstractions
- Overly clever code

### 2. Bugs/Correctness
- Logic errors
- Edge case handling
- Type safety issues
- Error handling gaps

### 3. Conventions/Abstractions
- Project pattern compliance
- Naming conventions
- File organization
- Import patterns

## Output Format

```markdown
## Code Review: [Feature/PR Name]

### Summary
[1-2 sentences on overall quality]

### Critical Issues (Must Fix)
_Issues with confidence 90+_

#### Issue 1: [Title]
- **File**: `path/to/file.ts:line`
- **Confidence**: 95/100
- **Category**: Bug/Correctness
- **Description**: What's wrong
- **Fix**: How to fix it

### Important Issues (Should Fix)
_Issues with confidence 80-89_

#### Issue 2: [Title]
- **File**: `path/to/file.ts:line`
- **Confidence**: 82/100
- **Category**: Conventions
- **Description**: What's wrong
- **Fix**: How to fix it

### Assessment

**Ready to merge?** Yes / No / With fixes

**Reasoning**: [1-2 sentences explaining the assessment]

### Quality Score: [X/10]
```

## How to Request Review

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code-reviewer subagent:**
- What was implemented
- Plan or requirements reference
- Base and head commits
- Brief description

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Parallel Review

Launch 3 code-reviewer agents in parallel with different focuses:
1. **Simplicity Focus**: DRY, elegance, unnecessary complexity
2. **Correctness Focus**: Bugs, edge cases, error handling
3. **Conventions Focus**: Project patterns, naming, organization

Consolidate findings and filter by confidence threshold.

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

## Key Principle

"Ask what you want to do" - After presenting issues, ask the user how to proceed rather than making assumptions.

---

## Receiving Code Review Feedback

This section covers how to **respond** to review feedback, not how to give it.

### The Process

```
Feedback Received → Read ALL → Verify → Evaluate → Implement → Respond
```

**Step 1: Read ALL Comments Before Implementing ANY**

Items may be related. Partial understanding = wrong implementation.

- Read every comment completely
- Note dependencies between suggestions
- Understand the reviewer's overall intent
- Don't react until you've read everything

**Step 2: Verify Against Actual Code**

Don't assume the reviewer is right. Check:

```
For each suggestion:
  - Does this code path actually exist?
  - Does the suggested fix compile/work?
  - Will it break existing functionality?
  - Is the edge case real or hypothetical?
```

**Step 3: Evaluate Technical Soundness**

Push back on technically questionable suggestions:

| Reviewer Says | Your Response |
|---------------|---------------|
| "This could fail if..." (hypothetical) | "Is this edge case actually reachable? Show me the path." |
| "Use pattern X instead" | "Does X fit our architecture? What's the trade-off?" |
| "This is inefficient" | "Is this a hot path? Premature optimization?" |
| "Add validation for Y" | "Is Y possible given our type system?" |

**Disagree with technical reasoning, not emotion.** If you're right, show evidence.

**Step 4: Implement Strategically**

Order matters:

1. **Blocking issues first** - Things that prevent merge
2. **Simple fixes next** - Quick wins to show progress
3. **Complex refactoring last** - Needs more thought

**One commit per logical change.** Makes it easier for re-review.

**Step 5: Respond to Each Comment**

| Situation | Response |
|-----------|----------|
| Fixed the issue | "Fixed in [commit]" or just resolve the comment |
| Disagree | Technical reasoning why, ask for their perspective |
| Need clarification | Ask specific question, don't guess |
| Won't fix | Explain why (tech debt ticket? out of scope?) |

### What NOT to Do

**Performative Agreement:**
```
BAD: "Great point! You're absolutely right! I'll fix that immediately!"
GOOD: "Fixed" or "Good catch" or just the fix itself
```

Actions demonstrate engagement better than words.

**Blind Implementation:**
```
BAD: Immediately implementing every suggestion without verification
GOOD: Verify suggestion makes sense for YOUR codebase, then implement
```

**Defensive Reactions:**
```
BAD: "Well actually, I wrote it this way because..."
GOOD: "Here's why I chose this approach: [technical reason]. Does that change your recommendation?"
```

### When Reviewer is Wrong

It happens. Handle professionally:

1. **Verify you understand** - Restate their concern
2. **Show evidence** - Code, tests, docs that support your approach
3. **Offer alternative** - "Would X address your concern while keeping Y?"
4. **Escalate if needed** - Get another opinion

Don't:
- Silently ignore feedback
- Implement something you know is wrong
- Get emotional or defensive

### Red Flags in Your Own Behavior

Stop if you're:
- Implementing without understanding
- Agreeing to avoid conflict
- Skipping comments you don't like
- Getting frustrated at reviewer
- Thinking "they don't understand the code"

---

## Cross-References

- **Testing feedback:** Review tests as rigorously as code (see `pop-test-driven-development`)
- **Debugging from feedback:** If review reveals bug, use `pop-systematic-debugging`
- **Root cause:** Don't just fix symptoms reviewer points out, trace to root cause
