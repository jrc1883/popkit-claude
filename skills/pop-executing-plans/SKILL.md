---
name: executing-plans
description: "Controlled batch execution of implementation plans with review checkpoints between phases. Loads plan, critically reviews for issues, executes tasks in batches, then pauses for architect feedback before continuing. Use when you have a complete implementation plan from brainstorming/writing-plans and want structured execution with quality gates. Do NOT use for ad-hoc implementation, exploratory coding, or when you don't have a formal plan - just implement directly with code review at the end."
---

# Executing Plans

## Overview

Load plan, review critically, execute tasks in batches, report for review between batches.

**Core principle:** Batch execution with checkpoints for architect review.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Batch
**Default: First 3 tasks**

For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Report
When batch complete:
- Show what was implemented
- Show verification output
- Use AskUserQuestion for feedback:

```
Use AskUserQuestion tool with:
- question: "Batch complete. How should I proceed?"
- header: "Feedback"
- options:
  - label: "Continue"
    description: "Looks good, proceed to next batch"
  - label: "Revise"
    description: "I have feedback on this batch first"
  - label: "Pause"
    description: "Stop here, I'll review more carefully"
- multiSelect: false
```

### Step 4: Continue
Based on selection:
- **Continue**: Execute next batch
- **Revise**: Wait for feedback, apply changes, then continue
- **Pause**: Stop execution, preserve progress

### Step 5: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- Use finishing-a-development-branch skill
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker mid-batch (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## PDF Input Support

Plans can be provided as PDF files:

```
User: Execute this plan: /path/to/implementation-plan.pdf
```

**Process PDF plans:**
1. Use Read tool to analyze the PDF content
2. Extract tasks, steps, and verification criteria
3. Convert to internal task list format
4. Proceed with standard execution process

**When reading plan PDFs:**
- Look for: numbered tasks, code blocks, file paths
- Extract: exact commands, expected outputs
- Note: dependencies between tasks
- Identify: verification steps for each phase

PRD PDFs can also be processed to understand requirements context before execution.

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Between batches: just report and wait
- Stop when blocked, don't guess
