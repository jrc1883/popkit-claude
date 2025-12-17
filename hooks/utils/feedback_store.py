#!/usr/bin/env python3
"""
Feedback Store - SQLite Storage for User Feedback

Part of Issue #91 (User Feedback Collection System)
Parent: Epic #88 (Self-Improvement & Learning System)

Provides persistent storage for user feedback ratings, aggregations,
and session tracking to avoid feedback fatigue.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
from enum import IntEnum


class FeedbackRating(IntEnum):
    """0-3 rating scale matching Claude Code's feedback system"""
    HARMFUL = 0      # Harmful/Wrong - Flag for review
    NOT_HELPFUL = 1  # Not helpful - Record and suggest alternatives
    HELPFUL = 2      # Somewhat helpful - Positive signal
    VERY_HELPFUL = 3 # Very helpful - Strong positive, reinforce


class ContextType:
    """Types of contexts that can receive feedback"""
    AGENT = "agent"           # After agent completion
    WORKFLOW = "workflow"     # After workflow phase
    COMMAND = "command"       # After command execution
    SESSION = "session"       # Overall session rating
    ERROR_RECOVERY = "error"  # After error fix suggestion


@dataclass
class FeedbackEntry:
    """Represents a single feedback entry"""
    id: str
    rating: int
    context_type: str
    context_id: Optional[str]
    agent_name: Optional[str]
    command_name: Optional[str]
    workflow_phase: Optional[str]
    user_comment: Optional[str]
    session_id: Optional[str]
    tool_call_count: int  # Tool calls since last feedback
    created_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FeedbackAggregate:
    """Aggregated feedback for a context"""
    context_type: str
    context_id: str
    avg_rating: float
    total_count: int
    rating_distribution: Dict[int, int]
    updated_at: str


class FeedbackStore:
    """SQLite-based storage for user feedback"""

    DB_VERSION = 1
    DEFAULT_DB_PATH = Path.home() / '.claude' / 'config' / 'feedback.db'

    # Feedback frequency settings
    MIN_TOOL_CALLS_BETWEEN_FEEDBACK = 10
    MAX_DISMISSED_BEFORE_PAUSE = 3

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the feedback store.

        Args:
            db_path: Path to SQLite database (defaults to ~/.claude/config/feedback.db)
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
                -- Feedback entries table
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 3),
                    context_type TEXT NOT NULL,
                    context_id TEXT,
                    agent_name TEXT,
                    command_name TEXT,
                    workflow_phase TEXT,
                    user_comment TEXT,
                    session_id TEXT,
                    tool_call_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for efficient queries
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                ON feedback(created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_feedback_context
                ON feedback(context_type, context_id);

                CREATE INDEX IF NOT EXISTS idx_feedback_agent
                ON feedback(agent_name);

                CREATE INDEX IF NOT EXISTS idx_feedback_session
                ON feedback(session_id);

                -- Feedback aggregates (materialized for performance)
                CREATE TABLE IF NOT EXISTS feedback_aggregates (
                    context_type TEXT,
                    context_id TEXT,
                    avg_rating REAL,
                    total_count INTEGER,
                    rating_0_count INTEGER DEFAULT 0,
                    rating_1_count INTEGER DEFAULT 0,
                    rating_2_count INTEGER DEFAULT 0,
                    rating_3_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (context_type, context_id)
                );

                -- Session tracking (for feedback fatigue prevention)
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    tool_calls_since_feedback INTEGER DEFAULT 0,
                    feedback_count INTEGER DEFAULT 0,
                    dismissed_count INTEGER DEFAULT 0,
                    never_ask_this_session INTEGER DEFAULT 0,
                    last_feedback_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Preferences
                CREATE TABLE IF NOT EXISTS feedback_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Schema version
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                INSERT OR IGNORE INTO schema_version (version) VALUES (1);

                -- Default preferences
                INSERT OR IGNORE INTO feedback_preferences (key, value)
                VALUES ('feedback_enabled', 'true');

                INSERT OR IGNORE INTO feedback_preferences (key, value)
                VALUES ('min_tool_calls', '10');

                INSERT OR IGNORE INTO feedback_preferences (key, value)
                VALUES ('show_session_summary', 'false');
            """)

    def _generate_id(self) -> str:
        """Generate a unique feedback ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:6]
        return f"fb-{timestamp}-{unique}"

    # =========================================================================
    # FEEDBACK OPERATIONS
    # =========================================================================

    def record_feedback(
        self,
        rating: int,
        context_type: str,
        context_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        command_name: Optional[str] = None,
        workflow_phase: Optional[str] = None,
        user_comment: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_call_count: int = 0
    ) -> FeedbackEntry:
        """
        Record a feedback entry.

        Args:
            rating: 0-3 rating (use FeedbackRating enum)
            context_type: Type of context (agent, command, workflow, etc.)
            context_id: Specific identifier for the context
            agent_name: Name of agent if applicable
            command_name: Name of command if applicable
            workflow_phase: Workflow phase if applicable
            user_comment: Optional free-text comment
            session_id: Session identifier for tracking
            tool_call_count: Number of tool calls since last feedback

        Returns:
            The recorded feedback entry
        """
        if not 0 <= rating <= 3:
            raise ValueError(f"Rating must be 0-3, got {rating}")

        feedback_id = self._generate_id()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO feedback
                (id, rating, context_type, context_id, agent_name, command_name,
                 workflow_phase, user_comment, session_id, tool_call_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (feedback_id, rating, context_type, context_id, agent_name,
                  command_name, workflow_phase, user_comment, session_id,
                  tool_call_count))

            # Update aggregates
            self._update_aggregate(conn, context_type, context_id or context_type, rating)

            # Update session state
            if session_id:
                self._update_session_after_feedback(conn, session_id)

        return self.get_feedback(feedback_id)

    def _update_aggregate(self, conn, context_type: str, context_id: str, new_rating: int):
        """Update the aggregate statistics for a context"""
        # Get current aggregate
        row = conn.execute("""
            SELECT * FROM feedback_aggregates
            WHERE context_type = ? AND context_id = ?
        """, (context_type, context_id)).fetchone()

        if row:
            # Update existing aggregate
            new_count = row['total_count'] + 1
            new_avg = ((row['avg_rating'] * row['total_count']) + new_rating) / new_count

            rating_cols = {
                0: 'rating_0_count',
                1: 'rating_1_count',
                2: 'rating_2_count',
                3: 'rating_3_count'
            }

            conn.execute(f"""
                UPDATE feedback_aggregates
                SET avg_rating = ?,
                    total_count = ?,
                    {rating_cols[new_rating]} = {rating_cols[new_rating]} + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE context_type = ? AND context_id = ?
            """, (new_avg, new_count, context_type, context_id))
        else:
            # Create new aggregate
            rating_counts = [0, 0, 0, 0]
            rating_counts[new_rating] = 1

            conn.execute("""
                INSERT INTO feedback_aggregates
                (context_type, context_id, avg_rating, total_count,
                 rating_0_count, rating_1_count, rating_2_count, rating_3_count, updated_at)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (context_type, context_id, float(new_rating),
                  rating_counts[0], rating_counts[1], rating_counts[2], rating_counts[3]))

    def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """Get a feedback entry by ID"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM feedback WHERE id = ?
            """, (feedback_id,)).fetchone()

            if row:
                return self._row_to_feedback(row)
            return None

    def _row_to_feedback(self, row: sqlite3.Row) -> FeedbackEntry:
        """Convert a database row to a FeedbackEntry"""
        return FeedbackEntry(
            id=row['id'],
            rating=row['rating'],
            context_type=row['context_type'],
            context_id=row['context_id'],
            agent_name=row['agent_name'],
            command_name=row['command_name'],
            workflow_phase=row['workflow_phase'],
            user_comment=row['user_comment'],
            session_id=row['session_id'],
            tool_call_count=row['tool_call_count'],
            created_at=row['created_at']
        )

    def list_feedback(
        self,
        limit: int = 50,
        context_type: Optional[str] = None,
        agent_name: Optional[str] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[FeedbackEntry]:
        """List feedback entries with optional filters"""
        query = "SELECT * FROM feedback"
        params = []
        conditions = []

        if context_type:
            conditions.append("context_type = ?")
            params.append(context_type)

        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)

        if min_rating is not None:
            conditions.append("rating >= ?")
            params.append(min_rating)

        if max_rating is not None:
            conditions.append("rating <= ?")
            params.append(max_rating)

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_feedback(row) for row in rows]

    def get_aggregate(self, context_type: str, context_id: str) -> Optional[FeedbackAggregate]:
        """Get aggregated feedback for a context"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM feedback_aggregates
                WHERE context_type = ? AND context_id = ?
            """, (context_type, context_id)).fetchone()

            if row:
                return FeedbackAggregate(
                    context_type=row['context_type'],
                    context_id=row['context_id'],
                    avg_rating=row['avg_rating'],
                    total_count=row['total_count'],
                    rating_distribution={
                        0: row['rating_0_count'],
                        1: row['rating_1_count'],
                        2: row['rating_2_count'],
                        3: row['rating_3_count']
                    },
                    updated_at=row['updated_at']
                )
            return None

    def get_low_rated_items(self, max_avg_rating: float = 1.5, min_count: int = 3) -> List[FeedbackAggregate]:
        """Get items with low average ratings (for review)"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM feedback_aggregates
                WHERE avg_rating <= ? AND total_count >= ?
                ORDER BY avg_rating ASC
            """, (max_avg_rating, min_count)).fetchall()

            return [
                FeedbackAggregate(
                    context_type=row['context_type'],
                    context_id=row['context_id'],
                    avg_rating=row['avg_rating'],
                    total_count=row['total_count'],
                    rating_distribution={
                        0: row['rating_0_count'],
                        1: row['rating_1_count'],
                        2: row['rating_2_count'],
                        3: row['rating_3_count']
                    },
                    updated_at=row['updated_at']
                )
                for row in rows
            ]

    # =========================================================================
    # SESSION STATE (Feedback Fatigue Prevention)
    # =========================================================================

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get or create session state for feedback tracking"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM session_state WHERE session_id = ?
            """, (session_id,)).fetchone()

            if row:
                return dict(row)

            # Create new session
            conn.execute("""
                INSERT INTO session_state (session_id)
                VALUES (?)
            """, (session_id,))

            return {
                'session_id': session_id,
                'tool_calls_since_feedback': 0,
                'feedback_count': 0,
                'dismissed_count': 0,
                'never_ask_this_session': 0,
                'last_feedback_at': None
            }

    def increment_tool_calls(self, session_id: str) -> int:
        """Increment tool call counter for a session, return new count"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO session_state (session_id, tool_calls_since_feedback)
                VALUES (?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                tool_calls_since_feedback = tool_calls_since_feedback + 1
            """, (session_id,))

            row = conn.execute("""
                SELECT tool_calls_since_feedback FROM session_state
                WHERE session_id = ?
            """, (session_id,)).fetchone()

            return row['tool_calls_since_feedback'] if row else 1

    def _update_session_after_feedback(self, conn, session_id: str):
        """Update session state after feedback is recorded"""
        conn.execute("""
            UPDATE session_state
            SET tool_calls_since_feedback = 0,
                feedback_count = feedback_count + 1,
                dismissed_count = 0,
                last_feedback_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))

    def record_dismissed(self, session_id: str) -> int:
        """Record that user dismissed a feedback prompt, return dismiss count"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE session_state
                SET dismissed_count = dismissed_count + 1
                WHERE session_id = ?
            """, (session_id,))

            row = conn.execute("""
                SELECT dismissed_count FROM session_state
                WHERE session_id = ?
            """, (session_id,)).fetchone()

            return row['dismissed_count'] if row else 0

    def set_never_ask_session(self, session_id: str):
        """Mark session as "never ask again" """
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE session_state
                SET never_ask_this_session = 1
                WHERE session_id = ?
            """, (session_id,))

    def should_ask_feedback(self, session_id: str) -> bool:
        """
        Determine if we should ask for feedback based on session state.

        Rules:
        - At least MIN_TOOL_CALLS_BETWEEN_FEEDBACK tool calls since last feedback
        - Not dismissed more than MAX_DISMISSED_BEFORE_PAUSE times
        - User hasn't said "never ask this session"
        """
        session = self.get_or_create_session(session_id)

        # Check "never ask" flag
        if session['never_ask_this_session']:
            return False

        # Check dismissed count
        if session['dismissed_count'] >= self.MAX_DISMISSED_BEFORE_PAUSE:
            return False

        # Check tool call threshold
        min_calls = int(self.get_preference('min_tool_calls', str(self.MIN_TOOL_CALLS_BETWEEN_FEEDBACK)))
        if session['tool_calls_since_feedback'] < min_calls:
            return False

        return True

    # =========================================================================
    # PREFERENCES
    # =========================================================================

    def get_preference(self, key: str, default: str = "") -> str:
        """Get a preference value"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT value FROM feedback_preferences WHERE key = ?
            """, (key,)).fetchone()
            return row['value'] if row else default

    def set_preference(self, key: str, value: str) -> None:
        """Set a preference value"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO feedback_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))

    def is_feedback_enabled(self) -> bool:
        """Check if feedback collection is enabled"""
        return self.get_preference('feedback_enabled', 'true') == 'true'

    def set_feedback_enabled(self, enabled: bool) -> None:
        """Enable or disable feedback collection"""
        self.set_preference('feedback_enabled', 'true' if enabled else 'false')

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get overall feedback statistics"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

            avg_rating = conn.execute(
                "SELECT AVG(rating) FROM feedback"
            ).fetchone()[0] or 0.0

            by_context = dict(conn.execute("""
                SELECT context_type, COUNT(*) FROM feedback GROUP BY context_type
            """).fetchall())

            by_rating = dict(conn.execute("""
                SELECT rating, COUNT(*) FROM feedback GROUP BY rating
            """).fetchall())

            recent_count = conn.execute("""
                SELECT COUNT(*) FROM feedback
                WHERE created_at > datetime('now', '-7 days')
            """).fetchone()[0]

            low_rated = len(self.get_low_rated_items())

            return {
                "total_feedback": total,
                "avg_rating": round(avg_rating, 2),
                "by_context_type": by_context,
                "by_rating": by_rating,
                "recent_7_days": recent_count,
                "low_rated_items": low_rated,
                "feedback_enabled": self.is_feedback_enabled()
            }

    def get_agent_stats(self) -> List[Dict[str, Any]]:
        """Get feedback statistics per agent"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    agent_name,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating,
                    SUM(CASE WHEN rating <= 1 THEN 1 ELSE 0 END) as low_count,
                    SUM(CASE WHEN rating >= 2 THEN 1 ELSE 0 END) as high_count
                FROM feedback
                WHERE agent_name IS NOT NULL
                GROUP BY agent_name
                ORDER BY avg_rating DESC
            """).fetchall()

            return [
                {
                    "agent": row['agent_name'],
                    "count": row['count'],
                    "avg_rating": round(row['avg_rating'], 2),
                    "low_count": row['low_count'],
                    "high_count": row['high_count']
                }
                for row in rows
            ]

    # =========================================================================
    # EXPORT / GDPR COMPLIANCE
    # =========================================================================

    def export_all(self, filepath: Path) -> int:
        """Export all feedback data for GDPR compliance"""
        feedback_list = self.list_feedback(limit=10000)
        data = {
            "version": self.DB_VERSION,
            "exported_at": datetime.now().isoformat(),
            "feedback": [f.to_dict() for f in feedback_list],
            "stats": self.get_stats()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        return len(feedback_list)

    def delete_all_data(self) -> Dict[str, int]:
        """Delete all feedback data (GDPR right to be forgotten)"""
        with self._get_connection() as conn:
            feedback_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            aggregate_count = conn.execute("SELECT COUNT(*) FROM feedback_aggregates").fetchone()[0]
            session_count = conn.execute("SELECT COUNT(*) FROM session_state").fetchone()[0]

            conn.execute("DELETE FROM feedback")
            conn.execute("DELETE FROM feedback_aggregates")
            conn.execute("DELETE FROM session_state")

            return {
                "feedback_deleted": feedback_count,
                "aggregates_deleted": aggregate_count,
                "sessions_deleted": session_count
            }


# Singleton instance
_store: Optional[FeedbackStore] = None


def get_feedback_store() -> FeedbackStore:
    """Get the singleton FeedbackStore instance"""
    global _store
    if _store is None:
        _store = FeedbackStore()
    return _store


if __name__ == "__main__":
    # Test the feedback store
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_feedback.db"

    try:
        store = FeedbackStore(db_path)

        # Test recording feedback
        feedback = store.record_feedback(
            rating=FeedbackRating.VERY_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer",
            session_id="test-session-001",
            user_comment="Great suggestions!"
        )
        print(f"Recorded feedback: {feedback.id}")

        # Record more feedback
        store.record_feedback(
            rating=FeedbackRating.HELPFUL,
            context_type=ContextType.COMMAND,
            command_name="/popkit:git commit",
            session_id="test-session-001"
        )

        store.record_feedback(
            rating=FeedbackRating.NOT_HELPFUL,
            context_type=ContextType.AGENT,
            agent_name="code-reviewer",
            session_id="test-session-001"
        )

        # Test listing
        all_feedback = store.list_feedback()
        print(f"Total feedback: {len(all_feedback)}")

        # Test aggregate
        agg = store.get_aggregate(ContextType.AGENT, "code-reviewer")
        if agg:
            print(f"code-reviewer avg: {agg.avg_rating:.2f} ({agg.total_count} ratings)")

        # Test stats
        stats = store.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")

        # Test session state
        session = store.get_or_create_session("test-session-002")
        print(f"Session state: {session}")

        # Increment tool calls
        for _ in range(12):
            count = store.increment_tool_calls("test-session-002")
        print(f"Tool calls: {count}")

        # Check if should ask
        should_ask = store.should_ask_feedback("test-session-002")
        print(f"Should ask feedback: {should_ask}")

        # Test low rated items
        low_rated = store.get_low_rated_items()
        print(f"Low rated items: {len(low_rated)}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
