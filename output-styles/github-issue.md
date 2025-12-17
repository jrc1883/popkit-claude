---
name: github-issue
description: AI-executable GitHub issue format with context, objectives, and acceptance criteria
---

# GitHub Issue Style

## Format

```markdown
## Context
<Background information needed to understand the issue>

## Objective
<Clear statement of what needs to be done>

## Requirements
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

## Technical Notes
<Implementation hints, relevant files, patterns to follow>

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Agent Routing
Suggested agents: <agent-names based on issue type>
```

## Sections

### Context
- Why this issue exists
- Related features or systems
- User impact or business need
- Don't assume reader knows the codebase

### Objective
- One clear sentence
- Starts with a verb
- Measurable outcome

### Requirements
- Checkboxes for trackability
- Specific and actionable
- Prioritized (P0 first)

### Technical Notes
- Relevant file paths
- Patterns to follow
- Dependencies or blockers
- Edge cases to consider

### Acceptance Criteria
- How to verify completion
- Testable conditions
- Edge cases covered

### Agent Routing
- Suggest appropriate AI agents
- Based on issue type and content

## Templates

### Bug Report

```markdown
## Context
Users are reporting that [feature] is [broken behavior] when [condition].

First reported: [date]
Frequency: [always/sometimes/rare]
Impact: [number of users affected]

## Objective
Fix the [specific bug] so that [expected behavior].

## Requirements
- [ ] Identify root cause
- [ ] Write failing test
- [ ] Implement fix
- [ ] Verify fix in all environments

## Technical Notes
- Error occurs in: `src/feature/component.ts:45`
- Related to: #previous-issue
- Logs show: [relevant error]

## Acceptance Criteria
- [ ] Bug no longer reproduces
- [ ] Regression test added
- [ ] No new bugs introduced

## Agent Routing
Suggested agents: bug-whisperer, test-writer-fixer
```

### Feature Request

```markdown
## Context
As a [user type], I need [capability] because [reason].

Related to: [epic/milestone]

## Objective
Implement [feature] that allows users to [action].

## Requirements
- [ ] Design component/API
- [ ] Implement core functionality
- [ ] Add tests
- [ ] Update documentation

## Technical Notes
- Similar feature: `src/existing/feature.ts`
- API pattern: REST with standard responses
- UI pattern: Form with validation

## Acceptance Criteria
- [ ] Feature works as specified
- [ ] Edge cases handled
- [ ] Tests pass (unit + integration)
- [ ] Documentation updated

## Agent Routing
Suggested agents: api-designer, code-reviewer
```

### Task

```markdown
## Context
Part of [epic/project]. This task [relationship to other work].

## Objective
[Specific deliverable] for [purpose].

## Requirements
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Technical Notes
- Files to modify: [list]
- Follow pattern in: [reference]

## Acceptance Criteria
- [ ] All steps complete
- [ ] Code reviewed
- [ ] Tests pass

## Agent Routing
Suggested agents: [based on task type]
```
