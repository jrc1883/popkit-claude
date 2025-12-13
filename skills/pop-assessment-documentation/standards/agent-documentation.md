# Agent Documentation Standards

Standards for creating effective AGENT.md files.

## Core Principles

### AGD-001: Agent Header

Clear identification at the top.

**Format:**
```markdown
# Agent Name

Brief one-line description of what this agent does.

**Tier:** 1 (always-active) | 2 (on-demand) | feature-workflow
```

### AGD-002: Purpose Statement

Why this agent exists.

**Required Elements:**
- Problems it solves
- Target scenarios
- Expected benefits

**Example:**
```markdown
## Purpose

The Code Reviewer agent performs comprehensive code reviews
focusing on TypeScript, React, and Node.js best practices.

**Use when:**
- After implementing significant features
- Before merging pull requests
- When code quality assessment is needed

**Benefits:**
- Consistent review standards
- Catches common issues automatically
- Suggests improvements based on best practices
```

### AGD-003: Tools Access

Explicit list of available tools.

**Format:**
```markdown
## Tools

This agent has access to:
- `Read` - Read file contents
- `Grep` - Search for patterns
- `Glob` - Find files by pattern
- `Edit` - Modify existing files

**Restricted:** Cannot use `Bash` for arbitrary commands.
```

### AGD-004: Activation Triggers

How the agent gets invoked.

**Format:**
```markdown
## Triggers

### Keywords
- "review code"
- "check quality"
- "code audit"

### File Patterns
- `*.test.ts` - Test files
- `*.spec.js` - Spec files

### Error Patterns
- `TypeError` - Type-related issues
- `ReferenceError` - Reference problems
```

### AGD-005: Workflow Steps

Step-by-step agent process.

**Format:**
```markdown
## Workflow

1. **Gather Context**
   - Read target files
   - Understand project structure

2. **Analyze Code**
   - Check for issues
   - Apply standards

3. **Generate Report**
   - List findings
   - Provide recommendations

4. **Exit Conditions**
   - Analysis complete
   - User acknowledges findings
```

### AGD-006: Input Requirements

What the agent needs.

**Format:**
```markdown
## Input Requirements

**Required:**
- Target file or directory path
- Review scope (full/partial)

**Optional:**
- Specific focus areas
- Severity threshold

**Prerequisites:**
- TypeScript project
- Source files accessible
```

### AGD-007: Output Description

What the agent produces.

**Format:**
```markdown
## Output

### Report Format
```json
{
  "summary": "Brief overview",
  "issues": [
    {"file": "path", "line": 10, "severity": "high", "message": "..."}
  ],
  "score": 85
}
```

### Artifacts Generated
- Review report (markdown)
- Issue list (if any)
- Improvement suggestions
```

### AGD-008: Configuration

Available options.

**Format:**
```markdown
## Configuration

Located in `agents/config.json`:

\`\`\`json
{
  "code-reviewer": {
    "severity_threshold": 80,
    "max_files": 50,
    "focus_areas": ["security", "performance"]
  }
}
\`\`\`
```

### AGD-009: Examples

Usage demonstrations.

**Format:**
```markdown
## Examples

### Basic Review
```
User: Review the authentication module
Agent: [Reads src/auth/*, analyzes, produces report]
```

### Targeted Review
```
User: Check security in api/routes.ts
Agent: [Focuses on security patterns in specified file]
```
```

### AGD-010: Limitations

Known constraints.

**Format:**
```markdown
## Limitations

**Cannot:**
- Review binary files
- Access external APIs
- Modify code without approval

**Known Issues:**
- May flag valid patterns in certain frameworks
- Performance degrades with 100+ files

**Workarounds:**
- Use file filters for large codebases
- Provide framework context in prompts
```

### AGD-011: Related Agents

Cross-references.

**Format:**
```markdown
## Related Agents

| Agent | Relationship |
|-------|-------------|
| test-writer | Complements reviews with tests |
| refactoring-expert | Takes over for major changes |
| security-auditor | For security-focused reviews |
```

### AGD-012: Confidence Threshold

Routing information.

**Format:**
```markdown
## Routing

**Confidence Range:** 70-100
**Activation Threshold:** 75

**Disambiguation:**
- If confidence 60-75, suggest alternatives
- If multiple agents match, prefer based on file type
```

## Template

```markdown
# Agent Name

Brief description.

**Tier:** [1/2/feature-workflow]

## Purpose

What the agent does and why.

## Tools

- Tool 1
- Tool 2

## Triggers

- Keyword triggers
- File patterns

## Workflow

1. Step one
2. Step two

## Input Requirements

**Required:**
- Requirement 1

## Output

- Output description

## Examples

### Example 1
[Usage example]

## Limitations

- Limitation 1

## Related Agents

- Agent 1: When to use
```

## Quality Metrics

| Metric | Target |
|--------|--------|
| Min length | 100 chars |
| Required sections | 5+ |
| Tools listed | Yes |
| Triggers documented | Yes |
| Examples provided | 1+ |
