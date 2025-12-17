---
description: "anthropic | security | performance | ux | architect | docs | all [--fix, --json]"
argument-hint: "<perspective> [options]"
---

# /popkit:assess - Multi-Perspective Self-Assessment

Run specialized assessor agents to review PopKit from different expert perspectives.

## Usage

```
/popkit:assess [assessor] [flags]
```

## Assessors

| Assessor | Description | Focus |
|----------|-------------|-------|
| `anthropic` | Anthropic Engineer | Claude Code compliance, hook protocols |
| `security` | Security Auditor | Vulnerabilities, secrets, injection |
| `performance` | Performance Tester | Token efficiency, context usage |
| `ux` | UX Reviewer | Command naming, discoverability |
| `architect` | Technical Architect | Code quality, DRY, patterns |
| `docs` | Documentation Auditor | CLAUDE.md, SKILL.md, AGENT.md |
| `all` | All Assessors | Complete assessment |

## Flags

| Flag | Description |
|------|-------------|
| `--fix` | Auto-fix issues where possible |
| `--json` | Output JSON instead of markdown |
| `--save FILE` | Save report to file |
| `--critical-only` | Only show critical issues |

## Examples

```bash
# Run all assessments
/popkit:assess all

# Run specific assessor
/popkit:assess security
/popkit:assess docs

# Get JSON output
/popkit:assess all --json

# Save report
/popkit:assess all --save reports/assessment-2025-01.md
```

## How It Works

### 1. Launch Assessor Agent

Each assessor type corresponds to a specialized agent in `agents/assessors/`:

| Command | Agent |
|---------|-------|
| `anthropic` | `anthropic-engineer-assessor` |
| `security` | `security-auditor-assessor` |
| `performance` | `performance-tester-assessor` |
| `ux` | `ux-reviewer-assessor` |
| `architect` | `technical-architect-assessor` |
| `docs` | `documentation-auditor-assessor` |

### 2. Run Assessment

The assessor agent:
1. Loads its specific checklist
2. Scans relevant files
3. Evaluates against criteria
4. Records findings with severity

### 3. Generate Report

Produces a report with:
- Overall score (0-100)
- Findings by severity (Critical, High, Medium, Low)
- Specific recommendations
- Commendations for things done well

## Report Format

```markdown
# PopKit Self-Assessment Report

**Generated:** 2025-01-15T10:30:00
**Overall Score:** 85/100

## Summary

| Assessor | Score | Critical | High | Warnings | Passed |
|----------|-------|----------|------|----------|--------|
| anthropic | 92/100 | 0 | 1 | 3 | 45 |
| security | 88/100 | 0 | 2 | 5 | 38 |
| docs | 75/100 | 1 | 3 | 8 | 52 |

## Critical Issues

### [docs] Missing SKILL.md in pop-new-skill
- **Severity**: Critical
- **File**: skills/pop-new-skill/
- **Recommendation**: Add SKILL.md with frontmatter

## Recommendations

1. **Immediate**: Fix critical documentation gaps
2. **Short-term**: Address hook error handling
3. **Long-term**: Improve test coverage
```

## Scoring

Scores are calculated based on findings:

| Finding Type | Deduction |
|--------------|-----------|
| Critical | -20 points |
| High | -10 points |
| Medium | -5 points |
| Low | -2 points |
| Warning | -1 point |

Starting from 100, deductions are applied up to a minimum of 0.

## Auto-Fix Mode

With `--fix`, certain issues can be automatically resolved:

| Issue Type | Auto-Fix Action |
|------------|-----------------|
| Missing frontmatter | Generate from filename |
| Outdated counts | Recalculate from files |
| Missing sections | Add template sections |
| Version mismatch | Sync with plugin.json |

Issues that cannot be auto-fixed are marked for manual attention.

## Integration

### Running Programmatically

```python
from tests.assessments.assessment_runner import AssessmentRunner
from pathlib import Path

runner = AssessmentRunner(Path("packages/plugin"))
results = runner.run_all()
print(f"Overall Score: {runner.get_overall_score()}/100")
```

### CI Integration

Add to GitHub Actions:

```yaml
- name: Run PopKit Self-Assessment
  run: python tests/assessments/assessment_runner.py all --json > assessment.json

- name: Check for Critical Issues
  run: |
    critical=$(jq '.results[].findings[] | select(.severity == "critical")' assessment.json)
    if [ -n "$critical" ]; then
      echo "Critical issues found!"
      exit 1
    fi
```

## Executable Commands

When this command is invoked:

```bash
# For specific assessor
python tests/assessments/assessment_runner.py {assessor}

# For all assessors
python tests/assessments/assessment_runner.py all

# With JSON output
python tests/assessments/assessment_runner.py all --json

# Or invoke assessor agents directly via Task tool
# See agents/assessors/ for full agent definitions
```

## Related

- `agents/assessors/` - Assessor agent definitions
- `tests/assessments/assessment_runner.py` - Python runner
- `tests/run_tests.py` - General test runner
- `/popkit:plugin test` - Plugin structure tests
