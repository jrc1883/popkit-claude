---
description: "list | add | remove | sync | search <query>"
argument-hint: "<subcommand> [query|url]"
---

# /popkit:knowledge

Manage configurable knowledge sources that are synced on session start. External documentation and blogs are fetched, cached, and made available to agents for context enrichment.

## Usage

```bash
/popkit:knowledge                    # List all sources with status
/popkit:knowledge add <url>          # Add new knowledge source
/popkit:knowledge remove <id>        # Remove a knowledge source
/popkit:knowledge refresh            # Force refresh all sources
/popkit:knowledge refresh <id>       # Force refresh specific source
/popkit:knowledge status             # Show detailed cache statistics
/popkit:knowledge search <query>     # Search across cached knowledge
```

## Architecture Integration

This command integrates with popkit's full architecture:

| Component | Role |
|-----------|------|
| **Skill** | `pop-knowledge-lookup` - Query cached knowledge |
| **Hook** | `knowledge-sync.py` - Session start sync with TTL |
| **Config** | `~/.claude/config/knowledge/sources.json` |
| **Cache** | `~/.claude/config/knowledge/cache.db` (SQLite) |
| **Content** | `~/.claude/config/knowledge/content/*.md` |

## Instructions

You are the knowledge source manager. Parse the ARGUMENTS to determine the subcommand.

### Step 0: Parse Arguments

Extract the subcommand and parameters from ARGUMENTS:
- No args → `list`
- `add <url>` → add workflow
- `remove <id>` → remove workflow
- `refresh [id]` → refresh workflow
- `status` → status workflow
- `search <query>` → search workflow

### Configuration Location

All operations use this config file:
```
~/.claude/config/knowledge/sources.json
```

Read it first to understand current state before any operation.

---

## Subcommand: List (default)

**Trigger:** No arguments provided

**Steps:**
1. Read `~/.claude/config/knowledge/sources.json`
2. Query cache status from `~/.claude/config/knowledge/cache.db`:
   ```sql
   SELECT source_id, fetched_at, expires_at, content_size, status
   FROM knowledge_cache
   ```
3. Display formatted table

**Output Format:**
```
## Knowledge Sources

| ID | Name | Status | Size | Last Fetch | Expires |
|----|------|--------|------|------------|---------|
| anthropic-engineering | Claude Code Engineering Blog | Fresh | 125KB | 2h ago | in 22h |
| claude-code-hooks | Claude Code Docs - Hooks | Fresh | 89KB | 2h ago | in 22h |

**Summary:** 2 sources | 2 fresh | 0 stale
```

---

## Subcommand: Add

**Trigger:** `add <url>`

**Steps:**
1. **Validate URL** - Must be valid HTTP(S)
2. **Check for duplicates** - Ensure URL not already configured
3. **Generate ID** - Create kebab-case from domain/path (e.g., `docs-anthropic-hooks`)
4. **Ask for details** using AskUserQuestion:
   - Name (or infer from page title via WebFetch)
   - Tags (comma-separated, default: ["documentation"])
   - Priority (high/medium/low, default: medium)
   - TTL in hours (default: 24)
5. **Test fetch** - Use WebFetch to verify URL is accessible
6. **Add to config** - Append to sources array in sources.json
7. **Trigger initial sync** - Fetch and cache content immediately

**Output Format:**
```
## Added Knowledge Source

**ID:** example-docs
**Name:** Example Documentation
**URL:** https://example.com/docs
**Priority:** high
**TTL:** 24 hours
**Tags:** documentation, api

Initial fetch: 45KB cached successfully
```

---

## Subcommand: Remove

**Trigger:** `remove <id>`

**Steps:**
1. **Read current config** from sources.json
2. **Find source by ID** - Error if not found
3. **Show what will be removed** (name, URL, cached size)
4. **Remove from sources.json** - Filter out the source
5. **Delete cached content** - Remove `~/.claude/config/knowledge/content/<id>.md`
6. **Clean cache DB** - Delete metadata row

**Output Format:**
```
## Removed Knowledge Source

**ID:** claude-code-overview
**Name:** Claude Code Docs - Overview
**Cached content deleted:** 45KB

Remaining sources: 2
```

---

## Subcommand: Refresh

**Trigger:** `refresh [id]`

**Steps:**
1. **Determine scope** - All sources or specific ID
2. **For each source:**
   - Fetch URL via WebFetch (bypass cache)
   - Update content file
   - Update cache.db metadata with new timestamps
3. **Report results**

**Output Format:**
```
## Knowledge Refresh

| Source | Status | Size | Duration |
|--------|--------|------|----------|
| anthropic-engineering | Updated | 125KB | 1.2s |
| claude-code-hooks | Updated | 89KB | 0.8s |

All sources refreshed successfully.
```

---

## Subcommand: Status

**Trigger:** `status`

**Steps:**
1. Read sources.json for configuration
2. Query cache.db for detailed metrics:
   ```sql
   SELECT * FROM knowledge_cache;
   SELECT source_id, COUNT(*), AVG(duration_ms) FROM fetch_history GROUP BY source_id;
   ```
3. Check content directory for file sizes
4. Display comprehensive status

**Output Format:**
```
## Knowledge Cache Status

**Location:** ~/.claude/config/knowledge/
**Total Sources:** 3 (3 enabled, 0 disabled)
**Cache Health:** 2 fresh, 1 stale, 0 missing

### Source Details

| ID | Status | Size | Fetched | Expires | Avg Fetch Time |
|----|--------|------|---------|---------|----------------|
| anthropic-engineering | Fresh | 125KB | 2h ago | in 22h | 1.1s |
| claude-code-hooks | Fresh | 89KB | 2h ago | in 22h | 0.9s |
| custom-docs | Stale | 45KB | 26h ago | expired | 2.3s |

### Recommendations
- Refresh stale source: `custom-docs`
```

---

## Subcommand: Search

**Trigger:** `search <query>`

**Steps:**
1. Search across all cached content files using Grep:
   ```bash
   grep -ri "<query>" ~/.claude/config/knowledge/content/
   ```
2. Group results by source
3. Show relevant excerpts with context

**Output Format:**
```
## Knowledge Search: "hooks"

### anthropic-engineering (3 matches)
- Line 45: "Hooks allow you to intercept tool calls..."
- Line 89: "Pre-tool hooks run before execution..."
- Line 134: "Post-tool hooks can modify output..."

### claude-code-hooks (12 matches)
- Line 12: "# Claude Code Hooks Reference..."
[truncated - showing first 5]

**Total:** 15 matches across 2 sources
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Source ID not found | List available IDs and suggest closest match |
| URL fetch failed | Show HTTP status, suggest checking URL manually |
| Config file missing | Create with defaults, inform user |
| Cache DB corrupted | Recreate DB, trigger full refresh |

---

## Related Components

- **Skill:** Invoke `pop-knowledge-lookup` for agent knowledge queries
- **Hook:** `knowledge-sync.py` runs on session start
- **Session continuity:** Knowledge persists across sessions via cache

## Validation

After any modification, verify:
1. `sources.json` is valid JSON
2. All enabled sources have corresponding content files (or are pending sync)
3. Cache DB is consistent with config
