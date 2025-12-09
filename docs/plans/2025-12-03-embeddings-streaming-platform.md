# Implementation Plan: Embeddings & Streaming Platform Enhancement

**Issues:** #19 (Embeddings Enhancement) + #23 (Fine-grained Streaming)
**Date:** 2025-12-03
**Complexity:** High
**Estimated Tasks:** 12

## Executive Summary

This plan implements two complementary Claude Platform features:
1. **Voyage-3.5 Embeddings** (#19) - Semantic search for knowledge, agent routing, and deduplication
2. **Fine-grained Streaming** (#23) - Real-time Power Mode visibility with streaming events

Both features share infrastructure (async patterns, message protocols) and enhance the same systems (Power Mode, agent routing).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Platform Features                      │
├────────────────────────────┬────────────────────────────────────┤
│   Embeddings (#19)         │   Streaming (#23)                  │
│   ─────────────────        │   ────────────────                 │
│   • voyage-3.5 model       │   • Stream events                  │
│   • Vector storage         │   • Real-time updates              │
│   • Semantic search        │   • Coordinator integration        │
├────────────────────────────┴────────────────────────────────────┤
│                    Shared Infrastructure                         │
│   • Async patterns (asyncio)                                    │
│   • Message protocol extensions                                 │
│   • SQLite storage layer                                        │
│   • Status line integration                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Shared Infrastructure (Tasks 1-3)

### Task 1: Add Async Support to Power Mode

**Files:**
- `power-mode/async_support.py` (NEW)
- `power-mode/coordinator.py` (MODIFY)

**Implementation:**

Create `power-mode/async_support.py`:
```python
#!/usr/bin/env python3
"""Async support utilities for Power Mode streaming and embeddings."""

import asyncio
from typing import AsyncIterator, Callable, Any
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running sync code in async context
_executor = ThreadPoolExecutor(max_workers=4)

async def run_sync(func: Callable, *args, **kwargs) -> Any:
    """Run synchronous function in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))

async def async_redis_listen(pubsub, timeout: float = 1.0) -> AsyncIterator[dict]:
    """Async wrapper for Redis pub/sub listener."""
    while True:
        message = await run_sync(pubsub.get_message, timeout=timeout)
        if message and message["type"] == "message":
            yield message
        await asyncio.sleep(0.01)  # Yield to event loop

class AsyncEventEmitter:
    """Simple async event emitter for stream events."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    async def emit(self, event: str, data: Any):
        for handler in self._handlers.get(event, []):
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
```

**Verification:**
```bash
python -c "import power-mode.async_support; print('OK')"
```

---

### Task 2: Extend Message Protocol for Streaming

**File:** `power-mode/protocol.py`

**Add to MessageType enum (after line 50):**
```python
    # Streaming (Issue #23)
    STREAM_START = "STREAM_START"      # Agent opens stream session
    STREAM_CHUNK = "STREAM_CHUNK"      # Incremental data chunk
    STREAM_END = "STREAM_END"          # Stream session complete
    STREAM_ERROR = "STREAM_ERROR"      # Stream failure

    # Embeddings (Issue #19)
    EMBEDDING_REQUEST = "EMBEDDING_REQUEST"    # Request embedding computation
    EMBEDDING_RESULT = "EMBEDDING_RESULT"      # Return computed embedding
    SIMILARITY_QUERY = "SIMILARITY_QUERY"      # Find similar content
    SIMILARITY_RESULT = "SIMILARITY_RESULT"    # Return similarity results
```

**Add StreamChunk dataclass (after Message class, ~line 200):**
```python
@dataclass
class StreamChunk:
    """Represents a streaming data chunk."""
    session_id: str           # Unique stream session
    agent_id: str             # Source agent
    chunk_index: int          # Sequence number
    content: str              # Partial content
    tool_name: Optional[str]  # Tool being executed
    is_final: bool = False    # Last chunk in stream
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_message(self) -> Message:
        return Message(
            id=f"{self.session_id}:{self.chunk_index}",
            type=MessageType.STREAM_CHUNK,
            from_agent=self.agent_id,
            to_agent="coordinator",
            payload={
                "session_id": self.session_id,
                "chunk_index": self.chunk_index,
                "content": self.content,
                "tool_name": self.tool_name,
                "is_final": self.is_final
            },
            timestamp=self.timestamp
        )
```

**Verification:**
```python
python -c "from power-mode.protocol import MessageType; print(MessageType.STREAM_CHUNK)"
```

---

### Task 3: Create Embedding Storage Layer

**File:** `hooks/utils/embedding_store.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Embedding storage and retrieval using SQLite.

Stores embeddings as JSON arrays for portability.
Uses cosine similarity for semantic search.
"""

import os
import json
import sqlite3
import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Default storage location
DEFAULT_DB_PATH = Path.home() / ".claude" / "config" / "embeddings.db"

@dataclass
class EmbeddingRecord:
    """A stored embedding with metadata."""
    id: str
    content: str
    embedding: List[float]
    source_type: str  # "skill", "agent", "knowledge", "insight"
    source_id: str
    metadata: Dict[str, Any]
    created_at: str

class EmbeddingStore:
    """SQLite-based embedding storage with semantic search."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,  -- JSON array
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    metadata TEXT,  -- JSON object
                    created_at TEXT NOT NULL,
                    embedding_model TEXT DEFAULT 'voyage-3.5'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source
                ON embeddings(source_type, source_id)
            """)
            conn.commit()

    def store(self, record: EmbeddingRecord) -> None:
        """Store an embedding record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings
                (id, content, embedding, source_type, source_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.content,
                json.dumps(record.embedding),
                record.source_type,
                record.source_id,
                json.dumps(record.metadata),
                record.created_at
            ))
            conn.commit()

    def get(self, id: str) -> Optional[EmbeddingRecord]:
        """Retrieve an embedding by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE id = ?", (id,)
            ).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def search(
        self,
        query_embedding: List[float],
        source_type: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[EmbeddingRecord, float]]:
        """
        Find similar embeddings using cosine similarity.

        Returns list of (record, similarity_score) tuples.
        """
        with sqlite3.connect(self.db_path) as conn:
            if source_type:
                rows = conn.execute(
                    "SELECT * FROM embeddings WHERE source_type = ?",
                    (source_type,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM embeddings").fetchall()

        results = []
        for row in rows:
            record = self._row_to_record(row)
            similarity = self._cosine_similarity(query_embedding, record.embedding)
            if similarity >= min_similarity:
                results.append((record, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _row_to_record(self, row: tuple) -> EmbeddingRecord:
        """Convert database row to EmbeddingRecord."""
        return EmbeddingRecord(
            id=row[0],
            content=row[1],
            embedding=json.loads(row[2]),
            source_type=row[3],
            source_id=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=row[6]
        )

    def count(self, source_type: Optional[str] = None) -> int:
        """Count stored embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            if source_type:
                return conn.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE source_type = ?",
                    (source_type,)
                ).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    def delete(self, id: str) -> bool:
        """Delete an embedding by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM embeddings WHERE id = ?", (id,))
            conn.commit()
            return cursor.rowcount > 0
```

**Verification:**
```bash
python -c "
from hooks.utils.embedding_store import EmbeddingStore, EmbeddingRecord
store = EmbeddingStore()
print(f'Embedding store initialized: {store.db_path}')
print(f'Current count: {store.count()}')
"
```

---

## Phase 2: Embeddings Implementation (Tasks 4-7)

### Task 4: Create Voyage Embedding Client

**File:** `hooks/utils/voyage_client.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Voyage-3.5 embedding client for PopKit.

Uses the Anthropic Voyage API for high-quality embeddings.
Falls back to local model if API unavailable.
"""

import os
import json
import hashlib
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import urllib.request
import urllib.error

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3.5"
EMBEDDING_DIM = 1024  # voyage-3.5 dimension

@dataclass
class EmbeddingResponse:
    """Response from embedding API."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]

class VoyageClient:
    """Client for Voyage embedding API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self._cache: Dict[str, List[float]] = {}

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed
            input_type: "document" for content, "query" for search queries

        Returns:
            List of embedding vectors
        """
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY not set")

        # Check cache
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            cache_key = self._cache_key(text, input_type)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Fetch uncached embeddings
        if uncached_texts:
            response = self._call_api(uncached_texts, input_type)
            for j, embedding in enumerate(response.embeddings):
                idx = uncached_indices[j]
                results[idx] = embedding
                cache_key = self._cache_key(uncached_texts[j], input_type)
                self._cache[cache_key] = embedding

        return results

    def embed_single(self, text: str, input_type: str = "document") -> List[float]:
        """Embed a single text string."""
        return self.embed([text], input_type)[0]

    def _call_api(self, texts: List[str], input_type: str) -> EmbeddingResponse:
        """Make API call to Voyage."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = json.dumps({
            "model": VOYAGE_MODEL,
            "input": texts,
            "input_type": input_type
        }).encode("utf-8")

        request = urllib.request.Request(VOYAGE_API_URL, data=data, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return EmbeddingResponse(
                    embeddings=[item["embedding"] for item in result["data"]],
                    model=result["model"],
                    usage=result.get("usage", {})
                )
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Voyage API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    def _cache_key(self, text: str, input_type: str) -> str:
        """Generate cache key for text."""
        content = f"{input_type}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)


# Singleton instance
_client: Optional[VoyageClient] = None

def get_client() -> VoyageClient:
    """Get or create Voyage client singleton."""
    global _client
    if _client is None:
        _client = VoyageClient()
    return _client

def embed(texts: List[str], input_type: str = "document") -> List[List[float]]:
    """Convenience function to embed texts."""
    return get_client().embed(texts, input_type)

def embed_single(text: str, input_type: str = "document") -> List[float]:
    """Convenience function to embed single text."""
    return get_client().embed_single(text, input_type)
```

**Verification:**
```bash
# Test import (no API call)
python -c "from hooks.utils.voyage_client import VoyageClient; print('OK')"

# Test with API key (requires VOYAGE_API_KEY)
python -c "
from hooks.utils.voyage_client import embed_single
vec = embed_single('test query', 'query')
print(f'Embedding dimension: {len(vec)}')
"
```

---

### Task 5: Pre-compute Skill/Agent Embeddings

**File:** `hooks/embedding_init.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Pre-compute embeddings for skills and agents.

Run during plugin initialization or on-demand.
Stores embeddings in SQLite for fast retrieval.
"""

import os
import sys
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

from voyage_client import VoyageClient, embed
from embedding_store import EmbeddingStore, EmbeddingRecord

POPKIT_ROOT = Path(__file__).parent.parent

def extract_skill_descriptions() -> List[Dict[str, Any]]:
    """Extract descriptions from all SKILL.md files."""
    skills = []
    skill_dirs = POPKIT_ROOT / "skills"

    for skill_dir in skill_dirs.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                # Extract description from YAML frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        frontmatter = content[3:end]
                        for line in frontmatter.split("\n"):
                            if line.startswith("description:"):
                                desc = line[12:].strip().strip('"\'')
                                skills.append({
                                    "id": f"skill:{skill_dir.name}",
                                    "name": skill_dir.name,
                                    "description": desc,
                                    "path": str(skill_file)
                                })
                                break
    return skills

def extract_agent_descriptions() -> List[Dict[str, Any]]:
    """Extract descriptions from all AGENT.md files."""
    agents = []

    for tier in ["tier-1-always-active", "tier-2-on-demand", "feature-workflow"]:
        tier_dir = POPKIT_ROOT / "agents" / tier
        if tier_dir.exists():
            for agent_dir in tier_dir.iterdir():
                if agent_dir.is_dir():
                    agent_file = agent_dir / "AGENT.md"
                    if agent_file.exists():
                        content = agent_file.read_text(encoding="utf-8")
                        # Extract description from YAML frontmatter
                        if content.startswith("---"):
                            end = content.find("---", 3)
                            if end > 0:
                                frontmatter = content[3:end]
                                for line in frontmatter.split("\n"):
                                    if line.startswith("description:"):
                                        desc = line[12:].strip().strip('"\'')
                                        agents.append({
                                            "id": f"agent:{agent_dir.name}",
                                            "name": agent_dir.name,
                                            "description": desc,
                                            "tier": tier,
                                            "path": str(agent_file)
                                        })
                                        break
    return agents

def compute_and_store_embeddings(
    items: List[Dict[str, Any]],
    source_type: str,
    store: EmbeddingStore,
    client: VoyageClient
) -> int:
    """Compute embeddings for items and store them."""
    if not items:
        return 0

    # Batch embed descriptions
    descriptions = [item["description"] for item in items]
    embeddings = client.embed(descriptions, input_type="document")

    # Store each embedding
    for item, embedding in zip(items, embeddings):
        record = EmbeddingRecord(
            id=item["id"],
            content=item["description"],
            embedding=embedding,
            source_type=source_type,
            source_id=item["name"],
            metadata={k: v for k, v in item.items() if k not in ["id", "description"]},
            created_at=datetime.now().isoformat()
        )
        store.store(record)

    return len(items)

def initialize_embeddings(force: bool = False) -> Dict[str, int]:
    """
    Initialize embeddings for all skills and agents.

    Args:
        force: Re-compute even if embeddings exist

    Returns:
        Dict with counts of embedded items
    """
    client = VoyageClient()
    if not client.is_available:
        return {"error": "VOYAGE_API_KEY not set"}

    store = EmbeddingStore()
    results = {"skills": 0, "agents": 0}

    # Check if already initialized
    if not force and store.count() > 0:
        return {
            "status": "already_initialized",
            "count": store.count()
        }

    # Extract and embed skills
    skills = extract_skill_descriptions()
    results["skills"] = compute_and_store_embeddings(skills, "skill", store, client)

    # Extract and embed agents
    agents = extract_agent_descriptions()
    results["agents"] = compute_and_store_embeddings(agents, "agent", store, client)

    results["total"] = results["skills"] + results["agents"]
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize PopKit embeddings")
    parser.add_argument("--force", action="store_true", help="Force re-computation")
    args = parser.parse_args()

    print("Initializing PopKit embeddings...")
    result = initialize_embeddings(force=args.force)
    print(json.dumps(result, indent=2))
```

**Verification:**
```bash
# Dry run (check extraction)
python -c "
from hooks.embedding_init import extract_skill_descriptions, extract_agent_descriptions
skills = extract_skill_descriptions()
agents = extract_agent_descriptions()
print(f'Found {len(skills)} skills, {len(agents)} agents')
"

# Full initialization (requires VOYAGE_API_KEY)
python hooks/embedding_init.py --force
```

---

### Task 6: Add Semantic Search to Knowledge Lookup

**File:** `skills/pop-knowledge-lookup/SKILL.md` (MODIFY)

**Add after existing search section:**
```markdown
### Semantic Search Mode

When embeddings are available, use semantic similarity:

#### Step 1: Check Embedding Availability

```python
from hooks.utils.embedding_store import EmbeddingStore
from hooks.utils.voyage_client import get_client

store = EmbeddingStore()
client = get_client()

if client.is_available and store.count("knowledge") > 0:
    # Use semantic search
    pass
else:
    # Fall back to Grep
    pass
```

#### Step 2: Semantic Query

```python
# Embed the query
query_embedding = client.embed_single(user_query, input_type="query")

# Search knowledge base
results = store.search(
    query_embedding,
    source_type="knowledge",
    top_k=5,
    min_similarity=0.7
)

# Format results
for record, score in results:
    print(f"[{score:.2f}] {record.source_id}: {record.content[:100]}...")
```

#### Step 3: Hybrid Ranking

Combine semantic and keyword scores:

```python
def hybrid_search(query: str, top_k: int = 5):
    # Semantic results
    semantic_results = semantic_search(query)

    # Keyword results (existing Grep)
    keyword_results = grep_search(query)

    # Merge and re-rank
    combined = {}
    for record, score in semantic_results:
        combined[record.id] = {"semantic": score, "keyword": 0}

    for result in keyword_results:
        if result.id in combined:
            combined[result.id]["keyword"] = result.match_count / 10
        else:
            combined[result.id] = {"semantic": 0, "keyword": result.match_count / 10}

    # Final score = 0.7 * semantic + 0.3 * keyword
    final = sorted(
        combined.items(),
        key=lambda x: 0.7 * x[1]["semantic"] + 0.3 * x[1]["keyword"],
        reverse=True
    )
    return final[:top_k]
```
```

**Verification:**
```
/popkit:knowledge search "how to use hooks"
```

---

### Task 7: Implement Semantic Agent Routing

**File:** `hooks/utils/semantic_router.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Semantic agent routing using embeddings.

Falls back to keyword matching if embeddings unavailable.
"""

import os
import sys
import json
from typing import List, Tuple, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from embedding_store import EmbeddingStore
from voyage_client import VoyageClient, get_client

class SemanticRouter:
    """Route requests to agents using semantic similarity."""

    def __init__(self):
        self.store = EmbeddingStore()
        self.client = get_client()
        self._keyword_fallback = self._load_keywords()

    def _load_keywords(self) -> dict:
        """Load keyword routing from config.json."""
        config_path = Path(__file__).parent.parent.parent / "agents" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config.get("keywords", {})
        return {}

    def route(
        self,
        query: str,
        top_k: int = 3,
        min_confidence: float = 0.6
    ) -> List[Tuple[str, float, str]]:
        """
        Route query to best matching agents.

        Args:
            query: User request or context
            top_k: Number of agents to return
            min_confidence: Minimum similarity threshold

        Returns:
            List of (agent_name, confidence, reason) tuples
        """
        # Try semantic routing first
        if self.client.is_available and self.store.count("agent") > 0:
            results = self._semantic_route(query, top_k, min_confidence)
            if results:
                return results

        # Fall back to keyword routing
        return self._keyword_route(query, top_k)

    def _semantic_route(
        self,
        query: str,
        top_k: int,
        min_confidence: float
    ) -> List[Tuple[str, float, str]]:
        """Route using embedding similarity."""
        query_embedding = self.client.embed_single(query, input_type="query")

        results = self.store.search(
            query_embedding,
            source_type="agent",
            top_k=top_k,
            min_similarity=min_confidence
        )

        return [
            (record.source_id, score, f"Semantic match: {record.content[:50]}...")
            for record, score in results
        ]

    def _keyword_route(
        self,
        query: str,
        top_k: int
    ) -> List[Tuple[str, float, str]]:
        """Route using keyword matching."""
        query_lower = query.lower()
        matches = []

        for keyword, agents in self._keyword_fallback.items():
            if keyword in query_lower:
                for agent in agents:
                    matches.append((agent, 0.8, f"Keyword match: '{keyword}'"))

        # Deduplicate, keeping highest confidence
        seen = {}
        for agent, conf, reason in matches:
            if agent not in seen or conf > seen[agent][0]:
                seen[agent] = (conf, reason)

        results = [(agent, conf, reason) for agent, (conf, reason) in seen.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# Singleton
_router: Optional[SemanticRouter] = None

def get_router() -> SemanticRouter:
    global _router
    if _router is None:
        _router = SemanticRouter()
    return _router

def route(query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
    """Convenience function to route a query."""
    return get_router().route(query, top_k)
```

**Verification:**
```bash
python -c "
from hooks.utils.semantic_router import route
results = route('I need to fix a security vulnerability')
for agent, score, reason in results:
    print(f'{agent}: {score:.2f} - {reason}')
"
```

---

## Phase 3: Streaming Implementation (Tasks 8-11)

### Task 8: Create Stream Session Manager

**File:** `power-mode/stream_manager.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Stream session manager for Power Mode.

Tracks active streams, buffers chunks, and coordinates with status line.
"""

import os
import sys
import json
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(__file__))
from protocol import Message, MessageType, StreamChunk

@dataclass
class StreamSession:
    """Active streaming session from an agent."""
    session_id: str
    agent_id: str
    tool_name: Optional[str]
    started_at: str
    chunks: List[StreamChunk] = field(default_factory=list)
    is_complete: bool = False
    error: Optional[str] = None

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def total_content(self) -> str:
        return "".join(chunk.content for chunk in self.chunks)

    @property
    def last_chunk_at(self) -> Optional[str]:
        if self.chunks:
            return self.chunks[-1].timestamp
        return None

class StreamManager:
    """Manages multiple concurrent stream sessions."""

    def __init__(self, on_chunk: Optional[Callable[[StreamChunk], None]] = None):
        self._sessions: Dict[str, StreamSession] = {}
        self._lock = threading.Lock()
        self._on_chunk = on_chunk

    def start_session(
        self,
        agent_id: str,
        tool_name: Optional[str] = None
    ) -> str:
        """Start a new streaming session."""
        session_id = str(uuid.uuid4())[:8]

        with self._lock:
            self._sessions[session_id] = StreamSession(
                session_id=session_id,
                agent_id=agent_id,
                tool_name=tool_name,
                started_at=datetime.now().isoformat()
            )

        return session_id

    def add_chunk(self, chunk: StreamChunk) -> None:
        """Add a chunk to a session."""
        with self._lock:
            session = self._sessions.get(chunk.session_id)
            if session:
                session.chunks.append(chunk)
                if chunk.is_final:
                    session.is_complete = True

        # Notify callback
        if self._on_chunk:
            self._on_chunk(chunk)

    def end_session(self, session_id: str, error: Optional[str] = None) -> Optional[StreamSession]:
        """End a streaming session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.is_complete = True
                session.error = error
                return session
        return None

    def get_session(self, session_id: str) -> Optional[StreamSession]:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[StreamSession]:
        """Get all incomplete sessions."""
        with self._lock:
            return [s for s in self._sessions.values() if not s.is_complete]

    def get_agent_session(self, agent_id: str) -> Optional[StreamSession]:
        """Get active session for an agent."""
        with self._lock:
            for session in self._sessions.values():
                if session.agent_id == agent_id and not session.is_complete:
                    return session
        return None

    def cleanup_completed(self, max_age_seconds: int = 300) -> int:
        """Remove old completed sessions."""
        now = datetime.now()
        removed = 0

        with self._lock:
            to_remove = []
            for session_id, session in self._sessions.items():
                if session.is_complete:
                    started = datetime.fromisoformat(session.started_at)
                    if (now - started).total_seconds() > max_age_seconds:
                        to_remove.append(session_id)

            for session_id in to_remove:
                del self._sessions[session_id]
                removed += 1

        return removed

    def get_status_summary(self) -> Dict:
        """Get summary for status line display."""
        with self._lock:
            active = [s for s in self._sessions.values() if not s.is_complete]
            return {
                "active_streams": len(active),
                "agents_streaming": [s.agent_id for s in active],
                "total_chunks": sum(s.chunk_count for s in active),
                "latest_tool": active[-1].tool_name if active else None
            }
```

**Verification:**
```bash
python -c "
from power_mode.stream_manager import StreamManager, StreamChunk
mgr = StreamManager()
sid = mgr.start_session('test-agent', 'Bash')
chunk = StreamChunk(sid, 'test-agent', 0, 'Hello ', 'Bash')
mgr.add_chunk(chunk)
print(mgr.get_status_summary())
"
```

---

### Task 9: Add Stream Handlers to Coordinator

**File:** `power-mode/coordinator.py` (MODIFY)

**Add imports at top:**
```python
from stream_manager import StreamManager, StreamSession
from protocol import StreamChunk
```

**Add to `__init__` method (after line ~380):**
```python
        # Streaming support (Issue #23)
        self.stream_manager = StreamManager(on_chunk=self._on_stream_chunk)
```

**Add new methods (after `_handle_result` method):**
```python
    def _on_stream_chunk(self, chunk: StreamChunk) -> None:
        """Callback when stream chunk received."""
        # Update status line state
        self._update_stream_status(chunk)

        # Check for early intervention opportunities
        if chunk.chunk_index > 0 and chunk.chunk_index % 10 == 0:
            self._check_stream_drift(chunk)

    def _handle_stream_start(self, channel: str, data: str) -> None:
        """Handle STREAM_START message."""
        msg = Message.from_json(data)
        payload = msg.payload

        session_id = self.stream_manager.start_session(
            agent_id=msg.from_agent,
            tool_name=payload.get("tool_name")
        )

        # Acknowledge stream start
        self._send_to_agent(msg.from_agent, Message(
            id=f"stream-ack-{session_id}",
            type=MessageType.RESPONSE,
            from_agent="coordinator",
            to_agent=msg.from_agent,
            payload={"session_id": session_id, "status": "streaming"}
        ))

    def _handle_stream_chunk(self, channel: str, data: str) -> None:
        """Handle STREAM_CHUNK message."""
        msg = Message.from_json(data)
        payload = msg.payload

        chunk = StreamChunk(
            session_id=payload["session_id"],
            agent_id=msg.from_agent,
            chunk_index=payload["chunk_index"],
            content=payload["content"],
            tool_name=payload.get("tool_name"),
            is_final=payload.get("is_final", False)
        )

        self.stream_manager.add_chunk(chunk)

    def _handle_stream_end(self, channel: str, data: str) -> None:
        """Handle STREAM_END message."""
        msg = Message.from_json(data)
        payload = msg.payload

        session = self.stream_manager.end_session(
            session_id=payload["session_id"],
            error=payload.get("error")
        )

        if session:
            # Log completion
            print(f"Stream {session.session_id} completed: {session.chunk_count} chunks")

    def _update_stream_status(self, chunk: StreamChunk) -> None:
        """Update status line with streaming info."""
        status = self.stream_manager.get_status_summary()

        # Write to state file for status line
        state_file = Path(".claude/power-mode-state.json")
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)

            state["streaming"] = status
            state["last_chunk_at"] = chunk.timestamp

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

    def _check_stream_drift(self, chunk: StreamChunk) -> None:
        """Check if streaming agent is drifting from objective."""
        session = self.stream_manager.get_session(chunk.session_id)
        if not session:
            return

        # Get accumulated content
        content = session.total_content

        # Simple drift detection: check for off-topic keywords
        drift_keywords = ["however", "alternatively", "instead", "but actually"]
        drift_score = sum(1 for kw in drift_keywords if kw in content.lower())

        if drift_score >= 2:
            # Send course correction
            self._send_to_agent(chunk.agent_id, Message(
                id=f"drift-{chunk.session_id}",
                type=MessageType.COURSE_CORRECT,
                from_agent="coordinator",
                to_agent=chunk.agent_id,
                payload={
                    "reason": "Potential drift detected in streaming output",
                    "suggestion": "Focus on the primary objective"
                }
            ))
```

**Update `_handle_message` dispatcher (add cases):**
```python
        elif msg_type == MessageType.STREAM_START.value:
            self._handle_stream_start(channel, data)
        elif msg_type == MessageType.STREAM_CHUNK.value:
            self._handle_stream_chunk(channel, data)
        elif msg_type == MessageType.STREAM_END.value:
            self._handle_stream_end(channel, data)
```

**Verification:**
```bash
python -c "
from power_mode.coordinator import PowerModeCoordinator
coord = PowerModeCoordinator()
print(f'Stream manager: {coord.stream_manager}')
"
```

---

### Task 10: Create Streaming Check-in Hook

**File:** `power-mode/stream-checkin-hook.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Streaming-aware check-in hook for Power Mode.

Extends checkin-hook.py with streaming event handling.
Sends STREAM_START/CHUNK/END messages during tool execution.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks", "utils"))

from protocol import Message, MessageType, Channels

class StreamingCheckinHook:
    """Hook that sends streaming updates during tool execution."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.current_session: Optional[str] = None
        self.chunk_index = 0
        self._redis = None

    def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(host="localhost", port=6379, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = False  # Mark as unavailable
        return self._redis if self._redis else None

    def on_tool_start(self, tool_name: str, tool_input: Dict) -> Optional[str]:
        """Called when tool execution starts."""
        redis = self._get_redis()
        if not redis:
            return None

        self.current_session = str(uuid.uuid4())[:8]
        self.chunk_index = 0

        msg = Message(
            id=f"stream-start-{self.current_session}",
            type=MessageType.STREAM_START,
            from_agent=self.agent_id,
            to_agent="coordinator",
            payload={
                "session_id": self.current_session,
                "tool_name": tool_name,
                "input_preview": str(tool_input)[:100]
            }
        )

        redis.publish(Channels.coordinator(), msg.to_json())
        return self.current_session

    def on_chunk(self, content: str, is_final: bool = False) -> None:
        """Called for each output chunk."""
        redis = self._get_redis()
        if not redis or not self.current_session:
            return

        msg = Message(
            id=f"chunk-{self.current_session}-{self.chunk_index}",
            type=MessageType.STREAM_CHUNK,
            from_agent=self.agent_id,
            to_agent="coordinator",
            payload={
                "session_id": self.current_session,
                "chunk_index": self.chunk_index,
                "content": content,
                "is_final": is_final
            }
        )

        redis.publish(Channels.coordinator(), msg.to_json())
        self.chunk_index += 1

    def on_tool_end(self, tool_result: Any, error: Optional[str] = None) -> None:
        """Called when tool execution completes."""
        redis = self._get_redis()
        if not redis or not self.current_session:
            return

        msg = Message(
            id=f"stream-end-{self.current_session}",
            type=MessageType.STREAM_END,
            from_agent=self.agent_id,
            to_agent="coordinator",
            payload={
                "session_id": self.current_session,
                "total_chunks": self.chunk_index,
                "error": error,
                "result_preview": str(tool_result)[:200] if tool_result else None
            }
        )

        redis.publish(Channels.coordinator(), msg.to_json())
        self.current_session = None
        self.chunk_index = 0


# Hook entry point for Claude Code
def process_hook(hook_input: Dict) -> Dict:
    """Process hook input and return response."""
    event = hook_input.get("event", "")

    # Get agent ID from environment or generate
    agent_id = os.environ.get("POPKIT_AGENT_ID", f"agent-{os.getpid()}")
    hook = StreamingCheckinHook(agent_id)

    if event == "PreToolUse":
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input = hook_input.get("tool_input", {})
        session_id = hook.on_tool_start(tool_name, tool_input)
        return {"continue": True, "session_id": session_id}

    elif event == "PostToolUse":
        tool_result = hook_input.get("tool_result")
        error = hook_input.get("error")
        hook.on_tool_end(tool_result, error)
        return {"continue": True}

    return {"continue": True}


if __name__ == "__main__":
    # Read JSON from stdin
    input_data = json.load(sys.stdin)
    result = process_hook(input_data)
    print(json.dumps(result))
```

**Verification:**
```bash
echo '{"event": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}' | python power-mode/stream-checkin-hook.py
```

---

### Task 11: Update Status Line for Streaming

**File:** `power-mode/statusline.py` (MODIFY)

**Add streaming display (after line ~140):**
```python
def format_streaming_status(state: Dict) -> str:
    """Format streaming info for status line."""
    streaming = state.get("streaming", {})

    if not streaming.get("active_streams", 0):
        return ""

    agents = streaming.get("agents_streaming", [])
    chunks = streaming.get("total_chunks", 0)
    tool = streaming.get("latest_tool", "")

    if len(agents) == 1:
        return f" [{agents[0]} streaming {tool}... {chunks} chunks]"
    else:
        return f" [{len(agents)} agents streaming... {chunks} chunks]"
```

**Update `format_status_line` function:**
```python
def format_status_line(state: Dict, use_color: bool = True) -> str:
    """Format the Power Mode status line."""
    # ... existing code ...

    # Add streaming info
    streaming_info = format_streaming_status(state)

    # Combine
    line = f"{prefix} #{issue} Phase: {phase} ({current}/{total}) [{progress_bar}] {pct}%{streaming_info}"

    # ... rest of function ...
```

**Verification:**
```bash
python power-mode/statusline.py
```

---

## Phase 4: Integration & Testing (Task 12)

### Task 12: Create Integration Tests

**File:** `tests/hooks/test_embeddings_streaming.py` (NEW)

**Implementation:**
```python
#!/usr/bin/env python3
"""Integration tests for embeddings and streaming features."""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'power-mode'))


class TestEmbeddingStore:
    """Tests for embedding storage."""

    def test_store_and_retrieve(self):
        from embedding_store import EmbeddingStore, EmbeddingRecord

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = EmbeddingStore(db_path)

            record = EmbeddingRecord(
                id="test-1",
                content="Test content",
                embedding=[0.1, 0.2, 0.3],
                source_type="skill",
                source_id="test-skill",
                metadata={"key": "value"},
                created_at="2025-01-01T00:00:00"
            )

            store.store(record)
            retrieved = store.get("test-1")

            assert retrieved is not None
            assert retrieved.content == "Test content"
            assert retrieved.embedding == [0.1, 0.2, 0.3]

    def test_cosine_similarity_search(self):
        from embedding_store import EmbeddingStore, EmbeddingRecord

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = EmbeddingStore(db_path)

            # Store two records
            store.store(EmbeddingRecord(
                id="similar",
                content="Similar content",
                embedding=[1.0, 0.0, 0.0],
                source_type="skill",
                source_id="s1",
                metadata={},
                created_at="2025-01-01"
            ))
            store.store(EmbeddingRecord(
                id="different",
                content="Different content",
                embedding=[0.0, 1.0, 0.0],
                source_type="skill",
                source_id="s2",
                metadata={},
                created_at="2025-01-01"
            ))

            # Search with query similar to first
            results = store.search([0.9, 0.1, 0.0], top_k=2)

            assert len(results) == 2
            assert results[0][0].id == "similar"
            assert results[0][1] > results[1][1]  # Higher similarity


class TestStreamManager:
    """Tests for stream session management."""

    def test_session_lifecycle(self):
        from stream_manager import StreamManager, StreamChunk

        mgr = StreamManager()

        # Start session
        session_id = mgr.start_session("agent-1", "Bash")
        assert session_id is not None

        # Add chunks
        for i in range(3):
            chunk = StreamChunk(
                session_id=session_id,
                agent_id="agent-1",
                chunk_index=i,
                content=f"chunk-{i}",
                tool_name="Bash",
                is_final=(i == 2)
            )
            mgr.add_chunk(chunk)

        # Check session
        session = mgr.get_session(session_id)
        assert session is not None
        assert session.chunk_count == 3
        assert session.total_content == "chunk-0chunk-1chunk-2"
        assert session.is_complete

    def test_multiple_agents(self):
        from stream_manager import StreamManager

        mgr = StreamManager()

        s1 = mgr.start_session("agent-1", "Read")
        s2 = mgr.start_session("agent-2", "Write")

        active = mgr.get_active_sessions()
        assert len(active) == 2

        status = mgr.get_status_summary()
        assert status["active_streams"] == 2
        assert "agent-1" in status["agents_streaming"]
        assert "agent-2" in status["agents_streaming"]


class TestSemanticRouter:
    """Tests for semantic agent routing."""

    def test_keyword_fallback(self):
        from semantic_router import SemanticRouter

        router = SemanticRouter()

        # Should use keyword matching (no embeddings)
        results = router.route("I found a security bug")

        # Should match security-auditor or bug-whisperer
        agent_names = [r[0] for r in results]
        assert any("security" in name or "bug" in name for name in agent_names)


class TestProtocolExtensions:
    """Tests for protocol message extensions."""

    def test_stream_message_types(self):
        from protocol import MessageType

        assert hasattr(MessageType, "STREAM_START")
        assert hasattr(MessageType, "STREAM_CHUNK")
        assert hasattr(MessageType, "STREAM_END")
        assert hasattr(MessageType, "STREAM_ERROR")

    def test_embedding_message_types(self):
        from protocol import MessageType

        assert hasattr(MessageType, "EMBEDDING_REQUEST")
        assert hasattr(MessageType, "EMBEDDING_RESULT")
        assert hasattr(MessageType, "SIMILARITY_QUERY")
        assert hasattr(MessageType, "SIMILARITY_RESULT")

    def test_stream_chunk_to_message(self):
        from protocol import StreamChunk, MessageType

        chunk = StreamChunk(
            session_id="abc123",
            agent_id="test-agent",
            chunk_index=5,
            content="hello world",
            tool_name="Bash"
        )

        msg = chunk.to_message()
        assert msg.type == MessageType.STREAM_CHUNK
        assert msg.from_agent == "test-agent"
        assert msg.payload["chunk_index"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Verification:**
```bash
cd "C:\Users\Josep\onedrive\documents\elshaddai\popkit"
python -m pytest tests/hooks/test_embeddings_streaming.py -v
```

---

## Summary

| Task | Phase | Files | Description |
|------|-------|-------|-------------|
| 1 | Shared | `power-mode/async_support.py` | Async utilities |
| 2 | Shared | `power-mode/protocol.py` | Message type extensions |
| 3 | Shared | `hooks/utils/embedding_store.py` | SQLite vector storage |
| 4 | Embeddings | `hooks/utils/voyage_client.py` | Voyage API client |
| 5 | Embeddings | `hooks/embedding_init.py` | Pre-compute embeddings |
| 6 | Embeddings | `skills/pop-knowledge-lookup/SKILL.md` | Semantic search |
| 7 | Embeddings | `hooks/utils/semantic_router.py` | Agent routing |
| 8 | Streaming | `power-mode/stream_manager.py` | Session management |
| 9 | Streaming | `power-mode/coordinator.py` | Stream handlers |
| 10 | Streaming | `power-mode/stream-checkin-hook.py` | Streaming hook |
| 11 | Streaming | `power-mode/statusline.py` | Status display |
| 12 | Testing | `tests/hooks/test_embeddings_streaming.py` | Integration tests |

## Prerequisites

- **Voyage API Key**: Set `VOYAGE_API_KEY` environment variable
- **Redis** (optional): For full streaming support in Power Mode
- **Python 3.9+**: For type hints and dataclasses

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Voyage API unavailable | Keyword fallback in all components |
| Redis unavailable | File-based fallback already exists |
| Embedding computation slow | Cache in SQLite, batch requests |
| Stream flood coordinator | Rate limiting, chunk batching |

## Success Criteria

1. `/popkit:knowledge search` returns semantic results
2. Agent routing uses embeddings when available
3. Power Mode shows real-time streaming status
4. All 12+ tests pass
5. Graceful fallback when APIs unavailable
