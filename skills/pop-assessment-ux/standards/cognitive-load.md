# Cognitive Load Standards

Standards for minimizing user cognitive load in CLI interactions.

## Core Principles

### CL-001: Progressive Disclosure

Show only what's needed at each step.

**Layers:**
1. **Essential** - Minimum to complete task
2. **Important** - Helpful but not critical
3. **Advanced** - Expert options

**Implementation:**
```
# Default (essential)
/popkit:project init my-project

# With options (important)
/popkit:project init my-project --template react

# Full control (advanced)
/popkit:project init my-project --template react --no-git --package-manager pnpm
```

### CL-002: Chunking Information

Group related items together.

**Guidelines:**
- Max 7±2 items per group
- Logical groupings by function
- Clear group labels

**Example:**
```
Project Commands:
  init     Initialize new project
  analyze  Analyze existing project
  generate Generate components

Git Commands:
  commit   Create a commit
  push     Push to remote
  pr       Create pull request
```

### CL-003: Recognition Over Recall

Show options rather than requiring memorization.

**Techniques:**
- Tab completion
- Suggestion prompts
- Recent commands
- Contextual help

**Example:**
```
# Instead of free text
Enter framework name: [blank]

# Show options
Which framework?
> React (Recommended)
  Vue
  Svelte
  Other
```

### CL-004: Consistent Mental Models

Maintain consistent patterns users can learn once.

**Patterns to Maintain:**
| Pattern | Consistency |
|---------|-------------|
| Command structure | Always verb-noun |
| Flag format | Always --flag or -f |
| Output format | Always same structure |
| Error format | Always same template |

### CL-005: Reduce Decision Points

Minimize the number of decisions required.

**Techniques:**
- Smart defaults
- Preset configurations
- "Quick" vs "Custom" modes
- Inferred settings

**Example:**
```
Quick setup (Recommended):
  - TypeScript
  - ESLint + Prettier
  - Jest for testing

Use quick setup? [Y/n]
```

### CL-006: Clear Visual Hierarchy

Use formatting to guide attention.

**Hierarchy:**
1. **Headers** - Command/section names
2. **Key information** - Status, results
3. **Details** - Supporting info
4. **Metadata** - Timestamps, counts

**Formatting:**
```
# Header (bold in terminal)
PROJECT ANALYSIS COMPLETE

# Key information
Score: 85/100 (Good)

# Details
  ✓ Code quality: 90/100
  ✓ Test coverage: 78%
  ⚠ Documentation: 65%

# Metadata
Analyzed 42 files in 2.3s
```

## Information Architecture

### Menu Structure

**Max Depth:** 3 levels
```
Level 1: /popkit:category
Level 2: /popkit:category subcommand
Level 3: /popkit:category subcommand action
```

### Help Organization

**Structure:**
```
COMMAND
  Brief description

USAGE
  /command [options] <required> [optional]

OPTIONS
  Most common options first
  Advanced options last

EXAMPLES
  Most common use case first
  Edge cases if space permits
```

### Output Organization

**Success Output:**
```
[Status emoji] Main result
  - Detail 1
  - Detail 2

Next: Suggested action
```

**Error Output:**
```
[Error emoji] What happened
  Context: Where/what

Fix: How to resolve
Help: Link to docs
```

## Attention Management

### What Demands Attention

| Item | Priority |
|------|----------|
| Errors | High - immediate |
| Warnings | Medium - consider |
| Success | Low - confirmation |
| Info | Minimal - background |

### Notification Principles

- Important updates first
- Actionable items highlighted
- Non-critical info suppressed by default
- Use `--verbose` for full details

## Measurement

### Cognitive Load Indicators

| Indicator | Target |
|-----------|--------|
| Options per prompt | ≤4 |
| Steps per workflow | ≤7 |
| Commands to memorize | 0 (show options) |
| Info per screen | Fits without scroll |

### Quality Metrics

| Metric | Target |
|--------|--------|
| Progressive disclosure | All commands |
| Consistent patterns | 100% |
| Smart defaults | All configs |
| Clear hierarchy | All output |
