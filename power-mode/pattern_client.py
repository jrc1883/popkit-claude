#!/usr/bin/env python3
"""
Pattern Client for Collective Learning

Part of Issue #71 (Collective Learning System)

Client for interacting with PopKit Cloud's pattern database.
Provides pattern submission, search, and feedback functionality.
"""

import json
import os
import re
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_CLOUD_URL = "https://popkit-cloud-api.joseph-cannon.workers.dev/v1"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PatternContext:
    """Context for a pattern."""
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    error_types: List[str] = field(default_factory=list)


@dataclass
class PatternResult:
    """Result from pattern search."""
    id: str
    trigger: str
    solution: str
    similarity: float
    quality_score: float
    context: PatternContext

    @classmethod
    def from_dict(cls, data: Dict) -> 'PatternResult':
        """Create from dictionary."""
        ctx = data.get("context", {})
        return cls(
            id=data["id"],
            trigger=data["trigger"],
            solution=data["solution"],
            similarity=data.get("similarity", 0),
            quality_score=data.get("quality_score", 0.5),
            context=PatternContext(
                languages=ctx.get("languages", []),
                frameworks=ctx.get("frameworks", []),
                error_types=ctx.get("error_types", [])
            )
        )


# =============================================================================
# ANONYMIZATION
# =============================================================================

# Patterns to remove from content
ANONYMIZE_PATTERNS = [
    # Absolute paths
    (r'/Users/[^/\s]+/', 'user_dir/'),
    (r'/home/[^/\s]+/', 'user_dir/'),
    (r'C:\\\\Users\\\\[^\\\\]+\\\\', 'user_dir/'),
    # API keys and secrets
    (r'(api[_-]?key|secret|token|password|auth)["\']?\s*[:=]\s*["\'][^"\']+["\']', '[CREDENTIAL]'),
    (r'Bearer\s+[A-Za-z0-9_-]+', 'Bearer [REDACTED]'),
    (r'pk_[a-z]+_[a-zA-Z0-9]+', '[API_KEY]'),
    (r'sk_[a-z]+_[a-zA-Z0-9]+', '[SECRET_KEY]'),
    # Email addresses
    (r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL]'),
    # IP addresses
    (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]'),
    # UUIDs
    (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[UUID]'),
]


def anonymize_content(content: str) -> str:
    """
    Anonymize content by removing sensitive information.

    Removes:
    - Absolute file paths
    - API keys and secrets
    - Email addresses
    - IP addresses
    - UUIDs
    """
    result = content

    for pattern, replacement in ANONYMIZE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def extract_abstract_error(error_message: str) -> str:
    """
    Extract abstract error pattern from specific error message.

    Example:
    "TypeError: Cannot read property 'token' of undefined at oauth.ts:45"
    -> "TypeError: Cannot read property of undefined"
    """
    # Remove line numbers
    result = re.sub(r':\d+:\d+', '', error_message)
    result = re.sub(r'at line \d+', '', result)

    # Remove specific property names in common patterns
    result = re.sub(r"property '([^']+)'", "property '[PROP]'", result)
    result = re.sub(r'property "([^"]+)"', 'property "[PROP]"', result)

    # Remove function names in stack traces
    result = re.sub(r'at ([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', 'at [FUNCTION](', result)

    # Remove file paths
    result = re.sub(r'\s+at\s+[^\s]+\.(ts|js|tsx|jsx):\d+', '', result)

    return result.strip()


# =============================================================================
# PATTERN CLIENT
# =============================================================================

class PatternClient:
    """
    Client for PopKit Cloud's collective learning patterns.

    Features:
    - Submit anonymized patterns
    - Search for matching patterns
    - Provide feedback on pattern effectiveness
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("POPKIT_API_KEY")
        self.base_url = (base_url or os.environ.get("POPKIT_CLOUD_URL", DEFAULT_CLOUD_URL)).rstrip('/')

        if not self.api_key:
            raise ValueError("POPKIT_API_KEY required for pattern client")

    def submit_pattern(
        self,
        trigger: str,
        solution: str,
        context: Optional[PatternContext] = None,
        anonymize: bool = True
    ) -> Dict[str, Any]:
        """
        Submit a pattern to the collective database.

        Args:
            trigger: What triggers this pattern (error description)
            solution: Solution approach
            context: Language/framework context
            anonymize: Whether to anonymize before submitting

        Returns:
            Result with status, pattern_id, or duplicate info
        """
        # Anonymize if requested
        if anonymize:
            trigger = anonymize_content(trigger)
            trigger = extract_abstract_error(trigger)
            solution = anonymize_content(solution)

        body = {
            "trigger": trigger,
            "solution": solution,
        }

        if context:
            body["context"] = {
                "languages": context.languages,
                "frameworks": context.frameworks,
                "error_types": context.error_types,
            }

        return self._request("POST", "/patterns/submit", body)

    def search_patterns(
        self,
        query: str,
        context: Optional[PatternContext] = None,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[PatternResult]:
        """
        Search for patterns matching a query.

        Args:
            query: Error or issue to search for
            context: Language/framework context for filtering
            limit: Max results to return
            threshold: Minimum similarity threshold

        Returns:
            List of matching patterns
        """
        body: Dict[str, Any] = {
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }

        if context:
            body["context"] = {
                "languages": context.languages,
                "frameworks": context.frameworks,
            }

        result = self._request("POST", "/patterns/search", body)
        return [PatternResult.from_dict(r) for r in result.get("results", [])]

    def provide_feedback(
        self,
        pattern_id: str,
        feedback_type: str
    ) -> Dict[str, Any]:
        """
        Provide feedback on a pattern.

        Args:
            pattern_id: ID of the pattern
            feedback_type: One of 'upvote', 'downvote', 'applied', 'success'

        Returns:
            Updated quality score
        """
        return self._request(
            "POST",
            f"/patterns/{pattern_id}/feedback",
            {"type": feedback_type}
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get collective learning statistics."""
        return self._request("GET", "/patterns/stats")

    def get_top_patterns(self, limit: int = 10) -> List[PatternResult]:
        """Get top patterns by quality score."""
        result = self._request("GET", f"/patterns/top?limit={limit}")
        return [PatternResult.from_dict(r) for r in result.get("patterns", [])]

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to cloud API."""
        url = f"{self.base_url}{path}"
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
# CLI
# =============================================================================

def main():
    """CLI for testing pattern client."""
    print("=" * 50)
    print("Pattern Client Test")
    print("=" * 50)

    try:
        client = PatternClient()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("Set POPKIT_API_KEY environment variable")
        return

    # Get stats
    print("\n[TEST] Getting stats...")
    stats = client.get_stats()
    print(f"  Total patterns: {stats.get('total_patterns', 0)}")
    print(f"  Success rate: {stats.get('success_rate', 'N/A')}")

    # Submit a test pattern
    print("\n[TEST] Submitting pattern...")
    result = client.submit_pattern(
        trigger="TypeError: Cannot read property 'data' of undefined in api.ts:123",
        solution="The API response may be null or undefined. Add null check before accessing .data property.",
        context=PatternContext(
            languages=["typescript"],
            frameworks=["express"],
            error_types=["TypeError"]
        )
    )
    print(f"  Status: {result.get('status')}")
    if result.get("status") == "created":
        print(f"  Pattern ID: {result.get('pattern_id')}")
    elif result.get("status") == "duplicate":
        print(f"  Duplicate of: {result.get('existing_id')}")

    # Search patterns
    print("\n[TEST] Searching patterns...")
    patterns = client.search_patterns(
        query="TypeError undefined property access",
        context=PatternContext(languages=["typescript"]),
        limit=3
    )
    print(f"  Found: {len(patterns)} patterns")
    for p in patterns:
        print(f"    - [{p.similarity:.3f}] {p.trigger[:50]}...")

    # Get top patterns
    print("\n[TEST] Getting top patterns...")
    top = client.get_top_patterns(limit=3)
    print(f"  Top patterns: {len(top)}")
    for p in top:
        print(f"    - [Q:{p.quality_score:.2f}] {p.trigger[:50]}...")

    print("\n" + "=" * 50)
    print("[OK] Pattern client test completed!")


if __name__ == "__main__":
    main()
