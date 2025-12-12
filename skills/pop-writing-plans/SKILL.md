---
name: writing-plans
description: "Creates comprehensive implementation plans with exact file paths, complete code examples, and verification steps for engineers with zero codebase context. Assumes skilled developers who need domain-specific guidance, following DRY, YAGNI, and TDD principles. Use after brainstorming/design is complete when handing off to another developer or planning complex multi-step work. Do NOT use for simple tasks, quick fixes, or when you're implementing yourself and already understand the codebase - just start coding instead."
inputs:
  - from: pop-brainstorming
    field: design_document
    required: false
  - from: any
    field: topic
    required: false
outputs:
  - field: plan_document
    type: file_path
  - field: github_issue
    type: issue_number
  - field: task_count
    type: number
next_skills:
  - pop-executing-plans
  - pop-subagent-driven
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Step 0: Check Upstream Context

**BEFORE creating a plan**, check for context from previous skills:

```python
from hooks.utils.skill_context import load_skill_context, get_artifact

# Check for design context from brainstorming
ctx = load_skill_context()

if ctx and ctx.previous_skill == "pop-brainstorming":
    # Use design document as input
    design_doc = get_artifact("design_document") or ctx.artifacts.get("design_document")
    topic = ctx.previous_output.get("topic")
    approach = ctx.previous_output.get("approach")

    # Don't re-ask decisions that were already made
    existing_decisions = ctx.shared_decisions

    print(f"Using design from brainstorming: {design_doc}")
    print(f"Topic: {topic}, Approach: {approach}")
else:
    # No upstream context - need to gather information
    # Check for existing design docs
    design_doc = None
```

If design document exists, **read it first** instead of asking questions already answered.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**

\`\`\`python
def test_specific_behavior():
    result = function(input)
    assert result == expected
\`\`\`

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

\`\`\`python
def function(input):
    return expected
\`\`\`

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

\`\`\`bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
\`\`\`
```

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD, frequent commits

## After Plan Created: GitHub Issue

**Check for existing issue or create one:**

```bash
# Search for existing issue
gh issue list --search "<topic>" --state open --json number,title --limit 5
```

**If no issue exists, offer to create:**

```
Use AskUserQuestion tool with:
- question: "No GitHub issue exists for this work. Create one?"
- header: "Issue"
- options:
  - label: "Create issue"
    description: "Create tracking issue with plan summary and task checklist"
  - label: "Link existing"
    description: "I'll provide an issue number to link"
  - label: "Skip"
    description: "Don't track in GitHub"
- multiSelect: false
```

**If creating issue:**

```bash
gh issue create --title "[Feature] <topic>" --body "$(cat <<'EOF'
## Summary
<brief description>

## Implementation Plan
See: `docs/plans/YYYY-MM-DD-<feature>.md`

## Tasks
- [ ] Task 1
- [ ] Task 2
...

---
*Plan created by PopKit*
EOF
)"
```

## Context Output (for downstream skills)

```python
from hooks.utils.skill_context import save_skill_context, SkillOutput, link_workflow_to_issue

# Save plan context for executing-plans or subagent-driven
save_skill_context(SkillOutput(
    skill_name="pop-writing-plans",
    status="completed",
    output={
        "plan_file": "docs/plans/YYYY-MM-DD-<feature>.md",
        "task_count": <number of tasks>,
        "github_issue": <issue number if created>
    },
    artifacts=["docs/plans/YYYY-MM-DD-<feature>.md"],
    next_suggested="pop-executing-plans",
    decisions_made=[<list of AskUserQuestion results>]
))

# Link to GitHub issue
if issue_number:
    link_workflow_to_issue(issue_number)
```

## Execution Handoff

After saving the plan, use AskUserQuestion to offer execution choice:

```
Use AskUserQuestion tool with:
- question: "Plan saved. How would you like to execute it?"
- header: "Execution"
- options:
  - label: "Subagent-Driven"
    description: "Execute in this session with fresh subagent per task"
  - label: "Parallel Session"
    description: "Open new session with executing-plans skill"
  - label: "Later"
    description: "Save for now, I'll execute it manually"
- multiSelect: false
```

**NEVER present as plain text** like "1. Subagent, 2. Parallel... type 1 or 2".

**If Subagent-Driven chosen:**
- Use subagent-driven-development skill
- Stay in this session
- Fresh subagent per task + code review
- Context automatically passed via skill_context

**If Parallel Session chosen:**
- Guide them to open new session in worktree
- New session uses executing-plans skill
- Context available via `.popkit/context/current-workflow.json`
