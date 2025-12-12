# Agent Routing Standard

## Overview

Agent routing determines which specialized agent handles a request based on keywords, file patterns, and error patterns. This standard defines coverage requirements and conflict resolution.

## Routing Mechanisms

### 1. Keyword Routing

Maps keywords in user requests to agents.

```json
{
  "routing": {
    "keywords": {
      "bug": ["bug-whisperer"],
      "security": ["security-auditor"],
      "performance": ["performance-optimizer"],
      "test": ["test-writer-fixer"],
      "review": ["code-reviewer"]
    }
  }
}
```

**Requirements:**

| Requirement | Description | Severity |
|-------------|-------------|----------|
| Coverage | All tier-1 agents should have at least 1 keyword | high |
| Specificity | Keywords should be specific (not "code", "help") | medium |
| No conflicts | Same keyword shouldn't map to competing agents | high |

### 2. File Pattern Routing

Maps file extensions and paths to agents.

```json
{
  "filePatterns": {
    "*.test.ts": ["test-writer-fixer"],
    "*.spec.ts": ["test-writer-fixer"],
    "*.sql": ["query-optimizer"],
    "Dockerfile": ["devops-automator"],
    "*.md": ["documentation-maintainer"]
  }
}
```

**Required Patterns:**

| Pattern | Agent | Severity |
|---------|-------|----------|
| `*.test.*` | test-writer-fixer | high |
| `*.spec.*` | test-writer-fixer | high |
| `*.sql` | query-optimizer | medium |
| `*.md` | documentation-maintainer | medium |
| `Dockerfile*` | devops-automator | medium |
| `*.yaml`, `*.yml` | devops-automator | medium |
| `.env*` | security-auditor | high |

### 3. Error Pattern Routing

Maps error types to debugging agents.

```json
{
  "errorPatterns": {
    "TypeError": ["bug-whisperer"],
    "SyntaxError": ["code-reviewer"],
    "SecurityError": ["security-auditor"],
    "PerformanceWarning": ["performance-optimizer"]
  }
}
```

**Required Error Patterns:**

| Error | Agent | Severity |
|-------|-------|----------|
| TypeError | bug-whisperer | high |
| SyntaxError | code-reviewer | high |
| SecurityError | security-auditor | critical |
| ImportError | migration-specialist | medium |
| ConnectionError | devops-automator | medium |
| MemoryError | performance-optimizer | medium |

## Coverage Requirements

### Tier-1 Agent Coverage

All tier-1 (always-active) agents MUST be routable:

| Check | Rule | Severity |
|-------|------|----------|
| Keyword coverage | At least 1 keyword per agent | high |
| Fallback routing | Default agent for unmatched | medium |

### Tier-2 Agent Coverage

Tier-2 (on-demand) agents SHOULD have activation triggers:

| Check | Rule | Severity |
|-------|------|----------|
| Trigger defined | Should have keyword, pattern, or error | medium |
| Documentation | Activation conditions documented | low |

## Conflict Resolution

### Priority Order

When multiple agents match:

1. **Exact keyword match** > Partial match
2. **More specific pattern** > General pattern
3. **Higher tier** > Lower tier
4. **First defined** > Later defined

### Conflict Detection

| Conflict Type | Example | Severity |
|---------------|---------|----------|
| Same keyword, different agents | "test" → [A, B] | warning |
| Overlapping patterns | `*.ts`, `*.test.ts` | low |
| Circular routing | A → B → A | critical |

## Validation Checklist

| Check ID | Description | Severity |
|----------|-------------|----------|
| AR-001 | All tier-1 agents have keywords | high |
| AR-002 | No duplicate keyword mappings | high |
| AR-003 | File patterns are valid globs | critical |
| AR-004 | Error patterns match real errors | medium |
| AR-005 | Referenced agents exist | critical |
| AR-006 | No circular routing | critical |
| AR-007 | Common file types covered | medium |
| AR-008 | Common errors covered | medium |

## Calculating Coverage

### Keyword Coverage

```
coverage = (agents_with_keywords / total_tier1_agents) * 100
```

**Target**: 95%+

### File Pattern Coverage

```
coverage = (matched_common_patterns / total_common_patterns) * 100
```

Common patterns: `*.ts`, `*.js`, `*.py`, `*.md`, `*.json`, `*.yaml`, `*.yml`, `*.sql`, `Dockerfile`, `.env*`

**Target**: 80%+

### Error Pattern Coverage

```
coverage = (matched_common_errors / total_common_errors) * 100
```

Common errors: TypeError, SyntaxError, ReferenceError, ImportError, SecurityError, ConnectionError

**Target**: 80%+

## References

- Source: packages/plugin/agents/config.json
- Agent definitions: packages/plugin/agents/tier-*/*/AGENT.md
