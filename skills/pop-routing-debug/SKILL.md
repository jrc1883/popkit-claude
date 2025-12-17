---
name: routing-debug
description: "Use when agent routing seems wrong, unexpected agents are selected, or you need to understand why a specific agent was chosen - provides detailed routing analysis and debugging. Shows keyword matches, confidence scores, and competing agents. Do NOT use for general agent questions or when routing is working correctly - just proceed with the selected agent."
---

# Routing Debugger

## Overview

Debug and analyze agent routing decisions. Shows why specific agents are selected, what keywords triggered routing, and how confidence scores are calculated.

**Announce at start:** "I'm using the routing-debug skill to analyze agent routing."

## Capabilities

1. **Explain Routing** - Show why an agent was selected
2. **Test Routing** - Simulate routing for a prompt
3. **List Keywords** - Show all routing keywords and patterns
4. **Trace Path** - Follow routing decision tree
5. **Compare Options** - Show competing agent scores

## Commands

```
/routing-debug "your prompt here"     # Analyze routing for prompt
/routing-debug explain <agent>        # Show agent's keywords
/routing-debug keywords               # List all routing keywords
/routing-debug trace "prompt"         # Detailed routing trace
/routing-debug compare "prompt"       # Compare all agent scores
```

## Output Format

### Routing Analysis

```
Routing Analysis for: "fix the authentication bug"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Selected Agent: bug-whisperer
Confidence: 0.85

Keyword Matches:
  ✓ "fix" → [bug-whisperer, code-reviewer] (+0.3)
  ✓ "bug" → [bug-whisperer] (+0.5)
  ✓ "authentication" → [security-auditor] (+0.2)

File Pattern Matches:
  (none)

Error Pattern Matches:
  (none)

Competing Agents:
  1. bug-whisperer: 0.85 ⭐
  2. security-auditor: 0.45
  3. code-reviewer: 0.30

Decision Reason: "bug" keyword has highest weight for bug-whisperer
```

### Keyword Listing

```
Agent Routing Keywords
━━━━━━━━━━━━━━━━━━━━━━━

bug-whisperer:
  Keywords: bug, fix, debug, error, issue, crash, broken
  File Patterns: *.error.*, *.debug.*
  Error Patterns: TypeError, ReferenceError, SyntaxError

security-auditor:
  Keywords: security, vulnerability, audit, safe, breach
  File Patterns: *auth*, *secret*, *.env
  Error Patterns: SecurityError, AuthenticationError

code-reviewer:
  Keywords: review, quality, standards, refactor, best practices
  File Patterns: *.ts, *.tsx, *.js
  Error Patterns: (none)
...
```

### Routing Trace

```
Routing Trace: "optimize the database query performance"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Keyword Extraction
  Found: ["optimize", "database", "query", "performance"]

Step 2: Keyword Matching
  "optimize" matches:
    - performance-optimizer: weight 0.4
    - query-optimizer: weight 0.3
  "database" matches:
    - query-optimizer: weight 0.5
    - data-integrity: weight 0.2
  "query" matches:
    - query-optimizer: weight 0.6
  "performance" matches:
    - performance-optimizer: weight 0.5
    - query-optimizer: weight 0.3

Step 3: Score Aggregation
  query-optimizer: 0.3 + 0.5 + 0.6 + 0.3 = 1.7 → normalized 0.85
  performance-optimizer: 0.4 + 0.5 = 0.9 → normalized 0.45
  data-integrity: 0.2 → normalized 0.10

Step 4: Final Selection
  Winner: query-optimizer (0.85)
```

## Data Sources

Routing data comes from:
- `agents/config.json` - Keywords, file patterns, error patterns
- Individual agent `.md` files - Tool permissions
- `hooks/agent-orchestrator.py` - Runtime routing logic

## Use Cases

1. **Unexpected routing** - "Why did security-auditor handle my performance question?"
2. **Low confidence** - "Why is the confidence score so low?"
3. **Missing agents** - "Why wasn't my custom agent selected?"
4. **Keyword tuning** - "What keywords should I add to improve routing?"

## Integration

**Called by:**
- Manual debugging via /routing-debug
- Post-task analysis
- Agent configuration tuning

**Reads from:**
- agents/config.json
- hooks/agent-orchestrator.py
- Agent definition files
