#!/usr/bin/env python3
"""
Cloud Agent Search Client

Queries PopKit Cloud for semantic agent discovery using Upstash Vector.
Falls back to local keyword matching on failure.

Part of Issue #101 (Upstash Vector Integration).
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Optional
from dataclasses import dataclass


# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_API_URL = os.environ.get(
    "POPKIT_API_URL",
    "https://popkit-cloud-api.joseph-cannon.workers.dev"
)
TIMEOUT_SECONDS = 3  # Fast timeout for responsive UX


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentMatch:
    """Result from semantic agent search."""
    agent: str
    score: float
    tier: str
    description: str
    keywords: List[str]
    method: str  # "semantic" or "keyword" (for fallback tracking)


@dataclass
class SearchResult:
    """Complete search result with metadata."""
    query: str
    matches: List[AgentMatch]
    fallback_to_keywords: bool
    error: Optional[str] = None


# =============================================================================
# CLIENT FUNCTIONS
# =============================================================================

def is_available() -> bool:
    """Check if cloud agent search is configured.

    Requires POPKIT_API_KEY environment variable.
    """
    return bool(os.environ.get("POPKIT_API_KEY"))


def search_agents(
    query: str,
    top_k: int = 3,
    min_score: float = 0.3,
    tier: Optional[str] = None
) -> SearchResult:
    """
    Search for agents using semantic similarity via PopKit Cloud.

    Args:
        query: Natural language query (e.g., "optimize database queries")
        top_k: Number of results to return (max 10)
        min_score: Minimum similarity threshold (0.0 to 1.0)
        tier: Optional tier filter ("tier-1-always-active", "tier-2-on-demand", "feature-workflow")

    Returns:
        SearchResult with matches or error indication

    Example:
        >>> result = search_agents("optimize database queries")
        >>> for match in result.matches:
        ...     print(f"{match.agent}: {match.score:.2f}")
        query-optimizer: 0.85
        performance-optimizer: 0.72
    """
    api_key = os.environ.get("POPKIT_API_KEY")

    if not api_key:
        return SearchResult(
            query=query,
            matches=[],
            fallback_to_keywords=True,
            error="POPKIT_API_KEY not set"
        )

    url = f"{POPKIT_API_URL}/v1/agents/search"

    body = {
        "query": query,
        "topK": min(top_k, 10),  # Cap at 10
        "minScore": min_score,
    }
    if tier:
        body["tier"] = tier

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-PopKit-Version": "0.9.10",
    }

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))

            matches = [
                AgentMatch(
                    agent=m.get("agent", ""),
                    score=m.get("score", 0.0),
                    tier=m.get("tier", ""),
                    description=m.get("description", ""),
                    keywords=m.get("keywords", []),
                    method="semantic"
                )
                for m in data.get("matches", [])
            ]

            return SearchResult(
                query=query,
                matches=matches,
                fallback_to_keywords=data.get("fallback_to_keywords", len(matches) == 0)
            )

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}: {e.reason}"
        return SearchResult(
            query=query,
            matches=[],
            fallback_to_keywords=True,
            error=error_msg
        )

    except urllib.error.URLError as e:
        error_msg = f"Connection error: {e.reason}"
        return SearchResult(
            query=query,
            matches=[],
            fallback_to_keywords=True,
            error=error_msg
        )

    except TimeoutError:
        return SearchResult(
            query=query,
            matches=[],
            fallback_to_keywords=True,
            error="Request timeout"
        )

    except Exception as e:
        return SearchResult(
            query=query,
            matches=[],
            fallback_to_keywords=True,
            error=str(e)
        )


def list_agents() -> List[dict]:
    """
    List all indexed agents from PopKit Cloud.

    Returns:
        List of agent info dicts with id, name, tier, description
    """
    api_key = os.environ.get("POPKIT_API_KEY")

    if not api_key:
        return []

    url = f"{POPKIT_API_URL}/v1/agents/list"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-PopKit-Version": "0.9.10",
    }

    try:
        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET"
        )

        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("agents", [])

    except Exception:
        return []


def get_agent(name: str) -> Optional[dict]:
    """
    Get details for a specific agent.

    Args:
        name: Agent name (e.g., "query-optimizer")

    Returns:
        Agent info dict or None if not found
    """
    api_key = os.environ.get("POPKIT_API_KEY")

    if not api_key:
        return None

    url = f"{POPKIT_API_URL}/v1/agents/{name}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-PopKit-Version": "0.9.10",
    }

    try:
        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET"
        )

        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception:
        return None


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Quick test
    print("Testing cloud agent search...")
    print(f"API URL: {POPKIT_API_URL}")
    print(f"API Key configured: {is_available()}")
    print()

    if is_available():
        # Test search
        result = search_agents("optimize database queries")
        print(f"Query: {result.query}")
        print(f"Fallback: {result.fallback_to_keywords}")

        if result.error:
            print(f"Error: {result.error}")
        else:
            print(f"Matches: {len(result.matches)}")
            for m in result.matches:
                print(f"  {m.agent}: {m.score:.3f} ({m.tier})")
    else:
        print("Set POPKIT_API_KEY to test cloud search")
