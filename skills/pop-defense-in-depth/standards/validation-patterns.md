# Defense-in-Depth Validation Patterns

This document defines standard patterns for implementing multi-layer validation.

## Core Principle

**Single validation is not enough.** Invalid data can bypass any single checkpoint through:
- Different code paths
- Internal function calls
- Mock objects in tests
- Refactoring that removes the check
- Edge cases on different platforms

The solution: **Validate at EVERY layer data passes through.**

## The Four Layers

### Layer 1: Entry Point Validation

**Where:** Public APIs, exported functions, HTTP handlers, CLI entry points

**What to check:**
- Input existence (not null/undefined)
- Input type (correct data type)
- Input format (expected structure)
- Input range (within bounds)

**Pattern:**
```typescript
// Entry point - maximum validation
export function createProject(config: ProjectConfig): Project {
  // Existence
  if (!config) {
    throw new ValidationError('config is required');
  }

  // Type (for non-TypeScript or runtime safety)
  if (typeof config.name !== 'string') {
    throw new ValidationError('config.name must be a string');
  }

  // Format
  if (!config.name.match(/^[a-z][a-z0-9-]*$/)) {
    throw new ValidationError('config.name must be lowercase alphanumeric with hyphens');
  }

  // Range/bounds
  if (config.name.length > 50) {
    throw new ValidationError('config.name cannot exceed 50 characters');
  }

  // Delegate to internal with validated data
  return createProjectInternal(config);
}
```

### Layer 2: Business Logic Validation

**Where:** Domain services, business logic functions, data transformations

**What to check:**
- Business rules and constraints
- Cross-field dependencies
- State prerequisites
- Domain invariants

**Pattern:**
```typescript
// Internal function - business validation
function createProjectInternal(config: ProjectConfig): Project {
  // Redundant basic check (defense)
  if (!config.name) {
    throw new BusinessError('Project name required');
  }

  // Business rule: unique name
  if (projectRegistry.exists(config.name)) {
    throw new BusinessError(`Project "${config.name}" already exists`);
  }

  // Business rule: resource limits
  if (projectRegistry.count() >= MAX_PROJECTS) {
    throw new BusinessError('Maximum project limit reached');
  }

  // State prerequisite
  if (!workspace.isInitialized()) {
    throw new BusinessError('Workspace must be initialized first');
  }

  return new Project(config);
}
```

### Layer 3: Environment Guards

**Where:** Dangerous operations, I/O boundaries, system calls

**What to check:**
- Test environment restrictions
- Production safety boundaries
- Resource access permissions
- Platform-specific constraints

**Pattern:**
```typescript
// Low-level operation - environment guards
async function gitInit(directory: string): Promise<void> {
  // Test environment guard
  if (process.env.NODE_ENV === 'test') {
    const normalized = path.normalize(path.resolve(directory));
    const tmpDir = path.normalize(path.resolve(os.tmpdir()));

    if (!normalized.startsWith(tmpDir)) {
      throw new EnvironmentError(
        `Refusing git init outside temp dir in tests: ${directory}`
      );
    }
  }

  // Production guard: sensitive directories
  const FORBIDDEN_PATHS = [
    '/etc', '/usr', '/bin', '/sbin',
    'node_modules', '.git'
  ];

  for (const forbidden of FORBIDDEN_PATHS) {
    if (directory.includes(forbidden)) {
      throw new EnvironmentError(
        `Refusing git init in forbidden path: ${directory}`
      );
    }
  }

  // Platform guard
  if (process.platform === 'win32' && directory.match(/^[A-Z]:\\Windows/i)) {
    throw new EnvironmentError('Refusing git init in Windows system directory');
  }

  await execFileAsync('git', ['init'], { cwd: directory });
}
```

### Layer 4: Debug Instrumentation

**Where:** Before critical operations, at error boundaries

**What to capture:**
- Input values
- Current state (cwd, env)
- Stack traces
- Timestamps

**Pattern:**
```typescript
// Instrumentation layer
async function gitInit(directory: string): Promise<void> {
  // Capture context before operation
  const context = {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    platform: process.platform,
    timestamp: new Date().toISOString(),
    stack: new Error().stack,
  };

  // In tests, use console.error (loggers may be suppressed)
  if (process.env.NODE_ENV === 'test') {
    console.error('DEBUG gitInit:', context);
  } else {
    logger.debug('gitInit', context);
  }

  try {
    await execFileAsync('git', ['init'], { cwd: directory });
    logger.debug('gitInit completed', { directory });
  } catch (error) {
    logger.error('gitInit failed', { ...context, error });
    throw error;
  }
}
```

## Error Types

Use distinct error types for each layer:

```typescript
// Layer 1: Validation errors (invalid input)
class ValidationError extends Error {
  constructor(message: string) {
    super(`Validation failed: ${message}`);
    this.name = 'ValidationError';
  }
}

// Layer 2: Business errors (rule violations)
class BusinessError extends Error {
  constructor(message: string) {
    super(`Business rule violated: ${message}`);
    this.name = 'BusinessError';
  }
}

// Layer 3: Environment errors (context violations)
class EnvironmentError extends Error {
  constructor(message: string) {
    super(`Environment guard triggered: ${message}`);
    this.name = 'EnvironmentError';
  }
}
```

## Layer Selection Matrix

| Operation Type | L1 | L2 | L3 | L4 |
|----------------|:--:|:--:|:--:|:--:|
| User input handling | Required | Optional | Optional | Recommended |
| File system operations | Required | Required | Required | Required |
| Database operations | Required | Required | Recommended | Recommended |
| External API calls | Required | Recommended | Optional | Required |
| Internal service calls | Recommended | Required | Optional | Optional |
| Test helper functions | Required | Required | Required | Recommended |

## Testing Defense Layers

### Strategy: Bypass Testing

For each layer, create a test that bypasses all previous layers:

```typescript
describe('Defense-in-Depth: gitInit', () => {
  describe('Layer 1: Entry validation', () => {
    it('rejects null directory', async () => {
      await expect(gitInit(null as any))
        .rejects.toThrow('directory is required');
    });

    it('rejects empty directory', async () => {
      await expect(gitInit(''))
        .rejects.toThrow('directory cannot be empty');
    });
  });

  describe('Layer 2: Business validation', () => {
    it('rejects non-absolute paths', async () => {
      // Bypasses L1 with valid-looking but problematic input
      await expect(gitInit('./relative/path'))
        .rejects.toThrow('must be absolute');
    });
  });

  describe('Layer 3: Environment guards', () => {
    it('rejects git init outside temp dir in tests', async () => {
      // Bypasses L1 and L2 with valid-looking path
      // but dangerous in test environment
      await expect(gitInit('/home/user/project'))
        .rejects.toThrow('outside temp dir');
    });
  });

  describe('Layer 4: Debug logging', () => {
    it('logs context before operation', async () => {
      const consoleSpy = jest.spyOn(console, 'error');
      const tempDir = path.join(os.tmpdir(), 'test-project');

      await gitInit(tempDir);

      expect(consoleSpy).toHaveBeenCalledWith(
        'DEBUG gitInit:',
        expect.objectContaining({
          directory: tempDir,
          nodeEnv: 'test',
        })
      );
    });
  });
});
```

## When to Apply Defense-in-Depth

### Always Apply For:
- File system operations (create, delete, modify)
- Database operations (especially writes)
- External service calls
- Authentication/authorization
- Test infrastructure code

### Consider For:
- Internal service boundaries
- Data transformation pipelines
- Configuration handling
- Cache operations

### May Be Overkill For:
- Pure functions with typed inputs
- Simple getter/setter methods
- UI-only logic with no side effects

## Common Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Same check everywhere | Not true defense | Different checks at each layer |
| Catching all errors | Hides bugs | Let errors propagate with context |
| Silent fallbacks | Masks problems | Log and throw |
| Trusting mocks | Tests pass but bugs exist | Test with real objects where possible |
| Performance paranoia | No validation | Profile first, then optimize critical paths |
