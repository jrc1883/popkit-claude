---
description: "init | analyze | embed | generate | mcp | setup | skills | observe [--power, --json]"
---

# /popkit:project - Project Analysis & Setup

Complete project lifecycle tools: initialization, analysis, configuration, customization, and cross-project observability.

## Usage

```
/popkit:project <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `init` | Initialize .claude/ structure with optional Power Mode |
| `analyze` | Deep codebase analysis (default) |
| `embed` | Embed project items for semantic search |
| `generate` | Full pipeline: analyze → skills → mcp → embed |
| `mcp` | Generate project-specific MCP server |
| `setup` | Configure pre-commit hooks and quality gates |
| `skills` | Generate custom skills from project patterns |
| `observe` | Cross-project dashboard (from monorepo) |

---

## Subcommand: init

Initialize a new project with complete Claude Code configuration, including optional Power Mode for multi-agent orchestration.

```
/popkit:project init                      # Initialize current directory
/popkit:project init my-app               # Initialize named project
/popkit:project init --power              # Initialize with Power Mode setup
```

### Process

Invokes the **pop-project-init** skill:

1. **Detect Project Type**
   - Node.js: package.json with react/next/vue/express
   - Python: requirements.txt, pyproject.toml, setup.py
   - Rust: Cargo.toml
   - Go: go.mod

2. **Create Directory Structure**
   ```
   .claude/
   ├── agents/           # Project-specific agents
   ├── commands/         # Custom slash commands
   ├── hooks/            # Hook scripts
   ├── skills/           # Project-specific skills
   ├── scripts/          # Utility scripts
   ├── logs/             # Log files
   ├── plans/            # Implementation plans
   ├── STATUS.json       # Session state
   └── settings.json     # Claude settings

   CLAUDE.md             # Project instructions
   ```

3. **Generate CLAUDE.md**
   - Project overview (from README.md or package.json)
   - Development notes (build, test commands)
   - Architecture patterns (detected from codebase)
   - Key files for reference

4. **Ask About Power Mode**
   - **Redis Mode**: Full parallel agents (requires Docker)
   - **File Mode**: Simpler coordination (no dependencies)
   - **Skip**: Set up later with `/popkit:power init`

### Output

```
/popkit:project init

Detecting project type...
[+] Node.js (Next.js 14) detected

Creating .claude/ structure...
[+] Directories created
[+] CLAUDE.md generated
[+] STATUS.json initialized
[+] .gitignore updated

Would you like to set up Power Mode for multi-agent orchestration?
  - Redis Mode: Full parallel agents (requires Docker)
  - File Mode: Simpler coordination (no dependencies)
  - Skip: Set up later with /popkit:power init

[User selects Redis Mode]

Setting up Power Mode...
[+] docker-compose.yml created
[+] Run 'docker compose up -d' to start Redis

Project initialized!

Recommended next steps:
1. Review and customize CLAUDE.md
2. Run /popkit:routine morning for project health check
3. Run /popkit:power init start to start Redis (if Docker installed)
4. Run /popkit:issue list to see GitHub issues
```

### Options

| Flag | Description |
|------|-------------|
| `--power` | Auto-select Power Mode (prompts for Redis vs File) |
| `--redis` | Use Redis Mode (requires Docker) |
| `--file` | Use File Mode (no dependencies) |
| `--skip-power` | Skip Power Mode setup entirely |

---

## Subcommand: analyze (default)

Comprehensive codebase analysis discovering architecture, patterns, dependencies, and improvement opportunities.

```
/popkit:project                       # Full analysis
/popkit:project analyze               # Same as above
/popkit:project analyze --quick       # Quick summary only
/popkit:project analyze --focus arch  # Focus on architecture
```

### Process

Invokes the **pop-analyze-project** skill:

1. **Structure Discovery**
   - Project type detection (Node.js, Python, Rust, Go, etc.)
   - Framework identification (React, Next.js, Express, Django, etc.)
   - Directory structure analysis

2. **Pattern Recognition**
   - Code organization patterns
   - Naming conventions
   - Import/export patterns
   - State management approaches

3. **Dependency Analysis**
   - Package dependencies and versions
   - Outdated or vulnerable packages
   - Unused dependencies

4. **Quality Assessment**
   - Test coverage estimation
   - Documentation completeness
   - Code complexity hotspots

5. **Improvement Opportunities**
   - Suggested refactorings
   - Missing best practices
   - Performance optimization targets

### Output

```
## Project Analysis: [Project Name]

### Identity
- Type: Next.js 14 with TypeScript
- Framework: React 18
- Database: Supabase (PostgreSQL)
- Testing: Jest + React Testing Library

### Architecture
- Pattern: Feature-based organization
- State: React Query + Context
- API: REST (App Router)

### Quality Metrics
- Test Coverage: ~65%
- TypeScript Strict: Yes
- Linting: ESLint + Prettier

### Patterns Detected
1. Server components for data fetching
2. Client components for interactivity
3. Supabase RLS for authorization

### Improvement Opportunities
1. [High] Add error boundaries to key routes
2. [Medium] Consolidate duplicate API error handling
3. [Low] Document the auth flow

### Recommended Next Steps
- Run `/popkit:project setup` to configure pre-commit hooks
- Run `/popkit:project mcp` to generate project-specific MCP server
```

### Options

| Flag | Description |
|------|-------------|
| `--quick` | Quick summary only (5-10 lines) |
| `--focus <area>` | Focus analysis: `arch`, `deps`, `quality`, `patterns` |
| `--output <file>` | Save analysis to file |
| `-T`, `--thinking` | Enable extended thinking for deep analysis |
| `--no-thinking` | Disable extended thinking (use default) |
| `--think-budget N` | Set thinking token budget (default: 10000) |

---

## Subcommand: embed

Embed project-local items (skills, agents, commands) for semantic search and discovery.

```
/popkit:project embed                   # Embed all project items
/popkit:project embed --status          # Show embedding status only
/popkit:project embed --force           # Re-embed all items
/popkit:project embed --type skill      # Embed only skills
```

### Process

Invokes the **pop-embed-project** skill:

1. **Scan Project**
   - Find all `.claude/skills/*/SKILL.md`
   - Find all `.claude/agents/*/AGENT.md`
   - Find all `.claude/commands/*.md`
   - Find all `.generated/` items

2. **Check for Changes**
   - Compare content hash with stored embeddings
   - Skip unchanged items unless `--force`

3. **Embed Items**
   - Call Voyage API for new/changed items
   - Respect 3 RPM rate limit (21s delays)
   - Store with project_path metadata

4. **Report Results**
   - Items found
   - Items embedded
   - Items skipped (unchanged)
   - Items with errors

### Output

```
Scanning project: /path/to/project

Found 8 items:
- 3 project-skill
- 2 project-agent
- 3 project-command

Embedding 5 new/changed items...
Waiting 21s for rate limit...

Embedding complete!
  Embedded: 5
  Skipped: 3 (unchanged)
  Errors: 0
```

### Status Output

```
/popkit:project embed --status

Project: /path/to/project
API Available: Yes

Items Found:    8
Items Embedded: 8
Items Stale:    0
Items Missing:  0

By Type:
  project-skill: 3/3
  project-agent: 2/2
  project-command: 3/3
```

### Options

| Flag | Description |
|------|-------------|
| `--status` | Show embedding status without embedding |
| `--force`, `-f` | Re-embed all items even if unchanged |
| `--type <type>` | Filter to type: `skill`, `agent`, `command` |

---

## Subcommand: generate

Run the full project generation pipeline: analyze → skills → mcp → embed.

```
/popkit:project generate                # Full pipeline
/popkit:project generate --no-embed     # Skip embedding step
/popkit:project generate --no-skills    # Skip skill generation
/popkit:project generate --no-mcp       # Skip MCP generation
/popkit:project generate --quick        # Quick analysis
```

### Process

Invokes multiple skills in sequence:

1. **Analyze Project** (pop-analyze-project)
   - Run with `--json` flag
   - Save to `.claude/analysis.json`
   - Detect patterns, frameworks, commands

2. **Generate Skills** (pop-skill-generator)
   - Use analysis for pattern-based generation
   - Create skills for detected patterns
   - Save to `.claude/skills/`

3. **Generate MCP Server** (pop-mcp-generator)
   - Use analysis for tool selection
   - Create project-specific tools
   - Save to `.claude/mcp-servers/`

4. **Embed Content** (pop-embed-content)
   - Embed all generated items
   - Export `tool_embeddings.json`
   - Enable semantic discovery

### Output

```
/popkit:project generate

PopKit Project Generation Pipeline
═══════════════════════════════════

Step 1/4: Analyze Project
─────────────────────────
Running analysis with --json output...
✓ Analysis saved to .claude/analysis.json

Detected:
  Framework: Next.js 14 (App Router)
  Database: Supabase
  Testing: Jest + RTL
  Patterns: 6 detected

Step 2/4: Generate Skills
─────────────────────────
Generating skills from detected patterns...
✓ project:deploy (nextjs + vercel-config)
✓ project:db-migrate (supabase)
✓ project:testing (colocated-tests)
✓ project:components (feature-based-organization)

Skills saved: 4

Step 3/4: Generate MCP Server
─────────────────────────────
Generating MCP server with analysis...
✓ health:dev-server
✓ health:database
✓ quality:typecheck
✓ quality:lint
✓ quality:test
✓ git:status
✓ git:diff
✓ search:tools

MCP server saved: .claude/mcp-servers/[project]-dev/

Step 4/4: Embed Content
───────────────────────
Embedding generated content...
✓ Embedded 4 skills
✓ Embedded 8 tools
✓ Exported tool_embeddings.json

Pipeline Complete!
══════════════════

Generated:
  .claude/analysis.json
  .claude/skills/ (4 skills)
  .claude/mcp-servers/[project]-dev/
  .claude/tool_embeddings.json

Next Steps:
1. cd .claude/mcp-servers/[project]-dev
2. npm install && npm run build
3. Restart Claude Code to load MCP server

Would you like me to build the MCP server now?
```

### Options

| Flag | Description |
|------|-------------|
| `--no-embed` | Skip embedding step |
| `--no-skills` | Skip skill generation |
| `--no-mcp` | Skip MCP server generation |
| `--quick` | Use quick analysis mode |
| `--force` | Force re-generation even if exists |

---

## Subcommand: mcp

Generate a project-specific MCP server with semantic tools, health checks, and project awareness.

```
/popkit:project mcp                   # Generate MCP server
/popkit:project mcp --name myproject  # Custom server name
/popkit:project mcp --minimal         # Minimal toolset
```

### Process

Invokes the **pop-mcp-generator** skill:

1. **Analyze Project**
   - Detect tech stack and frameworks
   - Identify key entry points
   - Find test and build commands

2. **Generate Tools**
   - Health check tools (dev server, database, services)
   - Git tools (status, diff, recent commits)
   - Quality tools (typecheck, lint, tests)
   - Project-specific tools based on stack

3. **Create MCP Server**
   - TypeScript implementation
   - Tool discovery via embeddings
   - Configuration for Claude Code

4. **Configure Integration**
   - Add to `.mcp.json`
   - Create npm scripts
   - Document available tools

### Output

```
Generating MCP server for [Project Name]...

Detected Stack:
- Framework: Next.js 14
- Database: Supabase
- Tests: Jest

Tools Generated:
- health:dev-server - Check Next.js dev server (port 3000)
- health:database - Check Supabase connection
- git:status - Show working tree status
- git:recent - Show recent commits
- quality:typecheck - Run TypeScript check
- quality:lint - Run ESLint
- quality:test - Run Jest tests

Files Created:
- .claude/mcp-server/index.ts
- .claude/mcp-server/package.json
- .claude/mcp-server/tsconfig.json

Configuration Added:
- .mcp.json updated with server entry

Next Steps:
1. cd .claude/mcp-server && npm install && npm run build
2. Restart Claude Code to load the MCP server
3. Tools will appear as mcp__[project]__[tool]
```

### Options

| Flag | Description |
|------|-------------|
| `--name <name>` | Custom server name (default: project name) |
| `--minimal` | Generate minimal toolset (health + git only) |
| `--no-install` | Skip npm install step |
| `-T`, `--thinking` | Enable extended thinking for semantic tool generation |
| `--no-thinking` | Disable extended thinking (use default) |
| `--think-budget N` | Set thinking token budget (default: 10000) |

---

## Subcommand: setup

Configure pre-commit hooks and quality gates for the project.

```
/popkit:project setup                 # Full setup with prompts
/popkit:project setup --level standard
/popkit:project setup --level strict
/popkit:project setup --ci            # Also configure CI workflow
```

### Process

Invokes the **pop-setup-precommit** skill:

1. **Detect Project Type**
   - Node.js: Husky + lint-staged + commitlint
   - Python: pre-commit framework
   - Rust: cargo-husky

2. **Install Dependencies**
   - Pre-commit hook framework
   - Linting tools (if not present)
   - Commit message validator

3. **Configure Hooks**
   - Pre-commit: Type check, lint, format, test (staged files)
   - Commit-msg: Conventional commit validation

4. **Optional CI Integration**
   - GitHub Actions workflow
   - Same checks as local hooks

### Quality Levels

| Level | Checks |
|-------|--------|
| `basic` | Whitespace, file endings, YAML/JSON syntax |
| `standard` | Basic + lint, format, type check |
| `strict` | Standard + tests, coverage check, commit validation |
| `enterprise` | Strict + security scan, license check, dependency audit |

### Output

```
Setting up pre-commit hooks...

Project Type: Node.js (TypeScript)
Quality Level: standard

Installing:
- husky (pre-commit framework)
- lint-staged (staged file linting)
- @commitlint/cli (commit validation)

Configuring:
- .husky/pre-commit: tsc + lint-staged
- .husky/commit-msg: commitlint
- .lintstagedrc.json: ESLint + Prettier
- commitlint.config.js: Conventional commits

Hooks installed! Testing...
[ok] Pre-commit hook working
[ok] Commit-msg hook working

Commands:
- Skip once: git commit --no-verify
- Run manually: npx lint-staged
```

### Options

| Flag | Description |
|------|-------------|
| `--level <level>` | Quality level: `basic`, `standard`, `strict`, `enterprise` |
| `--ci` | Also generate CI workflow |
| `--no-test` | Skip hook verification |

---

## Subcommand: skills

Generate custom skills from project patterns and common workflows.

```
/popkit:project skills                # Analyze and suggest skills
/popkit:project skills generate       # Generate recommended skills
/popkit:project skills list           # List existing project skills
```

### Process

Invokes the **pop-skill-generator** skill:

1. **Analyze Patterns**
   - Common command sequences you run
   - Project-specific conventions
   - Repeated code patterns

2. **Suggest Skills**
   - Skills that would save time
   - Skills matching project domain
   - Skills for complex workflows

3. **Generate Skills**
   - Create SKILL.md files
   - Add to `.claude/skills/`
   - Document usage

### Output

```
Analyzing project patterns...

Suggested Skills:

1. project:deploy
   - Detected: Manual deploy steps in DEPLOYMENT.md
   - Would automate: Build, test, deploy to Vercel
   - Confidence: High

2. project:db-migration
   - Detected: Prisma migration commands used frequently
   - Would automate: Generate, apply, push migrations
   - Confidence: Medium

3. project:feature-flag
   - Detected: LaunchDarkly integration
   - Would automate: Create/toggle feature flags
   - Confidence: Medium

Generate these skills? [y/N]

Generating skills...
[ok] .claude/skills/deploy/SKILL.md created
[ok] .claude/skills/db-migration/SKILL.md created
[ok] .claude/skills/feature-flag/SKILL.md created

Skills are now available via the Skill tool.
```

---

## Examples

```bash
# Analyze current project
/popkit:project
/popkit:project analyze

# Quick analysis focused on architecture
/popkit:project analyze --quick --focus arch

# Generate MCP server
/popkit:project mcp

# Setup pre-commit hooks (standard level)
/popkit:project setup --level standard

# Setup with CI integration
/popkit:project setup --level strict --ci

# Generate project-specific skills
/popkit:project skills generate
```

---

## Workflow Integration

This command covers the full project lifecycle:

1. **New Project**: `/popkit:project init` → Create .claude/ structure
2. **Understand Project**: `/popkit:project analyze` → Codebase analysis
3. **Configure Quality**: `/popkit:project setup` → Pre-commit hooks
4. **Enhance Tooling**: `/popkit:project mcp` → Project-specific MCP
5. **Customize**: `/popkit:project skills` → Project-specific skills
6. **Enable Discovery**: `/popkit:project embed` → Semantic search for project items

**One-Command Alternative:**
- `/popkit:project generate` → Full pipeline (steps 2, 4, 5, 6 combined)

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Init Skill | `skills/pop-project-init/SKILL.md` |
| Analysis Skill | `skills/pop-analyze-project/SKILL.md` |
| Embed Skill | `skills/pop-embed-project/SKILL.md` |
| MCP Generator Skill | `skills/pop-mcp-generator/SKILL.md` |
| Setup Skill | `skills/pop-setup-precommit/SKILL.md` |
| Skills Generator | `skills/pop-skill-generator/SKILL.md` |
| Embedding Module | `hooks/utils/embedding_project.py` |
| MCP Template | `templates/mcp-server/` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:routine morning` | Daily health check |
| `/popkit:power init` | Start/stop Redis for Power Mode |
| `/popkit:next` | Context-aware recommendations |

---

## Subcommand: observe

Cross-project observability dashboard. View all projects using PopKit Cloud from the main monorepo.

```
/popkit:project observe                 # Show dashboard
/popkit:project observe --active        # Only show active projects (24h)
/popkit:project observe --summary       # Quick summary stats
/popkit:project observe --project <id>  # View specific project details
```

### Prerequisites

Requires `POPKIT_API_KEY` environment variable set. This feature uses PopKit Cloud to aggregate data across all projects registered to your API key.

### Process

Calls the PopKit Cloud Project Registry API:

1. **Fetch All Projects**
   - Lists all registered projects
   - Sorted by last activity (most recent first)

2. **Display Dashboard**
   - Project name and anonymized path
   - Last active timestamp
   - Session count
   - Tool call count
   - Recent agents used
   - Recent commands used
   - Power Mode status
   - Health score (from morning routine)

3. **Show Summary Stats**
   - Total projects registered
   - Active in last 24h
   - Total tool calls across all projects
   - Total sessions
   - Average health score
   - Projects with Power Mode active

### Output

```
/popkit:project observe

═══════════════════════════════════════════════════════════════
                  PopKit Cross-Project Dashboard
═══════════════════════════════════════════════════════════════

Summary:
  Total Projects: 5
  Active (24h):   3
  Tool Calls:     1,247
  Sessions:       42
  Avg Health:     78
  Power Mode:     1 active

───────────────────────────────────────────────────────────────
Projects (sorted by last activity)
───────────────────────────────────────────────────────────────

1. popkit
   Path: .../elshaddai/popkit
   Last Active: 2 minutes ago
   Sessions: 18 | Tools: 543 | Health: 85
   Recent Agents: code-reviewer, bug-whisperer, test-writer-fixer
   Recent Commands: /popkit:dev, /popkit:git pr
   Power Mode: Redis (2 agents)

2. my-saas-app
   Path: .../projects/my-saas-app
   Last Active: 3 hours ago
   Sessions: 12 | Tools: 389 | Health: 72
   Recent Agents: api-designer, performance-optimizer
   Recent Commands: /popkit:routine morning, /popkit:issue list
   Power Mode: Off

3. client-dashboard
   Path: .../clients/dashboard
   Last Active: Yesterday
   Sessions: 8 | Tools: 215 | Health: 65
   Recent Agents: ui-designer, accessibility-guardian
   Recent Commands: /popkit:git commit
   Power Mode: Off

───────────────────────────────────────────────────────────────
Projects Inactive > 7 days (may need attention)
───────────────────────────────────────────────────────────────

4. old-project
   Path: .../archive/old-project
   Last Active: 15 days ago
   Health: 45

5. experiment
   Path: .../scratch/experiment
   Last Active: 23 days ago
   Health: 0 (never ran morning routine)
```

### Summary Output

```
/popkit:project observe --summary

PopKit Cloud Summary
════════════════════

Total Projects:      5
Active (24h):        3 (60%)
Total Tool Calls:    1,247
Total Sessions:      42
Average Health:      78/100
Power Mode Active:   1

Most Active Projects:
  1. popkit (543 tool calls)
  2. my-saas-app (389 tool calls)
  3. client-dashboard (215 tool calls)

Recent Agent Usage:
  1. code-reviewer (127 times)
  2. bug-whisperer (89 times)
  3. test-writer-fixer (67 times)

Top Commands:
  1. /popkit:git commit (156 times)
  2. /popkit:dev full (89 times)
  3. /popkit:routine morning (45 times)
```

### Project Detail Output

```
/popkit:project observe --project abc123

Project: popkit
═══════════════

ID: abc123def456789
Path: .../elshaddai/popkit
Platform: win32
PopKit Version: 0.9.10
Registered: 2025-01-15T10:00:00Z

Activity:
  Last Active: 2 minutes ago
  Sessions: 18
  Tool Calls: 543

Health:
  Score: 85/100
  Last Check: Today 09:15

Agents Used (last 10):
  - code-reviewer
  - bug-whisperer
  - test-writer-fixer
  - api-designer
  - security-auditor

Commands Used (last 10):
  - /popkit:dev full
  - /popkit:git pr
  - /popkit:routine morning
  - /popkit:issue list

Power Mode:
  Status: Active (Redis)
  Agents: 2
```

### Options

| Flag | Description |
|------|-------------|
| `--active` | Only show projects active in last 24h |
| `--summary` | Show quick summary statistics only |
| `--project <id>` | Show details for specific project |
| `--json` | Output as JSON for scripting |

### Use Cases

1. **Development Team Visibility**
   - See which projects are actively being developed
   - Identify stale projects that may need attention
   - Track tool and agent usage patterns

2. **Pattern Analysis**
   - Discover which agents are most useful across projects
   - See which commands drive productivity
   - Identify projects that could benefit from Power Mode

3. **Health Monitoring**
   - Track health scores across all projects
   - Find projects with low scores that need maintenance
   - Ensure morning routines are being run

4. **Smoke Testing**
   - After updating PopKit, check all projects still registering
   - Verify activity is being tracked correctly
   - Monitor for any errors or issues

### Architecture Integration

| Component | Integration |
|-----------|-------------|
| Cloud API | `packages/cloud/src/routes/projects.ts` |
| Plugin Client | `hooks/utils/project_client.py` |
| Registration Hook | `hooks/session-start.py` (auto-registers) |
| Activity Hook | `hooks/post-tool-use.py` (tracks activity) |

### Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:routine morning` | Updates health score for current project |
| `/popkit:privacy status` | View data collection settings |
| `/popkit:privacy export` | Export all your PopKit Cloud data |
