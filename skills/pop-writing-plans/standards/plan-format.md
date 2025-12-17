# Implementation Plan Format Standard

This document defines the required structure and conventions for implementation plans created by the `pop-writing-plans` skill.

## File Naming

Plans MUST be saved to: `docs/plans/YYYY-MM-DD-<feature-name>.md`

Examples:
- `docs/plans/2025-12-12-user-authentication.md`
- `docs/plans/2025-12-12-api-rate-limiting.md`

## Required Header

Every plan MUST start with this header structure:

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Header Field Requirements

| Field | Required | Description |
|-------|----------|-------------|
| Title | Yes | Must include "Implementation Plan" |
| Claude instruction | Yes | Reference to executing-plans skill |
| Goal | Yes | Single sentence, specific outcome |
| Architecture | Yes | High-level approach, 2-3 sentences |
| Tech Stack | Yes | List of key technologies |

## Task Structure

Each task follows this format:

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: [Action]**
[Details with code blocks]

**Step 2: [Action]**
[Details]

**Step N: Commit**
```bash
git add [files]
git commit -m "type: description"
```
```

### Task Requirements

1. **Numbered sequentially** starting from 1
2. **Files section** lists all files touched
3. **Steps are atomic** (2-5 minutes each)
4. **Each task ends with commit**

## Step Granularity

Steps should be bite-sized (2-5 minutes):

| Good Steps | Bad Steps |
|------------|-----------|
| "Write the failing test" | "Implement the feature" |
| "Run test to verify failure" | "Add tests" |
| "Implement minimal code" | "Build the module" |
| "Run test to verify pass" | "Test everything" |
| "Commit changes" | "Finalize" |

## Code Block Requirements

All code blocks MUST have language specifiers:

```markdown
<!-- Good -->
```python
def example():
    pass
```

<!-- Bad -->
```
def example():
    pass
```
```

Common language specifiers:
- `python`, `typescript`, `javascript`, `bash`, `json`, `yaml`, `markdown`

## File Path Requirements

### Must Be Specific

```markdown
<!-- Good -->
- Create: `src/auth/validators.py`
- Modify: `packages/plugin/hooks/pre-tool-use.py:45-67`

<!-- Bad -->
- Create: `path/to/file.py`
- Modify: `your/file.py`
- Create: `[insert path here]`
```

### Forbidden Placeholders

These patterns are invalid:
- `path/to/`
- `your/`
- `example/`
- `[path]`
- `<path>`
- `xxx`
- `.../`

## Run Commands

Run commands should include expected output:

```markdown
**Step 4: Verify tests pass**

Run: `pytest tests/auth/test_validators.py -v`
Expected: All tests PASS (3 passed)
```

### Expected Output Patterns

| Pattern | Usage |
|---------|-------|
| `PASS` / `FAIL` | Test results |
| `Expected: [specific output]` | Command output |
| Error message quotes | Failure verification |

## Commit Message Convention

Follow conventional commits:

```bash
git commit -m "type(scope): description"
```

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring |
| `test` | Test changes |
| `docs` | Documentation |
| `chore` | Maintenance |

## TDD Pattern

Plans should follow Red-Green-Refactor:

```markdown
**Step 1: Write failing test**
[Test code]

**Step 2: Run to verify failure**
Run: `pytest path/to/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Implement minimal code**
[Implementation]

**Step 4: Run to verify pass**
Run: `pytest path/to/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**
```

## Validation

Plans can be validated using the validator script:

```bash
python scripts/validate_plan.py docs/plans/YYYY-MM-DD-feature.md
```

### Validation Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Missing Goal/Architecture/Tech Stack | Error | Required header fields |
| No tasks found | Error | Must have `### Task N:` format |
| Placeholder file paths | Error | No generic paths |
| Missing Files section | Warning | Tasks should list files |
| No numbered steps | Warning | Tasks need `**Step N:**` |
| Missing commit step | Info | Each task should commit |
| Code blocks without language | Warning | Add language specifier |
| Run commands without expected | Info | Add expected output |

### Score Calculation

- Base score: 100
- Each error: -20 points
- Each warning: -5 points
- Pass threshold: 60+ with no errors

## Cross-References

Plans may reference other skills using @ syntax:

```markdown
After implementing, use @pop-code-review for quality check.
```

## Complete Example

```markdown
# User Authentication Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** Add JWT-based user authentication with login/logout endpoints.

**Architecture:** Stateless JWT tokens stored client-side, bcrypt password hashing,
middleware for protected routes. Uses existing User model.

**Tech Stack:** Python 3.11, FastAPI, PyJWT, bcrypt, pytest

---

### Task 1: Password Hashing Utilities

**Files:**
- Create: `src/auth/password.py`
- Test: `tests/auth/test_password.py`

**Step 1: Write failing test for hash_password**

```python
import pytest
from src.auth.password import hash_password, verify_password

def test_hash_password_returns_different_value():
    password = "secret123"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 50
```

**Step 2: Run test to verify failure**

Run: `pytest tests/auth/test_password.py::test_hash_password_returns_different_value -v`
Expected: FAIL with "No module named 'src.auth.password'"

**Step 3: Implement hash_password**

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()
```

**Step 4: Run test to verify pass**

Run: `pytest tests/auth/test_password.py::test_hash_password_returns_different_value -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/auth/password.py tests/auth/test_password.py
git commit -m "feat(auth): add password hashing utility"
```

### Task 2: JWT Token Generation
...
```
