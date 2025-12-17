---
name: benchmark-report
description: Comprehensive benchmark comparison between vanilla Claude Code and PopKit modes
used_by:
  - /popkit:benchmark
  - analyze-quality
  - run-both
---

# Benchmark Report Style

## Purpose

Present benchmark results with side-by-side comparisons of vanilla Claude Code, PopKit Quick Mode, PopKit Full Mode, and PopKit Power Mode. Highlight quality differences, performance metrics, and orchestration insights.

## Format

```markdown
## Benchmark Report: [Task Name]

**Task:** [task-id]
**Date:** [YYYY-MM-DD HH:mm]
**Category:** [standard|performance|security|github-issue]

---

### Executive Summary

| Mode | Quality | Duration | Cost | Tests Passed | Verdict |
|------|---------|----------|------|--------------|---------|
| Vanilla | [X/10] | [N]s | $[X.XX] | [M/N] | [emoji] |
| PopKit Quick | [X/10] | [N]s | $[X.XX] | [M/N] | [emoji] |
| PopKit Full | [X/10] | [N]s | $[X.XX] | [M/N] | [emoji] |
| PopKit Power | [X/10] | [N]s | $[X.XX] | [M/N] | [emoji] |

**Winner:** [Mode] - [Reason]

**Key Finding:** [One sentence summary of most important discovery]

---

### Quality Analysis

#### Code Quality Scores

| Criterion | Vanilla | PopKit Quick | PopKit Full | PopKit Power |
|-----------|---------|--------------|-------------|--------------|
| **Correctness** | [X/10] | [X/10] | [X/10] | [X/10] |
| **Architecture** | [X/10] | [X/10] | [X/10] | [X/10] |
| **Best Practices** | [X/10] | [X/10] | [X/10] | [X/10] |
| **Error Handling** | [X/10] | [X/10] | [X/10] | [X/10] |
| **Maintainability** | [X/10] | [X/10] | [X/10] | [X/10] |

#### Critical Issues Found

**Vanilla:**
- [List critical bugs or design flaws, or "None"]

**PopKit Quick:**
- [List critical bugs or design flaws, or "None"]

**PopKit Full:**
- [List critical bugs or design flaws, or "None"]

**PopKit Power:**
- [List critical bugs or design flaws, or "None"]

---

### Performance Metrics

#### Execution Timeline

```
Vanilla:      [===========================] 120s
PopKit Quick: [==================]          80s
PopKit Full:  [=======================]    100s
PopKit Power: [===============]             65s
```

#### Resource Usage

| Metric | Vanilla | PopKit Quick | PopKit Full | PopKit Power |
|--------|---------|--------------|-------------|--------------|
| **Duration** | [N]s | [N]s ([+/-X%]) | [N]s ([+/-X%]) | [N]s ([+/-X%]) |
| **Input Tokens** | [N]k | [N]k ([+/-X%]) | [N]k ([+/-X%]) | [N]k ([+/-X%]) |
| **Output Tokens** | [N]k | [N]k ([+/-X%]) | [N]k ([+/-X%]) | [N]k ([+/-X%]) |
| **Cost** | $[X.XX] | $[X.XX] ([+/-X%]) | $[X.XX] ([+/-X%]) | $[X.XX] ([+/-X%]) |
| **Tool Calls** | [N] | [N] ([+/-X%]) | [N] ([+/-X%]) | [N] ([+/-X%]) |

---

### Test Results

#### Test Suite Performance

| Test | Vanilla | PopKit Quick | PopKit Full | PopKit Power |
|------|---------|--------------|-------------|--------------|
| [test-name-1] | [pass/fail] | [pass/fail] | [pass/fail] | [pass/fail] |
| [test-name-2] | [pass/fail] | [pass/fail] | [pass/fail] | [pass/fail] |
| [test-name-3] | [pass/fail] | [pass/fail] | [pass/fail] | [pass/fail] |
| **Total** | **[M/N]** | **[M/N]** | **[M/N]** | **[M/N]** |

#### Test Failures Analysis

[Explain any test failures - are they implementation bugs or test definition issues?]

---

### Implementation Comparison

#### Approach Differences

**Vanilla:**
[Describe implementation approach, architecture decisions, patterns used]

**PopKit Quick:**
[Describe implementation approach, orchestration decisions, workflow used]

**PopKit Full:**
[Describe implementation approach, brainstorming insights, planning phase]

**PopKit Power:**
[Describe multi-agent coordination, parallel work distribution, consensus approach]

#### Code Samples

**Key Differences:**

Vanilla:
```[language]
[representative code snippet]
```

PopKit:
```[language]
[representative code snippet]
```

**Similarity:** [X]% identical / [Y]% different approaches

---

### Orchestration Analysis (PopKit Modes Only)

#### Workflow Execution

**PopKit Quick:**
- Routing Decision: [direct|skill invocation|agent spawn]
- Steps Taken: [numbered list]
- TodoWrite Usage: [number] todos created

**PopKit Full:**
- Brainstorming Phase: [insights discovered]
- Planning Phase: [plan quality, completeness]
- Execution Phase: [plan adherence]

**PopKit Power:**
- Agents Spawned: [list of agents]
- Coordination Pattern: [mesh|hierarchical|sequential]
- Consensus Quality: [assessment]

#### Command Expansion

[Show how /popkit:dev expanded into skills/agents]

---

### Detailed Metrics

#### File Operations

| Operation | Vanilla | PopKit Quick | PopKit Full | PopKit Power |
|-----------|---------|--------------|-------------|--------------|
| Files Read | [N] | [N] | [N] | [N] |
| Files Written | [N] | [N] | [N] | [N] |
| Files Edited | [N] | [N] | [N] | [N] |
| Total File Ops | [N] | [N] | [N] | [N] |

#### Tool Call Breakdown

| Tool | Vanilla | PopKit Quick | PopKit Full | PopKit Power |
|------|---------|--------------|-------------|--------------|
| Read | [N] | [N] | [N] | [N] |
| Write | [N] | [N] | [N] | [N] |
| Edit | [N] | [N] | [N] | [N] |
| Bash | [N] | [N] | [N] | [N] |
| Grep | [N] | [N] | [N] | [N] |
| Glob | [N] | [N] | [N] | [N] |
| AskUserQuestion | [N] | [N] | [N] | [N] |
| **Total** | **[N]** | **[N]** | **[N]** | **[N]** |

---

### Conclusions

#### Quality Verdict

[emoji] **Winner: [Mode]**

[Detailed explanation of quality comparison, focusing on correctness, maintainability, and best practices]

#### Performance Verdict

[emoji] **Winner: [Mode]**

[Detailed explanation of performance comparison, focusing on speed, cost efficiency, and resource usage]

#### Overall Recommendation

**Best for this task:** [Mode]

**Reasoning:** [Why this mode is optimal for this specific task type]

---

### Key Takeaways

1. **[Major insight #1]**
2. **[Major insight #2]**
3. **[Major insight #3]**

### Next Steps

- [ ] [Action item based on findings]
- [ ] [Action item based on findings]

---

**Report Generated:** [timestamp]
**Analyzer:** [tool/agent name]
**Results Saved:** `[path to results directory]`
```

## Example Usage

For a bouncing-balls benchmark comparing vanilla vs PopKit Quick:

```markdown
## Benchmark Report: Bouncing Balls Animation

**Task:** bouncing-balls
**Date:** 2025-12-15 17:12
**Category:** standard

---

### Executive Summary

| Mode | Quality | Duration | Cost | Tests Passed | Verdict |
|------|---------|----------|------|--------------|---------|
| Vanilla | 10/10 | 112s | $0.24 | 7/8 | ✅ |
| PopKit Quick | 10/10 | 96s | $0.24 | 7/8 | ✅ |

**Winner:** PopKit Quick - Equal quality, 14% faster

**Key Finding:** With prompt parity, PopKit achieves equal code quality to vanilla with slightly better execution time.

[rest of report...]
```

## Notes

- Use emoji indicators for quick visual assessment (✅ ❌ ⚠️ 🏆)
- Include percentage differences in parentheses for easy comparison
- Highlight critical bugs in bold or with warning emoji
- Show ASCII timeline bars for visual duration comparison
- Include code snippets only for significant implementation differences
- Link to full results directory for detailed logs
