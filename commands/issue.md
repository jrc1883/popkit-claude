---
description: "create | list | view | close | comment | edit | link [--state, --label]"
---

# /popkit:issue - GitHub Issue Management

Manage GitHub issues with AI-optimized formatting and PopKit workflow guidance.

## Usage

```
/popkit:issue <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List repository issues (default) |
| `view` | View issue details |
| `create` | Create new issue with template |
| `close` | Close an issue |
| `comment` | Add comment to issue |
| `edit` | Update issue metadata |
| `link` | Link issue to PR |

> **Note:** To start working on an issue, use `/popkit:dev work #N` instead.

---

## Subcommand: list (default)

List repository issues with Power Mode recommendations.

```
/popkit:issue                         # List open issues
/popkit:issue list                    # Same as above
/popkit:issue list --power            # Only issues recommending Power Mode
/popkit:issue list --votes            # Sort by vote score
/popkit:issue list --label bug        # Filter by label
/popkit:issue list --state all        # All issues (open + closed)
/popkit:issue list --assignee @me     # Assigned to me
/popkit:issue list --milestone v1.0   # By milestone
/popkit:issue list -n 10              # Limit results
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--power` | `-p` | Show only issues recommending Power Mode |
| `--votes` | `-v` | Sort by community vote score |
| `--label` | `-l` | Filter by label |
| `--state` | | `open` (default), `closed`, `all` |
| `--assignee` | | Filter by assignee |
| `--milestone` | | Filter by milestone |
| `--limit` | `-n` | Limit results (default: 20) |

### Output Format

**Standard Format:**
```
Open Issues with Power Mode Recommendations:

| #   | Title                          | Complexity | Power Mode  | Phases |
|-----|--------------------------------|------------|-------------|--------|
| 3   | Add user authentication        | medium     | optional    | 4      |
| 11  | Unified orchestration system   | epic       | RECOMMENDED | 6      |
| 15  | Fix login regression           | small      | not_needed  | 2      |

Legend:
  RECOMMENDED = Power Mode beneficial for this issue
  optional    = Power Mode available but not required
  not_needed  = Sequential execution preferred

Hint: Use /popkit:dev work #11 to start working
      Use /popkit:dev work #11 -p to force Power Mode
```

**With --votes flag:**
```
Open Issues (sorted by community votes):

| #   | Title                          | Votes                  | Score |
|-----|--------------------------------|------------------------|-------|
| 88  | [Epic] Self-Improvement System | 👍12 ❤️3 🚀2           | 24    |
| 75  | Team Coordination Features     | 👍8  ❤️5 🚀1           | 21    |
| 66  | Power Mode v2                  | 👍6  ❤️2               | 10    |
| 92  | Vote-Based Prioritization      | 👍3                    | 3     |

Vote Weights: 👍 +1 | ❤️ +2 | 🚀 +3 | 👎 -1
```

### Process with Votes

When `--votes` flag is provided:

```python
from priority_scorer import get_priority_scorer, fetch_open_issues

# Fetch and rank by priority score
scorer = get_priority_scorer()
issues = fetch_open_issues(limit=20)
ranked = scorer.rank_issues(issues)

# Display sorted by score
print(scorer.format_ranked_list(ranked, max_items=10))
```

### Process

Use the `issue_list.py` utility:

```python
from issue_list import list_issues_with_power_mode_status, format_issues_table

# Fetch and format issues
data = list_issues_with_power_mode_status(
    filter_power=False,  # Set True for --power flag
    label=None,          # Filter by label
    state="open",        # open/closed/all
    limit=20
)
print(format_issues_table(data))
```

**Steps performed:**
1. Fetch issues via `gh issue list --json number,title,body,labels,createdAt,author`
2. Parse PopKit Guidance from each issue body
3. Extract complexity, phases, Power Mode recommendation
4. Generate formatted table

---

## Subcommand: view

View issue details with parsed PopKit Guidance.

```
/popkit:issue view 45
/popkit:issue view 45 --comments
/popkit:issue view #45              # # prefix optional
```

### Output

```
#45: Login fails on mobile
State: open
Labels: bug, priority:high
Assignee: @username

PopKit Workflow:
  Type: Bug fix
  Agents: bug-whisperer, test-writer-fixer
  Power Mode: Not needed
  Phases: Investigation -> Fix -> Test -> Review

Description:
[Full issue body]
```

---

## Subcommand: create

Create new issue with template selection.

```
/popkit:issue create <title>
/popkit:issue create "Add user authentication"
/popkit:issue create --template bug
/popkit:issue create --template feature
/popkit:issue create --template architecture
/popkit:issue create --template research
```

### Available Templates

| Template | Use For | Labels |
|----------|---------|--------|
| `feature` | New features, enhancements | enhancement |
| `bug` | Bug reports, fixes | bug |
| `architecture` | Major changes, epics, multi-PR work | architecture, epic |
| `research` | Spikes, investigations, learning | research |

### Template Selection Flow

When creating without `--template`, prompt user:

```
What type of issue is this?
1. Feature - New capability or enhancement
2. Bug - Something isn't working correctly
3. Architecture - Major changes or epic initiative
4. Research - Investigation or spike
```

### PopKit Guidance Section

All templates include a **PopKit Guidance** section that directs workflow:

```markdown
## PopKit Guidance

### Workflow
- [ ] **Brainstorm First** - Use `pop-brainstorming` skill
- [ ] **Plan Required** - Use `/popkit:plan write`
- [ ] **Direct Implementation** - Proceed directly

### Development Phases
- [ ] Discovery
- [ ] Architecture
- [ ] Implementation
- [ ] Testing
- [ ] Documentation
- [ ] Review

### Suggested Agents
- Primary: `[agent-name]`
- Supporting: `[agent-name]`

### Quality Gates
- [ ] TypeScript check
- [ ] Build verification
- [ ] Lint pass
- [ ] Test pass

### Power Mode
- [ ] Recommended - Parallel agents beneficial
- [ ] Optional - Can benefit from coordination
- [ ] Not Needed - Sequential work is fine

### Estimated Complexity
- [ ] Small (1-2 files)
- [ ] Medium (3-5 files)
- [ ] Large (6+ files)
- [ ] Epic (multiple PRs)
```

**Why PopKit Guidance Matters:**

This section is parsed by PopKit to:
1. Determine if brainstorming should be triggered first
2. Auto-activate Power Mode for complex issues
3. Schedule quality gates between phases
4. Route to appropriate agents
5. Track phase progress

---

## Subcommand: close

Close an issue with optional comment or reason.

```
/popkit:issue close 45
/popkit:issue close 45 --comment "Fixed in #PR"
/popkit:issue close 45 --reason completed
/popkit:issue close 45 --reason not_planned
/popkit:issue close 45 --superseded-by 67
```

### Flags

| Flag | Description |
|------|-------------|
| `--comment` | Add closing comment |
| `--reason` | `completed` (default) or `not_planned` |
| `--superseded-by` | Reference replacement issue |

### Process

1. **Parse Arguments**: Extract issue number, comment, reason
2. **Build Command**: Construct `gh issue close` with options
3. **Execute**: Run the close command
4. **Confirm**: Report success to user
5. **Prompt Next Action**: Use AskUserQuestion for workflow continuation

**Execute this command:**
```bash
gh issue close <number> [--comment "..."] [--reason completed|not_planned]
```

If `--superseded-by N` is provided, include in comment: "Superseded by #N"

### Post-Close Prompt (Required)

After successfully closing an issue, **always use AskUserQuestion** to guide the user's next action:

```
Use AskUserQuestion tool with:
- question: "Issue #N closed. What would you like to do next?"
- header: "Next Action"
- options:
  1. label: "Work on next issue"
     description: "Start working on another open issue"
  2. label: "View remaining issues"
     description: "List all open issues (/popkit:issue list)"
  3. label: "End session"
     description: "Capture session state and finish"
- multiSelect: false
```

**Based on selection:**
- "Work on next issue" → Fetch open issues, present top 3-5 as options via another AskUserQuestion
- "View remaining issues" → Execute `/popkit:issue list`
- "End session" → Invoke `pop-session-capture` skill

---

## Subcommand: comment

Add comment to issue.

```
/popkit:issue comment 45 "Working on this"
/popkit:issue comment 45 --file notes.md
/popkit:issue comment 45 --phase-update "Completed implementation, moving to testing"
```

### Flags

| Flag | Description |
|------|-------------|
| `--file` | Read comment body from file |
| `--phase-update` | Format as phase transition update |

### Process

1. **Parse Arguments**: Extract issue number, comment text or file
2. **Format Comment**: If `--phase-update`, prefix with "## Phase Update\n\n"
3. **Execute**: Run `gh issue comment`
4. **Confirm**: Report success

**Execute this command:**
```bash
gh issue comment <number> --body "<comment>"
# OR with file:
gh issue comment <number> --body-file <file>
```

---

## Subcommand: edit

Update issue metadata.

```
/popkit:issue edit 45 --title "New title"
/popkit:issue edit 45 --label add:priority:high
/popkit:issue edit 45 --label remove:wontfix
/popkit:issue edit 45 --assignee @username
/popkit:issue edit 45 --milestone v1.0
```

### Flags

| Flag | Description |
|------|-------------|
| `--title` | Update issue title |
| `--label` | Add/remove label (`add:name` or `remove:name`) |
| `--assignee` | Set assignee |
| `--milestone` | Set milestone |
| `--body` | Update issue body |

### Process

1. **Parse Arguments**: Extract issue number and edit flags
2. **Build Command**: Construct `gh issue edit` with appropriate flags
3. **Execute**: Run the edit command
4. **Confirm**: Report changes made

**Execute this command:**
```bash
gh issue edit <number> [--title "..."] [--add-label <name>] [--remove-label <name>] [--assignee <user>] [--milestone <name>]
```

---

## Subcommand: link

Link issue to PR by adding a comment with the reference.

```
/popkit:issue link 45 --pr 67
/popkit:issue link 45 --closes-pr 67
```

### Flags

| Flag | Description |
|------|-------------|
| `--pr` | PR number to link (adds reference comment) |
| `--closes-pr` | PR that closes this issue |

### Process

1. **Parse Arguments**: Extract issue number and PR number
2. **Format Link**: Create reference comment
3. **Execute**: Add comment to issue with PR reference
4. **Confirm**: Report link created

**Execute this command:**
```bash
gh issue comment <issue> --body "Related: #<pr>"
# OR for closing reference:
gh issue comment <issue> --body "Closes: #<pr>"
```

Note: GitHub automatically links issues and PRs when referenced in commits/PR descriptions.

---

## Agent Routing

Based on issue content and labels:

| Indicator | Primary Agent | Supporting |
|-----------|---------------|------------|
| `[Bug]` label or "bug" in title | bug-whisperer | test-writer-fixer |
| `[Feature]` label | code-architect | test-writer-fixer |
| `[Architecture]` label | code-architect | migration-specialist, refactoring-expert |
| `[Research]` label | researcher | code-explorer |
| Security keywords | security-auditor | code-reviewer |
| Performance keywords | performance-optimizer | bundle-analyzer |
| API keywords | api-designer | documentation-maintainer |
| Database keywords | query-optimizer | migration-specialist |

---

## Inference for Issues Without Guidance

When an issue lacks PopKit Guidance, infer from:

| Indicator | Inferred Complexity | Power Mode |
|-----------|---------------------|------------|
| Label: `epic` | epic | RECOMMENDED |
| Label: `architecture` | large | RECOMMENDED |
| Label: `bug` | small-medium | optional |
| Label: `feature` | medium | optional |
| Label: `docs` | small | not_needed |
| No labels | unknown | (unknown) |

---

## Examples

```bash
# List open issues with Power Mode recommendations
/popkit:issue
/popkit:issue list

# List only issues recommending Power Mode
/popkit:issue list --power

# View issue details
/popkit:issue view 45

# Create with template selection prompt
/popkit:issue create "Add user authentication"

# Create with specific template
/popkit:issue create "Refactor auth system" --template architecture

# Close as superseded
/popkit:issue close 8 --superseded-by 11

# Add phase update comment
/popkit:issue comment 11 --phase-update "Completed Phase 1: Discovery"
```

---

## GitHub CLI Integration

All commands use `gh` CLI:

```bash
gh issue list --state open --json number,title,body,labels
gh issue view 45
gh issue create --title "..." --body "..." --template feature_request.md
gh issue close 45
gh issue comment 45 --body "..."
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Issue Listing | `hooks/utils/issue_list.py` |
| Issue Fetching | `gh issue view/list` via GitHub CLI |
| PopKit Guidance Parser | `hooks/utils/github_issues.py` |
| Vote Fetching | `hooks/utils/vote_fetcher.py` |
| Priority Scoring | `hooks/utils/priority_scorer.py` |
| Flag Parsing | `hooks/utils/flag_parser.py` |
| Issue Templates | `.github/ISSUE_TEMPLATE/*.md` |
| Phase Tracking | `STATUS.json` integration |
| Power Mode | `power-mode/coordinator.py` |
| Status Line | `power-mode/statusline.py` |
| State | `.claude/popkit/power-mode-state.json` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:dev work #N` | Start working on an issue |
| `/popkit:power status` | Check Power Mode status |
| `/popkit:git pr` | Create pull request |
