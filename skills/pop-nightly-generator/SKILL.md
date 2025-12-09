---
name: nightly-generator
description: "Use when you want to create a project-specific nightly cleanup and maintenance routine - analyzes the project's tech stack and generates customized cleanup routines for caches, build artifacts, and domain-specific maintenance. Detects Next.js, Node.js, Python, Rust, etc. and creates appropriate cleanup targets. Do NOT use if the generic /popkit:routine nightly is sufficient - only generate custom routines for projects with unique cleanup requirements or domain-specific maintenance needs."
---

# Nightly Generator

## Overview

Generate a project-specific nightly cleanup and maintenance command based on the project's tech stack, services, and domain. The generated command extends `/popkit:nightly` with project-aware cleanup and maintenance.

**Core principle:** Detect what needs cleanup for THIS project and automate it every night.

**Trigger:** `/popkit:nightly generate` command or via `/popkit:morning generate --nightly`

## What Gets Generated

```
.claude/commands/
└── [project]:nightly.md     # Project-specific nightly cleanup
```

## Detection Process

### Step 0: Detect MCP Infrastructure

Before detecting tech stack, check for existing MCP server infrastructure:

```bash
# Check for MCP SDK in package.json
grep -q "@modelcontextprotocol/sdk" package.json 2>/dev/null && echo "MCP SDK: Found"

# Check for .mcp.json configuration
test -f .mcp.json && echo "MCP Config: Found"

# Check for MCP server directories
ls -d packages/*/mcp packages/*/src/mcp **/mcp-server 2>/dev/null && echo "MCP Directories: Found"
```

**Decision Tree:**

```
Has MCP SDK or .mcp.json?
  │
  ├─ YES → Has nightly/cleanup MCP tools?
  │         │
  │         ├─ YES → Generate MCP wrapper commands
  │         │        - Minimal 10-20 line wrappers
  │         │        - Call mcp__server__tool directly
  │         │        - Skip bash-based cleanup
  │         │
  │         └─ NO → Generate hybrid commands
  │                  - MCP for available tools
  │                  - Bash for cleanup operations
  │
  └─ NO → Generate bash-based commands (full)
          - Complete tech stack detection
          - Comprehensive bash scripts
```

**MCP Nightly Tool Detection:**

Look for these patterns in MCP tool names:
- `nightly_routine`, `nightly_*` - Full nightly routines
- `cleanup_*`, `clean_*` - Cleanup operations
- `*_maintenance` - Maintenance tasks
- `backup_*`, `save_*` - State preservation

### Step 1: Detect Tech Stack

Analyze project for frameworks and build systems:

```bash
# Package managers and their cache locations
ls package.json Cargo.toml pyproject.toml go.mod requirements.txt 2>/dev/null

# Framework detection (build artifact locations)
grep -l "next" package.json 2>/dev/null && echo "Next.js: .next/"
grep -l "vite" package.json 2>/dev/null && echo "Vite: dist/"
grep -l "react-scripts" package.json 2>/dev/null && echo "CRA: build/"
grep -l "webpack" package.json 2>/dev/null && echo "Webpack: dist/"

# Cache detection
test -d node_modules/.cache && echo "Node cache: node_modules/.cache/"
test -f .eslintcache && echo "ESLint cache: .eslintcache"
test -f .tsbuildinfo && echo "TS cache: .tsbuildinfo"
test -d .pytest_cache && echo "Pytest cache: .pytest_cache/"
test -d __pycache__ && echo "Python cache: __pycache__/"
test -d target && echo "Rust target: target/"

# Test/coverage artifacts
test -d coverage && echo "Coverage: coverage/"
test -d .nyc_output && echo "NYC output: .nyc_output/"
```

### Step 2: Identify Cleanup Targets

Based on detected stack, determine cleanup operations:

| Detection | Cleanup Targets |
|-----------|-----------------|
| Next.js | `.next/`, `out/` |
| Vite | `dist/` |
| CRA | `build/` |
| General Node | `node_modules/.cache/`, `.eslintcache`, `.tsbuildinfo` |
| TypeScript | `*.tsbuildinfo`, `dist/` |
| Jest/Testing | `coverage/`, `.jest-cache/` |
| Python | `__pycache__/`, `.pytest_cache/`, `*.pyc` |
| Rust | `target/debug/` (not target/release) |
| Logs | `*.log` files older than 7 days |
| Temp Files | `*.tmp`, `.DS_Store` |

### Step 3: Identify Maintenance Tasks

| Detection | Maintenance Task |
|-----------|------------------|
| Git repo | `git gc --auto`, `git fetch --prune` |
| Package.json | `npm audit` |
| Prisma | `prisma generate` check |
| Docker | `docker system prune --filter "until=24h"` |
| External APIs | Token expiry checks |

### Step 4: Detect Project Prefix

Determine command prefix from project (same as morning-generator):

```bash
# From package.json name
jq -r '.name' package.json | tr -d '@/' | cut -d'-' -f1

# From directory name
basename $(pwd)

# From existing commands
ls .claude/commands/*:*.md 2>/dev/null | head -1 | cut -d':' -f1
```

### Step 5: Generate Command

Create `.claude/commands/[prefix]:nightly.md`:

```markdown
---
description: Nightly cleanup and maintenance for [Project Name] (Sleep Score 0-100)
---

# /[prefix]:nightly - [Project] Nightly Cleanup

End-of-day cleanup and maintenance for [Project Name].

## Usage

\`\`\`
/[prefix]:nightly              # Full nightly report
/[prefix]:nightly quick        # Compact summary
/[prefix]:nightly cleanup --auto-fix    # Execute cleanup
/[prefix]:nightly git --auto-fix        # Git maintenance
\`\`\`

## Cleanup Targets

| Category | Target | Size |
|----------|--------|------|
| Build Artifacts | [detected] | - |
| Caches | [detected] | - |
| Temp Files | [detected] | - |
| Old Logs | [detected] | - |

## Cleanup Commands

\`\`\`bash
# Build artifacts
rm -rf [detected paths]

# Caches
rm -rf [detected paths]

# Temp files
find . -name "*.tmp" -type f -delete
find . -name "*.log" -mtime +7 -type f -delete
\`\`\`

## Git Maintenance

\`\`\`bash
git gc --auto
git fetch --prune
git branch --merged main | grep -v "^\*\|main\|master" | xargs -r git branch -d
\`\`\`

## Security Check

\`\`\`bash
npm audit
\`\`\`

## Sleep Score

| Check | Points |
|-------|--------|
| No uncommitted changes | 30 |
| Session state saved | 20 |
| Git maintenance done | 15 |
| Security audit clean | 15 |
| Caches under limit | 10 |
| Logs rotated | 10 |

## Domain-Specific

[Based on project type]
- [ ] [API token expiry check]
- [ ] [Database backup status]
- [ ] [External service cleanup]
```

## Stack-Specific Templates

### Next.js Project

```markdown
## Cleanup Targets

| Category | Target | Typical Size |
|----------|--------|--------------|
| Build | `.next/` | 100-500 MB |
| Build | `out/` | 50-200 MB |
| Cache | `node_modules/.cache/` | 50-200 MB |
| Cache | `.eslintcache` | < 1 MB |
| Cache | `.tsbuildinfo` | < 1 MB |
| Coverage | `coverage/` | 10-50 MB |

## Cleanup Commands

\`\`\`bash
# Build artifacts (safe to delete)
rm -rf .next/ out/

# Caches (safe to delete)
rm -rf node_modules/.cache .eslintcache .tsbuildinfo

# Coverage (safe to delete)
rm -rf coverage/

# Old logs
find . -name "*.log" -mtime +7 -type f -delete
\`\`\`
```

### Python Project

```markdown
## Cleanup Targets

| Category | Target | Typical Size |
|----------|--------|--------------|
| Cache | `__pycache__/` | 10-50 MB |
| Cache | `.pytest_cache/` | 1-10 MB |
| Cache | `.mypy_cache/` | 5-20 MB |
| Build | `dist/` | varies |
| Build | `build/` | varies |
| Build | `*.egg-info/` | < 1 MB |
| Compiled | `*.pyc` | varies |

## Cleanup Commands

\`\`\`bash
# Python caches
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null

# Build artifacts
rm -rf dist/ build/ *.egg-info/

# Compiled files
find . -name "*.pyc" -type f -delete
\`\`\`
```

### Rust Project

```markdown
## Cleanup Targets

| Category | Target | Typical Size |
|----------|--------|--------------|
| Debug Build | `target/debug/` | 1-5 GB |
| Incremental | `target/debug/incremental/` | 500 MB-2 GB |

**Note:** Never delete `target/release/` automatically.

## Cleanup Commands

\`\`\`bash
# Debug artifacts only (preserves release builds)
rm -rf target/debug/

# Or more conservative - just incremental
rm -rf target/debug/incremental/

# Cargo clean (nuclear option)
# cargo clean
\`\`\`
```

### E-Commerce / API Project

```markdown
## Domain-Specific Cleanup

| Target | Description | Command |
|--------|-------------|---------|
| API Cache | Cached API responses | `rm -rf .api-cache/` |
| Token Cache | OAuth token cache | Check expiry, don't delete |
| Image Cache | Processed images | `find uploads/cache -mtime +7 -delete` |

## Domain-Specific Checks

| Check | Description |
|-------|-------------|
| OAuth Tokens | Alert if expiring within 24h |
| API Rate Limits | Check remaining quota |
| Database Backup | Verify last backup < 24h |
```

## Post-Generation

After generating:

```
Nightly command generated!

Created:
  .claude/commands/[prefix]:nightly.md

Detected stack:
  - Framework: Next.js 14
  - Database: Supabase (local)
  - Cache: Redis
  - Tests: Jest

Cleanup targets configured:
  ✓ .next/ (build artifacts)
  ✓ coverage/ (test coverage)
  ✓ node_modules/.cache/ (npm cache)
  ✓ .eslintcache (lint cache)
  ✓ Old log files (7+ days)

Maintenance configured:
  ✓ Git gc and prune
  ✓ npm audit
  ✓ Branch cleanup

You can now run:
  /[prefix]:nightly

Would you like me to also generate/update /[prefix]:morning?
```

## MCP Wrapper Mode

When MCP infrastructure with nightly tools is detected:

```markdown
---
description: Nightly cleanup via MCP (Sleep Score 0-100)
---

# /[prefix]:nightly - [Project] Nightly Cleanup

Run the MCP-based nightly routine.

## Implementation

Run the `mcp__[server]__nightly_routine` MCP tool.

If unavailable, run individual cleanup tools:
- `mcp__[server]__cleanup_caches`
- `mcp__[server]__git_maintenance`
- `mcp__[server]__security_audit`

Display the Sleep Score and any issues.
```

## Integration

**Requires:**
- Project structure (package.json, Cargo.toml, etc.)
- Optional: Existing service configuration

**Enables:**
- Daily cleanup automation
- Disk space management
- Security audit automation
- Session state preservation
- Team-wide nightly routine

## Customization

After generation, customize by:
1. Adding project-specific cleanup targets
2. Adjusting retention periods for logs
3. Adding domain-specific maintenance tasks
4. Including external service cleanup
5. Adding backup verification checks
