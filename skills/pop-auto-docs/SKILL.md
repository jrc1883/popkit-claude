---
name: auto-docs
description: "Use when documentation is stale, incomplete, or needs synchronization with codebase changes - automatically generates and updates plugin documentation including CLAUDE.md, README.md, and component docs. Scans agents, skills, commands, and hooks to produce accurate counts and descriptions. Do NOT use for user-facing application docs or when you just need to write a single README - handle those directly."
---

# Auto-Documentation

## Overview

Automatically generate and synchronize plugin documentation by analyzing the codebase structure. Scans agents, skills, commands, hooks, and configuration files to produce accurate, up-to-date documentation.

**Announce at start:** "I'm using the auto-docs skill to generate documentation."

## Monorepo Structure Awareness

PopKit uses a monorepo structure:

```
popkit/
├── CLAUDE.md           # Root project instructions (streamlined)
├── CHANGELOG.md        # Version history (separate file)
├── README.md           # User-facing documentation
├── packages/
│   ├── plugin/         # Main Claude Code plugin
│   │   ├── .claude-plugin/
│   │   ├── agents/
│   │   ├── skills/
│   │   ├── commands/
│   │   └── hooks/
│   └── cloud/          # PopKit Cloud API (optional)
```

## Capabilities

1. **CLAUDE.md Updates** - Update auto-generated sections (not full regeneration)
2. **CHANGELOG.md Management** - Version history in separate file
3. **README.md Updates** - Sync feature counts and descriptions
4. **Component Docs** - Generate docs for agents, skills, commands, hooks

## Key Principles

- **Surgical updates only** - Never overwrite user content
- **Preserve manual sections** - Only touch AUTO-GEN markers
- **Accuracy over completeness** - Document what exists, don't fabricate
- **Show diffs** - Always show what will change before applying

## Process

### 1. Scan Plugin Structure

```python
from pathlib import Path

plugin_path = Path("packages/plugin")

# Count and categorize
agents_dir = plugin_path / "agents"
skills_dir = plugin_path / "skills"
commands_dir = plugin_path / "commands"
hooks_dir = plugin_path / "hooks"

# Agent tiers from config.json
with open(agents_dir / "config.json") as f:
    config = json.load(f)
    tier1 = config["tiers"]["tier-1-always-active"]["agents"]
    tier2 = config["tiers"]["tier-2-on-demand"]["agents"]
    feature = config["tiers"]["feature-workflow"]["agents"]

# Skills (directories with SKILL.md)
skills = list(skills_dir.glob("*/SKILL.md"))

# Commands (active vs deprecated)
commands = list(commands_dir.glob("*.md"))
active = [c for c in commands if "DEPRECATED" not in c.read_text()]
deprecated = [c for c in commands if "DEPRECATED" in c.read_text()]

# Hooks from hooks.json
with open(hooks_dir / "hooks.json") as f:
    hooks = json.load(f)["hooks"]

# Utils
utils = list((hooks_dir / "utils").glob("*.py"))
```

### 2. Extract Metadata

For each component:
- Parse YAML frontmatter
- Extract name, description, tools
- Identify dependencies and relationships
- Note configuration options

### 3. Generate Documentation

#### CLAUDE.md - Streamlined Format

CLAUDE.md should be concise. Only update AUTO-GEN sections:

```markdown
## Version History

**Current Version:** 0.9.10 (User Feedback & Vote-Based Prioritization)

See [CHANGELOG.md](CHANGELOG.md) for full version history.
```

**AUTO-GEN Sections to Update:**

| Section | Content |
|---------|---------|
| `AUTO-GEN:TIER-COUNTS` | Agent counts per tier |
| `AUTO-GEN:REPO-STRUCTURE` | Directory tree with counts |
| `AUTO-GEN:KEY-FILES` | Important files table |

#### CHANGELOG.md - Version History

All version history goes in CHANGELOG.md:

```markdown
# Changelog

All notable changes to PopKit are documented in this file.

## [0.9.10] - Current

### User Feedback & Vote-Based Prioritization

- **Feature Name** (#issue): Description
```

#### README.md Sections

Update these sections in README.md:
- Feature counts (agents, skills, commands, hooks)
- Quick start instructions
- Installation steps

### 4. Detect Drift

Compare:
- Documented counts vs actual counts
- Listed components vs existing files
- Version in CLAUDE.md vs plugin.json vs CHANGELOG.md

Report discrepancies for manual review.

## Output

| File | Content |
|------|---------|
| CLAUDE.md | Updated auto-gen sections only |
| CHANGELOG.md | Version history (new entries at top) |
| README.md | Updated feature counts |
| docs/drift-report.md | Documentation drift analysis |

## Usage

```
/popkit:plugin docs              # Full documentation sync
/popkit:plugin docs --check      # Check for drift only
/popkit:plugin docs --claude     # Update CLAUDE.md sections only
/popkit:plugin docs --readme     # Update README.md only
/popkit:plugin docs --changelog  # Add new CHANGELOG entry
```

## Surgical Update Examples

### Adding New Version to CHANGELOG

```python
def add_changelog_entry(version: str, title: str, changes: list):
    """Add new version entry to CHANGELOG.md."""
    changelog_path = "CHANGELOG.md"

    with open(changelog_path, 'r') as f:
        content = f.read()

    # Find the first ## [version] line
    import re
    match = re.search(r'^## \[', content, re.MULTILINE)

    if match:
        # Insert new entry before first version
        new_entry = f"""## [{version}] - Current

### {title}

"""
        for change in changes:
            new_entry += f"- {change}\n"
        new_entry += "\n"

        # Update previous "Current" to remove that label
        content = re.sub(r'^(## \[\d+\.\d+\.\d+\]) - Current',
                        r'\1', content, count=1, flags=re.MULTILINE)

        content = content[:match.start()] + new_entry + content[match.start():]

    with open(changelog_path, 'w') as f:
        f.write(content)
```

### Updating CLAUDE.md Version Reference

```python
def update_claude_version(version: str, title: str):
    """Update version reference in CLAUDE.md."""
    claude_path = "CLAUDE.md"

    with open(claude_path, 'r') as f:
        content = f.read()

    # Update the version line
    import re
    pattern = r'\*\*Current Version:\*\* \d+\.\d+\.\d+ \([^)]+\)'
    replacement = f'**Current Version:** {version} ({title})'
    content = re.sub(pattern, replacement, content)

    with open(claude_path, 'w') as f:
        f.write(content)
```

### Updating AUTO-GEN Section

```python
def update_auto_gen_section(file_path: str, section_name: str, new_content: str):
    """Update a specific AUTO-GEN section."""
    with open(file_path, 'r') as f:
        content = f.read()

    start_marker = f"<!-- AUTO-GEN:{section_name} START -->"
    end_marker = f"<!-- AUTO-GEN:{section_name} END -->"

    import re
    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    replacement = f"{start_marker}\n{new_content}\n{end_marker}"

    if start_marker in content:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False
```

## Integration

**Called by:**
- Session end (optional - check for drift)
- After major changes (suggested by post-tool-use hook)
- Manual invocation via /popkit:plugin docs command
- Version bump workflow

**Outputs to:**
- Root directory (CLAUDE.md, CHANGELOG.md, README.md)
- docs/ directory (detailed docs if needed)

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-doc-sync` | Focused sync checking (this skill does full generation) |
| `pop-plugin-test` | Validates plugin integrity after doc updates |
| `pop-project-init` | Creates initial documentation structure |
