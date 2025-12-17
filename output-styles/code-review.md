---
name: code-review
description: Structured code review with confidence levels and quality scoring
---

# Code Review Style

## Format

```markdown
## Code Review: [Feature/PR Name]

### Summary
<1-2 sentences on overall quality>

### Critical Issues (Must Fix)
_Issues with confidence 90+_

#### Issue 1: [Title]
- **File**: `path/to/file.ts:line`
- **Confidence**: 95/100
- **Category**: [Bug/Correctness|Simplicity/DRY|Conventions]
- **Description**: <what's wrong>
- **Fix**: <how to fix it>

### Important Issues (Should Fix)
_Issues with confidence 80-89_

#### Issue 2: [Title]
...

### Minor Issues (Consider)
_Issues with confidence 70-79, shown if --verbose_

### Strengths
- <What was done well>

### Assessment

**Ready to merge?** [Yes|No|With fixes]

**Reasoning**: <1-2 sentences>

### Quality Score: [X/10]
```

## Confidence Levels

| Score | Meaning | Action |
|-------|---------|--------|
| 90-100 | Absolutely certain | Must fix (Critical) |
| 80-89 | Highly confident | Should fix (Important) |
| 70-79 | Moderately confident | Consider (Minor) |
| 50-69 | Possibly valid | Note only |
| 0-49 | Not a real problem | Ignore |

**Default threshold: 80+**

## Categories

### Bug/Correctness
- Logic errors
- Edge case handling
- Type safety issues
- Error handling gaps
- Security vulnerabilities

### Simplicity/DRY
- Code duplication
- Unnecessary complexity
- Missed abstractions
- Overly clever code
- Dead code

### Conventions
- Project pattern compliance
- Naming conventions
- File organization
- Import patterns
- Documentation

## Quality Score

| Score | Description |
|-------|-------------|
| 10 | Exceptional - example code |
| 8-9 | Excellent - minor improvements |
| 6-7 | Good - some issues to address |
| 4-5 | Acceptable - needs work |
| 2-3 | Below standard - significant issues |
| 0-1 | Unacceptable - major problems |

## Example

```markdown
## Code Review: User Authentication

### Summary
Solid implementation with good test coverage. One critical security issue needs attention.

### Critical Issues (Must Fix)

#### Issue 1: SQL Injection Vulnerability
- **File**: `src/auth/login.ts:45`
- **Confidence**: 98/100
- **Category**: Bug/Correctness
- **Description**: User input directly concatenated into SQL query
- **Fix**: Use parameterized query: `db.query('SELECT * FROM users WHERE email = $1', [email])`

### Important Issues (Should Fix)

#### Issue 2: Duplicate Validation Logic
- **File**: `src/auth/register.ts:30-45`
- **Confidence**: 85/100
- **Category**: Simplicity/DRY
- **Description**: Email validation duplicated from `src/utils/validators.ts`
- **Fix**: Import and reuse `validateEmail()` from utils

### Strengths
- Comprehensive test coverage (95%)
- Clear separation of concerns
- Good error messages for users

### Assessment

**Ready to merge?** With fixes

**Reasoning**: Critical SQL injection must be fixed before merging. Other issues are improvements that can be addressed in this PR or follow-up.

### Quality Score: 7/10
```

## Filtering

Issues below threshold (80) are filtered unless:
- `--verbose` flag is used
- `--threshold N` overrides default
- Issue is in specified focus area
