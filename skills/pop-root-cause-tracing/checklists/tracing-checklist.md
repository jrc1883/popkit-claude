# Root Cause Tracing Checklist

Use this checklist to systematically trace bugs back to their origin.

## Pre-Tracing Setup

- [ ] Bug is reproducible (can trigger it on demand)
- [ ] Have access to stack trace or error output
- [ ] Know which test/code path triggers the issue
- [ ] Development environment ready for debugging

---

## Phase 1: Observe Symptom

### Document the Error
- [ ] Exact error message captured
- [ ] Stack trace saved
- [ ] Line number where error manifests
- [ ] Expected vs actual behavior noted

### Categorize the Symptom
- [ ] Is this a crash or incorrect behavior?
- [ ] Is data wrong, or is it missing?
- [ ] Does it happen consistently or intermittently?
- [ ] Is it isolated or affecting multiple areas?

---

## Phase 2: Find Immediate Cause

### Identify the Direct Trigger
- [ ] Found the exact line of code that errors
- [ ] Understand what that code is trying to do
- [ ] Identified the invalid value/state

### Ask the First "Why"
- [ ] Why did this value become invalid?
- [ ] What called this function?
- [ ] What parameters were passed?

---

## Phase 3: Trace the Call Chain

### Work Backward Systematically
- [ ] Level 1: What called the erroring function?
- [ ] Level 2: What called that caller?
- [ ] Level 3: Continue until you find the origin

### At Each Level, Document
- [ ] Function name and file
- [ ] Parameters received
- [ ] Any transformations applied
- [ ] Where the bad value came from

### Stop Conditions
- [ ] Found where invalid data was created
- [ ] Found where valid data became invalid
- [ ] Found external source (user input, API, file)

---

## Phase 4: Add Instrumentation (if needed)

### When to Add Logging
- [ ] Call chain is too long to trace manually
- [ ] Multiple code paths could cause the issue
- [ ] Need to capture runtime values

### Instrumentation Best Practices
- [ ] Use `console.error()` in tests (not logger)
- [ ] Log BEFORE the dangerous operation
- [ ] Include: value, cwd, env, stack trace
- [ ] Use `new Error().stack` for call chain

### Example Instrumentation
```typescript
const stack = new Error().stack;
console.error('DEBUG operation:', {
  value,
  cwd: process.cwd(),
  nodeEnv: process.env.NODE_ENV,
  stack,
});
```

### After Adding Logging
- [ ] Run the failing test/code
- [ ] Capture output with: `npm test 2>&1 | grep 'DEBUG'`
- [ ] Analyze the captured stack traces

---

## Phase 5: Identify Root Cause

### Root Cause Characteristics
- [ ] Is the original source of invalid data
- [ ] Fix here would prevent all downstream issues
- [ ] Makes sense as the "real" problem

### Common Root Cause Patterns

| Pattern | Example |
|---------|---------|
| **Timing** | Variable accessed before initialized |
| **Missing validation** | Empty string accepted, should be rejected |
| **Wrong scope** | Test pollution from shared state |
| **Incorrect default** | Default value is invalid |
| **Missing null check** | Assumed value exists, it doesn't |
| **Off-by-one** | Array index out of bounds |
| **Race condition** | Concurrent access without sync |

### Verify It's the Root Cause
- [ ] Fixing here would fix the symptom
- [ ] No further "why" question to ask
- [ ] The bad data originates here

---

## Phase 6: Document and Fix

### Document the Trace
- [ ] Symptom → Immediate cause → ... → Root cause
- [ ] Depth of trace (how many levels)
- [ ] Key insight that revealed the cause

### Fix Strategy Decision
- [ ] Fix at source only (minimal change)
- [ ] Fix at source + defense layers (robust)
- [ ] Defense layers only (when source not changeable)

### Implement Fix
- [ ] Fix addresses root cause, not symptom
- [ ] No temporary workarounds
- [ ] Test covers the scenario

---

## Phase 7: Add Defenses (Recommended)

### Defense Layer Checklist
- [ ] Layer 1: Validate at entry point
- [ ] Layer 2: Validate at intermediate boundaries
- [ ] Layer 3: Guard dangerous operations
- [ ] Layer 4: Logging for future debugging

### Example Defense Layers
```typescript
// Layer 1: Entry validation
if (!projectDir) {
  throw new Error('projectDir is required');
}

// Layer 2: Boundary validation
if (!path.isAbsolute(projectDir)) {
  throw new Error('projectDir must be absolute');
}

// Layer 3: Operation guard
if (process.env.NODE_ENV === 'test' && !projectDir.includes('tmp')) {
  throw new Error('Refusing git init outside temp directory in tests');
}

// Layer 4: Diagnostic logging
console.error('About to git init in:', projectDir);
```

---

## Phase 8: Cleanup and Verify

### Remove Debug Code
- [ ] Remove temporary console.error statements
- [ ] Remove excessive logging
- [ ] Keep useful permanent logging (if any)

### Verify Fix
- [ ] Original bug no longer reproduces
- [ ] All tests pass
- [ ] No new issues introduced

### Document for Future
- [ ] Update relevant documentation
- [ ] Add comment explaining why validation exists
- [ ] Record in bug tracking if applicable

---

## Quick Reference: Tracing Questions

Ask these at each level of the trace:

1. **What** is the invalid value?
2. **Where** does it come from?
3. **Why** is it invalid?
4. **Who** called this function?
5. **When** did the value become invalid?

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Fix at symptom | Bug will recur differently | Trace to root cause |
| Skip instrumentation | Can't find deep bugs | Add logging when needed |
| Single fix point | Fragile, can break again | Add defense layers |
| Leave debug code | Clutters production | Clean up after debugging |
| Assume obvious cause | Miss actual root cause | Trace systematically |

---

## Trace Depth Guidelines

| Trace Depth | Complexity | Typical Scenario |
|-------------|------------|------------------|
| 1 level | Simple | Direct cause visible |
| 2-3 levels | Moderate | Standard call chain |
| 4-5 levels | Complex | Deep abstractions |
| 6+ levels | Very complex | Framework interactions |

If trace goes 6+ levels, consider:
- Adding permanent logging at key boundaries
- Refactoring to reduce call depth
- Creating dedicated debugging tools
