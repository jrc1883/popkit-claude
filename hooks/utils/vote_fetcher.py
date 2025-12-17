#!/usr/bin/env python3
"""
Vote Fetcher - GitHub Reaction-Based Voting System

Part of Issue #92 (Vote-Based Feature Prioritization)
Parent: Epic #88 (Self-Improvement & Learning System)

Fetches and caches GitHub issue reactions to calculate community
priority scores. Inspired by Long Horizon Coding Agent Demo.
"""

import json
import subprocess
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
from collections import Counter


@dataclass
class VoteResult:
    """Result of fetching votes for an issue"""
    issue_number: int
    score: int
    breakdown: Dict[str, int]
    total_reactions: int
    fetched_at: str
    cached: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# Default reaction weights
DEFAULT_WEIGHTS = {
    '+1': 1,        # 👍 - Community interest
    'heart': 2,     # ❤️ - Strong support
    'rocket': 3,    # 🚀 - Approved/prioritized
    '-1': -1,       # 👎 - Deprioritize
    'hooray': 1,    # 🎉 - Celebration (counts as +1)
    'confused': -1, # 😕 - Issues/concerns
    'eyes': 0,      # 👀 - Watching (neutral)
    'laugh': 0,     # 😄 - Humor (neutral)
}


class VoteCache:
    """SQLite-based cache for vote data to avoid API rate limits"""

    CACHE_TTL_HOURS = 1  # How long to cache votes
    DEFAULT_DB_PATH = Path.home() / '.claude' / 'config' / 'vote_cache.db'

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS vote_cache (
                    repo TEXT,
                    issue_number INTEGER,
                    score INTEGER,
                    breakdown TEXT,
                    total_reactions INTEGER,
                    fetched_at TIMESTAMP,
                    PRIMARY KEY (repo, issue_number)
                );

                CREATE INDEX IF NOT EXISTS idx_vote_cache_fetched
                ON vote_cache(fetched_at);
            """)

    def get(self, repo: str, issue_number: int) -> Optional[VoteResult]:
        """Get cached vote result if not expired"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM vote_cache
                WHERE repo = ? AND issue_number = ?
                AND fetched_at > datetime('now', '-' || ? || ' hours')
            """, (repo, issue_number, self.CACHE_TTL_HOURS)).fetchone()

            if row:
                return VoteResult(
                    issue_number=row['issue_number'],
                    score=row['score'],
                    breakdown=json.loads(row['breakdown']),
                    total_reactions=row['total_reactions'],
                    fetched_at=row['fetched_at'],
                    cached=True
                )
            return None

    def set(self, repo: str, result: VoteResult) -> None:
        """Cache a vote result"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO vote_cache
                (repo, issue_number, score, breakdown, total_reactions, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (repo, result.issue_number, result.score,
                  json.dumps(result.breakdown), result.total_reactions,
                  result.fetched_at))

    def clear_expired(self) -> int:
        """Clear expired cache entries"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM vote_cache
                WHERE fetched_at < datetime('now', '-' || ? || ' hours')
            """, (self.CACHE_TTL_HOURS * 2,))
            return cursor.rowcount

    def clear_all(self) -> int:
        """Clear all cache entries"""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM vote_cache")
            return cursor.rowcount


class VoteFetcher:
    """
    Fetches GitHub issue reactions and calculates vote scores.

    Uses gh CLI for API calls and SQLite for caching.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, int]] = None,
        cache: Optional[VoteCache] = None
    ):
        """
        Initialize the vote fetcher.

        Args:
            weights: Custom reaction weights (defaults to DEFAULT_WEIGHTS)
            cache: Vote cache instance (creates new one if not provided)
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.cache = cache or VoteCache()

    def get_repo(self) -> Optional[str]:
        """Get the current repository in owner/repo format"""
        try:
            result = subprocess.run(
                ['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def fetch_reactions(self, issue_number: int, repo: Optional[str] = None) -> List[Dict]:
        """
        Fetch reactions for a specific issue using gh API.

        Args:
            issue_number: GitHub issue number
            repo: Repository in owner/repo format (auto-detected if not provided)

        Returns:
            List of reaction objects from GitHub API
        """
        repo = repo or self.get_repo()
        if not repo:
            raise ValueError("Could not determine repository. Please specify repo parameter.")

        try:
            result = subprocess.run(
                ['gh', 'api', f'/repos/{repo}/issues/{issue_number}/reactions',
                 '--header', 'Accept: application/vnd.github+json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Handle case where issue has no reactions (404 or empty)
                if 'Not Found' in result.stderr or result.returncode == 1:
                    return []
                raise RuntimeError(f"GitHub API error: {result.stderr}")

            return json.loads(result.stdout) if result.stdout.strip() else []

        except subprocess.TimeoutExpired:
            raise RuntimeError("GitHub API request timed out")
        except json.JSONDecodeError:
            return []

    def calculate_score(self, reactions: List[Dict]) -> tuple:
        """
        Calculate vote score from reactions.

        Args:
            reactions: List of reaction objects from GitHub API

        Returns:
            Tuple of (score, breakdown_dict, total_count)
        """
        breakdown = Counter()

        for reaction in reactions:
            content = reaction.get('content', '')
            breakdown[content] += 1

        score = sum(
            self.weights.get(content, 0) * count
            for content, count in breakdown.items()
        )

        return score, dict(breakdown), len(reactions)

    def get_issue_votes(
        self,
        issue_number: int,
        repo: Optional[str] = None,
        use_cache: bool = True
    ) -> VoteResult:
        """
        Get vote score for a specific issue.

        Args:
            issue_number: GitHub issue number
            repo: Repository in owner/repo format
            use_cache: Whether to use cached results

        Returns:
            VoteResult with score and breakdown
        """
        repo = repo or self.get_repo()
        if not repo:
            raise ValueError("Could not determine repository")

        # Check cache first
        if use_cache:
            cached = self.cache.get(repo, issue_number)
            if cached:
                return cached

        # Fetch fresh data
        reactions = self.fetch_reactions(issue_number, repo)
        score, breakdown, total = self.calculate_score(reactions)

        result = VoteResult(
            issue_number=issue_number,
            score=score,
            breakdown=breakdown,
            total_reactions=total,
            fetched_at=datetime.now().isoformat(),
            cached=False
        )

        # Cache the result
        self.cache.set(repo, result)

        return result

    def get_bulk_votes(
        self,
        issue_numbers: List[int],
        repo: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[int, VoteResult]:
        """
        Get votes for multiple issues.

        Args:
            issue_numbers: List of issue numbers
            repo: Repository in owner/repo format
            use_cache: Whether to use cached results

        Returns:
            Dict mapping issue number to VoteResult
        """
        results = {}
        for num in issue_numbers:
            try:
                results[num] = self.get_issue_votes(num, repo, use_cache)
            except Exception as e:
                # Log error but continue with other issues
                results[num] = VoteResult(
                    issue_number=num,
                    score=0,
                    breakdown={},
                    total_reactions=0,
                    fetched_at=datetime.now().isoformat(),
                    cached=False
                )
        return results

    def format_vote_display(self, result: VoteResult, compact: bool = False) -> str:
        """
        Format vote result for display.

        Args:
            result: VoteResult to format
            compact: If True, use compact format

        Returns:
            Formatted string
        """
        breakdown = result.breakdown

        if compact:
            parts = []
            if breakdown.get('+1', 0):
                parts.append(f"👍{breakdown['+1']}")
            if breakdown.get('heart', 0):
                parts.append(f"❤️{breakdown['heart']}")
            if breakdown.get('rocket', 0):
                parts.append(f"🚀{breakdown['rocket']}")
            if breakdown.get('-1', 0):
                parts.append(f"👎{breakdown['-1']}")

            return f"{' '.join(parts)}  Score: {result.score}" if parts else "No votes"

        # Full format
        lines = [f"Vote Score: {result.score}"]
        if breakdown:
            lines.append("Breakdown:")
            emoji_map = {'+1': '👍', 'heart': '❤️', 'rocket': '🚀', '-1': '👎',
                        'hooray': '🎉', 'confused': '😕', 'eyes': '👀', 'laugh': '😄'}
            for content, count in sorted(breakdown.items(), key=lambda x: -self.weights.get(x[0], 0)):
                emoji = emoji_map.get(content, content)
                weight = self.weights.get(content, 0)
                contribution = weight * count
                lines.append(f"  {emoji} {content}: {count} (×{weight} = {contribution:+d})")
        else:
            lines.append("No reactions yet")

        if result.cached:
            lines.append(f"(cached at {result.fetched_at})")

        return '\n'.join(lines)


# Singleton instance
_fetcher: Optional[VoteFetcher] = None


def get_vote_fetcher() -> VoteFetcher:
    """Get the singleton VoteFetcher instance"""
    global _fetcher
    if _fetcher is None:
        _fetcher = VoteFetcher()
    return _fetcher


if __name__ == "__main__":
    # Test the vote fetcher
    fetcher = VoteFetcher()

    # Try to get repo
    repo = fetcher.get_repo()
    print(f"Current repo: {repo}")

    if repo:
        # Test fetching votes for an issue
        try:
            result = fetcher.get_issue_votes(88)  # Epic #88
            print(f"\nIssue #88 votes:")
            print(fetcher.format_vote_display(result))

            # Test compact format
            print(f"\nCompact: {fetcher.format_vote_display(result, compact=True)}")

        except Exception as e:
            print(f"Error fetching votes: {e}")
    else:
        print("Not in a git repository with gh configured")
