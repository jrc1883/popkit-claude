---
name: finishing-a-development-branch
description: "Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup. Presents exactly 4 options: merge locally, create PR, keep as-is, or discard. Do NOT use when tests are failing or work is incomplete - fix issues first before finishing the branch."
inputs:
  - from: pop-executing-plans
    field: tasks_completed
    required: false
  - from: pop-code-review
    field: merge_ready
    required: false
outputs:
  - field: completion_type
    type: string
  - field: pr_url
    type: string
  - field: issue_closed
    type: boolean
next_skills:
  - pop-session-capture
  - pop-using-git-worktrees
workflow:
  id: finish-branch
  name: Branch Completion Workflow
  version: 1
  description: Structured branch completion with verification
  steps:
    - id: verify_tests
      description: Run test suite to verify code works
      type: agent
      agent: test-writer-fixer
      next: test_result
    - id: test_result
      description: Evaluate test results
      type: user_decision
      question: "Test results?"
      header: "Tests"
      options:
        - id: passing
          label: "All passing"
          description: "Tests pass, ready to proceed"
          next: determine_base
        - id: failing
          label: "Some failing"
          description: "Tests fail, need to fix"
          next: fix_tests
        - id: no_tests
          label: "No tests"
          description: "No tests exist for this code"
          next: add_tests_decision
      next_map:
        passing: determine_base
        failing: fix_tests
        no_tests: add_tests_decision
    - id: fix_tests
      description: Fix failing tests
      type: skill
      skill: pop-test-driven-development
      next: verify_tests
    - id: add_tests_decision
      description: Decide on adding tests
      type: user_decision
      question: "Add tests before finishing?"
      header: "Tests"
      options:
        - id: yes
          label: "Add tests"
          description: "Write tests for this code first"
          next: fix_tests
        - id: no
          label: "Skip tests"
          description: "Proceed without tests (not recommended)"
          next: determine_base
      next_map:
        yes: fix_tests
        no: determine_base
    - id: determine_base
      description: Determine base branch
      type: agent
      agent: code-explorer
      next: completion_choice
    - id: completion_choice
      description: Choose how to complete the branch
      type: user_decision
      question: "Implementation complete. What would you like to do?"
      header: "Complete"
      options:
        - id: merge
          label: "Merge locally"
          description: "Merge back to base branch and clean up"
          next: merge_locally
        - id: pr
          label: "Create PR"
          description: "Push and create a Pull Request for review"
          next: create_pr
        - id: keep
          label: "Keep as-is"
          description: "Keep the branch, I'll handle it later"
          next: keep_branch
        - id: discard
          label: "Discard"
          description: "Delete this work permanently"
          next: confirm_discard
      next_map:
        merge: merge_locally
        pr: create_pr
        keep: keep_branch
        discard: confirm_discard
    - id: merge_locally
      description: Merge to base branch
      type: agent
      agent: code-architect
      next: post_merge_tests
    - id: post_merge_tests
      description: Verify tests after merge
      type: agent
      agent: test-writer-fixer
      next: cleanup_branch
    - id: create_pr
      description: Push branch and create PR
      type: agent
      agent: code-architect
      next: issue_close_decision
    - id: keep_branch
      description: Keep branch as-is
      type: terminal
    - id: confirm_discard
      description: Confirm discarding work
      type: user_decision
      question: "This will permanently delete the branch and all commits. Are you sure?"
      header: "Confirm"
      options:
        - id: yes
          label: "Yes, discard"
          description: "Permanently delete this work"
          next: discard_branch
        - id: no
          label: "Cancel"
          description: "Keep the branch"
          next: completion_choice
      next_map:
        yes: discard_branch
        no: completion_choice
    - id: discard_branch
      description: Delete branch and cleanup
      type: agent
      agent: code-architect
      next: cleanup_worktree
    - id: cleanup_branch
      description: Delete merged branch
      type: agent
      agent: code-architect
      next: issue_close_decision
    - id: cleanup_worktree
      description: Remove worktree if exists
      type: skill
      skill: pop-using-git-worktrees
      next: complete
    - id: issue_close_decision
      description: Close related issue?
      type: user_decision
      question: "Close the related GitHub issue?"
      header: "Issue"
      options:
        - id: yes
          label: "Yes, close it"
          description: "Mark issue as completed"
          next: close_issue
        - id: no
          label: "No, keep open"
          description: "Issue needs more work"
          next: next_action
      next_map:
        yes: close_issue
        no: next_action
    - id: close_issue
      description: Close GitHub issue
      type: agent
      agent: code-architect
      next: check_epic
    - id: check_epic
      description: Check if part of epic
      type: agent
      agent: code-explorer
      next: next_action
    - id: next_action
      description: Choose next action
      type: user_decision
      question: "What would you like to do next?"
      header: "Next Action"
      options:
        - id: another_issue
          label: "Another issue"
          description: "Work on another GitHub issue"
          next: fetch_issues
        - id: run_checks
          label: "Run checks"
          description: "Run full test suite"
          next: run_checks
        - id: exit
          label: "Exit"
          description: "Save state and exit"
          next: save_and_exit
      next_map:
        another_issue: fetch_issues
        run_checks: run_checks
        exit: save_and_exit
    - id: fetch_issues
      description: Fetch prioritized open issues
      type: agent
      agent: code-explorer
      next: complete
    - id: run_checks
      description: Run full test and lint suite
      type: agent
      agent: test-writer-fixer
      next: next_action
    - id: save_and_exit
      description: Save session state
      type: skill
      skill: pop-session-capture
      next: complete
    - id: complete
      description: Branch completion workflow done
      type: terminal
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests -> Present options -> Execute choice -> Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

**Before presenting options, verify tests pass:**

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:**
```
Tests failing (<N> failures). Must fix before completing:

[Show failures]

Cannot proceed with merge/PR until tests pass.
```

Stop. Don't proceed to Step 2.

**If tests pass:** Continue to Step 2.

### Step 2: Determine Base Branch

```bash
# Try common base branches
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

Or ask: "This branch split from main - is that correct?"

### Step 3: Present Options

**ALWAYS use AskUserQuestion** - never present plain text numbered options:

```
Use AskUserQuestion tool with:
- question: "Implementation complete. What would you like to do?"
- header: "Complete"
- options:
  - label: "Merge locally"
    description: "Merge back to <base-branch> and clean up"
  - label: "Create PR"
    description: "Push and create a Pull Request for review"
  - label: "Keep as-is"
    description: "Keep the branch, I'll handle it later"
  - label: "Discard"
    description: "Delete this work permanently"
- multiSelect: false
```

**NEVER present as plain text** like "1. Merge, 2. PR... type 1 or 2".

### Step 4: Execute Choice

#### Option 1: Merge Locally

```bash
# Switch to base branch
git checkout <base-branch>

# Pull latest
git pull

# Merge feature branch
git merge <feature-branch>

# Verify tests on merged result
<test command>

# If tests pass
git branch -d <feature-branch>
```

Then: Cleanup worktree (Step 5)

#### Option 2: Push and Create PR

```bash
# Push branch
git push -u origin <feature-branch>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Then: Cleanup worktree (Step 5)

#### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

If confirmed:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

Then: Cleanup worktree (Step 5)

### Step 5: Cleanup Worktree

**For Options 1, 2, 4:**

Check if in worktree:
```bash
git worktree list | grep $(git branch --show-current)
```

If yes:
```bash
git worktree remove <worktree-path>
```

**For Option 3:** Keep worktree.

### Step 6: Issue Close & Continue (if working on issue)

**Only applies when invoked via `/popkit:dev work #N`** - skip for standalone use.

#### 6a: Close Prompt

After successful merge (Option 1) or PR creation (Option 2):

```
Use AskUserQuestion tool with:
- question: "Work on issue #N complete. Close the issue?"
- header: "Close Issue"
- options:
  - label: "Yes, close it"
    description: "Mark issue as completed"
  - label: "No, keep open"
    description: "Issue needs more work or follow-up"
- multiSelect: false
```

If "Yes, close it":
```bash
gh issue close <number> --comment "Completed via /popkit:dev work #<number>"
```

#### 6b: Epic Parent Check

Check if issue references a parent epic (look for "Part of #N" or "Parent: #N" in body):

```bash
gh issue view <number> --json body --jq '.body' | grep -oE '(Part of|Parent:?) #[0-9]+'
```

If parent found:
1. Fetch all children of that epic
2. If all children closed, prompt to close epic

#### 6c: Context-Aware Next Actions

Present dynamic next actions based on project state:

```
Use AskUserQuestion tool with:
- question: "What would you like to do next?"
- header: "Next Action"
- options: [dynamically generated]
- multiSelect: false
```

**Generate options by:**

1. Fetch prioritized issues:
   ```bash
   gh issue list --state open --milestone v1.0.0 --json number,title,labels --limit 5
   ```

2. Sort by: P1 > P2 > P3, then phase:now > phase:next

3. Build 4 options:
   - Top 3 prioritized issues as "Work on #N: [title]"
   - "Session capture and exit" as final option

**Example:**
```
What would you like to do next?

1. Work on #108: Power Mode Metrics (P1-high)
   → Continue v1.0.0 milestone work

2. Work on #109: QStash Pub/Sub (P2-medium)
   → Add inter-agent messaging

3. Work on #93: Multi-Project Dashboard (P2-medium)
   → Build project visibility

4. Session capture and exit
   → Save state for later
```

**If user selects an issue**, immediately invoke `/popkit:dev work #N` - keeping them in the loop.

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch | Close Prompt |
|--------|-------|------|---------------|----------------|--------------|
| 1. Merge locally | Yes | - | - | Yes | Yes (if issue) |
| 2. Create PR | - | Yes | Yes | - | Yes (if issue) |
| 3. Keep as-is | - | - | Yes | - | No |
| 4. Discard | - | - | - | Yes (force) | No |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**Open-ended questions**
- **Problem:** "What should I do next?" -> ambiguous
- **Fix:** Present exactly 4 structured options

**Automatic worktree cleanup**
- **Problem:** Remove worktree when might need it (Option 2, 3)
- **Fix:** Only cleanup for Options 1 and 4

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request

**Always:**
- Verify tests before offering options
- Present exactly 4 options
- Get typed confirmation for Option 4
- Clean up worktree for Options 1 & 4 only

## Integration

**Called by:**
- **subagent-driven-development** (Step 7) - After all tasks complete
- **executing-plans** (Step 5) - After all batches complete

**Pairs with:**
- **using-git-worktrees** - Cleans up worktree created by that skill
