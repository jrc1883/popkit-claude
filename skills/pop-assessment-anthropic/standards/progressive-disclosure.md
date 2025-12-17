# Progressive Disclosure Standard

## Overview

Progressive disclosure ensures context window efficiency by loading only what's needed when it's needed. This standard defines tier limits, lazy loading requirements, and context management.

## Tiered Agent Architecture

### Tier-1: Always-Active

Agents loaded at session start. Should be minimal.

| Requirement | Value | Severity |
|-------------|-------|----------|
| Maximum count | 15 | high |
| Recommended count | 10-12 | medium |
| Each agent | Universal, project-agnostic | medium |

**Examples of Tier-1 agents:**
- code-reviewer (universal)
- bug-whisperer (universal)
- security-auditor (universal)
- test-writer-fixer (universal)

### Tier-2: On-Demand

Agents loaded only when triggered.

| Requirement | Value | Severity |
|-------------|-------|----------|
| Maximum count | No limit | - |
| Activation | Must have trigger | high |
| Trigger types | Keyword, file pattern, error pattern | - |

**Examples of Tier-2 agents:**
- ai-engineer (triggered by ML/AI keywords)
- query-optimizer (triggered by *.sql files)
- rollback-specialist (triggered by deployment errors)

### Feature Workflow

Specialized agents for multi-phase workflows.

| Requirement | Value | Severity |
|-------------|-------|----------|
| Activation | Via workflow command | high |
| Context | Preserved across phases | high |

## Lazy Loading Requirements

### Documentation Loading

| Requirement | Description | Severity |
|-------------|-------------|----------|
| Agent docs | Load only when agent invoked | medium |
| Skill docs | Load only when skill invoked | medium |
| Standards | Load only when assessing | low |
| Reference files | Load on demand | low |

### Anti-Patterns

| Pattern | Problem | Severity |
|---------|---------|----------|
| Loading all agent docs at start | Wastes context | high |
| Including full examples in prompts | Bloats context | medium |
| Embedding docs in CLAUDE.md | Unnecessary duplication | medium |
| Large inline code blocks | Use file references | low |

## Context Efficiency Metrics

### Token Budget

| Component | Max Tokens | Recommended |
|-----------|------------|-------------|
| System prompt | 10,000 | 5,000 |
| Agent definition | 3,000 | 1,500 |
| Skill definition | 2,000 | 1,000 |
| Tool descriptions | 5,000 | 3,000 |

### Efficiency Score Calculation

```
efficiency = 10 - deductions

Deductions:
- Tier-1 > 15 agents: -3
- Tier-1 > 12 agents: -1
- No lazy loading: -2
- Large system prompt: -1
- Inline code blocks > 500 lines: -1
- Duplicate documentation: -2
```

**Target**: 8+ / 10

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| PD-001 | Tier-1 agent count <= 15 | high |
| PD-002 | Tier-1 agent count <= 12 | medium |
| PD-003 | All tier-2 agents have triggers | high |
| PD-004 | No documentation duplication | medium |
| PD-005 | Large files not loaded at start | medium |
| PD-006 | Skills load docs on demand | low |
| PD-007 | CLAUDE.md not bloated (< 500 lines) | medium |
| PD-008 | Agent definitions < 3000 tokens | low |

## Measuring Disclosure

### Startup Context

What gets loaded when Claude Code starts:

```
System prompt (base)
+ CLAUDE.md
+ .claude-plugin/plugin.json (metadata)
+ Tier-1 agent names (NOT full definitions)
+ Active skill names (NOT full definitions)
= Startup context
```

**Target**: < 15,000 tokens at startup

### On-Demand Context

What gets loaded when needed:

```
Agent definition (on agent selection)
Skill definition (on skill invocation)
Reference files (on explicit read)
Standards (on assessment)
```

## Implementation Patterns

### Good: Lazy Reference

```markdown
# SKILL.md
When validation needed, read:
- `standards/hook-protocol.md`
- `checklists/hook-patterns.json`
```

### Bad: Inline Content

```markdown
# SKILL.md
## Hook Protocol (DO NOT DO THIS)

[500 lines of content that could be in a separate file]
```

### Good: Summary + Reference

```markdown
## Agent Capabilities

This agent handles:
- Code review
- Bug detection
- Performance analysis

For detailed criteria, see `standards/review-criteria.md`
```

### Bad: Full Details Inline

```markdown
## Agent Capabilities

### Code Review
[200 lines of detailed criteria]

### Bug Detection
[200 lines of detailed criteria]
```

## References

- Source: packages/plugin/agents/config.json (tiers section)
- Agent definitions: packages/plugin/agents/tier-*/
- CLAUDE.md: packages/plugin/CLAUDE.md
