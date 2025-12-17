#!/usr/bin/env python3
"""
Stream Session Manager for Power Mode

Tracks active streaming sessions, buffers chunks, and coordinates
with the status line display.

Part of PopKit Issue #23 (Fine-grained Streaming).
"""

import os
import sys
import json
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add protocol to path
sys.path.insert(0, os.path.dirname(__file__))
from protocol import Message, MessageType, StreamChunk

# =============================================================================
# CONFIGURATION
# =============================================================================

# Maximum chunks to keep per session
MAX_CHUNKS_PER_SESSION = 1000

# Session cleanup after completion (seconds)
SESSION_CLEANUP_DELAY = 300

# State file for status line integration
# NOTE: Must match path used by statusline.py and checkin-hook.py
STATE_FILE = Path(".claude/popkit/power-mode-state.json")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StreamSession:
    """
    Active streaming session from an agent.

    Tracks all chunks received and provides aggregation methods.
    """
    session_id: str
    agent_id: str
    tool_name: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    chunks: List[StreamChunk] = field(default_factory=list)
    is_complete: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_count(self) -> int:
        """Get number of chunks received."""
        return len(self.chunks)

    @property
    def total_content(self) -> str:
        """Get concatenated content from all chunks."""
        return "".join(chunk.content for chunk in self.chunks)

    @property
    def content_length(self) -> int:
        """Get total content length."""
        return sum(len(chunk.content) for chunk in self.chunks)

    @property
    def last_chunk_at(self) -> Optional[str]:
        """Get timestamp of last chunk."""
        if self.chunks:
            return self.chunks[-1].timestamp
        return None

    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        start = datetime.fromisoformat(self.started_at)
        if self.is_complete and self.last_chunk_at:
            end = datetime.fromisoformat(self.last_chunk_at)
        else:
            end = datetime.now()
        return (end - start).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without full chunk data)."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "started_at": self.started_at,
            "chunk_count": self.chunk_count,
            "content_length": self.content_length,
            "is_complete": self.is_complete,
            "error": self.error,
            "last_chunk_at": self.last_chunk_at,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class StreamStats:
    """Aggregate statistics across all sessions."""
    active_sessions: int = 0
    completed_sessions: int = 0
    total_chunks: int = 0
    total_bytes: int = 0
    agents_streaming: List[str] = field(default_factory=list)
    latest_tool: Optional[str] = None
    errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# STREAM MANAGER
# =============================================================================

class StreamManager:
    """
    Manages multiple concurrent stream sessions.

    Features:
    - Track sessions by ID and agent
    - Buffer chunks with size limits
    - Callbacks for real-time processing
    - Statistics for status line
    - Thread-safe operations
    """

    def __init__(
        self,
        on_chunk: Optional[Callable[[StreamChunk], None]] = None,
        on_session_complete: Optional[Callable[[StreamSession], None]] = None,
        max_chunks: int = MAX_CHUNKS_PER_SESSION
    ):
        """
        Initialize stream manager.

        Args:
            on_chunk: Callback for each chunk received
            on_session_complete: Callback when session completes
            max_chunks: Maximum chunks to keep per session
        """
        self._sessions: Dict[str, StreamSession] = {}
        self._lock = threading.RLock()
        self._on_chunk = on_chunk
        self._on_session_complete = on_session_complete
        self._max_chunks = max_chunks

    # =========================================================================
    # SESSION LIFECYCLE
    # =========================================================================

    def start_session(
        self,
        agent_id: str,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new streaming session.

        Args:
            agent_id: ID of the agent starting the stream
            tool_name: Name of tool being executed
            metadata: Optional additional metadata

        Returns:
            Unique session ID
        """
        session_id = str(uuid.uuid4())[:8]

        with self._lock:
            self._sessions[session_id] = StreamSession(
                session_id=session_id,
                agent_id=agent_id,
                tool_name=tool_name,
                metadata=metadata or {}
            )

        return session_id

    def add_chunk(self, chunk: StreamChunk) -> bool:
        """
        Add a chunk to a session.

        Args:
            chunk: StreamChunk to add

        Returns:
            True if chunk was added, False if session not found
        """
        with self._lock:
            session = self._sessions.get(chunk.session_id)
            if not session:
                return False

            # Enforce chunk limit
            if len(session.chunks) < self._max_chunks:
                session.chunks.append(chunk)

            # Mark complete if final chunk
            if chunk.is_final:
                session.is_complete = True

        # Notify callback
        if self._on_chunk:
            try:
                self._on_chunk(chunk)
            except Exception as e:
                print(f"Chunk callback error: {e}")

        # Notify session complete
        if chunk.is_final and self._on_session_complete:
            try:
                self._on_session_complete(session)
            except Exception as e:
                print(f"Session complete callback error: {e}")

        return True

    def end_session(
        self,
        session_id: str,
        error: Optional[str] = None
    ) -> Optional[StreamSession]:
        """
        End a streaming session.

        Args:
            session_id: Session to end
            error: Optional error message

        Returns:
            The ended session, or None if not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.is_complete = True
                session.error = error

                # Notify callback
                if self._on_session_complete:
                    try:
                        self._on_session_complete(session)
                    except Exception as e:
                        print(f"Session complete callback error: {e}")

                return session

        return None

    # =========================================================================
    # SESSION QUERIES
    # =========================================================================

    def get_session(self, session_id: str) -> Optional[StreamSession]:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_agent_session(self, agent_id: str) -> Optional[StreamSession]:
        """Get active session for an agent (most recent)."""
        with self._lock:
            for session in reversed(list(self._sessions.values())):
                if session.agent_id == agent_id and not session.is_complete:
                    return session
        return None

    def get_active_sessions(self) -> List[StreamSession]:
        """Get all incomplete sessions."""
        with self._lock:
            return [s for s in self._sessions.values() if not s.is_complete]

    def get_completed_sessions(self) -> List[StreamSession]:
        """Get all completed sessions."""
        with self._lock:
            return [s for s in self._sessions.values() if s.is_complete]

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> StreamStats:
        """Get aggregate statistics."""
        with self._lock:
            active = [s for s in self._sessions.values() if not s.is_complete]
            completed = [s for s in self._sessions.values() if s.is_complete]

            return StreamStats(
                active_sessions=len(active),
                completed_sessions=len(completed),
                total_chunks=sum(s.chunk_count for s in self._sessions.values()),
                total_bytes=sum(s.content_length for s in self._sessions.values()),
                agents_streaming=[s.agent_id for s in active],
                latest_tool=active[-1].tool_name if active else None,
                errors=sum(1 for s in self._sessions.values() if s.error)
            )

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary for status line display."""
        stats = self.get_stats()
        return {
            "active_streams": stats.active_sessions,
            "agents_streaming": stats.agents_streaming,
            "total_chunks": stats.total_chunks,
            "latest_tool": stats.latest_tool
        }

    # =========================================================================
    # MAINTENANCE
    # =========================================================================

    def cleanup_completed(self, max_age_seconds: int = SESSION_CLEANUP_DELAY) -> int:
        """
        Remove old completed sessions.

        Args:
            max_age_seconds: Maximum age for completed sessions

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        removed = 0

        with self._lock:
            to_remove = []
            for session_id, session in self._sessions.items():
                if session.is_complete:
                    started = datetime.fromisoformat(session.started_at)
                    if (now - started).total_seconds() > max_age_seconds:
                        to_remove.append(session_id)

            for session_id in to_remove:
                del self._sessions[session_id]
                removed += 1

        return removed

    def clear_all(self) -> int:
        """Clear all sessions."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count

    # =========================================================================
    # STATE PERSISTENCE
    # =========================================================================

    def save_state(self, state_file: Optional[Path] = None, batch_number: Optional[int] = None) -> None:
        """
        Save streaming state for status line integration.

        Args:
            state_file: Path to state file (defaults to .claude/power-mode-state.json)
            batch_number: Optional batch number for batch status widget (Issue #253)
        """
        state_file = state_file or STATE_FILE

        # Ensure directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state
        existing = {}
        if state_file.exists():
            try:
                with open(state_file) as f:
                    existing = json.load(f)
            except Exception:
                pass

        # Update with streaming state
        existing["streaming"] = self.get_status_summary()
        existing["streaming_updated_at"] = datetime.now().isoformat()

        # Update batch number if provided (Issue #253)
        if batch_number is not None:
            existing["batch_number"] = batch_number

        # Write back
        with open(state_file, "w") as f:
            json.dump(existing, f, indent=2)

    def load_state(self, state_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load streaming state from file.

        Args:
            state_file: Path to state file

        Returns:
            Streaming state dictionary
        """
        state_file = state_file or STATE_FILE

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    return data.get("streaming", {})
            except Exception:
                pass

        return {}


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_manager: Optional[StreamManager] = None


def get_manager() -> StreamManager:
    """Get or create the singleton stream manager."""
    global _manager
    if _manager is None:
        _manager = StreamManager()
    return _manager


def start_session(
    agent_id: str,
    tool_name: Optional[str] = None
) -> str:
    """Convenience function to start a session."""
    return get_manager().start_session(agent_id, tool_name)


def add_chunk(chunk: StreamChunk) -> bool:
    """Convenience function to add a chunk."""
    return get_manager().add_chunk(chunk)


def end_session(session_id: str, error: Optional[str] = None) -> Optional[StreamSession]:
    """Convenience function to end a session."""
    return get_manager().end_session(session_id, error)


def get_stats() -> StreamStats:
    """Convenience function to get stats."""
    return get_manager().get_stats()


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    print("StreamManager Test")
    print("=" * 40)

    # Create manager with callbacks
    received_chunks = []

    def on_chunk(chunk):
        received_chunks.append(chunk)

    def on_complete(session):
        print(f"  Session {session.session_id} complete: {session.chunk_count} chunks")

    mgr = StreamManager(on_chunk=on_chunk, on_session_complete=on_complete)

    # Test session lifecycle
    print("\n1. Starting session...")
    sid = mgr.start_session("agent-test", "Bash")
    print(f"   Session ID: {sid}")

    print("\n2. Adding chunks...")
    for i in range(5):
        chunk = StreamChunk(
            session_id=sid,
            agent_id="agent-test",
            chunk_index=i,
            content=f"chunk-{i} ",
            tool_name="Bash",
            is_final=(i == 4)
        )
        mgr.add_chunk(chunk)

    print(f"   Received: {len(received_chunks)} chunks")

    # Check session
    session = mgr.get_session(sid)
    print(f"\n3. Session state:")
    print(f"   Chunks: {session.chunk_count}")
    print(f"   Content: '{session.total_content}'")
    print(f"   Complete: {session.is_complete}")
    print(f"   Duration: {session.duration_seconds:.2f}s")

    # Stats
    stats = mgr.get_stats()
    print(f"\n4. Statistics:")
    print(f"   Active: {stats.active_sessions}")
    print(f"   Completed: {stats.completed_sessions}")
    print(f"   Total chunks: {stats.total_chunks}")

    # Cleanup
    removed = mgr.cleanup_completed(max_age_seconds=0)
    print(f"\n5. Cleanup: removed {removed} sessions")

    print("\n" + "=" * 40)
    print("All tests passed!")
