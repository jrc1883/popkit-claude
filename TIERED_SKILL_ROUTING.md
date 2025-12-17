# Tiered Skill Routing Architecture Research

**Date**: 2025-12-13
**Status**: Design Research
**Purpose**: Specification for skill-level tier gating with cloud routing abstraction

---

## Executive Summary

**Problem**: PopKit skills need tier gating (free vs pro), but pro users should not reverse-engineer cloud infrastructure (Upstash, QStash, vector databases).

**Solution**: Implement **Tiered Skill Routing** — a dispatcher pattern where:
1. Skills check user tier **immediately** at invocation
2. Free tier → lightweight local implementation
3. Pro tier → router agent abstraction (black box for users)
4. Infrastructure details hidden behind API contracts

**Key Benefit**: Pro users get cloud-powered features without seeing the IP underneath.

---

## Current State Analysis

### Existing Tier Architecture

PopKit currently implements tiering at **three levels**:

| Level | Current Implementation | Gating Mechanism |
|-------|------------------------|------------------|
| **Agent** | Tier 1 (always) vs Tier 2 (on-demand) | `config.json` routing rules |
| **Feature** | Power Mode, embeddings, generators | `premium_checker.py` entitlement checks |
| **Skill** | None yet (all skills available to all tiers) | Missing |

**Gap**: Skills don't have tier gating logic. A free user can invoke pro-only skills.

### Current Premium Feature Model

**Free Tier Fallbacks**:
```
Feature: Power Mode (Hosted Redis)
├─ Pro: 6+ agents, Redis Streams (Upstash)
└─ Free: 2-3 agents, file-based coordination
```

**Premium Features**:
- `pop-mcp-generator` (custom MCP servers) → FREE: none
- `pop-skill-generator` (project skills) → FREE: none
- `pop-embed-project` (embeddings) → FREE: 10/day
- `pop-power-mode:redis` (hosted) → FREE: file-based

**Pattern**: Each feature defines a `free_tier_fallback` or gracefully degrades.

### How Tier is Determined

```python
# hooks/utils/premium_checker.py
1. If POPKIT_BILLING_LIVE=true:
   - Call /v1/auth/me → fetch actual tier
2. Else (pre-launch):
   - Return "free" for all users
   - Show "coming soon" instead of upgrades
```

---

## Proposed Architecture: Tiered Skill Routing

### 1. Core Pattern

```
┌─ Skill Invocation ──────────────────────────┐
│                                             │
│  1. Check: POPKIT_TIER env var or API call │
│  2. Load implementation based on tier       │
│  3. Execute with appropriate resources      │
│  4. Signal tier level in response (subtle)  │
│                                             │
└─────────────────────────────────────────────┘

                        │
                        ▼

        ┌───────────────┴───────────────┐
        │                               │
    FREE TIER                       PRO TIER
    ┌──────────────┐          ┌──────────────────┐
    │ Local Files  │          │ Router Agent     │
    ├──────────────┤          ├──────────────────┤
    │ Simple scripts│          │ Cloud Abstraction│
    │ Basic check  │          ├──────────────────┤
    │ Embedded docs│          │ Upstash (Redis)  │
    │              │          │ QStash (Queue)   │
    │ Max 2s exec  │          │ Vector DB        │
    │ Offline ready│          │ Embeddings API   │
    └──────────────┘          │                  │
                              │ Graceful         │
                              │ fallback to free │
                              └──────────────────┘
```

### 2. Skill Folder Structure

**Current** (observed in codebase):
```
skill-name/
├── SKILL.md          (markdown definition)
├── scripts/          (Python/bash implementations)
├── standards/        (Guidelines, checklists)
└── checklists/       (Task lists)
```

**Proposed with Tier Gating**:
```
skill-name/
├── SKILL.md                    (shared, defines both tiers)
├── free/
│   ├── scripts/
│   │   ├── main.py            (lightweight implementation)
│   │   └── utils.py
│   ├── standards/             (basic standards)
│   ├── checklists/            (free tier tasks)
│   └── README.md              (how this tier works)
├── pro/
│   ├── cloud-router.json      (API contract only)
│   ├── scripts/
│   │   ├── router-proxy.py    (calls cloud API, never contains secrets)
│   │   └── utils.py           (formatting, validation)
│   ├── standards/             (enhanced standards)
│   ├── checklists/            (pro tier extended tasks)
│   └── README.md              (what cloud features it uses)
└── shared/
    ├── common.py              (shared utilities)
    └── data/                  (embedded reference data)
```

### 3. Tier Selection Logic

**Decision Tree** (in skill invocation):

```python
def select_implementation(skill_name: str, use_case: str) -> str:
    user_tier = get_user_tier()

    # Sometimes free is better
    if use_case == "offline_work":
        return "free"                    # No network latency
    if use_case == "quick_local_check":
        return "free"                    # <500ms response needed

    # Smart upgrades
    if user_tier == "pro":
        if use_case == "embeddings_search":
            return "pro"                 # Cloud vector DB
        if use_case == "historical_context":
            return "pro"                 # Redis cache, activity ledger
        if use_case == "async_workflow":
            return "pro"                 # QStash job queue
        else:
            return "pro"                 # Just use better implementation

    # Fallback
    return "free"

# Called during skill.md evaluation:
# {tier_choice|auto} → evaluates to "free" or "pro"
```

### 4. The Router Agent Abstraction

**Purpose**: Pro users never see cloud infrastructure details.

**What Users See**:
```python
# Pro users see function calls like:
router.get_skill_definition(skill_name)
router.find_similar_patterns(code_snippet)
router.get_enhanced_checklist(skill_name)
router.search_past_outputs(query)
```

**What They Don't See**:
```python
# Router internally does this:
upstash_redis.get(f"skill:{skill_name}:definition")
vector_db.similarity_search(embedding, k=5)
upstash_redis.xread(stream="popkit:activity", ...)
qstash.publish_job(task_name, ...)
# ... none of this is user-visible
```

**Implementation**:
```
tier-1-always-active/
├── skill-router-agent/
│   ├── AGENT.md
│   ├── router.py              (API abstraction, no secrets)
│   └── cloud-client.py        (internal HTTP client)
└── (invoked transparently by pro-tier skills)
```

**API Contract** (what users reverse-engineer):
```python
class SkillRouter:
    def get_skill_definition(self, name: str) -> SkillDef
    def find_similar_patterns(self, query: str, k: int = 5) -> List[Pattern]
    def get_enhanced_checklist(self, name: str) -> List[ChecklistItem]
    def search_past_outputs(self, query: str) -> List[Result]
    def get_skill_assets(self, name: str, asset_type: str) -> Dict
    def refresh_embeddings(self, skill_name: str) -> Status
```

**IP Protection**: The router is a **black box**. Users can see the function signatures but:
- Don't know if it uses Upstash or a different backend
- Don't see connection strings or API keys
- Can't access the vector DB directly
- Can't replay requests against Upstash
- Can't extract infrastructure topology

---

## Implementation Patterns

### Pattern 1: Skill Definition (SKILL.md)

**Before** (no tier gating):
```markdown
---
name: skill-name
description: "Does something"
---

# Skill Name
## Overview
## Process
```

**After** (with tier gating):
```markdown
---
name: skill-name
description: "Does something (enhanced in Pro)"
tier_default: "auto"          # auto|free|pro|pro-with-free-fallback
tier_indicators:
  free: "Basic version"
  pro: "Enhanced with cloud patterns"
---

# Skill Name

## Overview
[Shared description]

## Tier Availability
- **Free**: Basic checklists, local analysis
- **Pro**: Historical patterns, embeddings, async workflows

## Process

{if tier == "pro"}
### Pro Process (Enhanced)
1. Router agent fetches skill history
2. Vector search finds similar patterns
3. Async workflows via QStash
4. Results cached in Upstash Redis
{/if}

{if tier == "free"}
### Free Process (Lightweight)
1. Local checklist execution
2. Embedded standards
3. Synchronous execution
4. No external calls
{/if}

## Decision Points
[Standard AskUserQuestion prompts, same for both tiers]

## Integration
[Agent + skill usage, same for both]
```

### Pattern 2: Implementation Dispatch (router-proxy.py)

**Free Tier Script** (`free/scripts/main.py`):
```python
#!/usr/bin/env python3
"""
Free tier implementation - lightweight, offline-ready
"""

import json
import sys
from pathlib import Path

def main():
    # Read stdin (CloudCode/hook protocol)
    input_data = json.loads(sys.stdin.read())

    # Execute free tier logic
    result = {
        "status": "success",
        "tier_used": "free",
        "data": free_implementation(input_data),
        "note": "Free version - enhanced version available in Pro"
    }

    print(json.dumps(result))

def free_implementation(input_data):
    # Simple, embedded logic
    # Standard files, basic checks
    # Max 2 second execution
    pass
```

**Pro Tier Script** (`pro/scripts/main.py`):
```python
#!/usr/bin/env python3
"""
Pro tier implementation - calls router agent for cloud features
"""

import json
import sys
import os

def main():
    input_data = json.loads(sys.stdin.read())

    # Check if user is pro
    if not is_pro_user():
        # Fallback to free
        return free_tier_fallback(input_data)

    # Call router agent (abstraction layer)
    from skill_router import SkillRouter

    router = SkillRouter(
        api_key=os.getenv("POPKIT_API_KEY"),
        # Connection details hidden in router implementation
    )

    result = {
        "status": "success",
        "tier_used": "pro",
        "data": pro_implementation(router, input_data),
    }

    print(json.dumps(result))

def pro_implementation(router, input_data):
    skill_name = input_data.get("skill")

    # These calls hide infrastructure details
    similar = router.find_similar_patterns(input_data.get("query"))
    checklists = router.get_enhanced_checklist(skill_name)

    # Merge results
    return {
        "checklist": checklists,
        "patterns": similar,
        "async_ready": True
    }
```

### Pattern 3: Agent Config Routing

**Current** (`packages/plugin/agents/config.json`):
```json
{
  "routing": {
    "keywords": [
      {"pattern": "bug", "agent": "bug-whisperer"},
      {"pattern": "security", "agent": "security-auditor"}
    ]
  }
}
```

**Enhanced with Skill Tier Routing**:
```json
{
  "skill_routing": {
    "by_tier": {
      "free": {
        "max_context_size": "10KB",
        "max_execution_time": "2s",
        "available_skills": [
          "pop-code-review-basic",
          "pop-test-basics",
          "pop-security-baseline"
        ]
      },
      "pro": {
        "max_context_size": "unlimited",
        "max_execution_time": "30s",
        "available_skills": [
          "pop-code-review-*",
          "pop-test-*",
          "pop-mcp-generator",
          "pop-embed-project",
          "pop-skill-generator"
        ]
      }
    },
    "smart_selection": {
      "use_pro_if_available": [
        "embeddings_search",
        "historical_context",
        "async_workflow",
        "pattern_learning"
      ],
      "always_use_free": [
        "offline_work",
        "quick_local_check",
        "user_restricted"
      ]
    }
  }
}
```

### Pattern 4: Status Line Visibility

**Current** (no tier indicator):
```
[PK] ~2.4k | #45 3/7 40%
```

**With Tier Indicator** (subtle):
```
[PK Free] ~2.4k | #45 3/7 40%
[PK Pro] ~2.4k | #45 3/7 40% ⭐
```

Or in output template:

```markdown
## Results
[output]

---
*💡 Using free version. [Upgrade](popkit.com/upgrade) for cloud-powered patterns.*
```

**Configuration** (`.claude/popkit/config.json`):
```json
{
  "statusline": {
    "show_tier_indicator": true,
    "show_upgrade_hints": true,
    "hint_frequency": "every_5_skills"
  }
}
```

---

## Security: IP Protection Strategy

### Risk: Infrastructure Reverse Engineering

**Threat**: Pro users reverse-engineer cloud stack
```
User sees: router.find_similar_patterns()
User deduces: "There's probably a vector DB"
User attacks: Dumps Upstash keys from local env, hits API directly
```

### Mitigation: Three-Layer Abstraction

**Layer 1: Hidden Credentials**
```python
# ❌ Don't do this (visible to users):
upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
router = redis.Redis(url=upstash_url)

# ✅ Do this (hidden in cloud):
# User gets API key via POPKIT_API_KEY
# Cloud service holds Upstash credentials
# Router calls Cloud API, not Upstash directly
```

**Layer 2: API Contract Abstraction**
```python
# Router exposes high-level API:
router.find_similar_patterns(query)

# Internal implementation is opaque:
# - Uses vector DB? Unknown to user
# - Uses Redis? Unknown to user
# - Uses Elasticsearch? Unknown to user
# - Could swap backends without breaking contract
```

**Layer 3: No Direct Infrastructure Access**

```python
# ❌ User can't do:
redis.xread(stream="popkit:activity")  # Stream name exposed
vector_db.raw_query(query_json)        # DB exposed

# ✅ Only can do:
router.get_enhanced_checklist(skill)   # Opaque API
router.search_past_outputs(query)      # Opaque API
```

### Rate Limiting & Usage Tracking

Pro users are rate-limited at the API level:
```json
{
  "pro_tier": {
    "find_similar_patterns": {"daily": 1000, "monthly": 30000},
    "get_skill_definition": {"daily": 5000, "monthly": 150000},
    "search_past_outputs": {"daily": 500, "monthly": 15000}
  }
}
```

**Enforcement**: Cloud API checks `POPKIT_API_KEY` on every call, validates tier, decrements limits.

---

## Integration with Existing Tiers

### Agent Tiers (Unchanged)

```
Tier 1 agents (always active):
├─ Still routes all agents for all tiers
└─ Agent selection is tier-independent

Tier 2 agents (on-demand):
├─ Still activates based on keywords/patterns
└─ Agent selection is tier-independent

*NEW: Skill Router Agent (tier 1)*
├─ Pro tier skills call this to abstract cloud
└─ Free tier skills call local implementations
```

### How They Work Together

**Free User**:
```
User invokes skill-X
  → Skill checks tier: "free"
  → Loads free/scripts/main.py
  → Executes local logic
  → Agent router may still be active (tier 1)
  → Agent might invoke other free skills
```

**Pro User**:
```
User invokes skill-X
  → Skill checks tier: "pro"
  → Loads pro/scripts/main.py
  → Calls router agent (abstraction)
  → Router agent calls cloud API (credentials hidden)
  → Cloud returns skill definitions, embeddings, etc.
  → Agent router uses these enhanced assets
```

---

## Cloud Infrastructure Mapping

### What Goes Where

**Cloud API** (`packages/cloud/src/index.ts`):
- Tier verification
- Entitlement checks
- Usage tracking
- Skill definition serve
- Credential management

**Upstash Redis**:
- Skill definition cache (TTL: 24h)
- Embedding cache (TTL: 7d)
- Activity ledger (historical context)
- User context snapshot (for resuming sessions)

**Vector Database**:
- Skill embeddings (for similarity search)
- Past output embeddings (to find patterns)
- Code snippet embeddings (to find related skills)

**QStash** (optional for pro):
- Async embedding refresh
- Long-running skill analysis
- Background pattern detection

### Tier Storage Tiers

| Resource | Free | Pro |
|----------|------|-----|
| Skill definitions | Embedded in plugin | Cached in Upstash (24h TTL) |
| Embeddings | None | Computed once, cached forever |
| Activity ledger | File system (7 days) | Upstash Streams (30 days) |
| Past outputs | Local only | Upstash + vector DB |
| Context snapshot | `.popkit/context/*.json` | Upstash with Redis Streams |

---

## User Experience

### Transparency (Subtle Signals)

**Avoid**: Loud "You're using free version!" messages

**Do**:
```markdown
## Results
[output]

---
💡 *Pro tip: Upgrade for pattern matching across your project history*
```

**Or in status line**:
```
[PK Pro] ~2.4k | Enhanced patterns loaded
```

### Upgrade Path

**Free user sees:**
1. "This skill has a pro version available" (on skill invocation)
2. "Upgrade for X, Y, Z" (in output template)
3. "Similar patterns available in Pro" (contextual hint)
4. Never blocking, always graceful

**Pro user sees:**
1. Full output without hints
2. Maybe "Refreshing patterns..." (if async work)
3. Never sees infrastructure details

### Graceful Fallback

```
Pro skill called
  → Cloud API unavailable?
  → Fall back to free implementation
  → Note: "Using offline mode - cloud unavailable"
  → Don't fail, don't confuse user
```

---

## Implementation Phases

### Phase 1: Foundation (This Document)
- [x] Analyze current architecture
- [x] Design pattern
- [x] Security review
- [ ] Present to agent for feedback

### Phase 2: Pilot (1-2 skills)
- [ ] Convert pop-skill-generator to tiered
- [ ] Convert pop-mcp-generator to tiered
- [ ] Test free vs pro flows
- [ ] Validate IP protection

### Phase 3: Router Agent Implementation
- [ ] Create skill-router agent
- [ ] Implement cloud-client.py
- [ ] Add to tier-1-always-active
- [ ] Wire up Upstash + vector DB

### Phase 4: Bulk Migration
- [ ] Refactor remaining 60 skills
- [ ] Update agents config
- [ ] Test agent + skill integration
- [ ] Load test with rate limiting

### Phase 5: Documentation & Launch
- [ ] Update CLAUDE.md with pattern
- [ ] Document router API contract
- [ ] Add examples for skill developers
- [ ] Launch publicly

---

## Example: Converting a Skill to Tiered Routing

### Before (pop-code-review)
```
pop-code-review/
├── SKILL.md
├── scripts/
│   └── review.py
├── standards/
│   └── python-standards.md
└── checklists/
    └── review-checklist.md
```

### After (pop-code-review with tiers)
```
pop-code-review/
├── SKILL.md                        (updated: describes both tiers)
├── free/
│   ├── scripts/
│   │   ├── review.py              (local checklist runner)
│   │   └── confidence.py          (80+ threshold)
│   ├── standards/
│   │   └── python-standards.md    (essential rules only)
│   └── checklists/
│       └── review-checklist.md
├── pro/
│   ├── cloud-router.json          (API contract)
│   ├── scripts/
│   │   ├── review.py              (calls router agent)
│   │   └── utils.py               (formatting)
│   ├── standards/
│   │   ├── python-standards.md    (comprehensive)
│   │   ├── patterns.md            (found via embeddings)
│   │   └── antipatterns.md        (historical patterns)
│   └── checklists/
│       ├── review-checklist.md    (extended)
│       └── generated-checklist.md (from past project)
└── shared/
    ├── common.py                   (both use)
    └── data/
        └── builtin-patterns.json
```

### SKILL.md Changes
```markdown
---
name: code-review
description: "Review code for quality, security, and patterns"
tier_default: "auto"
tier_indicators:
  free: "Local checklist + standards"
  pro: "Historical patterns + embeddings"
---

# Code Review

## Tier Availability
- **Free**: 80+ confidence threshold, built-in standards
- **Pro**: 40+ confidence, historical patterns, similar code detection

## Process

{if tier == "pro"}
1. Router agent fetches historical patterns for this codebase
2. Find similar code patterns using embeddings
3. Check against learned antipatterns
4. Report with historical context
{/if}

{if tier == "free"}
1. Run built-in checklist
2. Check against standards
3. Report with confidence scores
{/if}
```

### Implementation (pro/scripts/review.py)
```python
#!/usr/bin/env python3

def main():
    input_data = json.loads(sys.stdin.read())

    if not is_pro_user():
        return free_tier_fallback(input_data)

    from skill_router import SkillRouter
    router = SkillRouter(api_key=os.getenv("POPKIT_API_KEY"))

    # Pro features
    file_path = input_data["file"]

    # Fetch similar code patterns
    patterns = router.find_similar_patterns(
        query=read_file(file_path),
        k=3
    )

    # Fetch historical issues for this project
    past_issues = router.search_past_outputs(
        query=f"issues in {file_path}",
        limit=10
    )

    # Run review with enhanced context
    result = review_code(
        file_path,
        similar_patterns=patterns,
        historical_context=past_issues
    )

    result["tier_used"] = "pro"
    print(json.dumps(result))
```

---

## Decisions Needed

**Q1: Cloud API First, or Upstash Direct?**
- Option A: Cloud API holds secrets, router calls cloud (recommended - better IP protection)
- Option B: Pro users get Upstash credentials directly (faster, but more exposure)

**Q2: Embedding Refresh Strategy?**
- Option A: Lazy - compute on first access, cache forever
- Option B: Eager - precompute for all skills, update daily via QStash
- Option C: Hybrid - lazy first access, daily refresh in background

**Q3: Activity Ledger Retention?**
- Option A: 30 days (to find patterns within a month)
- Option B: 90 days (more history, larger DB)
- Option C: Unlimited (most context, most cost)

**Q4: Graceful Degradation Priority?**
- Option A: Always fallback to free if cloud unavailable
- Option B: Fail fast with "cloud unavailable, upgrade required"
- Option C: Retry with exponential backoff, then fallback

---

## Success Metrics

| Metric | Goal | Measurement |
|--------|------|-------------|
| IP Protection | Users can't reverse-engineer cloud stack | Security audit passes, no exposed credentials |
| Adoption | 80%+ of skills migrated | Checklist: skills with both tiers |
| Performance | <500ms for free, <2s for pro | Latency monitoring |
| User Retention | Free users see upgrade value | Analytics: free → pro conversion |
| Reliability | 99.9% availability | Cloud API uptime SLO |

---

## References

- Current architecture: `CLAUDE.md` (tier system, premium features)
- Agent config: `packages/plugin/agents/config.json`
- Premium checker: `packages/plugin/hooks/utils/premium_checker.py`
- Skill decisions: `packages/plugin/agents/config.json#skill_decisions`
- Router pattern: `packages/plugin/power-mode/` (agent coordination)
- Cloud API: `packages/cloud/src/index.ts`

---

## Next Steps

1. **Review this document** with PopKit agents (`code-architect`, `code-reviewer`)
2. **Clarify decisions** (Q1-Q4 above)
3. **Design API contract** for router agent
4. **Pilot 2 skills** (pop-mcp-generator, pop-skill-generator)
5. **Implement router agent** in tier-1-always-active
6. **Migrate remaining skills** in bulk
7. **Launch and monitor** adoption metrics
