---
name: defense-in-depth
description: "Use when invalid data causes failures deep in execution, requiring validation at multiple system layers - validates at every layer data passes through to make bugs structurally impossible. Do NOT use for simple input validation or when a single validation point is sufficient - the multi-layer approach adds complexity only justified for critical data paths."
inputs:
  - from: pop-root-cause-tracing
    field: fix_location
    required: false
  - from: any
    field: data_path
    required: false
outputs:
  - field: layers_added
    type: number
  - field: validation_points
    type: array
next_skills:
  - pop-test-driven-development
  - pop-code-review
workflow:
  id: defense-in-depth
  name: Defense-in-Depth Workflow
  version: 1
  description: Multi-layer validation for critical data paths
  steps:
    - id: map_data_flow
      description: Map the data flow through the system
      type: agent
      agent: code-explorer
      next: identify_layers
    - id: identify_layers
      description: Identify validation checkpoint layers
      type: agent
      agent: code-architect
      next: layer_plan_decision
    - id: layer_plan_decision
      description: Review layer plan
      type: user_decision
      question: "How many validation layers to add?"
      header: "Layers"
      options:
        - id: full
          label: "All 4 layers"
          description: "Entry, business, environment, debug"
          next: add_entry_validation
        - id: three
          label: "3 layers"
          description: "Entry, business, environment"
          next: add_entry_validation
        - id: two
          label: "2 layers"
          description: "Entry and business only"
          next: add_entry_validation
        - id: custom
          label: "Custom"
          description: "Select specific layers"
          next: select_layers
      next_map:
        full: add_entry_validation
        three: add_entry_validation
        two: add_entry_validation
        custom: select_layers
    - id: select_layers
      description: Select specific layers to add
      type: user_decision
      question: "Which layers to add?"
      header: "Select"
      options:
        - id: entry
          label: "Entry point"
          description: "API boundary validation"
          next: add_entry_validation
        - id: business
          label: "Business logic"
          description: "Domain validation"
          next: add_business_validation
        - id: environment
          label: "Environment"
          description: "Context-specific guards"
          next: add_environment_guards
        - id: debug
          label: "Debug"
          description: "Logging and instrumentation"
          next: add_debug_logging
      next_map:
        entry: add_entry_validation
        business: add_business_validation
        environment: add_environment_guards
        debug: add_debug_logging
    - id: add_entry_validation
      description: Add Layer 1 - Entry point validation
      type: agent
      agent: code-architect
      next: test_entry_layer
    - id: test_entry_layer
      description: Test entry validation catches bad input
      type: agent
      agent: test-writer-fixer
      next: entry_result
    - id: entry_result
      description: Entry layer complete?
      type: user_decision
      question: "Entry validation working?"
      header: "Layer 1"
      options:
        - id: yes
          label: "Working"
          description: "Entry validation catches bad input"
          next: add_business_validation
        - id: fix
          label: "Needs fix"
          description: "Entry validation not catching correctly"
          next: add_entry_validation
      next_map:
        yes: add_business_validation
        fix: add_entry_validation
    - id: add_business_validation
      description: Add Layer 2 - Business logic validation
      type: agent
      agent: code-architect
      next: test_business_layer
    - id: test_business_layer
      description: Test business validation
      type: agent
      agent: test-writer-fixer
      next: business_result
    - id: business_result
      description: Business layer complete?
      type: user_decision
      question: "Business validation working?"
      header: "Layer 2"
      options:
        - id: yes
          label: "Working"
          description: "Business logic validates correctly"
          next: add_environment_guards
        - id: fix
          label: "Needs fix"
          description: "Business validation needs adjustment"
          next: add_business_validation
        - id: skip
          label: "Skip remaining"
          description: "Two layers sufficient"
          next: verify_all_layers
      next_map:
        yes: add_environment_guards
        fix: add_business_validation
        skip: verify_all_layers
    - id: add_environment_guards
      description: Add Layer 3 - Environment guards
      type: agent
      agent: code-architect
      next: test_environment_layer
    - id: test_environment_layer
      description: Test environment guards
      type: agent
      agent: test-writer-fixer
      next: environment_result
    - id: environment_result
      description: Environment layer complete?
      type: user_decision
      question: "Environment guards working?"
      header: "Layer 3"
      options:
        - id: yes
          label: "Working"
          description: "Guards prevent dangerous operations"
          next: add_debug_logging
        - id: fix
          label: "Needs fix"
          description: "Guards need adjustment"
          next: add_environment_guards
        - id: skip
          label: "Skip logging"
          description: "Three layers sufficient"
          next: verify_all_layers
      next_map:
        yes: add_debug_logging
        fix: add_environment_guards
        skip: verify_all_layers
    - id: add_debug_logging
      description: Add Layer 4 - Debug instrumentation
      type: agent
      agent: code-architect
      next: verify_all_layers
    - id: verify_all_layers
      description: Verify all layers work together
      type: spawn_agents
      agents:
        - type: test-writer-fixer
          task: "Test each layer catches bypass attempts"
        - type: code-reviewer
          task: "Review validation completeness"
      wait_for: all
      next: bypass_test
    - id: bypass_test
      description: Test bypass scenarios
      type: user_decision
      question: "Can any layer be bypassed?"
      header: "Bypass"
      options:
        - id: secure
          label: "All secure"
          description: "No bypasses found"
          next: document_layers
        - id: found
          label: "Found bypass"
          description: "Need to strengthen a layer"
          next: select_layers
      next_map:
        secure: document_layers
        found: select_layers
    - id: document_layers
      description: Document the defense layers
      type: agent
      agent: code-architect
      next: complete
    - id: complete
      description: Defense-in-depth complete
      type: terminal
---

# Defense-in-Depth Validation

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

## Why Multiple Layers

Single validation: "We fixed the bug"
Multiple layers: "We made the bug impossible"

Different layers catch different cases:
- Entry validation catches most bugs
- Business logic catches edge cases
- Environment guards prevent context-specific dangers
- Debug logging helps when other layers fail

## The Four Layers

### Layer 1: Entry Point Validation
**Purpose:** Reject obviously invalid input at API boundary

```typescript
function createProject(name: string, workingDirectory: string) {
  if (!workingDirectory || workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }
  if (!statSync(workingDirectory).isDirectory()) {
    throw new Error(`workingDirectory is not a directory: ${workingDirectory}`);
  }
  // ... proceed
}
```

### Layer 2: Business Logic Validation
**Purpose:** Ensure data makes sense for this operation

```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }
  // ... proceed
}
```

### Layer 3: Environment Guards
**Purpose:** Prevent dangerous operations in specific contexts

```typescript
async function gitInit(directory: string) {
  // In tests, refuse git init outside temp directories
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    const tmpDir = normalize(resolve(tmpdir()));

    if (!normalized.startsWith(tmpDir)) {
      throw new Error(
        `Refusing git init outside temp dir during tests: ${directory}`
      );
    }
  }
  // ... proceed
}
```

### Layer 4: Debug Instrumentation
**Purpose:** Capture context for forensics

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  logger.debug('About to git init', {
    directory,
    cwd: process.cwd(),
    stack,
  });
  // ... proceed
}
```

## Applying the Pattern

When you find a bug:

1. **Trace the data flow** - Where does bad value originate? Where used?
2. **Map all checkpoints** - List every point data passes through
3. **Add validation at each layer** - Entry, business, environment, debug
4. **Test each layer** - Try to bypass layer 1, verify layer 2 catches it

## Example from Session

Bug: Empty `projectDir` caused `git init` in source code

**Data flow:**
1. Test setup -> empty string
2. `Project.create(name, '')`
3. `WorkspaceManager.createWorkspace('')`
4. `git init` runs in `process.cwd()`

**Four layers added:**
- Layer 1: `Project.create()` validates not empty/exists/writable
- Layer 2: `WorkspaceManager` validates projectDir not empty
- Layer 3: `WorktreeManager` refuses git init outside tmpdir in tests
- Layer 4: Stack trace logging before git init

**Result:** All 1847 tests passed, bug impossible to reproduce

## Key Insight

All four layers were necessary. During testing, each layer caught bugs the others missed:
- Different code paths bypassed entry validation
- Mocks bypassed business logic checks
- Edge cases on different platforms needed environment guards
- Debug logging identified structural misuse

**Don't stop at one validation point.** Add checks at every layer.
