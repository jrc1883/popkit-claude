---
name: agent-name
description: "One-line description of when to use this agent"
tools: Read, Write, Grep, Glob
output_style: optional-style-name
model: inherit
version: 1.0.0
---

# Agent Name

## Metadata

- **Name**: agent-name
- **Category**: [Development|Testing|Security|Documentation|DevOps|Orchestration|Design|Research]
- **Type**: [Analyzer|Generator|Reviewer|Optimizer|Specialist|Coordinator]
- **Color**: [blue|green|yellow|red|cyan|magenta]
- **Priority**: [High|Medium|Low]
- **Version**: 1.0.0
- **Tier**: [tier-1-always-active|tier-2-on-demand|feature-workflow]

## Purpose

[2-4 sentences describing the agent's mission. What problems does it solve? When should it be invoked? What makes it distinct from other agents?]

## Primary Capabilities

- **Capability 1**: [Description of what this enables]
- **Capability 2**: [Description of what this enables]
- **Capability 3**: [Description of what this enables]
- [3-7 bullet points total]

## Progress Tracking

- **Checkpoint Frequency**: Every [N] tool calls or [milestone]
- **Format**: "[ICON] agent-name T:[tool-count] P:[percent] | [current-task]"
- **Efficiency**: [How progress is measured - files processed, issues found, etc.]

Example:
```
🔍 code-reviewer T:15 P:60% | Reviewing src/auth/login.ts
```

## Circuit Breakers

1. **[Limit Name]**: [threshold] → [action]
2. **[Limit Name]**: [threshold] → [action]
3. **[Limit Name]**: [threshold] → [action]
4. **Token Budget**: [N]k tokens → warn user
5. **Scope Creep**: [condition] → request clarification
6. **Human Escalation**: [condition] → pause and escalate

Example limits:
- **Max Files**: 50 files → summarize and ask to continue
- **Time Limit**: 10 minutes → checkpoint and report
- **Error Threshold**: 3 consecutive failures → halt and diagnose

## Systematic Approach

### Phase 1: [Phase Name]

[Description of what happens in this phase]

1. [Step 1]
2. [Step 2]
3. [Step 3]

### Phase 2: [Phase Name]

[Continue with phases as needed...]

### Phase N: Completion

[Final steps and wrap-up]

## Power Mode Integration

### Check-In Protocol

Participates in Power Mode check-ins every 5 tool calls.

### PUSH (Outgoing)

Share discoveries with other agents:

- **Discoveries**: File locations, patterns found, key information
- **Decisions**: Significant choices with reasoning
- **Tags**: [relevant, domain, tags]

Example:
```
↑ "Found User model at src/models/user.ts" [model, database]
↑ "Using Jest for testing" [test, jest]
```

### PULL (Incoming)

Accept insights with relevant tags:

- `[tag1]` - From [agent-type] about [what]
- `[tag2]` - From [agent-type] about [what]

Example:
```
↓ architect: "Use existing Prisma client" [database, orm]
↓ explorer: "Tests in __tests__/ directory" [test, location]
```

### Progress Format

```
[ICON] agent-name T:[count] P:[%] | [current-task]
```

### Sync Barriers

- [List sync points or "None - operates independently"]

Example:
- Wait after exploration phase before architecture
- Sync before implementation begins

## Integration with Other Agents

### Upstream (Receives from)

| Agent | What It Provides |
|-------|------------------|
| [agent-name] | [What context/data is passed] |

### Downstream (Passes to)

| Agent | What It Receives |
|-------|------------------|
| [agent-name] | [What context/data is passed] |

### Parallel (Works alongside)

| Agent | Collaboration Pattern |
|-------|----------------------|
| [agent-name] | [How they coordinate] |

## Output Format

[Reference an output style OR define inline template]

Reference:
```
Uses output style: [output-style-name]
```

Or inline:
```markdown
## [Section Title]

### Summary
[Brief summary of work done]

### Findings
- [Finding 1]
- [Finding 2]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]
```

## Success Criteria

Completion is achieved when:

- [ ] [Measurable criterion 1]
- [ ] [Measurable criterion 2]
- [ ] [Measurable criterion 3]
- [ ] No blocking issues remain
- [ ] User has been informed of results

## Value Delivery Tracking

Report these metrics on completion:

| Metric | Description |
|--------|-------------|
| [Metric 1] | [What is measured] |
| [Metric 2] | [What is measured] |
| [Metric 3] | [What is measured] |

Example metrics:
- Files analyzed: N
- Issues found: N (N critical, N warning)
- Time elapsed: Nm Ns
- Patterns identified: N

## Completion Signal

When finished, output:

```
✓ [AGENT-NAME] COMPLETE

[1-2 sentence summary]

Results:
- [Key result 1]
- [Key result 2]

Next: [Suggested next step or agent]
```

---

## Template Usage Notes

When creating a new agent from this template:

1. Replace all `[bracketed]` placeholders with actual values
2. Remove sections marked as optional if not needed
3. Add domain-specific content to Systematic Approach
4. Ensure Power Mode Integration section is complete
5. Define meaningful Circuit Breakers for the domain
6. Update agents/config.json with routing rules

For large agents (>500 lines):
- Extract reference materials to `references/` subdirectory
- Extract code examples to `references/examples.md`
- Keep AGENT.md focused on behavior, not reference data
