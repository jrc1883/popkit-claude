---
name: doc-sync
description: "Use when documentation counts are wrong, versions are mismatched, or CLAUDE.md needs updating - synchronizes auto-generated sections by reading source-of-truth files (plugin.json, config.json, hooks.json) and updating markers in CLAUDE.md. Do NOT use for writing new documentation or prose - this is specifically for keeping counts and versions in sync."
---

# Documentation Sync

## Overview

Synchronize documentation by reading source-of-truth files and updating auto-generated sections marked with `<!-- AUTO-GEN:SECTION-NAME START/END -->` comments.

**Announce at start:** "I'm using the doc-sync skill to check documentation synchronization."

## Monorepo Structure Awareness

PopKit uses a monorepo structure. Source-of-truth files are located in:

```
popkit/
├── CLAUDE.md                    # Root project instructions
├── CHANGELOG.md                 # Version history (separate file)
├── packages/
│   └── plugin/                  # Main plugin package
│       ├── .claude-plugin/
│       │   ├── plugin.json      # Plugin version
│       │   └── marketplace.json # Marketplace version (must match)
│       ├── agents/
│       │   └── config.json      # Agent counts per tier
│       ├── hooks/
│       │   ├── hooks.json       # Hook count
│       │   └── utils/*.py       # Utility module count
│       ├── skills/*/SKILL.md    # Skill count
│       └── commands/*.md        # Command count
```

## Source of Truth Files

| File | Location | Provides |
|------|----------|----------|
| `plugin.json` | `packages/plugin/.claude-plugin/` | Plugin version |
| `marketplace.json` | `packages/plugin/.claude-plugin/` | Marketplace version (should match) |
| `config.json` | `packages/plugin/agents/` | Agent counts per tier |
| `hooks.json` | `packages/plugin/hooks/` | Hook count |
| `SKILL.md` | `packages/plugin/skills/*/` | Skill count (count directories) |
| `*.md` | `packages/plugin/commands/` | Command count (grep for deprecated) |
| `*.py` | `packages/plugin/hooks/utils/` | Utility module count |
| `CHANGELOG.md` | Root | Version history |

## Target Sections

CLAUDE.md contains these auto-generated markers:

| Marker | Content |
|--------|---------|
| `AUTO-GEN:TIER-COUNTS` | Agent tier counts in "Tiered Loading" section |
| `AUTO-GEN:REPO-STRUCTURE` | Directory tree with file/component counts |
| `AUTO-GEN:KEY-FILES` | Important plugin files table |

**Note:** Version history is now in CHANGELOG.md, not CLAUDE.md.

## Process

### 1. Gather Current Counts

```python
import os
import json
from pathlib import Path

# Base paths (monorepo-aware)
root_path = "."  # or detected git root
plugin_path = os.path.join(root_path, "packages", "plugin")

# Read versions
plugin_json = os.path.join(plugin_path, ".claude-plugin", "plugin.json")
marketplace_json = os.path.join(plugin_path, ".claude-plugin", "marketplace.json")

with open(plugin_json) as f:
    plugin_version = json.load(f)["version"]
with open(marketplace_json) as f:
    marketplace_version = json.load(f)["plugins"][0]["version"]

# Read agent config
config_path = os.path.join(plugin_path, "agents", "config.json")
with open(config_path) as f:
    config = json.load(f)

tier1_count = len(config["tiers"]["tier-1-always-active"]["agents"])
tier2_count = len(config["tiers"]["tier-2-on-demand"]["agents"])
feature_count = len(config["tiers"]["feature-workflow"]["agents"])

# Count hooks
hooks_json = os.path.join(plugin_path, "hooks", "hooks.json")
with open(hooks_json) as f:
    hook_count = len(json.load(f)["hooks"])

# Count skills (directories with SKILL.md)
skills_path = os.path.join(plugin_path, "skills")
skill_count = len(list(Path(skills_path).glob("*/SKILL.md")))

# Count commands (exclude deprecated)
commands_path = os.path.join(plugin_path, "commands")
command_files = list(Path(commands_path).glob("*.md"))
active_commands = 0
deprecated_commands = 0
for cmd in command_files:
    content = cmd.read_text()
    if "deprecated: true" in content.lower() or "DEPRECATED" in content:
        deprecated_commands += 1
    else:
        active_commands += 1

# Count utils
utils_path = os.path.join(plugin_path, "hooks", "utils")
utils_count = len(list(Path(utils_path).glob("*.py")))
```

### 2. Parse Documented Values

Read CLAUDE.md and extract values from auto-generated sections:
- Find content between `<!-- AUTO-GEN:X START -->` and `<!-- AUTO-GEN:X END -->`
- Parse numbers from patterns like "11 core agents", "17 specialized agents"

### 3. Compare and Report

```
Documentation Sync Report
=========================

Version Sync:
  plugin.json:      0.9.10
  marketplace.json: 0.9.10 ✓
  CHANGELOG.md:     0.9.10 ✓

Agent Counts:
  Tier 1: config=11, docs=11 ✓
  Tier 2: config=17, docs=17 ✓
  Feature: config=3, docs=3 ✓

Component Counts:
  Skills: found=36, docs=36 ✓
  Commands: found=15 active (7 deprecated), docs=15 ✓
  Hooks: found=18, docs=18 ✓
  Utils: found=24, docs=24 ✓

Status: All synchronized ✓
```

### 4. Fix Drift (--fix mode)

When drift detected:
1. Read the target file (CLAUDE.md)
2. Find the marker section
3. Replace content between markers with updated values
4. Use Edit tool to apply changes
5. Report what was updated

## Modes

### Check Mode (Default)

```
Invoke skill: pop-doc-sync

# Just reports, no changes
```

### Fix Mode

```
Invoke skill: pop-doc-sync --fix

# Updates auto-generated sections
```

### Section Mode

```
Invoke skill: pop-doc-sync --section=repo-structure

# Only check/fix specific section
```

### Verbose Mode

```
Invoke skill: pop-doc-sync --verbose

# Show all comparisons even when matching
```

## Output Format

**When synchronized:**
```
[doc-sync] All documentation synchronized ✓
  Version: 0.9.10
  Agents: 31 (11 tier-1, 17 tier-2, 3 feature)
  Skills: 36, Commands: 15 active, Hooks: 18
```

**When drift detected:**
```
[doc-sync] Documentation drift detected!

  DRIFT: Hooks count
    Source: hooks.json has 18 hooks
    Docs: CLAUDE.md says "19 Python hooks"
    Fix: Update CLAUDE.md line 98

  DRIFT: Skills count
    Source: Found 36 skill directories
    Docs: CLAUDE.md says "35 reusable skills"
    Fix: Update CLAUDE.md line 96

Run with --fix to automatically update.
```

**After fix:**
```
[doc-sync] Fixed 2 drift issues:
  ✓ Updated hooks count: 19 → 18
  ✓ Updated skills count: 35 → 36

CLAUDE.md has been updated.
```

## CHANGELOG.md Sync

The version history is now in a separate CHANGELOG.md file. When checking versions:

1. **Check CLAUDE.md** has correct current version reference:
   ```markdown
   **Current Version:** 0.9.10 (User Feedback & Vote-Based Prioritization)
   ```

2. **Check CHANGELOG.md** has matching version as first entry:
   ```markdown
   ## [0.9.10] - Current
   ```

3. **Check plugin.json and marketplace.json** versions match

If mismatched, report which files need updating.

## Integration Points

### Called By

- `/popkit:plugin docs --check` - Runs check mode
- `/popkit:plugin docs --sync` - Runs fix mode
- `doc-sync` hook (PostToolUse) - Suggests when drift detected
- `/popkit:routine morning` - Part of morning health check
- Power Mode documentation checkpoint

### Triggers This Skill

- Editing plugin.json version
- Adding/removing agents, skills, commands, hooks
- Running `/popkit:plugin docs`

## Implementation Notes

### Marker Format

```markdown
<!-- AUTO-GEN:SECTION-NAME START -->
Content to be replaced
Can span multiple lines
<!-- AUTO-GEN:SECTION-NAME END -->
```

### Regex Patterns

```python
import re

# Find marker sections
MARKER_PATTERN = r'<!-- AUTO-GEN:(\w+[-\w]*) START -->(.*?)<!-- AUTO-GEN:\1 END -->'

# Extract counts from text
COUNT_PATTERNS = {
    "tier1": r'(\d+)\s+core agents',
    "tier2": r'(\d+)\s+specialized agents',
    "feature": r'(\d+)\s+agents for 7-phase',
    "skills": r'(\d+)\s+reusable skills',
    "commands": r'(\d+)\s+slash commands',
    "hooks": r'(\d+)\s+Python hooks',
    "utils": r'(\d+)\s+utility modules'
}
```

### Error Handling

- Missing source file → Report error, skip that check
- Missing marker → Report "marker not found", suggest adding
- Parse failure → Report raw content for manual review
- Monorepo not detected → Fall back to single-package paths

## Example Session

```
User: Check if documentation is in sync
Claude: I'm using the doc-sync skill to check documentation synchronization.

[Reads source files from packages/plugin/, compares to CLAUDE.md]

Documentation Sync Report
=========================

Version: 0.9.10 ✓
Agents: 31 (11 tier-1, 17 tier-2, 3 feature) ✓
Skills: 36 ✓, Commands: 15 active ✓, Hooks: 18 ✓

All documentation synchronized ✓
```

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-auto-docs` | Full documentation generation (this skill focuses on sync only) |
| `pop-plugin-test` | Tests plugin integrity including doc consistency |
| `pop-session-capture` | May trigger doc-sync check before session end |

## Architecture

```
doc-sync skill
     │
     ├── Detect monorepo structure
     │   └── packages/plugin/ or root
     │
     ├── Read source files
     │   ├── packages/plugin/.claude-plugin/plugin.json
     │   ├── packages/plugin/.claude-plugin/marketplace.json
     │   ├── packages/plugin/agents/config.json
     │   ├── packages/plugin/hooks/hooks.json
     │   └── (count directories/files)
     │
     ├── Parse CLAUDE.md markers
     │   ├── AUTO-GEN:TIER-COUNTS
     │   ├── AUTO-GEN:REPO-STRUCTURE
     │   └── AUTO-GEN:KEY-FILES
     │
     ├── Check CHANGELOG.md version
     │
     ├── Compare values
     │   └── Generate drift report
     │
     └── (--fix mode)
         └── Update markers with Edit tool
```
