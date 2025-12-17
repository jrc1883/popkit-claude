# [Architecture] Unified Orchestration System - Power Mode + Quality Gates + Development Pipeline

**Issue Draft** - To be created via `/popkit:issue create`

---

## Priority: CRITICAL

## Overview

Unify three interconnected capabilities into a cohesive orchestration system:

1. **Power Mode** (existing) - Multi-agent pub/sub coordination
2. **Quality Gates** (Issue #8) - Validation between agent runs
3. **Development Pipeline** (Issue #5) - Standardized 0-10 phases

The goal is a system where PopKit automatically knows WHEN to activate Power Mode, WHAT quality gates to run, and HOW to guide work through standardized phases - all driven by issue metadata and project context.

## Problem Statement

Current state has three disconnected pieces:

| Component | Status | Problem |
|-----------|--------|---------|
| Power Mode | v0.7.1 | Exists but no triggers - must be manually activated |
| Quality Gates | Issue #8 | Requested but not built - agents can break builds |
| Dev Pipeline | Issue #5 | Documented but not integrated - just theory |

Result: Users must manually orchestrate, agents can cause chaos, and there's no standardized workflow.

## Goals

1. **Auto-activation** - Power Mode activates based on issue complexity, not manual command
2. **Integrated quality gates** - Validation IS the phase transition, not separate
3. **Standardized phases** - Every feature follows discoverable, documented phases
4. **Comprehensive PRD** - `/popkit:prd` generates ALL development documents, not just PRD.md
5. **Issue-driven workflow** - PopKit Guidance section in issues directs the entire workflow

## Non-Goals

- Replacing human judgment for architectural decisions
- Auto-deploying to production
- Supporting non-Claude-Code workflows

## Proposed Architecture

### Current State

```
User → Manual Power Mode activation → Agents run in parallel → No validation → Hope nothing breaks

Issues → No guidance → User figures out workflow → Ad-hoc agent selection
```

### Target State

```
Issue Created (with PopKit Guidance section)
    ↓
PopKit reads issue metadata:
  - Complexity? → Determines Power Mode activation
  - Phases checked? → Generates phase workflow
  - Quality gates? → Schedules validation points
  - Agents suggested? → Pre-configures routing
    ↓
Automatic orchestration:
  Phase 1 (Discovery) → Quality Gate → Phase 2 (Architecture) → Quality Gate → ...
    ↓
Power Mode activates for parallelizable phases (Implementation, Testing, Docs)
    ↓
Each agent check-in runs quality validation
    ↓
Phase transitions require gates to pass
```

### Key Components

#### 1. Issue Metadata Parser

Reads PopKit Guidance section from GitHub issues:

```python
def parse_popkit_guidance(issue_body: str) -> WorkflowConfig:
    """Extract workflow configuration from issue."""
    return {
        "workflow_type": "brainstorm_first" | "plan_required" | "direct",
        "phases": ["discovery", "architecture", ...],
        "agents": {"primary": [...], "supporting": [...]},
        "quality_gates": ["tsc", "build", "lint", "test"],
        "power_mode": "recommended" | "optional" | "not_needed",
        "complexity": "small" | "medium" | "large" | "epic"
    }
```

#### 2. Activation Triggers

Power Mode activates automatically when:

| Trigger | Condition | Example |
|---------|-----------|---------|
| **Issue complexity** | `complexity: epic` or `complexity: large` | Architecture issues |
| **Multi-agent suggestion** | 3+ agents in suggested list | Feature with security + perf + tests |
| **Parallel phases** | Multiple phases can run simultaneously | Implementation + tests + docs |
| **Explicit flag** | `power_mode: recommended` checked | User opted in |
| **Task decomposition** | `/popkit:execute-plan` with 5+ independent tasks | Plan execution |

Power Mode stays OFF when:
- `complexity: small` or `complexity: medium`
- Single agent sufficient
- Sequential work required
- `power_mode: not_needed` checked

#### 3. Quality Gates as Phase Transitions

Quality gates are NOT a separate system - they ARE the mechanism for phase transitions:

```
Phase: Implementation
    ↓
Agent completes task
    ↓
Quality Gate runs:
  - tsc --noEmit (if TypeScript)
  - npm run build (if build script)
  - npm run lint (if lint script)
  - npm test (if test script)
    ↓
Gate passes? → Proceed to next phase
Gate fails? → Options presented:
  1. Fix issues (stay in current phase)
  2. Rollback to checkpoint
  3. Escalate to human
```

#### 4. Development Pipeline Phases

Standard 10-phase pipeline with artifacts:

| Phase | Agents | Artifacts | Quality Gate |
|-------|--------|-----------|--------------|
| 0. Discovery | researcher, code-explorer | `problem_statement.md`, `constraints.md` | Human review |
| 1. PRD | - | `PRD.md`, `user_stories.md`, `acceptance_criteria.md` | Human approval |
| 2. Architecture | code-architect | `ARCHITECTURE.md`, `data_model.md`, `api_spec.md` | Human review |
| 3. Technical Design | code-architect | `TECHNICAL_SPEC.md`, `file_structure.md` | Human review |
| 4. Implementation | Multiple (parallelizable) | Code files, `CHANGELOG.md` | tsc, build, lint |
| 5. Testing | test-writer-fixer | Test files, coverage report | All tests pass |
| 6. Review | code-reviewer, security-auditor | `review_notes.md` | No critical issues |
| 7. Documentation | documentation-maintainer | `README.md`, API docs | Docs build |
| 8. Deployment | devops-automator | `deployment_checklist.md` | CI/CD passes |
| 9. Monitoring | metrics-collector | `alerts.md`, `runbook.md` | Alerts configured |
| 10. Maintenance | - | `TECHNICAL_DEBT.md`, `lessons_learned.md` | Session captured |

#### 5. Comprehensive PRD Generation

`/popkit:prd` generates a complete document suite, not just PRD.md:

```
/popkit:prd "User authentication system"
    ↓
Generates:
  docs/features/auth/
  ├── PRD.md                 # Product requirements
  ├── user_stories.md        # User stories with acceptance criteria
  ├── ARCHITECTURE.md        # High-level architecture
  ├── TECHNICAL_SPEC.md      # Implementation details
  ├── data_model.md          # Schema/models
  ├── api_spec.md            # API endpoints (if applicable)
  ├── test_plan.md           # Testing strategy
  └── rollout_plan.md        # Deployment/rollout strategy
```

#### 6. Pub/Sub Patterns for Coordinated Agents

When Power Mode is active, agents communicate via defined patterns:

**Pattern A: Parallel Implementation**
```
Coordinator publishes: "Phase 4: Implementation starting"
  → Agent A (frontend): subscribes, works on UI
  → Agent B (backend): subscribes, works on API
  → Agent C (tests): subscribes, writes tests
Each agent: publishes insights to pop:insights
Coordinator: monitors pop:heartbeat, aggregates pop:results
All complete → Quality gate runs → Phase 5 begins
```

**Pattern B: Investigation Swarm**
```
Coordinator publishes: "Bug hunt: issue #123"
  → bug-whisperer A: investigates hypothesis 1
  → bug-whisperer B: investigates hypothesis 2
  → security-auditor: checks for security implications
First to find root cause: publishes to pop:insights
Coordinator: broadcasts finding, others can stop or verify
```

**Pattern C: Document Generation**
```
Coordinator publishes: "Phase 7: Documentation"
  → documentation-maintainer: README, guides
  → api-designer: API docs
  → code-reviewer: inline comments
All publish to pop:results
Coordinator: aggregates, checks for conflicts
```

### Migration Path

1. **Phase 1: Quality Gates Hook** (from Issue #8)
   - Add `post-tool-use-validation.py` hook
   - Runs tsc/build/lint after agent tool calls
   - Alert + rollback option on failure

2. **Phase 2: Issue Parser**
   - Parse PopKit Guidance section from issues
   - Store workflow config in session
   - Guide `/popkit:issue` to populate guidance

3. **Phase 3: Activation Logic**
   - Implement trigger rules
   - Auto-activate Power Mode based on config
   - Fall back to file-based if Redis unavailable

4. **Phase 4: Phase Orchestration**
   - Integrate quality gates as phase transitions
   - Track phase progress in STATUS.json
   - Enable phase skip only with human approval

5. **Phase 5: PRD Enhancement**
   - Update `/popkit:prd` to generate document suite
   - Create templates for each document type
   - Link documents to phases

## Components Affected

- [x] Skills (`pop:*`) - New skills for orchestration
- [x] Agents (tier-1, tier-2, feature-workflow) - Routing updates
- [x] Commands (`/popkit:*`) - PRD enhancement, new orchestration commands
- [x] Hooks - Quality gate hooks, phase transition hooks
- [x] Output Styles - Phase progress, quality gate results
- [x] Power Mode - Activation triggers, pub/sub patterns
- [ ] MCP Server Template - No changes
- [x] Documentation - Extensive updates

## Sub-Issues

This epic breaks down into:

- [ ] Close #8 - Superseded by this unified approach
- [ ] Close #5 - Developer Experience Guide merges here
- [ ] New: Quality Gates Hook implementation
- [ ] New: Issue metadata parser
- [ ] New: Activation trigger logic
- [ ] New: Phase orchestration system
- [ ] New: Enhanced PRD generation
- [ ] New: Pub/sub pattern documentation

## Acceptance Criteria

- [ ] Power Mode auto-activates based on issue complexity
- [ ] Quality gates run between phases
- [ ] Build failures block phase transitions with options
- [ ] `/popkit:prd` generates complete document suite
- [ ] PopKit Guidance section guides entire workflow
- [ ] Phase progress visible in output
- [ ] Rollback available at any phase boundary
- [ ] Works with both Redis and file-based coordination

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Over-automation frustrates users | Medium | High | Opt-out flags, manual override always available |
| Quality gates too slow | Low | Medium | Cache results, skip unchanged |
| Phase model too rigid | Medium | Medium | Allow phase skip with human approval |
| Power Mode complexity | Low | High | File-based fallback, progressive disclosure |

## Related Issues

- #8 - Agent Quality Gates (superseded)
- #5 - Developer Experience Guide (superseded)
- #9 - 1.0 Readiness Tracking (this contributes)

---

## PopKit Guidance

### Workflow
- [x] **Brainstorm First** - Use `pop-brainstorming` skill before implementation
- [x] **Plan Required** - Use `/popkit:write-plan` to create detailed implementation plan

### Development Phases
- [x] Discovery - Research existing patterns and constraints
- [x] Architecture - Design decisions and tradeoffs
- [x] Implementation - Incremental code changes
- [x] Testing - Comprehensive test coverage
- [x] Documentation - Architecture docs, README updates
- [x] Review - Multiple review checkpoints

### Suggested Agents
- Primary: `code-architect`, `refactoring-expert`
- Supporting: `migration-specialist`, `devops-automator`
- Quality: `test-writer-fixer`, `code-reviewer`

### Quality Gates
- [x] TypeScript check (`tsc --noEmit`) after each phase
- [x] Build verification after each phase
- [x] Lint pass
- [x] Test pass
- [x] Manual review checkpoint between phases

### Power Mode
- [x] **Recommended** - Implementation phase benefits from parallel agents

### Estimated Complexity
- [x] Epic (multiple PRs, architectural changes)

---

## Test Project Opportunity

This issue itself could be the test project! Implementing this unified system while:
- Keeping detailed transcripts of each session
- Using PopKit features as much as possible
- Documenting pain points and improvements discovered
- Iterating on the design based on real usage

This creates a feedback loop where building the tool improves the tool.
