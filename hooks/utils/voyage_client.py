#!/usr/bin/env python3
"""
Voyage Embedding Client

Client for Voyage AI embedding API (voyage-3.5).
Includes caching, rate limiting, and batch processing.

Part of PopKit Issue #19 (Embeddings Enhancement).
"""

import os
import json
import hashlib
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import urllib.request
import urllib.error

# Load .env file if available (for API keys)
def _load_dotenv():
    """Load environment variables from .env files."""
    # Check multiple locations for .env
    env_locations = [
        Path.cwd() / ".env",                          # Project root
        Path(__file__).parent.parent.parent / ".env", # PopKit root
        Path.home() / ".claude" / ".env",             # User claude config
    ]

    for env_path in env_locations:
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = value
                break  # Use first .env found
            except Exception:
                pass

_load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3.5"
EMBEDDING_DIM = 1024  # voyage-3.5 output dimension

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 300
MAX_TOKENS_PER_MINUTE = 1_000_000
BATCH_SIZE = 128  # Max texts per request


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EmbeddingResponse:
    """Response from embedding API."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class EmbeddingUsage:
    """Track API usage for rate limiting."""
    total_tokens: int = 0
    total_requests: int = 0
    last_reset: float = field(default_factory=time.time)

    def add(self, tokens: int) -> None:
        """Add usage."""
        now = time.time()
        # Reset counters every minute
        if now - self.last_reset > 60:
            self.total_tokens = 0
            self.total_requests = 0
            self.last_reset = now

        self.total_tokens += tokens
        self.total_requests += 1

    def can_request(self, estimated_tokens: int) -> Tuple[bool, float]:
        """
        Check if request is allowed.

        Returns:
            (allowed, wait_seconds)
        """
        now = time.time()
        elapsed = now - self.last_reset

        if elapsed > 60:
            return True, 0

        if self.total_requests >= MAX_REQUESTS_PER_MINUTE:
            return False, 60 - elapsed

        if self.total_tokens + estimated_tokens > MAX_TOKENS_PER_MINUTE:
            return False, 60 - elapsed

        return True, 0


# =============================================================================
# VOYAGE CLIENT
# =============================================================================

class VoyageClient:
    """
    Client for Voyage embedding API.

    Features:
    - Automatic API key from environment
    - Response caching
    - Rate limiting
    - Batch processing
    - Retry with backoff
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = VOYAGE_MODEL,
        cache_enabled: bool = True
    ):
        """
        Initialize Voyage client.

        Args:
            api_key: Voyage API key (defaults to VOYAGE_API_KEY env var)
            model: Embedding model name
            cache_enabled: Enable response caching
        """
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self.model = model
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, List[float]] = {}
        self._usage = EmbeddingUsage()

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def embed(
        self,
        texts: List[str],
        input_type: str = "document"
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed
            input_type: "document" for content, "query" for search queries

        Returns:
            List of embedding vectors (1024 dimensions each)

        Raises:
            ValueError: If API key not set
            RuntimeError: If API call fails
        """
        if not self.api_key:
            raise ValueError(
                "VOYAGE_API_KEY not set. "
                "Set environment variable or pass api_key to constructor."
            )

        if not texts:
            return []

        # Check cache for all texts
        results = [None] * len(texts)
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if self.cache_enabled:
                cache_key = self._cache_key(text, input_type)
                if cache_key in self._cache:
                    results[i] = self._cache[cache_key]
                    continue

            uncached_texts.append(text)
            uncached_indices.append(i)

        # Fetch uncached embeddings in batches
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(uncached_texts))
                batch_texts = uncached_texts[batch_start:batch_end]
                batch_indices = uncached_indices[batch_start:batch_end]

                # Rate limiting
                estimated_tokens = sum(len(t.split()) * 1.3 for t in batch_texts)
                self._wait_for_rate_limit(int(estimated_tokens))

                # API call with retry
                response = self._call_api_with_retry(batch_texts, input_type)

                # Store results and update cache
                for j, embedding in enumerate(response.embeddings):
                    idx = batch_indices[j]
                    results[idx] = embedding

                    if self.cache_enabled:
                        cache_key = self._cache_key(batch_texts[j], input_type)
                        self._cache[cache_key] = embedding

                # Update usage
                self._usage.add(response.usage.get("total_tokens", 0))

        return results

    def embed_single(
        self,
        text: str,
        input_type: str = "document"
    ) -> List[float]:
        """
        Embed a single text string.

        Args:
            text: Text to embed
            input_type: "document" or "query"

        Returns:
            Embedding vector (1024 dimensions)
        """
        return self.embed([text], input_type)[0]

    def embed_query(self, query: str) -> List[float]:
        """Shorthand for embedding a search query."""
        return self.embed_single(query, input_type="query")

    def embed_document(self, document: str) -> List[float]:
        """Shorthand for embedding a document."""
        return self.embed_single(document, input_type="document")

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @property
    def cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._cache)

    @property
    def usage(self) -> Dict[str, int]:
        """Get current usage stats."""
        return {
            "total_tokens": self._usage.total_tokens,
            "total_requests": self._usage.total_requests
        }

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _call_api(
        self,
        texts: List[str],
        input_type: str
    ) -> EmbeddingResponse:
        """Make API call to Voyage."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = json.dumps({
            "model": self.model,
            "input": texts,
            "input_type": input_type
        }).encode("utf-8")

        request = urllib.request.Request(
            VOYAGE_API_URL,
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                return EmbeddingResponse(
                    embeddings=[item["embedding"] for item in result["data"]],
                    model=result["model"],
                    usage=result.get("usage", {})
                )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Voyage API error {e.code}: {e.reason}\n{body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    def _call_api_with_retry(
        self,
        texts: List[str],
        input_type: str,
        max_attempts: int = 3,
        initial_delay: float = 1.0
    ) -> EmbeddingResponse:
        """Call API with exponential backoff retry."""
        last_error = None
        delay = initial_delay

        for attempt in range(max_attempts):
            try:
                return self._call_api(texts, input_type)
            except RuntimeError as e:
                last_error = e
                error_str = str(e)

                # Don't retry auth errors
                if "401" in error_str or "403" in error_str:
                    raise

                # Don't retry invalid requests
                if "400" in error_str:
                    raise

                # Retry rate limits and server errors
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    delay *= 2

        raise last_error

    def _wait_for_rate_limit(self, estimated_tokens: int) -> None:
        """Wait if rate limit would be exceeded."""
        allowed, wait_time = self._usage.can_request(estimated_tokens)
        if not allowed and wait_time > 0:
            time.sleep(wait_time)

    def _cache_key(self, text: str, input_type: str) -> str:
        """Generate cache key for text."""
        content = f"{self.model}:{input_type}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:24]

    def clear_cache(self) -> int:
        """Clear the response cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_client: Optional[VoyageClient] = None


def get_client() -> VoyageClient:
    """Get or create the singleton Voyage client."""
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


def embed_query(query: str) -> List[float]:
    """Convenience function to embed a search query."""
    return get_client().embed_query(query)


def embed_document(document: str) -> List[float]:
    """Convenience function to embed a document."""
    return get_client().embed_document(document)


def is_available() -> bool:
    """Check if Voyage API is available."""
    return get_client().is_available


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Voyage Client Test")
    print("=" * 40)

    client = VoyageClient()

    if not client.is_available:
        print("ERROR: VOYAGE_API_KEY not set")
        print("Set: export VOYAGE_API_KEY=your-key-here")
        sys.exit(1)

    print(f"API Key: {client.api_key[:8]}...{client.api_key[-4:]}")
    print(f"Model: {client.model}")

    # Test single embedding
    print("\nTesting single embedding...")
    embedding = client.embed_single("Hello, world!")
    print(f"Dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

    # Test query embedding
    print("\nTesting query embedding...")
    query_embedding = client.embed_query("What is machine learning?")
    print(f"Dimension: {len(query_embedding)}")

    # Test batch embedding
    print("\nTesting batch embedding...")
    texts = [
        "First document about AI",
        "Second document about coding",
        "Third document about Python"
    ]
    embeddings = client.embed(texts)
    print(f"Embedded {len(embeddings)} texts")

    # Test caching
    print("\nTesting cache...")
    _ = client.embed_single("Hello, world!")  # Should be cached
    print(f"Cache size: {client.cache_size}")

    print(f"\nUsage: {client.usage}")
    print("\nAll tests passed!")
