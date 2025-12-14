# pop-sandbox-test

Interactive sandbox testing for PopKit skills and commands.

## Trigger

Use this skill when the user wants to:
- Run sandbox tests for skills or commands
- Validate plugin functionality in isolation
- Check test results and analytics
- Compare test runs for regressions

## Overview

This skill provides an interactive interface to the PopKit Sandbox Testing Platform. It runs skills and commands in isolated environments, captures telemetry, and provides detailed analytics.

## Process

### Step 1: Test Selection

Present test options using AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "What would you like to test?"
- header: "Test Mode"
- options:
  1. label: "Run P0 smoke tests"
     description: "Critical tests that must pass (10 tests, ~10min)"
  2. label: "Run full test suite"
     description: "P0 + P1 tests (25 tests, ~1hr)"
  3. label: "Test specific skill"
     description: "Choose a skill to test"
  4. label: "Test specific command"
     description: "Choose a command to test"
- multiSelect: false
```

### Step 2: Configuration

If testing specific skill/command, ask:

```
Use AskUserQuestion tool with:
- question: "Which test runner should we use?"
- header: "Runner"
- options:
  1. label: "Local (Recommended)"
     description: "Fast, no setup required, uses temp directory"
  2. label: "E2B Cloud"
     description: "Full isolation, requires E2B API key"
  3. label: "Both (Comparison)"
     description: "Run in both and compare results"
- multiSelect: false
```

### Step 3: Load Test Matrix

Read the test matrix and filter based on selection:

```bash
cd packages/plugin/tests/sandbox
python matrix_loader.py --suite smoke --json   # For P0 tests
python matrix_loader.py --suite full --json    # For full suite
python matrix_loader.py --type skill --json    # For skills only
```

### Step 4: Execute Tests

For each test in the filtered list:

1. **Show Progress**:
   ```
   [2/10] Testing pop-brainstorming...
   ```

2. **Run Test** (local runner):
   ```python
   from local_runner import LocalTestRunner, TestConfig

   runner = LocalTestRunner()
   config = TestConfig(
       test_name="pop-brainstorming",
       test_type="skill",
       timeout_seconds=180
   )
   result = runner.run_skill_test("pop-brainstorming", {"topic": "test topic"}, config)
   ```

3. **Capture Result**:
   - Success: ✅
   - Failure: ❌
   - Partial: ⚠️
   - Timeout: ⏱️

### Step 5: Generate Report

After all tests complete:

```bash
cd packages/plugin/tests/sandbox
python analytics.py --recent 10 --json
```

Present summary:

```
## Test Results Summary

| Metric | Value |
|--------|-------|
| Total Tests | 10 |
| Passed | 8 |
| Failed | 1 |
| Partial | 1 |
| Duration | 8m 32s |

### Failed Tests

1. ❌ skill-session-resume-001
   - Error: STATUS.json not found
   - Duration: 45s

### Partial Tests

1. ⚠️ command-git-commit-001
   - Warning: No staged changes
   - Duration: 12s
```

### Step 6: Next Actions

```
Use AskUserQuestion tool with:
- question: "What would you like to do next?"
- header: "Next"
- options:
  1. label: "View detailed report"
     description: "Full markdown report with all metrics"
  2. label: "Re-run failed tests"
     description: "Retry the 2 failed/partial tests"
  3. label: "Compare with previous run"
     description: "Show regression analysis"
  4. label: "Done"
     description: "Exit sandbox testing"
- multiSelect: false
```

## Test Types

### Skill Tests

Test individual skills in isolation:
- Invoke skill via Skill tool simulation
- Capture tool calls and decisions
- Verify expected outputs
- Check for errors

### Command Tests

Test slash commands:
- Parse command arguments
- Execute command logic
- Verify side effects (file creation, git operations)
- Check output format

### Scenario Tests

Test multi-step workflows:
- Execute sequence of skills/commands
- Maintain state between steps
- Verify final outcome

## Telemetry

All tests capture:
- **Tool traces**: Every tool call with inputs/outputs
- **Decision points**: AskUserQuestion interactions
- **Phase changes**: Workflow progression
- **Errors**: Any failures with context
- **Timing**: Duration of each operation

## Example Session

```
User: Run sandbox tests

Claude: I'll help you run sandbox tests for PopKit.

[AskUserQuestion: What would you like to test?]
> Run P0 smoke tests

[AskUserQuestion: Which test runner?]
> Local (Recommended)

Starting P0 smoke tests (10 tests)...

[1/10] ✅ skill-brainstorming-001 (42s)
[2/10] ✅ skill-code-review-001 (1m 15s)
[3/10] ✅ skill-morning-generator-001 (38s)
[4/10] ✅ skill-session-capture-001 (22s)
[5/10] ❌ skill-session-resume-001 (45s)
       Error: STATUS.json not found in test directory
[6/10] ✅ skill-plugin-test-001 (2m 8s)
[7/10] ✅ command-dev-brainstorm-001 (55s)
[8/10] ✅ command-routine-morning-001 (1m 32s)
[9/10] ✅ command-routine-nightly-001 (1m 28s)
[10/10] ✅ command-plugin-test-001 (2m 5s)

## Results Summary

| Metric | Value |
|--------|-------|
| Passed | 9/10 (90%) |
| Failed | 1/10 |
| Duration | 11m 10s |
| Token Usage | 45,230 |
| Est. Cost | $0.18 |

[AskUserQuestion: What would you like to do next?]
```

## Integration

### With /popkit:plugin test

The existing plugin test command can invoke sandbox tests:

```
/popkit:plugin test sandbox              # Run smoke tests
/popkit:plugin test sandbox --full       # Run full suite
/popkit:plugin test sandbox --skill X    # Test specific skill
```

### With CI/CD

Generate CI-friendly reports:

```bash
python analytics.py --ci --recent 10 > test-results.json
```

Output includes pass/fail status and regression detection.

## Configuration

Tests are defined in `packages/plugin/tests/sandbox/test_matrix.json`.

Environment variables:
- `POPKIT_TEST_MODE=1` - Enable test telemetry
- `E2B_API_KEY` - For E2B cloud tests (optional)
- `UPSTASH_REDIS_REST_URL` - For cloud telemetry sync (optional)

## Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| Test Matrix | `tests/sandbox/test_matrix.json` | Test definitions |
| Matrix Loader | `tests/sandbox/matrix_loader.py` | Filter and load tests |
| Local Runner | `tests/sandbox/local_runner.py` | Local test execution |
| E2B Runner | `tests/sandbox/e2b_runner.py` | Cloud test execution |
| Analytics | `tests/sandbox/analytics.py` | Results analysis |
| Telemetry | `hooks/utils/test_telemetry.py` | Event capture |

## Related

- `/popkit:plugin test` - Plugin validation command
- `pop-plugin-test` - Plugin self-test skill
- Issue #225-231 - Sandbox Testing Platform
