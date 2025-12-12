<p align="center">
  <img src="https://raw.githubusercontent.com/jrc1883/popkit-claude/main/assets/images/popkit-banner.png" alt="PopKit Banner" width="600">
</p>

<h1 align="center">PopKit</h1>

<p align="center">
  <strong>AI-powered development workflows for Claude Code</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#features">Features</a> |
  <a href="#commands">Commands</a> |
  <a href="#agents">Agents</a> |
  <a href="#premium">Premium</a> |
  <a href="#faq">FAQ</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Claude%20Code-Plugin-purple?style=flat-square" alt="Claude Code Plugin">
</p>

---

## See the Difference

<p align="center">
  <img src="https://raw.githubusercontent.com/jrc1883/popkit-claude/main/assets/images/before-after.gif" alt="Before and After PopKit" width="700">
</p>

---

## Quick Start

Install PopKit in 2 commands:

```bash
# Add the marketplace
/plugin marketplace add jrc1883/popkit-claude

# Install the plugin
/plugin install popkit@popkit-claude
```

Then **restart Claude Code** to activate.

After restart, try:
```bash
/popkit:routine morning    # Morning health check
/popkit:dev brainstorm     # Start brainstorming a feature
/popkit:git commit         # Smart commit with auto-message
```

---

## Features

### Development Workflows

**7-Phase Feature Development** - From idea to implementation with guided phases:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Discovery  │ -> │ Exploration │ -> │  Questions  │ -> │Architecture │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│   Summary   │ <- │   Review    │ <- │Implementation│ <───────┘
└─────────────┘    └─────────────┘    └─────────────┘
```

### Intelligent Agents

**30+ specialized agents** that activate based on context:

| Tier | Agents | When |
|------|--------|------|
| **Tier 1** | 11 core agents | Always active |
| **Tier 2** | 17 specialists | On-demand by triggers |
| **Workflow** | 3 feature agents | During `/popkit:dev` |

### Day Routines

Start and end your day with health checks:

```
┌──────────────────────────────────────┐
│  MORNING ROUTINE - Ready to Code     │
├──────────────────────────────────────┤
│  Git Status:     ✓ Clean             │
│  TypeScript:     ✓ No errors         │
│  Dev Server:     ✓ Running on :3000  │
│  Dependencies:   ✓ Up to date        │
├──────────────────────────────────────┤
│  Ready to Code Score: 95/100         │
└──────────────────────────────────────┘
```

### Power Mode (Multi-Agent)

Parallel agent collaboration for complex tasks:

```
┌──────────────────────────────────────────────┐
│  POWER MODE - 4 Agents Active                │
├──────────────────────────────────────────────┤
│  code-reviewer   ████████░░ 80%  Reviewing   │
│  test-writer     ██████████ 100% Complete    │
│  docs-updater    ██████░░░░ 60%  Writing     │
│  security-audit  ████░░░░░░ 40%  Scanning    │
└──────────────────────────────────────────────┘
```

---

## Commands

### `/popkit:dev` - Development Workflows

The main entry point for feature development.

| Subcommand | Description |
|------------|-------------|
| `full` | 7-phase guided workflow (default) |
| `work #N` | Issue-driven development |
| `brainstorm` | Idea refinement through dialogue |
| `plan` | Create implementation plan |
| `execute` | Execute an existing plan |
| `quick` | Minimal ceremony for small tasks |
| `prd` | Generate PRD document |
| `suite` | Full documentation suite |

**Flags:** `-T` (thinking), `--power` (multi-agent), `--solo` (sequential)

```bash
# Examples
/popkit:dev "user authentication"
/popkit:dev work #57
/popkit:dev brainstorm "real-time notifications" -T
/popkit:dev quick "fix the login bug"
```

---

### `/popkit:git` - Git Workflow

Smart git operations with auto-generated messages.

| Subcommand | Description |
|------------|-------------|
| `commit` | Smart commit with auto-message (default) |
| `push` | Push to remote |
| `pr` | Create/manage pull requests |
| `review` | Code review with confidence filtering |
| `ci` | GitHub Actions workflow runs |
| `release` | Create releases with changelog |
| `finish` | Complete branch with 4-option flow |
| `prune` | Remove stale branches |

**Flags:** `--draft`, `--squash`, `--amend`

```bash
# Examples
/popkit:git                        # Smart commit
/popkit:git pr                     # Create pull request
/popkit:git release --tag v1.2.0   # Create release
/popkit:git finish                 # Complete development
```

---

### `/popkit:routine` - Day Routines

Morning health checks and nightly cleanup.

| Subcommand | Description |
|------------|-------------|
| `morning` | Health check → Ready to Code score |
| `nightly` | Cleanup → Sleep Score |

**Actions:** `run`, `quick`, `generate`, `list`, `set`, `edit`, `delete`

**Flags:** `--simple`, `--full`, `--no-debt`

```bash
# Examples
/popkit:routine morning             # Full morning routine
/popkit:routine morning quick       # One-line summary
/popkit:routine nightly             # End-of-day cleanup
/popkit:routine morning generate    # Create custom routine
```

---

### `/popkit:project` - Project Management

Project analysis and setup.

| Subcommand | Description |
|------------|-------------|
| `init` | Initialize PopKit in a project |
| `analyze` | Deep codebase analysis |
| `embed` | Create semantic embeddings |
| `generate` | Generate custom MCP server |
| `setup` | Configure project settings |

```bash
# Examples
/popkit:project init
/popkit:project analyze --json
/popkit:project generate mcp
```

---

### `/popkit:issue` - GitHub Issues

Full issue management.

| Subcommand | Description |
|------------|-------------|
| `create` | Create new issue |
| `list` | List issues with filters |
| `view` | View issue details |
| `close` | Close an issue |
| `comment` | Add comment |
| `edit` | Edit issue |
| `link` | Link related issues |

**Flags:** `--state`, `--label`, `--assign`

```bash
# Examples
/popkit:issue create "Bug in auth flow"
/popkit:issue list --label bug
/popkit:issue close 123 --comment "Fixed in #125"
```

---

### `/popkit:debug` - Systematic Debugging

Structured debugging with root cause analysis.

| Mode | Description |
|------|-------------|
| `code` | Debug code issues |
| `routing` | Debug agent routing |

**Flags:** `--trace`, `--verbose`

```bash
# Examples
/popkit:debug code "TypeError in user service"
/popkit:debug routing --verbose
```

---

### `/popkit:power` - Multi-Agent Mode

Parallel agent orchestration.

| Subcommand | Description |
|------------|-------------|
| `init` | Set up Power Mode |
| `start` | Start session |
| `status` | View agent status |
| `stop` | End session |

**Modes:** Redis (full), File-based (zero-setup fallback)

```bash
# Examples
/popkit:power init           # First-time setup
/popkit:power start          # Begin session
/popkit:power status         # Check agents
```

---

### More Commands

| Command | Description | Subcommands |
|---------|-------------|-------------|
| `/popkit:assess` | Multi-perspective assessment | (direct use) |
| `/popkit:audit` | Security audit | `quick`, `full`, `scan` |
| `/popkit:bug` | Bug reporting | `report`, `search`, `share` |
| `/popkit:knowledge` | Knowledge base | `list`, `add`, `search`, `sync` |
| `/popkit:next` | What to do next | `quick`, `verbose` |
| `/popkit:plugin` | Plugin management | `test`, `docs`, `sync` |
| `/popkit:privacy` | Privacy controls | `status`, `consent`, `export` |
| `/popkit:worktree` | Git worktrees | `create`, `list`, `remove` |

---

## Agents

### Tier 1: Always Active

These agents are always available and route automatically based on context:

| Agent | Triggers | Purpose |
|-------|----------|---------|
| **bug-whisperer** | "bug", "error", TypeError | Debug complex issues |
| **code-reviewer** | After implementation | Quality review |
| **security-auditor** | "security", "vulnerability" | Security analysis |
| **test-writer-fixer** | `*.test.ts`, "test" | Test implementation |
| **performance-optimizer** | "slow", "performance" | Optimization |
| **refactoring-expert** | "refactor", "clean up" | Code restructuring |
| **query-optimizer** | `*.sql`, "query" | Database optimization |
| **api-designer** | "API", "endpoint" | API design |
| **accessibility-guardian** | "a11y", "accessibility" | WCAG compliance |
| **migration-specialist** | "migrate", "upgrade" | System migrations |
| **documentation-maintainer** | "docs", `*.md` | Documentation |

### Tier 2: On-Demand Specialists

Activated when specific patterns are detected:

| Agent | When Activated |
|-------|----------------|
| **ai-engineer** | ML/AI tasks |
| **devops-automator** | CI/CD, Docker |
| **bundle-analyzer** | Bundle size issues |
| **cache-optimizer** | Caching strategies |
| **dead-code-eliminator** | Code cleanup |
| **rapid-prototyper** | Quick prototypes |
| **researcher** | Technical research |
| **meta-agent** | Agent creation |

---

## Premium Features

Some features require a PopKit subscription:

| Feature | Free | Pro ($9/mo) |
|---------|------|-------------|
| Core commands | Yes | Yes |
| Basic agents | Yes | Yes |
| Custom MCP server | - | Yes |
| Power Mode (Redis) | - | Yes |
| Pattern sharing | - | Yes |
| Team coordination | - | Team tier |

Upgrade with `/popkit:upgrade` or visit [popkit.dev/pricing](https://popkit.dev/pricing).

---

## FAQ

### How do I get started?

Install the plugin, restart Claude Code, then run `/popkit:routine morning` to see your project health.

### What's the difference between `/popkit:dev` and just coding?

`/popkit:dev` provides a structured 7-phase workflow with architecture design, code review, and quality gates. It's especially useful for larger features.

### Do I need Power Mode?

Power Mode enables multiple agents working in parallel. For most tasks, sequential mode works fine. Power Mode shines for complex refactoring or large features.

### Can I use PopKit without the cloud?

Yes! The core plugin works entirely locally. Cloud features (pattern sharing, team sync) require a subscription.

### How do agents get selected?

Agents route based on:
1. **Keywords** in your request ("bug" → bug-whisperer)
2. **File patterns** being edited (`*.test.ts` → test-writer-fixer)
3. **Error patterns** encountered (TypeError → bug-whisperer)

### What's the morning routine?

A health check that scores your project's readiness:
- Git status (uncommitted changes?)
- TypeScript errors
- Dev server status
- Dependency freshness

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](LICENSE)

---

<p align="center">
  Built with care for the Claude Code community
  <br>
  <a href="https://github.com/jrc1883/popkit-claude/issues">Report Bug</a> •
  <a href="https://github.com/jrc1883/popkit-claude/issues">Request Feature</a>
</p>
