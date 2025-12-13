# Skill Documentation Standards

Standards for creating clear, effective SKILL.md files.

## Core Principles

### SKD-001: YAML Frontmatter

Every SKILL.md must start with YAML frontmatter.

**Required Fields:**

```yaml
---
name: pop-skill-name
description: "One-line description under 200 characters"
triggers:
  - trigger phrase one
  - trigger phrase two
version: 1.0.0
---
```

**Guidelines:**
- `name`: Use kebab-case with `pop-` prefix
- `description`: Action-oriented, starts with verb
- `triggers`: 2-5 natural language phrases
- `version`: Semantic versioning (MAJOR.MINOR.PATCH)

### SKD-002: Purpose Section

Clear explanation of what the skill does.

**Required Elements:**
- What problem it solves
- When to use it
- Expected outcomes/benefits

**Example:**
```markdown
## Purpose

Validates documentation quality using automated metrics.
Use when auditing project docs or before releases.
Returns coverage percentage and improvement suggestions.
```

### SKD-003: How to Use Section

Step-by-step usage instructions.

**Format:**
```markdown
## How to Use

### Step 1: Prepare Context
[Description of preparation]

### Step 2: Execute Skill
[Invocation method]

### Step 3: Review Output
[What to expect]
```

**Guidelines:**
- Numbered steps
- Code blocks for commands
- Expected outputs described

### SKD-004: Input/Output Documentation

Clear specification of data flow.

**Input Documentation:**
```markdown
## Input

**Required:**
- `project_dir`: Path to project root

**Optional:**
- `--verbose`: Enable detailed output
- `--format json|text`: Output format
```

**Output Documentation:**
```markdown
## Output

Returns JSON with:
- `score`: 0-100 quality score
- `issues`: Array of findings
- `recommendations`: Suggested fixes
```

### SKD-005: Examples

Real-world usage demonstrations.

**Format:**
```markdown
## Examples

### Basic Usage
\`\`\`bash
python scripts/analyze.py ./src
\`\`\`

Output:
\`\`\`json
{"score": 85, "issues": 3}
\`\`\`

### With Options
\`\`\`bash
python scripts/analyze.py ./src --verbose --format text
\`\`\`
```

### SKD-006: Related Skills

Cross-references for discovery.

**Format:**
```markdown
## Related Skills

| Skill | When to Use Instead |
|-------|---------------------|
| pop-other-skill | When doing X instead of Y |
| pop-another | For more detailed Z analysis |
```

### SKD-007: Standards Reference

Link to applicable standards.

**Format:**
```markdown
## Standards Reference

| Standard | File | Key Checks |
|----------|------|------------|
| Code Quality | `standards/quality.md` | Q-001 through Q-010 |
| Security | `standards/security.md` | S-001 through S-005 |
```

### SKD-008: Resource Directory

Document available resources.

**Format:**
```markdown
## Resources

### Scripts
- `scripts/analyze.py` - Main analysis script
- `scripts/report.py` - Report generator

### Checklists
- `checklists/review.json` - Review checklist
- `checklists/audit.json` - Audit checklist

### Standards
- `standards/quality.md` - Quality standards
```

## Template

```markdown
---
name: pop-skill-name
description: "Brief description of what this skill does"
triggers:
  - trigger one
  - trigger two
version: 1.0.0
---

# Skill Name

## Purpose

[What the skill does and why]

## How to Use

### Step 1: [Action]
[Description]

### Step 2: [Action]
[Description]

## Input

**Required:**
- Input 1: Description

**Optional:**
- Option 1: Description

## Output

Returns [format] with:
- Field 1: Description
- Field 2: Description

## Examples

### Basic Usage
\`\`\`bash
[command]
\`\`\`

## Related Skills

- skill-name: When to use

## Standards Reference

| Standard | File |
|----------|------|
| Name | path |
```

## Quality Metrics

| Metric | Target |
|--------|--------|
| Min length | 200 chars |
| Max length | 10,000 chars |
| Required sections | 4+ |
| Examples | 1+ |
| Frontmatter complete | 100% |
