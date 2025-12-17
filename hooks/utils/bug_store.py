#!/usr/bin/env python3
"""
Bug Store - SQLite Storage for Captured Bugs

Part of Issue #90 (Automatic Bug Reporting System)

Provides persistent storage for captured bugs, consent preferences,
and sharing status tracking.
"""

import sqlite3
import json
import hashlib
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
from enum import Enum


class ShareStatus(Enum):
    """Status of bug sharing"""
    PENDING = "pending"      # Not yet asked
    SHARED = "shared"        # User approved sharing
    LOCAL_ONLY = "local_only"  # User declined sharing
    NEVER_ASK = "never_ask"  # User said never ask again


class ConsentLevel(Enum):
    """User consent levels for bug sharing"""
    STRICT = "strict"        # No sharing, local only
    MODERATE = "moderate"    # Share anonymized patterns
    MINIMAL = "minimal"      # Share more context (open source projects)


@dataclass
class CapturedBug:
    """Represents a captured bug"""
    id: str
    error_type: str
    error_message: Optional[str]
    error_message_hash: Optional[str]
    command_pattern: Optional[str]
    platform: str
    shell: Optional[str]
    context_summary: str
    anonymized_context: Optional[str]
    raw_context: Optional[str]  # JSON string of full context
    share_status: str
    detection_source: str  # "auto" or "manual"
    confidence: float
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ConsentPreference:
    """User consent preference"""
    key: str
    value: str
    updated_at: str


class BugStore:
    """SQLite-based storage for captured bugs and consent preferences"""

    DB_VERSION = 1
    DEFAULT_DB_PATH = Path.home() / '.claude' / 'config' / 'bug_reports.db'

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the bug store.

        Args:
            db_path: Path to SQLite database (defaults to ~/.claude/config/bug_reports.db)
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
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
        """Initialize the database schema"""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Captured bugs table
                CREATE TABLE IF NOT EXISTS captured_bugs (
                    id TEXT PRIMARY KEY,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    error_message_hash TEXT,
                    command_pattern TEXT,
                    platform TEXT NOT NULL,
                    shell TEXT,
                    context_summary TEXT NOT NULL,
                    anonymized_context TEXT,
                    raw_context TEXT,
                    share_status TEXT DEFAULT 'pending',
                    detection_source TEXT DEFAULT 'auto',
                    confidence REAL DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Index for efficient queries
                CREATE INDEX IF NOT EXISTS idx_bugs_created
                ON captured_bugs(created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_bugs_error_type
                ON captured_bugs(error_type);

                CREATE INDEX IF NOT EXISTS idx_bugs_share_status
                ON captured_bugs(share_status);

                -- Consent preferences table
                CREATE TABLE IF NOT EXISTS consent_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Bug sharing history
                CREATE TABLE IF NOT EXISTS sharing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bug_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bug_id) REFERENCES captured_bugs(id)
                );

                -- Schema version
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                INSERT OR IGNORE INTO schema_version (version) VALUES (1);

                -- Set default consent preferences
                INSERT OR IGNORE INTO consent_preferences (key, value)
                VALUES ('consent_level', 'strict');

                INSERT OR IGNORE INTO consent_preferences (key, value)
                VALUES ('sharing_enabled', 'false');

                INSERT OR IGNORE INTO consent_preferences (key, value)
                VALUES ('auto_detect_enabled', 'true');

                INSERT OR IGNORE INTO consent_preferences (key, value)
                VALUES ('ask_before_share', 'true');
            """)

    def _generate_id(self) -> str:
        """Generate a unique bug ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:6]
        return f"bug-{timestamp}-{unique}"

    def _hash_message(self, message: str) -> str:
        """Create a hash of an error message for deduplication"""
        normalized = ' '.join(message.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    # =========================================================================
    # BUG OPERATIONS
    # =========================================================================

    def capture_bug(
        self,
        error_type: str,
        context_summary: str,
        error_message: Optional[str] = None,
        command_pattern: Optional[str] = None,
        platform: Optional[str] = None,
        shell: Optional[str] = None,
        anonymized_context: Optional[str] = None,
        raw_context: Optional[Dict] = None,
        detection_source: str = "auto",
        confidence: float = 0.5
    ) -> CapturedBug:
        """
        Capture a new bug.

        Args:
            error_type: Type of error (e.g., "TypeError", "command_not_found")
            context_summary: Brief summary of what happened
            error_message: Full error message (will be hashed)
            command_pattern: Command pattern that triggered the error
            platform: OS platform
            shell: Shell type
            anonymized_context: Pre-anonymized context for sharing
            raw_context: Full context dictionary (stored as JSON)
            detection_source: "auto" or "manual"
            confidence: Detection confidence (0.0 to 1.0)

        Returns:
            The captured bug
        """
        import sys
        platform = platform or sys.platform
        bug_id = self._generate_id()
        error_hash = self._hash_message(error_message) if error_message else None
        raw_json = json.dumps(raw_context) if raw_context else None

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO captured_bugs
                (id, error_type, error_message, error_message_hash, command_pattern,
                 platform, shell, context_summary, anonymized_context, raw_context,
                 detection_source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bug_id, error_type, error_message, error_hash, command_pattern,
                  platform, shell, context_summary, anonymized_context, raw_json,
                  detection_source, confidence))

            # Log to history
            conn.execute("""
                INSERT INTO sharing_history (bug_id, action, result)
                VALUES (?, 'capture', 'created')
            """, (bug_id,))

        return self.get_bug(bug_id)

    def get_bug(self, bug_id: str) -> Optional[CapturedBug]:
        """Get a bug by ID"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM captured_bugs WHERE id = ?
            """, (bug_id,)).fetchone()

            if row:
                return self._row_to_bug(row)
            return None

    def _row_to_bug(self, row: sqlite3.Row) -> CapturedBug:
        """Convert a database row to a CapturedBug"""
        return CapturedBug(
            id=row['id'],
            error_type=row['error_type'],
            error_message=row['error_message'],
            error_message_hash=row['error_message_hash'],
            command_pattern=row['command_pattern'],
            platform=row['platform'],
            shell=row['shell'],
            context_summary=row['context_summary'],
            anonymized_context=row['anonymized_context'],
            raw_context=row['raw_context'],
            share_status=row['share_status'],
            detection_source=row['detection_source'],
            confidence=row['confidence'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def list_bugs(
        self,
        limit: int = 50,
        error_type: Optional[str] = None,
        share_status: Optional[str] = None,
        since: Optional[str] = None
    ) -> List[CapturedBug]:
        """
        List captured bugs with optional filters.

        Args:
            limit: Maximum number of bugs to return
            error_type: Filter by error type
            share_status: Filter by share status
            since: Only bugs after this date (ISO format)

        Returns:
            List of bugs
        """
        query = "SELECT * FROM captured_bugs"
        params = []
        conditions = []

        if error_type:
            conditions.append("error_type = ?")
            params.append(error_type)

        if share_status:
            conditions.append("share_status = ?")
            params.append(share_status)

        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_bug(row) for row in rows]

    def update_share_status(self, bug_id: str, status: ShareStatus) -> bool:
        """Update the share status of a bug"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE captured_bugs
                SET share_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status.value, bug_id))

            if cursor.rowcount > 0:
                conn.execute("""
                    INSERT INTO sharing_history (bug_id, action, result)
                    VALUES (?, 'status_change', ?)
                """, (bug_id, status.value))
                return True
            return False

    def delete_bug(self, bug_id: str) -> bool:
        """Delete a bug by ID"""
        with self._get_connection() as conn:
            # Delete history first
            conn.execute("DELETE FROM sharing_history WHERE bug_id = ?", (bug_id,))
            cursor = conn.execute("DELETE FROM captured_bugs WHERE id = ?", (bug_id,))
            return cursor.rowcount > 0

    def clear_old_bugs(self, days: int = 90) -> int:
        """Clear bugs older than N days"""
        with self._get_connection() as conn:
            # First get IDs to delete
            rows = conn.execute("""
                SELECT id FROM captured_bugs
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,)).fetchall()

            ids = [row['id'] for row in rows]
            if not ids:
                return 0

            placeholders = ','.join('?' * len(ids))
            conn.execute(f"DELETE FROM sharing_history WHERE bug_id IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM captured_bugs WHERE id IN ({placeholders})", ids)
            return len(ids)

    def find_similar(self, error_type: str, error_message: Optional[str] = None) -> List[CapturedBug]:
        """Find similar bugs by error type and message hash"""
        with self._get_connection() as conn:
            if error_message:
                error_hash = self._hash_message(error_message)
                rows = conn.execute("""
                    SELECT * FROM captured_bugs
                    WHERE error_type = ? OR error_message_hash = ?
                    ORDER BY created_at DESC LIMIT 10
                """, (error_type, error_hash)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM captured_bugs
                    WHERE error_type = ?
                    ORDER BY created_at DESC LIMIT 10
                """, (error_type,)).fetchall()

            return [self._row_to_bug(row) for row in rows]

    # =========================================================================
    # CONSENT OPERATIONS
    # =========================================================================

    def get_consent_level(self) -> ConsentLevel:
        """Get the current consent level"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT value FROM consent_preferences WHERE key = 'consent_level'
            """).fetchone()
            if row:
                try:
                    return ConsentLevel(row['value'])
                except ValueError:
                    return ConsentLevel.STRICT
            return ConsentLevel.STRICT

    def set_consent_level(self, level: ConsentLevel) -> None:
        """Set the consent level"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO consent_preferences (key, value, updated_at)
                VALUES ('consent_level', ?, CURRENT_TIMESTAMP)
            """, (level.value,))

    def get_preference(self, key: str, default: str = "") -> str:
        """Get a consent preference"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT value FROM consent_preferences WHERE key = ?
            """, (key,)).fetchone()
            return row['value'] if row else default

    def set_preference(self, key: str, value: str) -> None:
        """Set a consent preference"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO consent_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))

    def is_sharing_enabled(self) -> bool:
        """Check if sharing is enabled"""
        return self.get_preference('sharing_enabled', 'false') == 'true'

    def set_sharing_enabled(self, enabled: bool) -> None:
        """Enable or disable sharing"""
        self.set_preference('sharing_enabled', 'true' if enabled else 'false')

    def should_ask_before_share(self) -> bool:
        """Check if we should ask before sharing"""
        return self.get_preference('ask_before_share', 'true') == 'true'

    def set_ask_before_share(self, ask: bool) -> None:
        """Set whether to ask before sharing"""
        self.set_preference('ask_before_share', 'true' if ask else 'false')

    def is_auto_detect_enabled(self) -> bool:
        """Check if auto-detection is enabled"""
        return self.get_preference('auto_detect_enabled', 'true') == 'true'

    def set_auto_detect_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-detection"""
        self.set_preference('auto_detect_enabled', 'true' if enabled else 'false')

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about captured bugs"""
        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM captured_bugs"
            ).fetchone()[0]

            by_type = dict(conn.execute("""
                SELECT error_type, COUNT(*) FROM captured_bugs GROUP BY error_type
            """).fetchall())

            by_status = dict(conn.execute("""
                SELECT share_status, COUNT(*) FROM captured_bugs GROUP BY share_status
            """).fetchall())

            recent_count = conn.execute("""
                SELECT COUNT(*) FROM captured_bugs
                WHERE created_at > datetime('now', '-7 days')
            """).fetchone()[0]

            return {
                "total_bugs": total,
                "by_error_type": by_type,
                "by_share_status": by_status,
                "recent_7_days": recent_count,
                "consent_level": self.get_consent_level().value,
                "sharing_enabled": self.is_sharing_enabled()
            }

    # =========================================================================
    # EXPORT / GDPR COMPLIANCE
    # =========================================================================

    def export_all(self, filepath: Path) -> int:
        """Export all bug data for GDPR compliance"""
        bugs = self.list_bugs(limit=10000)
        data = {
            "version": self.DB_VERSION,
            "exported_at": datetime.now().isoformat(),
            "bugs": [bug.to_dict() for bug in bugs],
            "preferences": self._export_preferences()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        return len(bugs)

    def _export_preferences(self) -> Dict[str, str]:
        """Export all preferences"""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM consent_preferences").fetchall()
            return {row['key']: row['value'] for row in rows}

    def delete_all_data(self) -> Dict[str, int]:
        """Delete all user data (GDPR right to be forgotten)"""
        with self._get_connection() as conn:
            bugs_count = conn.execute("SELECT COUNT(*) FROM captured_bugs").fetchone()[0]
            history_count = conn.execute("SELECT COUNT(*) FROM sharing_history").fetchone()[0]

            conn.execute("DELETE FROM sharing_history")
            conn.execute("DELETE FROM captured_bugs")
            # Reset preferences to defaults but keep the records
            conn.execute("""
                UPDATE consent_preferences SET value = 'strict'
                WHERE key = 'consent_level'
            """)
            conn.execute("""
                UPDATE consent_preferences SET value = 'false'
                WHERE key = 'sharing_enabled'
            """)

            return {
                "bugs_deleted": bugs_count,
                "history_deleted": history_count
            }


# Singleton instance
_store: Optional[BugStore] = None


def get_bug_store() -> BugStore:
    """Get the singleton BugStore instance"""
    global _store
    if _store is None:
        _store = BugStore()
    return _store


if __name__ == "__main__":
    # Test the bug store
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_bugs.db"

    try:
        store = BugStore(db_path)

        # Test capturing a bug
        bug = store.capture_bug(
            error_type="TypeError",
            context_summary="Agent encountered TypeError when parsing JSON",
            error_message="TypeError: Cannot read property 'token' of undefined",
            command_pattern="npm run build",
            detection_source="auto",
            confidence=0.85
        )
        print(f"Captured bug: {bug.id}")

        # Test listing
        bugs = store.list_bugs()
        print(f"Total bugs: {len(bugs)}")

        # Test stats
        stats = store.get_stats()
        print(f"Stats: {stats}")

        # Test consent
        print(f"Consent level: {store.get_consent_level().value}")
        store.set_consent_level(ConsentLevel.MODERATE)
        print(f"New consent level: {store.get_consent_level().value}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
