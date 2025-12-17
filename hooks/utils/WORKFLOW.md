# PopKit Workflow Orchestration System

A file-based state machine for programmatic skill orchestration in Claude Code.

## Overview

The workflow system enables:
- **Multi-step workflows** defined in skill YAML frontmatter
- **User decision branching** via AskUserQuestion integration
- **Cross-session persistence** (survives Claude Code restarts)
- **Event-based coordination** for async operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PopKit Plugin                               │
├─────────────────────────────────────────────────────────────────┤
│  Skills with workflow: YAML frontmatter                         │
│      ↓                                                          │
│  workflow_parser.py  →  Parses workflow definitions             │
│      ↓                                                          │
│  workflow_engine.py  →  File-based state machine                │
│      ↓                                                          │
│  response_router.py  →  Routes AskUserQuestion responses        │
│      ↓                                                          │
│  post-tool-use.py    →  Hook integration (routes user answers)  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
.claude/popkit/workflows/
├── active.json                  # Currently active workflow
├── {workflow_id}.json          # Workflow state + definition
├── {workflow_id}.events/       # Pending events directory
│   └── {event_id}.json         # Stored event data
└── {workflow_id}.log           # Audit log (newline-delimited JSON)
```

## State File Format

### `active.json`
```json
{
  "workflow_id": "feature-dev-abc123",
  "set_at": "2025-12-12T10:30:00.000Z"
}
```

### `{workflow_id}.json`
```json
{
  "workflow_id": "feature-dev-abc123",
  "workflow_type": "feature-development",
  "workflow_name": "Feature Development",
  "current_step": "decision",
  "completed_steps": ["start", "exploration"],
  "pending_events": ["decision-approach"],
  "context": {
    "issue_number": 42,
    "exploration_result": {...}
  },
  "step_results": {
    "start": {"result": "success"},
    "exploration": {"files_found": 15}
  },
  "status": "waiting",
  "error_message": null,
  "created_at": "2025-12-12T10:30:00.000Z",
  "updated_at": "2025-12-12T10:35:00.000Z",
  "github_issue": 42,
  "definition": {
    "id": "feature-development",
    "name": "Feature Development",
    "version": 1,
    "steps": [...]
  }
}
```

## Workflow Definition Schema

### In Skill YAML Frontmatter

```yaml
---
name: pop-feature-dev
description: 7-phase feature development workflow

workflow:
  id: feature-development
  name: Feature Development
  version: 1
  description: Guided feature implementation
  steps:
    - id: discovery
      description: Understand requirements
      type: skill
      skill: pop-research-analyze
      next: exploration

    - id: exploration
      description: Explore codebase patterns
      type: agent
      agent: code-explorer
      next: approach_decision

    - id: approach_decision
      description: Choose implementation approach
      type: user_decision
      question: "Which approach should we use?"
      header: "Approach"
      options:
        - id: minimal
          label: "Minimal"
          description: "Quick basic implementation"
          next: implement_minimal
        - id: comprehensive
          label: "Comprehensive"
          description: "Full implementation with tests"
          next: implement_comprehensive
      next_map:
        minimal: implement_minimal
        comprehensive: implement_comprehensive

    - id: implement_minimal
      description: Basic implementation
      type: skill
      skill: pop-quick-implement
      next: review

    - id: implement_comprehensive
      description: Full implementation
      type: spawn_agents
      agents:
        - type: code-reviewer
          task: "Review as implemented"
        - type: test-writer-fixer
          task: "Write tests for new code"
      wait_for: all
      next: review

    - id: review
      description: Final review
      type: agent
      agent: code-reviewer
      next: complete

    - id: complete
      description: Workflow finished
      type: terminal
---
```

### Step Types

| Type | Purpose | Required Fields |
|------|---------|-----------------|
| `skill` | Invoke a PopKit skill | `skill`, `next` |
| `agent` | Use a specific agent | `agent`, `next` |
| `user_decision` | AskUserQuestion with routing | `question`, `header`, `options`, `next_map` |
| `spawn_agents` | Parallel agent execution | `agents`, `wait_for`, `next` |
| `terminal` | End workflow | (none) |

## API Reference

### workflow_engine.py

```python
from hooks.utils.workflow_engine import FileWorkflowEngine

# Create new workflow
engine = FileWorkflowEngine.create_workflow(
    workflow_id="feature-dev-abc123",
    workflow_def=workflow_definition,
    initial_context={"issue_number": 42},
    github_issue=42
)

# Load existing workflow
engine = FileWorkflowEngine.load_workflow("feature-dev-abc123")

# Get active workflow
engine = FileWorkflowEngine.get_active_workflow()

# Get current step
step = engine.get_current_step()

# Advance to next step
next_step = engine.advance_step({"result": "success"})

# Wait for external event (user decision)
engine.wait_for_event("decision-approach")

# Notify event occurred
engine.notify_event("decision-approach", {"answer": "comprehensive"})

# Get workflow state
state = engine.get_state()
summary = engine.get_summary()
context = engine.get_context()

# Update context
engine.update_context({"new_key": "new_value"})

# Error handling
engine.set_error("Something went wrong")
engine.cancel()

# Cleanup
engine.delete()
```

### workflow_parser.py

```python
from hooks.utils.workflow_parser import (
    parse_skill_workflow,
    validate_workflow_definition,
    WorkflowRegistry
)

# Parse workflow from skill file
workflow_def = parse_skill_workflow(Path("skills/pop-feature-dev/SKILL.md"))

# Validate workflow definition
result = validate_workflow_definition(workflow_def)
if not result.valid:
    print(f"Errors: {result.errors}")

# Load registry of all workflows
registry = WorkflowRegistry.load()
workflow = registry.get_by_skill("pop-feature-dev")
workflow = registry.get_by_id("feature-development")

# List all workflows
for entry in registry.list_workflows():
    print(f"{entry.skill_name}: {entry.workflow_id}")
```

### response_router.py

```python
from hooks.utils.response_router import (
    route_user_response,
    get_workflow_status,
    get_pending_decision,
    should_route_response,
    format_hook_output
)

# Route AskUserQuestion response
result = route_user_response({"answers": {"Approach": "Comprehensive"}})
if result.routed:
    print(f"Next step: {result.next_step}")
    print(f"Skill to invoke: {result.skill}")

# Get current workflow status
status = get_workflow_status()

# Get pending decision details
decision = get_pending_decision()
if decision:
    print(f"Waiting for: {decision['question']}")

# Format for hook output
hook_output = format_hook_output(result)
```

## Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Workflow created but not started |
| `running` | Actively executing a step |
| `waiting` | Waiting for external event (user decision) |
| `complete` | Successfully finished |
| `error` | Failed with error |
| `cancelled` | Manually cancelled |

## Integration with Hooks

### post-tool-use.py Integration

```python
# In hooks/post-tool-use.py
from utils.response_router import route_user_response, should_route_response

def handle_tool_output(tool_name: str, tool_output: dict):
    # ... existing code ...

    # Route AskUserQuestion responses to workflows
    if should_route_response(tool_name):
        result = route_user_response(tool_output)
        if result.routed:
            # Include workflow guidance in hook output
            return {
                "stderr": result.message,
                "context": result.context
            }
```

## Authoring Guide

This section explains how to add workflow definitions to PopKit skills.

### Quick Start

Add a `workflow:` section to your skill's YAML frontmatter:

```yaml
---
name: my-skill
description: Description of what this skill does

workflow:
  id: my-workflow
  name: My Workflow
  version: 1
  description: Brief workflow description
  steps:
    - id: start
      description: First step
      type: agent
      agent: code-explorer
      next: decision

    - id: decision
      description: User chooses path
      type: user_decision
      question: "Which path?"
      header: "Path"
      options:
        - id: path_a
          label: "Path A"
          description: "First option"
          next: complete
        - id: path_b
          label: "Path B"
          description: "Second option"
          next: complete
      next_map:
        path_a: complete
        path_b: complete

    - id: complete
      description: Done
      type: terminal
---
```

### Step Type Reference

#### `skill` - Invoke Another Skill

```yaml
- id: gather_context
  description: Run research skill
  type: skill
  skill: pop-knowledge-lookup
  next: next_step
```

#### `agent` - Use a Specific Agent

```yaml
- id: explore
  description: Explore codebase
  type: agent
  agent: code-explorer
  next: next_step
```

Available agents: `code-explorer`, `code-architect`, `code-reviewer`, `bug-whisperer`, `test-writer-fixer`, `security-auditor`, `performance-optimizer`, etc.

#### `user_decision` - Interactive Choice

```yaml
- id: approach_decision
  description: Choose approach
  type: user_decision
  question: "Which approach should we use?"
  header: "Approach"        # Max 12 chars
  options:
    - id: minimal
      label: "Minimal"
      description: "Quick implementation"
      next: minimal_path
    - id: full
      label: "Full"
      description: "Complete with tests"
      next: full_path
  next_map:
    minimal: minimal_path
    full: full_path
```

**Rules:**
- `header` must be 12 characters or less
- 2-4 options required
- Each option needs `id`, `label`, `description`, `next`
- `next_map` must match all option `id` values

#### `spawn_agents` - Parallel Execution

```yaml
- id: parallel_work
  description: Run agents in parallel
  type: spawn_agents
  agents:
    - type: code-reviewer
      task: "Review the implementation"
    - type: test-writer-fixer
      task: "Write tests for new code"
  wait_for: all              # or "any"
  next: next_step
```

#### `terminal` - End Workflow

```yaml
- id: complete
  description: Workflow finished
  type: terminal
```

### Validation Rules

The JSON Schema (`workflow_schema.json`) enforces:

1. **Workflow level:**
   - `id` required, lowercase with hyphens (`^[a-z][a-z0-9-]*$`)
   - `steps` required, at least 1 step

2. **Step level:**
   - `id` required, lowercase with hyphens/underscores
   - `type` required, one of: `skill`, `agent`, `user_decision`, `spawn_agents`, `terminal`

3. **Type-specific:**
   - `skill` type requires `skill` field
   - `agent` type requires `agent` field
   - `user_decision` type requires `question`, `options`
   - `spawn_agents` type requires `agents` array

### Best Practices

1. **Start with exploration** - First step should gather context
2. **Use decisions for branching** - Let users choose their path
3. **End with terminal** - Every path must reach a terminal step
4. **Keep headers short** - 12 char limit for AskUserQuestion
5. **Descriptive step IDs** - Use `_decision` suffix for decision steps
6. **Reachability** - Ensure all steps are reachable from start

### Example: Complete Workflow

See these skills for reference implementations:

| Skill | Workflow | Features |
|-------|----------|----------|
| `pop-brainstorming` | `brainstorming` | GitHub check, decisions, skill chaining |
| `pop-analyze-project` | `analyze-project` | Depth selection, spawn_agents, output formats |
| `pop-systematic-debugging` | `systematic-debugging` | 4-phase process, retry loops |
| `pop-security-scan` | `security-scan` | Severity thresholds, fix/rollback paths |
| `pop-executing-plans` | `executing-plans` | Batch execution, checkpoints, next actions |

### Testing Workflows

Use the workflow parser to validate:

```python
from hooks.utils.workflow_parser import parse_skill_workflow, validate_workflow_definition

# Parse from skill file
workflow = parse_skill_workflow(Path("skills/my-skill/SKILL.md"))

# Validate
result = validate_workflow_definition(workflow)
if not result.valid:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `next` on non-terminal steps | Add `next: step_id` |
| `next_map` doesn't match options | Ensure all option IDs are in next_map |
| Header too long | Keep under 12 characters |
| Unreachable steps | Check all `next` references |
| Invalid step type | Use one of: skill, agent, user_decision, spawn_agents, terminal |

## Related Issues

- #206 - File-Based Workflow Engine (this implementation)
- #207 - Skill Workflow Definitions
- #208 - Response Router Integration
- #205 - Programmatic Skill Orchestration Research
- #115 - Intelligent Orchestration Epic
