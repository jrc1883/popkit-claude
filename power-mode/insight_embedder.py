#!/usr/bin/env python3
"""
Insight Embedder for Power Mode

Part of Issue #70 (Embedding-Enhanced Check-ins)

Provides embedding functionality for insights with hybrid approach:
1. Try PopKit Cloud (server-side, no local API key needed)
2. Fall back to local Voyage API (if VOYAGE_API_KEY available)
3. Fall back to no embedding (tag-based matching only)
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import urllib.request
import urllib.error

# Add hooks/utils to path for local Voyage client
HOOKS_UTILS = Path(__file__).parent.parent / "hooks" / "utils"
sys.path.insert(0, str(HOOKS_UTILS))


# =============================================================================
# CONFIGURATION
# =============================================================================

# Deduplication threshold (0.90 = strict)
DUPLICATE_THRESHOLD = 0.90

# Summary max length
SUMMARY_MAX_WORDS = 10


# =============================================================================
# CLOUD CLIENT
# =============================================================================

class CloudInsightEmbedder:
    """
    Embed insights via PopKit Cloud API.

    Uses server-side embedding generation - no local Voyage API key needed.
    """

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    def embed_insight(
        self,
        insight_id: str,
        content: str,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Embed an insight via cloud API.

        Returns:
            {
                "status": "created" | "duplicate",
                "insight_id": str,
                "tokens": int,
                "cost": float,
                "duplicate"?: { "id": str, "similarity": float }
            }
        """
        url = f"{self.base_url}/embeddings/insight"

        body = {
            "insight_id": insight_id,
            "content": content,
        }
        if summary:
            body["summary"] = summary

        return self._request("POST", url, body)

    def search_similar(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.5,
        exclude_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar insights.

        Returns:
            {
                "results": [{ "id": str, "summary": str, "similarity": float }],
                "tokens": int,
                "cost": float
            }
        """
        url = f"{self.base_url}/embeddings/search"

        body = {
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }
        if exclude_ids:
            body["exclude_ids"] = exclude_ids

        return self._request("POST", url, body)

    def get_usage(self) -> Dict[str, Any]:
        """Get embedding usage statistics."""
        url = f"{self.base_url}/embeddings/usage"
        return self._request("GET", url)

    def _request(self, method: str, url: str, body: Optional[Dict] = None) -> Dict:
        """Make HTTP request to cloud API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = None
        if body:
            data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Cloud API error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")


# =============================================================================
# LOCAL CLIENT (FALLBACK)
# =============================================================================

class LocalInsightEmbedder:
    """
    Embed insights using local Voyage API.

    Requires VOYAGE_API_KEY environment variable.
    """

    def __init__(self):
        self.voyage_client = None
        self._try_load_voyage()

    def _try_load_voyage(self):
        """Try to load local Voyage client."""
        try:
            from voyage_client import VoyageClient
            self.voyage_client = VoyageClient()
        except ImportError:
            pass
        except Exception:
            pass

    @property
    def available(self) -> bool:
        """Check if local embedding is available."""
        return self.voyage_client is not None

    def embed_insight(
        self,
        insight_id: str,
        content: str,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Embed an insight locally."""
        if not self.available:
            raise RuntimeError("Local Voyage client not available")

        embedding = self.voyage_client.embed_document(content)

        return {
            "status": "created",
            "insight_id": insight_id,
            "embedding": embedding,
            "dimensions": len(embedding),
            "local": True
        }

    def search_similar(
        self,
        query: str,
        embeddings: Dict[str, List[float]],
        limit: int = 5,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Search for similar insights in provided embeddings."""
        if not self.available:
            return []

        query_embedding = self.voyage_client.embed_query(query)

        results = []
        for insight_id, embedding in embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity >= threshold:
                results.append({
                    "id": insight_id,
                    "similarity": similarity
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


# =============================================================================
# HYBRID EMBEDDER
# =============================================================================

class InsightEmbedder:
    """
    Hybrid insight embedder with fallback chain:
    1. PopKit Cloud (if POPKIT_API_KEY set)
    2. Local Voyage (if VOYAGE_API_KEY set)
    3. No embedding (graceful degradation)
    """

    def __init__(self):
        self.cloud_client: Optional[CloudInsightEmbedder] = None
        self.local_client: Optional[LocalInsightEmbedder] = None
        self.mode = "none"

        self._initialize()

    def _initialize(self):
        """Initialize the best available embedder."""
        # Try cloud first
        api_key = os.environ.get("POPKIT_API_KEY")
        cloud_enabled = os.environ.get("POPKIT_CLOUD_ENABLED", "true").lower() != "false"

        if api_key and cloud_enabled:
            base_url = os.environ.get(
                "POPKIT_CLOUD_URL",
                "https://popkit-cloud-api.joseph-cannon.workers.dev/v1"
            )
            self.cloud_client = CloudInsightEmbedder(api_key, base_url)
            self.mode = "cloud"
            return

        # Try local Voyage
        self.local_client = LocalInsightEmbedder()
        if self.local_client.available:
            self.mode = "local"
            return

        # No embedding available
        self.mode = "none"

    @property
    def available(self) -> bool:
        """Check if any embedding is available."""
        return self.mode != "none"

    def embed_insight(
        self,
        content: str,
        from_agent: str,
        insight_type: str = "discovery"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Embed an insight and check for duplicates.

        Args:
            content: Full insight content
            from_agent: Agent ID that created the insight
            insight_type: Type of insight (discovery, pattern, blocker)

        Returns:
            Tuple of (insight_id, result_dict)

            If duplicate: result has "status": "duplicate"
            If created: result has "status": "created"
            If no embedding: result has "status": "skipped"
        """
        # Generate insight ID
        insight_id = self._generate_insight_id(content, from_agent)

        # Generate summary
        summary = self._generate_summary(content)

        if self.mode == "cloud":
            try:
                result = self.cloud_client.embed_insight(insight_id, content, summary)
                result["summary"] = summary
                return insight_id, result
            except Exception as e:
                # Fall through to local if cloud fails
                if self.local_client and self.local_client.available:
                    self.mode = "local"
                else:
                    return insight_id, {
                        "status": "error",
                        "error": str(e),
                        "summary": summary
                    }

        if self.mode == "local":
            try:
                result = self.local_client.embed_insight(insight_id, content, summary)
                result["summary"] = summary
                return insight_id, result
            except Exception as e:
                return insight_id, {
                    "status": "error",
                    "error": str(e),
                    "summary": summary
                }

        # No embedding - return basic insight
        return insight_id, {
            "status": "skipped",
            "reason": "no_embedding_available",
            "summary": summary
        }

    def search_relevant(
        self,
        context: str,
        exclude_agent: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Search for relevant insights based on context.

        Args:
            context: Current work context (files, task, etc.)
            exclude_agent: Agent ID to exclude (self)
            limit: Max results

        Returns:
            List of relevant insights with similarity scores
        """
        if self.mode == "cloud":
            try:
                result = self.cloud_client.search_similar(
                    query=context,
                    limit=limit,
                    threshold=0.5,
                    exclude_ids=[]  # Cloud handles exclusion differently
                )
                return result.get("results", [])
            except Exception:
                pass

        # Local or no embedding - return empty
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get embedding statistics."""
        stats = {
            "mode": self.mode,
            "available": self.available
        }

        if self.mode == "cloud":
            try:
                usage = self.cloud_client.get_usage()
                stats["usage"] = usage
            except Exception:
                pass

        return stats

    def _generate_insight_id(self, content: str, from_agent: str) -> str:
        """Generate unique insight ID."""
        data = f"{content}{from_agent}{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _generate_summary(self, content: str) -> str:
        """Generate short summary from content."""
        words = content.split()
        if len(words) <= SUMMARY_MAX_WORDS:
            return content

        # Take first N words
        return " ".join(words[:SUMMARY_MAX_WORDS]) + "..."


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI for testing the insight embedder."""
    print("=" * 50)
    print("Insight Embedder Test")
    print("=" * 50)

    embedder = InsightEmbedder()

    print(f"\nMode: {embedder.mode}")
    print(f"Available: {embedder.available}")

    if not embedder.available:
        print("\n[WARN] No embedding available")
        print("Set POPKIT_API_KEY or VOYAGE_API_KEY")
        return

    # Test embedding
    print("\n[TEST] Embedding insight...")
    insight_id, result = embedder.embed_insight(
        content="Found authentication module at src/auth using JWT tokens",
        from_agent="test-agent",
        insight_type="discovery"
    )

    print(f"  Insight ID: {insight_id}")
    print(f"  Status: {result.get('status')}")
    print(f"  Summary: {result.get('summary')}")

    if result.get("status") == "duplicate":
        print(f"  Duplicate of: {result.get('duplicate', {}).get('id')}")
        print(f"  Similarity: {result.get('duplicate', {}).get('similarity'):.4f}")

    # Test search
    print("\n[TEST] Searching for relevant insights...")
    results = embedder.search_relevant(
        context="authentication login security",
        exclude_agent="other-agent",
        limit=3
    )

    print(f"  Found: {len(results)} results")
    for r in results:
        print(f"    - {r.get('id')}: {r.get('summary', 'N/A')} ({r.get('similarity', 0):.4f})")

    # Get stats
    print("\n[TEST] Getting stats...")
    stats = embedder.get_stats()
    print(f"  Mode: {stats.get('mode')}")
    if "usage" in stats:
        usage = stats["usage"]
        print(f"  Today: {usage.get('today', {}).get('tokens', 0)} tokens")
        print(f"  Total insights: {usage.get('total_insights', 0)}")

    print("\n" + "=" * 50)
    print("[OK] All tests completed!")


if __name__ == "__main__":
    main()
