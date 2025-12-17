---
name: pdf-prd
description: Product Requirements Document formatted for PDF export
format: pdf
used_by:
  - researcher
  - user-story-writer
  - /popkit:design prd
---

# PDF PRD Style

## Purpose

Generate formal Product Requirements Documents suitable for PDF export and stakeholder review. Designed for product managers, engineers, and business stakeholders.

## Format

```markdown
---
title: "PRD: [Feature/Product Name]"
version: "[1.0]"
date: "[YYYY-MM-DD]"
author: "[Product Manager/Owner]"
status: "[Draft|In Review|Approved]"
---

# [Feature/Product Name]

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | YYYY-MM-DD | [name] | Initial draft |

---

# 1. Overview

## 1.1 Problem Statement

[Clearly describe the problem this feature/product solves. Include data or user research that validates the problem exists.]

## 1.2 Proposed Solution

[High-level description of the solution approach]

## 1.3 Goals & Success Metrics

| Goal | Metric | Target | Current |
|------|--------|--------|---------|
| [goal] | [metric] | [target] | [baseline] |

## 1.4 Non-Goals (Out of Scope)

- [Explicitly state what this PRD does NOT cover]
- [Prevents scope creep]

---

# 2. User Research

## 2.1 Target Users

| Persona | Description | Primary Need |
|---------|-------------|--------------|
| [Persona Name] | [Who they are] | [What they need] |

## 2.2 User Journey

```
[Current State] --> [Pain Point] --> [Proposed Solution] --> [Desired Outcome]
```

## 2.3 User Quotes/Evidence

> "[Quote from user research]"
> - User Type, Context

---

# 3. Requirements

## 3.1 Functional Requirements

### 3.1.1 [Requirement Name]

**Description:** [What the system must do]

**Acceptance Criteria:**
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]

**Priority:** [P0|P1|P2]

### 3.1.2 [Next Requirement]
...

## 3.2 Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Performance | [target] | [how measured] |
| Availability | [target] | [how measured] |
| Scalability | [target] | [how measured] |
| Security | [target] | [how measured] |

## 3.3 Constraints

- **Technical:** [constraints from existing architecture]
- **Business:** [budget, timeline, resources]
- **Regulatory:** [compliance requirements]

---

# 4. Design

## 4.1 User Flow

```
[Step 1] --> [Step 2] --> [Step 3] --> [Outcome]
```

## 4.2 Wireframes/Mockups

[Reference to design files or embedded images]

## 4.3 Information Architecture

```
Feature
├── Component A
│   ├── Sub-component 1
│   └── Sub-component 2
└── Component B
    └── Sub-component 3
```

## 4.4 API/Data Requirements

| Endpoint/Data | Type | Description |
|---------------|------|-------------|
| [endpoint] | [REST/GraphQL] | [what it does] |

---

# 5. Technical Approach

## 5.1 Architecture

[High-level architecture diagram or description]

## 5.2 Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| [dependency] | [Internal/External] | [High/Med/Low] | [plan] |

## 5.3 Migration/Rollout Plan

| Phase | Description | Duration | Risk |
|-------|-------------|----------|------|
| Phase 1 | [description] | [time] | [risk] |

---

# 6. Launch Plan

## 6.1 Rollout Strategy

- **Beta:** [who, when, what]
- **GA:** [who, when, what]
- **Full Rollout:** [who, when, what]

## 6.2 Feature Flags

| Flag | Purpose | Default |
|------|---------|---------|
| [flag_name] | [why needed] | [on/off] |

## 6.3 Success Criteria for Launch

- [ ] [Metric meets threshold]
- [ ] [No critical bugs]
- [ ] [Documentation complete]

---

# 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| [risk] | [H/M/L] | [H/M/L] | [plan] | [who] |

---

# 8. Timeline

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Design Complete | [date] | [status] |
| Development Complete | [date] | [status] |
| QA Complete | [date] | [status] |
| Launch | [date] | [status] |

---

# 9. Appendix

## A. Related Documents

- [Link to design spec]
- [Link to technical spec]
- [Link to user research]

## B. Glossary

| Term | Definition |
|------|------------|
| [term] | [definition] |

## C. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product | [name] | | |
| Engineering | [name] | | |
| Design | [name] | | |

---

*Generated via PopKit PRD workflow*
```

## PDF Styling Guidelines

### Professional Appearance
- Clean, business-appropriate formatting
- Clear hierarchy with numbered sections
- Tables for structured information
- Consistent typography throughout

### Print Considerations
- Page breaks before major sections
- Table of contents for documents > 10 pages
- Headers/footers with document title and page numbers
- Margins suitable for binding (1.25" left margin)

## When to Use

- Formal feature proposals
- Stakeholder presentations
- Product planning documentation
- Cross-team alignment documents
- Archival records

## Integration with Brainstorming

1. Use `/popkit:design brainstorm` to refine the idea
2. Generate PRD using this output style
3. Use `document-skills:pdf` to create final PDF
4. Store in `docs/prds/` directory

## PDF Input Support

This style also supports **reading existing PRDs**:

When given a PDF file path, extract and analyze:
- Current requirements (what's specified)
- Gaps (what's missing)
- Risks (what needs attention)
- Implementation readiness (can we start building?)
