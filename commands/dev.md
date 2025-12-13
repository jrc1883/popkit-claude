---
description: "full | work #N | brainstorm | plan | execute | quick | prd | suite [-T, --power]"
argument-hint: "<mode> [topic|#issue] [flags]"
---

# /popkit:dev - Development Workflows

Unified entry point for all development workflows, from idea refinement to implementation.

## Usage

```
/popkit:dev [mode] [topic] [flags]
```

## Modes

| Mode | Description | Source |
|------|-------------|--------|
| `full` | 7-phase guided workflow (default) | feature-dev |
| `work #N` | Issue-driven development | issue work |
| `brainstorm` | Idea refinement through dialogue | design brainstorm |
| `plan` | Create implementation plan | plan write |
| `execute` | Execute an existing plan | plan execute |
| `quick` | Minimal ceremony implementation | NEW |
| `prd` | Generate PRD document | design prd |
| `suite` | Generate full documentation suite | design suite |

## Flags

| Flag | Description |
|------|-------------|
| `-T`, `--thinking` | Enable extended thinking mode |
| `--no-thinking` | Disable extended thinking |
| `--think-budget N` | Set thinking token budget (default: 10000) |
| `--from FILE` | Generate from existing design/plan document |
| `--issue N` | Reference GitHub issue for context |
| `-p`, `--power` | Force Power Mode (for work mode) |
| `-s`, `--solo` | Force sequential mode (for work mode) |

---

## Mode: full (default)

Complete 7-phase guided workflow for feature development.

```
/popkit:dev "user authentication"
/popkit:dev full "payment integration"
/popkit:dev "dark mode" -T
```

### The 7 Phases

#### Phase 1: Discovery
**Goal:** Understand what to build

```
What feature would you like to build?
> User authentication with OAuth

Let me gather context about the project...
- Project: Next.js 14 with Supabase
- Existing auth: None
- Related: User model exists
```

#### Phase 2: Exploration
**Goal:** Understand the codebase

Uses **code-explorer** agent:

```
Exploring codebase for similar features...

Entry Points:
- `src/app/api/auth/route.ts` (new)
- `src/components/auth/` (to create)

Patterns Found:
- API routes use standard Response format
- Components use server actions
```

#### Phase 3: Questions
**Goal:** Clarify requirements using curated templates

Uses **pop-project-templates** skill:

```
[AskUserQuestion: Runtime - Node.js+Fastify / Python+FastAPI / etc.]
[AskUserQuestion: Database - PostgreSQL / MySQL / MongoDB / etc.]
[AskUserQuestion: Auth - Clerk / Auth0 / Supabase Auth / etc.]
```

#### Phase 4: Architecture
**Goal:** Design the implementation

Uses **code-architect** agent:

```
## Architecture Design: User Authentication

### Approach: Pragmatic Balance

| Component | Purpose | Location |
|-----------|---------|----------|
| AuthProvider | Context for auth state | `src/providers/` |
| LoginForm | Email/password form | `src/components/auth/` |

Do you approve this architecture? [y/N]
```

#### Phase 5: Implementation
**Goal:** Build the feature

```
Creating worktree for isolated development...
Generating implementation plan...
Executing plan in batches...
[Task-by-task implementation with TDD]
```

#### Phase 6: Review
**Goal:** Verify quality

Uses **code-reviewer** agent:

```
## Code Review: User Authentication

### Summary
Clean implementation with 95% test coverage.

### Critical Issues: 0
### Important Issues: 1

Quality Score: 8/10
```

#### Phase 7: Summary
**Goal:** Complete and document

```
Feature development complete!

Options:
1. Merge to main
2. Create PR for review
3. Keep branch for more work
4. Discard

Which option?
```

#### Phase 8: Close & Continue (for work mode)
**Goal:** Close issue and keep user in the loop

After successful merge or PR creation in `work` mode:

**Step 1: Close Prompt**
```
Use AskUserQuestion tool with:
- question: "Work on issue #N complete. Close the issue?"
- header: "Close Issue"
- options:
  1. label: "Yes, close it"
     description: "Mark issue as completed"
  2. label: "No, keep open"
     description: "Issue needs more work or follow-up"
- multiSelect: false
```

If "Yes", execute: `gh issue close <number> --comment "Completed via /popkit:dev work"`

**Step 2: Epic Parent Check**

If the closed issue references a parent epic (check issue body for "Part of #N" or "Parent: #N"):
1. Fetch all child issues of that epic
2. If all children are closed, prompt:

```
Use AskUserQuestion tool with:
- question: "All children of Epic #M are now complete. Close the epic?"
- header: "Close Epic"
- options:
  1. label: "Yes, close epic"
     description: "Mark epic as completed"
  2. label: "No, keep open"
     description: "Epic needs more tracking"
- multiSelect: false
```

**Step 3: Context-Aware Next Actions**

After close decision, present dynamic next actions:

```
Use AskUserQuestion tool with:
- question: "What would you like to do next?"
- header: "Next Action"
- options: [dynamically generated - see below]
- multiSelect: false
```

**Dynamic Options Generation:**

1. Fetch open issues: `gh issue list --state open --milestone v1.0.0 --json number,title,labels --limit 5`
2. Sort by priority (P1 > P2 > P3) and phase (now > next)
3. Build options:

| Option | When to Include |
|--------|-----------------|
| "Work on #N: [title]" | Always include top 3-4 prioritized issues |
| "Run nightly routine" | If time is evening (after 5pm) |
| "Run morning health check" | If time is morning (before 10am) |
| "Analyze project" | If no urgent issues |
| "Session capture and exit" | Always include as last option |

**Example Output:**
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

**If user selects an issue**, immediately invoke `/popkit:dev work #N` for that issue - keeping them in the loop.

### Architecture Integration

| Component | Integration |
|-----------|-------------|
| Agent: code-explorer | Phase 2 - Codebase exploration |
| Agent: code-architect | Phase 4 - Architecture design |
| Agent: code-reviewer | Phase 6 - Code review |
| Skill: pop-brainstorming | Phase 1 - Discovery |
| Skill: pop-project-templates | Phase 3 - Technology choices |
| Skill: pop-writing-plans | Phase 5 - Plan generation |
| Skill: pop-executing-plans | Phase 5 - Plan execution |
| Skill: pop-finish-branch | Phase 7 - Completion |

---

## Mode: work

Issue-driven development with optional Power Mode.

```
/popkit:dev work #57
/popkit:dev work #57 -p              # Force Power Mode
/popkit:dev work #57 --solo          # Force sequential mode
/popkit:dev work #57 --phases explore,implement,test
```

### Flags (work mode)

| Flag | Short | Description |
|------|-------|-------------|
| `--power` | `-p` | Force Power Mode activation |
| `--solo` | `-s` | Force sequential mode |
| `--phases` | | Override phases: `--phases explore,implement,test` |
| `--agents` | | Override agents: `--agents reviewer,tester` |

### Power Mode Decision Priority

1. **Command flags override everything**
2. **If no flags, use PopKit Guidance from issue**
3. **If no guidance, infer from labels/title**
4. **Default to sequential mode**

### Process

1. **Fetch Issue**: `gh issue view <number> --json number,title,body,labels,state,author`
2. **Parse PopKit Guidance**: Extract workflow, phases, agents, quality gates
3. **Determine Mode**: Apply decision priority
4. **Create Todo List**: Generate todos from phases
5. **Begin Work**: Start first phase (brainstorming if required)
6. **Execute All Phases**: Work through each phase until complete
7. **Complete Work**: Invoke `pop-finish-branch` skill for merge/PR options
8. **Next Action Loop**: Present context-aware next actions using AskUserQuestion

### Completion (CRITICAL - Issue #118)

**After all phases complete**, you MUST:

1. Use `pop-finish-branch` skill to:
   - Verify tests pass
   - Present merge/PR/keep/discard options
   - Execute user's choice

2. Then present next actions using AskUserQuestion:
```
Use AskUserQuestion tool with:
- question: "What would you like to do next?"
- header: "Next Action"
- options: [dynamically generated from open issues]
  - Top 3 prioritized issues as "Work on #N: [title]"
  - "Session capture and exit" as final option
- multiSelect: false
```

**NEVER end a workflow without presenting next step options to the user.**

### Output (Power Mode)

```
[+] POWER MODE - ISSUE #57
Title: Create /popkit:dev command
Labels: enhancement

Configuration:
  Source: PopKit Guidance
  Phases: 3 (implementation -> testing -> documentation)
  Agents: api-designer, code-reviewer
  Quality Gates: lint, plugin test

Starting Phase 1: Implementation...
```

### Output (Sequential Mode)

```
[+] WORKING ON ISSUE #57
Title: Create /popkit:dev command
Mode: Sequential

Phases: 3 (implementation -> testing -> documentation)

Starting Phase 1: Implementation...
```

---

## Mode: brainstorm

Refine rough ideas into fully-formed designs through collaborative Socratic questioning.

```
/popkit:dev brainstorm
/popkit:dev brainstorm "real-time notifications"
/popkit:dev brainstorm -T
```

### Process

Invokes the **pop-brainstorming** skill:

1. **Understand context** - Review project state, docs, recent commits
2. **Ask questions** - One at a time, using AskUserQuestion
3. **Explore approaches** - Present 2-3 options with trade-offs
4. **Present design** - In 200-300 word sections, validate each
5. **Document** - Save to `docs/plans/YYYY-MM-DD-<topic>-design.md`
6. **Next steps** - Offer worktree setup and plan creation

### Example Session

```
/popkit:dev brainstorm user authentication

Claude: Let me check the current project state...

Found: Next.js 14, Supabase, no existing auth

[AskUserQuestion: What type of authentication?]
- Email/password only
- OAuth providers (Google, GitHub)
- Magic link (passwordless)
- Multiple options

> OAuth providers

[AskUserQuestion: Which OAuth providers?]
...

Let me present the design in sections...

## Section 1: Architecture
We'll use NextAuth.js with Supabase adapter...

Does this section look right so far?
```

### Output

Creates design document at `docs/plans/YYYY-MM-DD-<topic>-design.md`

### After Design Approval

Offers:
- Create worktree for implementation
- Generate implementation plan via `/popkit:dev plan`
- Create GitHub issue from design

---

## Mode: plan

Create comprehensive implementation plans for engineers with zero codebase context.

```
/popkit:dev plan
/popkit:dev plan user-auth
/popkit:dev plan --from design.md
/popkit:dev plan --issue 45
```

### Process

Invokes the **pop-writing-plans** skill:

1. Load design document or gather requirements
2. Break into bite-sized tasks (2-5 minutes each)
3. Include exact file paths
4. Provide complete code examples
5. Add verification commands
6. Save to `docs/plans/YYYY-MM-DD-<feature>.md`

### Plan Structure

```markdown
# [Feature] Implementation Plan

> **For Claude:** Use /popkit:dev execute to implement.

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Technologies]

---

### Task 1: [Component Name]

**Files:**
- Create: `exact/path/to/file.ts`
- Modify: `existing/file.ts:50-75`
- Test: `tests/file.test.ts`

**Step 1: Write the failing test**
[Complete test code]

**Step 2: Run test to verify it fails**
Run: `npm test -- file.test.ts`
Expected: FAIL

**Step 3: Write minimal implementation**
[Complete implementation]

**Step 4: Run test to verify it passes**
Expected: PASS

**Step 5: Commit**
```

### After Planning

Offers execution options:
1. **Execute Now** - Run `/popkit:dev execute`
2. **Subagent-Driven** - Same session, fresh subagent per task
3. **Later** - Save plan for future execution

---

## Mode: execute

Execute implementation plans in controlled batches with review checkpoints.

```
/popkit:dev execute
/popkit:dev execute docs/plans/2025-01-15-auth.md
/popkit:dev execute --batch-size 5
/popkit:dev execute --start-at 4
/popkit:dev execute --dry-run
```

### Options

| Option | Description |
|--------|-------------|
| `--batch-size N` | Tasks per batch (default: 3) |
| `--start-at N` | Resume from task N |
| `--dry-run` | Preview without executing |

### Process

Invokes the **pop-executing-plans** skill:

1. **Load and Review** - Read plan, identify concerns
2. **Execute Batch** - Default 3 tasks per batch
3. **Report** - Show what was implemented
4. **Feedback** - User provides input
5. **Repeat** - Continue until all tasks complete
6. **Finish** - Invoke `/popkit:git finish` flow

### Batch Execution

```
Executing Batch 1 (Tasks 1-3):

Task 1: Create auth context [in_progress]
- Writing test...
- Test fails as expected
- Implementing...
- Test passes
- Committed: abc123

Task 1: Complete

[AskUserQuestion: How should I proceed?]
- Continue (next batch)
- Revise (I have feedback)
- Pause (stop here)
```

### Handling Blockers

If blocked mid-batch:
1. Stop immediately
2. Report the blocker
3. Ask for clarification
4. Don't guess or work around

---

## Mode: quick

Minimal ceremony implementation for small tasks and quick fixes.

```
/popkit:dev quick "fix the timezone bug"
/popkit:dev quick "add loading spinner to button"
```

### Process

1. **Understand** - Quick context gathering (no full exploration)
2. **Find** - Locate relevant code
3. **Fix** - Make the change
4. **Verify** - Run tests if applicable
5. **Commit** - Offer to commit

### Example

```
/popkit:dev quick "fix the timezone bug in user profiles"

Quick mode - minimal ceremony.

Let me find the relevant code...
Found: src/utils/formatDate.ts:45

The bug: Not accounting for user's timezone when displaying dates.

Fix: Use user.timezone in formatDate() call.

[Makes the fix]
[Runs tests]

Done. Commit this fix?
```

### When to Use

- Small bug fixes
- Single-file changes
- Quick additions
- Typo corrections

### When NOT to Use

- New features
- Multi-file changes
- Anything requiring design decisions
- Complex logic changes

---

## Mode: prd

Generate a Product Requirements Document from a brainstorming session or feature description.

```
/popkit:dev prd "task management app"
/popkit:dev prd --from design.md
```

### Process

1. Run brainstorming session (if not provided)
2. Extract requirements
3. Structure as PRD
4. Save to `docs/prd/YYYY-MM-DD-<topic>.md`

### PRD Template

Generates document with:
- Executive Summary
- Problem Statement
- Goals and Objectives
- Functional Requirements (P0/P1/P2)
- Non-Functional Requirements
- User Stories
- Technical Considerations
- Risks and Mitigations

### After PRD Generation

Offers:
1. Review and edit the PRD
2. Generate implementation plan
3. Create GitHub issues from requirements

---

## Mode: suite

Generate a complete document suite for comprehensive feature development.

```
/popkit:dev suite "user authentication"
/popkit:dev suite "payment system" -T
```

### Generated Documents

| Document | Location | Purpose |
|----------|----------|---------|
| `problem_statement.md` | `docs/discovery/` | Problem definition |
| `PRD.md` | `docs/prd/` | Product requirements |
| `user_stories.md` | `docs/prd/` | User stories with acceptance criteria |
| `ARCHITECTURE.md` | `docs/architecture/` | High-level architecture |
| `TECHNICAL_SPEC.md` | `docs/architecture/` | Detailed technical spec |

### Process

1. **Discovery Phase** - Brainstorm, extract problem statement
2. **Requirements Phase** - Structure PRD, organize user stories
3. **Architecture Phase** - Define high-level architecture
4. **Technical Design Phase** - Detail APIs, data models, dependencies

### Output

```
Document Suite Generated:
├── docs/
│   ├── discovery/
│   │   └── 2025-01-15-user-authentication-problem.md
│   ├── prd/
│   │   ├── 2025-01-15-user-authentication-prd.md
│   │   └── 2025-01-15-user-authentication-stories.md
│   └── architecture/
│       ├── 2025-01-15-user-authentication-architecture.md
│       └── 2025-01-15-user-authentication-tech-spec.md

Summary:
- Problem statement documented
- 12 P0/P1/P2 requirements
- 15 user stories across 3 epics
- 5 key architecture decisions
- Full API specification
```

---

## Examples

```bash
# Full 7-phase guided workflow
/popkit:dev "user authentication"
/popkit:dev full "payment integration" -T

# Issue-driven development
/popkit:dev work #57
/popkit:dev work #57 -p   # With Power Mode

# Just brainstorming
/popkit:dev brainstorm "real-time notifications"

# Create implementation plan
/popkit:dev plan "dark mode"
/popkit:dev plan --from docs/designs/auth.md

# Execute a plan
/popkit:dev execute
/popkit:dev execute docs/plans/2025-01-15-auth.md --batch-size 5

# Quick fix
/popkit:dev quick "fix login validation"

# Generate PRD
/popkit:dev prd "task management"

# Generate full doc suite
/popkit:dev suite "user authentication"
```

---

## Executable Commands

### full (default)

**Phase 1: Discovery**
```bash
# Gather project context
cat package.json 2>/dev/null | head -20
cat README.md 2>/dev/null | head -50
git log --oneline -10
```

**Phase 2: Exploration**
```
Use Task tool with subagent_type="Explore"
Prompt: "Explore the codebase to understand patterns for [feature]"
```

**Phase 4: Architecture**
```
Use Task tool with subagent_type="Plan"
Prompt: "Design architecture for [feature] based on exploration findings"
```

**Phase 5: Implementation**
```bash
# Create isolated worktree
git worktree add .worktrees/feature-<name> -b feature/<name>

# Invoke pop-writing-plans skill for plan
# Invoke pop-executing-plans skill for execution
```

**Phase 6: Review**
```
Use Task tool with subagent_type="code-reviewer"
Prompt: "Review implementation of [feature] against architecture design"
```

### work

```bash
# Fetch issue details
gh issue view <number> --json number,title,body,labels,state,author
```

Then process PopKit Guidance from issue body and begin workflow.

### brainstorm

```
Use Skill tool with skill="popkit:pop-brainstorming"
```

### plan

```
Use Skill tool with skill="popkit:pop-writing-plans"
```

### execute

```
Use Skill tool with skill="popkit:pop-executing-plans"
```

### quick

No skill invocation - direct implementation with minimal ceremony:
1. Search for relevant code
2. Make targeted changes
3. Run tests
4. Commit

### prd / suite

```
Use Skill tool with skill="popkit:pop-brainstorming"
```
Then generate documents using templates.

---

## Migration from Old Commands

| Old Command | New Command |
|-------------|-------------|
| `/popkit:design` | `/popkit:dev brainstorm` |
| `/popkit:design brainstorm` | `/popkit:dev brainstorm` |
| `/popkit:design prd` | `/popkit:dev prd` |
| `/popkit:design suite` | `/popkit:dev suite` |
| `/popkit:plan` | `/popkit:dev plan` |
| `/popkit:plan write` | `/popkit:dev plan` |
| `/popkit:plan execute` | `/popkit:dev execute` |
| `/popkit:feature-dev` | `/popkit:dev` or `/popkit:dev full` |
| `/popkit:issue work #N` | `/popkit:dev work #N` |

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Brainstorming Skill | `skills/pop-brainstorming/SKILL.md` |
| Writing Plans Skill | `skills/pop-writing-plans/SKILL.md` |
| Executing Plans Skill | `skills/pop-executing-plans/SKILL.md` |
| Project Templates Skill | `skills/pop-project-templates/SKILL.md` |
| Finish Branch Skill | `skills/pop-finish-branch/SKILL.md` |
| Code Explorer Agent | `agents/feature-workflow/code-explorer/AGENT.md` |
| Code Architect Agent | `agents/feature-workflow/code-architect/AGENT.md` |
| Code Reviewer Agent | `agents/tier-1-always-active/code-reviewer/AGENT.md` |
| Design Documents | `docs/plans/YYYY-MM-DD-<topic>-design.md` |
| PRD Documents | `docs/prd/YYYY-MM-DD-<topic>.md` |
| Plan Documents | `docs/plans/YYYY-MM-DD-<feature>.md` |
| Issue Workflow Hook | `hooks/issue-workflow.py` |
| Quality Gate Hook | `hooks/quality-gate.py` |
| Power Mode | `power-mode/coordinator.py` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:git` | Version control and PR management |
| `/popkit:git finish` | Complete branch after development |
| `/popkit:issue` | Issue management (CRUD operations) |
| `/popkit:worktree` | Git worktree management |
| `/popkit:power` | Multi-agent orchestration |
