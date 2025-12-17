# Defense-in-Depth Layer Checklist

Use this checklist to implement comprehensive multi-layer validation.

## Pre-Implementation

- [ ] Root cause of the bug is identified
- [ ] Data flow through the system is mapped
- [ ] All checkpoints where data passes are documented
- [ ] Critical vs non-critical paths identified

---

## Layer 1: Entry Point Validation

### Purpose
Reject obviously invalid input at API/function boundary.

### Checklist
- [ ] Validate input is not null/undefined
- [ ] Validate input is correct type
- [ ] Validate input is not empty (if applicable)
- [ ] Validate input format/structure
- [ ] Validate input range/bounds

### Implementation Pattern
```typescript
function createProject(name: string, workingDirectory: string) {
  // Existence check
  if (!workingDirectory) {
    throw new Error('workingDirectory is required');
  }

  // Type/format check
  if (typeof workingDirectory !== 'string') {
    throw new Error('workingDirectory must be a string');
  }

  // Empty check
  if (workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }

  // Validity check
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }

  // Semantic check
  if (!statSync(workingDirectory).isDirectory()) {
    throw new Error(`workingDirectory is not a directory: ${workingDirectory}`);
  }
}
```

### Tests for Layer 1
- [ ] Null input throws appropriate error
- [ ] Undefined input throws appropriate error
- [ ] Empty string throws appropriate error
- [ ] Invalid type throws appropriate error
- [ ] Non-existent path throws appropriate error
- [ ] Valid input passes validation

---

## Layer 2: Business Logic Validation

### Purpose
Ensure data makes sense for the specific operation.

### Checklist
- [ ] Domain rules are enforced
- [ ] Business constraints are validated
- [ ] Cross-field dependencies checked
- [ ] State prerequisites verified

### Implementation Pattern
```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  // Redundant check (defense in depth)
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }

  // Business rule: session must be valid
  if (!isValidSessionId(sessionId)) {
    throw new Error('Invalid session ID format');
  }

  // Business rule: directory must be under allowed paths
  if (!isAllowedProjectDirectory(projectDir)) {
    throw new Error('Project directory not in allowed paths');
  }
}
```

### Tests for Layer 2
- [ ] Invalid business state is rejected
- [ ] Cross-field validation works
- [ ] Domain constraints are enforced
- [ ] Bypassing Layer 1 still gets caught here

---

## Layer 3: Environment Guards

### Purpose
Prevent dangerous operations in specific contexts.

### Checklist
- [ ] Test environment restrictions in place
- [ ] Production safety checks exist
- [ ] Context-specific guards implemented
- [ ] Resource boundaries enforced

### Implementation Pattern
```typescript
async function gitInit(directory: string) {
  // Environment guard: refuse dangerous operations in tests
  if (process.env.NODE_ENV === 'test') {
    const normalized = path.normalize(path.resolve(directory));
    const tmpDir = path.normalize(path.resolve(os.tmpdir()));

    if (!normalized.startsWith(tmpDir)) {
      throw new Error(
        `Refusing git init outside temp dir during tests: ${directory}`
      );
    }
  }

  // Production guard: refuse in sensitive directories
  const sensitivePatterns = ['/etc', '/usr', '/bin', 'node_modules'];
  if (sensitivePatterns.some(p => directory.includes(p))) {
    throw new Error(`Refusing git init in sensitive directory: ${directory}`);
  }
}
```

### Tests for Layer 3
- [ ] Test environment blocks dangerous operations
- [ ] Production guards prevent sensitive directory access
- [ ] Allowed operations pass through
- [ ] Bypassing Layers 1-2 still gets caught here

---

## Layer 4: Debug Instrumentation

### Purpose
Capture context for forensics when other layers fail.

### Checklist
- [ ] Critical operations are logged
- [ ] Input values are captured
- [ ] Current state is recorded
- [ ] Stack traces are available

### Implementation Pattern
```typescript
async function gitInit(directory: string) {
  // Debug instrumentation
  const stack = new Error().stack;
  logger.debug('About to git init', {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    timestamp: new Date().toISOString(),
    stack,
  });

  // Proceed with operation
  await execFileAsync('git', ['init'], { cwd: directory });

  logger.debug('git init completed', { directory });
}
```

### Logging Best Practices
- [ ] Use `console.error()` in tests (not logger)
- [ ] Log BEFORE dangerous operations
- [ ] Include relevant context (cwd, env, timestamps)
- [ ] Include stack trace for call chain analysis

---

## Integration Verification

### Bypass Testing
For each layer, test that bypassing previous layers still catches the issue:

| Test Scenario | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|---------------|---------|---------|---------|---------|
| Direct invalid call | Catches | Catches | Catches | Logs |
| Bypass L1 via internal call | Skipped | Catches | Catches | Logs |
| Bypass L1-L2 via low-level call | Skipped | Skipped | Catches | Logs |
| All layers bypassed | Skipped | Skipped | Skipped | Logs |

### Test Each Layer Independently
- [ ] L1: Call public API with invalid input
- [ ] L2: Call internal function with invalid input
- [ ] L3: Call low-level function in test environment
- [ ] L4: Verify logs captured even when operation fails

---

## Documentation Requirements

### Per-Layer Documentation
For each layer, document:
- [ ] What it validates
- [ ] Why this layer is necessary
- [ ] What scenarios it catches
- [ ] What bypasses it prevents

### Example Documentation
```typescript
/**
 * Layer 1: Entry validation for project creation.
 *
 * Catches: null, empty, non-existent directories at API boundary.
 *
 * Why needed: First line of defense against invalid caller input.
 * Prevents most common mistakes before they propagate.
 *
 * Not sufficient alone: Internal code paths can bypass this.
 * That's why Layer 2 exists.
 */
```

---

## Quick Reference: Layer Selection

| Scenario | L1 | L2 | L3 | L4 |
|----------|----|----|----|----|
| Public API | Required | Recommended | Optional | Recommended |
| Internal service | Recommended | Required | Recommended | Optional |
| Test environment | Required | Required | Required | Required |
| File system ops | Required | Required | Required | Required |
| Database ops | Required | Required | Recommended | Recommended |
| External API calls | Required | Recommended | Optional | Required |

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Single validation point | Can be bypassed | Add multiple layers |
| Same check repeated | Not defense in depth | Different checks at each layer |
| Silent failures | Hard to debug | Always log or throw |
| Trusting internal code | Internal bugs exist | Validate everywhere |
| Over-validation | Performance impact | Focus on critical paths |
