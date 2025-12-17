#!/usr/bin/env python3
"""
Research Index - Knowledge Base Management

Manages the research index for capturing decisions, findings, learnings,
and spikes during development. Integrates with embeddings for semantic search.

Part of PopKit Issue #142 (Research Index with Embeddings).
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

RESEARCH_DIR = ".claude/research"
INDEX_FILE = "index.json"
ENTRIES_DIR = "entries"
INDEX_VERSION = "1.0.0"

ENTRY_TYPES = ["decision", "finding", "learning", "spike"]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ResearchEntry:
    """A research entry with full content."""
    id: str
    type: str  # decision, finding, learning, spike
    title: str
    content: str
    context: str = ""
    rationale: str = ""
    alternatives: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    project: str = ""
    references: List[str] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    embedding_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ResearchEntry':
        """Create from dictionary."""
        # Handle snake_case vs camelCase
        if 'createdAt' in d:
            d['created_at'] = d.pop('createdAt')
        if 'updatedAt' in d:
            d['updated_at'] = d.pop('updatedAt')
        if 'embeddingId' in d:
            d['embedding_id'] = d.pop('embeddingId')
        if 'relatedEntries' in d:
            d['related_entries'] = d.pop('relatedEntries')

        # Filter to known fields
        known_fields = {
            'id', 'type', 'title', 'content', 'context', 'rationale',
            'alternatives', 'tags', 'project', 'references',
            'related_entries', 'created_at', 'updated_at', 'embedding_id'
        }
        filtered = {k: v for k, v in d.items() if k in known_fields}

        return cls(**filtered)

    @property
    def searchable_text(self) -> str:
        """Get combined text for embedding/search."""
        parts = [
            self.title,
            self.content,
            self.context,
            self.rationale,
        ]
        if self.alternatives:
            parts.append(" ".join(self.alternatives))
        return "\n\n".join(p for p in parts if p)


@dataclass
class IndexEntry:
    """Lightweight index entry (without full content)."""
    id: str
    type: str
    title: str
    tags: List[str]
    project: str
    created_at: str
    embedding_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'IndexEntry':
        """Create from dictionary."""
        if 'createdAt' in d:
            d['created_at'] = d.pop('createdAt')
        if 'embeddingId' in d:
            d['embedding_id'] = d.pop('embeddingId')

        known_fields = {'id', 'type', 'title', 'tags', 'project', 'created_at', 'embedding_id'}
        filtered = {k: v for k, v in d.items() if k in known_fields}

        return cls(**filtered)


@dataclass
class ResearchIndex:
    """Master index for research entries."""
    version: str = INDEX_VERSION
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    entries: List[IndexEntry] = field(default_factory=list)
    tag_index: Dict[str, List[str]] = field(default_factory=dict)
    project_index: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "lastUpdated": self.last_updated,
            "entries": [e.to_dict() for e in self.entries],
            "tagIndex": self.tag_index,
            "projectIndex": self.project_index,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ResearchIndex':
        """Create from dictionary."""
        return cls(
            version=d.get("version", INDEX_VERSION),
            last_updated=d.get("lastUpdated", datetime.utcnow().isoformat() + "Z"),
            entries=[IndexEntry.from_dict(e) for e in d.get("entries", [])],
            tag_index=d.get("tagIndex", {}),
            project_index=d.get("projectIndex", {}),
        )


@dataclass
class SearchResult:
    """Result from research search."""
    entry: ResearchEntry
    similarity: float
    rank: int = 0
    match_type: str = "semantic"  # semantic, keyword, tag

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry": self.entry.to_dict(),
            "similarity": self.similarity,
            "rank": self.rank,
            "matchType": self.match_type,
        }


# =============================================================================
# RESEARCH INDEX MANAGER
# =============================================================================

class ResearchIndexManager:
    """
    Manages the research knowledge base.

    Features:
    - Create, read, update, delete research entries
    - Tag and project-based indexing
    - Semantic search via embeddings
    - Keyword/tag search fallback
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the research index manager.

        Args:
            project_root: Root directory for the project. Defaults to cwd.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.research_dir = self.project_root / RESEARCH_DIR
        self.index_path = self.research_dir / INDEX_FILE
        self.entries_dir = self.research_dir / ENTRIES_DIR

        # Ensure directories exist
        self.entries_dir.mkdir(parents=True, exist_ok=True)

        # Load or create index
        self._index = self._load_index()

    # =========================================================================
    # INDEX MANAGEMENT
    # =========================================================================

    def _load_index(self) -> ResearchIndex:
        """Load index from disk or create new one."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ResearchIndex.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass

        return ResearchIndex()

    def _save_index(self) -> None:
        """Save index to disk."""
        self._index.last_updated = datetime.utcnow().isoformat() + "Z"
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self._index.to_dict(), f, indent=2)

    def _generate_id(self) -> str:
        """Generate next entry ID."""
        if not self._index.entries:
            return "r001"

        # Find highest existing ID
        max_num = 0
        for entry in self._index.entries:
            match = re.match(r'r(\d+)', entry.id)
            if match:
                max_num = max(max_num, int(match.group(1)))

        return f"r{max_num + 1:03d}"

    def _update_indexes(self, entry: ResearchEntry, remove: bool = False) -> None:
        """Update tag and project indexes."""
        # Update tag index
        for tag in entry.tags:
            if tag not in self._index.tag_index:
                self._index.tag_index[tag] = []

            if remove:
                if entry.id in self._index.tag_index[tag]:
                    self._index.tag_index[tag].remove(entry.id)
            else:
                if entry.id not in self._index.tag_index[tag]:
                    self._index.tag_index[tag].append(entry.id)

        # Clean empty tags
        self._index.tag_index = {
            k: v for k, v in self._index.tag_index.items() if v
        }

        # Update project index
        if entry.project:
            if entry.project not in self._index.project_index:
                self._index.project_index[entry.project] = []

            if remove:
                if entry.id in self._index.project_index[entry.project]:
                    self._index.project_index[entry.project].remove(entry.id)
            else:
                if entry.id not in self._index.project_index[entry.project]:
                    self._index.project_index[entry.project].append(entry.id)

        # Clean empty projects
        self._index.project_index = {
            k: v for k, v in self._index.project_index.items() if v
        }

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    def create(self, entry: ResearchEntry) -> str:
        """
        Create a new research entry.

        Args:
            entry: ResearchEntry to create (id will be generated if not set)

        Returns:
            Generated entry ID
        """
        # Generate ID if not provided
        if not entry.id or entry.id == "":
            entry.id = self._generate_id()

        # Set timestamps
        now = datetime.utcnow().isoformat() + "Z"
        entry.created_at = now
        entry.updated_at = now

        # Save full entry
        entry_path = self.entries_dir / f"{entry.id}.json"
        with open(entry_path, 'w', encoding='utf-8') as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Add to index
        index_entry = IndexEntry(
            id=entry.id,
            type=entry.type,
            title=entry.title,
            tags=entry.tags,
            project=entry.project,
            created_at=entry.created_at,
            embedding_id=entry.embedding_id,
        )
        self._index.entries.append(index_entry)

        # Update indexes
        self._update_indexes(entry)
        self._save_index()

        return entry.id

    def get(self, entry_id: str) -> Optional[ResearchEntry]:
        """
        Get a research entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            ResearchEntry or None
        """
        entry_path = self.entries_dir / f"{entry_id}.json"
        if not entry_path.exists():
            return None

        with open(entry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return ResearchEntry.from_dict(data)

    def update(self, entry: ResearchEntry) -> bool:
        """
        Update an existing research entry.

        Args:
            entry: Updated ResearchEntry

        Returns:
            True if updated, False if not found
        """
        entry_path = self.entries_dir / f"{entry.id}.json"
        if not entry_path.exists():
            return False

        # Load old entry to update indexes properly
        old_entry = self.get(entry.id)
        if old_entry:
            self._update_indexes(old_entry, remove=True)

        # Update timestamp
        entry.updated_at = datetime.utcnow().isoformat() + "Z"

        # Save entry
        with open(entry_path, 'w', encoding='utf-8') as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Update index entry
        for i, idx_entry in enumerate(self._index.entries):
            if idx_entry.id == entry.id:
                self._index.entries[i] = IndexEntry(
                    id=entry.id,
                    type=entry.type,
                    title=entry.title,
                    tags=entry.tags,
                    project=entry.project,
                    created_at=entry.created_at,
                    embedding_id=entry.embedding_id,
                )
                break

        # Update indexes
        self._update_indexes(entry)
        self._save_index()

        return True

    def delete(self, entry_id: str) -> bool:
        """
        Delete a research entry.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted, False if not found
        """
        entry_path = self.entries_dir / f"{entry_id}.json"
        if not entry_path.exists():
            return False

        # Load entry for index cleanup
        entry = self.get(entry_id)
        if entry:
            self._update_indexes(entry, remove=True)

        # Delete file
        entry_path.unlink()

        # Remove from index
        self._index.entries = [
            e for e in self._index.entries if e.id != entry_id
        ]
        self._save_index()

        return True

    # =========================================================================
    # LISTING AND FILTERING
    # =========================================================================

    def list(
        self,
        entry_type: Optional[str] = None,
        project: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20
    ) -> List[IndexEntry]:
        """
        List research entries with optional filters.

        Args:
            entry_type: Filter by type (decision, finding, learning, spike)
            project: Filter by project name
            tag: Filter by tag
            limit: Maximum entries to return

        Returns:
            List of IndexEntry
        """
        entries = self._index.entries

        # Filter by type
        if entry_type:
            entries = [e for e in entries if e.type == entry_type]

        # Filter by project
        if project:
            entries = [e for e in entries if e.project == project]

        # Filter by tag
        if tag:
            tag_ids = set(self._index.tag_index.get(tag, []))
            entries = [e for e in entries if e.id in tag_ids]

        # Sort by date (newest first)
        entries = sorted(entries, key=lambda e: e.created_at, reverse=True)

        return entries[:limit]

    def list_tags(self) -> Dict[str, int]:
        """
        List all tags with counts.

        Returns:
            Dictionary of tag -> count
        """
        return {
            tag: len(ids)
            for tag, ids in self._index.tag_index.items()
        }

    def list_projects(self) -> Dict[str, int]:
        """
        List all projects with counts.

        Returns:
            Dictionary of project -> count
        """
        return {
            project: len(ids)
            for project, ids in self._index.project_index.items()
        }

    # =========================================================================
    # SEARCH
    # =========================================================================

    def search_keywords(
        self,
        query: str,
        entry_type: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Search entries by keywords (fallback when embeddings unavailable).

        Args:
            query: Search query
            entry_type: Optional type filter
            project: Optional project filter
            limit: Maximum results

        Returns:
            List of SearchResult
        """
        query_words = set(query.lower().split())
        results = []

        for idx_entry in self._index.entries:
            # Apply filters
            if entry_type and idx_entry.type != entry_type:
                continue
            if project and idx_entry.project != project:
                continue

            # Load full entry for content search
            entry = self.get(idx_entry.id)
            if not entry:
                continue

            # Score by word matches
            text = entry.searchable_text.lower()
            matches = sum(1 for word in query_words if word in text)

            # Boost for title matches
            title_matches = sum(1 for word in query_words if word in entry.title.lower())
            matches += title_matches * 2

            # Boost for tag matches
            tag_text = " ".join(entry.tags).lower()
            tag_matches = sum(1 for word in query_words if word in tag_text)
            matches += tag_matches * 3

            if matches > 0:
                # Normalize score to 0-1 range
                similarity = min(matches / (len(query_words) * 3), 1.0)
                results.append(SearchResult(
                    entry=entry,
                    similarity=similarity,
                    match_type="keyword"
                ))

        # Sort by similarity
        results.sort(key=lambda r: r.similarity, reverse=True)

        # Add ranks
        for i, result in enumerate(results[:limit]):
            result.rank = i + 1

        return results[:limit]

    def search_tags(
        self,
        tags: List[str],
        entry_type: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Search entries by tags.

        Args:
            tags: Tags to search for
            entry_type: Optional type filter
            project: Optional project filter
            limit: Maximum results

        Returns:
            List of SearchResult
        """
        # Get all entries matching any tag
        matching_ids = set()
        for tag in tags:
            matching_ids.update(self._index.tag_index.get(tag, []))

        results = []
        for entry_id in matching_ids:
            idx_entry = next((e for e in self._index.entries if e.id == entry_id), None)
            if not idx_entry:
                continue

            # Apply filters
            if entry_type and idx_entry.type != entry_type:
                continue
            if project and idx_entry.project != project:
                continue

            entry = self.get(entry_id)
            if not entry:
                continue

            # Score by tag overlap
            overlap = len(set(tags) & set(entry.tags))
            similarity = overlap / len(tags)

            results.append(SearchResult(
                entry=entry,
                similarity=similarity,
                match_type="tag"
            ))

        # Sort by similarity
        results.sort(key=lambda r: r.similarity, reverse=True)

        # Add ranks
        for i, result in enumerate(results[:limit]):
            result.rank = i + 1

        return results[:limit]

    def search_semantic(
        self,
        query: str,
        entry_type: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.6
    ) -> List[SearchResult]:
        """
        Search entries semantically using embeddings.

        Requires POPKIT_API_KEY or VOYAGE_API_KEY to be set.

        Args:
            query: Search query
            entry_type: Optional type filter
            project: Optional project filter
            limit: Maximum results
            min_similarity: Minimum similarity threshold

        Returns:
            List of SearchResult
        """
        # Try to import embedding utilities
        try:
            from .voyage_client import VoyageClient
            from .embedding_store import EmbeddingStore
        except ImportError:
            # Fall back to keyword search
            return self.search_keywords(query, entry_type, project, limit)

        # Check for API key
        api_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get("POPKIT_API_KEY")
        if not api_key:
            return self.search_keywords(query, entry_type, project, limit)

        try:
            # Generate query embedding
            client = VoyageClient(api_key)
            query_embedding = client.embed_text(query)

            # Search embedding store
            store = EmbeddingStore()
            search_results = store.search(
                query_embedding=query_embedding,
                source_type="research",
                top_k=limit * 2,  # Get more for filtering
                min_similarity=min_similarity
            )

            results = []
            for sr in search_results:
                # Extract entry ID from embedding source_id
                entry_id = sr.record.source_id

                # Load full entry
                entry = self.get(entry_id)
                if not entry:
                    continue

                # Apply filters
                if entry_type and entry.type != entry_type:
                    continue
                if project and entry.project != project:
                    continue

                results.append(SearchResult(
                    entry=entry,
                    similarity=sr.similarity,
                    match_type="semantic"
                ))

                if len(results) >= limit:
                    break

            # Add ranks
            for i, result in enumerate(results):
                result.rank = i + 1

            return results

        except Exception:
            # Fall back to keyword search on error
            return self.search_keywords(query, entry_type, project, limit)

    # =========================================================================
    # TAG MANAGEMENT
    # =========================================================================

    def add_tags(self, entry_id: str, tags: List[str]) -> bool:
        """
        Add tags to an entry.

        Args:
            entry_id: Entry ID
            tags: Tags to add

        Returns:
            True if successful
        """
        entry = self.get(entry_id)
        if not entry:
            return False

        # Add new tags
        existing = set(entry.tags)
        for tag in tags:
            existing.add(tag)
        entry.tags = list(existing)

        return self.update(entry)

    def remove_tags(self, entry_id: str, tags: List[str]) -> bool:
        """
        Remove tags from an entry.

        Args:
            entry_id: Entry ID
            tags: Tags to remove

        Returns:
            True if successful
        """
        entry = self.get(entry_id)
        if not entry:
            return False

        # Remove tags
        entry.tags = [t for t in entry.tags if t not in tags]

        return self.update(entry)

    def set_tags(self, entry_id: str, tags: List[str]) -> bool:
        """
        Set tags for an entry (replaces existing).

        Args:
            entry_id: Entry ID
            tags: New tags

        Returns:
            True if successful
        """
        entry = self.get(entry_id)
        if not entry:
            return False

        entry.tags = list(set(tags))
        return self.update(entry)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def stats(self) -> Dict[str, Any]:
        """
        Get research index statistics.

        Returns:
            Dictionary with stats
        """
        by_type = {}
        for entry in self._index.entries:
            by_type[entry.type] = by_type.get(entry.type, 0) + 1

        return {
            "total": len(self._index.entries),
            "by_type": by_type,
            "tags": len(self._index.tag_index),
            "projects": len(self._index.project_index),
            "last_updated": self._index.last_updated,
            "version": self._index.version,
        }

    # =========================================================================
    # EMBEDDING MANAGEMENT
    # =========================================================================

    def embed_entry(self, entry_id: str, force: bool = False) -> Optional[str]:
        """
        Generate and store embedding for an entry.

        Args:
            entry_id: Entry ID to embed
            force: Re-embed even if already has embedding

        Returns:
            Embedding ID if successful, None otherwise
        """
        entry = self.get(entry_id)
        if not entry:
            return None

        if entry.embedding_id and not force:
            return entry.embedding_id

        # Try to import embedding utilities
        try:
            from .voyage_client import VoyageClient
            from .embedding_store import EmbeddingStore, EmbeddingRecord
        except ImportError:
            return None

        # Check for API key
        api_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get("POPKIT_API_KEY")
        if not api_key:
            return None

        try:
            # Generate embedding
            client = VoyageClient(api_key)
            embedding = client.embed_text(entry.searchable_text)

            # Store in embedding store
            store = EmbeddingStore()
            embedding_id = f"research_{entry.id}"

            record = EmbeddingRecord(
                id=embedding_id,
                content=entry.searchable_text,
                embedding=embedding,
                source_type="research",
                source_id=entry.id,
                metadata={
                    "type": entry.type,
                    "title": entry.title,
                    "tags": entry.tags,
                    "project": entry.project,
                },
                project_path=str(self.project_root),
            )
            store.store(record)

            # Update entry with embedding ID
            entry.embedding_id = embedding_id
            self.update(entry)

            return embedding_id

        except Exception:
            return None

    def embed_all(self, force: bool = False) -> Tuple[int, int]:
        """
        Embed all entries that don't have embeddings.

        Args:
            force: Re-embed even if already has embedding

        Returns:
            Tuple of (success_count, failure_count)
        """
        success = 0
        failure = 0

        for idx_entry in self._index.entries:
            if idx_entry.embedding_id and not force:
                continue

            result = self.embed_entry(idx_entry.id, force=force)
            if result:
                success += 1
            else:
                failure += 1

        return success, failure


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_keywords(text: str) -> List[str]:
    """
    Extract keywords from text for auto-tagging.

    Args:
        text: Text to extract keywords from

    Returns:
        List of keywords
    """
    # Common tech keywords to look for
    tech_keywords = {
        # Infrastructure
        "redis", "postgres", "mysql", "mongodb", "sqlite", "database",
        "docker", "kubernetes", "aws", "cloudflare", "vercel",
        # Frontend
        "react", "vue", "angular", "svelte", "astro", "next", "nuxt",
        "css", "tailwind", "typescript", "javascript",
        # Backend
        "node", "python", "rust", "go", "api", "rest", "graphql",
        "auth", "authentication", "authorization", "jwt", "oauth",
        # Concepts
        "security", "performance", "testing", "ci", "cd", "deployment",
        "caching", "rate-limiting", "webhooks", "websocket",
        "embedding", "ai", "ml", "vector",
    }

    # Find matches
    text_lower = text.lower()
    found = []

    for keyword in tech_keywords:
        if keyword in text_lower:
            found.append(keyword)

    return found[:5]  # Limit to 5 tags


def get_research_manager(project_root: Optional[str] = None) -> ResearchIndexManager:
    """
    Get a research index manager instance.

    Args:
        project_root: Optional project root path

    Returns:
        ResearchIndexManager instance
    """
    return ResearchIndexManager(project_root)


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Research Index Test")
    print("=" * 40)

    # Create manager in temp location
    import tempfile
    test_dir = Path(tempfile.mkdtemp())
    manager = ResearchIndexManager(test_dir)

    # Test create
    entry = ResearchEntry(
        id="",
        type="decision",
        title="Use Redis for session storage",
        content="We decided to use Redis for session tokens...",
        context="Evaluating session storage options",
        rationale="Redis provides TTL support and fast lookups",
        alternatives=["PostgreSQL", "JWT-only"],
        tags=["auth", "redis", "infrastructure"],
        project="popkit",
    )
    entry_id = manager.create(entry)
    print(f"Created: {entry_id}")

    # Test get
    retrieved = manager.get(entry_id)
    assert retrieved is not None
    assert retrieved.title == entry.title
    print(f"Retrieved: {retrieved.id} - {retrieved.title}")

    # Test list
    entries = manager.list()
    assert len(entries) == 1
    print(f"Listed: {len(entries)} entries")

    # Test search keywords
    results = manager.search_keywords("redis session")
    assert len(results) > 0
    print(f"Keyword search found: {len(results)} results")

    # Test tag search
    results = manager.search_tags(["auth", "redis"])
    assert len(results) > 0
    print(f"Tag search found: {len(results)} results")

    # Test stats
    stats = manager.stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")

    # Test delete
    deleted = manager.delete(entry_id)
    assert deleted
    print(f"Deleted: {entry_id}")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("\nAll tests passed!")
