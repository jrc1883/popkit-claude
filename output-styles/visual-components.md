---
name: visual-components
description: Reusable visual components for consistent PopKit command output
---

# Visual Components Library

Standard visual elements for PopKit command output. Use these components for consistent, polished UX across all commands.

## Box Headers

Use for command entry points and major sections.

### Standard Box Header

```
╔══════════════════════════════════════════════════════════╗
║           PopKit [Command Name]                          ║
╚══════════════════════════════════════════════════════════╝
```

### With Subtitle

```
╔══════════════════════════════════════════════════════════╗
║           PopKit Project Initialization                  ║
║           Project: my-app | Branch: main                 ║
╚══════════════════════════════════════════════════════════╝
```

### Simple Header (Preferred)

For most commands, use the simpler single-line header with underline:

```
PopKit Project Initialization
═════════════════════════════
```

Or with context:

```
PopKit Morning Report - my-app
══════════════════════════════
Branch: main | 2025-12-10 09:30
```

## Progress Indicators

Use for multi-step operations.

### Numbered Steps (Recommended)

```
[1/4] Checking for plugin conflicts...
      ✓ No conflicts detected

[2/4] Detecting project type...
      ✓ Node.js (Next.js 14) detected

[3/4] Creating .claude/ structure...
      ✓ Directories created
      ✓ STATUS.json initialized
      ✓ settings.json created

[4/4] Updating CLAUDE.md...
      ✓ PopKit section appended
      ✓ Existing content preserved
```

### With Timing

```
[1/3] Building Docker image...
      → Stage 1/3: deps (cached)
      → Stage 2/3: builder (47s)
      → Stage 3/3: runner (3s)
      ✓ Build complete (52s)
```

### In-Progress Indicator

```
[2/4] Running tests...
      → 23/47 tests complete...
```

### Error State

```
[3/4] Deploying to production...
      ✗ Deployment failed: ImagePullBackOff
```

## Status Indicators

### Checkmarks and Crosses

| Symbol | Meaning | Usage |
|--------|---------|-------|
| ✓ | Success | Task completed successfully |
| ✗ | Failure | Task failed |
| → | In progress | Currently executing |
| ⚠️ | Warning | Completed with warnings |
| ℹ️ | Info | Informational note |

### Status Tags

```
[OK]      All checks passed
[WARN]    2 warnings detected
[ERROR]   Build failed
[SKIP]    Skipped (not applicable)
```

### Service Status

```
Services:
  ✓ Dev Server: Running on :3000
  ✓ Database: Connected on :5432
  ✗ Redis: Not running
  ○ Elasticsearch: Not configured
```

## Tables

### Standard Table

```
| File | Status | Action |
|------|--------|--------|
| CLAUDE.md | Created | New file |
| STATUS.json | Updated | Modified |
| .gitignore | Skipped | Already exists |
```

### Compact Table

```
| Check | Status |
|-------|--------|
| TypeScript | ✓ Clean |
| Lint | ⚠️ 2 warnings |
| Tests | ✓ 47/47 |
```

### Key-Value Display

When table overhead isn't needed:

```
Project Type: Node.js (Next.js 14)
Deployment State: configured
Targets: docker, vercel
Last Deploy: v1.2.0 (2h ago)
```

## Scores and Metrics

### Score Display

```
Ready to Code Score: 85/100
═══════════════════════════
██████████████████░░ 85%

Breakdown:
  Git: 25/25 (clean working directory)
  TypeScript: 20/20 (no errors)
  Tests: 25/25 (all passing)
  Lint: 15/15 (clean)
```

### Compact Score

```
Ready to Code: 85/100 🟢
```

### Score Colors

| Score Range | Indicator | Meaning |
|-------------|-----------|---------|
| 90-100 | 🟢 | Excellent |
| 70-89 | 🟡 | Good |
| 50-69 | 🟠 | Needs attention |
| 0-49 | 🔴 | Blocked |

## Urgency Indicators

### In Tables

```
| Item | Status | Urgency |
|------|--------|---------|
| Uncommitted files | 5 files | HIGH |
| Behind remote | 2 commits | MEDIUM |
| Technical debt | 3 items | LOW |
| TypeScript | Clean | OK |
```

### Inline

```
⚠️ HIGH: 5 uncommitted files
⚠️ MEDIUM: Branch is 2 commits behind
ℹ️ LOW: 3 technical debt items
✓ OK: TypeScript clean
```

## Sections and Dividers

### Section Headers

```
Summary
───────
Configuration saved successfully.

Next Steps
──────────
1. Run /popkit:deploy setup docker
2. Configure environment variables
```

### Major Divider

```
═══════════════════════════════════════════════════════════
```

### Minor Divider

```
───────────────────────────────────────────────────────────
```

## Recommendations and Actions

### Numbered Recommendations

```
## Recommended Actions

### 1. Commit Your Current Work
**Command:** `/popkit:git commit`
**Why:** You have 5 uncommitted files
**Benefit:** Clean working directory

### 2. Push to Remote
**Command:** `/popkit:git push`
**Why:** Branch is 2 commits ahead
**Benefit:** Backup and team visibility
```

### Quick Reference Table

```
## Quick Reference

| If you want to... | Use this command |
|-------------------|------------------|
| Commit changes | `/popkit:git commit` |
| Create PR | `/popkit:git pr` |
| Check health | `/popkit:routine morning` |
```

## Completion Messages

### Success

```
[Command Name] Complete!
════════════════════════

Summary:
  - Files created: 4
  - Files modified: 2
  - Duration: 12s

What would you like to do next?
```

### With Follow-up Options

Always end multi-step commands with next action prompt using AskUserQuestion.

### Error Recovery

```
[Command Name] Failed
═════════════════════

Error: Could not connect to database

Recovery options:
  1. Check database is running: docker-compose up -d db
  2. Verify connection string in .env
  3. Try again: /popkit:[command]
```

## Dashboard Layout

For comprehensive status displays (morning routine, power mode status):

```
┌─────────────────────────────────────────────────────────────┐
│ PopKit Morning Report - my-app                              │
│ 2025-12-10 09:30 | Branch: main                            │
├─────────────────────────────────────────────────────────────┤
│ Ready to Code: 85/100 🟢                                    │
├─────────────────────────────────────────────────────────────┤
│ Services          │ Git                                     │
│ ✓ Dev Server      │ Branch: main                           │
│ ✓ Database        │ Last: abc123 (2h ago)                  │
│ ✗ Redis           │ Uncommitted: 0                         │
├─────────────────────────────────────────────────────────────┤
│ Quality           │ Issues                                  │
│ ✓ TypeScript      │ 3 open (1 HIGH)                        │
│ ✓ Lint            │ 2 awaiting review                      │
│ ✓ Tests (47/47)   │                                        │
├─────────────────────────────────────────────────────────────┤
│ Recommendations:                                            │
│ 1. Start Redis: docker-compose up -d redis                 │
│ 2. Review issue #42: /popkit:issue view 42                 │
└─────────────────────────────────────────────────────────────┘
```

## Terminal Width Considerations

- Standard width: 60-80 characters
- Box borders: Degrade gracefully (use simple headers if narrow)
- Tables: Consider compact format for narrow terminals
- Progress indicators: Always work regardless of width

## Color Guidelines (When Supported)

| Element | Color |
|---------|-------|
| Success (✓) | Green |
| Error (✗) | Red |
| Warning (⚠️) | Yellow/Orange |
| Info (→) | Blue |
| Headers | Bold |

Note: Not all terminals support colors. Visual elements should be readable without color.

## Usage in Skills

When creating skills or commands, reference this component library:

```markdown
# In your SKILL.md

## Output Format

Use the `visual-components` output style for progress indicators.

[1/N] Step description...
      ✓ Sub-step complete

See `output-styles/visual-components.md` for full component reference.
```
