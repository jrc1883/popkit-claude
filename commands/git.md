---
description: "commit | push | pr | review | ci | release | prune | finish [--draft, --squash]"
---

# /popkit:git - Git Workflow Management

Comprehensive git operations with smart commits, PR management, code review, CI/CD runs, releases, branch cleanup, and development completion.

## Usage

```
/popkit:git <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `commit` | Smart commit with auto-generated message (default) |
| `push` | Push current branch to remote |
| `pr` | Pull request management (create, list, view, merge) |
| `review` | Code review with confidence-based filtering |
| `ci` | GitHub Actions workflow runs (list, view, rerun, watch) |
| `release` | GitHub releases (create, list, view, changelog) |
| `prune` | Remove stale local branches after PR merge |
| `finish` | Complete development with 4-option flow |

---

## Subcommand: commit (default)

Generate commit message from staged changes, following repository conventions.

```
/popkit:git                           # Auto-generate commit message
/popkit:git commit                    # Same as above
/popkit:git commit "fixed the login"  # Use hint for message
/popkit:git commit --amend            # Amend previous commit
```

### Process

1. **Check Status**
   ```bash
   git status --porcelain
   git diff --cached --stat
   ```

2. **Analyze Changes**
   - Count files changed
   - Identify change types (new, modified, deleted)
   - Detect patterns (feat, fix, refactor, etc.)

3. **Generate Message**
   Following conventional commits:
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```
   Types: feat, fix, docs, style, refactor, perf, test, chore, ci, revert

4. **Commit**
   ```bash
   git commit -m "$(cat <<'EOF'
   <generated message>

   Generated with Claude Code

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

### Attribution

All commits include:
- Claude Code attribution link
- Co-Authored-By header

---

## Subcommand: push

Push current branch to remote.

```
/popkit:git push                      # Push current branch
/popkit:git push --force-with-lease   # Force push safely
/popkit:git push -u                   # Set upstream
```

### Safety

- Warns before pushing to main/master
- Uses `--force-with-lease` instead of `--force`
- Confirms if branch has no upstream

---

## Subcommand: pr

Full pull request management - create, list, view, merge, and more.

### pr create (default for pr)

Create new pull request:

```
/popkit:git pr                        # Create PR from current branch
/popkit:git pr create                 # Same as above
/popkit:git pr create --title "Add auth"
/popkit:git pr create --draft         # As draft
/popkit:git pr create --base develop  # Target branch
```

**Process:**
1. Verify clean state
2. Create/switch branch (if needed)
3. Stage changes
4. Generate commit
5. Push branch
6. Create PR with template

**PR Template:**
```markdown
## Summary
<2-3 bullet points describing changes>

## Changes
- `file.ts`: <what changed>

## Test Plan
- [ ] Unit tests pass
- [ ] Manual testing completed

## Related Issues
Closes #<issue-number>

---
Generated with Claude Code
```

### pr list

List pull requests:

```
/popkit:git pr list                   # Open PRs
/popkit:git pr list --state all       # All PRs
/popkit:git pr list --author @me      # My PRs
/popkit:git pr list --review-requested
/popkit:git pr list --draft           # Draft PRs only
```

Output:
```
Open PRs (5):
#67 [ready] Add authentication - @user - 2 reviews
#66 [draft] Refactor API - @user - 0 reviews
#65 [changes] Fix login bug - @user - 1 review
```

### pr view

View PR details:

```
/popkit:git pr view 67
/popkit:git pr view 67 --comments
/popkit:git pr view 67 --files
/popkit:git pr view 67 --checks
```

Output:
```
#67: Add authentication
State: open (ready for review)
Author: @username
Base: main <- feature/auth
Created: 2 days ago

Checks:
[ok] CI / build
[ok] CI / test
[ok] CI / lint

Reviews:
[ok] @reviewer1: approved
[...] @reviewer2: pending

Files changed (5):
+120 -45 src/auth/login.ts
```

### pr merge

Merge pull request:

```
/popkit:git pr merge 67               # Default merge
/popkit:git pr merge 67 --squash      # Squash and merge
/popkit:git pr merge 67 --rebase      # Rebase and merge
/popkit:git pr merge 67 --delete-branch
```

**Pre-merge checks:**
1. All required reviews approved
2. All status checks passing
3. No merge conflicts
4. Branch is up to date

### pr checkout

Check out PR locally:

```
/popkit:git pr checkout 67
```

### pr diff

View PR diff:

```
/popkit:git pr diff 67
/popkit:git pr diff 67 --file src/auth.ts
```

### pr ready

Mark PR as ready for review (from draft):

```
/popkit:git pr ready 67
```

### pr update

Update PR branch with base:

```
/popkit:git pr update 67
```

---

## Subcommand: review

Code review with confidence-based issue filtering.

```
/popkit:git review                    # Review uncommitted changes
/popkit:git review --staged           # Review staged changes only
/popkit:git review --branch feature/auth
/popkit:git review --pr 67            # Review PR changes
/popkit:git review --file src/auth.ts # Review specific file
```

### Process

Invokes the **code-review** skill:

1. **Gather Changes**
   ```bash
   git diff HEAD~1...HEAD         # For branch review
   git diff --cached              # For staged
   git diff                       # For uncommitted
   ```

2. **Analyze Categories**
   - **Simplicity/DRY/Elegance** - Duplication, complexity, abstractions
   - **Bugs/Correctness** - Logic errors, edge cases, type safety
   - **Conventions** - Project patterns, naming, organization

3. **Score and Filter**
   Each issue gets confidence score (0-100):
   - 0-49: Ignored (likely false positive)
   - 50-79: Noted but not reported
   - 80-89: Important (should fix)
   - 90-100: Critical (must fix)

   **Threshold: 80+** only reported.

4. **Report**

### Output

```markdown
## Code Review: Feature Auth

### Summary
Clean implementation with good test coverage. Two issues found.

### Critical Issues (Must Fix)

#### Issue 1: Missing null check
- **File**: `src/auth.ts:45`
- **Confidence**: 95/100
- **Category**: Bug/Correctness
- **Description**: `user.email` accessed without null check
- **Fix**: Add optional chaining or null check

### Important Issues (Should Fix)

#### Issue 2: Duplicate validation logic
- **File**: `src/auth.ts:60-75`
- **Confidence**: 82/100
- **Category**: Simplicity/DRY
- **Description**: Email validation duplicated from utils
- **Fix**: Import and use existing validateEmail()

### Assessment

**Ready to merge?** With fixes
**Quality Score: 7/10**
```

### Options

```
/popkit:git review --focus simplicity     # Focus on DRY/elegance
/popkit:git review --focus correctness    # Focus on bugs
/popkit:git review --focus conventions    # Focus on patterns
/popkit:git review --threshold 70         # Lower confidence threshold
/popkit:git review --verbose              # Include lower-confidence issues
```

---

## Subcommand: ci

Monitor and manage GitHub Actions workflows.

```
/popkit:git ci                            # Recent runs (default)
/popkit:git ci list                       # Same as above
/popkit:git ci list --workflow ci.yml     # Specific workflow
/popkit:git ci list --branch main         # By branch
/popkit:git ci list --status failure      # Failed only
/popkit:git ci view 234                   # View run details
/popkit:git ci view 234 --log             # With logs
/popkit:git ci rerun 233                  # Rerun all jobs
/popkit:git ci rerun 233 --failed         # Rerun failed only
/popkit:git ci watch 235                  # Watch running workflow
/popkit:git ci cancel 235                 # Cancel running workflow
/popkit:git ci download 234               # Download artifacts
/popkit:git ci logs 234                   # View logs
```

### ci list (default for ci)

List workflow runs:

```
/popkit:git ci                            # Recent runs
/popkit:git ci list --workflow ci.yml     # Specific workflow
/popkit:git ci list --branch main         # By branch
/popkit:git ci list --status failure      # Failed only
/popkit:git ci list --limit 20            # More results
```

Output:
```
Recent Workflow Runs:
[ok] CI #234 - main - 2m ago - 3m 45s
[x] CI #233 - feature/auth - 1h ago - 2m 12s
[ok] Deploy #89 - main - 2h ago - 5m 30s
[...] CI #235 - fix/bug - running - 1m 20s
```

### ci view

View run details:

```
/popkit:git ci view 234
/popkit:git ci view 234 --log
/popkit:git ci view 234 --job build
```

Output:
```
Run #234: CI
Status: success
Workflow: ci.yml
Branch: main
Commit: abc123 - "feat: add auth"
Duration: 3m 45s
Triggered: push

Jobs:
[ok] build (1m 20s)
[ok] test (2m 15s)
[ok] lint (45s)
```

### ci rerun

Rerun workflow:

```
/popkit:git ci rerun 233              # Rerun all jobs
/popkit:git ci rerun 233 --failed     # Rerun failed jobs only
/popkit:git ci rerun 233 --job test   # Rerun specific job
```

### ci watch

Watch running workflow with live updates:

```
/popkit:git ci watch 235
```

### ci cancel

Cancel running workflow:

```
/popkit:git ci cancel 235
```

### ci download

Download artifacts:

```
/popkit:git ci download 234           # All artifacts
/popkit:git ci download 234 --name dist
```

### ci logs

View logs:

```
/popkit:git ci logs 234               # All logs
/popkit:git ci logs 234 --job build   # Specific job
/popkit:git ci logs 234 --failed      # Failed steps only
```

### Workflow Status Icons

- [ok] success
- [x] failure
- [...] in_progress
- [ ] queued
- [~] cancelled
- [!] skipped

---

## Subcommand: release

Create and manage GitHub releases with auto-generated changelogs.

```
/popkit:git release                       # List releases (default)
/popkit:git release list                  # Same as above
/popkit:git release create v1.2.0         # Create release
/popkit:git release create v1.2.0 --draft # Create as draft
/popkit:git release view v1.2.0           # View release
/popkit:git release edit v1.2.0           # Edit release
/popkit:git release delete v1.2.0         # Delete release
/popkit:git release changelog             # Preview changelog
```

### release list (default for release)

List releases:

```
/popkit:git release                       # All releases
/popkit:git release list --limit 5        # Recent 5
/popkit:git release list --draft          # Include drafts
```

### release create

Create new release with automatic changelog generation:

```
/popkit:git release create <version>
/popkit:git release create v1.2.0
/popkit:git release create v1.2.0 --draft
/popkit:git release create v1.2.0 --prerelease
/popkit:git release create v1.2.0 --title "Feature Name"
/popkit:git release create v1.2.0 --update-docs     # Also update CLAUDE.md
/popkit:git release create v1.2.0 --changelog-only  # Preview changelog
```

**Process:**
1. Parse commits since last release tag
2. Generate changelog from conventional commits
3. If `--update-docs`: Update CLAUDE.md Version History
4. Create git tag
5. Create GitHub release with notes

**Changelog Generation (--update-docs):**

Uses `hooks/utils/changelog_generator.py` to:
1. Parse conventional commits (feat, fix, docs, etc.)
2. Extract issue numbers from commit messages
3. Generate formatted CLAUDE.md entry
4. Insert at correct position in Version History

```bash
# Preview what would be added to CLAUDE.md
python hooks/utils/changelog_generator.py --preview

# Generate and update CLAUDE.md
python hooks/utils/changelog_generator.py --update --version 1.2.0 --title "Feature Name"
```

**Release Notes Template:**
```markdown
## What's Changed

### Features
- feat: Add user authentication (#45)
- feat: Add dark mode support (#43)

### Bug Fixes
- fix: Resolve login validation issue (#44)

### Other Changes
- chore: Update dependencies
- docs: Improve API documentation

## Full Changelog
https://github.com/owner/repo/compare/v1.1.0...v1.2.0

---
Generated with Claude Code
```

### release view

View release details:

```
/popkit:git release view v1.2.0
```

### release edit

Edit release:

```
/popkit:git release edit v1.2.0 --notes "Updated notes"
/popkit:git release edit v1.2.0 --draft false
/popkit:git release edit v1.2.0 --prerelease true
```

### release delete

Delete release:

```
/popkit:git release delete v1.2.0
/popkit:git release delete v1.2.0 --tag  # Also delete tag
```

### release changelog

Generate changelog without creating release:

```
/popkit:git release changelog          # Since last release
/popkit:git release changelog v1.1.0   # Since specific version
/popkit:git release changelog --format md
```

### Version Detection

Automatically detects version from:
1. Command argument
2. package.json version
3. Cargo.toml version
4. Latest tag + increment

### Changelog Generation

Analyzes commits for:
- **feat**: New features
- **fix**: Bug fixes
- **docs**: Documentation
- **perf**: Performance
- **refactor**: Code changes
- **test**: Tests
- **chore**: Maintenance

Groups by type and includes PR/issue links.

---

## Subcommand: prune

Remove stale local branches after PRs are merged.

```
/popkit:git prune                     # Interactive cleanup
/popkit:git prune --dry-run           # Preview only
/popkit:git prune --force             # Include unmerged branches
```

### Process

1. **Fetch and Prune**
   ```bash
   git fetch --prune
   ```

2. **Find Gone Branches**
   ```bash
   git branch -vv | grep ': gone]' | awk '{print $1}'
   ```

3. **Preview** (always)
   ```
   Found 3 branches to remove:
   - feature/auth (merged 2 days ago)
   - fix/login-bug (merged 1 week ago)

   Proceed with deletion? [y/N]
   ```

4. **Delete** (if confirmed)

### Safety

- Uses `-d` (safe delete) not `-D`
- Won't delete unmerged branches by default
- Always previews before deletion
- Never deletes main/master/develop

---

## Subcommand: finish

Guide completion of development work with structured options.

```
/popkit:git finish                    # Finish current branch
/popkit:git finish feature/auth       # Finish specific branch
```

### Process

Invokes the **pop-finish-branch** skill:

#### Step 1: Verify Tests

```
Running tests...
[ok] 47 tests passing

Tests verified. Proceeding to options.
```

#### Step 2: Present Options

```
Implementation complete. What would you like to do?

1. Merge back to main locally
2. Push and create a Pull Request
3. Keep the branch as-is (handle later)
4. Discard this work

Which option? [1-4]
```

### Option 1: Merge Locally

```
Merged feature/auth into main.
Branch deleted.
Worktree cleaned up.
```

### Option 2: Create PR

Uses `/popkit:git pr create` flow.

### Option 3: Keep As-Is

```
Keeping branch feature/auth.
Worktree preserved at .worktrees/feature-auth
```

### Option 4: Discard

Requires typed confirmation. Deletes branch, commits, and worktree.

### Safety

- Always verifies tests first
- Never force-pushes without confirmation
- Requires typed confirmation for discard
- Preserves worktree for PR option

---

## Examples

```bash
# Smart commit with auto-generated message
/popkit:git
/popkit:git commit
/popkit:git commit "fixed the auth bug"

# Push to remote
/popkit:git push

# Full PR workflow
/popkit:git pr
/popkit:git pr create --draft
/popkit:git pr list --review-requested
/popkit:git pr view 67 --checks
/popkit:git pr merge 67 --squash --delete-branch

# Code review
/popkit:git review
/popkit:git review --pr 67
/popkit:git review --focus correctness

# Clean up merged branches
/popkit:git prune
/popkit:git prune --dry-run

# Complete development work
/popkit:git finish

# CI/CD - Check why CI failed
/popkit:git ci list --status failure
/popkit:git ci view 233 --log
/popkit:git ci rerun 233 --failed

# CI/CD - Watch current run
/popkit:git ci watch

# Releases - Create with auto-generated notes
/popkit:git release create v1.2.0
/popkit:git release create v1.3.0 --draft

# View changelog preview
/popkit:git release changelog
```

---

## Git Safety Protocol

All git operations follow these rules:

- **NEVER** update git config
- **NEVER** run destructive/irreversible commands without explicit request
- **NEVER** skip hooks (--no-verify) unless explicitly requested
- **NEVER** force push to main/master
- **AVOID** git commit --amend unless explicitly requested
- **ALWAYS** check authorship before amending
- **ALWAYS** preview before bulk operations

---

## GitHub CLI Integration

All PR commands use `gh` CLI:

```bash
gh pr create --title "..." --body "..."
gh pr list --state open
gh pr view 67
gh pr merge 67 --squash
gh pr review 67 --approve
gh pr checkout 67
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Commit Generation | Conventional commits format |
| PR Templates | `output-styles/pr-description.md` |
| Code Review Skill | `skills/pop-code-review/SKILL.md` |
| Branch Cleanup | Git branch tracking |
| Finish Flow | `skills/pop-finish-branch/SKILL.md` |
| GitHub CLI | `gh pr create`, `gh pr list`, `gh run`, `gh release` |
| Workflow Runs | `gh run list/view/rerun/watch/cancel` commands |
| Workflow Artifacts | `gh run download` for build outputs |
| Release Creation | `gh release create` with auto-notes |
| Changelog Generation | Parses conventional commits (feat, fix, docs, etc.) |
| Changelog Generator | `hooks/utils/changelog_generator.py` |
| Version Detection | package.json, Cargo.toml, pyproject.toml, git tags |
| Morning Health Check | `/popkit:morning` includes CI status |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:worktree` | Git worktree management |
| `/popkit:dev execute` | Leads to finish flow |
| `/popkit:morning` | Includes CI status check |
