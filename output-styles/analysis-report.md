---
name: analysis-report
description: Codebase analysis findings with architecture, patterns, and recommendations
used_by:
  - researcher
  - code-explorer
  - /popkit:analyze-project
---

# Analysis Report Style

## Purpose

Document comprehensive codebase analysis including architecture, patterns, dependencies, quality metrics, and improvement opportunities.

## Format

```markdown
## Analysis Report: [Project/Feature Name]

**Scope:** [Full codebase|Module|Feature]
**Date:** [YYYY-MM-DD]
**Analyst:** [agent-name]

---

### Executive Summary

**Health Score:** [0-100] [emoji indicator]

| Metric | Score | Status |
|--------|-------|--------|
| Architecture | [0-10] | [emoji] |
| Code Quality | [0-10] | [emoji] |
| Test Coverage | [0-10] | [emoji] |
| Documentation | [0-10] | [emoji] |
| Security | [0-10] | [emoji] |

**Key Finding:** [One sentence summary of most important discovery]

---

### Architecture Overview

#### Tech Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | [React/Vue/etc] | [version] |
| Backend | [Node/Python/etc] | [version] |
| Database | [PostgreSQL/etc] | [version] |
| Cache | [Redis/etc] | [version] |

#### Directory Structure
```
project/
├── src/
│   ├── components/    # [description]
│   ├── services/      # [description]
│   ├── utils/         # [description]
│   └── types/         # [description]
├── tests/             # [description]
└── docs/              # [description]
```

#### Key Entry Points
| Entry Point | File | Purpose |
|-------------|------|---------|
| Main | `src/index.ts` | Application entry |
| API | `src/api/index.ts` | API routes |
| CLI | `src/cli/index.ts` | CLI commands |

---

### Patterns Identified

#### Design Patterns

| Pattern | Location | Usage |
|---------|----------|-------|
| [Repository] | `src/repos/` | Database access abstraction |
| [Factory] | `src/factories/` | Object creation |
| [Observer] | `src/events/` | Event handling |

#### Architectural Patterns

| Pattern | Implementation | Notes |
|---------|---------------|-------|
| [MVC/MVVM/etc] | [where] | [notes] |
| [Microservices/Monolith] | [where] | [notes] |
| [Event-driven] | [where] | [notes] |

#### Code Conventions

| Convention | Example | Consistency |
|------------|---------|-------------|
| Naming | camelCase for vars | 95% |
| File structure | feature-based | 90% |
| Error handling | try/catch with logging | 80% |

---

### Dependencies Analysis

#### Production Dependencies ([count])

| Package | Version | Purpose | Risk |
|---------|---------|---------|------|
| [package] | [ver] | [why] | [Low/Med/High] |

**Top 5 by size:**
1. [package] - [size]
2. [package] - [size]

#### Security Vulnerabilities

| Severity | Count | Action |
|----------|-------|--------|
| Critical | [n] | Immediate fix required |
| High | [n] | Fix this sprint |
| Medium | [n] | Schedule fix |
| Low | [n] | Monitor |

**Critical Issues:**
- [package@version]: [vulnerability description]

---

### Code Quality Metrics

#### Complexity Analysis

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Avg Cyclomatic Complexity | [n] | <10 | [emoji] |
| Max Cyclomatic Complexity | [n] | <20 | [emoji] |
| Lines of Code | [n] | - | - |
| Code Duplication | [n]% | <5% | [emoji] |

#### Hotspots (High Complexity)

| File | Complexity | Lines | Recommendation |
|------|------------|-------|----------------|
| `src/path/file.ts` | [n] | [n] | Refactor |

#### Technical Debt

| Category | Count | Effort |
|----------|-------|--------|
| TODO comments | [n] | [hours] |
| FIXME comments | [n] | [hours] |
| Deprecated APIs | [n] | [hours] |
| Missing types | [n] | [hours] |

---

### Test Coverage

#### Coverage Summary

| Metric | Percentage | Status |
|--------|------------|--------|
| Statements | [n]% | [emoji] |
| Branches | [n]% | [emoji] |
| Functions | [n]% | [emoji] |
| Lines | [n]% | [emoji] |

#### Untested Areas

| Area | Risk | Recommendation |
|------|------|----------------|
| `src/critical/path.ts` | High | Add tests immediately |
| `src/utils/helpers.ts` | Medium | Add tests this sprint |

---

### Recommendations

#### Critical (Do Immediately)

1. **[Title]**
   - **What:** [action]
   - **Why:** [reason]
   - **How:** [approach]
   - **Effort:** [hours/days]

#### High Priority (This Sprint)

1. **[Title]**
   - **What:** [action]
   - **Why:** [reason]
   - **Effort:** [hours/days]

#### Medium Priority (Backlog)

1. **[Title]**
   - **What:** [action]
   - **Why:** [reason]

#### Nice to Have

1. [suggestion]
2. [suggestion]

---

### Agent Opportunities

Based on this analysis, these agents would be valuable:

| Agent | Why | Priority |
|-------|-----|----------|
| [agent-name] | [reason] | High |
| [agent-name] | [reason] | Medium |

---

### Next Steps

1. [ ] [Immediate action]
2. [ ] [Short-term action]
3. [ ] [Long-term action]

---

**Analysis Confidence:** [0-100]
**Recommended Follow-up:** [agent-name or action]
```

## Health Score Calculation

| Metric | Weight | Scoring |
|--------|--------|---------|
| Architecture | 20% | Clean separation, clear patterns |
| Code Quality | 25% | Low complexity, minimal duplication |
| Test Coverage | 25% | >80% coverage, critical paths tested |
| Documentation | 15% | README, API docs, inline comments |
| Security | 15% | No vulnerabilities, secure patterns |

## Status Indicators

| Score | Emoji | Meaning |
|-------|-------|---------|
| 9-10 | 🟢 | Excellent |
| 7-8 | 🟡 | Good |
| 5-6 | 🟠 | Needs attention |
| 0-4 | 🔴 | Critical issues |

## Example: E-Commerce Analysis

```markdown
## Analysis Report: Reseller Central

**Scope:** Full codebase
**Date:** 2025-01-28
**Analyst:** researcher

---

### Executive Summary

**Health Score:** 72/100 🟡

| Metric | Score | Status |
|--------|-------|--------|
| Architecture | 8/10 | 🟢 |
| Code Quality | 7/10 | 🟡 |
| Test Coverage | 6/10 | 🟠 |
| Documentation | 7/10 | 🟡 |
| Security | 8/10 | 🟢 |

**Key Finding:** Strong architecture with clean separation, but test coverage is below target (62% vs 80% goal) especially in critical inventory sync paths.

---

### Architecture Overview

#### Tech Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Next.js | 14.0.4 |
| Backend | Node.js | 20.10.0 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7.2 |
| Queue | BullMQ | 5.0 |

#### Key Entry Points
| Entry Point | File | Purpose |
|-------------|------|---------|
| Web App | `src/app/page.tsx` | Main dashboard |
| API | `src/app/api/` | REST endpoints |
| Workers | `src/workers/` | Background jobs |
| CLI | `src/cli/index.ts` | Admin commands |

---

### Patterns Identified

#### Design Patterns

| Pattern | Location | Usage |
|---------|----------|-------|
| Repository | `src/repos/` | Database abstraction |
| Service Layer | `src/services/` | Business logic |
| Queue/Worker | `src/workers/` | Async processing |
| Adapter | `src/adapters/` | eBay API integration |

---

### Recommendations

#### Critical (Do Immediately)

1. **Add tests for inventory sync**
   - **What:** Unit and integration tests for `src/services/inventory-sync.ts`
   - **Why:** Critical path with 0% coverage, high bug risk
   - **Effort:** 4 hours

#### High Priority (This Sprint)

1. **Fix Redis connection handling**
   - **What:** Add retry logic and connection pooling
   - **Why:** Intermittent connection drops in logs
   - **Effort:** 2 hours

---

### Agent Opportunities

| Agent | Why | Priority |
|-------|-----|----------|
| test-writer-fixer | Low coverage in critical paths | High |
| performance-optimizer | Redis connection issues | Medium |
| query-optimizer | Some N+1 queries detected | Medium |

---

**Analysis Confidence:** 85
**Recommended Follow-up:** test-writer-fixer for inventory sync coverage
```

## Integration

### In Agent Definition

```yaml
---
name: researcher
output_style: analysis-report
---
```
