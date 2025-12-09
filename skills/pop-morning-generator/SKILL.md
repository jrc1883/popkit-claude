---
name: morning-generator
description: "Use when you want to create a project-specific morning health check routine - analyzes the project's tech stack and generates customized health checks for services, databases, and domain-specific validations. Detects Next.js, Express, Supabase, Redis, etc. and creates appropriate checks. Do NOT use if the generic /popkit:routine morning is sufficient - only generate custom routines for projects with unique health check requirements."
---

# Morning Generator

## Overview

Generate a project-specific morning health check command based on the project's tech stack, services, and domain. The generated command extends `/popkit:morning` with project-aware checks.

**Core principle:** Detect what matters for THIS project and check it every morning.

**Trigger:** `/popkit:generate-morning` command or as part of `/popkit:init-project`

## What Gets Generated

```
.claude/commands/
├── [project]:morning.md     # Project-specific morning check
└── [project]:nightly.md     # Project-specific nightly cleanup (optional)
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
  ├─ YES → Has health-related MCP tools?
  │         │
  │         ├─ YES → Generate MCP wrapper commands (Step 5)
  │         │        - Minimal 10-20 line wrappers
  │         │        - Call mcp__server__tool directly
  │         │        - Skip bash-based checks
  │         │
  │         └─ NO → Generate hybrid commands
  │                  - MCP for available tools
  │                  - Bash for missing checks
  │
  └─ NO → Generate bash-based commands (Step 1-4)
          - Full tech stack detection
          - Comprehensive bash scripts
```

**MCP Health Tool Detection:**

Look for these patterns in MCP tool names:
- `morning_routine`, `nightly_routine` - Daily health routines
- `check_*` (check_database, check_api, etc.) - Explicit checks
- `*_health`, `*_status` - Status queries
- `ping_*`, `verify_*` - Connectivity tests

**Example MCP Detection Output:**

```
MCP Infrastructure Detected!

Server: mcp__reseller-central-dev
SDK Version: ^1.0.0
Config: .mcp.json

Health-Related Tools (8):
  ✓ morning_routine - Daily health check
  ✓ check_api - API server status
  ✓ check_database - Database connectivity
  ✓ check_redis - Redis connection
  ✓ check_ebay_connection - eBay API status
  ✓ nightly_routine - Sleep score
  ✓ system_overview - Full system status
  ✓ verify_oauth - OAuth token status

Recommendation: Generate MCP wrapper commands
```

When MCP is detected, use AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "MCP health tools detected. How should we generate the morning command?"
- header: "Generator"
- options:
  - label: "MCP Wrapper"
    description: "Minimal 10-20 line wrapper calling MCP tools (recommended)"
  - label: "Bash Script"
    description: "Full bash-based checks (100+ lines, ignore MCP)"
  - label: "Hybrid"
    description: "MCP for available tools, bash for gaps"
- multiSelect: false
```

If MCP wrapper selected, skip to **Step 5: Generate MCP Wrapper Commands**.

### Step 1: Detect Tech Stack

Analyze project for frameworks and services:

```bash
# Package managers
ls package.json Cargo.toml pyproject.toml go.mod requirements.txt 2>/dev/null

# Framework detection
grep -l "next" package.json 2>/dev/null && echo "Next.js"
grep -l "express" package.json 2>/dev/null && echo "Express"
grep -l "react" package.json 2>/dev/null && echo "React"
grep -l "vue" package.json 2>/dev/null && echo "Vue"
grep -l "django" requirements.txt 2>/dev/null && echo "Django"
grep -l "fastapi" requirements.txt 2>/dev/null && echo "FastAPI"

# Database detection
ls prisma/ 2>/dev/null && echo "Prisma"
ls supabase/ 2>/dev/null && echo "Supabase"
grep -l "mongoose" package.json 2>/dev/null && echo "MongoDB"
grep -l "pg" package.json 2>/dev/null && echo "PostgreSQL"
grep -l "redis" package.json 2>/dev/null && echo "Redis"

# Docker/services
ls docker-compose.yml docker-compose.yaml 2>/dev/null && echo "Docker Compose"
```

### Step 2: Identify Health Checks

Based on detected stack, determine checks:

| Detection | Health Check Added |
|-----------|-------------------|
| Next.js | Dev server on port 3000/3001/3002 |
| Express | API server on configured port |
| Vite | Dev server on port 5173 |
| Supabase local | Supabase services (54321-54334) |
| PostgreSQL | Database connection |
| Redis | Redis connection |
| MongoDB | MongoDB connection |
| Docker Compose | Container status |
| Prisma | Database schema sync |
| eBay SDK | eBay API credentials/OAuth |
| Stripe | Stripe API key validation |

### Step 3: Detect Project Prefix

Determine command prefix from project:

```bash
# From package.json name
jq -r '.name' package.json | tr -d '@/' | cut -d'-' -f1

# From directory name
basename $(pwd)

# From existing commands
ls .claude/commands/*:*.md 2>/dev/null | head -1 | cut -d':' -f1
```

Examples:
- genesis → `/genesis:morning`
- reseller-central → `/rc:morning`
- my-app → `/myapp:morning`

### Step 4: Generate Command

Create `.claude/commands/[prefix]:morning.md`:

```markdown
---
description: Morning health check for [Project Name] (Ready to Code score 0-100)
---

# /[prefix]:morning - [Project] Morning Check

Comprehensive health check for [Project Name] development.

## Usage

\`\`\`
/[prefix]:morning           # Full morning report
/[prefix]:morning quick     # Compact summary
\`\`\`

## Checks

### Services
[Generated based on detection]
- [ ] [Service 1] on port [X]
- [ ] [Service 2] on port [Y]
- [ ] [Database] connection

### Git Status
- Branch, uncommitted changes, remote sync

### Code Quality
[Based on detected tools]
- [ ] TypeScript errors
- [ ] Lint status
- [ ] Test results

### Domain-Specific
[Based on project type]
- [ ] [API credentials]
- [ ] [External service status]

## Ready to Code Score

| Check | Points |
|-------|--------|
| Services running | 30 |
| Clean working directory | 20 |
| Remote sync | 10 |
| TypeScript clean | 15 |
| Tests passing | 25 |

## Commands Reference

\`\`\`bash
# Start services
[Detected start commands]

# Check specific service
[Service-specific commands]

# Quick fixes
[Common fix commands]
\`\`\`
```

## Stack-Specific Templates

### Next.js + Supabase

```markdown
## Services

| Service | Port | Check Command |
|---------|------|---------------|
| Next.js | 3000 | `curl -s localhost:3000 > /dev/null` |
| Supabase API | 54321 | `curl -s localhost:54321/health` |
| Supabase DB | 54322 | `psql -h localhost -p 54322 -U postgres -c '\q'` |
| Supabase Studio | 54323 | `curl -s localhost:54323` |

## Start All Services

\`\`\`bash
# Start Supabase
npx supabase start

# Start Next.js
npm run dev
\`\`\`
```

### Express + Redis + PostgreSQL

```markdown
## Services

| Service | Port | Check Command |
|---------|------|---------------|
| Express API | 5001 | `curl -s localhost:5001/health` |
| PostgreSQL | 5432 | `pg_isready -h localhost -p 5432` |
| Redis | 6379 | `docker exec <container> redis-cli ping` |

## Start All Services

\`\`\`bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Start API
npm run dev:server
\`\`\`
```

### E-Commerce (with eBay)

```markdown
## Services

| Service | Port | Check Command |
|---------|------|---------------|
| API Server | 5001 | `curl -s localhost:5001/health` |
| Redis | 6379 | `docker exec <container> redis-cli ping` |
| Database | 5432 | `pg_isready` |

## Domain Checks

| Check | Description |
|-------|-------------|
| eBay OAuth | Token expiry and refresh |
| Cloudflare Tunnel | Required for webhooks |
| BullMQ | Job queue status |

## Critical Validations

- eBay OAuth token expires in: [X hours]
- Redis required for token refresh: [status]
- Webhook tunnel: [status]
```

## Post-Generation

After generating:

```
Morning command generated!

Created:
  .claude/commands/[prefix]:morning.md

Detected stack:
  - Framework: Next.js 14
  - Database: Supabase (local)
  - Cache: Redis
  - Tests: Jest

Health checks included:
  ✓ Next.js dev server (port 3000)
  ✓ Supabase services (ports 54321-54334)
  ✓ Redis connection
  ✓ TypeScript validation
  ✓ Jest test suite

You can now run:
  /[prefix]:morning
```

Then use AskUserQuestion to offer nightly generation:

```
Use AskUserQuestion tool with:
- question: "Would you like to also generate the nightly cleanup command?"
- header: "Nightly"
- options:
  - label: "Yes, generate"
    description: "Create /[prefix]:nightly for end-of-day cleanup"
  - label: "No, skip"
    description: "I'll generate it later if needed"
- multiSelect: false
```

## Integration

**Requires:**
- Project structure (package.json, etc.)
- Optional: Existing service configuration

**Enables:**
- Daily health checks
- Quick issue detection
- Consistent development startup
- Team-wide morning routine

### Step 5: Generate MCP Wrapper Commands (If MCP Detected)

When MCP infrastructure is detected with health tools, generate minimal wrapper commands instead of bash scripts:

**Template: `.claude/commands/[prefix]:morning.md`**

```markdown
---
description: Morning health check via MCP (Ready to Code score 0-100)
---

# /[prefix]:morning - [Project] Morning Check

Run the MCP-based morning health check.

## Implementation

Run the `mcp__[server]__morning_routine` MCP tool.

If unavailable, run individual checks:
- `mcp__[server]__check_database`
- `mcp__[server]__check_api`
- `mcp__[server]__check_redis`

Display the Ready to Code score and any issues.
```

**Benefits of MCP Wrappers:**

| Aspect | MCP Wrapper | Bash Command |
|--------|-------------|--------------|
| Lines of code | 10-20 | 100-200+ |
| Maintenance | Auto-syncs with MCP | Manual updates |
| Error handling | Structured JSON | Text parsing |
| Extensibility | Add to MCP server | Edit markdown |
| Agent integration | Direct tool calls | Shell out |

**Post-Generation (MCP Mode):**

```
Morning command generated! (MCP Wrapper Mode)

Created:
  .claude/commands/[prefix]:morning.md  (15 lines)

MCP Server Detected: mcp__[server-name]
Health Tools Available: 8

The generated command calls these MCP tools:
  ✓ morning_routine (primary)
  ✓ check_database (fallback)
  ✓ check_api (fallback)
  ✓ check_redis (fallback)

Benefits:
  - 15 lines vs 200+ bash lines
  - Structured JSON responses
  - Auto-syncs with MCP server updates

You can now run:
  /[prefix]:morning
```

## Customization

After generation, customize by:
1. Adding project-specific checks
2. Adjusting port numbers
3. Adding API credential validations
4. Including external service checks
