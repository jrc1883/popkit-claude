#!/usr/bin/env python3
"""
Pattern Learner for PopKit Command Learning

Part of Issue #89 - Platform-Aware Command Learning

SQLite-based storage for command corrections with confidence scoring.
Learns from failures and successes to improve future suggestions.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager

from .platform_detector import OSType, ShellType, get_platform_info


@dataclass
class CommandCorrection:
    """A learned command correction"""
    id: Optional[int]
    original_command: str
    platform: str
    shell: str
    error_pattern: Optional[str]
    corrected_command: str
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.0
    source: str = "auto"  # 'auto', 'manual', 'community'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CorrectionSuggestion:
    """A suggestion for correcting a command"""
    original: str
    suggested: str
    confidence: float
    source: str
    reason: Optional[str] = None


class PatternLearner:
    """SQLite-based pattern learning system"""

    DB_VERSION = 1
    DEFAULT_DB_PATH = Path.home() / '.claude' / 'config' / 'command_patterns.db'

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the pattern learner.

        Args:
            db_path: Path to the SQLite database (defaults to ~/.claude/config/command_patterns.db)
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
            # Create tables
            conn.executescript("""
                -- Command corrections table
                CREATE TABLE IF NOT EXISTS command_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_command TEXT NOT NULL,
                    original_command_hash TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    shell TEXT NOT NULL,
                    error_pattern TEXT,
                    corrected_command TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'auto',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(original_command_hash, platform, shell)
                );

                -- Index for fast lookups
                CREATE INDEX IF NOT EXISTS idx_corrections_lookup
                ON command_corrections(original_command_hash, platform, shell);

                -- Index for confidence-based sorting
                CREATE INDEX IF NOT EXISTS idx_corrections_confidence
                ON command_corrections(success_count, failure_count);

                -- Error patterns table (for pattern matching)
                CREATE TABLE IF NOT EXISTS error_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL UNIQUE,
                    pattern_type TEXT NOT NULL,
                    description TEXT,
                    suggestion_template TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Learning history (for analytics)
                CREATE TABLE IF NOT EXISTS learning_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correction_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (correction_id) REFERENCES command_corrections(id)
                );

                -- Schema version
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                -- Insert version if not exists
                INSERT OR IGNORE INTO schema_version (version) VALUES (1);
            """)

            # Seed common error patterns
            self._seed_error_patterns(conn)

    def _seed_error_patterns(self, conn: sqlite3.Connection):
        """Seed the database with common error patterns"""
        patterns = [
            ("'\\w+' is not recognized as an internal or external command",
             "command_not_found", "Windows command not found", None),
            ("command not found", "command_not_found", "Unix command not found", None),
            ("The system cannot find the path specified",
             "path_not_found", "Windows path error", None),
            ("No such file or directory", "path_not_found", "Unix path error", None),
            ("Access is denied", "permission_denied", "Windows permission error", None),
            ("Permission denied", "permission_denied", "Unix permission error", None),
            ("Invalid parameter", "invalid_params", "Invalid command parameters", None),
            ("Invalid switch", "invalid_params", "Invalid command switch", None),
            ("cannot copy a directory", "recursive_needed",
             "Recursive flag needed for directory", "Add -r flag"),
            ("xcopy.*Invalid number of parameters", "xcopy_params",
             "XCopy parameter error", "Check source and destination syntax"),
        ]

        for pattern, ptype, desc, suggestion in patterns:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO error_patterns
                    (pattern, pattern_type, description, suggestion_template)
                    VALUES (?, ?, ?, ?)
                """, (pattern, ptype, desc, suggestion))
            except sqlite3.IntegrityError:
                pass

    def _hash_command(self, command: str) -> str:
        """Create a hash for a command (normalizes whitespace)"""
        normalized = ' '.join(command.split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def record_correction(
        self,
        original_command: str,
        corrected_command: str,
        platform: Optional[str] = None,
        shell: Optional[str] = None,
        error_pattern: Optional[str] = None,
        source: str = "auto"
    ) -> CommandCorrection:
        """
        Record a command correction.

        Args:
            original_command: The original command that failed/needed correction
            corrected_command: The corrected command
            platform: OS type (auto-detected if not provided)
            shell: Shell type (auto-detected if not provided)
            error_pattern: The error message pattern that triggered correction
            source: Source of correction ('auto', 'manual', 'community')

        Returns:
            The recorded CommandCorrection
        """
        info = get_platform_info()
        platform = platform or info.os_type.value
        shell = shell or info.shell_type.value
        command_hash = self._hash_command(original_command)

        with self._get_connection() as conn:
            # Check if correction already exists
            existing = conn.execute("""
                SELECT id, success_count, failure_count FROM command_corrections
                WHERE original_command_hash = ? AND platform = ? AND shell = ?
            """, (command_hash, platform, shell)).fetchone()

            if existing:
                # Update existing correction
                conn.execute("""
                    UPDATE command_corrections
                    SET corrected_command = ?,
                        error_pattern = COALESCE(?, error_pattern),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (corrected_command, error_pattern, existing['id']))
                correction_id = existing['id']
            else:
                # Insert new correction
                cursor = conn.execute("""
                    INSERT INTO command_corrections
                    (original_command, original_command_hash, platform, shell,
                     error_pattern, corrected_command, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (original_command, command_hash, platform, shell,
                      error_pattern, corrected_command, source))
                correction_id = cursor.lastrowid

            # Log to history
            conn.execute("""
                INSERT INTO learning_history (correction_id, action, result)
                VALUES (?, 'record', 'created')
            """, (correction_id,))

        # Fetch the correction outside the with block (after commit)
        return self.get_correction(correction_id)

    def record_success(self, correction_id: int) -> None:
        """Record a successful use of a correction"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE command_corrections
                SET success_count = success_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (correction_id,))

            conn.execute("""
                INSERT INTO learning_history (correction_id, action, result)
                VALUES (?, 'use', 'success')
            """, (correction_id,))

    def record_failure(self, correction_id: int) -> None:
        """Record a failed use of a correction"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE command_corrections
                SET failure_count = failure_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (correction_id,))

            conn.execute("""
                INSERT INTO learning_history (correction_id, action, result)
                VALUES (?, 'use', 'failure')
            """, (correction_id,))

    def get_correction(self, correction_id: int) -> Optional[CommandCorrection]:
        """Get a correction by ID"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT id, original_command, platform, shell, error_pattern,
                       corrected_command, success_count, failure_count, source,
                       created_at, updated_at
                FROM command_corrections
                WHERE id = ?
            """, (correction_id,)).fetchone()

            if row:
                return self._row_to_correction(row)
            return None

    def _row_to_correction(self, row: sqlite3.Row) -> CommandCorrection:
        """Convert a database row to a CommandCorrection"""
        success = row['success_count']
        failure = row['failure_count']
        total = success + failure
        confidence = success / total if total > 0 else 0.0

        return CommandCorrection(
            id=row['id'],
            original_command=row['original_command'],
            platform=row['platform'],
            shell=row['shell'],
            error_pattern=row['error_pattern'],
            corrected_command=row['corrected_command'],
            success_count=success,
            failure_count=failure,
            confidence=confidence,
            source=row['source'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def find_suggestions(
        self,
        command: str,
        platform: Optional[str] = None,
        shell: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[CorrectionSuggestion]:
        """
        Find correction suggestions for a command.

        Args:
            command: The command to find suggestions for
            platform: OS type (auto-detected if not provided)
            shell: Shell type (auto-detected if not provided)
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of suggestions sorted by confidence
        """
        info = get_platform_info()
        platform = platform or info.os_type.value
        shell = shell or info.shell_type.value
        command_hash = self._hash_command(command)

        suggestions = []

        with self._get_connection() as conn:
            # Exact match
            row = conn.execute("""
                SELECT id, corrected_command, success_count, failure_count, source
                FROM command_corrections
                WHERE original_command_hash = ? AND platform = ? AND shell = ?
            """, (command_hash, platform, shell)).fetchone()

            if row:
                success = row['success_count']
                failure = row['failure_count']
                total = success + failure
                confidence = success / total if total > 0 else 0.5  # Default 0.5 for new

                if confidence >= min_confidence:
                    suggestions.append(CorrectionSuggestion(
                        original=command,
                        suggested=row['corrected_command'],
                        confidence=confidence,
                        source=row['source'],
                        reason="Exact match in learned patterns"
                    ))

            # Also check for similar commands (same base command)
            base_command = command.split()[0] if command else ""
            similar_rows = conn.execute("""
                SELECT corrected_command, success_count, failure_count, source,
                       original_command
                FROM command_corrections
                WHERE original_command LIKE ? AND platform = ? AND shell = ?
                      AND original_command_hash != ?
                ORDER BY success_count DESC
                LIMIT 5
            """, (f"{base_command}%", platform, shell, command_hash)).fetchall()

            for row in similar_rows:
                success = row['success_count']
                failure = row['failure_count']
                total = success + failure
                confidence = (success / total if total > 0 else 0.3) * 0.7  # Lower confidence for similar

                if confidence >= min_confidence:
                    suggestions.append(CorrectionSuggestion(
                        original=command,
                        suggested=row['corrected_command'],
                        confidence=confidence,
                        source=row['source'],
                        reason=f"Similar to learned pattern: {row['original_command']}"
                    ))

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions

    def get_best_suggestion(
        self,
        command: str,
        platform: Optional[str] = None,
        shell: Optional[str] = None,
        min_confidence: float = 0.7
    ) -> Optional[CorrectionSuggestion]:
        """
        Get the best correction suggestion for a command.

        Args:
            command: The command to find a suggestion for
            platform: OS type (auto-detected if not provided)
            shell: Shell type (auto-detected if not provided)
            min_confidence: Minimum confidence threshold

        Returns:
            Best suggestion or None if no good suggestion found
        """
        suggestions = self.find_suggestions(command, platform, shell, min_confidence)
        return suggestions[0] if suggestions else None

    def get_all_corrections(
        self,
        platform: Optional[str] = None,
        shell: Optional[str] = None,
        limit: int = 100
    ) -> List[CommandCorrection]:
        """Get all corrections, optionally filtered by platform/shell"""
        with self._get_connection() as conn:
            query = """
                SELECT id, original_command, platform, shell, error_pattern,
                       corrected_command, success_count, failure_count, source,
                       created_at, updated_at
                FROM command_corrections
            """
            params = []

            if platform or shell:
                conditions = []
                if platform:
                    conditions.append("platform = ?")
                    params.append(platform)
                if shell:
                    conditions.append("shell = ?")
                    params.append(shell)
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY success_count DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_correction(row) for row in rows]

    def delete_correction(self, correction_id: int) -> bool:
        """Delete a correction by ID"""
        with self._get_connection() as conn:
            # Delete history first (foreign key)
            conn.execute("""
                DELETE FROM learning_history WHERE correction_id = ?
            """, (correction_id,))

            cursor = conn.execute("""
                DELETE FROM command_corrections WHERE id = ?
            """, (correction_id,))

            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, any]:
        """Get statistics about learned patterns"""
        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM command_corrections"
            ).fetchone()[0]

            by_platform = dict(conn.execute("""
                SELECT platform, COUNT(*) FROM command_corrections GROUP BY platform
            """).fetchall())

            by_shell = dict(conn.execute("""
                SELECT shell, COUNT(*) FROM command_corrections GROUP BY shell
            """).fetchall())

            high_confidence = conn.execute("""
                SELECT COUNT(*) FROM command_corrections
                WHERE success_count > 0
                  AND CAST(success_count AS REAL) / (success_count + failure_count) >= 0.7
            """).fetchone()[0]

            recent_learning = conn.execute("""
                SELECT COUNT(*) FROM learning_history
                WHERE timestamp > datetime('now', '-7 days')
            """).fetchone()[0]

            return {
                "total_corrections": total,
                "by_platform": by_platform,
                "by_shell": by_shell,
                "high_confidence_count": high_confidence,
                "recent_learning_events": recent_learning
            }

    def export_patterns(self, filepath: Path) -> int:
        """Export all patterns to a JSON file"""
        corrections = self.get_all_corrections(limit=10000)
        data = {
            "version": self.DB_VERSION,
            "exported_at": datetime.now().isoformat(),
            "patterns": [c.to_dict() for c in corrections]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        return len(corrections)

    def import_patterns(self, filepath: Path, source: str = "imported") -> int:
        """Import patterns from a JSON file"""
        with open(filepath) as f:
            data = json.load(f)

        imported = 0
        for pattern in data.get("patterns", []):
            try:
                self.record_correction(
                    original_command=pattern["original_command"],
                    corrected_command=pattern["corrected_command"],
                    platform=pattern.get("platform"),
                    shell=pattern.get("shell"),
                    error_pattern=pattern.get("error_pattern"),
                    source=source
                )
                imported += 1
            except Exception:
                continue

        return imported


# Singleton instance
_learner: Optional[PatternLearner] = None


def get_learner() -> PatternLearner:
    """Get the singleton PatternLearner instance"""
    global _learner
    if _learner is None:
        _learner = PatternLearner()
    return _learner


def learn_correction(
    original: str,
    corrected: str,
    error: Optional[str] = None,
    source: str = "auto"
) -> CommandCorrection:
    """Convenience function to record a correction"""
    return get_learner().record_correction(
        original_command=original,
        corrected_command=corrected,
        error_pattern=error,
        source=source
    )


def suggest_correction(command: str, min_confidence: float = 0.7) -> Optional[str]:
    """Convenience function to get a correction suggestion"""
    suggestion = get_learner().get_best_suggestion(command, min_confidence=min_confidence)
    return suggestion.suggested if suggestion else None


if __name__ == "__main__":
    # Test the pattern learner
    learner = PatternLearner()

    print("Pattern Learner Test")
    print("=" * 50)

    # Record some test corrections
    corrections = [
        ("cp -r source/ dest/", "xcopy /E /I /Y source\\ dest\\"),
        ("rm -rf /tmp/test", "rmdir /S /Q C:\\tmp\\test"),
        ("cat file.txt", "type file.txt"),
    ]

    for orig, corrected in corrections:
        c = learner.record_correction(orig, corrected, source="test")
        print(f"Recorded: {orig} -> {corrected}")

        # Simulate some successes
        for _ in range(3):
            learner.record_success(c.id)

    # Test suggestion
    suggestion = learner.get_best_suggestion("cp -r source/ dest/")
    if suggestion:
        print(f"\nSuggestion for 'cp -r source/ dest/':")
        print(f"  -> {suggestion.suggested} (confidence: {suggestion.confidence:.2f})")

    # Show stats
    stats = learner.get_stats()
    print(f"\nStats: {stats}")
