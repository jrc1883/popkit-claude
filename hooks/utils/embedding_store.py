#!/usr/bin/env python3
"""
Embedding Storage and Retrieval

SQLite-based vector storage with cosine similarity search.
Stores embeddings as JSON arrays for portability (no native vector type needed).

Part of PopKit Issue #19 (Embeddings Enhancement).
"""

import os
import json
import sqlite3
import math
import hashlib
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_DB_PATH = Path.home() / ".claude" / "config" / "embeddings.db"
DEFAULT_EMBEDDING_MODEL = "voyage-3.5"
DEFAULT_EMBEDDING_DIM = 1024


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EmbeddingRecord:
    """A stored embedding with metadata."""
    id: str
    content: str
    embedding: List[float]
    source_type: str  # "skill", "agent", "command", "project-skill", "project-agent", "project-command"
    source_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    project_path: Optional[str] = None  # NULL = global PopKit, path = project-local

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'EmbeddingRecord':
        """Create from dictionary."""
        return cls(**d)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return len(self.embedding)


@dataclass
class SearchResult:
    """Result from similarity search."""
    record: EmbeddingRecord
    similarity: float
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record": self.record.to_dict(),
            "similarity": self.similarity,
            "rank": self.rank
        }


# =============================================================================
# EMBEDDING STORE
# =============================================================================

class EmbeddingStore:
    """
    SQLite-based embedding storage with semantic search.

    Features:
    - Store embeddings with metadata
    - Cosine similarity search
    - Filter by source type
    - Batch operations
    - Thread-safe connections
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the embedding store.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.claude/config/embeddings.db
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    embedding_model TEXT DEFAULT 'voyage-3.5',
                    embedding_dim INTEGER,
                    content_hash TEXT,
                    project_path TEXT DEFAULT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_type
                ON embeddings(source_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_id
                ON embeddings(source_type, source_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash
                ON embeddings(content_hash)
            """)

            conn.commit()

            # Migration: Add project_path column if it doesn't exist (for existing DBs)
            self._migrate_add_project_path(conn)

    def _migrate_add_project_path(self, conn: sqlite3.Connection) -> None:
        """Add project_path column to existing databases."""
        try:
            # Check if column exists
            cursor = conn.execute("PRAGMA table_info(embeddings)")
            columns = [row[1] for row in cursor.fetchall()]

            if "project_path" not in columns:
                conn.execute("ALTER TABLE embeddings ADD COLUMN project_path TEXT DEFAULT NULL")
                conn.commit()

            # Create indexes for project-scoped queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_path
                ON embeddings(project_path)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_source
                ON embeddings(project_path, source_type)
            """)

            conn.commit()
        except Exception:
            pass  # Column already exists or other non-critical error

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    def store(self, record: EmbeddingRecord) -> None:
        """
        Store an embedding record.

        Args:
            record: EmbeddingRecord to store
        """
        content_hash = hashlib.sha256(record.content.encode()).hexdigest()[:16]

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings
                (id, content, embedding, source_type, source_id, metadata,
                 created_at, embedding_model, embedding_dim, content_hash, project_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.content,
                json.dumps(record.embedding),
                record.source_type,
                record.source_id,
                json.dumps(record.metadata),
                record.created_at,
                record.embedding_model,
                len(record.embedding),
                content_hash,
                record.project_path
            ))
            conn.commit()

    def store_batch(self, records: List[EmbeddingRecord]) -> int:
        """
        Store multiple embedding records efficiently.

        Args:
            records: List of EmbeddingRecord to store

        Returns:
            Number of records stored
        """
        if not records:
            return 0

        with self._get_connection() as conn:
            data = []
            for record in records:
                content_hash = hashlib.sha256(record.content.encode()).hexdigest()[:16]
                data.append((
                    record.id,
                    record.content,
                    json.dumps(record.embedding),
                    record.source_type,
                    record.source_id,
                    json.dumps(record.metadata),
                    record.created_at,
                    record.embedding_model,
                    len(record.embedding),
                    content_hash,
                    record.project_path
                ))

            conn.executemany("""
                INSERT OR REPLACE INTO embeddings
                (id, content, embedding, source_type, source_id, metadata,
                 created_at, embedding_model, embedding_dim, content_hash, project_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()

        return len(records)

    def get(self, id: str) -> Optional[EmbeddingRecord]:
        """
        Retrieve an embedding by ID.

        Args:
            id: Record ID

        Returns:
            EmbeddingRecord or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE id = ?", (id,)
            ).fetchone()

            if row:
                return self._row_to_record(row)

        return None

    def get_by_source(self, source_type: str, source_id: str) -> Optional[EmbeddingRecord]:
        """
        Retrieve an embedding by source type and ID.

        Args:
            source_type: Type of source (skill, agent, etc.)
            source_id: ID within source type

        Returns:
            EmbeddingRecord or None
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE source_type = ? AND source_id = ?",
                (source_type, source_id)
            ).fetchone()

            if row:
                return self._row_to_record(row)

        return None

    def delete(self, id: str) -> bool:
        """
        Delete an embedding by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM embeddings WHERE id = ?", (id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_by_source(self, source_type: str, source_id: Optional[str] = None) -> int:
        """
        Delete embeddings by source.

        Args:
            source_type: Type of source
            source_id: Optional specific source ID

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            if source_id:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE source_type = ? AND source_id = ?",
                    (source_type, source_id)
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE source_type = ?",
                    (source_type,)
                )
            conn.commit()
            return cursor.rowcount

    # =========================================================================
    # SIMILARITY SEARCH
    # =========================================================================

    def search(
        self,
        query_embedding: List[float],
        source_type: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
        exclude_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Find similar embeddings using cosine similarity.

        Args:
            query_embedding: Query vector
            source_type: Optional filter by source type
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            exclude_ids: IDs to exclude from results

        Returns:
            List of SearchResult ordered by similarity (descending)
        """
        exclude_ids = exclude_ids or []

        with self._get_connection() as conn:
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

            if record.id in exclude_ids:
                continue

            similarity = self._cosine_similarity(query_embedding, record.embedding)

            if similarity >= min_similarity:
                results.append(SearchResult(record=record, similarity=similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x.similarity, reverse=True)

        # Add ranks and limit
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1

        return results[:top_k]

    def search_by_content(
        self,
        query: str,
        embed_func,
        source_type: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[SearchResult]:
        """
        Search by content string (embeds query first).

        Args:
            query: Text query
            embed_func: Function to embed text (str -> List[float])
            source_type: Optional filter
            top_k: Number of results
            min_similarity: Minimum threshold

        Returns:
            List of SearchResult
        """
        query_embedding = embed_func(query)
        return self.search(
            query_embedding=query_embedding,
            source_type=source_type,
            top_k=top_k,
            min_similarity=min_similarity
        )

    # =========================================================================
    # PROJECT-SCOPED OPERATIONS
    # =========================================================================

    def needs_update(self, id: str, content: str) -> bool:
        """
        Check if content has changed and needs re-embedding.

        Compares content hash to detect changes without loading embeddings.

        Args:
            id: Record ID to check
            content: New content to compare

        Returns:
            True if content has changed or doesn't exist, False if unchanged
        """
        new_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT content_hash FROM embeddings WHERE id = ?",
                (id,)
            ).fetchone()

            if not result:
                return True  # Doesn't exist, needs embedding

            return result[0] != new_hash

    def search_project(
        self,
        query_embedding: List[float],
        project_path: str,
        source_type: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
        include_global: bool = True,
        global_boost: float = 0.0
    ) -> List[SearchResult]:
        """
        Search embeddings with project scope.

        Project items are searched first, optionally including global PopKit items.
        Project items get a priority boost to prefer project-specific matches.

        Args:
            query_embedding: Query vector
            project_path: Project root path to scope results
            source_type: Optional filter by source type
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            include_global: Whether to include global PopKit items
            global_boost: Boost to add to global items (negative = deprioritize)

        Returns:
            List of SearchResult ordered by similarity (descending)
        """
        with self._get_connection() as conn:
            # Build query based on filters
            if include_global:
                if source_type:
                    rows = conn.execute(
                        """SELECT * FROM embeddings
                           WHERE (project_path = ? OR project_path IS NULL)
                           AND source_type = ?""",
                        (project_path, source_type)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT * FROM embeddings
                           WHERE project_path = ? OR project_path IS NULL""",
                        (project_path,)
                    ).fetchall()
            else:
                if source_type:
                    rows = conn.execute(
                        """SELECT * FROM embeddings
                           WHERE project_path = ? AND source_type = ?""",
                        (project_path, source_type)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM embeddings WHERE project_path = ?",
                        (project_path,)
                    ).fetchall()

        results = []
        for row in rows:
            record = self._row_to_record(row)
            similarity = self._cosine_similarity(query_embedding, record.embedding)

            # Apply boost for global items
            if record.project_path is None and global_boost != 0.0:
                similarity += global_boost

            if similarity >= min_similarity:
                results.append(SearchResult(record=record, similarity=similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x.similarity, reverse=True)

        # Add ranks and limit
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1

        return results[:top_k]

    def clear_project(
        self,
        project_path: str,
        source_type: Optional[str] = None
    ) -> int:
        """
        Clear embeddings for a specific project.

        Args:
            project_path: Project root path
            source_type: Optional specific source type to clear

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            if source_type:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE project_path = ? AND source_type = ?",
                    (project_path, source_type)
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE project_path = ?",
                    (project_path,)
                )
            conn.commit()
            return cursor.rowcount

    def count_project(self, project_path: str, source_type: Optional[str] = None) -> int:
        """
        Count embeddings for a specific project.

        Args:
            project_path: Project root path
            source_type: Optional filter by source type

        Returns:
            Number of embeddings for the project
        """
        with self._get_connection() as conn:
            if source_type:
                result = conn.execute(
                    """SELECT COUNT(*) FROM embeddings
                       WHERE project_path = ? AND source_type = ?""",
                    (project_path, source_type)
                ).fetchone()
            else:
                result = conn.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE project_path = ?",
                    (project_path,)
                ).fetchone()

            return result[0] if result else 0

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects with embeddings.

        Returns:
            List of project info dictionaries
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT project_path, COUNT(*) as count,
                          GROUP_CONCAT(DISTINCT source_type) as types
                   FROM embeddings
                   WHERE project_path IS NOT NULL
                   GROUP BY project_path
                   ORDER BY project_path"""
            ).fetchall()

        return [
            {
                "project_path": row[0],
                "count": row[1],
                "source_types": row[2].split(",") if row[2] else []
            }
            for row in rows
        ]

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def count(self, source_type: Optional[str] = None) -> int:
        """
        Count stored embeddings.

        Args:
            source_type: Optional filter by source type

        Returns:
            Number of embeddings
        """
        with self._get_connection() as conn:
            if source_type:
                result = conn.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE source_type = ?",
                    (source_type,)
                ).fetchone()
            else:
                result = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()

            return result[0] if result else 0

    def stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats
        """
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

            by_type = {}
            for row in conn.execute(
                "SELECT source_type, COUNT(*) FROM embeddings GROUP BY source_type"
            ):
                by_type[row[0]] = row[1]

            models = {}
            for row in conn.execute(
                "SELECT embedding_model, COUNT(*) FROM embeddings GROUP BY embedding_model"
            ):
                models[row[0]] = row[1]

            dims = conn.execute(
                "SELECT DISTINCT embedding_dim FROM embeddings"
            ).fetchall()

        return {
            "total": total,
            "by_type": by_type,
            "by_model": models,
            "dimensions": [d[0] for d in dims if d[0]],
            "db_path": str(self.db_path)
        }

    def list_sources(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all stored sources.

        Args:
            source_type: Optional filter

        Returns:
            List of source info dictionaries
        """
        with self._get_connection() as conn:
            if source_type:
                rows = conn.execute(
                    """SELECT source_type, source_id, content, created_at
                       FROM embeddings WHERE source_type = ?
                       ORDER BY source_type, source_id""",
                    (source_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT source_type, source_id, content, created_at
                       FROM embeddings
                       ORDER BY source_type, source_id"""
                ).fetchall()

        return [
            {
                "source_type": row[0],
                "source_id": row[1],
                "content_preview": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (-1.0 to 1.0, typically 0.0 to 1.0 for embeddings)
        """
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
        # Row columns: id, content, embedding, source_type, source_id, metadata,
        #              created_at, embedding_model, embedding_dim, content_hash, project_path
        return EmbeddingRecord(
            id=row[0],
            content=row[1],
            embedding=json.loads(row[2]),
            source_type=row[3],
            source_id=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=row[6],
            embedding_model=row[7] or DEFAULT_EMBEDDING_MODEL,
            project_path=row[10] if len(row) > 10 else None
        )

    def clear(self, source_type: Optional[str] = None) -> int:
        """
        Clear all embeddings (or by type).

        Args:
            source_type: Optional type to clear

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            if source_type:
                cursor = conn.execute(
                    "DELETE FROM embeddings WHERE source_type = ?",
                    (source_type,)
                )
            else:
                cursor = conn.execute("DELETE FROM embeddings")
            conn.commit()
            return cursor.rowcount

    def exists(self, id: str) -> bool:
        """Check if an embedding exists."""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT 1 FROM embeddings WHERE id = ?", (id,)
            ).fetchone()
            return result is not None

    def content_exists(self, content: str) -> Optional[str]:
        """
        Check if content already has an embedding.

        Args:
            content: Content to check

        Returns:
            Record ID if exists, None otherwise
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT id FROM embeddings WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()

            return result[0] if result else None


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("EmbeddingStore Test")
    print("=" * 40)

    # Create test store in temp location
    import tempfile
    test_db = Path(tempfile.gettempdir()) / "test_embeddings.db"
    store = EmbeddingStore(test_db)

    # Test store
    record = EmbeddingRecord(
        id="test-1",
        content="This is a test skill for debugging",
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        source_type="skill",
        source_id="test-skill",
        metadata={"tier": "test"}
    )
    store.store(record)
    print(f"Stored: {record.id}")

    # Test retrieve
    retrieved = store.get("test-1")
    assert retrieved is not None
    assert retrieved.content == record.content
    print(f"Retrieved: {retrieved.id}")

    # Test search
    results = store.search(
        query_embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        top_k=5
    )
    assert len(results) == 1
    assert results[0].similarity > 0.99
    print(f"Search found: {len(results)} results, similarity={results[0].similarity:.4f}")

    # Test stats
    stats = store.stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")

    # Cleanup
    store.clear()
    test_db.unlink()
    print("\nAll tests passed!")
