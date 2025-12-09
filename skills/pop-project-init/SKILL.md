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

1. **NEVER overwrite existing CLAUDE.md** - Only add the PopKit section
2. **Check for plugin conflicts** before proceeding
3. **Use AskUserQuestion** for all user decisions
4. **Preserve existing .claude/ content** if present

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

### Step 2: Create Directory Structure (if needed)

Only create directories that don't exist:

```bash
# Create .claude/ structure only if it doesn't exist
[ -d ".claude" ] || mkdir -p .claude/{agents,commands,hooks,skills,scripts,logs,plans,popkit}
touch .claude/logs/.gitkeep 2>/dev/null
touch .claude/plans/.gitkeep 2>/dev/null
```

### Step 3: Surgically Update CLAUDE.md

**This is the critical part.** Do NOT overwrite the file. Instead:

1. **Check if CLAUDE.md exists**
2. **Check if PopKit section already exists**
3. **If no PopKit section, append it at the end**
4. **If PopKit section exists, update only that section**

#### PopKit Section Format

The PopKit section uses markers for surgical updates:

```markdown
<!-- POPKIT:START -->
## PopKit Integration

This project uses [PopKit](https://github.com/jrc1883/popkit) for AI-powered development workflows.

### Quick Commands

| Command | Description |
|---------|-------------|
| `/popkit:next` | Get context-aware recommendations |
| `/popkit:routine morning` | Daily health check |
| `/popkit:dev work #N` | Start working on issue #N |
| `/popkit:git commit` | Smart commit with message generation |

### Project Configuration

- **Power Mode:** [Not configured / File-based / Redis]
- **Custom Routines:** `.claude/popkit/routines/`
- **Project Skills:** `.claude/skills/`

### Resources

- [PopKit Documentation](https://github.com/jrc1883/popkit)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
<!-- POPKIT:END -->
```

#### Surgical Update Logic

```python
def update_claude_md(project_path: str, power_mode: str = "not_configured"):
    """Surgically add or update PopKit section in CLAUDE.md."""
    claude_md_path = os.path.join(project_path, "CLAUDE.md")

    popkit_section = generate_popkit_section(power_mode)

    if not os.path.exists(claude_md_path):
        # No CLAUDE.md - create minimal file with just PopKit section
        with open(claude_md_path, 'w') as f:
            f.write(f"# {os.path.basename(project_path)}\n\n")
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
        # Update existing section
        import re
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        new_content = re.sub(pattern, popkit_section, content, flags=re.DOTALL)

        with open(claude_md_path, 'w') as f:
            f.write(new_content)
        return "updated"
    else:
        # Append new section at end
        with open(claude_md_path, 'a') as f:
            f.write("\n\n")
            f.write(popkit_section)
        return "appended"
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
        }
    }
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)
```

### Step 5: Create settings.json (if not exists)

```python
settings_path = ".claude/settings.json"
if not os.path.exists(settings_path):
    settings = {
        "model": "claude-sonnet-4-20250514",
        "permissions": {
            "allowBash": True,
            "allowFileOperations": True,
            "allowGit": True
        }
    }
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
```

### Step 6: Ask About Power Mode Setup

Use AskUserQuestion:

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

**Based on selection, update the PopKit section in CLAUDE.md** with the appropriate Power Mode status.

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

[1/4] Checking for plugin conflicts...
      ✓ No conflicts detected (1 plugin: popkit)

[2/4] Detecting project type...
      ✓ Node.js (Next.js 14) detected

[3/4] Creating .claude/ structure...
      ✓ Directories created (5 new)
      ✓ STATUS.json initialized
      ✓ settings.json created

[4/4] Updating CLAUDE.md...
      ✓ PopKit section appended (existing content preserved)

Summary:
  - CLAUDE.md: PopKit section added (lines 145-175)
  - Power Mode: Not configured
  - Ready for: /popkit:routine morning

What would you like to do next?
```

## If CLAUDE.md Already Has PopKit Section

```
PopKit Project Initialization
═════════════════════════════

[1/4] Checking for plugin conflicts...
      ✓ No conflicts detected

[2/4] Detecting project type...
      ✓ Node.js detected

[3/4] Creating .claude/ structure...
      ✓ Already exists (skipped)

[4/4] Updating CLAUDE.md...
      ✓ PopKit section updated (existing user content preserved)

Note: Your existing CLAUDE.md content was preserved.
      Only the <!-- POPKIT:START --> to <!-- POPKIT:END --> section was updated.
```

## Integration

**Triggers:**
- `/popkit:project init` command
- Manual skill invocation

**Followed by:**
- **/popkit:project analyze** - Deep codebase analysis
- **/popkit:project mcp** - Generate project-specific MCP server
- **/popkit:project setup** - Configure pre-commit hooks
- **/popkit:power init** - Start Redis for Power Mode
- **/popkit:issue list** - View issues with orchestration recommendations

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-analyze-project` | Run after init for deep analysis |
| `pop-doc-sync` | Keeps PopKit section in sync |
| `pop-plugin-test` | Validates plugin integrity |
