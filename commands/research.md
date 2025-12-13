---
description: "list | search | add | tag | show | delete | merge [--type, --project]"
argument-hint: "<subcommand> [query|id|branch] [options]"
---

# /popkit:research - Research Management

Capture, index, and surface research insights during development. Maintains a searchable knowledge base of findings, decisions, and learnings.

## Usage

```
/popkit:research <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List captured research (default) |
| `search` | Semantic search across research entries |
| `add` | Add new research entry |
| `tag` | Add/remove tags from entries |
| `show` | View full research entry |
| `delete` | Remove research entry |
| `merge` | Process research branches from Claude Code Web sessions |

---

## Subcommand: list (default)

List all captured research entries with optional filtering.

```
/popkit:research                         # List all entries
/popkit:research list                    # Same as above
/popkit:research list --type decision    # Filter by type
/popkit:research list --project myapp    # Filter by project
/popkit:research list --tag api          # Filter by tag
/popkit:research list -n 10              # Limit results
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--type` | `-t` | Filter by type (decision, finding, learning, spike) |
| `--project` | `-p` | Filter by project name |
| `--tag` | | Filter by tag |
| `--limit` | `-n` | Limit results (default: 20) |

### Output Format

```
Research Entries (12 total):

| ID   | Type     | Title                           | Tags              | Date       |
|------|----------|--------------------------------|-------------------|------------|
| r001 | decision | Use Redis for session storage  | auth, infra       | 2024-12-09 |
| r002 | finding  | Stripe webhook timing issue    | billing, stripe   | 2024-12-08 |
| r003 | learning | Astro SSR hydration quirks     | frontend, astro   | 2024-12-07 |
| r004 | spike    | Evaluate Upstash Vector        | embeddings, search| 2024-12-06 |

Use /popkit:research show <id> to view details
Use /popkit:research search "query" for semantic search
```

### Process

1. Load research index from `.claude/research/index.json`
2. Apply filters (type, project, tag)
3. Sort by date (newest first)
4. Format as table
5. Display with hints

---

## Subcommand: search

Semantic search across all research entries using embeddings.

```
/popkit:research search "how to handle auth tokens"
/popkit:research search "database migration strategies" --type decision
/popkit:research search "performance optimization" -n 5
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--type` | `-t` | Filter results by type |
| `--project` | `-p` | Filter by project |
| `--limit` | `-n` | Maximum results (default: 5) |
| `--threshold` | | Minimum similarity score (default: 0.6) |

### Output Format

```
Search Results for "auth token handling":

1. [decision] Use Redis for session storage (r001) - 0.89
   > We decided to use Redis for session tokens because...
   Tags: auth, infra | Project: popkit-cloud

2. [finding] JWT refresh token race condition (r015) - 0.82
   > Found that concurrent refresh requests can cause...
   Tags: auth, security | Project: myapp

3. [learning] OAuth state parameter importance (r008) - 0.76
   > State parameter prevents CSRF attacks by...
   Tags: auth, oauth | Project: popkit-cloud

Use /popkit:research show <id> for full entry
```

### Process

1. Generate embedding for search query using Voyage AI
2. Query vector index for similar entries
3. Filter by optional constraints (type, project)
4. Return top N results with similarity scores
5. Display with truncated content preview

---

## Subcommand: add

Add a new research entry to the knowledge base.

```
/popkit:research add "Decision: Use Resend for transactional email"
/popkit:research add --type decision --title "Use Resend for email"
/popkit:research add --interactive
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--type` | `-t` | Entry type: decision, finding, learning, spike |
| `--title` | | Entry title |
| `--project` | `-p` | Associated project |
| `--tag` | | Tags (can specify multiple) |
| `--interactive` | `-i` | Use interactive prompt flow |

### Entry Types

| Type | Description | Use For |
|------|-------------|---------|
| `decision` | Architectural or design decision | Tech choices, patterns, conventions |
| `finding` | Discovery during development | Bugs, behaviors, edge cases |
| `learning` | Knowledge gained | Best practices, gotchas, tips |
| `spike` | Investigation results | Research, evaluations, comparisons |

### Interactive Flow

When `--interactive` or called without sufficient args:

```
Use AskUserQuestion tool with:
- question: "What type of research entry is this?"
- header: "Entry Type"
- options:
  1. label: "Decision"
     description: "Architectural or design choice"
  2. label: "Finding"
     description: "Discovery during development"
  3. label: "Learning"
     description: "Knowledge or insight gained"
  4. label: "Spike"
     description: "Investigation or evaluation results"
- multiSelect: false
```

Then prompt for content:
```
Please provide the research content:

What to include:
- **Context**: Why was this researched?
- **Content**: What was discovered/decided?
- **Rationale**: Why this conclusion?
- **Alternatives**: What else was considered?
- **References**: Links, docs, or related issues
```

### Process

1. Parse arguments or run interactive flow
2. Generate unique ID (r001, r002, etc.)
3. Create entry object with metadata
4. Generate embedding for content
5. Store in `.claude/research/entries/<id>.json`
6. Update index at `.claude/research/index.json`
7. Upsert embedding to vector store (if cloud API available)
8. Confirm creation

### Entry Schema

```json
{
  "id": "r001",
  "type": "decision",
  "title": "Use Redis for session storage",
  "content": "We decided to use Redis for session tokens because...",
  "context": "Evaluating session storage options for auth system",
  "rationale": "Redis provides TTL support and fast lookups",
  "alternatives": ["PostgreSQL sessions", "JWT-only", "Memcached"],
  "tags": ["auth", "infrastructure", "redis"],
  "project": "popkit-cloud",
  "createdAt": "2024-12-09T10:30:00Z",
  "updatedAt": "2024-12-09T10:30:00Z",
  "references": ["#68", "https://redis.io/docs/"],
  "relatedEntries": []
}
```

---

## Subcommand: tag

Add or remove tags from research entries.

```
/popkit:research tag r001 --add security
/popkit:research tag r001 --remove deprecated
/popkit:research tag r001 --set auth,security,critical
```

### Flags

| Flag | Description |
|------|-------------|
| `--add` | Add tag(s) to entry |
| `--remove` | Remove tag(s) from entry |
| `--set` | Replace all tags with these (comma-separated) |

### Process

1. Load entry from `.claude/research/entries/<id>.json`
2. Modify tags based on flags
3. Update `updatedAt` timestamp
4. Save entry
5. Update index
6. Confirm changes

---

## Subcommand: show

View full details of a research entry.

```
/popkit:research show r001
/popkit:research show r001 --related
```

### Flags

| Flag | Description |
|------|-------------|
| `--related` | Also show related entries |

### Output Format

```
# Research Entry: r001

**Type:** Decision
**Title:** Use Redis for session storage
**Project:** popkit-cloud
**Created:** 2024-12-09
**Tags:** auth, infrastructure, redis

## Context

Evaluating session storage options for the authentication system.
Need fast lookups and automatic expiration.

## Content

We decided to use Redis for session tokens because:
1. Native TTL support for automatic expiration
2. Sub-millisecond read/write latency
3. Upstash provides serverless Redis compatible with Cloudflare Workers
4. Already using Upstash for rate limiting

## Alternatives Considered

- **PostgreSQL sessions**: Too slow for auth checks
- **JWT-only**: Can't revoke tokens server-side
- **Memcached**: Less feature-rich than Redis

## References

- Issue #68: Hosted Redis Service
- https://redis.io/docs/manual/expire/
- https://upstash.com/docs/redis/

---
Related: r015 (JWT refresh token handling)
```

---

## Subcommand: delete

Remove a research entry.

```
/popkit:research delete r001
/popkit:research delete r001 --confirm
```

### Flags

| Flag | Description |
|------|-------------|
| `--confirm` | Skip confirmation prompt |

### Process

Without `--confirm`:
```
Use AskUserQuestion tool with:
- question: "Delete research entry 'Use Redis for session storage'?"
- header: "Confirm"
- options:
  1. label: "Yes, delete"
     description: "Permanently remove this entry"
  2. label: "Cancel"
     description: "Keep the entry"
- multiSelect: false
```

1. Load entry to confirm it exists
2. Prompt for confirmation (unless --confirm)
3. Remove from `.claude/research/entries/`
4. Update index
5. Remove from vector store (if cloud API)
6. Confirm deletion

---

## Subcommand: merge

Process research branches from Claude Code Web sessions. Detects branches, previews content, and offers merge options.

```
/popkit:research merge                    # Process all detected branches
/popkit:research merge <branch>           # Process specific branch
/popkit:research merge --list             # List detected branches only
/popkit:research merge --dry-run          # Preview without executing
```

### Flags

| Flag | Description |
|------|-------------|
| `--list` | List detected branches without processing |
| `--dry-run` | Preview merge operations without executing |
| `--no-issue` | Merge without creating GitHub issue |
| `--delete` | Delete remote branch after merge |

### Branch Detection

Detects branches matching patterns:
- `claude/research-*` - Research branches from Claude Code Web
- `*-research-*` - Manual research branches
- Branches with `RESEARCH*.md` files

### Process

1. **Detect Branches**
   ```bash
   git fetch --all --prune
   git branch -r | grep -E "research|claude/"
   ```

2. **Preview Content**
   Shows for each branch:
   - Topic and age
   - Commit count
   - Documentation files found
   - Summary preview

3. **User Decision**
   ```
   Use AskUserQuestion tool with:
   - question: "Found research branch: [topic]. How should we process it?"
   - header: "Research"
   - options:
     - label: "Merge + Issue"
       description: "Squash-merge, organize docs, create GitHub issue"
     - label: "Merge Only"
       description: "Just merge the content"
     - label: "Skip"
       description: "Process later"
     - label: "Delete"
       description: "Discard research (cannot be undone)"
   - multiSelect: false
   ```

4. **Execute Based on Choice**

   **Merge + Issue:**
   - Squash merge branch
   - Move docs to `docs/research/`
   - Create GitHub issue with findings
   - Delete remote branch

   **Merge Only:**
   - Squash merge branch
   - Optionally delete remote

   **Skip:**
   - No action, process later

   **Delete:**
   - Confirm, then delete remote branch

### Output Format

```
## Research Branches Detected

| Branch | Topic | Age | Commits | Docs |
|--------|-------|-----|---------|------|
| claude/research-vhs-01Rc... | VHS tape generation | 26h | 1 | 2 |
| claude/review-changelog... | Claude Code 2.0.67 | 20h | 1 | 1 |

Processing: research-vhs-01Rc...
[ok] Merged to master
[ok] Docs moved to docs/research/
[ok] Issue #220 created
[ok] Remote branch deleted

## Summary
| Branch | Action | Result |
|--------|--------|--------|
| research-vhs... | Merged + Issue | #220 |
| review-changelog... | Skipped | - |
```

### Integration

This command invokes the `pop-research-merge` skill which handles:
- Conflict detection via `scripts/detect_conflicts.py`
- Finding merging via `scripts/merge_findings.py`
- Workflow coordination via `workflows/merge-workflow.json`

---

## Storage Structure

```
.claude/
  research/
    index.json          # Entry index with metadata
    entries/
      r001.json         # Full entry content
      r002.json
      ...
```

### index.json Schema

```json
{
  "version": "1.0.0",
  "lastUpdated": "2024-12-09T10:30:00Z",
  "entries": [
    {
      "id": "r001",
      "type": "decision",
      "title": "Use Redis for session storage",
      "tags": ["auth", "infrastructure"],
      "project": "popkit-cloud",
      "createdAt": "2024-12-09T10:30:00Z",
      "embeddingId": "vec_r001"
    }
  ],
  "tagIndex": {
    "auth": ["r001", "r015"],
    "infrastructure": ["r001"],
    "billing": ["r002"]
  },
  "projectIndex": {
    "popkit-cloud": ["r001", "r002"],
    "myapp": ["r015"]
  }
}
```

---

## Auto-Surfacing During Development

Research entries are automatically surfaced when relevant to current work:

### Trigger Points

1. **Starting work on an issue** (`/popkit:dev work #N`)
   - Search research by issue keywords
   - Display related decisions/findings

2. **Before making architectural decisions**
   - Prompt: "Found 3 related research entries - review?"
   - Link to relevant prior decisions

3. **During code review**
   - Check if changes conflict with documented decisions
   - Surface relevant learnings

### Integration

The `pop-research-capture` skill is invoked automatically:
- After completing a spike or investigation
- When making significant architectural decisions
- At end of session (session capture prompts for new learnings)

---

## Cloud Sync (Premium)

For Pro/Team users with cloud API:

```
/popkit:research sync              # Sync local entries to cloud
/popkit:research sync --pull       # Pull shared team entries
```

Team tier enables:
- Shared team knowledge base
- Cross-project research discovery
- Collective learning from team decisions

---

## Examples

```bash
# List all research
/popkit:research

# Search for relevant entries
/popkit:research search "authentication patterns"

# Add a decision
/popkit:research add --type decision --title "Use Stripe for billing"

# Interactive add
/popkit:research add --interactive

# View entry details
/popkit:research show r001

# Tag management
/popkit:research tag r001 --add critical
/popkit:research tag r001 --remove deprecated

# Delete with confirmation
/popkit:research delete r015
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Storage | `.claude/research/` directory |
| Indexing | `index.json` with tag/project indexes |
| Embeddings | Voyage AI via cloud API |
| Vector Store | Upstash Vector (Premium) |
| Auto-surface | Integration with dev workflow |
| Session | `pop-session-capture` prompts for learnings |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:dev work #N` | Surfaces related research |
| `/popkit:knowledge` | External documentation cache |
| `pop-research-capture` | Skill for capturing research |
