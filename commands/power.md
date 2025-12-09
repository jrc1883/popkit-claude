---
description: "start | stop | status | init | widgets | consensus [--consensus, --agents N]"
---

# /popkit:power - Power Mode Management

Manage multi-agent orchestration via Redis pub/sub for complex tasks requiring parallel agent collaboration.

## Usage

```
/popkit:power <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `status` | Check current Power Mode status (default) |
| `start` | Start Power Mode with objective |
| `stop` | Stop Power Mode gracefully |
| `init` | Initialize Redis infrastructure |
| `widgets` | Manage status line widgets (Issue #79) |
| `consensus` | Manage consensus mode for multi-agent decisions (Issue #86) |

---

## Subcommand: status (default)

Check current Power Mode status.

```
/popkit:power
/popkit:power status
```

### Output When Active

```
[+] POWER MODE ACTIVE

Session: abc123
Issue: #11 - Unified orchestration system
Started: 15 minutes ago
Runtime: 15m 32s

Current State:
  Phase: implementation (3/5)
  Progress: 45%
  Agents: 2 active

Active Agents:
  - code-architect: Designing API structure [T:28 P:60%]
  - test-writer-fixer: Writing unit tests [T:15 P:30%]

Recent Check-ins:
  10:05:32 code-architect: "Found existing auth patterns in src/auth/"
  10:04:18 test-writer-fixer: "Using Jest with existing test setup"

Insights Shared: 8
Patterns Learned: 3

Commands:
  /popkit:power stop    Stop Power Mode
  /popkit:issue work #11      Continue current issue
```

### Output When Inactive

```
[i] POWER MODE INACTIVE

No active Power Mode session.

To start Power Mode:
  /popkit:issue work #N -p     Work on issue with Power Mode
  /popkit:power start "task"   Start with custom objective
  /popkit:issue list --power   List issues recommending Power Mode

Redis Status: localhost:16379 [OK]
```

---

## Subcommand: start

Start Power Mode with an objective.

```
/popkit:power start "Build user authentication with tests"
/popkit:power start "Create REST API" --phases explore,design,implement,test
/popkit:power start "Refactor database layer" --agents reviewer,architect,tester
```

### Arguments

| Argument | Description |
|----------|-------------|
| `[objective]` | Task description (required) |
| `--phases` | Comma-separated phase names (default: explore,design,implement,test,review) |
| `--agents` | Comma-separated agent names to use |
| `--timeout` | Max runtime in minutes (default: 30) |
| `--consensus` | Enable consensus mode for multi-agent decision-making |
| `--consensus-rules` | Preset rules: default, quick, strict, critical |

### Prerequisites

**Redis must be running:**
```bash
# Check Redis
/popkit:power init

# Start if needed
/popkit:power init start
```

### Process

1. **Check Prerequisites**: Verify Redis connection
2. **Parse Objective**: Extract description, success criteria, phases, boundaries
3. **Start Coordinator**: Enable power mode and start coordinator process
4. **Display Configuration**: Show phases, agents, boundaries
5. **Begin Orchestration**: Dispatch initial agents

### Output

```
POWER MODE ACTIVATED

Session: abc123
Objective: Build user authentication with tests

Phases:
1. explore   - Analyze codebase and requirements
2. design    - Plan implementation
3. implement - Build the feature
4. test      - Write and run tests
5. review    - Final review

Boundaries:
  Files: src/auth/**, tests/auth/**
  Protected: .env*, secrets/
  Human approval: deploy, push main

Check-ins: Every 5 tool calls
Timeout: 30 minutes

Redis: localhost:6379 [OK]
Channels: pop:broadcast, pop:insights, pop:heartbeat

Ready to orchestrate. Agents will check in periodically.
```

---

## Subcommand: stop

Stop Power Mode gracefully.

```
/popkit:power stop
```

### Process

1. Send stop signal to coordinator
2. Wait for active agents to complete current tool call
3. Save session state
4. Clean up Redis channels

### Output

```
[+] STOPPING POWER MODE

Sending stop signal to coordinator...
Waiting for active agents to complete current tool call...
Saving session state...
Cleaning up Redis channels...

Power Mode deactivated.

Session Summary:
  Session: abc123
  Issue: #11
  Runtime: 25m 18s
  Phases completed: 3/5
  Insights shared: 12
  Patterns learned: 5

Session transcript saved to:
  ~/.claude/power-mode-sessions/abc123.json

Resume later with:
  /popkit:issue work #11
```

---

## Subcommand: init

Initialize Redis infrastructure for Power Mode.

```
/popkit:power init              # Check status and setup if needed
/popkit:power init start        # Start Redis
/popkit:power init stop         # Stop Redis
/popkit:power init restart      # Restart Redis
/popkit:power init debug        # Start with Redis Commander (http://localhost:8081)
/popkit:power init test         # Test Redis connectivity
/popkit:power init statusline   # Configure status line display
```

### Prerequisites

- Docker installed and running
- Docker Compose (V1 or V2)

If Docker is not installed:
- **macOS**: Install Docker Desktop from https://docs.docker.com/desktop/mac/install/
- **Windows**: Install Docker Desktop from https://docs.docker.com/desktop/windows/install/
- **Linux**: Install Docker Engine from https://docs.docker.com/engine/install/

### Init Subcommands

#### Default (status + auto-start)

```
/popkit:power init

Checking Docker availability...
Docker is installed and running
Starting Redis container...
Redis container started
Waiting for Redis to be healthy...
Redis is running and accessible

Ready for Power Mode!

Next steps:
1. Run /popkit:power start "objective" to activate
2. Run /popkit:power init debug to open Redis Commander
```

#### start

```bash
cd power-mode/
python setup-redis.py start
```

Pulls Redis 7 Alpine image, creates container, exposes port 6379, creates persistent volume.

#### stop

```bash
cd power-mode/
python setup-redis.py stop
```

Gracefully stops Redis container (data persists in volume).

#### debug

```
/popkit:power init debug

Starting Redis Commander at http://localhost:8081

Inspect:
- Active pub/sub subscriptions
- Agent heartbeats
- Message queues
- Insight pool
```

#### test

```
/popkit:power init test
```

Verifies Redis connectivity, pub/sub functionality, and all Power Mode channels.

### Redis Channels

| Channel | Purpose |
|---------|---------|
| pop:broadcast | Messages to all agents |
| pop:heartbeat | Agent health checks |
| pop:results | Task completion results |
| pop:insights | Shared discoveries between agents |
| pop:coordinator | Coordinator commands |
| pop:human | Requests for human decisions |

---

## Subcommand: widgets (Issue #79)

Manage status line widgets for real-time metrics display.

```
/popkit:power widgets                    # List available widgets
/popkit:power widgets list               # Same as above
/popkit:power widgets enable <widget>    # Enable a widget
/popkit:power widgets disable <widget>   # Disable a widget
/popkit:power widgets compact [on|off]   # Toggle compact mode
/popkit:power widgets reset              # Reset to default config
```

### Available Widgets

| Widget | Description | Compact | Full |
|--------|-------------|---------|------|
| `popkit` | PopKit branding indicator | `[PK]` | `[PopKit]` |
| `efficiency` | Token savings (Issue #78) | `~2.4k` | `~2.4k saved P:3 D:12` |
| `power_mode` | Power Mode status | `#45 3/7 40%` | `#45 Phase 3/7 Agents:4 [####----] 40%` |
| `workflow` | Workflow progress | `impl 70%` | `feature-dev: Implementation (70%)` |
| `health` | Build/test/lint status | `✓✓✓` | `Build:✓ Tests:12/12 Lint:0` |

### Examples

```
# List widgets with current status
/popkit:power widgets

Output:
Available Widgets:
----------------------------------------
  [✓] popkit       - PopKit branding indicator
       Sample: [PK]
  [✓] efficiency   - Token savings, patterns matched
       Sample: ~2.4k
  [✓] power_mode   - Power Mode status with issue, phase
       Sample: #45 3/7 40%
  [ ] workflow     - Current workflow progress
  [ ] health       - Build, test, lint status

Current config: popkit, efficiency, power_mode
Compact mode: true

# Enable health widget
/popkit:power widgets enable health

# Disable workflow widget
/popkit:power widgets disable workflow

# Switch to full display mode
/popkit:power widgets compact off
```

### Widget Configuration

Configuration is stored in `.claude/popkit/config.json`:

```json
{
  "statusline": {
    "widgets": ["popkit", "efficiency", "power_mode"],
    "compact_mode": true,
    "show_hints": true,
    "separator": " | "
  }
}
```

---

## Status Line Integration

When Power Mode is active, the status line shows configured widgets:

**Default (Widget-Based):**
```
[PK] | ~2.4k | #45 3/7 40%
```

**Legacy Format:**
```
[POP] #11 Phase: implement (3/5) [####------] 40% (/power status | stop)
```

Components:
- `[PK]` or `[POP]` - PopKit/Power Mode indicator
- Efficiency metrics - Token savings
- Issue/Phase info - Current progress
- Commands hint - Quick reference (optional)

### Setup Status Line

**Automatic (Recommended):**
```
/popkit:power init statusline
```

This adds the following to your `.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python",
    "args": ["~/.claude/plugins/marketplaces/popkit-marketplace/power-mode/statusline.py"],
    "padding": 0
  }
}
```

**Manual:**
1. Create or edit `.claude/settings.json` in your user home directory
2. Add the statusLine configuration above
3. Restart Claude Code to apply

**State File:** Power Mode state is stored at `.claude/popkit/power-mode-state.json`

---

## Examples

```bash
# Check Power Mode status
/popkit:power
/popkit:power status

# Initialize Redis
/popkit:power init
/popkit:power init start

# Start with custom objective
/popkit:power start "Add dark mode toggle"

# Custom objective with specific phases
/popkit:power start "Optimize database queries" --phases analyze,implement,test

# Custom objective with specific agents
/popkit:power start "Security audit" --agents security-auditor

# Stop Power Mode
/popkit:power stop

# Debug Redis
/popkit:power init debug
```

---

## Subcommand: consensus (Issue #86)

Manage consensus mode for structured multi-agent decision-making through democratic voting.

```
/popkit:power consensus                    # Show consensus status
/popkit:power consensus status             # Same as above
/popkit:power consensus enable             # Enable consensus for current session
/popkit:power consensus disable            # Disable consensus
/popkit:power consensus rules              # Show current voting rules
/popkit:power consensus rules <preset>     # Set rules preset
```

### Consensus Protocol

Inspired by IEEE 802.5 Token Ring and distributed consensus protocols (Raft, PBFT, Paxos).

**Token Ring Protocol:**
- Ordered turn-taking prevents "everyone talking at once"
- Round-robin agent sequencing
- Timeout handling with automatic advancement
- Dynamic participant join/leave

**7-Phase Consensus State Machine:**
```
GATHERING -> PROPOSING -> DISCUSSING -> CONVERGING -> VOTING -> COMMITTED (or ABORTED)
```

### Trigger Mechanisms

| Trigger | When It Fires |
|---------|---------------|
| UserRequestTrigger | Explicit user-initiated ("agents, decide this") |
| AgentRequestTrigger | Agent detects need for consensus |
| ConflictTrigger | File or opinion conflicts detected |
| ThresholdTrigger | Disagreement score exceeds threshold |
| CheckpointTrigger | Mandatory decision points |
| PhaseTransitionTrigger | Between Power Mode phases |
| ScheduledTrigger | Periodic checks during long sessions |

### Rule Presets

| Preset | Quorum | Approval | Use Case |
|--------|--------|----------|----------|
| `default` | 67% | 60% | Standard decisions |
| `quick` | 50% | 50% | Fast, low-stakes decisions |
| `strict` | 80% | 75% | Important architecture decisions |
| `critical` | 100% | 100% | Breaking changes, security |

### Examples

```bash
# Start Power Mode with consensus enabled
/popkit:power start "Refactor database layer" --consensus

# Use strict consensus for architecture decisions
/popkit:power start "Redesign API" --consensus --consensus-rules strict

# Check consensus status during session
/popkit:power consensus status

# Change rules mid-session
/popkit:power consensus rules critical
```

### Output (Consensus Active)

```
[+] CONSENSUS MODE ACTIVE

Current Session: abc123
Voting Rules: default (67% quorum, 60% approval)

Active Consensus:
  Topic: "Which database migration approach?"
  Phase: VOTING (4/6)
  Participants: 3/4 (code-architect, migration-specialist, query-optimizer)
  Token Holder: migration-specialist

Proposals:
  1. "Blue-green deployment with rollback" - 2 votes
  2. "Incremental migration with feature flags" - 1 vote

Time Remaining: 2m 30s
```

### Consensus Files

| File | Purpose |
|------|---------|
| `power-mode/consensus/protocol.py` | Message types, phases, voting |
| `power-mode/consensus/coordinator.py` | Session management, token ring |
| `power-mode/consensus/triggers.py` | 7 trigger implementations |
| `power-mode/consensus/monitor.py` | Conflict detection |
| `power-mode/consensus/agent_hook.py` | PostToolUse hook for agents |
| `power-mode/consensus/config.json` | Rules, timeouts, thresholds |
| `power-mode/consensus/README.md` | Comprehensive documentation |

---

## File-Based Fallback

Power Mode works without Redis using file-based coordination:
- Uses shared JSON file for coordination
- Good for 2-3 agents, development, learning
- Auto-activates when Redis unavailable
- Zero setup required

---

## Auto-Activation (Issue #66)

Power Mode can automatically suggest or enable itself based on task analysis.

### Activation Triggers

| Trigger | Confidence | Auto-Enable |
|---------|------------|-------------|
| Label: `epic` | +80% | Yes |
| Label: `power-mode` | +80% | Yes |
| Label: `complex`, `multi-phase`, `architecture`, `refactor`, `migration` | +30% each | No |
| PopKit Guidance: Power Mode checkbox | +90% | Yes |
| PopKit Guidance: 3+ phases | +20% | No |
| PopKit Guidance: 2+ agents | +15% | No |
| PopKit Guidance: High complexity | +20% | No |
| 5+ files estimated | +10-30% | No |
| Title keywords: epic, migration, refactor, architecture | +15% each | No |
| Body keywords: comprehensive, multi-agent, parallel | +10% each | No |

### Decision Priority

1. **Explicit flags** (`-p`/`--power` or `--solo`) override everything
2. **PopKit Guidance section** in issue body
3. **Issue labels** (epic, complex, etc.)
4. **Content analysis** (keywords, file counts)
5. **Default to sequential** mode if confidence < 60%

### Thresholds

| Confidence | Action |
|------------|--------|
| 0-59% | Sequential mode (no suggestion) |
| 60-79% | Suggest Power Mode |
| 80-100% | Auto-enable Power Mode |

### Detection Files

| File | Purpose |
|------|---------|
| `hooks/utils/power_detector.py` | PowerDetector class |
| `hooks/issue-workflow.py` | Integration with issue work |

### Usage in Commands

```bash
# Explicit Power Mode
/popkit:dev work #45 -p

# Explicit Sequential Mode
/popkit:dev work #45 --solo

# Auto-detection (uses PowerDetector)
/popkit:dev work #45

# Check what would be detected for an issue
python hooks/utils/power_detector.py --issue 45 --json
```

### PowerDetector API

```python
from hooks.utils.power_detector import PowerDetector, get_power_mode_recommendation

# Analyze an issue
detector = PowerDetector()
result = detector.analyze_issue(issue_data)

if result.should_auto_enable:
    print(f"Auto-enable: {result.reason}")
elif result.should_suggest:
    print(f"Suggest: {result.reason}")

# Quick check
if should_suggest_power_mode(issue_data):
    print("Power Mode recommended")

# Full API
recommendation = get_power_mode_recommendation(
    issue_data=issue_data,
    task="Refactor the auth system",
    flags={"power": True}  # Explicit flag overrides
)
```

### Example Output

```
Power Mode Recommendation:
  Should suggest: True
  Should auto-enable: True
  Confidence: 85%
  Reason: Power Mode recommended: epic issue

Detected signals:
  - Labels: epic
  - PopKit Guidance: 5 phases
  - PopKit Guidance: 3 agents
  - Estimated files: 12

Suggested phases: explore → design → implement → test → review
Suggested agents: code-architect, api-designer, test-writer-fixer
```

---

## Skill Reference

This command activates the `pop-power-mode` skill. For detailed documentation see: `skills/pop-power-mode/SKILL.md`

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| **Coordinator** | `power-mode/coordinator.py` |
| **Auto-Coordinator** | `power-mode/coordinator_auto.py` |
| **File Fallback** | `power-mode/file_fallback.py` |
| **Check-In Hook** | `power-mode/checkin-hook.py` |
| **Status Line** | `power-mode/statusline.py` |
| **Efficiency Tracker** | `hooks/utils/efficiency_tracker.py` |
| **Config** | `power-mode/config.json` |
| **Widget Config** | `.claude/popkit/config.json` (statusline section) |
| **Docker Setup** | `power-mode/docker-compose.yml` |
| **Setup Script** | `power-mode/setup-redis.py` |
| **State File** | `~/.claude/power-mode-state.json` |
| **Efficiency Metrics** | `.claude/popkit/efficiency-metrics.json` |
| **Health State** | `.claude/popkit/health-state.json` |
| **Consensus Protocol** | `power-mode/consensus/protocol.py` |
| **Consensus Coordinator** | `power-mode/consensus/coordinator.py` |
| **Consensus Triggers** | `power-mode/consensus/triggers.py` |
| **Consensus Monitor** | `power-mode/consensus/monitor.py` |
| **Consensus Agent Hook** | `power-mode/consensus/agent_hook.py` |
| **Consensus Config** | `power-mode/consensus/config.json` |
| **Consensus Tests** | `tests/consensus/` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:issue work #N -p` | Work on issue with Power Mode |
| `/popkit:issue list --power` | List issues recommending Power Mode |
| `/popkit:stats` | View efficiency metrics (Issue #78) |
| `/popkit:routine morning` | Includes Redis health check |
