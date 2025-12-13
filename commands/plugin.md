---
description: "test | docs | sync | detect | version [--verbose, --json]"
argument-hint: "<subcommand> [options]"
---

# /popkit:plugin - Plugin Management

Manage the popkit plugin itself - run tests, generate docs, validate integrity, and manage versions.

## Usage

```
/popkit:plugin <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `test` | Run plugin self-tests (default) |
| `docs` | Generate and update documentation |
| `sync` | Validate plugin integrity |
| `detect` | Detect conflicts with other plugins |
| `version` | Bump version with full release workflow |

---

## Subcommand: test (default)

Run comprehensive tests on plugin components to ensure everything works correctly.

```
/popkit:plugin                        # Run all tests (default)
/popkit:plugin test                   # Same as above
/popkit:plugin test hooks             # Test hooks only
/popkit:plugin test agents            # Test agents only
/popkit:plugin test skills            # Test skills only
/popkit:plugin test routing           # Test agent routing
/popkit:plugin test structure         # Test file structure
```

### Test Categories

| Category | What It Tests |
|----------|---------------|
| `hooks` | JSON stdin/stdout, error handling, timeouts |
| `agents` | Definitions, tools, routing keywords |
| `skills` | SKILL.md format, descriptions, dependencies |
| `routing` | Agent selection based on prompts |
| `structure` | File existence, YAML validity, references |

### Process

1. Load test definitions from `tests/` directory
2. Execute tests by category
3. Report results with pass/fail summary

### Output

```
Running plugin self-tests...

[Structure Tests]
[ok] agents/config.json valid
[ok] hooks/hooks.json valid
[ok] All 29 agents have definitions
[ok] All 22 skills have SKILL.md

[Hook Tests]
[ok] pre-tool-use: JSON protocol
[ok] post-tool-use: JSON protocol
[ok] session-start: JSON protocol
...

[Agent Tests]
[ok] bug-whisperer: definition valid
[ok] code-reviewer: routing keywords work
...

[Routing Tests]
[ok] "fix bug" -> bug-whisperer (0.8 confidence)
[ok] "review code" -> code-reviewer (0.9 confidence)
...

---
Results: 54 passed, 0 failed, 2 skipped
Time: 12.3s
---
```

### Options

| Flag | Description |
|------|-------------|
| `--verbose` | Show detailed test output |
| `--fail-fast` | Stop on first failure |
| `--json` | Output results as JSON |

### Test Files

Test definitions are stored in:
- `tests/hooks/` - Hook input/output tests
- `tests/agents/` - Agent definition tests
- `tests/skills/` - Skill structure tests
- `tests/routing/` - Agent routing tests

---

## Subcommand: docs

Generate and synchronize plugin documentation by analyzing the codebase.

```
/popkit:plugin docs                   # Full documentation check and generation
/popkit:plugin docs --check           # Check for documentation drift only
/popkit:plugin docs --sync            # Auto-fix drift in auto-generated sections
/popkit:plugin docs --json            # Output drift report as JSON
```

### Process

1. **Run doc-sync check** using `hooks/utils/doc_sync.py`:
   - Compare source counts to CLAUDE.md auto-generated sections
   - Detect version mismatches between plugin.json and marketplace.json
   - Identify count drift (agents, skills, commands, hooks, utils)

2. **Invoke skill** based on mode:
   - `--check`: Run `pop-doc-sync` skill in check mode
   - `--sync`: Run `pop-doc-sync` skill with `--fix` flag
   - Default: Check mode with suggestion to run `--sync` if drift found

3. **Report results**:
   - Show source-of-truth counts
   - List any drift issues found
   - Suggest fixes if in check-only mode

### Options

| Flag | Description |
|------|-------------|
| `--check` | Only check for drift, don't update files (default) |
| `--sync` | Automatically fix drift in auto-generated sections |
| `--json` | Output results as JSON |
| `--verbose` | Show all comparisons even when matching |

### Output (Check Mode)

```
/popkit:plugin docs

Documentation Sync Report
=========================

Version Sync:
  plugin.json:      0.9.8
  marketplace.json: 0.9.8 ✓

Agent Counts:
  Tier 1: 11, Tier 2: 17, Feature: 3
  Total: 31

Component Counts:
  Skills: 36
  Commands: 22 (15 active, 7 deprecated)
  Hooks: 18
  Utils: 23

Status: All synchronized ✓
```

### Output (Drift Detected)

```
/popkit:plugin docs

Documentation Sync Report
=========================
...

DRIFT DETECTED: 2 issue(s)
  - skills: source=36, docs=35
  - utils: source=23, docs=22

Run `/popkit:plugin docs --sync` to automatically update CLAUDE.md.
```

### Output (Sync Mode)

```
/popkit:plugin docs --sync

[doc-sync] Fixed 2 drift issues:
  ✓ Updated skills count: 35 → 36
  ✓ Updated utils count: 22 → 23

CLAUDE.md has been updated.
```

### Auto-Generated Sections

The `--sync` mode updates content between these markers in CLAUDE.md:

| Marker | Content Updated |
|--------|-----------------|
| `AUTO-GEN:TIER-COUNTS` | Agent tier counts |
| `AUTO-GEN:REPO-STRUCTURE` | Directory tree with counts |
| `AUTO-GEN:KEY-FILES` | Key files table |

### Related Skill

This command invokes the `pop-doc-sync` skill. See `skills/pop-doc-sync/SKILL.md` for details.

---

## Subcommand: sync

Validate plugin integrity and offer to fix issues.

```
/popkit:plugin sync                   # Analyze and report only
/popkit:plugin sync apply             # Automatically apply safe fixes
/popkit:plugin sync --component=agents
/popkit:plugin sync --component=hooks
```

### Validation Checks

#### Agents (`agents/`)
- All agent files have valid YAML frontmatter
- Required fields present: description, tools
- output_style references exist in `output-styles/`
- Agent is listed in appropriate tier in `config.json`

#### Routing (`agents/config.json`)
- All keywords map to valid agent references
- File patterns are syntactically valid globs
- No orphaned agents (defined but not in any tier)
- No missing agents (referenced but not defined)

#### Output Styles (`output-styles/`)
- All styles have YAML frontmatter
- Schemas exist for styles with `output_style` references

#### Hooks (`hooks/`)
- All hooks in `hooks.json` exist as files
- Python files have valid syntax
- Hooks follow JSON stdin/stdout protocol
- Shebang is `#!/usr/bin/env python3`

#### Skills (`skills/`)
- Each skill directory has `SKILL.md`
- Frontmatter has required fields: name, description
- No duplicate skill names

#### Commands (`commands/`)
- All command files have valid frontmatter
- Description field is present

#### Tests (`tests/`)
- Test files are valid JSON
- Routing rules have test coverage

### Output

```
## Popkit Sync Report

**Scan Date:** [timestamp]
**Components Checked:** 7
**Issues Found:** 1 error, 3 warnings, 2 info

### Summary

| Component | Status | Issues |
|-----------|--------|--------|
| Agents | warning | 2 |
| Routing | pass | 0 |
| Output Styles | error | 1 |
| Hooks | pass | 0 |
| Skills | warning | 1 |
| Commands | pass | 0 |
| Tests | info | 2 |

### Errors (Must Fix)
- `output-styles/agent-handoff.md`: Missing schema

### Warnings (Should Fix)
- `agents/tier-2-on-demand/new-agent.md`: Missing output_style field

### Auto-Fixable Issues
1. Missing schema - Will create from template

Run `/popkit:plugin sync apply` to apply these fixes.
```

### Apply Mode

**Safe Auto-Fixes:**
- Add missing frontmatter fields with defaults
- Register orphaned agents in config.json tiers
- Create missing schema files from templates
- Add missing routing test cases

**Never Auto-Fix:**
- Code changes in hooks
- Agent prompt content
- Skill instructions
- Configuration values requiring decisions

---

## Subcommand: detect

Detect conflicts between popkit and other installed Claude Code plugins.

```
/popkit:plugin detect                 # Full conflict report
/popkit:plugin detect --quick         # One-line summary
/popkit:plugin detect --json          # JSON output
```

### When It Runs

- **On-demand**: Run `/popkit:plugin detect` for full analysis
- **In morning routine**: Quick check included in `/popkit:morning`
- **NOT at session start**: No automatic startup checks (performance)

### Conflict Categories

| Type | Severity | Description |
|------|----------|-------------|
| Command Collision | HIGH | Same command name in multiple plugins |
| Skill Collision | MEDIUM | Same skill name in multiple plugins |
| Hook Collision | MEDIUM | Same event, overlapping tools |
| Routing Overlap | LOW | Same keywords to different agents |

### Process

1. **Scan Plugins**: Find all plugins in `~/.claude/plugins/`
2. **Load Manifests**: Read `plugin.json` from each plugin
3. **Extract Components**: Scan commands, skills, hooks, agents
4. **Compare**: Check for name collisions and overlaps
5. **Report**: Generate conflict report by severity

### Output

```
/popkit:plugin detect

Plugin Conflict Report
==================================================

Plugins Scanned: 3
  - popkit: 16 commands, 30 skills
  - other-plugin: 5 commands, 10 skills
  - another-plugin: 3 commands, 8 skills

Conflicts Found: 2
  High:   1
  Medium: 1
  Low:    0

[HIGH] Conflicts:
  - Command 'commit' defined in multiple plugins: popkit, other-plugin

[MEDIUM] Conflicts:
  - Skill 'code-review' defined in multiple plugins: popkit, another-plugin

Recommendations:
  - Rename or prefix conflicting commands
  - Consider uninstalling conflicting plugin
  - Check plugin priorities in settings
```

### Quick Mode

```
/popkit:plugin detect --quick

Plugin Conflicts: 2 (1 HIGH, 1 medium)
```

Or if no conflicts:

```
Plugin Conflicts: None (3 plugins, all compatible)
```

### Options

| Flag | Description |
|------|-------------|
| `--quick` | One-line summary only |
| `--json` | Output as JSON |
| `--plugins <dir>` | Override plugins directory |

### Integration with Morning

The morning routine includes a quick plugin conflict check:

```
+==================================================================+
|                  Morning Development Status                       |
+==================================================================+
| Ready to Code: 85/100                                             |
+------------------------------------------------------------------+
| ...                                                               |
| Plugin Conflicts:    None detected                                |
| ...                                                               |
+==================================================================+
```

If conflicts are detected:

```
| Plugin Conflicts:    2 (1 HIGH!) - run /popkit:plugin detect     |
```

---

## Subcommand: version

Bump the plugin version with a full release workflow: update version files, changelog, commit, push, and publish.

```
/popkit:plugin version                # Interactive bump (asks for type)
/popkit:plugin version patch          # 1.0.0 → 1.0.1
/popkit:plugin version minor          # 1.0.0 → 1.1.0
/popkit:plugin version major          # 1.0.0 → 2.0.0
/popkit:plugin version --dry-run      # Preview without changes
```

### Process

1. **Determine Version Bump**
   - If type provided (patch/minor/major), use it
   - Otherwise, prompt with AskUserQuestion

2. **Update Version Files**
   - `packages/plugin/.claude-plugin/plugin.json`
   - `packages/plugin/.claude-plugin/marketplace.json`

3. **Update CHANGELOG.md**
   - Add new version header with date
   - Prompt for changelog summary or auto-generate from commits

4. **Commit Changes**
   ```bash
   git add packages/plugin/.claude-plugin/*.json CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z"
   ```

5. **Push to Origin**
   ```bash
   git push origin master
   ```

6. **Publish to Public Repo**
   - Uses `git subtree split` to extract `packages/plugin/`
   - Pushes to `jrc1883/popkit-claude` (public repo)
   - Creates git tag for the version

### Options

| Option | Description |
|--------|-------------|
| `patch` | Increment patch version (1.0.0 → 1.0.1) |
| `minor` | Increment minor version (1.0.0 → 1.1.0) |
| `major` | Increment major version (1.0.0 → 2.0.0) |
| `--dry-run` | Show what would change without modifying files |
| `--no-publish` | Skip publishing to public repo |
| `--no-push` | Skip pushing to origin (local only) |
| `--message "text"` | Custom changelog message |

### Output

```
/popkit:plugin version minor

PopKit Version Bump
===================

Current version: 1.0.0
New version:     1.1.0

Files to update:
  - packages/plugin/.claude-plugin/plugin.json
  - packages/plugin/.claude-plugin/marketplace.json
  - CHANGELOG.md

[1/5] Updating version files...     ✓
[2/5] Adding changelog entry...     ✓
[3/5] Committing changes...         ✓
[4/5] Pushing to origin...          ✓
[5/5] Publishing to popkit-claude...✓

Release complete!
  Tag: v1.1.0
  Public repo: https://github.com/jrc1883/popkit-claude

Users can update with:
  /plugin update popkit@popkit-marketplace
```

### Changelog Entry Format

The changelog entry follows this format:

```markdown
## [X.Y.Z] - Month Day, Year

### Summary

<User-provided or auto-generated summary>

- **Feature/Fix Name**: Description
```

### Version Numbering

Following semantic versioning:
- **MAJOR** (X.0.0): Breaking changes to commands, agents, or hooks
- **MINOR** (0.X.0): New features, commands, or agents (backward compatible)
- **PATCH** (0.0.X): Bug fixes, documentation updates

---

## Examples

```bash
# Run all plugin tests
/popkit:plugin
/popkit:plugin test

# Test specific category
/popkit:plugin test routing
/popkit:plugin test hooks

# Update documentation
/popkit:plugin docs
/popkit:plugin docs check

# Validate plugin integrity
/popkit:plugin sync
/popkit:plugin sync apply

# Detect plugin conflicts
/popkit:plugin detect
/popkit:plugin detect --quick
/popkit:plugin detect --json

# Version management
/popkit:plugin version minor         # Bump minor version
/popkit:plugin version patch         # Bump patch version
/popkit:plugin version --dry-run     # Preview changes
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Test Definitions | `tests/` directory |
| Plugin Test Skill | `skills/pop-plugin-test/SKILL.md` |
| Auto-Docs Skill | `skills/pop-auto-docs/SKILL.md` |
| Doc-Sync Skill | `skills/pop-doc-sync/SKILL.md` |
| Doc-Sync Utility | `hooks/utils/doc_sync.py` |
| Validation Engine | `skills/pop-validation-engine/SKILL.md` |
| Plugin Detector | `hooks/utils/plugin_detector.py` |
| Conflict Report Style | `output-styles/conflict-report.md` |
| Documentation | CLAUDE.md, README.md |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:debug routing` | Debug agent routing issues |
| `/popkit:morning` | Includes plugin conflict check |
| `/popkit:nightly` | End-of-day cleanup and maintenance |
