---
name: agent-handoff
description: Standardized format for passing context between agents or from subagent to parent
used_by:
  - all-agents
  - multi-agent-workflows
---

# Agent Handoff Style

## Purpose

Enable seamless context transfer between agents in multi-agent workflows. When Agent A delegates to Agent B, or when a subagent returns results to its parent, this format ensures all critical context is preserved and auditable.

## Format

```markdown
## Agent Handoff Report

**From:** [agent-name]
**To:** [target-agent or parent]
**Task:** [brief description]
**Status:** [completed|partial|blocked|failed]
**Confidence:** [0-100]

---

### Summary
<2-3 sentences describing what was accomplished>

### Findings

#### Key Discoveries
1. [Discovery with file:line reference]
2. [Discovery with file:line reference]

#### Artifacts Created
- `path/to/file.ts` - [description]
- `path/to/file.ts` - [description]

#### Artifacts Modified
- `path/to/file.ts:50-75` - [what changed]

### Context for Next Agent

#### Relevant Files
| File | Lines | Why It Matters |
|------|-------|----------------|
| `src/path/file.ts` | 1-50 | [reason] |

#### Patterns Identified
- [Pattern]: Found in [location]
- [Pattern]: Used for [purpose]

#### Decisions Made
- **Decision**: [what was decided]
  - **Rationale**: [why]
  - **Alternatives Considered**: [what else was possible]

### Blockers / Open Questions

- [ ] [Blocker or question requiring human input]
- [ ] [Technical issue that couldn't be resolved]

### Recommendations for Next Agent

1. [Specific action to take]
2. [Area to focus on]
3. [Thing to avoid]

### Verification Commands

```bash
# How to verify this work
[command 1]
[command 2]
```

---

**Handoff Confidence:** [0-100]
**Ready for Next Phase:** [Yes|No|With caveats]
```

## Field Definitions

### Status Values

| Status | Meaning |
|--------|---------|
| `completed` | Task fully accomplished, all objectives met |
| `partial` | Some objectives met, others pending |
| `blocked` | Cannot proceed without input/resolution |
| `failed` | Task could not be completed |

### Confidence Score

| Score | Meaning |
|-------|---------|
| 90-100 | High confidence, work is solid |
| 70-89 | Good confidence, minor uncertainties |
| 50-69 | Moderate confidence, some assumptions made |
| 0-49 | Low confidence, significant uncertainty |

## Use Cases

### 1. Sequential Agent Chain
```
code-explorer → code-architect → code-reviewer
```
Each agent hands off to the next with full context.

### 2. Parallel Agent Merge
```
security-auditor ─┐
                  ├→ code-reviewer (merges findings)
performance-opt ──┘
```
Multiple agents hand off to a coordinating agent.

### 3. Subagent Return
```
parent-agent
    └→ subagent (returns findings)
```
Subagent returns structured results to parent.

## Example: Code Explorer → Code Architect

```markdown
## Agent Handoff Report

**From:** code-explorer
**To:** code-architect
**Task:** Analyze authentication patterns for new OAuth feature
**Status:** completed
**Confidence:** 85

---

### Summary
Explored existing authentication implementation. Found NextAuth.js with Supabase adapter. Current pattern uses JWT sessions with 7-day expiry. No existing OAuth providers configured.

### Findings

#### Key Discoveries
1. Auth config in `src/lib/auth.ts:1-45` - NextAuth setup
2. Session handling in `src/middleware.ts:20-35` - JWT validation
3. Protected routes use `withAuth` HOC from `src/components/withAuth.tsx`

#### Artifacts Created
- None (exploration only)

#### Artifacts Modified
- None (exploration only)

### Context for Next Agent

#### Relevant Files
| File | Lines | Why It Matters |
|------|-------|----------------|
| `src/lib/auth.ts` | 1-45 | Main auth configuration |
| `src/middleware.ts` | 20-35 | Session validation logic |
| `src/components/withAuth.tsx` | All | HOC pattern to follow |

#### Patterns Identified
- **Provider Pattern**: Auth providers in `auth.ts` providers array
- **Adapter Pattern**: Supabase adapter for user storage
- **HOC Pattern**: `withAuth` for protected components

#### Decisions Made
- **Decision**: OAuth should be added to existing NextAuth setup
  - **Rationale**: Minimal changes, follows existing patterns
  - **Alternatives Considered**: Separate OAuth flow, rejected as duplicative

### Blockers / Open Questions

- [ ] Which OAuth providers to support? (Google, GitHub, both?)
- [ ] Should we add email/password fallback?

### Recommendations for Next Agent

1. Add OAuth providers to `src/lib/auth.ts` providers array
2. Follow existing `withAuth` HOC pattern for protected routes
3. Avoid modifying session handling - current JWT approach is solid

### Verification Commands

```bash
# Check auth config
cat src/lib/auth.ts

# Verify middleware
cat src/middleware.ts
```

---

**Handoff Confidence:** 85
**Ready for Next Phase:** Yes
```

## Integration

### In Agent Definitions

```yaml
---
name: code-explorer
output_style: agent-handoff
---
```

### In Workflows

The `agent-handoff` style is automatically used when:
- One agent delegates to another via Task tool
- Subagents return results to parent
- Multi-phase workflows transition between phases

## Parsing Handoff Reports

For programmatic processing:

```typescript
interface AgentHandoff {
  from: string;
  to: string;
  task: string;
  status: 'completed' | 'partial' | 'blocked' | 'failed';
  confidence: number;
  summary: string;
  findings: {
    discoveries: string[];
    artifactsCreated: string[];
    artifactsModified: string[];
  };
  context: {
    relevantFiles: { file: string; lines: string; reason: string }[];
    patterns: string[];
    decisions: { decision: string; rationale: string; alternatives: string }[];
  };
  blockers: string[];
  recommendations: string[];
  verificationCommands: string[];
  readyForNextPhase: boolean;
}
```
