---
name: finishing-a-development-branch
description: "Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup. Presents exactly 4 options: merge locally, create PR, keep as-is, or discard. Do NOT use when tests are failing or work is incomplete - fix issues first before finishing the branch."
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
