---
name: project-init
description: "Use when starting a new project or setting up Claude Code integration - initializes .claude/ directory structure and surgically adds PopKit section to CLAUDE.md without overwriting existing content. Detects plugin conflicts and recommends resolutions. Do NOT use if .claude/ already exists - use analyze-project instead to understand existing configuration."
---

# Project Initialization

## Overview

Scaffold a new project with complete Claude Code configuration. **Surgically adds PopKit configuration** without overwriting existing user content in CLAUDE.md.

**Core principle:** Never destroy user content. Add what's needed, preserve what exists.

**Trigger:** `/popkit:project init` command or when starting work on a new project

## Critical Rules

1. **NEVER overwrite existing CLAUDE.md** - Only add/update the PopKit section using markers
2. **ALWAYS create `.claude/popkit/` directory** - Required for deploy, routines, and state
3. **Check for plugin conflicts** before proceeding
4. **Use AskUserQuestion** for all user decisions
5. **Preserve existing .claude/ content** if present

## Initialization Process

### Step 0: Check for Plugin Conflicts

**ALWAYS run this first** using the plugin conflict detector:

```python
from plugin_detector import run_detection, format_conflict_report, format_quick_summary

result, plugins = run_detection()

if result["total"] > 0:
    # Show conflicts to user
    print(format_conflict_report(result, plugins))
```

If conflicts detected, use AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "Plugin conflicts detected. How would you like to proceed?"
- header: "Conflicts"
- options:
  - label: "View details"
    description: "Show full conflict report before continuing"
  - label: "Continue anyway"
    description: "Proceed with initialization (conflicts may cause issues)"
  - label: "Cancel"
    description: "Stop and resolve conflicts first"
- multiSelect: false
```

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

Create ALL required directories, even if .claude/ exists. This ensures PopKit runtime directories are always present:

```bash
# Create .claude/ structure - always ensure all directories exist
mkdir -p .claude/agents
mkdir -p .claude/commands
mkdir -p .claude/hooks
mkdir -p .claude/skills
mkdir -p .claude/scripts
mkdir -p .claude/logs
mkdir -p .claude/plans

# CRITICAL: Create .claude/popkit/ for PopKit runtime state
mkdir -p .claude/popkit/routines/morning
mkdir -p .claude/popkit/routines/nightly

# Create .gitkeep files for empty directories
touch .claude/logs/.gitkeep 2>/dev/null
touch .claude/plans/.gitkeep 2>/dev/null
touch .claude/popkit/routines/morning/.gitkeep 2>/dev/null
touch .claude/popkit/routines/nightly/.gitkeep 2>/dev/null
```

### Step 2b: Create PopKit Config (REQUIRED)

**Always create `.claude/popkit/config.json`** with project configuration:

```python
import os
import json
from datetime import datetime

def get_project_prefix(project_name: str) -> str:
    """Generate prefix from first letters of each word."""
    words = project_name.replace('-', ' ').replace('_', ' ').split()
    if len(words) == 1:
        return words[0][:2].lower()
    return ''.join(word[0].lower() for word in words[:3])

popkit_config_path = ".claude/popkit/config.json"
project_name = os.path.basename(os.getcwd())

config = {
    "version": "1.0",
    "project_name": project_name,
    "project_prefix": get_project_prefix(project_name),
    "default_routines": {
        "morning": "pk",
        "nightly": "pk"
    },
    "initialized_at": datetime.now().isoformat(),
    "popkit_version": "1.2.0",
    "tier": "free",
    "features": {
        "power_mode": "not_configured",
        "deployments": [],
        "custom_routines": []
    }
}

# Only create if doesn't exist (preserve existing config)
if not os.path.exists(popkit_config_path):
    with open(popkit_config_path, 'w') as f:
        json.dump(config, f, indent=2)
```

### Step 3: Surgically Update CLAUDE.md

**CRITICAL: Always use HTML markers for surgical updates.**

The PopKit section MUST be wrapped with markers so it can be updated without touching user content:

```markdown
<!-- POPKIT:START -->
## PopKit Integration

This project uses [PopKit](https://github.com/jrc1883/popkit-claude) for AI-powered development workflows.

### Quick Commands

| Command | Description |
|---------|-------------|
| `/popkit:next` | Get context-aware recommendations |
| `/popkit:routine morning` | Daily health check |
| `/popkit:dev work #N` | Start working on issue #N |
| `/popkit:git commit` | Smart commit with message generation |

### Project Configuration

- **Power Mode:** [Not configured / Local Mode / PopKit Cloud]
- **Custom Routines:** `.claude/popkit/routines/`
- **Project Skills:** `.claude/skills/`

### Resources

- [PopKit Documentation](https://github.com/jrc1883/popkit-claude)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
<!-- POPKIT:END -->
```

#### Surgical Update Logic

```python
import os
import re

def update_claude_md(project_path: str, power_mode: str = "not_configured"):
    """Surgically add or update PopKit section in CLAUDE.md."""
    claude_md_path = os.path.join(project_path, "CLAUDE.md")

    popkit_section = generate_popkit_section(power_mode)

    if not os.path.exists(claude_md_path):
        # No CLAUDE.md - create minimal file with PopKit section
        project_name = os.path.basename(project_path)
        with open(claude_md_path, 'w') as f:
            f.write(f"# {project_name}\n\n")
            f.write("Project instructions for Claude Code.\n\n")
            f.write(popkit_section)
        return "created"

    # Read existing content
    with open(claude_md_path, 'r') as f:
        content = f.read()

    # Check for existing PopKit section
    start_marker = "<!-- POPKIT:START -->"
    end_marker = "<!-- POPKIT:END -->"

    if start_marker in content and end_marker in content:
        # Update existing section between markers
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        new_content = re.sub(pattern, popkit_section, content, flags=re.DOTALL)

        with open(claude_md_path, 'w') as f:
            f.write(new_content)
        return "updated"
    else:
        # Append new section at end with markers
        with open(claude_md_path, 'a') as f:
            f.write("\n\n")
            f.write(popkit_section)
        return "appended"

def generate_popkit_section(power_mode: str) -> str:
    """Generate the PopKit section content with markers."""
    power_mode_display = {
        "not_configured": "Not configured",
        "local": "Local Mode",
        "cloud": "PopKit Cloud"
    }.get(power_mode, "Not configured")

    return f'''<!-- POPKIT:START -->
## PopKit Integration

This project uses [PopKit](https://github.com/jrc1883/popkit-claude) for AI-powered development workflows.

### Quick Commands

| Command | Description |
|---------|-------------|
| `/popkit:next` | Get context-aware recommendations |
| `/popkit:routine morning` | Daily health check |
| `/popkit:dev work #N` | Start working on issue #N |
| `/popkit:git commit` | Smart commit with message generation |

### Project Configuration

- **Power Mode:** {power_mode_display}
- **Custom Routines:** `.claude/popkit/routines/`
- **Project Skills:** `.claude/skills/`

### Resources

- [PopKit Documentation](https://github.com/jrc1883/popkit-claude)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
<!-- POPKIT:END -->'''
```

### Step 4: Create STATUS.json (if not exists)

Only create if it doesn't exist:

```python
status_path = ".claude/STATUS.json"
if not os.path.exists(status_path):
    status = {
        "lastUpdate": datetime.now().isoformat(),
        "project": os.path.basename(os.getcwd()),
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
        },
        "powerMode": {
            "enabled": False,
            "type": None,
            "agents": 0
        }
    }
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)
```

### Step 5: Create settings.json (if not exists)

Include PopKit-specific fields:

```python
settings_path = ".claude/settings.json"
if not os.path.exists(settings_path):
    settings = {
        "model": "claude-sonnet-4-20250514",
        "permissions": {
            "allowBash": True,
            "allowFileOperations": True,
            "allowGit": True
        },
        "popkit": {
            "tier": "free",
            "competency_level": "auto",
            "features_available": ["local-power-mode", "basic-patterns"]
        }
    }
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
```

### Step 6: Ask About Power Mode Setup

Use AskUserQuestion with **updated naming** (PopKit Cloud instead of Redis Mode):

```
Use AskUserQuestion tool with:
- question: "Would you like to set up Power Mode for multi-agent orchestration?"
- header: "Power Mode"
- options:
  - label: "PopKit Cloud (Recommended)"
    description: "Hosted infrastructure, zero setup. Requires Pro subscription."
  - label: "Local Mode"
    description: "File-based coordination, works offline. No external dependencies."
  - label: "Skip"
    description: "Set up later with /popkit:power init"
- multiSelect: false
```

**Based on selection:**
- **PopKit Cloud**: Check tier, setup cloud connection
- **Local Mode**: Create `.claude/power-mode/` with file-based config
- **Skip**: Leave Power Mode unconfigured

**Update the PopKit section in CLAUDE.md** with the appropriate Power Mode status.

### Step 7: Update .gitignore

Only add lines that don't already exist:

```python
gitignore_additions = """
# Claude Code - Runtime/session files
.claude/logs/
.claude/STATUS.json
.claude/power-mode-state.json
.claude/popkit/state.json
.worktrees/

# Claude Code - Generated content
.generated/
"""

gitignore_path = ".gitignore"
if os.path.exists(gitignore_path):
    with open(gitignore_path, 'r') as f:
        existing = f.read()

    # Only add lines not already present
    for line in gitignore_additions.strip().split('\n'):
        if line and not line.startswith('#') and line not in existing:
            with open(gitignore_path, 'a') as f:
                f.write(f"\n{line}")
else:
    with open(gitignore_path, 'w') as f:
        f.write(gitignore_additions)
```

### Step 8: Post-Init Recommendations

Use AskUserQuestion:

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
    description: "I'll explore on my own"
- multiSelect: false
```

## Output Format

```
PopKit Project Initialization
═════════════════════════════

[1/5] Checking for plugin conflicts...
      ✓ No conflicts detected (1 plugin: popkit)

[2/5] Detecting project type...
      ✓ Node.js (Next.js 14) detected

[3/5] Creating .claude/ structure...
      ✓ Directories created
      ✓ .claude/popkit/ initialized with config.json
      ✓ STATUS.json initialized
      ✓ settings.json created

[4/5] Updating CLAUDE.md...
      ✓ PopKit section appended with markers
      ✓ Existing content preserved

[5/5] Power Mode setup...
      ✓ [Based on user selection]

Summary:
  - PopKit Config: .claude/popkit/config.json
  - CLAUDE.md: PopKit section with <!-- POPKIT:START/END --> markers
  - Power Mode: [Not configured / Local Mode / PopKit Cloud]
  - Ready for: /popkit:routine morning

What would you like to do next?
```

## If CLAUDE.md Already Has PopKit Section

```
PopKit Project Initialization
═════════════════════════════

[1/5] Checking for plugin conflicts...
      ✓ No conflicts detected

[2/5] Detecting project type...
      ✓ Node.js detected

[3/5] Creating .claude/ structure...
      ✓ Already exists
      ✓ .claude/popkit/ verified/created

[4/5] Updating CLAUDE.md...
      ✓ PopKit section updated between markers
      ✓ User content outside markers preserved

[5/5] Power Mode setup...
      ✓ [Based on user selection]

Note: Your existing CLAUDE.md content was preserved.
      Only the <!-- POPKIT:START --> to <!-- POPKIT:END --> section was updated.
```

## Verification Checklist

After initialization, verify these files/directories exist:

| Path | Purpose |
|------|---------|
| `.claude/` | Root Claude Code config |
| `.claude/popkit/` | PopKit runtime state |
| `.claude/popkit/config.json` | Project PopKit config |
| `.claude/popkit/routines/` | Custom routines |
| `.claude/STATUS.json` | Session state |
| `.claude/settings.json` | Claude settings with PopKit fields |
| `CLAUDE.md` | Has `<!-- POPKIT:START -->` markers |

## Integration

**Triggers:**
- `/popkit:project init` command
- Manual skill invocation

**Followed by:**
- **/popkit:project analyze** - Deep codebase analysis
- **/popkit:project mcp** - Generate project-specific MCP server
- **/popkit:project setup** - Configure pre-commit hooks
- **/popkit:power init** - Configure Power Mode
- **/popkit:issue list** - View issues with orchestration recommendations

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-analyze-project` | Run after init for deep analysis |
| `pop-doc-sync` | Keeps PopKit section in sync using markers |
| `pop-plugin-test` | Validates plugin integrity |
