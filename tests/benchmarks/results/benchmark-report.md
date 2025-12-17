# PopKit Performance Benchmark Report
**Generated:** 2025-12-09T12:21:03.209262
**Total Scenarios:** 5

## Summary

| Scenario | Mode | Duration (ms) | Quality | Status |
|----------|------|---------------|---------|--------|
| agent-routing | solo | 17.62 | 10.0/10 | PASS |
| skill-invocation | solo | 3.40 | 10.0/10 | PASS |
| command-execution | solo | 1.65 | 10.0/10 | PASS |
| hook-execution | solo | 1.57 | 10.0/10 | PASS |
| config-load | solo | 0.88 | 10.0/10 | PASS |

## Detailed Results

### agent-routing (solo)

- **Duration:** 17.62ms
- **Quality Score:** 10.0/10
- **Success:** Yes

**Metrics:**
- accuracy: 1.0
- correct: 10
- total: 10
- avg_routing_time_ms: 1.761627197265625

### skill-invocation (solo)

- **Duration:** 3.40ms
- **Quality Score:** 10.0/10
- **Success:** Yes

**Metrics:**
- skills_loaded: 41
- skills_total: 41
- avg_load_time_ms: 0.06540810189596037
- max_load_time_ms: 0.14495849609375
- min_load_time_ms: 0.0514984130859375

### command-execution (solo)

- **Duration:** 1.65ms
- **Quality Score:** 10.0/10
- **Success:** Yes

**Metrics:**
- commands_loaded: 16
- commands_total: 16
- total_size_bytes: 169326
- avg_size_bytes: 10582.875

### hook-execution (solo)

- **Duration:** 1.57ms
- **Quality Score:** 10.0/10
- **Success:** Yes

**Metrics:**
- hooks_valid: 23
- hooks_total: 23
- validation_rate: 1.0

### config-load (solo)

- **Duration:** 0.88ms
- **Quality Score:** 10.0/10
- **Success:** Yes

**Metrics:**
- configs_loaded: 6
- configs_total: 6
- total_size_bytes: 27915
- avg_load_time_ms: 0.14694531758626303

