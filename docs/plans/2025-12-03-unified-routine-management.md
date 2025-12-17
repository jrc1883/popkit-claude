# Unified Routine Management System

**Status:** Approved - Ready for Implementation
**Date:** 2025-12-03
**Author:** Claude + User Collaboration

---

## Overview

Redesign `/popkit:morning` and `/popkit:nightly` commands to use a unified routine management system with numbered project-specific routines accessible via a single command interface.

### Goals

1. **Single command interface** - No more separate `/rc:morning` commands cluttering namespace
2. **Numbered routine slots** - Project routines accessible via `run <id>`
3. **Configurable defaults** - Set which routine runs by default per project
4. **Clear namespacing** - PopKit universal vs project-specific routines
5. **YAGNI** - One universal routine + flags, complexity lives in project routines

---

## Command Structure

### Morning Command

```
/popkit:morning [subcommand] [options]
```

| Subcommand | Description |
|------------|-------------|
| (default) | Run the configured default routine |
| `run [id]` | Run a specific routine by ID |
| `quick` | One-liner summary (existing) |
| `generate` | Create a new project-specific routine |
| `list` | List available routines |
| `set <id>` | Set the default routine for this project |
| `edit <id>` | Edit a project routine (opens in editor context) |
| `delete <id>` | Delete a project routine |

### Nightly Command

Identical structure:

```
/popkit:nightly [subcommand] [options]
```

Same subcommands: `run`, `quick`, `generate`, `list`, `set`, `edit`, `delete`

---

## Routine Identification

### PopKit Universal Routine

- **ID:** `pk` (or `pk-standard`)
- **Location:** Built into popkit plugin (`commands/morning.md`, `commands/nightly.md`)
- **Mutable:** No - versioned with popkit releases
- **Flags for variation:**
  - `--full` - Include tests + security audit (slower)
  - `--skip-tests` - Skip test execution
  - `--skip-services` - Skip service health checks
  - `--simple` - Markdown tables instead of ASCII dashboard

### Project-Specific Routines

- **ID Format:** `<prefix>-<number>` (e.g., `rc-1`, `rc-2`, `maa-1`)
- **Location:** `.claude/popkit/routines/morning/<prefix>-<number>/`
- **Mutable:** Yes
- **Limit:** 5 custom routines per type (morning/nightly) per project

### Prefix Generation Algorithm

Generate prefix from project name (first letter of each word):

| Project Name | Prefix |
|--------------|--------|
| Reseller Central | `rc` |
| My Awesome App | `maa` |
| genesis | `gen` |
| popkit | `pk` (RESERVED - collision handling below) |

**Collision Handling:**
- If generated prefix = `pk`, use first 3 chars instead: `pop`
- If still collision, append number: `pop1`

---

## Storage Structure

Following Claude Code conventions, all PopKit project-local data lives under `.claude/popkit/`:

```
.claude/
├── settings.json                      # Claude Code settings (not ours)
├── CLAUDE.md                          # Project instructions (not ours)
│
└── popkit/                            # PopKit namespace
    ├── config.json                    # Project config (prefix, defaults)
    ├── state.json                     # Consolidated state (session, power-mode)
    │
    └── routines/
        ├── morning/
        │   ├── rc-1/
        │   │   ├── routine.md         # Main routine definition
        │   │   ├── config.json        # Routine-specific settings
        │   │   └── checks/
        │   │       ├── git-status.sh
        │   │       ├── typescript.sh
        │   │       ├── supabase.sh
        │   │       └── ebay-api.sh
        │   │
        │   └── rc-2/
        │       ├── routine.md
        │       ├── config.json
        │       └── checks/
        │           └── quick-api.sh
        │
        ├── nightly/
        │   └── rc-1/
        │       ├── routine.md
        │       ├── config.json
        │       └── scripts/
        │           ├── cache-cleaner.sh
        │           └── log-rotator.sh
        │
        └── shared/                    # Reusable across routines
            ├── checks/
            │   └── redis-ping.sh
            └── templates/
                └── ascii-dashboard.md
```

**Note:** This follows Claude Code convention of using `.claude/` with plugin namespacing.

### config.json Schema

```json
{
  "project_name": "Reseller Central",
  "prefix": "rc",
  "defaults": {
    "morning": "rc-1",
    "nightly": "pk"
  },
  "routines": {
    "morning": [
      {
        "id": "rc-1",
        "name": "Full E-Commerce Check",
        "description": "eBay API, Redis, Supabase, BullMQ",
        "created": "2025-12-03T10:30:00Z",
        "based_on": "pk"
      },
      {
        "id": "rc-2",
        "name": "Quick API Check",
        "description": "Just eBay and database",
        "created": "2025-12-03T14:00:00Z",
        "based_on": "rc-1"
      }
    ],
    "nightly": [
      {
        "id": "rc-1",
        "name": "Full Cleanup",
        "description": "Caches, logs, git maintenance",
        "created": "2025-12-03T10:35:00Z",
        "based_on": "pk"
      }
    ]
  }
}
```

---

## Command Behaviors

### `/popkit:morning` (no arguments)

1. Check for `.claude/popkit/config.json`
2. If exists, read `defaults.morning`
3. Run that routine
4. Display startup banner:

```
┌─────────────────────────────────────────────────────────────┐
│ Morning Routine: rc-1 (Full E-Commerce Check)               │
│ Project: Reseller Central                                   │
│ Other routines: pk, rc-2 | Run: /popkit:morning list        │
└─────────────────────────────────────────────────────────────┘

+==================================================================+
|                  Morning Development Status                       |
...
```

If no config exists:
```
┌─────────────────────────────────────────────────────────────┐
│ Morning Routine: pk (PopKit Standard)                       │
│ Project: Reseller Central                                   │
│ Tip: Create a custom routine with /popkit:morning generate  │
└─────────────────────────────────────────────────────────────┘
```

### `/popkit:morning run <id>`

Run a specific routine by ID:

```bash
/popkit:morning run pk        # Run popkit universal
/popkit:morning run rc-1      # Run project routine #1
/popkit:morning run rc-2      # Run project routine #2
```

### `/popkit:morning generate`

Interactive generation flow:

```
/popkit:morning generate

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

✓ Routine rc-1 created!

Set as default? [Y/n] y
✓ Default morning routine set to rc-1

Run it now? [Y/n] y
```

**Future Enhancement:** Accept unstructured prompt for AI-assisted generation:
```
/popkit:morning generate "I need to check eBay OAuth tokens,
Redis for BullMQ, and make sure Supabase is running"
```

### `/popkit:morning list`

```
/popkit:morning list

Morning Routines for: Reseller Central

| ID    | Name                  | Default | Created    |
|-------|-----------------------|---------|------------|
| pk    | PopKit Standard       |         | (built-in) |
| rc-1  | Full E-Commerce Check | ✓       | 2025-12-03 |
| rc-2  | Quick API Check       |         | 2025-12-03 |

Slots available: 3 of 5

Commands:
  /popkit:morning run <id>     Run specific routine
  /popkit:morning set <id>     Change default
  /popkit:morning generate     Create new routine
  /popkit:morning edit <id>    Edit routine
  /popkit:morning delete <id>  Delete routine
```

### `/popkit:morning set <id>`

```
/popkit:morning set rc-2

Default morning routine changed: rc-1 → rc-2

Next time you run /popkit:morning, it will use:
  rc-2: Quick API Check
```

### `/popkit:morning edit <id>`

```
/popkit:morning edit rc-1

Opening routine for editing: rc-1 (Full E-Commerce Check)

Current checks:
  [x] Git status
  [x] TypeScript errors
  [x] Lint status
  [x] Supabase connection
  [x] Redis connection
  [x] eBay API credentials
  [ ] Run full test suite
  [ ] Security audit

Toggle checks or describe changes:
> Add BullMQ queue health check

Adding BullMQ health check...
✓ Routine rc-1 updated
```

### `/popkit:morning delete <id>`

```
/popkit:morning delete rc-2

Delete routine rc-2 (Quick API Check)? [y/N] y

✓ Routine rc-2 deleted
✓ Folder removed: .claude/popkit/routines/morning/rc-2/

Note: rc-1 is still your default morning routine.
```

**Protection:** Cannot delete `pk` (built-in) or the current default without changing default first.

---

## Routine File Format

### Project Routine: `.claude/popkit/routines/morning/rc-1/routine.md`

```markdown
---
id: rc-1
name: Full E-Commerce Check
type: morning
project: Reseller Central
prefix: rc
based_on: pk
created: 2025-12-03T10:30:00Z
modified: 2025-12-03T14:00:00Z
---

# Morning Routine: Full E-Commerce Check

Custom morning health check for Reseller Central e-commerce platform.

## Checks

### Git Status
```bash
git status --porcelain
git log --oneline -3
```

### Code Quality
```bash
npx tsc --noEmit 2>&1 | head -20
npx eslint . --max-warnings 10 2>&1 | tail -5
```

### Services

#### Supabase
```bash
curl -s http://localhost:54321/health
psql -h localhost -p 54322 -U postgres -c '\q' 2>/dev/null
```

#### Redis
```bash
docker exec popkit-redis redis-cli ping
```

#### eBay API
```bash
# Check OAuth token expiry
cat .env | grep EBAY_TOKEN_EXPIRY
# Verify API connectivity
curl -s -H "Authorization: Bearer $EBAY_ACCESS_TOKEN" \
  https://api.ebay.com/sell/account/v1/privilege
```

### BullMQ
```bash
# Check queue status via Redis
docker exec popkit-redis redis-cli LLEN bull:default:wait
```

## Score Calculation

| Check | Points | Criteria |
|-------|--------|----------|
| Git clean | 20 | No uncommitted changes |
| TypeScript | 15 | No type errors |
| Lint | 10 | No lint errors |
| Supabase | 20 | Both API and DB responding |
| Redis | 15 | Ping successful |
| eBay API | 20 | Token valid, API responding |

Total: 100 points
```

---

## Flags for PopKit Universal Routine

The `pk` routine supports these flags:

| Flag | Description |
|------|-------------|
| `--full` | Include tests + security audit |
| `--skip-tests` | Skip test execution |
| `--skip-services` | Skip service health checks |
| `--simple` | Markdown tables instead of ASCII |
| `--no-nightly` | Skip "From Last Night" section |
| `--no-debt` | Skip technical debt check |

Example:
```bash
/popkit:morning run pk --full          # Everything including slow checks
/popkit:morning run pk --skip-services # Just git + code quality
```

Project routines can also accept flags (passed through):
```bash
/popkit:morning run rc-1 --simple      # Project routine with markdown output
```

---

## Implementation Plan

### Phase 1: Storage Infrastructure
1. Create `.claude/popkit/routines/` directory structure
2. Implement `config.json` schema and read/write
3. Implement prefix generation algorithm
4. Add collision detection

### Phase 2: Core Commands
1. Refactor `morning.md` with new subcommand structure
2. Implement `run`, `list`, `set` subcommands
3. Add startup banner with routine indication
4. Implement flag passthrough

### Phase 3: Generate Flow
1. Refactor `generate` to create routine files (not separate commands)
2. Interactive check selection
3. Project detection and auto-configuration
4. Config.json updates

### Phase 4: Edit/Delete
1. Implement `edit` subcommand
2. Implement `delete` subcommand with protections
3. Add slot limit enforcement (5 max)

### Phase 5: Nightly Parity
1. Apply same structure to `nightly.md`
2. Share config.json storage
3. Ensure consistent UX

### Phase 6: Documentation & Cleanup
1. Update CLAUDE.md
2. Remove old generate-based approach references
3. Create GitHub issues for tracking
4. Migration guide for existing users

---

## Migration Path

For users who already have `/rc:morning` style commands:

1. **Detection:** On first run, detect existing `[prefix]:morning.md` commands
2. **Offer migration:**
   ```
   Found existing command: /rc:morning

   Migrate to new routine system? [Y/n]

   This will:
   - Import as routine rc-1
   - Set rc-1 as default
   - Keep old command file (can delete manually)
   ```
3. **Import:** Parse existing command and create routine file
4. **Graceful coexistence:** Old commands still work during transition

---

## GitHub Issues (Created)

| Issue | Title | Status |
|-------|-------|--------|
| #28 | [Epic] Unified Routine Management System | Open |
| #29 | [Feature] Routine storage infrastructure | Open |
| #30 | [Feature] Morning command routine subcommands | Open |
| #31 | [Feature] Routine generate refactor | Open |
| #32 | [Feature] Routine edit/delete subcommands | Open |
| #33 | [Feature] Nightly command routine parity | Open |
| #34 | [Docs] Routine management documentation | Open |

---

## Open Questions

1. **Prompt-based generation:** Should `generate` accept a natural language description?
   - Defer to future enhancement issue

2. **Routine sharing:** Should routines be exportable/importable between projects?
   - Defer - YAGNI for now

3. **Routine templates:** Should popkit ship with optional templates (e-commerce, SaaS, etc.)?
   - Defer - let patterns emerge from usage first

---

## Approval Checklist

- [x] Command structure approved
- [x] Storage format approved (`.claude/popkit/`)
- [x] Naming convention (prefix-number) approved
- [x] Migration path approved
- [x] Implementation phases approved
- [x] Ready for implementation
