# PopKit Polish & Philosophy Documentation Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** Document PopKit's core philosophy, fix outdated documentation, and test the `/popkit:knowledge` command flow.

**Architecture:** This plan addresses three areas: (1) Philosophy documentation in CLAUDE.md, (2) README/CONTRIBUTING accuracy updates, (3) Knowledge command testing and potential fixes. Each area is independent and could be parallelized.

**Tech Stack:** Markdown, Python (hooks), JSON configuration

---

## Phase 1: Document Core Philosophy

### Task 1.1: Add Philosophy Section to CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:1-50` (add after Project Overview section)

**Step 1: Read current CLAUDE.md structure**

Run: Review CLAUDE.md to find insertion point after "## Project Overview"

**Step 2: Add Philosophy section**

Insert after "## Project Overview" section (around line 15):

```markdown
## Core Philosophy

PopKit exists to **orchestrate Claude Code's full power** for real-world development workflows. Claude Code provides raw tools; PopKit chains them together programmatically.

### Key Principles

1. **Full Claude Code Orchestration**
   - Leverages ALL capabilities: hooks, agents, skills, commands, status line, output styles, MCP servers
   - Not just using tools, but composing them into coherent workflows

2. **Non-Linear Development Support**
   - Development isn't linear; there are branches and different paths
   - Can help new projects (generate PRDs, setup GitHub)
   - Can analyze existing projects (identify gaps, recommend fixes)
   - Adapts to any project type (full stack, web, mobile)

3. **Programmatic Chaining**
   - Simple tasks chained together → orchestrated workflows
   - Example: GitHub push + feature update as unified `/popkit:commit-push-pr`
   - Follows Claude Code engineering blog best practices
   - Context preservation for long-running processes

4. **Tiered Loading**
   - Don't load all tools at once
   - Tier 1: Always-active core agents (11)
   - Tier 2: On-demand specialists activated by triggers (16)
   - Feature Workflow: 7-phase development agents (3)

5. **Project-Specific Customization ("Chain Combos")**
   - Base commands work everywhere (Tier 1)
   - Generate custom versions for specific projects (Tier 2)
   - Skills/commands that learn and grow with the project
   - Example: `/popkit:generate-mcp` creates project-specific MCP server

6. **Inter-Agent Communication** (Future)
   - Pub-sub pattern for parallel agent orchestration
   - JSON file checkpoints for agent message passing
   - Structured output styles for inter-agent communication
   - Future state: Redis cache for high-availability

### Design Goals

| Goal | Implementation |
|------|----------------|
| Check GitHub first | Always improve existing code before implementing from scratch |
| Context preservation | STATUS.json pattern, session capture/restore skills |
| Confidence-based filtering | 80+ threshold prevents false positives |
| Progressive disclosure | Load documentation only when needed |
| Engineering blog alignment | Follow Anthropic's recommended patterns |
```

**Step 3: Verify insertion**

Run: `grep -n "Core Philosophy" CLAUDE.md`
Expected: Line number showing "## Core Philosophy"

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Core Philosophy section to CLAUDE.md

Documents PopKit's design principles including full orchestration,
non-linear development support, tiered loading, and future inter-agent
communication plans.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 2: Fix README Accuracy

### Task 2.1: Update Feature Counts in README

**Files:**
- Modify: `README.md:6-13`

**Step 1: Count actual components**

Run these commands to verify counts:
```bash
# Count skills
ls -1 skills/*/SKILL.md | wc -l
# Expected: 29

# Count commands
ls -1 commands/*.md | wc -l
# Expected: 27

# Count hooks
ls -1 hooks/*.py | wc -l
# Expected: 14

# Count output styles
ls -1 output-styles/*.md | wc -l
# Expected: 9
```

**Step 2: Update README features section**

Replace lines 6-13 with:

```markdown
## Features

- **29 Specialized Agents** - 11 Tier-1 always-active + 16 Tier-2 on-demand + 3 feature-workflow
- **29 Skills** - From brainstorming to code review to knowledge management
- **27 Commands** - Full GitHub lifecycle, git operations, knowledge sync, and more
- **14 Hooks** - Safety checks, agent orchestration, session management, chain validation
- **9 Output Styles** - Consistent templates for commits, PRs, reviews, agent handoffs
- **MCP Server Template** - Generate project-specific dev servers with semantic search
```

**Step 3: Verify changes**

Run: `head -15 README.md`
Expected: Updated counts visible

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README feature counts to match actual components

- Skills: 21 → 29
- Commands: 17 → 27
- Hooks: 10 → 14
- Output Styles: 8 → 9

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.2: Add Missing Commands to README

**Files:**
- Modify: `README.md:59-99` (Commands Reference section)

**Step 1: Identify missing commands**

Missing from README:
- `/popkit:knowledge` - Knowledge source management
- `/popkit:workflow-viz` - Workflow chain visualization
- `/popkit:sync` - Plugin synchronization
- `/popkit:next` - Context-aware recommendations
- `/popkit:popkit-release` - Plugin release workflow
- `/popkit:generate-morning` - Morning command generator

**Step 2: Add new section after GitHub Lifecycle table**

Insert after line ~89 (after GitHub Lifecycle section):

```markdown
### Knowledge & Observability
| Command | Description |
|---------|-------------|
| `/popkit:knowledge` | Manage external knowledge sources with caching |
| `/popkit:knowledge add <url>` | Add new knowledge source |
| `/popkit:knowledge refresh` | Force refresh cached knowledge |
| `/popkit:workflow-viz` | Visualize workflow chains with metrics |
| `/popkit:sync` | Validate and synchronize plugin state |
| `/popkit:next` | Context-aware action recommendations |
| `/popkit:morning` | Morning health check with "Ready to Code" score |
| `/popkit:generate-morning` | Create project-specific morning command |

### Meta
| Command | Description |
|---------|-------------|
| `/popkit:popkit-release` | Release new version of popkit itself |
| `/popkit:plugin-test` | Run plugin self-tests |
| `/popkit:routing-debug` | Debug agent selection logic |
| `/popkit:auto-docs` | Generate and sync documentation |
```

**Step 3: Verify insertion**

Run: `grep -n "Knowledge & Observability" README.md`
Expected: Line number showing new section

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add missing commands to README reference

Adds Knowledge & Observability section with knowledge, workflow-viz,
sync, next, morning commands. Adds Meta section with plugin management.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.3: Add Missing Skills to README

**Files:**
- Modify: `README.md:135-165` (Skills section)

**Step 1: Add missing skills to appropriate sections**

Insert in Session Management section (after line ~151):

```markdown
### Knowledge & Chains
- `popkit:knowledge-lookup` - Query cached external knowledge sources
- `popkit:chain-management` - Workflow chain validation and metrics
- `popkit:next-action` - Context-aware recommendation engine
- `popkit:validation-engine` - Reusable validation patterns
```

**Step 2: Verify changes**

Run: `grep -n "knowledge-lookup" README.md`
Expected: Line showing new skill

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add missing skills to README

Adds knowledge-lookup, chain-management, next-action, validation-engine
skills to documentation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.4: Fix CONTRIBUTING.md Prefix

**Files:**
- Modify: `CONTRIBUTING.md` (replace all `pop:` with `popkit:`)

**Step 1: Count occurrences**

Run: `grep -c "pop:" CONTRIBUTING.md`
Expected: Number of occurrences to fix

**Step 2: Replace all occurrences**

Use Edit tool to replace:
- `pop:yourskill` → `popkit:yourskill`
- `pop:yourcommand` → `popkit:yourcommand`
- `/pop:plugin-test` → `/popkit:plugin-test`
- `pop:name` → `popkit:name`
- `pop-name/` stays as `pop-name/` (directory convention)

**Step 3: Verify changes**

Run: `grep "popkit:" CONTRIBUTING.md | head -5`
Expected: Shows updated references

**Step 4: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: update CONTRIBUTING.md to use popkit: prefix

Replaces outdated pop: prefix with popkit: throughout contribution guide.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: Test and Fix /popkit:knowledge Command

### Task 3.1: Test Knowledge Command - List Subcommand

**Files:**
- Test: `commands/knowledge.md`
- Config: `~/.claude/config/knowledge/sources.json`

**Step 1: Run the command**

Run: `/popkit:knowledge`

**Step 2: Observe behavior**

Expected behavior (per command definition):
1. Should read `~/.claude/config/knowledge/sources.json`
2. Should query cache status from `~/.claude/config/knowledge/cache.db`
3. Should display formatted table of sources

Actual behavior to observe:
- Does it use Read tool or bash cat?
- Does it create config directory if missing?
- Does it handle missing config gracefully?

**Step 3: Document findings**

Create test result file:
```bash
echo "# /popkit:knowledge Test Results - $(date)" > docs/test-results/knowledge-test.md
```

---

### Task 3.2: Test Knowledge Command - Add Subcommand

**Files:**
- Test: `commands/knowledge.md`
- Expected creation: `~/.claude/config/knowledge/sources.json`

**Step 1: Test adding a knowledge source**

Run: `/popkit:knowledge add https://docs.anthropic.com/en/docs/claude-code`

**Step 2: Observe behavior**

Expected per command definition:
1. Should validate URL
2. Should use WebFetch to test fetch and get page title
3. Should ask for details via AskUserQuestion
4. Should add to sources.json
5. Should trigger initial sync

Actual behavior to observe:
- Does it use WebFetch or bash curl?
- Does it invoke the skill properly?
- Does it ask questions or just proceed?

**Step 3: Document findings**

Append to test results file.

---

### Task 3.3: Analyze Knowledge Skill Implementation

**Files:**
- Read: `skills/pop-knowledge-lookup/SKILL.md`

**Step 1: Review skill instructions**

Check if skill instructs to use:
- Native Read tool vs bash cat
- Native Grep tool vs bash grep
- WebFetch tool vs bash curl
- SQLite queries (bash is appropriate here)

**Step 2: Identify improvements**

Per Claude Code best practices:
- Native tools preferred for LLM-directed operations
- Bash appropriate for SQLite, system commands
- WebFetch should be used for URL fetching (not curl)

**Step 3: Document recommended fixes**

If fixes needed, create issue or fix directly.

---

### Task 3.4: Fix Knowledge Skill If Needed

**Files:**
- Modify: `skills/pop-knowledge-lookup/SKILL.md`

**Step 1: Update tool references**

If skill uses bash for file reading, update to use Read tool:

Replace:
```bash
cat ~/.claude/config/knowledge/sources.json
```

With instruction:
```markdown
Use the Read tool to read `~/.claude/config/knowledge/sources.json`
```

Replace:
```bash
grep -ri "hooks" ~/.claude/config/knowledge/content/
```

With instruction:
```markdown
Use the Grep tool to search for patterns in `~/.claude/config/knowledge/content/`
```

Keep SQLite as bash (no native equivalent):
```bash
sqlite3 ~/.claude/config/knowledge/cache.db "SELECT ..."
```

**Step 2: Verify changes compile**

Run: `/popkit:plugin-test`
Expected: All tests pass

**Step 3: Commit**

```bash
git add skills/pop-knowledge-lookup/SKILL.md
git commit -m "fix: update knowledge skill to use native Claude Code tools

Uses Read tool instead of cat, Grep tool instead of grep.
Keeps SQLite queries as bash (appropriate use case).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 4: Clean Up Test Artifacts

### Task 4.1: Remove Test Directories

**Files:**
- Delete: `Test1.2.0/`
- Delete: `test1.3.0/`
- Delete: `nul`
- Delete: `hooks/__pycache__/`
- Delete: `hooks/utils/__pycache__/`

**Step 1: Remove test artifacts**

```bash
rm -rf Test1.2.0 test1.3.0 nul
rm -rf hooks/__pycache__ hooks/utils/__pycache__
```

**Step 2: Add __pycache__ to .gitignore if not present**

Check: `grep __pycache__ .gitignore`

If not present, add:
```
__pycache__/
*.pyc
```

**Step 3: Verify cleanup**

Run: `git status`
Expected: Only intentional changes shown

**Step 4: Commit .gitignore if changed**

```bash
git add .gitignore
git commit -m "chore: add __pycache__ to .gitignore

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Philosophy | 1 task | 5 min |
| Phase 2: README/CONTRIBUTING | 4 tasks | 15 min |
| Phase 3: Knowledge Testing | 4 tasks | 20 min |
| Phase 4: Cleanup | 1 task | 2 min |

**Total: 10 tasks, ~42 minutes**

---

## Execution Options

After completing this plan, consider:

1. **Create GitHub Issue** for inter-agent pub-sub implementation (bigger feature)
2. **Run `/popkit:plugin-test`** to verify all changes
3. **Push changes** when satisfied
