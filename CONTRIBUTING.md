# Contributing to popkit

Thank you for your interest in contributing to popkit! This document provides guidelines for contributing to this Claude Code plugin.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Install Claude Code if you haven't already
4. Load the plugin locally: `claude plugins add /path/to/your/fork`

## Project Structure

```
.claude-plugin/     Plugin manifest files
agents/             Agent definitions (tier-1, tier-2, feature-workflow)
commands/           Slash commands (/popkit:*)
hooks/              Python hooks for lifecycle events
skills/             Skill definitions (pop-*/SKILL.md)
output-styles/      Output format templates
templates/          MCP server template
tests/              Plugin self-tests
```

## Types of Contributions

### Adding a New Skill

1. Create a directory: `skills/pop-yourskill/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: popkit:yourskill
   description: "When to use this skill"
   ---
   ```
3. Document the skill's purpose and workflow
4. Update README.md to list the new skill

### Adding a New Command

1. Create `commands/yourcommand.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   name: popkit:yourcommand
   description: Short description
   ---
   ```
3. Document usage and examples
4. Update README.md

### Adding a New Agent

1. Determine tier (tier-1-always-active or tier-2-on-demand)
2. Create the agent file in appropriate directory
3. Add routing rules to `agents/config.json`
4. Update README.md

### Improving Existing Content

- Fix typos or clarify documentation
- Improve skill/command prompts
- Add examples to existing features

## Code Style

- **Markdown**: Use YAML frontmatter with `name:` and `description:` fields
- **JSON**: 2-space indentation, trailing commas not allowed
- **Python hooks**: Use `#!/usr/bin/env python3`, JSON stdin/stdout protocol
- **Naming**: Skills use `popkit:name` in frontmatter, `pop-name/` for directories

## Commit Messages

Use conventional commits:

```
feat: add new skill for X
fix: correct routing for Y agent
docs: update installation instructions
refactor: simplify hook implementation
```

Include Claude attribution:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Testing

Run the built-in test suite:
```
/popkit:plugin-test
```

This validates:
- Plugin structure
- Hook JSON protocol
- Agent routing

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes
3. Run `/popkit:plugin-test` to verify nothing is broken
4. Commit with conventional commit message
5. Push and create a PR
6. Fill out the PR template

## GitHub Development Workflow

PopKit provides commands that work together for a smooth development cycle:

### Issue-Driven Development

```bash
# 1. Find or create an issue
/popkit:issue list                    # See open issues
/popkit:issue create "Add feature X"  # Create new issue

# 2. Create isolated workspace
/popkit:worktree create fix-42        # Creates branch + worktree

# 3. Do the work
# ... make your changes ...

# 4. Commit and finish
/popkit:commit                        # Auto-generate commit message
/popkit:finish-branch                 # Choose: merge, PR, keep, or discard

# 5. Clean up after merge
/popkit:prune-branches                # Remove stale branches
```

### Quick PR Flow

```bash
# One command: branch → commit → push → PR
/popkit:commit-push-pr feature/auth
```

### Release Flow

```bash
# After PRs are merged
/popkit:release changelog             # Preview what's included
/popkit:release create v0.8.0         # Tag and publish
```

### Daily Routine

```bash
/popkit:morning                       # Health check, "Ready to Code" score
/popkit:next                          # What should I work on?
```

### Worktree Best Practices

Worktrees let you work on multiple features simultaneously:

```bash
/popkit:worktree create feature/auth  # Main feature
/popkit:worktree create fix/urgent    # Urgent fix in parallel
/popkit:worktree list                 # See all workspaces
/popkit:worktree analyze              # Find opportunities
```

## Questions?

- Open an issue with the "question" label
- Check existing issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
