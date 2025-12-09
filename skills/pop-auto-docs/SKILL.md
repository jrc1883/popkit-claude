---
name: auto-docs
description: "Use when documentation is stale, incomplete, or needs synchronization with codebase changes - automatically generates and updates plugin documentation including CLAUDE.md, README.md, and component docs. Scans agents, skills, commands, and hooks to produce accurate counts and descriptions. Do NOT use for user-facing application docs or when you just need to write a single README - handle those directly."
---

# Auto-Documentation

## Overview

Automatically generate and synchronize plugin documentation by analyzing the codebase structure. Scans agents, skills, commands, hooks, and configuration files to produce accurate, up-to-date documentation.

**Announce at start:** "I'm using the auto-docs skill to generate documentation."

## Capabilities

1. **CLAUDE.md Generation** - Create project instructions from plugin structure
2. **README.md Updates** - Sync feature counts and descriptions
3. **Component Docs** - Generate docs for agents, skills, commands, hooks
4. **Change Detection** - Identify documentation drift from code

## Process

### 1. Scan Plugin Structure

```
Scan directories:
- agents/           → Count and categorize agents
- skills/           → Extract skill descriptions
- commands/         → List available commands
- hooks/            → Document hook events
- output-styles/    → Catalog output formats
```

### 2. Extract Metadata

For each component:
- Parse YAML frontmatter
- Extract name, description, tools
- Identify dependencies and relationships
- Note configuration options

### 3. Generate Documentation

**CLAUDE.md Template:**
```markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview
[Auto-generated from plugin.json]

## Repository Structure
[Auto-generated directory tree]

## Key Components
[Auto-generated from scans]

## Development Notes
[Static section - preserve existing]
```

**README.md Sections:**
- Feature counts (agents, skills, commands, hooks)
- Quick start instructions
- Installation steps
- Configuration options

### 4. Detect Drift

Compare:
- Documented counts vs actual counts
- Listed components vs existing files
- Described features vs implementations

Report discrepancies for manual review.

## Output

| File | Content |
|------|---------|
| CLAUDE.md | Project instructions for Claude Code |
| README.md | User-facing documentation |
| docs/components.md | Detailed component reference |
| docs/drift-report.md | Documentation drift analysis |

## Usage

```
/auto-docs               # Full documentation generation
/auto-docs --check       # Check for drift only
/auto-docs --claude      # Update CLAUDE.md only
/auto-docs --readme      # Update README.md only
```

## Key Principles

- **Accuracy over completeness** - Document what exists, don't fabricate
- **Preserve manual sections** - Mark sections for preservation with `<!-- PRESERVE -->`
- **Atomic updates** - Update one file at a time with verification
- **Show diffs** - Always show what will change before applying

## Integration

**Called by:**
- Session end (optional - check for drift)
- After major changes (suggested by post-tool-use hook)
- Manual invocation via /auto-docs command

**Outputs to:**
- Project root (CLAUDE.md, README.md)
- docs/ directory (detailed docs)
