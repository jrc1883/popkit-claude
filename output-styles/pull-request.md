---
name: pull-request
description: Pull request template with summary, changes, and test plan
---

# Pull Request Style

## Format

```markdown
## Summary
<2-3 bullet points describing the change>

## Changes
- `path/to/file.ts`: <what changed>
- `path/to/other.ts`: <what changed>

## Test Plan
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] <specific verification step>

## Screenshots
<if UI changes, include before/after>

## Related Issues
Closes #<issue-number>

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Sections

### Summary
- 2-3 concise bullet points
- Focus on WHAT changed and WHY
- Not HOW (that's in the diff)

### Changes
- List files changed with brief description
- Group by feature area if many files
- Highlight risky changes

### Test Plan
- Checkboxes for verification steps
- Include manual testing if applicable
- Reference test files if relevant

### Screenshots
- Required for UI changes
- Before/after comparisons
- Mobile views if responsive

### Related Issues
- Use "Closes #N" to auto-close
- Use "Related to #N" for reference only
- Link to design docs if applicable

## Examples

**Feature PR:**
```markdown
## Summary
- Add user authentication with Google OAuth
- Implement session management with JWT
- Add protected route middleware

## Changes
- `src/auth/provider.ts`: OAuth provider setup
- `src/auth/middleware.ts`: JWT validation
- `src/components/LoginButton.tsx`: Login UI

## Test Plan
- [x] Unit tests pass (47 tests)
- [x] Manual OAuth flow tested
- [ ] Session expiry verified

## Related Issues
Closes #23

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Bug Fix PR:**
```markdown
## Summary
- Fix login button not responding on mobile
- Add touch event handling

## Changes
- `src/components/LoginButton.tsx`: Add touch handler

## Test Plan
- [x] Desktop click works
- [x] Mobile tap works (iOS Safari)
- [x] Mobile tap works (Android Chrome)

## Screenshots
Before: Button required double-tap
After: Button responds to single tap

## Related Issues
Closes #45

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
