---
description: "morning | nightly [run|quick|generate|list|set|edit|delete]"
argument-hint: "<routine> [subcommand] [options]"
---

# /popkit:routine - Day Routines

Unified command for morning health checks and nightly maintenance routines. Supports project-specific customization with numbered routine slots.

## Usage

```
/popkit:routine <morning|nightly> [subcommand] [options]
```

## Primary Subcommands

| Subcommand | Description |
|------------|-------------|
| `morning` | Morning health check - Ready to Code score (0-100) |
| `nightly` | End-of-day cleanup - Sleep Score (0-100) |

---

## Morning Routines

Start your day with a comprehensive project health assessment.

```
/popkit:routine morning                   # Run default morning routine
/popkit:routine morning quick             # One-line summary
/popkit:routine morning run pk            # Run specific routine
/popkit:routine morning generate          # Create custom routine
/popkit:routine morning list              # List available routines
/popkit:routine morning set rc-1          # Set default routine
/popkit:routine morning edit rc-1         # Edit routine
/popkit:routine morning delete rc-2       # Delete routine
```

### Morning Subcommands

| Subcommand | Description |
|------------|-------------|
| (default) | Run the configured default routine |
| `run [id]` | Run a specific routine by ID |
| `quick` | Compact one-line summary |
| `generate` | Create a new project-specific routine |
| `list` | List available routines |
| `set <id>` | Set the default routine |
| `edit <id>` | Edit a project routine |
| `delete <id>` | Delete a project routine |

### Morning Flags

| Flag | Description |
|------|-------------|
| `--simple` | Use markdown tables instead of ASCII dashboard |
| `--no-nightly` | Skip "From Last Night" section |
| `--no-debt` | Skip technical debt check |
| `--full` | Include tests + security audit (slower) |
| `--skip-tests` | Skip test execution |
| `--skip-services` | Skip service health checks |
| `--skip-deployments` | Skip deployment status check |

### Ready to Code Score (0-100)

| Check | Points | Criteria |
|-------|--------|----------|
| Clean working directory | 25 | No uncommitted changes |
| Up to date with remote | 15 | Not behind origin |
| TypeScript clean | 20 | No type errors (or no tsconfig) |
| Lint clean | 15 | No lint errors (or no eslint) |
| Tests passing | 25 | All tests pass (or no tests) |

### Deployment Status (Optional)

When deploy targets are configured (via `/popkit:deploy init`), morning routine includes deployment health:

| Target | Status Display |
|--------|----------------|
| npm | Package name, latest version, days since publish |
| PyPI | Package name, latest version, days since publish |
| Docker | Image ID (short), last push date |
| Vercel | Deployment status, last deploy time |
| Netlify | Deployment status, last deploy time |
| GitHub Releases | Latest release tag, days since release |

**Deployment Tool Updates** (monitors for breaking changes):
```
⚠️ Vercel CLI v35.0.0 released (breaking changes)
   See: https://github.com/vercel/vercel/releases/tag/v35.0.0
```

Configure monitored repos in `.claude/popkit/config.json`:
```json
{
  "deployment_research": {
    "repositories": [
      {"owner": "vercel", "repo": "vercel"},
      {"owner": "npm", "repo": "cli"}
    ]
  }
}
```

### Morning Output

```
+==================================================================+
|                  Morning Development Status                       |
+==================================================================+
| Ready to Code: 85/100                                             |
+------------------------------------------------------------------+
| From Last Night:                                                  |
|   Sleep Score: 92/100                                             |
|   Session: Saved                                                  |
|   Focus: User authentication                                      |
+------------------------------------------------------------------+
| Git Status:           Clean                                       |
| TypeScript:           No errors                                   |
| Lint:                 Clean                                       |
| Tests:                All passing (142/142)                       |
+------------------------------------------------------------------+
| Technical Debt:       5 TODOs, 2 FIXMEs                           |
| PR Review Queue:      1 awaiting your review                      |
+------------------------------------------------------------------+
| Deployments:                                                      |
|   npm: v1.2.0 (2d ago)  │  PyPI: v1.2.0 (2d ago)                  |
|   Docker: abc123 (1d)   │  Vercel: healthy (12h ago)              |
+------------------------------------------------------------------+
| Services (Power Mode):                                            |
|   Docker: Running | Redis: Ready | Power Mode: Available          |
+------------------------------------------------------------------+
| Recommendations:                                                  |
|   None - you're ready to code!                                    |
+==================================================================+
```

---

## Nightly Routines

End your development day with cleanup, maintenance, and state preservation.

```
/popkit:routine nightly                   # Run default nightly routine
/popkit:routine nightly quick             # One-line summary
/popkit:routine nightly cleanup           # Clean caches and artifacts
/popkit:routine nightly git               # Git maintenance
/popkit:routine nightly security          # Security audit
/popkit:routine nightly backup            # Save session state
/popkit:routine nightly generate          # Create custom routine
/popkit:routine nightly list              # List available routines
/popkit:routine nightly set rc-1          # Set default routine
```

### Nightly Subcommands

| Subcommand | Description |
|------------|-------------|
| (default) | Run the configured default routine |
| `run [id]` | Run a specific routine by ID |
| `quick` | One-line summary |
| `cleanup` | Caches, artifacts, temp files |
| `git` | gc, branch cleanup, orphans |
| `security` | npm audit, secrets scan |
| `backup` | Save session state for tomorrow |
| `generate` | Create a new project-specific routine |
| `list` | List available routines |
| `set <id>` | Set the default routine |
| `edit <id>` | Edit a project routine |
| `delete <id>` | Delete a project routine |

### Nightly Flags

| Flag | Description |
|------|-------------|
| `--simple` | Use markdown tables instead of ASCII dashboard |
| `--skip-cleanup` | Skip cleanup recommendations |
| `--skip-security` | Skip security audit |
| `--full` | Include aggressive cleanup options (slower) |

### Sleep Score (0-100)

| Check | Points | Criteria |
|-------|--------|----------|
| No uncommitted changes | 25 | **Critical** - caps score at 49 if fails |
| Session state saved | 20 | STATUS.json updated within last hour |
| Git maintenance done | 15 | No orphans, gc run recently |
| Security audit clean | 15 | No critical/high vulnerabilities |
| IP leak scan clean | 10 | No leaked secrets or proprietary code |
| Caches under limit | 10 | < 500MB total cache size |
| Logs rotated | 5 | No logs older than 7 days |

**Score Interpretation:**
- 80-100: Safe to sleep - everything is clean
- 60-79: Minor cleanup recommended
- 40-59: Cleanup needed before leaving
- 0-39: **Do not leave** - uncommitted work or issues

### Nightly Output

```
Nightly Report - [Project Name]
[Date]

Sleep Score: [XX/100]

Uncommitted Work:
  Status: Clean (or UNCOMMITTED CHANGES - resolve before leaving!)
  Stashes: 0

Session State:
  STATUS.json: Updated 30 minutes ago
  Last focus: Implementing user auth

Git Maintenance:
  Orphans: None
  Merged branches: 2 ready for cleanup
  Stale remotes: 1

Cleanup Opportunities:
  Caches: 234 MB (node_modules/.cache, .next)
  Artifacts: 45 MB (dist, coverage)
  Old logs: 3 files

Security:
  npm audit: 0 critical, 0 high, 2 moderate
  Exposed secrets: None detected

IP Protection (for split-repo projects):
  Plugin scan: Clean (no leaked IP)
  Last deep scan: 3 days ago
  Recommendation: Run /popkit:audit ip-leak --deep weekly

Recommendations:
  - Run `/popkit:routine nightly cleanup --auto-fix` to clear 279 MB
  - Run `/popkit:routine nightly git --auto-fix` to clean branches
```

---

## Routine System

### PopKit Universal Routine (`pk`)

The built-in routine that works on any project:

- **ID:** `pk`
- **Mutable:** No - versioned with PopKit releases
- **Customization:** Use flags for variation (`--full`, `--skip-tests`, etc.)

### Project-Specific Routines

Custom routines stored in `.claude/popkit/routines/`:

- **ID Format:** `<prefix>-<number>` (e.g., `rc-1`, `rc-2`)
- **Mutable:** Yes
- **Limit:** 5 custom routines per type (morning/nightly)

### Prefix Algorithm

First letter of each word in project name:
- "Reseller Central" → `rc`
- "My Awesome App" → `maa`
- "popkit" → `p`

### Storage Structure

```
.claude/popkit/
├── config.json              # Project prefix, defaults
├── state.json               # Session state
└── routines/
    ├── morning/
    │   └── rc-1/            # Project routine folder
    │       ├── routine.md   # Main definition
    │       ├── config.json  # Routine settings
    │       └── checks/      # Check scripts
    └── nightly/
        └── rc-1/
            ├── routine.md
            ├── config.json
            └── scripts/     # Cleanup scripts
```

---

## Generator Flow

```
/popkit:routine morning generate

Generating custom morning routine for: Reseller Central
Prefix: rc
Slot: rc-1 (first available)

Analyzing project...
Detected:
  - Framework: Next.js 14
  - Database: Supabase (local)
  - Services: Redis, eBay API
  - Tests: Jest

What should this routine check? (select all that apply)
  [x] Git status
  [x] TypeScript errors
  [x] Lint status
  [x] Supabase connection
  [x] Redis connection
  [x] eBay API credentials
  [ ] Run full test suite (slow)
  [ ] Security audit (slow)

Routine name: Full E-Commerce Check
Description (optional): eBay API, Redis, Supabase health checks

Creating .claude/popkit/routines/morning/rc-1/...
Updating .claude/popkit/config.json...

Routine rc-1 created!

Set as default? [Y/n] y
Default morning routine set to rc-1

Run it now? [Y/n] y
```

---

## Examples

```bash
# Morning routines
/popkit:routine morning                   # Run default
/popkit:routine morning quick             # One-line summary
/popkit:routine morning run pk --full     # Universal with all checks
/popkit:routine morning run rc-1          # Project-specific routine
/popkit:routine morning generate --nightly # Generate both routines

# Nightly routines
/popkit:routine nightly                   # Run default
/popkit:routine nightly quick             # One-line summary
/popkit:routine nightly cleanup --auto-fix # Execute cleanup
/popkit:routine nightly git --auto-fix    # Git maintenance
/popkit:routine nightly security --fix    # Fix vulnerabilities
/popkit:routine nightly backup            # Save session state

# Routine management (same for both)
/popkit:routine morning list              # List routines
/popkit:routine morning set rc-2          # Change default
/popkit:routine nightly edit rc-1         # Edit routine
/popkit:routine morning delete rc-2       # Delete routine
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Routine Storage | `hooks/utils/routine_storage.py` |
| Project Config | `.claude/popkit/config.json` |
| Morning Routines | `.claude/popkit/routines/morning/` |
| Nightly Routines | `.claude/popkit/routines/nightly/` |
| Morning Output Style | `output-styles/morning-report.md` |
| Nightly Output Style | `output-styles/nightly-summary.md` |
| Generator Skills | `pop-morning-generator`, `pop-nightly-generator` |
| Session Capture | `skills/pop-session-capture` |
| STATUS.json | Session state persistence |
| Score Calculation | 100-point system for both |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:power init` | Setup Redis for Power Mode |
| `/popkit:power` | Manage multi-agent orchestration |
| `/popkit:deploy` | Deployment workflow management |
| `/popkit:next` | Get context-aware recommendations |
| `/popkit:git prune` | Git branch cleanup |
