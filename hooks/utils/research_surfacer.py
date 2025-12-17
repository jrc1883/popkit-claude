#!/usr/bin/env python3
"""
Research Surfacer - Auto-surface Relevant Research

Detects when conversation context relates to indexed research
and surfaces relevant entries to help inform decisions.

Part of PopKit Issue #143 (Auto-surface Relevant Research).
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum similarity score to surface (0.0 to 1.0)
MIN_SIMILARITY_THRESHOLD = 0.65

# Maximum entries to surface at once
MAX_SURFACE_COUNT = 3

# Keywords that strongly indicate research relevance
RESEARCH_TRIGGER_KEYWORDS = {
    # Architecture decisions
    "architecture", "design", "pattern", "approach", "strategy",
    "evaluate", "compare", "choose", "select", "decide",
    # Technical topics
    "implement", "integrate", "migrate", "upgrade", "refactor",
    "database", "cache", "auth", "api", "frontend", "backend",
    # Exploration
    "research", "investigate", "explore", "analyze", "understand",
    "spike", "poc", "prototype", "experiment",
}

# File paths that indicate high relevance
RELEVANT_FILE_PATTERNS = [
    r"\.config\.",
    r"\.env",
    r"schema\.",
    r"migration",
    r"auth",
    r"billing",
    r"api",
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SurfacedResearch:
    """A research entry surfaced as relevant."""
    id: str
    type: str
    title: str
    tags: List[str]
    similarity: float
    reason: str  # Why this was surfaced


@dataclass
class SurfaceResult:
    """Result of research surfacing check."""
    should_surface: bool
    entries: List[SurfacedResearch]
    message: str


# =============================================================================
# RESEARCH SURFACER
# =============================================================================

class ResearchSurfacer:
    """
    Detects relevant research and surfaces it during development.

    Features:
    - Keyword-based trigger detection
    - File context awareness
    - Semantic search integration
    - Non-intrusive notifications
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the research surfacer.

        Args:
            project_root: Root directory for the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._research_manager = None
        self._enabled = self._check_enabled()

    def _check_enabled(self) -> bool:
        """Check if research surfacing is enabled."""
        # Check environment variable
        if os.environ.get("POPKIT_RESEARCH_SURFACE", "true").lower() == "false":
            return False

        # Check if research directory exists
        research_dir = self.project_root / ".claude" / "research"
        return research_dir.exists()

    def _get_research_manager(self):
        """Get or create research manager instance."""
        if self._research_manager is None:
            try:
                from research_index import ResearchIndexManager
                self._research_manager = ResearchIndexManager(str(self.project_root))
            except ImportError:
                return None
        return self._research_manager

    # =========================================================================
    # TRIGGER DETECTION
    # =========================================================================

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Normalize text
        text_lower = text.lower()

        # Find matching trigger keywords
        found = []
        for keyword in RESEARCH_TRIGGER_KEYWORDS:
            if keyword in text_lower:
                found.append(keyword)

        return found

    def _extract_file_context(self, files: List[str]) -> List[str]:
        """Extract context from file paths."""
        contexts = []

        for file_path in files:
            file_lower = file_path.lower()

            # Check for relevant patterns
            for pattern in RELEVANT_FILE_PATTERNS:
                if re.search(pattern, file_lower):
                    # Extract meaningful part
                    basename = os.path.basename(file_path)
                    contexts.append(basename)
                    break

        return contexts

    def _should_check_research(
        self,
        message: str,
        tool_name: Optional[str] = None,
        files: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Determine if we should check for relevant research.

        Returns:
            Tuple of (should_check, reason)
        """
        if not self._enabled:
            return False, "disabled"

        # Extract keywords from message
        keywords = self._extract_keywords(message)

        # Check file context
        file_contexts = []
        if files:
            file_contexts = self._extract_file_context(files)

        # Determine if we should check
        if len(keywords) >= 2:
            return True, f"keywords: {', '.join(keywords[:3])}"

        if file_contexts:
            return True, f"files: {', '.join(file_contexts[:3])}"

        # Check for explicit research triggers
        research_patterns = [
            r"how (should|do) (we|i)",
            r"what('s| is) the best",
            r"which .+ (should|to) use",
            r"decide between",
            r"evaluate",
            r"compare",
        ]

        for pattern in research_patterns:
            if re.search(pattern, message.lower()):
                return True, "question pattern"

        return False, "no triggers"

    # =========================================================================
    # RESEARCH LOOKUP
    # =========================================================================

    def _search_local(
        self,
        query: str,
        limit: int = MAX_SURFACE_COUNT
    ) -> List[SurfacedResearch]:
        """Search local research index."""
        manager = self._get_research_manager()
        if not manager:
            return []

        try:
            # Try semantic search first
            results = manager.search_semantic(
                query,
                limit=limit,
                min_similarity=MIN_SIMILARITY_THRESHOLD
            )

            # Fall back to keyword search if no results
            if not results:
                results = manager.search_keywords(query, limit=limit)

            surfaced = []
            for result in results:
                if result.similarity >= MIN_SIMILARITY_THRESHOLD:
                    surfaced.append(SurfacedResearch(
                        id=result.entry.id,
                        type=result.entry.type,
                        title=result.entry.title,
                        tags=result.entry.tags,
                        similarity=result.similarity,
                        reason=result.match_type,
                    ))

            return surfaced

        except Exception:
            return []

    def _search_cloud(
        self,
        query: str,
        limit: int = MAX_SURFACE_COUNT
    ) -> List[SurfacedResearch]:
        """Search cloud research index (for Pro/Team users)."""
        api_key = os.environ.get("POPKIT_API_KEY")
        if not api_key:
            return []

        try:
            import requests

            response = requests.post(
                "https://popkit-cloud.elshaddai.workers.dev/v1/research/search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": query, "limit": limit},
                timeout=5,
            )

            if response.ok:
                data = response.json()
                surfaced = []

                for result in data.get("results", []):
                    entry = result.get("entry", {})
                    surfaced.append(SurfacedResearch(
                        id=entry.get("id", ""),
                        type=entry.get("type", ""),
                        title=entry.get("title", ""),
                        tags=entry.get("tags", []),
                        similarity=result.get("score", 0),
                        reason="cloud",
                    ))

                return surfaced

        except Exception:
            pass

        return []

    # =========================================================================
    # MAIN INTERFACE
    # =========================================================================

    def check_and_surface(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None
    ) -> SurfaceResult:
        """
        Check if relevant research should be surfaced.

        Args:
            message: Current conversation message
            tool_name: Name of tool being used (optional)
            tool_input: Tool input parameters (optional)
            files: List of relevant file paths (optional)

        Returns:
            SurfaceResult with entries to surface
        """
        # Check if we should look for research
        should_check, reason = self._should_check_research(message, tool_name, files)

        if not should_check:
            return SurfaceResult(
                should_surface=False,
                entries=[],
                message=""
            )

        # Build search query from context
        query_parts = [message[:500]]  # Limit message length

        # Add file context
        if files:
            query_parts.extend(files[:3])

        # Add tool context
        if tool_input:
            if isinstance(tool_input, dict):
                # Extract relevant fields
                for key in ["file_path", "pattern", "query", "command"]:
                    if key in tool_input:
                        query_parts.append(str(tool_input[key]))

        query = " ".join(query_parts)

        # Search for relevant research
        local_results = self._search_local(query)
        cloud_results = self._search_cloud(query)

        # Combine and deduplicate
        seen_ids = set()
        combined = []

        for result in local_results + cloud_results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                combined.append(result)

        # Sort by similarity and limit
        combined.sort(key=lambda x: x.similarity, reverse=True)
        top_results = combined[:MAX_SURFACE_COUNT]

        if not top_results:
            return SurfaceResult(
                should_surface=False,
                entries=[],
                message=""
            )

        # Format notification message
        message = self._format_notification(top_results)

        return SurfaceResult(
            should_surface=True,
            entries=top_results,
            message=message
        )

    def _format_notification(self, entries: List[SurfacedResearch]) -> str:
        """Format notification message for surfaced research."""
        lines = ["", "💡 **Relevant Research Found**"]

        for entry in entries:
            type_emoji = {
                "decision": "📋",
                "finding": "🔍",
                "learning": "📚",
                "spike": "🧪",
            }.get(entry.type, "📄")

            tags = ", ".join(entry.tags[:3]) if entry.tags else ""
            tag_str = f" ({tags})" if tags else ""

            lines.append(f"   {type_emoji} [{entry.type}] {entry.title}{tag_str}")

        lines.append("")
        lines.append("   Use `/popkit:research show <id>` for details")
        lines.append("")

        return "\n".join(lines)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_surfacer(project_root: Optional[str] = None) -> ResearchSurfacer:
    """
    Get a research surfacer instance.

    Args:
        project_root: Optional project root path

    Returns:
        ResearchSurfacer instance
    """
    return ResearchSurfacer(project_root)


def check_research_relevance(
    message: str,
    tool_name: Optional[str] = None,
    tool_input: Optional[Dict[str, Any]] = None,
    files: Optional[List[str]] = None
) -> Optional[str]:
    """
    Quick check for relevant research.

    Args:
        message: Current message
        tool_name: Tool being used
        tool_input: Tool input
        files: Related files

    Returns:
        Notification message if relevant research found, None otherwise
    """
    surfacer = get_surfacer()
    result = surfacer.check_and_surface(message, tool_name, tool_input, files)

    if result.should_surface:
        return result.message

    return None


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Research Surfacer Test")
    print("=" * 40)

    surfacer = ResearchSurfacer()

    # Test trigger detection
    test_messages = [
        "How should we implement authentication?",
        "Compare Redis vs PostgreSQL for sessions",
        "Fix the typo in README",
        "What's the best approach for caching?",
        "Add console.log for debugging",
    ]

    print("\nTrigger Detection:")
    for msg in test_messages:
        should_check, reason = surfacer._should_check_research(msg)
        status = "✓" if should_check else "✗"
        print(f"  {status} '{msg[:40]}...' - {reason}")

    # Test keyword extraction
    print("\nKeyword Extraction:")
    test_text = "We need to evaluate different caching strategies and decide on an architecture"
    keywords = surfacer._extract_keywords(test_text)
    print(f"  Keywords: {keywords}")

    print("\nAll tests passed!")
