#!/usr/bin/env python3
"""
Semantic Agent Router

Routes requests to agents using embedding similarity.
Falls back to keyword matching when embeddings unavailable.
Supports project-aware routing with priority for project-local items.

Part of PopKit Issue #19 (Embeddings Enhancement).
Updated for Issue #48 (Project Awareness).
"""

import os
import sys
import json
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from embedding_store import EmbeddingStore
from voyage_client import VoyageClient, is_available

# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = POPKIT_ROOT / "agents" / "config.json"

# Default confidence threshold
# Voyage-3.5 embeddings produce lower similarity scores than expected
# 0.3-0.5 is typical for good matches, 0.5+ is excellent
DEFAULT_MIN_CONFIDENCE = 0.3

# Project item boost (10% boost for project-local items)
PROJECT_ITEM_BOOST = 0.1


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RoutingResult:
    """Result of agent routing."""
    agent: str
    confidence: float
    reason: str
    method: str  # "semantic", "keyword", "file_pattern", "error_pattern"
    is_project_item: bool = False  # True if from project-local embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "confidence": self.confidence,
            "reason": self.reason,
            "method": self.method,
            "is_project_item": self.is_project_item
        }


# =============================================================================
# SEMANTIC ROUTER
# =============================================================================

class SemanticRouter:
    """
    Route requests to agents using semantic similarity.

    Features:
    - Semantic matching using embeddings
    - Project-aware routing with priority boost
    - Keyword fallback
    - File pattern matching
    - Error pattern matching
    - Confidence scoring
    """

    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize the semantic router.

        Args:
            project_path: Optional project root path for project-aware routing.
                         Auto-detected from cwd if not specified.
        """
        self.store = EmbeddingStore()
        self.client = VoyageClient() if is_available() else None
        self._config = self._load_config()

        # Set up project awareness
        if project_path:
            self.project_path = project_path
        else:
            # Auto-detect project root
            self.project_path = self._detect_project_root()

    def _detect_project_root(self) -> Optional[str]:
        """Auto-detect project root from cwd."""
        try:
            from embedding_project import get_project_root
            return get_project_root()
        except ImportError:
            # Fallback: look for .claude or .git
            current = Path.cwd()
            for path in [current] + list(current.parents):
                if (path / ".claude").is_dir() or (path / ".git").is_dir():
                    return str(path)
            return None

    def _load_config(self) -> Dict[str, Any]:
        """Load agent routing config."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def route(
        self,
        query: str,
        top_k: int = 3,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RoutingResult]:
        """
        Route query to best matching agents.

        Args:
            query: User request or context
            top_k: Number of agents to return
            min_confidence: Minimum confidence threshold
            context: Optional context (file paths, error messages, etc.)

        Returns:
            List of RoutingResult ordered by confidence
        """
        context = context or {}
        results = []

        # Try semantic routing first (if embeddings available)
        if self.client and self.client.is_available and self.store.count("agent") > 0:
            semantic_results = self._semantic_route(query, top_k, min_confidence)
            results.extend(semantic_results)

        # Check file patterns
        file_path = context.get("file_path", "")
        if file_path:
            file_results = self._file_pattern_route(file_path)
            results.extend(file_results)

        # Check error patterns
        error = context.get("error", "")
        if error:
            error_results = self._error_pattern_route(error)
            results.extend(error_results)

        # Keyword fallback
        if len(results) < top_k:
            keyword_results = self._keyword_route(query, top_k - len(results))
            results.extend(keyword_results)

        # Deduplicate and sort
        results = self._deduplicate_results(results)
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results[:top_k]

    def route_single(
        self,
        query: str,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RoutingResult]:
        """
        Route to single best agent.

        Returns:
            Best RoutingResult or None if no match
        """
        results = self.route(query, top_k=1, min_confidence=min_confidence, context=context)
        return results[0] if results else None

    def explain_routing(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed routing explanation.

        Returns:
            Dictionary with routing details including project context
        """
        context = context or {}

        # Compute project embedding count
        project_count = 0
        if self.project_path:
            project_count = self.store.count_project(self.project_path)

        explanation = {
            "query": query,
            "context": context,
            "project_path": self.project_path,
            "semantic_available": bool(self.client and self.client.is_available),
            "embedding_count": self.store.count("agent"),
            "project_embedding_count": project_count,
            "methods_tried": [],
            "results": []
        }

        # Try each method and record results
        if self.client and self.client.is_available and self.store.count("agent") > 0:
            explanation["methods_tried"].append("semantic")
            semantic = self._semantic_route(query, 5, 0.0)
            explanation["semantic_results"] = [r.to_dict() for r in semantic]

        if context.get("file_path"):
            explanation["methods_tried"].append("file_pattern")
            file_results = self._file_pattern_route(context["file_path"])
            explanation["file_pattern_results"] = [r.to_dict() for r in file_results]

        if context.get("error"):
            explanation["methods_tried"].append("error_pattern")
            error_results = self._error_pattern_route(context["error"])
            explanation["error_pattern_results"] = [r.to_dict() for r in error_results]

        explanation["methods_tried"].append("keyword")
        keyword_results = self._keyword_route(query, 5)
        explanation["keyword_results"] = [r.to_dict() for r in keyword_results]

        # Final results
        final = self.route(query, top_k=5, min_confidence=0.0, context=context)
        explanation["results"] = [r.to_dict() for r in final]

        return explanation

    def route_for_project(
        self,
        query: str,
        project_path: str,
        top_k: int = 3,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RoutingResult]:
        """
        Route with explicit project context.

        Temporarily sets project path for routing, then restores original.
        Useful when routing for a specific project different from auto-detected.

        Args:
            query: User request or context
            project_path: Explicit project root path
            top_k: Number of agents to return
            min_confidence: Minimum confidence threshold
            context: Optional context (file paths, error messages, etc.)

        Returns:
            List of RoutingResult ordered by confidence
        """
        old_path = self.project_path
        self.project_path = project_path

        try:
            return self.route(query, top_k=top_k, min_confidence=min_confidence, context=context)
        finally:
            self.project_path = old_path

    # =========================================================================
    # ROUTING METHODS
    # =========================================================================

    def _semantic_route(
        self,
        query: str,
        top_k: int,
        min_confidence: float
    ) -> List[RoutingResult]:
        """Route using embedding similarity with project awareness."""
        if not self.client:
            return []

        try:
            query_embedding = self.client.embed_query(query)

            # Use project-aware search if project path is set
            if self.project_path and self.store.count_project(self.project_path) > 0:
                # Search project items + global agents
                results = self.store.search_project(
                    query_embedding=query_embedding,
                    project_path=self.project_path,
                    source_type=None,  # Search all types
                    top_k=top_k * 2,  # Get more for filtering
                    min_similarity=min_confidence,
                    include_global=True,
                    global_boost=0.0  # We'll handle boost ourselves
                )

                # Filter to agent types only
                agent_types = {"agent", "project-agent", "generated-agent"}
                results = [r for r in results if r.record.source_type in agent_types]
            else:
                # Fall back to global search
                results = self.store.search(
                    query_embedding=query_embedding,
                    source_type="agent",
                    top_k=top_k,
                    min_similarity=min_confidence
                )

            # Convert to RoutingResult with project boost
            routing_results = []
            for r in results:
                is_project = r.record.source_type.startswith("project-") or \
                             r.record.source_type.startswith("generated-")

                # Apply boost for project items
                confidence = r.similarity
                if is_project:
                    confidence = min(1.0, confidence + PROJECT_ITEM_BOOST)

                routing_results.append(RoutingResult(
                    agent=r.record.source_id,
                    confidence=confidence,
                    reason=f"Semantic match: {r.record.content[:60]}...",
                    method="semantic",
                    is_project_item=is_project
                ))

            # Sort by confidence and return top_k
            routing_results.sort(key=lambda x: x.confidence, reverse=True)
            return routing_results[:top_k]

        except Exception as e:
            print(f"Semantic routing error: {e}")
            return []

    def _keyword_route(
        self,
        query: str,
        top_k: int
    ) -> List[RoutingResult]:
        """Route using keyword matching."""
        keywords = self._config.get("keywords", {})
        query_lower = query.lower()

        matches = []
        for keyword, agents in keywords.items():
            if keyword.lower() in query_lower:
                for agent in agents:
                    matches.append(RoutingResult(
                        agent=agent,
                        confidence=0.8,  # Keyword matches get 0.8 confidence
                        reason=f"Keyword match: '{keyword}'",
                        method="keyword"
                    ))

        return matches[:top_k]

    def _file_pattern_route(self, file_path: str) -> List[RoutingResult]:
        """Route based on file pattern."""
        import fnmatch

        patterns = self._config.get("filePatterns", {})
        results = []

        for pattern, agents in patterns.items():
            if fnmatch.fnmatch(file_path, pattern):
                for agent in agents:
                    results.append(RoutingResult(
                        agent=agent,
                        confidence=0.9,  # File patterns get 0.9 confidence
                        reason=f"File pattern: '{pattern}'",
                        method="file_pattern"
                    ))

        return results

    def _error_pattern_route(self, error: str) -> List[RoutingResult]:
        """Route based on error pattern."""
        patterns = self._config.get("errorPatterns", {})
        results = []

        for pattern, agents in patterns.items():
            if pattern.lower() in error.lower():
                for agent in agents:
                    results.append(RoutingResult(
                        agent=agent,
                        confidence=0.85,  # Error patterns get 0.85 confidence
                        reason=f"Error pattern: '{pattern}'",
                        method="error_pattern"
                    ))

        return results

    def _deduplicate_results(
        self,
        results: List[RoutingResult]
    ) -> List[RoutingResult]:
        """Remove duplicate agents, keeping highest confidence."""
        seen = {}
        for result in results:
            if result.agent not in seen or result.confidence > seen[result.agent].confidence:
                seen[result.agent] = result
        return list(seen.values())


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_router: Optional[SemanticRouter] = None


def get_router() -> SemanticRouter:
    """Get or create the singleton router."""
    global _router
    if _router is None:
        _router = SemanticRouter()
    return _router


def route(
    query: str,
    top_k: int = 3,
    context: Optional[Dict[str, Any]] = None
) -> List[RoutingResult]:
    """Convenience function to route a query."""
    return get_router().route(query, top_k=top_k, context=context)


def route_single(
    query: str,
    context: Optional[Dict[str, Any]] = None
) -> Optional[RoutingResult]:
    """Convenience function to get single best agent."""
    return get_router().route_single(query, context=context)


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Semantic agent routing")
    parser.add_argument("query", nargs="?", default="", help="Query to route")
    parser.add_argument("--file", "-f", help="File path context")
    parser.add_argument("--error", "-e", help="Error message context")
    parser.add_argument("--explain", "-x", action="store_true", help="Show detailed explanation")
    parser.add_argument("--top", "-k", type=int, default=3, help="Number of results")

    args = parser.parse_args()

    if not args.query:
        print("Usage: python semantic_router.py 'your query here'")
        print("\nExamples:")
        print("  python semantic_router.py 'fix a security vulnerability'")
        print("  python semantic_router.py 'write tests' -f src/app.test.ts")
        print("  python semantic_router.py 'handle error' -e TypeError")
        sys.exit(1)

    router = SemanticRouter()

    context = {}
    if args.file:
        context["file_path"] = args.file
    if args.error:
        context["error"] = args.error

    if args.explain:
        explanation = router.explain_routing(args.query, context)
        print(json.dumps(explanation, indent=2))
    else:
        results = router.route(args.query, top_k=args.top, context=context)

        print(f"Query: {args.query}")
        if context:
            print(f"Context: {context}")
        print(f"\nResults ({len(results)}):")
        print("-" * 50)

        for i, result in enumerate(results, 1):
            print(f"{i}. {result.agent}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Method: {result.method}")
            print(f"   Reason: {result.reason}")
            print()
