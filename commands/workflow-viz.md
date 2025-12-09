---
description: "[workflow-name] [--validate, --metrics, --ascii]"
---

# /popkit:workflow-viz

Visualize workflow chains from `agents/config.json` with ASCII diagrams, validation status, and performance metrics.

## Usage

```bash
/popkit:workflow-viz                    # List all workflows
/popkit:workflow-viz <workflow-id>      # Visualize specific workflow
/popkit:workflow-viz <workflow-id> status # Show execution status
/popkit:workflow-viz <workflow-id> metrics # Show performance metrics
/popkit:workflow-viz validate           # Validate all chains
```

## Architecture Integration

| Component | Role |
|-----------|------|
| **Skill** | `pop-chain-management` - Programmatic chain operations |
| **Hook** | `chain-validator.py` - Validates chains before execution |
| **Hook** | `chain-metrics.py` - Tracks execution metrics |
| **Config** | `agents/config.json` - Workflow definitions |
| **Metrics** | `~/.claude/chain-metrics.json` - Execution history |

## Instructions

You are the chain visualization engine. Parse ARGUMENTS to determine the subcommand.

### Step 0: Parse Arguments

- No args → `list`
- `<workflow-id>` → visualize that workflow
- `<workflow-id> status` → show execution status
- `<workflow-id> metrics` → show performance metrics
- `validate` → validate all chains

---

## Subcommand: List (default)

**Trigger:** No arguments provided

**Steps:**
1. Read `agents/config.json`
2. Extract workflow definitions
3. Display summary table

**Output Format:**
```
## Available Workflows

| Workflow | Phases | Agents | Mode |
|----------|--------|--------|------|
| feature-dev | 7 | 3 | phased |
| debug | - | 2 | sequential |
| security-audit | - | 1 | parallel |

Use `/popkit:workflow-viz <workflow-id>` to visualize a specific workflow.
```

---

## Subcommand: Visualize Workflow

**Trigger:** `<workflow-id>` provided

**Steps:**
1. Read workflow from config.json
2. Generate ASCII visualization
3. Show agent assignments

**Output Format (Phased Workflow):**
```
## Workflow: feature-dev

### 7-Phase Feature Development

```
  [Discovery]
       |
       v
  [Exploration] -----> code-explorer
       |
       v
  [Questions]
       |
       v
  [Architecture] ----> code-architect
       |
       v
  [Implementation]
       |
       v
  [Review] ----------> code-reviewer
       |
       v
  [Summary]
```

**Phases:** 7 | **Agents:** 3 | **Success Rate:** 87%
```

**Output Format (Sequential Workflow):**
```
## Workflow: debug

### Debug Workflow (Sequential)

```
  [bug-whisperer]
       |
       v
  [log-analyzer]
```

**Agents:** 2 | **Mode:** sequential
```

**Output Format (Parallel Workflow):**
```
## Workflow: security-audit

### Security Audit (Parallel)

```
  +------------------+
  | parallel exec    |
  +------------------+
  | security-auditor |
  +------------------+
```

**Agents:** 1 | **Mode:** parallel
```

---

## Subcommand: Status

**Trigger:** `<workflow-id> status`

**Steps:**
1. Read `~/.claude/chain-metrics.json`
2. Filter runs for this workflow
3. Display recent execution history

**Output Format:**
```
## Workflow: feature-dev - Recent Runs

### Run #1 (abc123) - 2h ago
**Status:** COMPLETED
**Duration:** 12m 30s

| Step | Status | Duration | Details |
|------|--------|----------|---------|
| Discovery | Done | 0:45 | - |
| Exploration | Done | 2:15 | confidence: 85 |
| Questions | Done | 1:30 | - |
| Architecture | Done | 3:20 | - |
| Implementation | Done | 4:10 | - |
| Review | Done | 1:45 | - |
| Summary | Done | 0:35 | - |

### Run #2 (def456) - Yesterday
**Status:** COMPLETED
**Duration:** 15m 10s
```

---

## Subcommand: Metrics

**Trigger:** `<workflow-id> metrics`

**Steps:**
1. Read chain metrics history
2. Calculate aggregate statistics
3. Identify bottlenecks

**Output Format:**
```
## Workflow: feature-dev - Metrics

### Overall Stats
| Metric | Value |
|--------|-------|
| Total runs | 15 |
| Success rate | 87% |
| Avg duration | 12m 30s |

### Step Performance

| Step | Avg Time | Success | Bottleneck |
|------|----------|---------|------------|
| Discovery | 0:45 | 100% | |
| Exploration | 2:15 | 93% | |
| Questions | 1:30 | 100% | |
| Architecture | 3:20 | 87% | ! |
| Implementation | 4:10 | 80% | !! |
| Review | 1:45 | 93% | |
| Summary | 0:35 | 100% | |

### Top Bottlenecks
1. **Implementation** (4:10 avg) - Consider breaking into smaller tasks
2. **Architecture** (3:20 avg) - May need additional context
3. **Exploration** (2:15 avg) - Normal for large codebases
```

---

## Subcommand: Validate

**Trigger:** `validate`

**Steps:**
1. Run `chain-validator.py` hook logic
2. Check all workflow definitions
3. Verify agent references exist
4. Report findings

**Output Format:**
```
## Chain Validation Results

### feature-dev
**Status:** VALID
- Phases: 7
- Agents: 3 (all found)
- Warnings: 0

### debug
**Status:** VALID
- Agents: 2 (all found)
- Warnings: 0

### security-audit
**Status:** VALID
- Agents: 1 (all found)
- Warnings: 0

---
**Total:** 3 workflows | 0 errors | 0 warnings
```

**With Warnings:**
```
### feature-dev
**Status:** VALID (with warnings)
- Warnings:
  - Phase 'Architecture': Agent 'code-architect-v2' not found in tier definitions
```

---

## Workflow Configuration Schema

Workflows in `agents/config.json`:

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
    },
    "debug": {
      "agents": ["bug-whisperer", "log-analyzer"],
      "sequential": true
    }
  }
}
```

---

## Related Components

- **Skill:** `pop-chain-management` for programmatic access
- **Hook:** `chain-validator.py` validates before execution
- **Hook:** `chain-metrics.py` tracks execution data
- **Command:** `/popkit:feature-dev` uses the feature-dev workflow
