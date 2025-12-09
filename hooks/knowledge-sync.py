#!/usr/bin/env python3
"""
Knowledge Sync Hook
Syncs external knowledge sources (documentation, blogs) on session start.

Features:
- Configurable knowledge sources via sources.json
- TTL-based caching with SQLite metadata
- Priority-based fetching within time budget
- HTML to markdown conversion
"""

import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Optional imports with graceful fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

# Constants
KNOWLEDGE_DIR = Path.home() / ".claude" / "config" / "knowledge"
SOURCES_FILE = KNOWLEDGE_DIR / "sources.json"
CACHE_DB = KNOWLEDGE_DIR / "cache.db"
CONTENT_DIR = KNOWLEDGE_DIR / "content"

DEFAULT_TTL_SECONDS = 86400  # 24 hours
FETCH_TIMEOUT_SECONDS = 30
MAX_CONTENT_SIZE = 50000  # chars
TIME_BUDGET_SECONDS = 8  # Stay within 10s hook timeout


# Default sources configuration
DEFAULT_SOURCES = {
    "version": "1.0.0",
    "settings": {
        "defaultTTL": 86400,
        "maxContentSize": 50000,
        "fetchTimeout": 30000
    },
    "sources": [
        {
            "id": "anthropic-engineering",
            "name": "Claude Code Engineering Blog",
            "url": "https://www.anthropic.com/engineering",
            "enabled": True,
            "ttl": 86400,
            "tags": ["claude", "best-practices"],
            "priority": "high"
        },
        {
            "id": "claude-code-docs-overview",
            "name": "Claude Code Documentation - Overview",
            "url": "https://docs.anthropic.com/en/docs/claude-code/overview",
            "enabled": True,
            "ttl": 86400,
            "tags": ["claude-code", "documentation"],
            "priority": "high"
        },
        {
            "id": "claude-code-docs-hooks",
            "name": "Claude Code Documentation - Hooks",
            "url": "https://docs.anthropic.com/en/docs/claude-code/hooks",
            "enabled": True,
            "ttl": 86400,
            "tags": ["claude-code", "hooks"],
            "priority": "high"
        }
    ]
}


class KnowledgeSync:
    """Manages knowledge source syncing and caching."""

    def __init__(self):
        self.start_time = datetime.now()
        self._ensure_directories()
        self._init_database()

    def _ensure_directories(self):
        """Create required directories."""
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Initialize SQLite cache database."""
        conn = sqlite3.connect(str(CACHE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_cache (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content_size INTEGER,
                status TEXT DEFAULT 'fresh',
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fetch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                url TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL,
                duration_ms INTEGER,
                content_size INTEGER,
                error_message TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source_id ON knowledge_cache(source_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expires_at ON knowledge_cache(expires_at)
        ''')

        conn.commit()
        conn.close()

    def load_config(self) -> Dict[str, Any]:
        """Load sources configuration, create defaults if missing."""
        if not SOURCES_FILE.exists():
            self.save_config(DEFAULT_SOURCES)
            return DEFAULT_SOURCES

        try:
            with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return DEFAULT_SOURCES

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save sources configuration."""
        try:
            with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError:
            return False

    def is_cache_fresh(self, source_id: str) -> bool:
        """Check if cached content is still valid."""
        conn = sqlite3.connect(str(CACHE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT expires_at FROM knowledge_cache
            WHERE source_id = ? AND status = 'fresh'
        ''', (source_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return False

        try:
            expires_at = datetime.fromisoformat(result[0])
            return datetime.now() < expires_at
        except ValueError:
            return False

    def time_remaining(self) -> float:
        """Get remaining time budget in seconds."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return max(0, TIME_BUDGET_SECONDS - elapsed)

    def fetch_url(self, url: str, timeout: int = FETCH_TIMEOUT_SECONDS) -> Optional[str]:
        """Fetch URL and convert HTML to markdown."""
        if not HAS_REQUESTS:
            return None

        try:
            response = requests.get(
                url,
                timeout=min(timeout, self.time_remaining()),
                headers={
                    'User-Agent': 'popkit-knowledge-sync/1.0',
                    'Accept': 'text/html,application/xhtml+xml'
                }
            )

            if response.status_code != 200:
                return None

            html_content = response.text

            # Convert HTML to markdown if possible
            if HAS_HTML2TEXT:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0  # No wrapping
                content = h.handle(html_content)
            else:
                # Basic HTML stripping fallback
                import re
                content = re.sub(r'<[^>]+>', '', html_content)
                content = re.sub(r'\s+', ' ', content)

            # Truncate if too large
            if len(content) > MAX_CONTENT_SIZE:
                content = content[:MAX_CONTENT_SIZE] + "\n\n[Content truncated...]"

            return content

        except Exception:
            return None

    def cache_content(self, source: Dict[str, Any], content: str) -> bool:
        """Store content in file and metadata in database."""
        source_id = source.get('id', 'unknown')
        url = source.get('url', '')
        ttl = source.get('ttl', DEFAULT_TTL_SECONDS)

        # Save content to file
        content_file = CONTENT_DIR / f"{source_id}.md"
        try:
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(f"# {source.get('name', source_id)}\n\n")
                f.write(f"Source: {url}\n")
                f.write(f"Fetched: {datetime.now().isoformat()}\n\n")
                f.write("---\n\n")
                f.write(content)
        except IOError:
            return False

        # Save metadata to database
        now = datetime.now()
        expires = now + timedelta(seconds=ttl)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        conn = sqlite3.connect(str(CACHE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_cache
            (id, source_id, url, fetched_at, expires_at, content_hash, content_size, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            source_id,
            source_id,
            url,
            now.isoformat(),
            expires.isoformat(),
            content_hash,
            len(content),
            'fresh',
            now.isoformat()
        ))

        conn.commit()
        conn.close()

        return True

    def log_fetch(self, source_id: str, url: str, success: bool,
                  duration_ms: int, content_size: int = 0, error: str = None):
        """Log fetch attempt to history table."""
        conn = sqlite3.connect(str(CACHE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO fetch_history
            (source_id, url, timestamp, success, duration_ms, content_size, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            source_id,
            url,
            datetime.now().isoformat(),
            1 if success else 0,
            duration_ms,
            content_size,
            error
        ))

        conn.commit()
        conn.close()

    def sync_sources(self) -> Dict[str, Any]:
        """Sync all enabled sources within time budget."""
        config = self.load_config()
        sources = config.get('sources', [])

        # Sort by priority (high first)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        sources = sorted(sources,
                        key=lambda s: priority_order.get(s.get('priority', 'medium'), 1))

        results = {
            'synced': [],
            'fresh': [],
            'skipped': [],
            'errors': []
        }

        for source in sources:
            # Check time budget
            if self.time_remaining() < 2:
                results['skipped'].append(source.get('id', 'unknown'))
                continue

            source_id = source.get('id', 'unknown')

            # Skip disabled sources
            if not source.get('enabled', True):
                results['skipped'].append(source_id)
                continue

            # Check cache freshness
            if self.is_cache_fresh(source_id):
                results['fresh'].append(source_id)
                continue

            # Fetch and cache
            url = source.get('url', '')
            start = datetime.now()

            content = self.fetch_url(url)
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            if content:
                if self.cache_content(source, content):
                    results['synced'].append(source_id)
                    self.log_fetch(source_id, url, True, duration_ms, len(content))
                else:
                    results['errors'].append(source_id)
                    self.log_fetch(source_id, url, False, duration_ms, error="Cache write failed")
            else:
                results['errors'].append(source_id)
                self.log_fetch(source_id, url, False, duration_ms, error="Fetch failed")

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get current cache status."""
        config = self.load_config()
        sources = config.get('sources', [])

        conn = sqlite3.connect(str(CACHE_DB))
        cursor = conn.cursor()

        status = {
            'total_sources': len(sources),
            'enabled_sources': sum(1 for s in sources if s.get('enabled', True)),
            'cached': 0,
            'fresh': 0,
            'stale': 0,
            'sources': []
        }

        for source in sources:
            source_id = source.get('id', 'unknown')

            cursor.execute('''
                SELECT fetched_at, expires_at, content_size, status
                FROM knowledge_cache WHERE source_id = ?
            ''', (source_id,))

            result = cursor.fetchone()

            if result:
                status['cached'] += 1
                try:
                    expires = datetime.fromisoformat(result[1])
                    is_fresh = datetime.now() < expires
                except ValueError:
                    is_fresh = False

                if is_fresh:
                    status['fresh'] += 1
                else:
                    status['stale'] += 1

                status['sources'].append({
                    'id': source_id,
                    'name': source.get('name', source_id),
                    'status': 'fresh' if is_fresh else 'stale',
                    'fetched_at': result[0],
                    'size': result[2]
                })
            else:
                status['sources'].append({
                    'id': source_id,
                    'name': source.get('name', source_id),
                    'status': 'not_cached'
                })

        conn.close()
        return status


def main():
    """Main entry point for the hook - JSON stdin/stdout protocol."""
    try:
        # Read input data from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Initialize and sync knowledge
        syncer = KnowledgeSync()
        results = syncer.sync_sources()

        # Log status to stderr
        synced_count = len(results.get('synced', []))
        fresh_count = len(results.get('fresh', []))
        if synced_count > 0:
            print(f"Knowledge sync: {synced_count} updated, {fresh_count} cached", file=sys.stderr)

        # Output JSON response
        response = {
            "status": "success",
            "knowledge_sync": results,
            "timestamp": datetime.now().isoformat(),
            "cache_location": str(KNOWLEDGE_DIR)
        }
        print(json.dumps(response))

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON input: {e}"}
        print(json.dumps(response))
        sys.exit(0)
    except Exception as e:
        response = {"status": "error", "error": str(e)}
        print(json.dumps(response))
        print(f"Error in knowledge-sync hook: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
