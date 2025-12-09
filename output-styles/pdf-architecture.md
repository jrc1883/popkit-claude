---
name: pdf-architecture
description: Architecture Decision Record (ADR) formatted for PDF export
format: pdf
used_by:
  - code-architect
  - researcher
  - /popkit:design
---

# PDF Architecture Style

## Purpose

Generate Architecture Decision Records (ADRs) and technical specifications suitable for PDF export. Designed for engineering teams, technical stakeholders, and documentation archives.

## Format

```markdown
---
title: "ADR-[NNN]: [Decision Title]"
date: "[YYYY-MM-DD]"
status: "[Proposed|Accepted|Deprecated|Superseded]"
deciders: "[List of people involved]"
supersedes: "[ADR-XXX if applicable]"
superseded_by: "[ADR-YYY if applicable]"
---

# ADR-[NNN]: [Decision Title]

## Status

[Proposed|Accepted|Deprecated|Superseded by ADR-XXX]

Date: [YYYY-MM-DD]

---

## Context

[Describe the forces at play, including technological, political, social, and project local. This section describes the situation we were in and the problem we needed to solve.]

### Current State

[Describe how things work today]

### Problem Statement

[Clearly state what problem needs solving]

### Constraints

- [Technical constraints]
- [Business constraints]
- [Time constraints]
- [Resource constraints]

---

## Decision Drivers

1. **[Driver 1]** - [Why this matters]
2. **[Driver 2]** - [Why this matters]
3. **[Driver 3]** - [Why this matters]

---

## Considered Options

### Option 1: [Name]

**Description:** [What this option entails]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Estimated Effort:** [Low|Medium|High]

### Option 2: [Name]

**Description:** [What this option entails]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Estimated Effort:** [Low|Medium|High]

### Option 3: [Name]
...

---

## Decision

**Chosen Option:** [Option Name]

**Rationale:**
[Explain why this option was selected over the alternatives. Reference the decision drivers and how this option best addresses them.]

---

## Consequences

### Positive

- [Positive consequence 1]
- [Positive consequence 2]

### Negative

- [Negative consequence 1]
- [Tradeoff we're accepting]

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [risk] | [H/M/L] | [H/M/L] | [mitigation] |

---

## Implementation

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐
│  Component  │────▶│  Component  │
│      A      │     │      B      │
└─────────────┘     └─────────────┘
        │                   │
        ▼                   ▼
┌─────────────────────────────────┐
│          Shared Service          │
└─────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| [component] | [what it does] | [tech stack] |

### Data Flow

```
[Input] → [Process 1] → [Process 2] → [Output]
```

### Migration Path

| Phase | Description | Timeline | Risk |
|-------|-------------|----------|------|
| 1 | [phase 1] | [time] | [risk] |
| 2 | [phase 2] | [time] | [risk] |

---

## Validation

### Success Criteria

- [ ] [Measurable criterion 1]
- [ ] [Measurable criterion 2]
- [ ] [Measurable criterion 3]

### Testing Strategy

| Test Type | Scope | Approach |
|-----------|-------|----------|
| Unit | [scope] | [how] |
| Integration | [scope] | [how] |
| Performance | [scope] | [how] |

---

## Related Documents

- [Link to related ADR]
- [Link to PRD]
- [Link to design docs]

---

## Appendix

### A. Technical Details

[Extended technical specifications, code examples, or configuration]

### B. References

1. [External reference 1]
2. [External reference 2]

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [date] | [author] | Initial version |

---

*Architecture decision documented via PopKit*
*Review Status: [Pending|Approved|Needs Revision]*
```

## Lightweight ADR Format

For smaller decisions, use this condensed format:

```markdown
# ADR-[NNN]: [Decision Title]

**Date:** [YYYY-MM-DD]
**Status:** [Proposed|Accepted|Deprecated]

## Context
[Why we need to make this decision]

## Decision
[What we decided to do]

## Consequences
[What happens as a result]
```

## PDF Styling Guidelines

### Technical Documentation Style
- Clear section numbering (1, 1.1, 1.1.1)
- ASCII diagrams or high-resolution images
- Code blocks with syntax highlighting
- Tables for structured comparisons

### Diagram Best Practices
- ASCII art for simple diagrams (portable, text-searchable)
- Mermaid or PlantUML for complex diagrams (generate images)
- Include diagram source in appendix for editability

## When to Use

- Major architectural decisions
- Technology selection
- Infrastructure changes
- API design decisions
- Breaking changes to existing systems

## PDF Input Support

This style supports **reading existing architecture documents**:

When given a PDF file path containing architecture specs:
- Extract decision context and constraints
- Identify architectural patterns in use
- Map to PopKit agent recommendations
- Generate implementation plan from architecture

### Example PDF Analysis

```markdown
## PDF Analysis: system-architecture.pdf

**Document Type:** Architecture Specification
**Pages Analyzed:** 15

### Extracted Architecture

**Pattern:** Microservices with Event-Driven Communication
**Key Services:**
- User Service (authentication, profiles)
- Order Service (cart, checkout, fulfillment)
- Inventory Service (stock, synchronization)

### Recommended Agents

| Phase | Agent | Reasoning |
|-------|-------|-----------|
| Implementation | api-designer | Define service contracts |
| Data Layer | query-optimizer | Database per service |
| Integration | devops-automator | Service mesh setup |

### Missing Elements
- No disaster recovery plan
- Message queue selection not specified
- Monitoring strategy undefined
```

## Integration with Code Architect Agent

The `code-architect` agent uses this style for:
1. Designing new features
2. Evaluating architectural options
3. Documenting decisions
4. Creating implementation blueprints

```yaml
---
name: code-architect
output_style: pdf-architecture
accepts_input:
  - pdf  # Architecture PDFs
  - md   # Design docs
---
```
