---
name: systematic-debugging
description: "Four-phase debugging framework for any bug, test failure, or unexpected behavior. Enforces root cause investigation before proposing fixes through pattern analysis, hypothesis testing, and validated implementation. Use when standard debugging fails, issues span multiple components, or you've already tried obvious fixes without success. Do NOT use for simple typos, obvious syntax errors, or issues where the cause is immediately clear - those are faster to fix directly."
inputs:
  - from: any
    field: error_message
    required: false
  - from: any
    field: reproduction_steps
    required: false
outputs:
  - field: root_cause
    type: string
  - field: fix_applied
    type: boolean
  - field: github_issue
    type: issue_number
next_skills:
  - pop-test-driven-development
  - pop-root-cause-tracing
workflow:
  id: systematic-debugging
  name: Systematic Debugging Workflow
  version: 1
  description: Four-phase debugging with enforced root cause investigation
  steps:
    - id: initial_triage
      description: Gather error information and context
      type: agent
      agent: bug-whisperer
      next: issue_type_decision
    - id: issue_type_decision
      description: Classify the type of issue
      type: user_decision
      question: "What type of issue are we debugging?"
      header: "Issue Type"
      options:
        - id: test_failure
          label: "Test failure"
          description: "Test is failing - check for flakiness first"
          next: flakiness_check
        - id: runtime_bug
          label: "Runtime bug"
          description: "Bug in production or development"
          next: phase1_investigate
        - id: build_failure
          label: "Build failure"
          description: "Build or compilation error"
          next: phase1_investigate
        - id: performance
          label: "Performance"
          description: "Slow or degraded performance"
          next: phase1_investigate
      next_map:
        test_failure: flakiness_check
        runtime_bug: phase1_investigate
        build_failure: phase1_investigate
        performance: phase1_investigate
    - id: flakiness_check
      description: Run test 5x to check for flakiness
      type: agent
      agent: test-writer-fixer
      next: flakiness_result
    - id: flakiness_result
      description: Determine if test is flaky
      type: user_decision
      question: "What were the flakiness check results?"
      header: "Flaky?"
      options:
        - id: consistent_fail
          label: "Fails 5/5"
          description: "Consistent failure - investigate as bug"
          next: phase1_investigate
        - id: consistent_pass
          label: "Passes 5/5"
          description: "Not flaky - investigate normally"
          next: phase1_investigate
        - id: flaky
          label: "Mixed results"
          description: "Flaky test - fix test first"
          next: fix_flaky_test
      next_map:
        consistent_fail: phase1_investigate
        consistent_pass: phase1_investigate
        flaky: fix_flaky_test
    - id: fix_flaky_test
      description: Fix the flaky test before debugging code
      type: skill
      skill: pop-test-driven-development
      next: phase1_investigate
    - id: phase1_investigate
      description: "Phase 1: Root cause investigation"
      type: spawn_agents
      agents:
        - type: bug-whisperer
          task: "Read error messages, check recent changes, trace data flow"
        - type: code-explorer
          task: "Explore related code and dependencies"
      wait_for: all
      next: phase2_patterns
    - id: phase2_patterns
      description: "Phase 2: Pattern analysis - find working examples"
      type: agent
      agent: code-explorer
      next: root_cause_decision
    - id: root_cause_decision
      description: Confirm root cause understanding
      type: user_decision
      question: "Do we have a clear root cause hypothesis?"
      header: "Root Cause"
      options:
        - id: yes
          label: "Yes"
          description: "Root cause identified - proceed to fix"
          next: phase3_hypothesis
        - id: need_more
          label: "Need more info"
          description: "Gather more evidence"
          next: gather_more_evidence
        - id: architectural
          label: "Architectural"
          description: "Looks like an architectural issue"
          next: architectural_decision
      next_map:
        yes: phase3_hypothesis
        need_more: gather_more_evidence
        architectural: architectural_decision
    - id: gather_more_evidence
      description: Add diagnostic instrumentation and gather evidence
      type: skill
      skill: pop-root-cause-tracing
      next: root_cause_decision
    - id: architectural_decision
      description: Decide how to handle architectural issue
      type: user_decision
      question: "How should we handle this architectural problem?"
      header: "Approach"
      options:
        - id: refactor
          label: "Refactor"
          description: "Address the architectural issue"
          next: plan_refactor
        - id: workaround
          label: "Workaround"
          description: "Apply workaround for now"
          next: phase3_hypothesis
        - id: escalate
          label: "Escalate"
          description: "Need team discussion"
          next: complete
      next_map:
        refactor: plan_refactor
        workaround: phase3_hypothesis
        escalate: complete
    - id: plan_refactor
      description: Create refactoring plan
      type: skill
      skill: pop-writing-plans
      next: complete
    - id: phase3_hypothesis
      description: "Phase 3: Form and test hypothesis"
      type: agent
      agent: bug-whisperer
      next: phase4_implement
    - id: phase4_implement
      description: "Phase 4: Create failing test and implement fix"
      type: skill
      skill: pop-test-driven-development
      next: verify_fix
    - id: verify_fix
      description: Verify the fix worked
      type: user_decision
      question: "Did the fix resolve the issue?"
      header: "Verified?"
      options:
        - id: fixed
          label: "Fixed"
          description: "Issue resolved, tests pass"
          next: complete
        - id: not_fixed
          label: "Not fixed"
          description: "Issue persists"
          next: retry_decision
      next_map:
        fixed: complete
        not_fixed: retry_decision
    - id: retry_decision
      description: Decide whether to retry or escalate
      type: user_decision
      question: "How many fix attempts so far? (3+ suggests architectural issue)"
      header: "Attempts"
      options:
        - id: under_three
          label: "Less than 3"
          description: "Re-analyze with new information"
          next: phase1_investigate
        - id: three_plus
          label: "3 or more"
          description: "Stop and question architecture"
          next: architectural_decision
      next_map:
        under_three: phase1_investigate
        three_plus: architectural_decision
    - id: complete
      description: Debugging workflow complete
      type: terminal
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Manager wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

#### Special Case: Test Failures - Check for Flakiness First

**For ANY test failure, check if the test itself is the problem:**

```
Test fails → Is it flaky? → Run 5x locally
  ├─ Passes 5/5: Not your code, not flaky - investigate as normal bug
  ├─ Fails 5/5: Consistent failure - investigate as normal bug
  └─ Mixed results (e.g., 3/5): FLAKY TEST - fix the test first
```

**Flaky test investigation checklist:**

| Check | How | Fix |
|-------|-----|-----|
| **Isolated or connected?** | Run single test vs full suite | If fails alone but passes in suite (or vice versa): state pollution |
| **Timing-dependent?** | Look for `setTimeout`, `sleep`, hardcoded delays | Use condition-based waiting (see `pop-test-driven-development` skill) |
| **Environment-specific?** | Run in CI vs local, different machines | Mock environment variables, isolate external dependencies |
| **Order-dependent?** | Run tests in different order | Add proper setup/teardown, don't share state between tests |
| **Race condition?** | Look for async operations without proper waits | Add proper async/await, use polling for state changes |

**If test is flaky:** Fix the test BEFORE debugging the code. A flaky test proves nothing.

**Then continue with normal investigation:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible -> gather more data, don't guess

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   **WHEN system has multiple components (CI -> build -> signing, API -> service -> database):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

5. **Trace Data Flow**

   **WHEN error is deep in call stack:**

   Use root-cause-tracing skill for backward tracing technique

   **Quick version:**
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

### Phase 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in same codebase
   - What works that's similar to what's broken?

2. **Compare Against References**
   - If implementing pattern, read reference implementation COMPLETELY
   - Don't skim - read every line
   - Understand the pattern fully before applying

3. **Identify Differences**
   - What's different between working and broken?
   - List every difference, however small
   - Don't assume "that can't matter"

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and Testing

**Scientific method:**

1. **Form Single Hypothesis**
   - State clearly: "I think X is the root cause because Y"
   - Write it down
   - Be specific, not vague

2. **Test Minimally**
   - Make the SMALLEST possible change to test hypothesis
   - One variable at a time
   - Don't fix multiple things at once

3. **Verify Before Continuing**
   - Did it work? Yes -> Phase 4
   - Didn't work? Form NEW hypothesis
   - DON'T add more fixes on top

4. **When You Don't Know**
   - Say "I don't understand X"
   - Don't pretend to know
   - Ask for help
   - Research more

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case**
   - Simplest possible reproduction
   - Automated test if possible
   - One-off test script if no framework
   - MUST have before fixing
   - Use test-driven-development skill for writing proper failing tests

2. **Implement Single Fix**
   - Address the root cause identified
   - ONE change at a time
   - No "while I'm here" improvements
   - No bundled refactoring

3. **Verify Fix**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?

4. **If Fix Doesn't Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If >= 3: STOP and question the architecture (step 5 below)**
   - DON'T attempt Fix #4 without architectural discussion

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with user before attempting more fixes**

## Red Flags - STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals new problem in different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (see Phase 4.5)

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms != understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

---

## Cross-References

- **Flaky test fixes:** See `pop-test-driven-development` skill (Condition-Based Waiting section)
- **Root cause tracing:** See `pop-root-cause-tracing` skill (backward tracing through call stack)
- **Defense in depth:** See `pop-defense-in-depth` skill (multi-layer validation to prevent bugs)
