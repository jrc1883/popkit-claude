# Agent Routing Strategy

This document describes PopKit's intelligent agent routing system that automatically selects the right specialized agent for each task.

## Overview

PopKit uses a **three-mechanism routing system** to match user requests with specialized agents:

1. **Keyword Routing** - Routes based on words in the request
2. **File Pattern Routing** - Routes based on file extensions and paths
3. **Error Pattern Routing** - Routes based on error types and exceptions

All routing rules are defined in `config.json` and can be extended per-project.

## Architecture

### Tiered Agent System

PopKit organizes agents into tiers for optimal performance:

| Tier | Count | Loading | Purpose |
|------|-------|---------|---------|
| **Tier 1** (Always Active) | 11 | Loaded on startup | Core agents for common tasks |
| **Tier 2** (On-Demand) | 17 | Activated by triggers | Specialized agents for specific scenarios |
| **Feature Workflow** | 3 | Phase-based | 7-phase feature development |
| **Assessors** | 6 | Manual invocation | Multi-perspective code review |

**Total**: 31 agents + 6 assessors

### Routing Flow

```
User Request
    ↓
Parse keywords, file context, error messages
    ↓
Match against routing rules (keywords, patterns, errors)
    ↓
Select agent(s) based on confidence + tier priority
    ↓
Activate agent with appropriate context
```

## Routing Mechanism 1: Keyword Routing

### How It Works

Keywords in the user's message are matched against the `routing.keywords` map. Each keyword maps to one or more agents.

### Examples

| User Request | Matched Keyword | Selected Agent(s) |
|--------------|-----------------|-------------------|
| "Fix this bug in login" | `bug` | bug-whisperer, test-writer-fixer |
| "Review my PR" | `pr` | code-reviewer |
| "Optimize database query" | `optimize`, `database` | performance-optimizer, query-optimizer |
| "Security audit API" | `security`, `api` | security-auditor, api-designer |
| "Deploy to production" | `deploy` | deployment-validator, devops-automator |

### Configuration

```json
{
  "routing": {
    "keywords": {
      "bug": ["bug-whisperer", "test-writer-fixer"],
      "security": ["security-auditor"],
      "performance": ["performance-optimizer", "bundle-analyzer"],
      "optimize": ["performance-optimizer", "query-optimizer"],
      "test": ["test-writer-fixer"],
      "api": ["api-designer"],
      "refactor": ["refactoring-expert"],
      "docs": ["documentation-maintainer"],
      "database": ["query-optimizer"],
      "migration": ["migration-specialist"],
      "accessibility": ["accessibility-guardian"],
      "deploy": ["deployment-validator", "devops-automator"]
    }
  }
}
```

### Multi-Keyword Matching

When multiple keywords match, agents are merged:

```
Request: "Fix security bug in authentication"
Keywords: "security", "bug"
Agents: security-auditor + bug-whisperer
Result: Both agents activated (security-auditor takes lead)
```

### Priority Rules

When multiple agents match the same keyword:

1. **First agent** in the array is the primary
2. **Additional agents** are consulted for their expertise
3. **Tier 1 agents** take priority over Tier 2

## Routing Mechanism 2: File Pattern Routing

### How It Works

When a file is mentioned or being edited, its path is matched against `routing.filePatterns`. This automatically activates the appropriate specialist.

### Examples

| File Path | Matched Pattern | Selected Agent(s) |
|-----------|-----------------|-------------------|
| `src/auth/login.test.ts` | `*.test.ts` | test-writer-fixer |
| `database/migrations/001.sql` | `*.sql` | query-optimizer |
| `README.md` | `*.md` | documentation-maintainer |
| `Dockerfile` | `Dockerfile` | devops-automator |
| `.env.production` | `.env*` | security-auditor |
| `components/Button.tsx` | `*.tsx`, `*/components/*` | rapid-prototyper, accessibility-guardian |

### Configuration

```json
{
  "routing": {
    "filePatterns": {
      "*.test.ts": ["test-writer-fixer"],
      "*.spec.ts": ["test-writer-fixer"],
      "*.tsx": ["rapid-prototyper", "accessibility-guardian"],
      "*.jsx": ["rapid-prototyper", "accessibility-guardian"],
      "*.sql": ["query-optimizer"],
      "*.md": ["documentation-maintainer"],
      "package.json": ["bundle-analyzer"],
      "Dockerfile": ["devops-automator"],
      ".env*": ["security-auditor"],
      ".eslintrc*": ["code-reviewer"],
      "eslint.config.*": ["code-reviewer"],
      ".prettierrc*": ["code-reviewer"],
      "*.config.js": ["code-reviewer"],
      "*.config.ts": ["code-reviewer"],
      "tsconfig*.json": ["code-reviewer"],
      "*.css": ["rapid-prototyper", "accessibility-guardian"],
      "*.scss": ["rapid-prototyper", "accessibility-guardian"],
      "*.html": ["rapid-prototyper", "accessibility-guardian"],
      "*/components/*": ["rapid-prototyper", "accessibility-guardian"],
      "*/ui/*": ["rapid-prototyper", "accessibility-guardian"],
      "*/styles/*": ["rapid-prototyper", "accessibility-guardian"],
      "tailwind.config.*": ["rapid-prototyper", "accessibility-guardian"]
    }
  }
}
```

### Glob Pattern Support

File patterns support standard glob syntax:

- `*.ext` - Any file with extension
- `*.test.*` - Files with `.test.` in name
- `*/dir/*` - Files in any directory named `dir`
- `.env*` - Files starting with `.env`
- `*config.*` - Files with `config` in name

### Multiple Pattern Matches

Files can match multiple patterns:

```
File: src/components/Button.tsx
Patterns matched:
  - *.tsx → rapid-prototyper, accessibility-guardian
  - */components/* → rapid-prototyper, accessibility-guardian
Result: Both agents activated (deduplicated)
```

## Routing Mechanism 3: Error Pattern Routing

### How It Works

When errors are detected in tool output or user messages, error types are matched against `routing.errorPatterns` to activate debugging specialists.

### Examples

| Error Message | Matched Pattern | Selected Agent(s) |
|---------------|-----------------|-------------------|
| `TypeError: Cannot read property 'name'` | `TypeError` | bug-whisperer |
| `SyntaxError: Unexpected token` | `SyntaxError` | code-reviewer |
| `SecurityError: Permission denied` | `SecurityError` | security-auditor |
| `MemoryError: Out of memory` | `MemoryError` | performance-optimizer |
| `ModuleNotFoundError: No module named 'x'` | `ModuleNotFoundError` | migration-specialist |
| `ConnectionError: Failed to connect` | `ConnectionError` | devops-automator |

### Configuration

```json
{
  "routing": {
    "errorPatterns": {
      "TypeError": ["bug-whisperer"],
      "SyntaxError": ["code-reviewer"],
      "ReferenceError": ["bug-whisperer"],
      "RangeError": ["bug-whisperer"],
      "SecurityError": ["security-auditor"],
      "PermissionError": ["security-auditor"],
      "AuthenticationError": ["security-auditor"],
      "PerformanceWarning": ["performance-optimizer"],
      "MemoryError": ["performance-optimizer"],
      "TimeoutError": ["performance-optimizer"],
      "DeprecationWarning": ["migration-specialist"],
      "ImportError": ["migration-specialist"],
      "ModuleNotFoundError": ["migration-specialist"],
      "ConnectionError": ["devops-automator"],
      "NetworkError": ["devops-automator"],
      "DNSError": ["devops-automator"]
    }
  }
}
```

### Error Detection

Errors are detected from:

1. **Bash tool output** - stderr from commands
2. **Test failures** - jest/pytest/etc error messages
3. **User messages** - "I'm getting a TypeError..."
4. **Log analysis** - Application logs

### Automatic Context Passing

When an error pattern triggers:

1. Error message is captured
2. Stack trace is extracted
3. Relevant files are identified
4. Context is passed to the agent

```
Error: TypeError in auth/login.ts:42
    ↓
bug-whisperer activated with:
  - Error message
  - Stack trace
  - File: auth/login.ts (lines around 42)
  - Related test files
```

## Agent Selection Algorithm

### Priority Resolution

When multiple mechanisms match, priority is:

1. **Error patterns** (highest priority - immediate debugging)
2. **File patterns** (context-specific)
3. **Keywords** (user intent)

### Example: Multi-Mechanism Match

```
Request: "Fix TypeError in Button.tsx"
File: src/components/Button.tsx
Error: TypeError

Matches:
  Error Pattern: TypeError → bug-whisperer
  File Pattern: *.tsx → rapid-prototyper, accessibility-guardian
  Keyword: "fix" → (no direct match)

Selected Agents:
  Primary: bug-whisperer (error takes priority)
  Supporting: rapid-prototyper (component context)
  Supporting: accessibility-guardian (UI validation)
```

### Confidence Filtering

Agents use confidence thresholds to filter false positives:

```json
{
  "confidence": {
    "threshold": 80,
    "levels": {
      "0": "Not a real problem",
      "25": "Possibly valid",
      "50": "Moderately confident",
      "75": "Highly confident",
      "100": "Absolutely certain"
    }
  }
}
```

**Usage in agents:**

- code-reviewer only reports issues with 80+ confidence
- Prevents "noisy" reports on minor style preferences
- Focuses attention on genuine problems

## Workflows

### Feature Development Workflow

The `/popkit:feature-dev` command follows a 7-phase workflow:

```
Phase 1: Discovery
  ↓
Phase 2: Exploration (code-explorer)
  ↓
Phase 3: Questions
  ↓
Phase 4: Architecture (code-architect)
  ↓
Phase 5: Implementation
  ↓
Phase 6: Review (code-reviewer)
  ↓
Phase 7: Summary
```

**Configuration:**

```json
{
  "workflows": {
    "feature-dev": {
      "phases": [
        {"name": "Discovery", "agents": []},
        {"name": "Exploration", "agents": ["code-explorer"]},
        {"name": "Questions", "agents": []},
        {"name": "Architecture", "agents": ["code-architect"]},
        {"name": "Implementation", "agents": []},
        {"name": "Review", "agents": ["code-reviewer"]},
        {"name": "Summary", "agents": []}
      ]
    }
  }
}
```

### Debug Workflow

Sequential debugging with multiple specialists:

```json
{
  "workflows": {
    "debug": {
      "agents": ["bug-whisperer", "log-analyzer"],
      "sequential": true
    }
  }
}
```

1. bug-whisperer analyzes the error
2. log-analyzer examines logs for patterns
3. Results are combined for root cause analysis

### Security Audit Workflow

Parallel security analysis:

```json
{
  "workflows": {
    "security-audit": {
      "agents": ["security-auditor"],
      "sequential": false
    }
  }
}
```

## Tier-Specific Routing

### Tier 1 (Always Active)

These agents are **always available** for routing:

- code-reviewer
- bug-whisperer
- security-auditor
- test-writer-fixer
- api-designer
- performance-optimizer
- refactoring-expert
- documentation-maintainer
- query-optimizer
- migration-specialist
- accessibility-guardian

**Characteristics:**
- Load immediately on startup
- Handle 80% of common tasks
- Low activation overhead
- Can be combined with Tier 2 agents

### Tier 2 (On-Demand)

These agents are **activated only when triggered**:

- ai-engineer
- deployment-validator
- feature-prioritizer
- rapid-prototyper
- backup-coordinator
- meta-agent
- researcher
- user-story-writer
- devops-automator
- bundle-analyzer
- log-analyzer
- metrics-collector
- feedback-synthesizer
- rollback-specialist
- data-integrity
- dead-code-eliminator
- power-coordinator

**Characteristics:**
- Loaded on first use
- Specialized for specific scenarios
- Reduce startup overhead
- Unload after task completion

### Feature Workflow Agents

Phase-specific agents for feature development:

- code-explorer (Phase 2: Exploration)
- code-architect (Phase 4: Architecture)
- code-reviewer (Phase 6: Review)

**Characteristics:**
- Loaded only during `/popkit:feature-dev`
- Activated at specific workflow phases
- Maintain context across phases
- Collaborate in sequence

## Plan Mode Configuration

As of Claude Code 2.0.70+, agents can present implementation plans for user approval before executing changes.

### Plan Mode Strategy

```json
{
  "plan_mode": {
    "tier_defaults": {
      "tier-1-always-active": false,
      "tier-2-on-demand": true,
      "feature-workflow": "per-agent"
    }
  }
}
```

**Rationale:**

- **Tier 1**: Core agents are read-only or low-risk, can execute directly
- **Tier 2**: Specialized agents modify code/deploy, require approval
- **Feature Workflow**: Varies by phase (exploration=no plan, architecture=plan)

### Agent-Specific Overrides

```json
{
  "plan_mode": {
    "agent_overrides": {
      "code-explorer": false,           // Read-only analysis
      "code-architect": true,            // Generates implementation plans
      "bug-whisperer": true,             // Code modifications
      "security-auditor": true,          // Security-critical changes
      "deployment-validator": false,     // Read-only validation
      "devops-automator": true,          // Infrastructure changes
      "documentation-maintainer": false  // Low-risk doc updates
    }
  }
}
```

**User Overrides:**

- `--require-plans`: Force all agents to present plans
- `--trust-agents`: Allow all agents to execute directly
- Default: Use configuration-based strategy

## Model Assignment

Agents are assigned Claude models based on task complexity:

| Model | Use Case | Example Agents |
|-------|----------|----------------|
| **Haiku** | Writing-focused, quick tasks | documentation-maintainer, feature-prioritizer, user-story-writer |
| **Sonnet** | Balanced analysis + implementation | code-reviewer, test-writer-fixer, api-designer, refactoring-expert |
| **Opus** | Deep reasoning, critical decisions | bug-whisperer, security-auditor, performance-optimizer, code-architect |

**Configuration:**

```json
{
  "model": {
    "default": "sonnet",
    "agents": {
      "tier-1-always-active": {
        "bug-whisperer": "opus",
        "security-auditor": "opus",
        "query-optimizer": "opus"
      }
    }
  }
}
```

**Override:**

```bash
/popkit:debug --model opus    # Force Opus for this session
```

## Effort Parameter

Compute allocation per agent (Claude API platform feature):

```json
{
  "effort": {
    "default": "medium",
    "agents": {
      "tier-1-always-active": {
        "bug-whisperer": "high",
        "security-auditor": "high",
        "performance-optimizer": "high",
        "documentation-maintainer": "low"
      }
    }
  }
}
```

**Levels:**

- **High**: 80% of tasks require deep analysis (debugging, security, architecture)
- **Medium**: Balanced - handles most scenarios effectively
- **Low**: 80% of tasks are straightforward (docs, writing, quick prototypes)

## Extending Routing Rules

### Project-Specific Rules

Create `.claude/config.json` in your project:

```json
{
  "routing": {
    "keywords": {
      "stripe": ["api-designer", "security-auditor"],
      "payment": ["api-designer", "security-auditor"],
      "analytics": ["metrics-collector"]
    },
    "filePatterns": {
      "*.graphql": ["api-designer"],
      "*/stripe/*": ["api-designer", "security-auditor"]
    }
  }
}
```

### Custom Workflows

Define project-specific workflows:

```json
{
  "workflows": {
    "payment-feature": {
      "agents": [
        "api-designer",
        "security-auditor",
        "test-writer-fixer",
        "code-reviewer"
      ],
      "sequential": true
    }
  }
}
```

Invoke with:

```bash
/popkit:workflow payment-feature
```

## Debugging Routing Decisions

### View Routing Logic

```bash
/popkit:debug routing
```

**Output:**

```
User Request: "Fix security bug in auth"

Keyword Matches:
  - "security" → security-auditor
  - "bug" → bug-whisperer, test-writer-fixer

File Context: src/auth/login.ts
  - *.ts → (no specific match)

Error Pattern: None detected

Selected Agents:
  Primary: security-auditor (security keyword + tier 1)
  Supporting: bug-whisperer (bug keyword + tier 1)
  Supporting: test-writer-fixer (bug keyword + tier 1)

Activation Order:
  1. security-auditor (model: opus, effort: high)
  2. bug-whisperer (model: opus, effort: high)
  3. test-writer-fixer (model: sonnet, effort: medium)
```

### Routing Metrics

Track routing effectiveness:

```bash
/popkit:metrics routing
```

**Example Output:**

```
Routing Metrics (Last 30 days):

Keyword Routing:
  - Total activations: 1,247
  - Most common: "review" (312), "bug" (198), "test" (145)
  - Accuracy: 94% (user confirmed correct agent)

File Pattern Routing:
  - Total activations: 892
  - Most common: *.ts (402), *.md (156), *.tsx (98)
  - Accuracy: 97%

Error Pattern Routing:
  - Total activations: 423
  - Most common: TypeError (189), SyntaxError (87)
  - Accuracy: 92%

Agent Performance:
  - code-reviewer: 412 activations, 95% satisfaction
  - bug-whisperer: 287 activations, 89% satisfaction
  - test-writer-fixer: 234 activations, 91% satisfaction
```

## Coverage Analysis

### Current Coverage

Run coverage analysis:

```bash
/popkit:assess routing
```

**Results:**

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Tier 1 Keyword Coverage | 95% | 100% | ✓ |
| File Pattern Coverage | 80% | 85% | ✓ |
| Error Pattern Coverage | 80% | 88% | ✓ |
| Agent Overlap | < 20% | 12% | ✓ |

**Coverage Formulas:**

```
Keyword Coverage = (agents_with_keywords / total_tier1_agents) * 100
File Coverage = (matched_common_patterns / total_common_patterns) * 100
Error Coverage = (matched_common_errors / total_common_errors) * 100
```

### Gap Analysis

Identify missing coverage:

```bash
/popkit:assess routing --gaps
```

**Example Output:**

```
Routing Gaps Detected:

Missing File Patterns:
  - *.rs (Rust files) → Suggested: refactoring-expert
  - *.go (Go files) → Suggested: api-designer
  - *.proto (Protocol buffers) → Suggested: api-designer

Missing Error Patterns:
  - AssertionError → Suggested: test-writer-fixer
  - ValidationError → Suggested: api-designer

Tier 2 Agents Without Triggers:
  - meta-agent (manual invocation only)
  - backup-coordinator (keyword: "backup" exists)
```

## Best Practices

### 1. Keyword Specificity

**Bad:**

```json
{
  "keywords": {
    "code": ["code-reviewer"],
    "help": ["meta-agent"]
  }
}
```

Too generic - matches everything.

**Good:**

```json
{
  "keywords": {
    "review": ["code-reviewer"],
    "pr": ["code-reviewer"],
    "pull-request": ["code-reviewer"]
  }
}
```

Specific, actionable keywords.

### 2. Pattern Granularity

**Bad:**

```json
{
  "filePatterns": {
    "*.ts": ["code-reviewer"]
  }
}
```

Too broad - matches all TypeScript files.

**Good:**

```json
{
  "filePatterns": {
    "*.test.ts": ["test-writer-fixer"],
    "*.spec.ts": ["test-writer-fixer"],
    "*.config.ts": ["code-reviewer"]
  }
}
```

Specific patterns for specialized handling.

### 3. Avoid Circular Routing

**Bad:**

```json
{
  "workflows": {
    "debug": {
      "agents": ["bug-whisperer", "code-reviewer"],
      "sequential": true
    },
    "review": {
      "agents": ["code-reviewer", "bug-whisperer"],
      "sequential": true
    }
  }
}
```

Agents call each other indefinitely.

**Good:**

```json
{
  "workflows": {
    "debug": {
      "agents": ["bug-whisperer", "log-analyzer"],
      "sequential": true
    }
  }
}
```

Clear, one-directional flow.

### 4. Leverage Multi-Agent Collaboration

When tasks span domains, combine agents:

```
Request: "Add accessibility to payment form"

Selected Agents:
  - accessibility-guardian (a11y compliance)
  - api-designer (payment API integration)
  - rapid-prototyper (UI implementation)

Collaboration:
  1. accessibility-guardian defines requirements
  2. rapid-prototyper implements UI with a11y
  3. api-designer integrates payment logic
  4. code-reviewer validates final result
```

## References

- **Configuration**: `packages/plugin/agents/config.json`
- **Agent Definitions**: `packages/plugin/agents/tier-*/*/AGENT.md`
- **Routing Standards**: `packages/plugin/skills/pop-assessment-anthropic/standards/agent-routing.md`
- **Power Mode Coordination**: `packages/plugin/power-mode/coordinator.py`
- **Hook Implementation**: `packages/plugin/hooks/utils/agent_router.py`

## Version History

- **v1.1.0** (2025-01-15): Added plan mode configuration, model assignment
- **v1.0.0** (2024-12-16): Initial routing strategy documentation
