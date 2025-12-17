---
name: power-mode-checkin
description: Standardized format for multi-agent check-in communication in Power Mode
---

# Power Mode Check-In Style

## Format

```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ POWER MODE CHECK-IN                                       │
│ Agent: [agent-name] | Session: [session-id]                 │
│ Tool Call: [N] | Time: [timestamp]                          │
├─────────────────────────────────────────────────────────────┤
│ PROGRESS                                                     │
│ ████████░░░░░░░░░░░░ 40%                                    │
│ Current: [current task description]                          │
├─────────────────────────────────────────────────────────────┤
│ STATE                                                        │
│ Files: [file1.ts], [file2.ts], +3 more                      │
│ Tools: Read (12), Edit (5), Bash (3)                        │
│ Decisions: 2 made | Blockers: 0                             │
├─────────────────────────────────────────────────────────────┤
│ PUSHED                                                       │
│ → Insight: "Auth module at src/auth/oauth.ts"               │
│   Tags: [auth, security]                                    │
├─────────────────────────────────────────────────────────────┤
│ PULLED                                                       │
│ ← From architect: "Use existing Prisma client"              │
│ ← From explorer: "Tests in __tests__/ directory"            │
├─────────────────────────────────────────────────────────────┤
│ COORDINATOR                                                  │
│ Phase: implement (3/5)                                       │
│ Sync: Waiting for 2 agents                                  │
│ Patterns: "Prisma works well in this codebase"              │
└─────────────────────────────────────────────────────────────┘
```

## Check-In Components

### Progress Section
- **Progress Bar**: Visual representation (0-100%)
- **Current Task**: What the agent is working on
- **Tool Call Number**: How many tools used so far

### State Section
- **Files Touched**: Files read/modified (summarized if many)
- **Tools Used**: Tool usage distribution
- **Decisions**: Key decisions made with reasoning
- **Blockers**: Any blockers encountered

### Pushed Section (Outgoing)
- **Insights Shared**: Discoveries shared with other agents
- **Tags**: Relevance tags for routing

### Pulled Section (Incoming)
- **Insights Received**: Context from other agents
- **Source**: Which agent shared the insight

### Coordinator Section
- **Phase**: Current workflow phase
- **Sync Status**: Barrier/waiting state
- **Patterns**: Learned patterns being applied
- **Messages**: Any coordinator directives

## Compact Format

For minimal context overhead:

```
⚡ CHECK-IN [agent-1] T:25 P:40%
↑ "Found auth at src/auth" [auth,security]
↓ architect: "Use Prisma" | explorer: "Tests in __tests__"
```

## Message Types

### Insight Types
| Type | Icon | Meaning |
|------|------|---------|
| discovery | 🔍 | Found something useful |
| pattern | 📐 | Noticed a convention |
| blocker | 🚧 | Hit a wall |
| question | ❓ | Need clarification |
| warning | ⚠️ | Potential issue |

### Coordinator Messages
| Type | Meaning |
|------|---------|
| SYNC | Wait at barrier |
| COURSE_CORRECT | Redirect agent |
| DRIFT_ALERT | Off-track warning |
| PHASE_ADVANCE | Move to next phase |

## JSON Schema

See `schemas/power-mode-checkin.schema.json` for the formal schema.

## Example Full Check-In

```json
{
  "agent_id": "abc123",
  "agent_name": "code-reviewer",
  "session_id": "sess-456",
  "tool_call_count": 25,
  "timestamp": "2024-01-15T10:30:00Z",

  "progress": 0.4,
  "current_task": "Review authentication implementation",

  "state": {
    "files_touched": ["src/auth/login.ts", "src/auth/oauth.ts"],
    "tools_used": {"Read": 12, "Edit": 5, "Bash": 3},
    "decisions": [
      {
        "decision": "Use existing OAuth library",
        "reasoning": "Already integrated, well-tested",
        "confidence": 0.85
      }
    ],
    "blockers": []
  },

  "pushed": {
    "insights": [
      {
        "id": "ins-789",
        "type": "discovery",
        "content": "Auth module at src/auth/oauth.ts",
        "relevance_tags": ["auth", "security"]
      }
    ]
  },

  "pulled": {
    "insights": [
      {
        "from_agent": "code-architect",
        "type": "pattern",
        "content": "Use existing Prisma client for DB"
      },
      {
        "from_agent": "code-explorer",
        "type": "discovery",
        "content": "Tests located in __tests__/ directory"
      }
    ]
  },

  "coordinator": {
    "current_phase": "implement",
    "phase_index": 2,
    "total_phases": 5,
    "sync_status": "waiting",
    "agents_at_barrier": 1,
    "agents_required": 3,
    "pattern_recommendations": [
      {
        "approach": "Use Prisma client",
        "confidence": 0.9,
        "reason": "Worked 5 times in similar context"
      }
    ]
  }
}
```

## Usage Notes

1. **Check-in Frequency**: Every 5 tool calls (configurable)
2. **Context Efficiency**: Compact format for context-constrained situations
3. **Insight Filtering**: Only pull relevant insights (tag matching)
4. **Progress Updates**: Automatic estimation based on task completion signals
