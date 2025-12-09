---
name: pop-chain-management
description: "Programmatic access to workflow chain operations including validation, metrics, and visualization. Provides APIs for recording workflow runs, tracking step durations, calculating success rates, and identifying bottlenecks. Use when building custom workflow orchestration, analyzing multi-agent performance, or integrating chain tracking into automation. Do NOT use for simple single-agent tasks or when you just want to run an existing workflow - use the workflow command directly instead."
---

# Chain Management

## Overview

Provides programmatic access to workflow chain operations for agents and skills. Use this skill when you need to validate chains, record metrics, or generate visualizations.

**Core principle:** Understand and track workflow execution for continuous improvement.

**Trigger:** When working with multi-agent workflows or analyzing workflow performance.

## When to Use

Invoke this skill when:
- Starting a multi-phase workflow (record metrics)
- Completing workflow steps (update metrics)
- Debugging workflow issues (check validation)
- Analyzing workflow performance (review metrics)
- Documenting workflow structure (generate visualizations)

## Available Operations

### 1. Validate Workflows

Check if workflow definitions are valid:

```bash
# Run the chain validator
python hooks/chain-validator.py
```

This will output:
- List of all workflows with validation status
- Warnings for missing agents
- Error for circular dependencies (if any)

### 2. View Workflow Definitions

```bash
# Read workflow configurations
python -c "
import json
with open('agents/config.json') as f:
    config = json.load(f)
    print(json.dumps(config.get('workflows', {}), indent=2))
"
```

### 3. Record Workflow Metrics

When starting a workflow:
```bash
# Start a new run
echo '{"operation": "start_run", "workflow_id": "feature-dev", "workflow_name": "7-Phase Feature Development"}' | python hooks/chain-metrics.py
# Returns: {"status": "success", "run_id": "abc123"}
```

When completing a step:
```bash
# Record step completion
echo '{"operation": "record_step", "run_id": "abc123", "step_id": "exploration", "step_name": "Exploration", "agent": "code-explorer", "step_status": "completed", "duration_ms": 135000, "confidence": 85}' | python hooks/chain-metrics.py
```

When completing the workflow:
```bash
# Complete the run
echo '{"operation": "complete_run", "run_id": "abc123", "run_status": "completed"}' | python hooks/chain-metrics.py
```

### 4. Query Metrics

Get workflow statistics:
```bash
# Get stats for a workflow
echo '{"operation": "get_stats", "workflow_id": "feature-dev"}' | python hooks/chain-metrics.py
```

Get recent runs:
```bash
# Get last 10 runs
echo '{"operation": "get_recent", "workflow_id": "feature-dev", "limit": 10}' | python hooks/chain-metrics.py
```

### 5. Generate Visualizations

```bash
# Run validator with visualization
python -c "
import sys
sys.path.insert(0, 'hooks')
from chain_validator import ChainValidator

validator = ChainValidator()
for workflow_id in validator.config.get('workflows', {}).keys():
    print(validator.get_workflow_visualization(workflow_id))
    print()
"
```

## Metrics Data Structure

Metrics are stored in `~/.claude/chain-metrics.json`:

```json
{
  "version": "1.0.0",
  "runs": [
    {
      "run_id": "abc123",
      "workflow_id": "feature-dev",
      "started_at": "2025-01-28T10:00:00Z",
      "ended_at": "2025-01-28T10:12:30Z",
      "status": "completed",
      "steps": [
        {
          "step_id": "exploration",
          "step_name": "Exploration",
          "agent": "code-explorer",
          "status": "completed",
          "duration_ms": 135000,
          "confidence": 85
        }
      ],
      "total_duration_ms": 750000
    }
  ],
  "aggregates": {
    "feature-dev": {
      "total_runs": 15,
      "successful_runs": 13,
      "success_rate": 86.7,
      "avg_duration_ms": 750000,
      "step_metrics": {},
      "bottlenecks": []
    }
  }
}
```

## Integration with Agents

When an agent is part of a workflow:

1. **Before agent execution:**
   - Record step start with `record_step` (status: "running")

2. **After agent completion:**
   - Update step with final status, duration, and confidence
   - If this is the last step, complete the run

3. **On failure:**
   - Record step with status "failed"
   - Complete run with status "failed"

## Example: Full Workflow Tracking

```python
# Pseudo-code for tracking a feature-dev workflow

# 1. Start the workflow
run_id = start_run("feature-dev", "Feature: User Authentication")

# 2. Discovery phase (no agent)
record_step(run_id, "discovery", "Discovery", status="completed", duration_ms=45000)

# 3. Exploration phase (code-explorer agent)
record_step(run_id, "exploration", "Exploration",
            agent="code-explorer", status="completed",
            duration_ms=135000, confidence=85)

# 4. Continue through phases...

# 5. Complete the workflow
complete_run(run_id, "completed")
```

## Analyzing Performance

To identify bottlenecks:

```bash
# Get aggregates and find slow steps
cat ~/.claude/chain-metrics.json | python -c "
import json, sys
data = json.load(sys.stdin)
for wid, agg in data.get('aggregates', {}).items():
    print(f'{wid}:')
    print(f'  Success rate: {agg.get(\"success_rate\", 0)}%')
    print(f'  Avg duration: {agg.get(\"avg_duration_ms\", 0) / 1000:.1f}s')
    if agg.get('bottlenecks'):
        print('  Bottlenecks:')
        for b in agg['bottlenecks']:
            print(f'    - {b[\"step_id\"]}: {b[\"avg_ms\"] / 1000:.1f}s')
"
```

## Related

- `/popkit:workflow-viz` command - User-facing visualization
- `chain-validator.py` hook - Validation logic
- `chain-metrics.py` hook - Metrics tracking
- `agents/config.json` - Workflow definitions
