---
name: root-cause-tracing
description: "Use when errors occur deep in execution and you need to trace back to find the original trigger - systematically traces bugs backward through call stack, adding instrumentation when needed, to identify source of invalid data or incorrect behavior. Do NOT use for obvious errors with clear stack traces or simple typos - the systematic tracing is overkill when the cause is already apparent."
inputs:
  - from: pop-systematic-debugging
    field: error_details
    required: false
  - from: any
    field: symptom_description
    required: false
outputs:
  - field: root_cause
    type: string
  - field: trace_depth
    type: number
  - field: fix_location
    type: file_path
next_skills:
  - pop-defense-in-depth
  - pop-test-driven-development
workflow:
  id: root-cause-tracing
  name: Root Cause Tracing Workflow
  version: 1
  description: Systematic backward tracing to find bug origins
  steps:
    - id: observe_symptom
      description: Document the observed symptom
      type: agent
      agent: bug-whisperer
      next: stack_analysis
    - id: stack_analysis
      description: Analyze available stack trace
      type: agent
      agent: code-explorer
      next: trace_depth_decision
    - id: trace_depth_decision
      description: Evaluate how deep to trace
      type: user_decision
      question: "Stack trace analysis complete. How to proceed?"
      header: "Trace"
      options:
        - id: clear
          label: "Clear cause"
          description: "Root cause is visible in stack trace"
          next: document_cause
        - id: deeper
          label: "Trace deeper"
          description: "Need to trace through call chain"
          next: trace_call_chain
        - id: instrument
          label: "Add logging"
          description: "Need instrumentation to find source"
          next: add_instrumentation
      next_map:
        clear: document_cause
        deeper: trace_call_chain
        instrument: add_instrumentation
    - id: trace_call_chain
      description: Trace backward through calls
      type: agent
      agent: bug-whisperer
      next: found_origin_decision
    - id: add_instrumentation
      description: Add debug logging/stack traces
      type: agent
      agent: bug-whisperer
      next: run_with_logging
    - id: run_with_logging
      description: Run code with instrumentation
      type: agent
      agent: test-writer-fixer
      next: analyze_logs
    - id: analyze_logs
      description: Analyze captured logs and traces
      type: agent
      agent: bug-whisperer
      next: found_origin_decision
    - id: found_origin_decision
      description: Evaluate if root cause found
      type: user_decision
      question: "Have we found the root cause?"
      header: "Found?"
      options:
        - id: yes
          label: "Found it"
          description: "Root cause identified"
          next: document_cause
        - id: deeper
          label: "Trace more"
          description: "Need to go further back"
          next: trace_call_chain
        - id: more_logging
          label: "More logging"
          description: "Need additional instrumentation"
          next: add_instrumentation
      next_map:
        yes: document_cause
        deeper: trace_call_chain
        more_logging: add_instrumentation
    - id: document_cause
      description: Document the root cause
      type: agent
      agent: bug-whisperer
      next: fix_approach
    - id: fix_approach
      description: Choose fix approach
      type: user_decision
      question: "How should we fix this?"
      header: "Fix"
      options:
        - id: source
          label: "Fix at source"
          description: "Fix where bad data originates"
          next: implement_fix
        - id: defense
          label: "Defense in depth"
          description: "Add multiple validation layers"
          next: defense_layers
        - id: both
          label: "Both"
          description: "Fix source and add defenses"
          next: implement_fix
      next_map:
        source: implement_fix
        defense: defense_layers
        both: implement_fix
    - id: implement_fix
      description: Implement the fix at source
      type: agent
      agent: code-architect
      next: add_defense_decision
    - id: add_defense_decision
      description: Add defense layers?
      type: user_decision
      question: "Add defense-in-depth layers?"
      header: "Defense"
      options:
        - id: yes
          label: "Add defenses"
          description: "Add validation layers for safety"
          next: defense_layers
        - id: no
          label: "Skip"
          description: "Source fix is sufficient"
          next: verify_fix
      next_map:
        yes: defense_layers
        no: verify_fix
    - id: defense_layers
      description: Add defense-in-depth layers
      type: skill
      skill: pop-defense-in-depth
      next: verify_fix
    - id: verify_fix
      description: Verify the fix works
      type: agent
      agent: test-writer-fixer
      next: cleanup_decision
    - id: cleanup_decision
      description: Clean up instrumentation?
      type: user_decision
      question: "Remove debug instrumentation?"
      header: "Cleanup"
      options:
        - id: yes
          label: "Remove"
          description: "Clean up debug logging"
          next: cleanup_instrumentation
        - id: keep
          label: "Keep some"
          description: "Keep useful logging"
          next: complete
      next_map:
        yes: cleanup_instrumentation
        keep: complete
    - id: cleanup_instrumentation
      description: Remove debug logging
      type: agent
      agent: code-architect
      next: complete
    - id: complete
      description: Root cause tracing complete
      type: terminal
---

# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack (git init in wrong directory, file created in wrong location, database opened with wrong path). Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

## When to Use

**Use when:**
- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem

## The Tracing Process

### 1. Observe the Symptom
```
Error: git init failed in /Users/jesse/project/packages/core
```

### 2. Find Immediate Cause
**What code directly causes this?**
```typescript
await execFileAsync('git', ['init'], { cwd: projectDir });
```

### 3. Ask: What Called This?
```typescript
WorktreeManager.createSessionWorktree(projectDir, sessionId)
  -> called by Session.initializeWorkspace()
  -> called by Session.create()
  -> called by test at Project.create()
```

### 4. Keep Tracing Up
**What value was passed?**
- `projectDir = ''` (empty string!)
- Empty string as `cwd` resolves to `process.cwd()`
- That's the source code directory!

### 5. Find Original Trigger
**Where did empty string come from?**
```typescript
const context = setupCoreTest(); // Returns { tempDir: '' }
Project.create('name', context.tempDir); // Accessed before beforeEach!
```

## Adding Stack Traces

When you can't trace manually, add instrumentation:

```typescript
// Before the problematic operation
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    stack,
  });

  await execFileAsync('git', ['init'], { cwd: directory });
}
```

**Critical:** Use `console.error()` in tests (not logger - may not show)

**Run and capture:**
```bash
npm test 2>&1 | grep 'DEBUG git init'
```

**Analyze stack traces:**
- Look for test file names
- Find the line number triggering the call
- Identify the pattern (same test? same parameter?)

## Finding Which Test Causes Pollution

If something appears during tests but you don't know which test:

Run tests one-by-one, stops at first polluter. Bisection is key.

## Real Example: Empty projectDir

**Symptom:** `.git` created in `packages/core/` (source code)

**Trace chain:**
1. `git init` runs in `process.cwd()` <- empty cwd parameter
2. WorktreeManager called with empty projectDir
3. Session.create() passed empty string
4. Test accessed `context.tempDir` before beforeEach
5. setupCoreTest() returns `{ tempDir: '' }` initially

**Root cause:** Top-level variable initialization accessing empty value

**Fix:** Made tempDir a getter that throws if accessed before beforeEach

**Also added defense-in-depth:**
- Layer 1: Project.create() validates directory
- Layer 2: WorkspaceManager validates not empty
- Layer 3: NODE_ENV guard refuses git init outside tmpdir
- Layer 4: Stack trace logging before git init

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger.

## Stack Trace Tips

**In tests:** Use `console.error()` not logger - logger may be suppressed
**Before operation:** Log before the dangerous operation, not after it fails
**Include context:** Directory, cwd, environment variables, timestamps
**Capture stack:** `new Error().stack` shows complete call chain

## Real-World Impact

From debugging session (2025-10-03):
- Found root cause through 5-level trace
- Fixed at source (getter validation)
- Added 4 layers of defense
- 1847 tests passed, zero pollution
