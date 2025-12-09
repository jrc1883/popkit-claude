# Consensus Mode

Multi-agent consensus protocol for structured decision-making in PopKit Power Mode.

## Overview

Consensus Mode enables multiple AI agents to collaboratively reach decisions through a structured discussion and voting process. Inspired by network consensus protocols (Raft, PBFT, Paxos, Token Ring), it provides:

- **Ordered Turn-Taking**: Token ring ensures each agent speaks in sequence
- **Structured Phases**: Gathering → Proposing → Discussing → Converging → Voting → Committed
- **Multiple Trigger Mechanisms**: User, agent, monitor, checkpoint, conflict, threshold, scheduled
- **Byzantine Fault Tolerance**: Handles agent timeouts, disconnections, and disagreements
- **Integration with Power Mode**: Works alongside existing multi-agent orchestration

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Consensus Mode                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Trigger   │───▶│ Coordinator │───▶│   Session   │         │
│  │   Manager   │    │             │    │             │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Token Ring Manager                      │       │
│  │  ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐             │       │
│  │  │ A │──▶│ B │──▶│ C │──▶│ D │──▶│ A │──▶ ...      │       │
│  │  └───┘   └───┘   └───┘   └───┘   └───┘             │       │
│  │           TOKEN                                      │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Monitor   │    │    Vote     │    │   Agent     │         │
│  │   Agent     │    │  Collector  │    │   Hook      │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start Redis (if not already running)

```bash
# Use the existing Power Mode setup
cd power-mode
python setup-redis.py start
```

### 2. Start the Consensus Coordinator

```bash
python -m consensus.coordinator start
```

### 3. Trigger a Consensus Session

```python
from consensus import ConsensusCoordinator, TriggerType

coordinator = ConsensusCoordinator()
coordinator.connect()
coordinator.start()

# Create a session
session = coordinator.create_session(
    topic="API Design Decision",
    description="Should we use REST or GraphQL for the new service?",
    trigger_type=TriggerType.USER_REQUESTED,
    invited_agents=["code-architect", "api-designer", "performance-optimizer"]
)

# Start discussion
coordinator.start_discussion(session.id)
```

### 4. Using the CLI

```bash
# Trigger a consensus session
python -m consensus.triggers trigger --topic "Architecture Decision" --agents agent-1 agent-2

# Check status
python -m consensus.coordinator status

# Start the monitor
python -m consensus.monitor start
```

## Protocol Details

### Message Types

| Type | Description | Used For |
|------|-------------|----------|
| `CONSENSUS_START` | Session begins | Coordinator → All |
| `TOKEN_GRANT` | Agent receives turn | Coordinator → Agent |
| `TOKEN_RELEASE` | Agent finishes turn | Agent → Coordinator |
| `TOKEN_SKIP` | Agent skips turn | Agent → Coordinator |
| `CONTRIBUTION` | Substantive input | Agent → All |
| `PROPOSAL` | Formal proposal | Agent → All |
| `VOTE_START` | Voting begins | Coordinator → All |
| `VOTE` | Individual vote | Agent → Coordinator |
| `VOTE_RESULT` | Voting outcome | Coordinator → All |
| `CONSENSUS_REACHED` | Agreement achieved | Coordinator → All |

### Phases

```
GATHERING ──▶ PROPOSING ──▶ DISCUSSING ──▶ CONVERGING ──▶ VOTING ──▶ COMMITTED
                                                                      │
                                                                      ▼
                                                                   ABORTED
```

1. **GATHERING**: Agents join the session
2. **PROPOSING**: Initial proposals are made
3. **DISCUSSING**: Token ring discussion (agents take turns)
4. **CONVERGING**: Narrowing down to agreement
5. **VOTING**: Formal voting on proposals
6. **COMMITTED**: Consensus achieved
7. **ABORTED**: Failed to reach consensus

### Token Ring Flow

```
Round 1:
  Agent A (TOKEN) ──▶ contributes ──▶ releases token
  Agent B (TOKEN) ──▶ contributes ──▶ releases token
  Agent C (TOKEN) ──▶ skips      ──▶ releases token
  Agent D (TOKEN) ──▶ contributes ──▶ releases token

Round 2:
  Agent A (TOKEN) ──▶ ...
```

### Vote Types

| Vote | Meaning |
|------|---------|
| `APPROVE` | Fully support |
| `APPROVE_WITH_CONCERNS` | Support with reservations |
| `ABSTAIN` | No opinion |
| `REQUEST_CHANGES` | Would approve if modified |
| `REJECT` | Cannot support |

## Trigger Mechanisms

### 1. User Requested

Explicit user request for consensus:

```python
from consensus import TriggerPublisher, TriggerType

publisher = TriggerPublisher()
publisher.connect()
publisher.request_consensus(
    topic="Database Schema Decision",
    description="Should we use normalized or denormalized schema?",
    agents=["code-architect", "query-optimizer"],
    priority="high"
)
```

### 2. Agent Requested

Agent detects need for group decision:

```python
from consensus.triggers import AgentRequestTrigger

trigger = AgentRequestTrigger()
context = trigger.trigger({
    "agent_id": "code-architect",
    "reason": "Conflicting design patterns detected",
    "confidence": 0.8,
    "topic": "Design pattern selection",
    "suggested_agents": ["api-designer"]
})
```

### 3. Monitor Detected

Automatic detection of conflicts:

```python
from consensus import ConsensusMonitor

monitor = ConsensusMonitor()
monitor.connect()
monitor.start()

# Monitor automatically triggers consensus when:
# - Multiple agents edit same files
# - Agents express conflicting opinions
# - Agents receive repeated corrections
# - Progress stalls
```

### 4. Checkpoint Triggered

System checkpoints requiring consensus:

```python
# Mandatory checkpoints (always trigger):
mandatory = [
    "architecture_decision",
    "security_change",
    "breaking_change",
    "api_design",
    "deployment_approval"
]
```

### 5. Phase Transition

Between Power Mode phases:

```python
# Automatic consensus before transitioning from:
consensus_phases = ["design", "architecture", "planning"]
```

### 6. Scheduled

Periodic consensus checks:

```json
{
  "scheduled": {
    "enabled": true,
    "interval_minutes": 30,
    "require_pending_decisions": true
  }
}
```

## Configuration

See `config.json` for full configuration options.

### Rule Presets

| Preset | Quorum | Approval | Rounds | Use Case |
|--------|--------|----------|--------|----------|
| `default` | 67% | 60% | 5 | Standard decisions |
| `quick` | 50% | 50% | 3 | Time-sensitive issues |
| `strict` | 80% | 75% | 7 | Important decisions |
| `critical` | 100% | 100% | 10 | Security/production |

### Monitor Patterns

| Pattern | Threshold | Window |
|---------|-----------|--------|
| `conflicting_edits` | 2 agents | 5 min |
| `opinion_divergence` | 0.6 score | 10 min |
| `repeated_corrections` | 3 times | 5 min |
| `stalled_progress` | 5 min | 5 min |
| `insight_contradictions` | 2 | 5 min |

## Agent Integration

### Hook Configuration

Add to `hooks/hooks.json`:

```json
{
  "event": "PostToolUse",
  "hooks": [
    {
      "command": "python",
      "args": ["power-mode/consensus/agent_hook.py"]
    }
  ]
}
```

### Agent Participation

When an agent receives a token, it gets a structured prompt:

```
## Consensus Discussion - Your Turn

You have been granted the speaking token in a consensus session.

**Session ID:** abc123
**Round:** 2

### Discussion Context
Round 2/5. 4 contributions (1 proposal). Key positions: REST is simpler; GraphQL is more flexible

### Previous Contributions
1. **code-architect**: I recommend REST for its simplicity and caching benefits...
2. **api-designer**: GraphQL would reduce over-fetching...

### Your Turn
Please provide your contribution. You can:
1. Share an opinion
2. Ask a question
3. Make a proposal
4. Synthesize
5. Skip
```

## Integration with Power Mode

Consensus Mode integrates with the existing Power Mode infrastructure:

### Shared Redis Channels

```
Power Mode                    Consensus Mode
────────────                  ──────────────
pop:broadcast        ◀──────▶ pop:consensus:broadcast
pop:insights         ◀──────▶ pop:consensus:session
pop:coordinator      ◀──────▶ pop:consensus:triggers
```

### Phase Sync

```python
# Consensus triggered at phase boundaries
if power_mode.phase == "design" and power_mode.transitioning:
    consensus.trigger(
        type=PHASE_TRANSITION,
        topic=f"Approve {power_mode.phase} results before {power_mode.next_phase}"
    )
```

### Insight Sharing

Consensus contributions become insights for Power Mode:

```python
contribution = Contribution(
    content="We should use event-driven architecture...",
    ...
)

# Automatically shared as insight
insight = Insight(
    type=InsightType.PATTERN,
    content=f"Consensus decision: {contribution.content}",
    relevance_tags=["architecture", "events"]
)
```

## Protocol Inspirations

### Token Ring (IEEE 802.5)
- Only token holder can "transmit" (contribute)
- Deterministic ordering ensures fairness
- Timeout handling for stuck agents

### Raft
- Term-based session management
- Leader (coordinator) election concept
- Log replication for contribution history

### PBFT
- Multi-phase agreement (propose → discuss → vote → commit)
- 2/3 majority for Byzantine fault tolerance
- View changes for coordinator failover

### Paxos
- Proposer/Acceptor/Learner roles
- Proposal numbering and acceptance
- Eventual consistency with safety

## API Reference

### ConsensusCoordinator

```python
class ConsensusCoordinator:
    def connect() -> bool
    def start()
    def stop()

    def create_session(
        topic: str,
        description: str,
        trigger_type: TriggerType,
        invited_agents: List[str],
        rules: ConsensusRules = None
    ) -> ConsensusSession

    def join_session(session_id: str, agent_id: str, agent_name: str) -> bool
    def start_discussion(session_id: str) -> bool

    def receive_contribution(
        session_id: str,
        agent_id: str,
        content: str,
        contribution_type: str = "opinion"
    ) -> Contribution

    def receive_vote(
        session_id: str,
        agent_id: str,
        proposal_id: str,
        vote_type: VoteType
    ) -> bool

    def get_session(session_id: str) -> ConsensusSession
    def get_active_sessions() -> List[ConsensusSession]
    def get_status() -> Dict
```

### TriggerManager

```python
class TriggerManager:
    def register_trigger(trigger: ConsensusTrigger)
    def on_trigger(callback: Callable[[TriggerContext], None])
    def check_all(context: Dict) -> List[TriggerContext]
    def trigger_by_type(type: TriggerType, context: Dict) -> TriggerContext
    def get_trigger_status() -> Dict
```

### ConsensusMonitor

```python
class ConsensusMonitor:
    def connect(host: str, port: int) -> bool
    def start()
    def stop()
    def get_status() -> Dict
    def get_agents() -> Dict
```

## File Structure

```
consensus/
├── __init__.py          # Module exports
├── README.md            # This documentation
├── config.json          # Configuration
├── protocol.py          # Message types, data structures
├── coordinator.py       # Session management, token ring
├── triggers.py          # Trigger mechanisms
├── monitor.py           # Conflict detection agent
└── agent_hook.py        # PostToolUse hook for participation
```

## Testing

```bash
# Run tests
pytest tests/consensus/

# Test specific component
pytest tests/consensus/test_token_ring.py
pytest tests/consensus/test_voting.py
pytest tests/consensus/test_triggers.py
```

## Troubleshooting

### No token received

1. Check Redis connection: `redis-cli -p 16379 ping`
2. Verify agent is in session: Check `session.participants`
3. Check token manager state: `coordinator.token_managers[session_id].state`

### Consensus blocked

1. Check vote results: `coordinator.vote_collectors[session_id].get_result(...)`
2. Verify quorum: Enough participants?
3. Check for vetoes or unanimous rejections

### Monitor not triggering

1. Verify patterns enabled in config
2. Check cooldown periods
3. Verify thresholds aren't too high

## Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update this README for API changes
4. Use conventional commits

## License

Part of PopKit plugin - MIT License
