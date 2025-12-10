---
name: power-mode
description: "Multi-agent orchestration system using Redis pub/sub or file-based fallback for parallel agent collaboration. Enables shared context, periodic check-ins, sync barriers between phases, and coordinator oversight. Use for complex tasks benefiting from parallel execution (epics, large refactors, multi-phase features). Do NOT use for simple tasks or sequential workflows - the coordination overhead isn't justified."
---

# Pop Power Mode

Multi-agent orchestration using Redis pub/sub for parallel collaboration with shared context.

**Core principle:** Agents work in parallel, check in periodically, share discoveries, and coordinate through a mesh network.

## Free vs Premium Tiers

| Feature | Free Tier | Pro Tier ($9/mo) |
|---------|-----------|------------------|
| File-based coordination | ✅ 2-3 agents | ✅ Included |
| Hosted Redis | ❌ | ✅ 6+ agents |
| Persistent sessions | ❌ | ✅ |
| Advanced metrics | Basic | Full |

### Free Tier: File-Based Fallback

Free tier users automatically get file-based Power Mode:

```markdown
## File-Based Power Mode (Free Tier)

Power Mode is working in file-based mode (Redis not available or not Pro tier).

### What You Get
- ✅ 2-3 agents working sequentially
- ✅ Shared context via JSON files
- ✅ Basic coordination

### Limitations
- Max 2-3 agents (sequential coordination)
- No real-time pub/sub
- Sessions not persisted

### Files Used
- `.claude/popkit/power-state.json` - Session state
- `.claude/popkit/insights.json` - Shared discoveries

This is great for learning Power Mode concepts!
Run `/popkit:upgrade` to unlock hosted Redis with 6+ parallel agents.
```

### Pro Tier: Full Redis Mode

Pro users get hosted Redis for full parallel coordination:
- 6+ agents working in parallel
- Real-time pub/sub messaging
- Persistent session state
- Advanced metrics dashboard

## Overview

**Inspired by:**
- ZigBee/Z-Wave mesh networks (failover, redundancy)
- DeepMind's objective-driven agents (constrained exploration)
- Node-RED (flow-based coordination)

**When to use:**
- Complex tasks requiring multiple specialized agents
- Tasks that benefit from parallel exploration
- When agents need to share discoveries in real-time
- Large implementations with distinct subtasks

**When NOT to use:**
- Simple, single-agent tasks
- Tasks requiring tight sequential dependency
- When Redis is unavailable
- Quick fixes or small changes

## Prerequisites

1. **Redis running** (local or remote)
   ```bash
   # Start Redis locally
   docker run -d -p 6379:6379 redis:alpine
   # Or: redis-server
   ```

2. **Python redis package**
   ```bash
   pip install redis
   ```

## Activation

### Method 1: Command
```
/popkit:power-mode "Build user authentication with tests and docs"
```

### Method 2: Environment Variable
```bash
export POP_POWER_MODE=1
```

### Method 3: Manual
```bash
touch ~/.claude/power-mode-enabled
```

## How It Works

### 1. Define Objective

Power mode requires a clear objective with:
- **Description**: What we're building
- **Success criteria**: How we know we're done
- **Phases**: Ordered stages of work
- **Boundaries**: What agents can't do

```python
Objective:
  description: "Build user authentication"
  success_criteria:
    - "Login endpoint works"
    - "Tests pass"
    - "Documentation updated"
  phases: [explore, design, implement, test, document]
  boundaries:
    - file_patterns: ["src/auth/**", "tests/auth/**"]
    - restricted_tools: []
```

### 2. Coordinator Starts

The coordinator:
- Creates Redis channels
- Stores objective
- Monitors agent health
- Routes insights
- Manages sync barriers

### 3. Agents Register & Work

Each agent:
- Registers with coordinator
- Gets assigned a subtask
- Works independently
- Checks in every 5 tool calls

### 4. Check-In Protocol

Every 5 tool calls, agents:

**PUSH (outgoing):**
- Progress update
- Files touched
- Discoveries made (insights)

**PULL (incoming):**
- Relevant insights from others
- Pattern recommendations
- Coordinator messages

### 5. Sync Barriers

Between phases:
- Coordinator creates barrier
- Agents acknowledge when ready
- All wait until complete
- Next phase begins

### 6. Completion

When objective met:
- Coordinator aggregates results
- Patterns saved for future
- Session transcript stored

## Redis Channels

| Channel | Purpose |
|---------|---------|
| `pop:broadcast` | Coordinator → All agents |
| `pop:agent:{id}` | Direct messages to agent |
| `pop:heartbeat` | Agent health check-ins |
| `pop:results` | Completed work |
| `pop:insights` | Shared discoveries |
| `pop:human` | Human decision requests |

## Guardrails

**Automatic protections:**
- Protected paths (.env, secrets, .git)
- Human-required actions (deploy, delete prod data)
- Drift detection (working outside scope)
- Unconventional approach detection

**Human escalation triggers:**
- Modifying security configuration
- Pushing to main/production
- Accessing credentials
- Bulk file deletions
- Actions that might be "cheating"

## Example Workflow

```
User: /popkit:power-mode "Build a REST API with user authentication"

[Coordinator starts, creates objective]

Phase 1: EXPLORE (parallel)
├── code-explorer → Analyzes existing codebase
├── researcher → Researches auth best practices
└── architect → Reviews project structure

[Insights shared via Redis]
explorer → "Found existing User model at src/models"
researcher → "JWT recommended for stateless auth"
architect → "Routes pattern: src/routes/{feature}/"

[SYNC BARRIER - wait for all]

Phase 2: DESIGN (coordinator routes insights)
└── code-architect → Designs auth system
    (receives all Phase 1 insights automatically)

[SYNC BARRIER]

Phase 3: IMPLEMENT (parallel with check-ins)
├── rapid-prototyper → Implements endpoints
│   ├── Check-in 1: "Created login route"
│   ├── Check-in 2: "Added JWT generation"
│   └── Check-in 3: "Need: User model location"
│       ← Receives: "src/models/user.ts" from explorer
│
├── test-writer → Writes tests in parallel
│   └── Check-in: "Testing login endpoint"
│
└── docs-maintainer → Updates documentation
    └── Check-in: "Documenting API endpoints"

[SYNC BARRIER]

Phase 4: REVIEW
└── code-reviewer → Reviews all changes
    (receives aggregated results from all agents)

[Complete - results aggregated, patterns saved]
```

## Configuration

Edit `power-mode/config.json`:

```json
{
  "intervals": {
    "checkin_every_n_tools": 5,
    "heartbeat_seconds": 15
  },
  "limits": {
    "max_parallel_agents": 6,
    "max_runtime_minutes": 30
  },
  "guardrails": {
    "protected_paths": [".env*", "**/secrets/**"],
    "drift_detection": { "enabled": true }
  }
}
```

## Deactivation

```bash
# Remove enable file
rm ~/.claude/power-mode-enabled

# Or unset environment
unset POP_POWER_MODE

# Or use command
/popkit:power-mode-stop
```

## Troubleshooting

**Redis connection failed:**
- Check container running: `docker ps --filter name=popkit-redis`
- Test connection: `docker exec popkit-redis redis-cli ping`
- Or Python: `python -c "import redis; print(redis.Redis(port=16379).ping())"`

**Agents not communicating:**
- Verify power mode enabled
- Check Redis channels: `docker exec popkit-redis redis-cli subscribe pop:broadcast`

**Check-ins not happening:**
- Verify checkin-hook.py is executable
- Check hooks.json includes power-mode hook

**Drift alerts:**
- Agent working outside scope boundaries
- Update boundaries or reassign task

## Integration

**Works with:**
- All popkit agents (they gain check-in capability)
- Existing skills (run within power mode context)
- Output styles (check-ins use power-mode-checkin format)

**Coordinator agent:**
- `power-coordinator` - Can be invoked as coordinator

**Related skills:**
- `pop-subagent-dev` - Single-session alternative
- `pop-executing-plans` - Parallel session alternative
