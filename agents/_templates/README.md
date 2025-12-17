# Agent Template & Migration Guide

This directory contains the standardized agent template and migration instructions.

## Files

- `AGENT.template.md` - Standard 12-section template for new agents

## Agent Directory Structure

Each agent lives in its own directory:

```
agents/
  tier-1-always-active/
    code-reviewer/
      AGENT.md              # Core definition (300-500 lines max)
      references/           # Reference materials (optional)
        patterns.md         # Common patterns, examples
        checklist.md        # Validation checklists
        examples.md         # Code snippets
      scripts/              # Executable helpers (optional)
        validate.py         # Validation scripts
      assets/               # Static content (optional)
        diagram.md          # Architecture diagrams
```

## Required Sections (12)

Every AGENT.md must contain these sections:

| # | Section | Purpose |
|---|---------|---------|
| 1 | **Metadata** | Name, Category, Type, Color, Priority, Version, Tier |
| 2 | **Purpose** | 2-4 sentence mission statement |
| 3 | **Primary Capabilities** | 3-7 bullet points of what the agent does |
| 4 | **Progress Tracking** | Checkpoint frequency and format |
| 5 | **Circuit Breakers** | 4-6 limits with thresholds and actions |
| 6 | **Systematic Approach** | Phase-based methodology |
| 7 | **Power Mode Integration** | Check-in protocol, push/pull, sync |
| 8 | **Integration with Other Agents** | Upstream/downstream/parallel patterns |
| 9 | **Output Format** | Reference output_style or inline template |
| 10 | **Success Criteria** | Measurable completion conditions |
| 11 | **Value Delivery Tracking** | Metrics to report |
| 12 | **Completion Signal** | Standardized end marker |

## Migration Process

### Step 1: Create Directory

```bash
# For tier-1 agent
mkdir -p agents/tier-1-always-active/agent-name

# For tier-2 agent
mkdir -p agents/tier-2-on-demand/agent-name

# For feature-workflow agent
mkdir -p agents/feature-workflow/agent-name
```

### Step 2: Copy Template

```bash
cp agents/_templates/AGENT.template.md agents/tier-X/agent-name/AGENT.md
```

### Step 3: Migrate Content

1. **Copy frontmatter** from old file (name, description, tools, output_style)
2. **Fill Metadata section** from old file's header content
3. **Extract Purpose** from existing description/overview
4. **Map capabilities** from existing bullet points
5. **Add Progress Tracking** (may need to create)
6. **Add Circuit Breakers** (may need to create)
7. **Preserve Systematic Approach** from existing methodology
8. **Add Power Mode Integration** (use template section as-is, customize tags)
9. **Map Integration** from existing "Related agents" sections
10. **Preserve Output Format** from existing templates
11. **Add Success Criteria** (may need to create)
12. **Add Value Delivery Tracking** (may need to create)
13. **Add Completion Signal** (use standard format)

### Step 4: Extract Large Content

For agents >500 lines, extract to supporting files:

| Content Type | Destination |
|-------------|-------------|
| Code examples | `references/examples.md` |
| Checklists | `references/checklist.md` |
| Pattern libraries | `references/patterns.md` |
| Error catalogs | `references/errors.md` |
| Scoring models | `references/scoring.md` |

Reference extracted content:
```markdown
## Patterns

See [references/patterns.md](references/patterns.md) for common patterns.
```

### Step 5: Verify Size

Target: 300-500 lines for AGENT.md

| Lines | Action |
|-------|--------|
| <200 | May need more detail |
| 200-500 | Ideal range |
| 500-800 | Consider extraction |
| >800 | Must extract |

### Step 6: Update Config

Add to `agents/config.json`:

```json
{
  "tiers": {
    "tier-1-always-active": {
      "agents": {
        "agent-name": {
          "path": "tier-1-always-active/agent-name/AGENT.md"
        }
      }
    }
  }
}
```

### Step 7: Test

```bash
# Validate structure
/popkit:plugin-test structure

# Test routing
/popkit:routing-debug agent-name

# Test Power Mode (if applicable)
# Trigger the agent and verify check-ins work
```

### Step 8: Clean Up

After validation:
1. Remove old flat file (e.g., `tier-1-always-active/agent-name.md`)
2. Commit changes
3. Update any documentation references

## Power Mode Integration

All agents must support Power Mode check-ins. The minimum required section:

```markdown
## Power Mode Integration

### Check-In Protocol
Participates in Power Mode check-ins every 5 tool calls.

### PUSH (Outgoing)
- **Discoveries**: [What this agent discovers]
- **Decisions**: [What decisions it makes]
- **Tags**: [relevant, tags]

### PULL (Incoming)
Accept insights with tags: [tag-list]

### Progress Format
```
ICON agent-name T:[count] P:[%] | [current-task]
```

### Sync Barriers
- [List or "None - operates independently"]
```

### Customizing Tags

Choose tags relevant to the agent's domain:

| Agent Type | Recommended Tags |
|-----------|-----------------|
| Testing | `test`, `coverage`, `fixture`, `mock` |
| Security | `security`, `auth`, `vulnerability`, `owasp` |
| API | `api`, `endpoint`, `schema`, `rest`, `graphql` |
| Database | `database`, `query`, `migration`, `schema` |
| Performance | `performance`, `optimization`, `bottleneck` |
| Documentation | `docs`, `readme`, `api-doc`, `changelog` |

## Extraction Guidelines

### When to Extract

Extract content when:
- Same information used in multiple places
- Content is >100 lines of reference material
- Code examples dominate the agent file
- Checklists or patterns could be reused

### What to Keep Inline

Keep inline:
- Agent behavior description
- Phase methodology
- Decision logic
- Integration patterns

### Reference File Format

Each reference file should have:

```markdown
# [Title]

> Referenced by: AGENT.md Section [X]

## Overview

[Brief description of what this reference contains]

## Content

[The actual reference material]
```

## Validation Checklist

Before finalizing a migrated agent:

- [ ] Frontmatter has name, description, tools
- [ ] All 12 sections present
- [ ] Metadata section complete
- [ ] Power Mode Integration section present
- [ ] Circuit Breakers defined (4-6 limits)
- [ ] Progress Tracking format defined
- [ ] Completion Signal follows standard format
- [ ] AGENT.md is 200-500 lines
- [ ] Extracted files referenced properly
- [ ] Config.json updated with new path
- [ ] Old flat file removed
- [ ] `/popkit:plugin-test` passes

## Examples

See these agents as migration examples:

| Agent | Tier | Notes |
|-------|------|-------|
| `code-reviewer` | 1 | Medium complexity, well-structured |
| `power-coordinator` | 2 | Has all sections, good reference |
| `code-explorer` | FW | Small agent, minimal structure |
