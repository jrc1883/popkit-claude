---
name: doc-sync
description: "Use when documentation counts are wrong, versions are mismatched, or CLAUDE.md needs updating - synchronizes auto-generated sections by reading source-of-truth files (plugin.json, config.json, hooks.json) and updating markers in CLAUDE.md. Do NOT use for writing new documentation or prose - this is specifically for keeping counts and versions in sync."
---

# Documentation Sync

## Overview

Synchronize documentation by reading source-of-truth files and updating auto-generated sections marked with `<!-- AUTO-GEN:SECTION-NAME START/END -->` comments.

**Announce at start:** "I'm using the doc-sync skill to check documentation synchronization."

## Source of Truth Files

| File | Provides |
|------|----------|
| `.claude-plugin/plugin.json` | Plugin version |
| `.claude-plugin/marketplace.json` | Marketplace version (should match) |
| `agents/config.json` | Agent counts per tier |
| `hooks/hooks.json` | Hook count |
| `skills/*/SKILL.md` | Skill count (count directories) |
| `commands/*.md` | Command count (grep for deprecated) |
| `hooks/utils/*.py` | Utility module count |

## Target Sections

CLAUDE.md contains these auto-generated markers:

| Marker | Content |
|--------|---------|
| `AUTO-GEN:TIER-COUNTS` | Agent tier counts in "Tiered Loading" section |
| `AUTO-GEN:REPO-STRUCTURE` | Directory tree with file/component counts |
| `AUTO-GEN:KEY-FILES` | Important plugin files table |

## Process

### 1. Gather Current Counts

```python
# Read source files and count:
plugin_version = read_json(".claude-plugin/plugin.json")["version"]
marketplace_version = read_json(".claude-plugin/marketplace.json")["version"]
tier1_count = len(config["tiers"]["tier-1-always-active"]["agents"])
tier2_count = len(config["tiers"]["tier-2-on-demand"]["agents"])
feature_count = len(config["tiers"]["feature-workflow"]["agents"])
hook_count = len(hooks_json["hooks"])
skill_count = count_dirs("skills/*/SKILL.md")
command_count = count_files("commands/*.md")
deprecated_count = grep_count("deprecated", "commands/*.md")
utils_count = count_files("hooks/utils/*.py")
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
  plugin.json:      0.9.8
  marketplace.json: 0.9.8 ✓

Agent Counts:
  Tier 1: config=11, docs=11 ✓
  Tier 2: config=17, docs=17 ✓
  Feature: config=2, docs=2 ✓

Component Counts:
  Skills: found=35, docs=35 ✓
  Commands: found=22, docs=22 ✓
  Hooks: found=18, docs=18 ✓
  Utils: found=22, docs=22 ✓

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
  Version: 0.9.8
  Agents: 30 (11 tier-1, 17 tier-2, 2 feature)
  Skills: 35, Commands: 22, Hooks: 18
```

**When drift detected:**
```
[doc-sync] Documentation drift detected!

  DRIFT: Hooks count
    Source: hooks.json has 18 hooks
    Docs: CLAUDE.md says "19 Python hooks"
    Fix: Update CLAUDE.md line 98

  DRIFT: Skills count
    Source: Found 35 skill directories
    Docs: CLAUDE.md says "34 reusable skills"
    Fix: Update CLAUDE.md line 96

Run with --fix to automatically update.
```

**After fix:**
```
[doc-sync] Fixed 2 drift issues:
  ✓ Updated hooks count: 19 → 18
  ✓ Updated skills count: 34 → 35

CLAUDE.md has been updated.
```

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

## Example Session

```
User: Check if documentation is in sync
Claude: I'm using the doc-sync skill to check documentation synchronization.

[Reads source files, compares to CLAUDE.md]

Documentation Sync Report
=========================

Version: 0.9.8 ✓
Agents: 30 (11 tier-1, 17 tier-2, 2 feature) ✓
Skills: 35 ✓, Commands: 22 ✓, Hooks: 18 ✓

All documentation synchronized ✓
```

```
User: The hooks count is wrong, please fix it

Claude: I'm using the doc-sync skill with --fix to update documentation.

[Reads hooks.json: 18 hooks]
[Reads CLAUDE.md: says "19 Python hooks"]

DRIFT detected: Hooks count (19 → 18)

Fixing...
[Updates CLAUDE.md AUTO-GEN:REPO-STRUCTURE section]

Fixed 1 drift issue:
  ✓ Updated hooks count: 19 → 18
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
     ├── Read source files
     │   ├── .claude-plugin/plugin.json
     │   ├── .claude-plugin/marketplace.json
     │   ├── agents/config.json
     │   ├── hooks/hooks.json
     │   └── (count directories/files)
     │
     ├── Parse CLAUDE.md markers
     │   ├── AUTO-GEN:TIER-COUNTS
     │   ├── AUTO-GEN:REPO-STRUCTURE
     │   └── AUTO-GEN:KEY-FILES
     │
     ├── Compare values
     │   └── Generate drift report
     │
     └── (--fix mode)
         └── Update markers with Edit tool
```
