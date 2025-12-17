# Startup Performance Standards

Standards for fast, efficient plugin initialization.

## Core Principles

### SP-001: Minimal Startup Files

Only essential files should be read at startup.

**Required at Startup:**
| File | Purpose | Max Size |
|------|---------|----------|
| plugin.json | Plugin manifest | 2KB |
| marketplace.json | Marketplace info | 1KB |
| config.json | Agent routing | 10KB |
| hooks.json | Hook config | 3KB |

**Deferred Until Needed:**
- SKILL.md files
- AGENT.md files
- Output styles
- Standards/checklists

### SP-002: Total Startup Size

Combined startup files should be minimal.

**Targets:**
| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Total size | <50KB | 50-100KB | >100KB |
| File count | <10 | 10-20 | >20 |
| Parse time | <100ms | 100-500ms | >500ms |

### SP-003: Lazy Loading Architecture

Implement tiered loading for scalability.

**Tier System:**
```
Tier 0: Startup (plugin.json, config.json, hooks.json)
Tier 1: Always-active agents (loaded after startup)
Tier 2: On-demand agents (loaded on activation)
Tier 3: Skills (loaded on invocation)
```

**Implementation:**
- Index triggers at startup, not full content
- Load agent prompts only when selected
- Load skill content only when invoked

### SP-004: Agent Tier Balance

Distribute agents appropriately across tiers.

**Guidelines:**
| Tier | Purpose | Count Target |
|------|---------|--------------|
| Tier 1 | Universal tools | <=15 |
| Tier 2 | Specialized | No limit |
| Feature | Workflow agents | 2-5 |

**Tier 1 Criteria:**
- Used across all projects
- No specialized dependencies
- Frequent activation

**Tier 2 Criteria:**
- Domain-specific
- Occasional use
- Resource-intensive

### SP-005: Trigger Optimization

Efficient trigger matching at startup.

**Index Structure:**
```json
{
  "keywords": {
    "review": ["code-reviewer", "security-auditor"],
    "test": ["test-writer-fixer"]
  },
  "patterns": {
    "*.test.ts": "test-writer-fixer",
    "*.sql": "query-optimizer"
  }
}
```

**Guidelines:**
- Pre-compile regex patterns
- Use hash maps for keyword lookup
- Sort patterns by specificity

### SP-006: Hook Initialization

Hooks should initialize quickly.

**Best Practices:**
```python
# Good: Deferred imports
def hook_handler(input_data):
    from .utils.heavy_module import process
    return process(input_data)

# Bad: Top-level heavy imports
from .utils.heavy_module import process
def hook_handler(input_data):
    return process(input_data)
```

**Guidelines:**
- Defer non-essential imports
- Cache parsed configurations
- Avoid file I/O in module initialization

## Optimization Techniques

### Config Pre-processing

Process config once, cache results:

```python
_config_cache = None

def get_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = load_and_process_config()
    return _config_cache
```

### Async Initialization

Where possible, initialize in parallel:

```python
async def initialize():
    config, hooks = await asyncio.gather(
        load_config(),
        load_hooks()
    )
    return config, hooks
```

### Startup Profiling

Measure startup components:

```python
import time

start = time.time()
load_config()
config_time = time.time() - start

start = time.time()
load_hooks()
hooks_time = time.time() - start

print(f"Config: {config_time*1000:.0f}ms, Hooks: {hooks_time*1000:.0f}ms")
```

## Measurement

### Automated Analysis

Run startup analysis:
```bash
python scripts/analyze_loading.py ./
```

### Manual Verification

Checklist:
- [ ] Startup files total <50KB
- [ ] Tier 1 agents <=15
- [ ] No heavy imports at module level
- [ ] Triggers indexed efficiently

## Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Startup time | <500ms | Time to ready state |
| File reads | <10 | Files read at startup |
| Tier 1 ratio | <40% | Tier 1 / total agents |
| Parse time | <100ms | JSON/YAML parsing |
