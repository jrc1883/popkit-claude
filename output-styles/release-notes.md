---
name: release-notes
description: Release notes with changelog, highlights, and breaking changes
---

# Release Notes Style

## Format

```markdown
# Release v[X.Y.Z]

**Release Date:** YYYY-MM-DD

## Highlights

- <Major feature or change 1>
- <Major feature or change 2>

## What's Changed

### Features
- feat: <description> (#PR)
- feat: <description> (#PR)

### Bug Fixes
- fix: <description> (#PR)
- fix: <description> (#PR)

### Performance
- perf: <description> (#PR)

### Other Changes
- chore: <description>
- docs: <description>

## Breaking Changes

### [Change Name]
**What changed:** <description>
**Migration:** <how to update>

## Upgrade Guide

<Steps to upgrade from previous version>

## Full Changelog
https://github.com/owner/repo/compare/vPrev...vCurr

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Sections

### Highlights
- 2-3 most important changes
- User-facing language
- No technical jargon

### What's Changed
- Grouped by type (feat, fix, perf, etc.)
- Each item links to PR
- Author attribution if multiple contributors

### Breaking Changes
- Clear warning at top
- What changed
- How to migrate
- Code examples if helpful

### Upgrade Guide
- Step-by-step instructions
- Common issues and solutions
- Rollback procedure

## Version Numbering

Follow Semantic Versioning:
- **Major (X)**: Breaking changes
- **Minor (Y)**: New features, backward compatible
- **Patch (Z)**: Bug fixes, backward compatible

## Example

```markdown
# Release v2.0.0

**Release Date:** 2025-01-15

## Highlights

- Complete rewrite of authentication system with OAuth support
- New dashboard with real-time updates
- 50% faster page loads through caching improvements

## What's Changed

### Features
- feat(auth): Add OAuth support for Google and GitHub (#67)
- feat(dashboard): Real-time data updates with WebSockets (#65)
- feat(ui): New dark mode theme (#62)

### Bug Fixes
- fix(auth): Resolve session timeout issues (#70)
- fix(api): Handle null responses gracefully (#68)

### Performance
- perf(api): Add Redis caching layer (#66)
- perf(ui): Lazy load dashboard components (#64)

### Other Changes
- docs: Update API documentation (#71)
- chore: Upgrade dependencies (#69)

## Breaking Changes

### Authentication API Changes
**What changed:** Session-based auth replaced with JWT tokens.
**Migration:**
1. Update client to use Authorization header
2. Remove session cookie handling
3. Implement token refresh logic

```javascript
// Before
fetch('/api/data', { credentials: 'include' })

// After
fetch('/api/data', {
  headers: { Authorization: `Bearer ${token}` }
})
```

### Dashboard Component Props
**What changed:** `data` prop renamed to `initialData`
**Migration:** Update all Dashboard component usages.

## Upgrade Guide

1. Update dependencies: `npm install @app/core@2.0.0`
2. Update authentication (see Breaking Changes)
3. Update Dashboard component props
4. Clear local storage: `localStorage.clear()`
5. Test OAuth flow

## Full Changelog
https://github.com/owner/repo/compare/v1.5.0...v2.0.0

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Auto-Generation

From git history:
1. Parse commits since last tag
2. Group by type (feat, fix, etc.)
3. Link to PRs/issues
4. Detect breaking changes from commit messages
