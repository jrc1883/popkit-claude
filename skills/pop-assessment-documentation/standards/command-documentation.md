# Command Documentation Standards

Standards for documenting slash commands.

## Core Principles

### CMD-001: Command Header

Clear identification and purpose.

**Format:**
```markdown
---
description: "Brief description for command list"
---

# /command-name

One-paragraph description of what this command does.
```

### CMD-002: Subcommands

Document all available subcommands.

**Format:**
```markdown
## Subcommands

| Subcommand | Description |
|------------|-------------|
| `action1` | What action1 does |
| `action2` | What action2 does |
| (default) | What happens with no subcommand |
```

### CMD-003: Flags and Options

All available flags documented.

**Format:**
```markdown
## Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--verbose` | `-v` | Enable detailed output | false |
| `--format` | `-f` | Output format (json/text) | text |
| `--dry-run` | | Preview without executing | false |
```

### CMD-004: Usage Examples

Real invocation examples.

**Format:**
```markdown
## Examples

### Basic Usage
\`\`\`
/command action
\`\`\`

### With Options
\`\`\`
/command action --verbose --format json
\`\`\`

### Common Patterns
\`\`\`
# Pattern 1: Quick check
/command check

# Pattern 2: Full analysis
/command analyze --all --verbose
\`\`\`
```

### CMD-005: Output Description

What the command returns.

**Format:**
```markdown
## Output

### Success Output
- Summary message
- Action results
- Next steps (if any)

### Error Output
- Error message format
- Common error codes
- Resolution hints
```

### CMD-006: Prerequisites

Requirements before using.

**Format:**
```markdown
## Prerequisites

- Git repository initialized
- CLAUDE.md present
- Node.js 18+ installed
```

### CMD-007: Related Commands

Cross-references.

**Format:**
```markdown
## Related Commands

| Command | When to Use |
|---------|-------------|
| `/other-cmd` | For X instead of Y |
| `/another` | After completing this command |
```

### CMD-008: Skill Integration

Document underlying skills.

**Format:**
```markdown
## Implementation

This command invokes:
- `pop-skill-one` - For initial analysis
- `pop-skill-two` - For report generation

**Skill Sequence:**
1. skill-one processes input
2. skill-two generates output
```

## Template

```markdown
---
description: "One-line description for command list"
---

# /command-name

What this command does in 1-2 sentences.

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `action` | What it does |

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--flag` | What it does | value |

## Examples

### Basic
\`\`\`
/command action
\`\`\`

### With Options
\`\`\`
/command action --flag value
\`\`\`

## Output

What the command returns.

## Prerequisites

- Requirement 1

## Related Commands

- /related: When to use
```

## Quality Checklist

| Check | Required | Description |
|-------|----------|-------------|
| Description in frontmatter | Yes | Shows in command list |
| Purpose paragraph | Yes | What and why |
| Subcommands table | If applicable | All subcommands |
| Flags table | If applicable | All options |
| Examples | Yes | At least one |
| Output description | Yes | What to expect |
| Prerequisites | If applicable | Requirements |
| Related commands | No | Cross-references |

## Common Patterns

### Action Commands
```markdown
/command action [target] [--options]

Actions operate on targets with optional flags.
```

### Query Commands
```markdown
/command query [filter]

Queries return information matching optional filters.
```

### Configuration Commands
```markdown
/command set key value
/command get key
/command list

Configuration commands manage settings.
```

## Anti-Patterns

**Avoid:**
- Undocumented flags
- Missing examples
- Vague descriptions
- Inconsistent flag naming
- Missing error documentation
