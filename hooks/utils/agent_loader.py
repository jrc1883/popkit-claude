#!/usr/bin/env python3
"""
Agent Loader with Semantic Search

Loads only relevant agents using embedding-based similarity search.
Part of Phase 2: Embedding-Based Agent Loading.
"""

from typing import List, Dict, Any
import json
import sys
from pathlib import Path

from embedding_store import EmbeddingStore, SearchResult
from voyage_client import embed
from cloud_agent_search import search_agents as cloud_search


class AgentLoader:
    """
    Load relevant agents using semantic search.

    Attributes:
        store: Embedding store for local search
        use_embeddings: Whether to use embeddings (fallback to keywords if False)
        always_include_tier1: Always include some Tier 1 agents
    """

    def __init__(
        self,
        use_embeddings: bool = True,
        always_include_tier1: bool = True
    ):
        """
        Initialize agent loader.

        Args:
            use_embeddings: Use semantic search (default: True)
            always_include_tier1: Always include Tier 1 agents (default: True)
        """
        self.use_embeddings = use_embeddings
        self.always_include_tier1 = always_include_tier1

        if use_embeddings:
            self.store = EmbeddingStore()

    def load(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Load top relevant agents for a query.

        Args:
            query: User query or task description
            top_k: Number of agents to load

        Returns:
            List of agent dicts with agent_id, similarity, tier
        """
        if self.use_embeddings:
            try:
                return self._load_with_embeddings(query, top_k)
            except Exception as e:
                print(f"Embedding search failed: {e}, falling back to keywords", file=sys.stderr)
                return self._load_with_keywords(query, top_k)
        else:
            return self._load_with_keywords(query, top_k)

    def _load_with_embeddings(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Load agents using semantic search."""
        # Get query embedding
        query_embedding = embed([query], input_type="query")[0]

        # Search in SQLite
        results = self.store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            source_type="agent"
        )

        # Convert to agent dicts
        agents = []
        for result in results:
            agents.append({
                'agent_id': result.record.source_id,
                'similarity': result.similarity,
                'tier': result.record.metadata.get('tier', 'unknown'),
                'description': result.record.content[:100]
            })

        # Ensure some Tier 1 agents always included
        if self.always_include_tier1:
            agents = self._ensure_tier1_agents(agents, top_k)

        return agents[:top_k]

    def _load_with_keywords(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback: Load agents using keyword matching."""
        keywords = query.lower().split()

        # Hardcoded keyword mappings
        keyword_map = {
            'bug': ['bug-whisperer'],
            'security': ['security-auditor'],
            'test': ['test-writer-fixer'],
            'performance': ['performance-optimizer', 'query-optimizer'],
            'refactor': ['refactoring-expert'],
            'api': ['api-designer'],
            'review': ['code-reviewer'],
            'vulnerability': ['security-auditor'],
            'authentication': ['security-auditor'],
        }

        matched_agents = set()
        for keyword in keywords:
            if keyword in keyword_map:
                matched_agents.update(keyword_map[keyword])

        # Always include code-reviewer (Tier 1)
        matched_agents.add('code-reviewer')

        # Convert to agent dicts
        agents = [
            {
                'agent_id': agent_id,
                'similarity': 0.5,  # Keyword match = medium similarity
                'tier': 'tier-1-always-active' if agent_id == 'code-reviewer' else 'tier-2-on-demand',
                'description': ''
            }
            for agent_id in list(matched_agents)[:top_k]
        ]

        return agents

    def _ensure_tier1_agents(self, agents: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Ensure at least 3 Tier 1 agents are included."""
        tier1_agents = [a for a in agents if a['tier'] == 'tier-1-always-active']

        # If we have enough Tier 1, return as-is
        if len(tier1_agents) >= 3:
            return agents

        # Add essential Tier 1 agents
        essential_tier1 = ['code-reviewer', 'bug-whisperer', 'documentation-maintainer']

        for agent_id in essential_tier1:
            if agent_id not in [a['agent_id'] for a in agents]:
                agents.append({
                    'agent_id': agent_id,
                    'similarity': 0.7,
                    'tier': 'tier-1-always-active',
                    'description': ''
                })

            if len([a for a in agents if a['tier'] == 'tier-1-always-active']) >= 3:
                break

        # Re-sort by similarity
        agents.sort(key=lambda a: a['similarity'], reverse=True)

        return agents


def load_relevant_agents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Load relevant agents for a query (convenience function).

    Args:
        query: User query or task description
        top_k: Number of agents to load

    Returns:
        List of agent dicts
    """
    loader = AgentLoader()
    return loader.load(query, top_k)
