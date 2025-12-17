# PopKit Command Consolidation Design

> Created: 2025-12-04 via /popkit:design brainstorm

## Summary

Consolidate PopKit's 17 top-level commands into 11 commands through strategic merging, eliminating redundancy while improving discoverability and maintaining clear user journeys.

## Goals

1. **Reduce cognitive load**: Fewer commands to remember
2. **Clearer user journeys**: Obvious paths for common tasks
3. **Eliminate redundancy**: No duplicate functionality
4. **Maintain flexibility**: Multiple entry points for different needs

## Before/After Overview

| Before (17) | After (11) | Change |
|-------------|------------|--------|
| `/popkit:design` | → `/popkit:dev` | Merged |
| `/popkit:plan` | → `/popkit:dev` | Merged |
| `/popkit:feature-dev` | → `/popkit:dev` | Merged |
| `/popkit:ci` | → `/popkit:git` | Merged |
| `/popkit:git` | `/popkit:git` | Enhanced |
| `/popkit:issue` | `/popkit:issue` | Simplified |
| `/popkit:init-project` | → `/popkit:project` | Merged |
| `/popkit:project` | `/popkit:project` | Enhanced |
| `/popkit:morning` | → `/popkit:routine` | Merged |
| `/popkit:nightly` | → `/popkit:routine` | Merged |
| `/popkit:next` | `/popkit:next` | Keep |
| `/popkit:power` | `/popkit:power` | Keep |
| `/popkit:worktree` | `/popkit:worktree` | Keep |
| `/popkit:debug` | `/popkit:debug` | Keep |
| `/popkit:knowledge` | `/popkit:knowledge` | Keep |
| `/popkit:workflow-viz` | `/popkit:workflow-viz` | Keep (review later) |
| `/popkit:plugin` | `/popkit:plugin` | Keep |

---

## Detailed Design

### 1. /popkit:dev (NEW)

**Replaces:** design, plan, feature-dev

**Rationale:** These three commands all serve the development lifecycle but with different entry points. Merging them creates a single mental model: "I want to develop something."

#### Subcommands

| Subcommand | Description | Source |
|------------|-------------|--------|
| `full` (default) | 7-phase guided workflow | feature-dev |
| `work #N` | Issue-driven development | issue work |
| `brainstorm` | Idea refinement through dialogue | design brainstorm |
| `plan` | Create implementation plan | plan write |
| `execute` | Execute an existing plan | plan execute |
| `quick` | Minimal ceremony implementation | NEW |
| `prd` | Generate PRD document | design prd |
| `suite` | Generate full documentation suite | design suite |

#### User Journeys

```
Rough idea       → /popkit:dev brainstorm "topic"
Clear design     → /popkit:dev plan --from design.md
Have a plan      → /popkit:dev execute plan.md
GitHub issue     → /popkit:dev work #45
Want guidance    → /popkit:dev full "feature"
Quick fix        → /popkit:dev quick "fix bug"
```

#### Skills Integration

| Mode | Skills Invoked |
|------|----------------|
| brainstorm | pop-brainstorming |
| plan | pop-writing-plans |
| execute | pop-executing-plans |
| full | pop-brainstorming → pop-project-templates → code-explorer → code-architect → pop-writing-plans → pop-executing-plans → pop-finish-branch |

---

### 2. /popkit:git (Enhanced)

**Absorbs:** ci

**Rationale:** CI/CD operations (workflow runs, releases) are closely tied to git workflow. Consolidating reduces command sprawl while keeping related functionality together.

#### Subcommands

| Subcommand | Description | Source |
|------------|-------------|--------|
| `commit` | Smart commit with auto-generated message | git commit |
| `push` | Push to remote | git push |
| `pr` | Pull request management | git pr |
| `review` | Code review | git review |
| `finish` | Complete development branch | git finish |
| `prune` | Clean stale branches | git prune |
| `ci` | Workflow run management | ci run |
| `release` | GitHub release management | ci release |

#### CI Subcommand Detail

```bash
/popkit:git ci list              # List workflow runs
/popkit:git ci view 234          # View specific run
/popkit:git ci rerun 233         # Rerun workflow
/popkit:git ci watch 235         # Watch in progress
/popkit:git ci cancel 235        # Cancel run
/popkit:git ci logs 234          # View logs
```

#### Release Subcommand Detail

```bash
/popkit:git release create v1.0  # Create release with changelog
/popkit:git release list         # List releases
/popkit:git release view v1.0    # View release
/popkit:git release changelog    # Generate changelog preview
```

---

### 3. /popkit:issue (Simplified)

**Removes:** `work` subcommand (moved to dev)

**Rationale:** `issue work` triggers development workflows, making it a better fit for `/popkit:dev`. The issue command becomes pure issue management.

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List repository issues |
| `view` | View issue details |
| `create` | Create new issue with template |
| `close` | Close an issue |
| `comment` | Add comment to issue |
| `edit` | Update issue metadata |
| `link` | Link issue to PR |

---

### 4. /popkit:project (Enhanced)

**Absorbs:** init-project

**Rationale:** Project initialization is a project operation. Having a separate command adds unnecessary complexity.

#### Subcommands

| Subcommand | Description | Source |
|------------|-------------|--------|
| `init` | Initialize .claude/ structure | init-project |
| `analyze` | Analyze codebase | project analyze |
| `embed` | Embed for semantic search | project embed |
| `generate` | Full generation pipeline | project generate |
| `mcp` | Generate MCP server | project mcp |
| `setup` | Configure project | project setup |
| `skills` | Generate custom skills | project skills |

---

### 5. /popkit:routine (NEW)

**Replaces:** morning, nightly

**Rationale:** These are mirror commands with identical subcommand structures. Unifying them under one parent improves discoverability.

#### Structure

```bash
/popkit:routine morning [subcommand]
/popkit:routine nightly [subcommand]
```

#### Subcommands (same for both morning/nightly)

| Subcommand | Description |
|------------|-------------|
| (default) | Run the routine |
| `quick` | Quick summary |
| `generate` | Create custom routine |
| `list` | List available routines |
| `set` | Set default routine |
| `edit` | Edit routine |
| `delete` | Delete routine |

#### Examples

```bash
/popkit:routine morning              # Run morning routine
/popkit:routine morning quick        # Quick morning check
/popkit:routine nightly generate     # Generate nightly routine
/popkit:routine morning list         # List morning routines
/popkit:routine nightly set rc-1     # Set default nightly
```

---

### 6-11. Unchanged Commands

| Command | Purpose | Notes |
|---------|---------|-------|
| `/popkit:power` | Multi-agent orchestration | Core feature, keep separate |
| `/popkit:worktree` | Git worktree management | Specialized, keep separate |
| `/popkit:next` | Context-aware recommendations | Useful standalone utility |
| `/popkit:debug` | Debugging tools | Specialized, keep separate |
| `/popkit:knowledge` | External knowledge management | Specialized, keep separate |
| `/popkit:workflow-viz` | Visualize workflow chains | Review for future merge into power |
| `/popkit:plugin` | Plugin management | PopKit-specific, keep separate |

---

## Implementation Plan

### Phase 1: Create New Commands

1. Create `/popkit:dev` command file
   - Implement subcommand routing
   - Integrate existing skills
   - Add `quick` mode

2. Update `/popkit:git` command file
   - Add `ci` subcommand group
   - Add `release` subcommand group
   - Update help text

3. Create `/popkit:routine` command file
   - Implement morning/nightly routing
   - Preserve all existing functionality

4. Update `/popkit:project` command file
   - Add `init` subcommand
   - Update help text

### Phase 2: Update Existing Commands

1. Remove `work` from `/popkit:issue`
2. Add deprecation warnings to old commands
3. Update CLAUDE.md documentation

### Phase 3: Cleanup

1. Remove deprecated command files:
   - `commands/design.md`
   - `commands/plan.md`
   - `commands/feature-dev.md`
   - `commands/ci.md`
   - `commands/init-project.md`
   - `commands/morning.md`
   - `commands/nightly.md`

2. Update all references in:
   - Skills
   - Agents
   - Hooks
   - Output styles
   - Tests

### Phase 4: Documentation

1. Update CLAUDE.md with new command structure
2. Update command count in plugin.json
3. Create migration guide for users

---

## User Journey Reference

| "I want to..." | Command |
|---------------|---------|
| Build something new | `/popkit:dev` |
| Work on a GitHub issue | `/popkit:dev work #N` |
| Brainstorm an idea | `/popkit:dev brainstorm` |
| Create a plan | `/popkit:dev plan` |
| Execute a plan | `/popkit:dev execute` |
| Quick fix | `/popkit:dev quick` |
| Commit code | `/popkit:git commit` |
| Create a PR | `/popkit:git pr create` |
| Check CI | `/popkit:git ci list` |
| Create release | `/popkit:git release create` |
| Manage issues | `/popkit:issue` |
| Set up project | `/popkit:project init` |
| Start my day | `/popkit:routine morning` |
| End my day | `/popkit:routine nightly` |
| What's next? | `/popkit:next` |
| Use Power Mode | `/popkit:power start` |

---

## Success Metrics

- [ ] Command count reduced from 17 to 11
- [ ] All existing functionality preserved
- [ ] Clear documentation for each command
- [ ] No breaking changes to skill invocations
- [ ] Updated CLAUDE.md reflects new structure
- [ ] Tests updated and passing

---

## Future Considerations

1. **workflow-viz**: May merge into `/popkit:power viz` in future
2. **worktree**: Could become `/popkit:git worktree` if needed
3. **next**: Could integrate into dev workflow prompts
4. **Status line**: Investigate why not working (separate issue)

---

## Related Issues

- Status line not working (mentioned during brainstorm - investigate separately)

---

*Generated with Claude Code via /popkit:design brainstorm*
