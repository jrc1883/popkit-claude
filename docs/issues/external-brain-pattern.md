# External Brain Pattern - Knowledge Externalization

> **Type**: Feature
> **Priority**: Low (Future)
> **Epic**: Context Management
> **Depends On**: Context Boundary Hook, Tiered Retention, Checkpoints
> **Estimated Complexity**: High

## Summary

Implement an **External Brain** system that moves discoveries, patterns, and learnings out of conversation context into structured file storage, retrievable on-demand via semantic search. This enables indefinite knowledge accumulation without context bloat.

## Problem Statement

Even with retention policies and checkpoints, valuable knowledge gets lost:

1. **Session boundaries**: Discoveries from last week aren't in today's context
2. **Context compaction**: When `/compact` runs, nuanced learnings get summarized away
3. **Cross-project patterns**: Solution from Project A could help Project B
4. **Team knowledge**: One developer's discoveries don't benefit others

The "brain" should persist independently of conversation context.

## Solution

Create a structured knowledge store that:
- **Captures** discoveries, decisions, and patterns automatically
- **Persists** across sessions, projects, and even users (opt-in)
- **Retrieves** relevant knowledge via semantic search
- **Integrates** with existing embeddings infrastructure

### Knowledge Model

```
~/.claude/popkit/brain/
├── index.db                    # SQLite: embeddings + metadata
├── projects/
│   └── my-app/
│       ├── discoveries.jsonl   # What we learned about this project
│       ├── decisions.jsonl     # Architecture/design decisions
│       ├── patterns.jsonl      # Code patterns identified
│       └── issues/
│           └── 123/
│               ├── context.md  # Issue-specific learnings
│               └── solution.md # How it was solved
├── global/
│   ├── patterns.jsonl          # Cross-project patterns
│   ├── errors.jsonl            # Common errors + solutions
│   └── tools.jsonl             # Tool usage patterns
└── shared/                     # Opt-in team sharing
    └── patterns.jsonl
```

### Knowledge Types

| Type | Description | Capture Trigger | Example |
|------|-------------|-----------------|---------|
| **Discovery** | Facts learned about codebase | File read + insight extraction | "Auth tokens stored in Redis, not DB" |
| **Decision** | Why something was done a certain way | User confirms, commit message | "Using JWT because stateless scaling needed" |
| **Pattern** | Reusable code/solution pattern | Similar code detected 3+ times | "Error handling pattern: try/catch with logger" |
| **Error** | Bug + solution pair | Test pass after fix | "TypeError on null: added null check" |
| **Tool Usage** | Effective tool combinations | Successful workflow completion | "For React: grep components → read → edit → test" |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Conversation Context                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Current  │  │ Active   │  │ Recent   │  │ Retrieved│        │
│  │ Task     │  │ File     │  │ Tools    │  │ Knowledge│◄───┐   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
└─────────────────────────────────────────────────────────────│───┘
                                                              │
                         ┌────────────────┐                   │
                         │ Knowledge      │                   │
                         │ Retriever      │───────────────────┘
                         │ (semantic)     │
                         └───────┬────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────┐
│                    External Brain                                │
│  ┌──────────────┐  ┌──────────┴───────┐  ┌──────────────┐      │
│  │ Discoveries  │  │ Embeddings Index │  │ Patterns     │      │
│  │ (project)    │  │ (Voyage AI)      │  │ (global)     │      │
│  └──────────────┘  └──────────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐      │
│  │ Decisions    │  │ Errors           │  │ Tool Usage   │      │
│  │ (project)    │  │ (global)         │  │ (global)     │      │
│  └──────────────┘  └──────────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Integration with Existing Infrastructure

### 1. Extend Embedding Store

Build on `hooks/utils/embedding_store.py`:

```python
class BrainStore(EmbeddingStore):
    """Extended embedding store for External Brain."""

    KNOWLEDGE_TYPES = ["discovery", "decision", "pattern", "error", "tool_usage"]

    def __init__(self, brain_dir: Path = None):
        self.brain_dir = brain_dir or Path.home() / ".claude" / "popkit" / "brain"
        super().__init__(db_path=self.brain_dir / "index.db")

    def add_knowledge(
        self,
        content: str,
        knowledge_type: str,
        project: Optional[str] = None,
        issue: Optional[int] = None,
        metadata: Dict = None
    ) -> str:
        """Add knowledge to the brain."""
        # Generate embedding
        embedding = self.embed(content)

        # Store in SQLite
        knowledge_id = self._store_knowledge(
            content=content,
            embedding=embedding,
            knowledge_type=knowledge_type,
            project=project,
            issue=issue,
            metadata=metadata or {}
        )

        # Also append to JSONL for human readability
        self._append_jsonl(knowledge_type, project, {
            "id": knowledge_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        })

        return knowledge_id

    def recall(
        self,
        query: str,
        project: Optional[str] = None,
        knowledge_types: List[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Retrieve relevant knowledge via semantic search."""
        query_embedding = self.embed(query)

        results = self._semantic_search(
            embedding=query_embedding,
            project=project,
            knowledge_types=knowledge_types or self.KNOWLEDGE_TYPES,
            limit=limit
        )

        return results
```

### 2. Knowledge Extractor Hook

New file `hooks/knowledge-extractor.py`:

```python
class KnowledgeExtractor:
    """PostToolUse hook that extracts knowledge from tool results."""

    DISCOVERY_SIGNALS = [
        r"found .+ at",
        r"using .+ for",
        r"configured .+ in",
        r"pattern: .+",
        r"convention: .+",
    ]

    DECISION_SIGNALS = [
        r"decided to",
        r"choosing .+ because",
        r"will use .+ for",
        r"architecture: .+",
    ]

    def extract(self, tool_name: str, tool_input: Dict, tool_result: str) -> List[Dict]:
        """Extract knowledge from tool result."""
        knowledge_items = []

        # Discovery extraction
        if tool_name == "Read":
            discoveries = self._extract_discoveries(tool_input, tool_result)
            knowledge_items.extend(discoveries)

        # Pattern extraction
        if tool_name in ["Grep", "Glob"]:
            patterns = self._extract_patterns(tool_input, tool_result)
            knowledge_items.extend(patterns)

        # Error/solution extraction
        if self._is_error_result(tool_result):
            error_knowledge = self._extract_error(tool_name, tool_result)
            if error_knowledge:
                knowledge_items.append(error_knowledge)

        return knowledge_items

    def _extract_discoveries(self, tool_input: Dict, tool_result: str) -> List[Dict]:
        """Extract discoveries from file read."""
        discoveries = []
        file_path = tool_input.get("file_path", "")

        # Configuration files → discovery about project setup
        if any(cfg in file_path for cfg in ["config", "env", "settings"]):
            # Extract key configuration details
            ...

        # Architecture files → discovery about structure
        if any(arch in file_path for arch in ["architecture", "design", "adr"]):
            ...

        return discoveries
```

### 3. Automatic Externalization at Boundaries

Extend context boundary hook:

```python
# In hooks/context-boundary.py
def on_boundary_crossed(self, boundary_type: str, details: Dict) -> Dict:
    # ... checkpoint logic ...

    # Externalize knowledge at boundaries
    if boundary_type in ["commit_pushed", "pr_created", "issue_closed"]:
        brain = BrainStore()

        # Extract decisions from commit/PR
        if boundary_type == "commit_pushed":
            decision = self._extract_commit_decision(details)
            if decision:
                brain.add_knowledge(
                    content=decision["content"],
                    knowledge_type="decision",
                    project=self.project_name,
                    metadata={"commit": details["commit_hash"]}
                )

        # Mark issue knowledge as complete
        if boundary_type == "issue_closed":
            brain.add_knowledge(
                content=details.get("solution_summary", ""),
                knowledge_type="pattern",
                project=self.project_name,
                issue=details["issue_number"],
                metadata={"type": "issue_solution"}
            )
```

### 4. Knowledge Retrieval Skill

New skill `skills/pop-recall/SKILL.md`:

```markdown
---
name: recall
description: "Retrieve relevant knowledge from External Brain. Use when starting new tasks, debugging unfamiliar code, or looking for patterns. Searches across discoveries, decisions, patterns, and error solutions."
---

# Knowledge Recall

## Overview

Search the External Brain for relevant knowledge about the current task.

## Process

### Step 1: Determine Query

Based on current context:
- Current task description
- Files being worked on
- Error messages (if debugging)
- Feature being implemented

### Step 2: Search Brain

```python
from brain_store import BrainStore

brain = BrainStore()
results = brain.recall(
    query="[current task/error/pattern]",
    project="[current project]",  # Prioritize project-specific
    limit=5
)
```

### Step 3: Present Relevant Knowledge

Format results:

```
📚 Relevant Knowledge (3 matches)

1. [Discovery] Auth tokens in Redis
   Project: my-app | Confidence: 0.89
   "Auth tokens stored in Redis (not DB) for faster validation.
    See src/auth/token-store.ts"

2. [Pattern] Error handling
   Global | Confidence: 0.82
   "Standard error handling: wrap in try/catch, log with context,
    return typed error response"

3. [Decision] JWT over sessions
   Project: my-app | Confidence: 0.78
   "Using JWT because: stateless scaling, mobile app support,
    microservices compatibility"
```

### Step 4: Offer to Load Details

If user wants more:
- Read referenced files
- Show full decision context
- Load related patterns
```

### 5. Power Mode Integration

Extend checkin hook to query brain:

```python
# In power-mode/checkin-hook.py
def _perform_checkin(self, tool_name: str, tool_input: Dict, tool_result: Any) -> Dict:
    # ... existing checkin logic ...

    # Query External Brain for relevant knowledge
    if self.brain_enabled:
        brain = BrainStore()
        current_context = self._get_current_context()

        relevant = brain.recall(
            query=current_context,
            project=self.project_name,
            limit=2
        )

        if relevant:
            checkin["brain_recall"] = [
                {
                    "type": r["knowledge_type"],
                    "content": r["content"][:100],
                    "confidence": r["similarity"]
                }
                for r in relevant
            ]
```

## Command Interface

### Add Knowledge Manually

```bash
/popkit:brain add "Auth uses Redis for token storage, configured in src/config/redis.ts"

# Output:
# ✓ Knowledge added to External Brain
#
# Type: discovery (auto-detected)
# Project: my-app
# ID: kn_abc123
#
# Related existing knowledge:
# - [decision] "Using Redis for caching" (0.85 similarity)
```

### Search Knowledge

```bash
/popkit:brain recall "how does authentication work"

# Output:
# 📚 External Brain Search: "how does authentication work"
#
# Found 4 relevant items:
#
# 1. [discovery] Auth tokens in Redis (0.91)
#    Project: my-app
#    Auth tokens stored in Redis for faster validation...
#
# 2. [decision] JWT over sessions (0.87)
#    Project: my-app
#    Using JWT because: stateless scaling...
#
# 3. [pattern] Token refresh flow (0.82)
#    Global
#    Standard pattern: check expiry → refresh if needed → retry...
#
# 4. [error] Token validation TypeError (0.76)
#    Project: my-app
#    Fixed by adding null check before decode...
#
# [1] Load full details  [2] Search again  [3] Add to context
```

### View Brain Status

```bash
/popkit:brain status

# Output:
# External Brain Status
# ─────────────────────
#
# Location: ~/.claude/popkit/brain/
# Index size: 2.3 MB
#
# Knowledge by type:
#   Discoveries: 45 (23 this project)
#   Decisions: 12 (8 this project)
#   Patterns: 34 (15 global)
#   Errors: 28 (20 global)
#   Tool usage: 15 (global)
#
# Recent additions:
#   - [discovery] Redis token config (2h ago)
#   - [decision] Using JWT (5h ago)
#   - [pattern] Error handling (yesterday)
#
# Embedding model: voyage-3.5
# Last sync: 10 minutes ago
```

### Export/Import for Teams

```bash
# Export project knowledge
/popkit:brain export --project my-app --output knowledge.json

# Import shared knowledge
/popkit:brain import --file team-patterns.json --scope global
```

## Implementation Plan

### Phase 1: Brain Store Foundation

1. Create `hooks/utils/brain_store.py`
2. Extend SQLite schema for knowledge types
3. Implement JSONL persistence
4. Add semantic search

**Files:**
- `hooks/utils/brain_store.py` (new)

### Phase 2: Knowledge Extraction

1. Create `hooks/knowledge-extractor.py`
2. Implement discovery extraction from file reads
3. Implement pattern detection
4. Implement error/solution pairing

**Files:**
- `hooks/knowledge-extractor.py` (new)

### Phase 3: Boundary Integration

1. Externalize at context boundaries
2. Extract decisions from commits/PRs
3. Capture issue solutions

**Files:**
- `hooks/context-boundary.py` (modify)

### Phase 4: Recall Skill

1. Create `pop-recall` skill
2. Implement search formatting
3. Add context loading

**Files:**
- `skills/pop-recall/SKILL.md` (new)

### Phase 5: Commands

1. Create `/popkit:brain` command
2. Implement add, recall, status, export, import

**Files:**
- `commands/brain.md` (new)

### Phase 6: Power Mode Integration

1. Add brain recall to checkins
2. Auto-suggest relevant knowledge
3. Track knowledge usage

**Files:**
- `power-mode/checkin-hook.py` (modify)

## Configuration

```json
{
  "brain": {
    "enabled": true,
    "location": "~/.claude/popkit/brain",
    "embedding_model": "voyage-3.5",
    "auto_extract": {
      "discoveries": true,
      "patterns": true,
      "errors": true,
      "decisions": "on_commit"
    },
    "recall": {
      "auto_on_task_start": true,
      "max_results": 5,
      "min_confidence": 0.7
    },
    "sharing": {
      "enabled": false,
      "endpoint": null
    },
    "retention": {
      "max_items_per_type": 1000,
      "prune_below_confidence": 0.5
    }
  }
}
```

## Acceptance Criteria

- [ ] BrainStore persists knowledge to SQLite + JSONL
- [ ] Knowledge extraction identifies discoveries, patterns, errors
- [ ] Semantic search returns relevant knowledge
- [ ] Context boundaries trigger externalization
- [ ] `/popkit:brain` commands work (add, recall, status)
- [ ] `pop-recall` skill retrieves and formats knowledge
- [ ] Power Mode checkins query brain
- [ ] Configuration allows customization

## Privacy Considerations

1. **Local by default**: All data stays in `~/.claude/popkit/brain/`
2. **Project isolation**: Project-specific knowledge separate from global
3. **Opt-in sharing**: Team sharing requires explicit configuration
4. **Anonymization**: Shared patterns stripped of project-specific details
5. **Export review**: User can review before exporting

## Metrics to Track

| Metric | Purpose |
|--------|---------|
| Knowledge items by type | Understand what's being captured |
| Recall hit rate | How often retrieved knowledge was useful |
| Cross-project matches | Value of global patterns |
| Time to resolution | Does brain speed up debugging? |

## Open Questions

1. **Deduplication**: How to handle similar knowledge from different sessions?
2. **Decay**: Should old knowledge lose relevance over time?
3. **Validation**: How to verify extracted knowledge is accurate?
4. **Conflicts**: What if different sessions recorded contradictory decisions?
5. **Sync**: How to handle brain across multiple machines?

---

## PopKit Guidance

```yaml
workflow_type: brainstorm_first
complexity: high
power_mode: recommended
phases:
  - discovery (research existing embedding infrastructure)
  - architecture (design brain schema and extraction)
  - implementation (core brain store)
  - implementation (extraction hooks)
  - implementation (recall and commands)
  - testing
  - documentation
agents:
  primary: code-architect
  supporting: ai-engineer, test-writer-fixer
quality_gates:
  - python-lint
  - hook-tests
  - embedding-tests
```
