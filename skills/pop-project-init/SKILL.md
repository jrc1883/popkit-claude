---
name: project-init
description: "Use when starting a new project or setting up Claude Code integration - initializes .claude/ directory structure including agents, skills, commands, hooks, and project documentation templates. Creates CLAUDE.md, STATUS.json, settings.json with optional Power Mode setup. Do NOT use if .claude/ already exists - use analyze-project instead to understand existing configuration."
---

# Project Initialization

## Overview

Scaffold a new project with complete Claude Code configuration including agents, skills, commands, and documentation.

**Core principle:** Every project gets a consistent, well-organized .claude/ structure.

**Trigger:** `/init-project` command or when starting work on a new project

## Directory Structure Created

```
.claude/
├── agents/                    # Project-specific agents
│   └── README.md
├── commands/                  # Slash commands
│   └── README.md
├── hooks/                     # Hook scripts (pre-tool-use, etc.)
│   └── README.md
├── skills/                    # Project-specific skills
│   └── README.md
├── scripts/                   # Utility scripts
│   ├── session-start.ps1     # Session startup script
│   └── session-end.ps1       # Session cleanup script
├── logs/                      # Log files
│   └── .gitkeep
├── plans/                     # Implementation plans
│   └── .gitkeep
├── STATUS.json               # Session continuity state
└── settings.json             # Claude Code settings
CLAUDE.md                     # Project instructions
```

## Initialization Process

### Step 1: Detect Project Type

```bash
# Detect project type from files
if [ -f "package.json" ]; then
  type="node"
elif [ -f "Cargo.toml" ]; then
  type="rust"
elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  type="python"
elif [ -f "go.mod" ]; then
  type="go"
else
  type="generic"
fi
```

### Step 2: Create Directory Structure

```bash
mkdir -p .claude/{agents,commands,hooks,skills,scripts,logs,plans}
touch .claude/logs/.gitkeep
touch .claude/plans/.gitkeep
```

### Step 3: Create CLAUDE.md

Generate project instructions template:

```markdown
# [Project Name] - Claude Instructions

## Project Identity
- **Name**: [Project Name]
- **Type**: [Detected type]
- **Stack**: [Detected tech stack]

## Quick Start
\`\`\`bash
# Development
[Project-specific dev commands]
\`\`\`

## Key Files
- [Main entry point]
- [Configuration files]
- [Test directories]

## Current Focus
[Area currently being worked on]

## Important Notes
- [Project-specific rules]
- [Things to avoid]
```

### Step 4: Create STATUS.json

Initialize empty status:

```json
{
  "lastUpdate": "[ISO timestamp]",
  "project": "[project-name]",
  "sessionType": "Fresh",
  "git": {
    "branch": "main",
    "lastCommit": "",
    "uncommittedFiles": 0
  },
  "tasks": {
    "inProgress": [],
    "completed": []
  },
  "services": {},
  "context": {
    "focusArea": "",
    "nextAction": ""
  }
}
```

### Step 5: Create settings.json

```json
{
  "model": "claude-sonnet-4-20250514",
  "maxTokens": 8192,
  "permissions": {
    "allowBash": true,
    "allowFileOperations": true,
    "allowGit": true
  },
  "statusLine": {
    "type": "command",
    "command": "python power-mode/statusline.py",
    "padding": 0
  }
}
```

**Note:** The statusLine configuration enables Power Mode status display when active. It shows:
- `[POP] #N Phase: X (N/M) [####------] 40%` when Power Mode is running
- Empty when Power Mode is inactive (no visual clutter)

### Step 6: Ask About Power Mode Setup

Offer Power Mode setup for multi-agent orchestration using AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "Would you like to set up Power Mode for multi-agent orchestration?"
- header: "Power Mode"
- options:
  - label: "Redis Mode"
    description: "Full parallel agent orchestration (requires Docker)"
  - label: "File Mode"
    description: "Simpler coordination without external dependencies"
  - label: "Skip"
    description: "Set up later with /popkit:power init"
- multiSelect: false
```

**NEVER present as plain text** like "1. Redis, 2. File, 3. Skip".

**If Redis Mode selected:**
```bash
# Copy docker-compose.yml template
cp power-mode/docker-compose.yml .claude/docker-compose.yml
echo "[+] docker-compose.yml created"
echo "Run 'docker compose -f .claude/docker-compose.yml up -d' to start Redis"
```

**If File Mode selected:**
```bash
# Create initial power mode state file
cat > .claude/power-mode-state.json << 'EOF'
{
  "active": false,
  "session_id": null,
  "mode": "file",
  "note": "File-based Power Mode. Activate with /popkit:issue work #N -p"
}
EOF
echo "[+] Power Mode configured for file-based coordination"
```

### Step 7: Update .gitignore

Add to .gitignore:

```
# Claude Code - Runtime/session files
.claude/logs/
.claude/STATUS.json
.claude/power-mode-state.json
.worktrees/

# Claude Code - Development-only content (not for distribution)
# Uses .local suffix pattern like Claude Code's settings.local.json
commands.local/
skills.local/
agents.local/
hooks.local/

# Claude Code - Generated content from /popkit:generate-* commands
.generated/
```

### Step 8: Create README Files

Create README.md in each subdirectory explaining purpose and how to add items.

## Project-Type Specific Setup

### Node.js Projects

- Add npm/yarn run commands to CLAUDE.md
- Detect test framework (jest, mocha, vitest)
- Note port from package.json scripts

### Python Projects

- Add pip/poetry commands
- Detect test framework (pytest, unittest)
- Note virtual environment

### Rust Projects

- Add cargo commands
- Note workspace structure

### Go Projects

- Add go commands
- Note module structure

## Post-Init Recommendations

After initialization, present next steps using AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "Project initialized. What would you like to do next?"
- header: "Next Step"
- options:
  - label: "Analyze codebase"
    description: "Run /popkit:project analyze for deep codebase analysis"
  - label: "Setup quality gates"
    description: "Run /popkit:project setup for pre-commit hooks"
  - label: "View issues"
    description: "Run /popkit:issue list to see GitHub issues"
  - label: "Done for now"
    description: "I'll customize CLAUDE.md manually"
- multiSelect: false
```

## Integration

**Triggers:**
- `/popkit:init-project` command
- Manual skill invocation

**Followed by:**
- **/popkit:project analyze** - Deep codebase analysis
- **/popkit:project mcp** - Generate project-specific MCP server
- **/popkit:project setup** - Configure pre-commit hooks
- **/popkit:power init** - Start Redis for Power Mode
- **/popkit:issue list** - View issues with orchestration recommendations
