#!/usr/bin/env python3
"""
Cross-Project Pattern Sharing Client

Client for PopKit Cloud pattern sharing API.
Enables sharing learned patterns, corrections, and solutions across projects.

Part of Issue #95 (Cross-Project Pattern Sharing).
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import urllib.request
import urllib.error

from pattern_anonymizer import anonymize_pattern, validate_anonymization


# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_API_URL = os.environ.get(
    "POPKIT_API_URL",
    "https://popkit-cloud-api.joseph-cannon.workers.dev"
)
PATTERNS_ENDPOINT = "/api/v1/patterns"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PatternType:
    """Types of patterns that can be shared."""
    COMMAND: str = "command"          # Command corrections
    ERROR: str = "error"              # Error solutions
    WORKFLOW: str = "workflow"        # Workflow patterns
    CONFIGURATION: str = "config"     # Configuration patterns
    BEST_PRACTICE: str = "practice"   # Best practices


@dataclass
class ShareLevel:
    """Sharing levels for patterns."""
    PRIVATE: str = "private"          # Local only (free tier)
    TEAM: str = "team"                # Team members only (team tier)
    COMMUNITY: str = "community"      # Public pattern database (pro/team)


@dataclass
class Pattern:
    """Pattern structure for sharing."""
    id: str
    type: str  # PatternType value
    content: str
    solution: str
    share_level: str = ShareLevel.PRIVATE
    platform: Optional[str] = None    # windows, linux, darwin
    language: Optional[str] = None    # typescript, python, rust, etc.
    framework: Optional[str] = None   # react, nextjs, django, etc.
    tags: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    votes: int = 0
    created_at: Optional[str] = None
    _anonymized: bool = False


@dataclass
class PatternSearchResult:
    """Result from pattern search."""
    patterns: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int


@dataclass
class PatternSubmitResult:
    """Result from pattern submission."""
    status: str
    pattern_id: str
    quality_score: Optional[float] = None
    message: Optional[str] = None


# =============================================================================
# PATTERN CLIENT
# =============================================================================

class PatternClient:
    """
    Client for PopKit Cloud pattern sharing.

    Features:
    - Submit patterns for community sharing
    - Search community patterns
    - Vote on pattern quality
    - Track pattern usage
    - Privacy-first with full anonymization
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = POPKIT_API_URL,
        default_share_level: str = ShareLevel.PRIVATE
    ):
        """
        Initialize pattern client.

        Args:
            api_key: PopKit API key (or from POPKIT_API_KEY env)
            api_url: API base URL
            default_share_level: Default sharing level for new patterns
        """
        self.api_key = api_key or os.environ.get("POPKIT_API_KEY")
        self.api_url = api_url.rstrip("/")
        self.default_share_level = default_share_level
        self._cache: Dict[str, Any] = {}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data (for POST/PUT)
            timeout: Request timeout

        Returns:
            Response JSON

        Raises:
            Exception: On request failure
        """
        url = f"{self.api_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "popkit-pattern-client/1.0",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = json.dumps(data).encode() if data else None

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"API error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def submit_pattern(
        self,
        pattern_type: str,
        content: str,
        solution: str,
        project_root: Optional[str] = None,
        share_level: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PatternSubmitResult:
        """
        Submit a pattern for sharing.

        Args:
            pattern_type: Type of pattern (command, error, workflow)
            content: Original content/problem
            solution: Solution or correction
            project_root: Project root for anonymization
            share_level: Sharing level (defaults to client default)
            metadata: Additional metadata (platform, language, etc.)

        Returns:
            PatternSubmitResult with status and ID

        Raises:
            ValueError: If anonymization validation fails
            Exception: On API error
        """
        import uuid

        # Create pattern
        pattern = {
            'id': str(uuid.uuid4()),
            'type': pattern_type,
            'content': content,
            'solution': solution,
            'share_level': share_level or self.default_share_level,
            'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        }

        # Add metadata
        if metadata:
            pattern.update(metadata)

        # Anonymize if sharing publicly
        if pattern['share_level'] in [ShareLevel.TEAM, ShareLevel.COMMUNITY]:
            pattern = anonymize_pattern(pattern, project_root)

            # Validate anonymization
            issues = validate_anonymization(pattern)
            if issues['errors']:
                raise ValueError(f"Anonymization failed: {', '.join(issues['errors'])}")

        # Submit to API
        response = self._make_request(
            "POST",
            f"{PATTERNS_ENDPOINT}/submit",
            data=pattern
        )

        return PatternSubmitResult(
            status=response.get('status', 'unknown'),
            pattern_id=response.get('pattern_id', pattern['id']),
            quality_score=response.get('quality_score'),
            message=response.get('message')
        )

    def search_patterns(
        self,
        query: str,
        pattern_type: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        min_score: float = 0.0,
        page: int = 1,
        per_page: int = 20
    ) -> PatternSearchResult:
        """
        Search community patterns.

        Args:
            query: Search query
            pattern_type: Filter by type
            platform: Filter by platform (windows, linux, darwin)
            language: Filter by language
            framework: Filter by framework
            min_score: Minimum quality score
            page: Page number
            per_page: Results per page

        Returns:
            PatternSearchResult with matching patterns
        """
        params = {
            'q': query,
            'page': page,
            'per_page': per_page,
            'min_score': min_score,
        }

        if pattern_type:
            params['type'] = pattern_type
        if platform:
            params['platform'] = platform
        if language:
            params['language'] = language
        if framework:
            params['framework'] = framework

        # Build query string
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())

        response = self._make_request(
            "GET",
            f"{PATTERNS_ENDPOINT}/search?{query_string}"
        )

        return PatternSearchResult(
            patterns=response.get('patterns', []),
            total=response.get('total', 0),
            page=response.get('page', page),
            per_page=response.get('per_page', per_page)
        )

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern by ID.

        Args:
            pattern_id: Pattern UUID

        Returns:
            Pattern dict or None if not found
        """
        try:
            response = self._make_request(
                "GET",
                f"{PATTERNS_ENDPOINT}/{pattern_id}"
            )
            return response.get('pattern')
        except Exception:
            return None

    def vote_pattern(self, pattern_id: str, vote: int) -> bool:
        """
        Vote on a pattern's quality.

        Args:
            pattern_id: Pattern UUID
            vote: Vote value (+1 or -1)

        Returns:
            True if vote was recorded
        """
        try:
            self._make_request(
                "POST",
                f"{PATTERNS_ENDPOINT}/{pattern_id}/vote",
                data={'vote': max(-1, min(1, vote))}
            )
            return True
        except Exception:
            return False

    def get_similar_patterns(
        self,
        content: str,
        pattern_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find patterns similar to the given content.

        Uses semantic similarity to find relevant patterns.

        Args:
            content: Content to match
            pattern_type: Filter by type
            limit: Maximum results

        Returns:
            List of similar patterns
        """
        params = {
            'content': content,
            'limit': limit,
        }

        if pattern_type:
            params['type'] = pattern_type

        try:
            response = self._make_request(
                "POST",
                f"{PATTERNS_ENDPOINT}/similar",
                data=params
            )
            return response.get('patterns', [])
        except Exception:
            return []

    def report_pattern_usage(
        self,
        pattern_id: str,
        success: bool,
        context: Optional[str] = None
    ) -> bool:
        """
        Report that a pattern was used.

        Helps improve pattern quality scores.

        Args:
            pattern_id: Pattern UUID
            success: Whether the pattern was helpful
            context: Optional anonymized context

        Returns:
            True if report was recorded
        """
        try:
            self._make_request(
                "POST",
                f"{PATTERNS_ENDPOINT}/{pattern_id}/usage",
                data={
                    'success': success,
                    'context': context
                }
            )
            return True
        except Exception:
            return False

    def get_trending_patterns(
        self,
        pattern_type: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending/popular patterns.

        Args:
            pattern_type: Filter by type
            platform: Filter by platform
            limit: Maximum results

        Returns:
            List of trending patterns
        """
        params = {'limit': limit}
        if pattern_type:
            params['type'] = pattern_type
        if platform:
            params['platform'] = platform

        query_string = '&'.join(f"{k}={v}" for k, v in params.items())

        try:
            response = self._make_request(
                "GET",
                f"{PATTERNS_ENDPOINT}/trending?{query_string}"
            )
            return response.get('patterns', [])
        except Exception:
            return []


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_pattern_client() -> PatternClient:
    """Get a configured pattern client instance.

    Returns:
        PatternClient instance
    """
    return PatternClient()


def share_command_correction(
    original: str,
    corrected: str,
    platform: Optional[str] = None,
    project_root: Optional[str] = None
) -> Optional[str]:
    """
    Share a command correction pattern.

    Convenience function for sharing command-type patterns.

    Args:
        original: Original (incorrect) command
        corrected: Corrected command
        platform: Platform (windows, linux, darwin)
        project_root: Project root for anonymization

    Returns:
        Pattern ID if successful, None otherwise
    """
    import platform as plat

    client = get_pattern_client()

    try:
        result = client.submit_pattern(
            pattern_type=PatternType.COMMAND,
            content=f"User tried: {original}",
            solution=f"Use: {corrected}",
            project_root=project_root,
            share_level=ShareLevel.COMMUNITY,
            metadata={
                'platform': platform or plat.system().lower()
            }
        )
        return result.pattern_id
    except Exception:
        return None


def find_error_solution(
    error_message: str,
    language: Optional[str] = None,
    framework: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Find a solution for an error message.

    Convenience function for finding error-type patterns.

    Args:
        error_message: Error message to find solution for
        language: Programming language
        framework: Framework in use

    Returns:
        Best matching pattern or None
    """
    client = get_pattern_client()

    patterns = client.get_similar_patterns(
        content=error_message,
        pattern_type=PatternType.ERROR,
        limit=1
    )

    return patterns[0] if patterns else None


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: pattern_client.py <command> [args]")
        print("Commands: search, trending, submit")
        sys.exit(1)

    command = sys.argv[1]
    client = get_pattern_client()

    if command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        result = client.search_patterns(query)
        print(f"Found {result.total} patterns:")
        for p in result.patterns[:5]:
            print(f"  - [{p.get('type')}] {p.get('content')[:50]}...")

    elif command == "trending":
        patterns = client.get_trending_patterns()
        print("Trending patterns:")
        for p in patterns:
            print(f"  - [{p.get('type')}] {p.get('content')[:50]}... (score: {p.get('quality_score', 0):.1f})")

    elif command == "submit":
        if len(sys.argv) < 5:
            print("Usage: pattern_client.py submit <type> <content> <solution>")
            sys.exit(1)

        pattern_type = sys.argv[2]
        content = sys.argv[3]
        solution = sys.argv[4]

        result = client.submit_pattern(pattern_type, content, solution)
        print(f"Submitted pattern: {result.pattern_id}")
        print(f"Status: {result.status}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
