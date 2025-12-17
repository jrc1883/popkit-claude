---
name: commit-message
description: Conventional commit message format with attribution
---

# Commit Message Style

## Format

```
<type>(<scope>): <subject>

<body>

<footer>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |
| `revert` | Reverting previous commit |

## Rules

1. **Subject line**
   - Max 72 characters
   - Use imperative mood ("add" not "added")
   - No period at end
   - Lowercase

2. **Scope** (optional)
   - Component or module affected
   - Examples: auth, api, ui, db

3. **Body** (optional)
   - Explain what and why
   - Wrap at 72 characters
   - Blank line before body

4. **Footer** (optional)
   - Breaking changes: `BREAKING CHANGE: description`
   - Issue references: `Closes #123`

## Examples

**Simple:**
```
feat(auth): add password reset flow
```

**With body:**
```
fix(api): handle null user in profile endpoint

The profile endpoint was crashing when user object
was null. Added null check and appropriate error
response.

Closes #45
```

**Breaking change:**
```
feat(api): change authentication to JWT

Migrate from session-based to JWT authentication
for better scalability.

BREAKING CHANGE: All clients must include JWT token
in Authorization header instead of session cookie.
```
