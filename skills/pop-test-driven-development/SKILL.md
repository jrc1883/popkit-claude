---
name: test-driven-development
description: "RED-GREEN-REFACTOR workflow that writes tests before implementation code. Ensures tests actually verify behavior by requiring them to fail first, then writing minimal code to pass. Use when implementing features, fixing bugs, or when test coverage matters. Do NOT use for exploratory coding, prototypes, or throwaway scripts where test overhead isn't justified."
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask user):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor

### RED - Write Failing Test

Write one minimal test showing what should happen.

**Good:**
```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);

  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```
Clear name, tests real behavior, one thing

**Bad:**
```typescript
test('retry works', async () => {
  const mock = jest.fn()
    .mockRejectedValueOnce(new Error())
    .mockRejectedValueOnce(new Error())
    .mockResolvedValueOnce('success');
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(3);
});
```
Vague name, tests mock not code

**Requirements:**
- One behavior
- Clear name
- Real code (no mocks unless unavoidable)

### Verify RED - Watch It Fail

**MANDATORY. Never skip.**

```bash
npm test path/to/test.test.ts
```

Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature missing (not typos)

**Test passes?** You're testing existing behavior. Fix test.

**Test errors?** Fix error, re-run until it fails correctly.

### GREEN - Minimal Code

Write simplest code to pass the test.

**Good:**
```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
  throw new Error('unreachable');
}
```
Just enough to pass

**Bad:**
```typescript
async function retryOperation<T>(
  fn: () => Promise<T>,
  options?: {
    maxRetries?: number;
    backoff?: 'linear' | 'exponential';
    onRetry?: (attempt: number) => void;
  }
): Promise<T> {
  // YAGNI
}
```
Over-engineered

Don't add features, refactor other code, or "improve" beyond the test.

### Verify GREEN - Watch It Pass

**MANDATORY.**

```bash
npm test path/to/test.test.ts
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix code, not test.

**Other tests fail?** Fix now.

### REFACTOR - Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

### Repeat

Next failing test for next feature.

## Good Tests

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One thing. "and" in name? Split it. | `test('validates email and domain and whitespace')` |
| **Clear** | Name describes behavior | `test('test1')` |
| **Shows intent** | Demonstrates desired API | Obscures what code should do |

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc != systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for existing code. |

## Red Flags - STOP and Start Over

- Code before test
- Test after implementation
- Test passes immediately
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## Example: Bug Fix

**Bug:** Empty email accepted

**RED**
```typescript
test('rejects empty email', async () => {
  const result = await submitForm({ email: '' });
  expect(result.error).toBe('Email required');
});
```

**Verify RED**
```bash
$ npm test
FAIL: expected 'Email required', got undefined
```

**GREEN**
```typescript
function submitForm(data: FormData) {
  if (!data.email?.trim()) {
    return { error: 'Email required' };
  }
  // ...
}
```

**Verify GREEN**
```bash
$ npm test
PASS
```

**REFACTOR**
Extract validation for multiple fields if needed.

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## Condition-Based Waiting

Flaky tests often use arbitrary delays:

```typescript
// BAD - Guessing at timing
await page.click('#submit');
await sleep(2000);  // Hope it's enough
expect(await page.textContent('#result')).toBe('Success');
```

**Replace with condition polling:**

```typescript
// GOOD - Wait for actual state
await page.click('#submit');
await waitForCondition(
  () => page.textContent('#result') === 'Success',
  { timeout: 5000, interval: 100 }
);
```

**Implementation pattern:**

```typescript
async function waitForCondition(
  check: () => boolean | Promise<boolean>,
  options: { timeout: number; interval: number }
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < options.timeout) {
    if (await check()) return;
    await sleep(options.interval);
  }
  throw new Error('Condition not met within timeout');
}
```

**When to use:**
- DOM element appears/changes
- API response arrives
- State updates propagate
- File written to disk
- Process completes

**Determinism check:** Run test 5x locally. Must pass 5/5. If not, fix the wait condition.

---

## Testing Anti-Patterns to Avoid

### Anti-Pattern 1: Mocking What You're Testing

```typescript
// BAD - Tests the mock, not the code
const mockCalculator = { add: jest.fn().mockReturnValue(5) };
expect(mockCalculator.add(2, 3)).toBe(5);
// Proves nothing about real Calculator
```

**Fix:** Test real implementation. Mock only external dependencies.

### Anti-Pattern 2: Test-Only Methods in Production

```typescript
// BAD - Pollutes production with test scaffolding
class UserService {
  private users: User[] = [];

  // Added just for tests
  _resetForTesting() { this.users = []; }
  _getUsersForTesting() { return this.users; }
}
```

**Fix:** Use proper test isolation (fresh instance per test, dependency injection).

### Anti-Pattern 3: Over-Specific Implementation Assertions

```typescript
// BAD - Tests implementation, not behavior
test('saves user', () => {
  saveUser(user);
  expect(db.query).toHaveBeenCalledWith(
    'INSERT INTO users (id, name) VALUES (?, ?)',
    [user.id, user.name]
  );
});
```

**Fix:** Test observable behavior (user exists after save), not SQL string matching.

### Anti-Pattern 4: Sleep-Based Waits

```typescript
// BAD - Arbitrary timing
await submitForm();
await sleep(1000);  // "Should be enough"
expect(result).toBeDefined();
```

**Fix:** Use condition-based waiting (see section above).

### Anti-Pattern 5: Incomplete Mocks

```typescript
// BAD - Missing fields the code depends on
const mockResponse = { data: { id: 1 } };
// Real API returns { data: { id, name, email, createdAt } }
// Code breaks on response.data.email
```

**Fix:** Mock complete shapes. Use TypeScript to enforce completeness.

---

## Cross-References

- **Flaky test debugging:** See `pop-systematic-debugging` skill (Phase 1: Flaky Test Branch)
- **Code review for tests:** See `pop-code-review` skill (reviews test quality too)
- **Defense layers for tests:** See `pop-defense-in-depth` skill (test isolation guards)

---

## Final Rule

```
Production code -> test exists and failed first
Otherwise -> not TDD
```

No exceptions without user's permission.
