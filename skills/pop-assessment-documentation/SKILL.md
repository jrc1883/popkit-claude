---
name: pop-assessment-documentation
description: "Validates PopKit documentation quality using concrete coverage metrics, accuracy checks, and freshness analysis"
triggers:
  - assess documentation
  - doc audit
  - documentation review
version: 1.0.0
---

# Documentation Assessment Skill

## Purpose

Provides concrete, reproducible documentation assessment for PopKit plugins using:
- Coverage metrics (percent documented)
- Accuracy validation (matches reality)
- Freshness analysis (up-to-date)
- Cross-reference verification

## How to Use

### Step 1: Run Automated Documentation Scan

```bash
python skills/pop-assessment-documentation/scripts/measure_coverage.py packages/plugin/
python skills/pop-assessment-documentation/scripts/validate_accuracy.py packages/plugin/
python skills/pop-assessment-documentation/scripts/calculate_doc_score.py packages/plugin/
```

### Step 2: Apply Documentation Checklists

Read and apply checklists in order:
1. `checklists/claude-md-requirements.json` - CLAUDE.md sections
2. `checklists/skill-documentation.json` - SKILL.md requirements
3. `checklists/agent-documentation.json` - AGENT.md requirements
4. `checklists/auto-generated-accuracy.json` - Count verification

### Step 3: Generate Report

Combine automated metrics with checklist results for final documentation report.

## Standards Reference

| Standard | File | Key Checks |
|----------|------|------------|
| CLAUDE.md Structure | `standards/claude-md-structure.md` | CM-001 through CM-012 |
| Skill Documentation | `standards/skill-documentation.md` | SKD-001 through SKD-008 |
| Agent Documentation | `standards/agent-documentation.md` | AGD-001 through AGD-012 |
| Command Documentation | `standards/command-documentation.md` | CMD-001 through CMD-008 |

## Coverage Targets

| Category | Target | Warning | Critical |
|----------|--------|---------|----------|
| Skills with SKILL.md | 100% | 90-99% | <90% |
| Agents with AGENT.md | 100% | 90-99% | <90% |
| Commands documented | 100% | 90-99% | <90% |
| Examples provided | >80% | 50-80% | <50% |
| Auto-gen accuracy | 100% | 95-99% | <95% |

## CLAUDE.md Required Sections

| Section | Check ID | Required |
|---------|----------|----------|
| Project Overview | CM-001 | Yes |
| Repository Structure | CM-002 | Yes |
| Development Notes | CM-003 | Yes |
| Key Architectural Patterns | CM-004 | Yes |
| Key Files Table | CM-005 | Yes |
| Version History | CM-006 | No |
| Conventions | CM-007 | Yes |

## Output

Returns JSON with:
- `doc_score`: 0-100 (higher = better)
- `coverage`: Percent of items documented
- `accuracy`: Percent matching reality
- `freshness`: Days since last update
- `gaps`: Missing documentation items
- `stale_docs`: Documents needing refresh
