# Context Efficiency Standards

Standards for efficient context window usage in Claude Code plugins.

## Core Principles

### CE-001: Skill Prompt Sizing

Skills should minimize context consumption while remaining effective.

**Targets:**
| Component | Target | Warning | Critical |
|-----------|--------|---------|----------|
| SKILL.md | <2000 tokens | 2000-4000 | >4000 |
| Frontmatter | <100 tokens | 100-200 | >200 |
| Examples | <500 tokens | 500-800 | >800 |

**Guidelines:**
- Use tables over verbose lists
- One clear example over multiple redundant ones
- Reference external docs for detailed info
- Remove boilerplate text

### CE-002: Agent Prompt Sizing

Agents have more context allowance but still need efficiency.

**Targets:**
| Component | Target | Warning | Critical |
|-----------|--------|---------|----------|
| AGENT.md | <5000 tokens | 5000-8000 | >8000 |
| Tool list | <200 tokens | 200-400 | >400 |
| Workflow | <800 tokens | 800-1200 | >1200 |

**Guidelines:**
- Only include tools the agent actually uses
- Keep workflows to essential steps
- Use numbered lists over prose
- Reference config files for complex routing

### CE-003: Configuration Efficiency

Configuration files should be concise and deduplicated.

**Targets:**
| File | Target | Warning | Critical |
|------|--------|---------|----------|
| config.json | <10K tokens | 10K-15K | >15K |
| plugin.json | <2K tokens | 2K-3K | >3K |
| hooks.json | <3K tokens | 3K-5K | >5K |

**Deduplication Rules:**
- Define patterns once, reference by ID
- Use inheritance for similar agents
- Externalize large keyword lists

### CE-004: Output Style Efficiency

Output styles should be minimal templates.

**Guidelines:**
- Use placeholders over hardcoded text
- Keep templates under 500 tokens
- Share common sections across styles
- Remove redundant formatting instructions

## Optimization Techniques

### Token Reduction Strategies

1. **Abbreviate Common Patterns**
   ```markdown
   # Instead of:
   "This skill allows users to perform X operation"

   # Use:
   "Performs X operation"
   ```

2. **Table Over List**
   ```markdown
   # Instead of:
   - Option A: Description of option A
   - Option B: Description of option B

   # Use:
   | Option | Description |
   |--------|-------------|
   | A | Description A |
   | B | Description B |
   ```

3. **Reference Over Embed**
   ```markdown
   # Instead of embedding full docs:
   See `standards/detailed-guide.md` for complete reference.
   ```

### Content Organization

**High-Value First:**
1. Purpose (what it does)
2. Quick usage (how to invoke)
3. Examples (most common case)
4. Details (only if needed)

**Progressive Disclosure:**
- Core info in SKILL.md
- Extended docs in separate files
- Advanced options in config files

## Measurement

### Token Estimation

Rough estimation: ~4 characters per token

```python
def estimate_tokens(text: str) -> int:
    return len(text) // 4
```

### Automated Checks

Run context measurement:
```bash
python scripts/measure_context.py ./
```

### Manual Review

Checklist:
- [ ] All skills under 2000 tokens
- [ ] All agents under 5000 tokens
- [ ] Config files under thresholds
- [ ] No duplicate content across files

## Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Avg skill tokens | <1500 | Average across all skills |
| Avg agent tokens | <4000 | Average across all agents |
| Config overhead | <20% | Config / total content ratio |
| Deduplication | >90% | No repeated content |
