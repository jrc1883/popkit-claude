---
description: "create <branch> | list | analyze | remove [--force]"
argument-hint: "<subcommand> [branch] [options]"
---

# /popkit:worktree - Git Worktree Management

Create and manage isolated workspaces for parallel development.

## Usage

```
/popkit:worktree <subcommand> [options]
```

## Subcommands

### create

Create new worktree with branch:

```
/popkit:worktree create <name>
/popkit:worktree create feature/auth
/popkit:worktree create fix-123 --from main
```

Process:
1. Check worktree directory exists
2. Verify .gitignore includes worktrees
3. Create worktree: `git worktree add .worktrees/<name> -b <name>`
4. Run project setup (npm install, etc.)
5. Verify tests pass
6. Report location

### list

List all worktrees:

```
/popkit:worktree list
```

Output:
```
Worktrees:
- main (default): /path/to/project
- feature/auth: /path/to/project/.worktrees/feature-auth
- fix/login: /path/to/project/.worktrees/fix-login
```

### analyze

Find opportunities for worktrees:

```
/popkit:worktree analyze
```

Checks for:
- Multiple in-progress branches
- Stale branches with uncommitted work
- Complex merge situations

### remove

Remove worktree and optionally branch:

```
/popkit:worktree remove <name>
/popkit:worktree remove feature/auth --keep-branch
```

Process:
1. Confirm worktree exists
2. Check for uncommitted changes
3. Warn if uncommitted: "Worktree has uncommitted changes. Delete anyway?"
4. Remove: `git worktree remove .worktrees/<name>`
5. Optionally delete branch

### prune

Clean up stale worktrees:

```
/popkit:worktree prune
```

Removes worktrees with deleted directories.

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Skill | `skills/pop-worktrees/SKILL.md` |
| Git Worktrees | `git worktree add/list/remove/prune` commands |
| Directory Structure | Creates `.worktrees/` in project root |
| Branch Management | Creates feature branches with `-b` flag |
| Project Detection | Detects npm/cargo/pip for dependency installation |
| Test Verification | Runs detected test framework after setup |
| .gitignore | Verifies `.worktrees/` is ignored |
| Safety Checks | Warns on uncommitted changes before removal |
| Hooks | Can trigger `pre-tool-use.py` for safety validation |

## Executable Commands

### Create Worktree
```bash
# Create worktree directory
mkdir -p .worktrees

# Add worktree with new branch
git worktree add .worktrees/<name> -b <name>

# Or from specific base branch
git worktree add .worktrees/<name> -b <name> origin/main

# Setup dependencies
cd .worktrees/<name> && npm install  # Node.js
cd .worktrees/<name> && pip install -e .  # Python
cd .worktrees/<name> && cargo build  # Rust
```

### List Worktrees
```bash
git worktree list
```

### Remove Worktree
```bash
# Check for uncommitted changes first
cd .worktrees/<name> && git status --porcelain

# Remove worktree
git worktree remove .worktrees/<name>

# Optionally delete branch
git branch -d <name>
```

### Prune Stale
```bash
git worktree prune
```

## Examples

```
# Start new feature
/popkit:worktree create feature/user-profiles

# See all workspaces
/popkit:worktree list

# Clean up after merge
/popkit:worktree remove feature/user-profiles

# Find parallel work opportunities
/popkit:worktree analyze
```
