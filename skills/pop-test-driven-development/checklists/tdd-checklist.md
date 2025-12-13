# TDD Checklist

Use this checklist to ensure proper TDD discipline during development.

## Pre-TDD Setup

- [ ] Understand the requirement clearly
- [ ] Test framework is configured and working
- [ ] Know where test files should go
- [ ] Have a running test command (`npm test`, `pytest`, etc.)

---

## RED Phase Checklist

### Before Writing Test
- [ ] No production code written yet for this feature
- [ ] Clear understanding of what behavior to test
- [ ] Test file location decided

### Test Quality
- [ ] Test name describes expected behavior
  - Good: `test_empty_email_returns_validation_error`
  - Bad: `test_email` or `test1`
- [ ] Test has exactly one assertion (or closely related assertions)
- [ ] Test uses real objects where possible (not mocks)
- [ ] Test demonstrates desired API usage

### After Writing Test
- [ ] **RAN THE TEST** (mandatory!)
- [ ] Test FAILS (not errors)
- [ ] Failure message is clear and expected
- [ ] Failure is because feature is missing (not typo/syntax error)

### Red Phase Violations (STOP if any are true)
- [ ] Test passes immediately → Fix the test
- [ ] Test has syntax errors → Fix syntax first
- [ ] Production code already exists → Delete it, start over
- [ ] Can't explain why test fails → Understand before proceeding

---

## GREEN Phase Checklist

### Implementation Approach
- [ ] Writing MINIMAL code to pass the test
- [ ] Not adding features beyond what test requires
- [ ] Not refactoring other code yet
- [ ] Not adding "nice to have" functionality

### Code Quality (minimal for now)
- [ ] Code compiles/runs without errors
- [ ] Code makes the test pass
- [ ] No obvious bugs introduced

### After Implementation
- [ ] **RAN THE TEST** (mandatory!)
- [ ] Test PASSES
- [ ] All other tests still pass
- [ ] No warnings or errors in output

### Green Phase Violations (STOP if any are true)
- [ ] Test still fails → Fix implementation, not test
- [ ] Other tests broke → Fix regression immediately
- [ ] Added extra features → Remove them

---

## REFACTOR Phase Checklist

### Refactoring Candidates
- [ ] Duplicate code that can be extracted
- [ ] Poor variable/function names
- [ ] Long methods that should be split
- [ ] Complex conditionals that can be simplified
- [ ] Magic numbers to replace with constants

### Refactoring Rules
- [ ] Only refactoring, not adding behavior
- [ ] Running tests after each small change
- [ ] Keeping all tests green throughout

### After Refactoring
- [ ] **RAN ALL TESTS** (mandatory!)
- [ ] All tests still pass
- [ ] Code is cleaner than before
- [ ] No new behavior added

### Refactor Phase Violations
- [ ] Tests started failing → Undo last change
- [ ] Added new functionality → That needs its own RED phase

---

## Cycle Completion Checklist

Before marking a TDD cycle complete:

- [ ] Test exists and is meaningful
- [ ] Watched test fail before implementation
- [ ] Implementation is minimal and correct
- [ ] Refactoring completed (or consciously skipped)
- [ ] All tests pass
- [ ] Ready to commit

---

## Common Violations to Watch For

### "I Already Wrote Some Code"
**Symptom:** Existing implementation code when starting test
**Fix:** Delete the code. Start fresh with TDD.

### "Test Passes Immediately"
**Symptom:** New test passes without writing implementation
**Fix:** Either testing existing behavior (add different test) or test is wrong (fix it)

### "Just This Once"
**Symptom:** Rationalizing skipping TDD for "simple" code
**Fix:** Simple code is fastest to TDD. Do it properly.

### "I'll Add Tests After"
**Symptom:** Implementation exists, planning to test later
**Fix:** Delete implementation. Test-first proves the test catches the bug.

### "Keep As Reference"
**Symptom:** Want to keep code you wrote to "guide" TDD
**Fix:** You'll copy it instead of TDD. Delete means delete.

### "Test Is Hard To Write"
**Symptom:** Struggling to write a test
**Fix:** This is valuable feedback! Hard to test = hard to use. Redesign the API.

---

## Anti-Pattern Detection

Watch for these patterns and correct immediately:

| Pattern | Detection | Fix |
|---------|-----------|-----|
| Mock everything | Test has 5+ mocks | Use real objects, mock only external deps |
| Test implementation | Asserting on private methods | Test public behavior only |
| Test-per-method | `testMethodName()` pattern | Test behaviors, not methods |
| Setup soup | 50+ lines of setup | Extract fixtures, simplify design |
| Assertion-free | Test runs but asserts nothing | Add meaningful assertions |
| Sleep-based | `Thread.sleep()` or `await delay()` | Use condition-based waiting |

---

## Coverage Checkpoints

### Minimum Coverage
- [ ] Happy path tested
- [ ] At least one error case tested
- [ ] Boundary conditions tested (empty, null, zero)

### Good Coverage
- [ ] All code paths exercised
- [ ] Edge cases covered
- [ ] Error handling verified
- [ ] Integration points tested

### Excellent Coverage
- [ ] Property-based tests where applicable
- [ ] Performance-sensitive paths benchmarked
- [ ] Concurrent scenarios tested
- [ ] Failure recovery tested

---

## TDD Discipline Score

Calculate your discipline score:

| Metric | Points |
|--------|--------|
| Started with test | +10 |
| Test failed first | +10 |
| Minimal implementation | +10 |
| Refactored after green | +5 |
| All tests pass | +10 |
| No violations | +5 |

**Score Interpretation:**
- 50: Perfect TDD
- 40-49: Good TDD
- 30-39: Needs improvement
- <30: Not really TDD

Track your score across cycles to improve discipline over time.
