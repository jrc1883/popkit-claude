#!/usr/bin/env python3
"""
File-Based Power Mode Fallback
A Redis-compatible interface using JSON files for multi-agent coordination.

This fallback enables Power Mode to work WITHOUT Docker/Redis for:
- Development and testing
- Single-machine setups
- 2-3 agent scenarios

Limitations:
- No true pub/sub (uses polling instead)
- File locking for concurrency (not as robust as Redis)
- Single machine only (no network distribution)
- Performance degrades with 4+ agents
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Platform-specific imports for file locking
if sys.platform == 'win32':
    import msvcrt
    WINDOWS = True
else:
    import fcntl
    WINDOWS = False


# =============================================================================
# FILE-BASED STORAGE
# =============================================================================

class FileLock:
    """Cross-platform file-based lock to prevent race conditions."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock_fd = None

    def __enter__(self):
        """Acquire the lock."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_fd = open(self.lock_file, 'w')

        # Try to acquire lock with timeout
        timeout = 5  # seconds
        start = time.time()

        while time.time() - start < timeout:
            try:
                if WINDOWS:
                    # Windows: use msvcrt
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    # Unix: use fcntl
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                time.sleep(0.01)  # 10ms

        raise TimeoutError(f"Could not acquire lock on {self.lock_file}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if self.lock_fd:
            try:
                if WINDOWS:
                    # Windows: unlock
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    # Unix: unlock
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass  # Ignore unlock errors
            finally:
                self.lock_fd.close()


@dataclass
class StateData:
    """The structure of our file-based state."""
    # Pub/sub message queues (channel -> list of messages)
    messages: Dict[str, List[Dict]] = field(default_factory=dict)

    # Key-value store (like Redis GET/SET)
    keys: Dict[str, str] = field(default_factory=dict)

    # Hash storage (like Redis HSET/HGET)
    hashes: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # List storage (like Redis LPUSH/LRANGE)
    lists: Dict[str, List[str]] = field(default_factory=dict)

    # Subscriptions (client_id -> set of channels)
    subscriptions: Dict[str, Set[str]] = field(default_factory=dict)

    # Last read position for each subscription (client_id -> channel -> index)
    read_positions: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "messages": self.messages,
            "keys": self.keys,
            "hashes": self.hashes,
            "lists": self.lists,
            "subscriptions": {k: list(v) for k, v in self.subscriptions.items()},
            "read_positions": self.read_positions,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'StateData':
        """Create from dict."""
        d = d.copy()
        # Convert subscription lists back to sets
        if "subscriptions" in d:
            d["subscriptions"] = {k: set(v) for k, v in d["subscriptions"].items()}
        return cls(**d)


# =============================================================================
# FILE-BASED REDIS CLIENT
# =============================================================================

class FileBasedPowerMode:
    """
    A Redis-compatible interface using JSON files.

    Mimics the Redis operations used by PowerModeCoordinator:
    - publish(channel, message)
    - subscribe(channel)
    - get(key) / set(key, value)
    - hset(key, field, value) / hget(key, field)
    - lpush(key, value) / lrange(key, start, stop)
    - ping()

    Thread-safe with file locking.
    """

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize file-based client.

        Args:
            state_file: Path to JSON state file. Defaults to .claude/popkit/power-mode-state.json
        """
        if state_file:
            self.state_file = Path(state_file)
        else:
            self.state_file = Path.cwd() / ".claude" / "popkit" / "power-mode-state.json"

        self.lock_file = self.state_file.with_suffix('.lock')

        # Client ID for this instance
        self.client_id = f"client-{os.getpid()}-{id(self)}"

        # PubSub object (created on demand)
        self._pubsub = None

        # Initialize state file if it doesn't exist
        self._ensure_state_file()

    def _ensure_state_file(self):
        """Create state file if it doesn't exist."""
        if not self.state_file.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(self.lock_file):
                with open(self.state_file, 'w') as f:
                    json.dump(StateData().to_dict(), f, indent=2)

    def _load_state(self) -> StateData:
        """Load state from file (assumes lock is held)."""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return StateData.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return StateData()

    def _save_state(self, state: StateData):
        """Save state to file (assumes lock is held)."""
        state.last_updated = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)

    # =========================================================================
    # REDIS COMPATIBILITY API
    # =========================================================================

    def ping(self) -> bool:
        """Check if the storage is accessible."""
        try:
            with FileLock(self.lock_file):
                return self.state_file.exists()
        except Exception:
            return False

    def publish(self, channel: str, message: str) -> int:
        """
        Publish a message to a channel.

        Returns: Number of subscribers that received the message.
        """
        with FileLock(self.lock_file):
            state = self._load_state()

            # Initialize channel if needed
            if channel not in state.messages:
                state.messages[channel] = []

            # Add message with timestamp
            msg_data = {
                "data": message,
                "timestamp": datetime.now().isoformat(),
                "channel": channel
            }
            state.messages[channel].append(msg_data)

            # Trim old messages (keep last 100 per channel)
            if len(state.messages[channel]) > 100:
                state.messages[channel] = state.messages[channel][-100:]

            # Count subscribers
            subscriber_count = sum(
                1 for subs in state.subscriptions.values()
                if channel in subs
            )

            self._save_state(state)
            return subscriber_count

    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        with FileLock(self.lock_file):
            state = self._load_state()
            return state.keys.get(key)

    def set(self, key: str, value: str) -> bool:
        """Set a key-value pair."""
        with FileLock(self.lock_file):
            state = self._load_state()
            state.keys[key] = value
            self._save_state(state)
            return True

    def hset(self, name: str, key: Optional[str] = None, value: Optional[str] = None,
             mapping: Optional[Dict[str, str]] = None) -> int:
        """
        Set hash field(s).

        Supports both single field and mapping.
        """
        with FileLock(self.lock_file):
            state = self._load_state()

            if name not in state.hashes:
                state.hashes[name] = {}

            fields_set = 0

            # Single field
            if key is not None and value is not None:
                state.hashes[name][key] = value
                fields_set = 1

            # Mapping
            if mapping:
                for k, v in mapping.items():
                    state.hashes[name][k] = v
                    fields_set += 1

            self._save_state(state)
            return fields_set

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field value."""
        with FileLock(self.lock_file):
            state = self._load_state()
            return state.hashes.get(name, {}).get(key)

    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        with FileLock(self.lock_file):
            state = self._load_state()
            return state.hashes.get(name, {}).copy()

    def lpush(self, name: str, *values: str) -> int:
        """Push values to the head of a list."""
        with FileLock(self.lock_file):
            state = self._load_state()

            if name not in state.lists:
                state.lists[name] = []

            # Insert at beginning (left push)
            for value in reversed(values):
                state.lists[name].insert(0, value)

            list_length = len(state.lists[name])
            self._save_state(state)
            return list_length

    def lrange(self, name: str, start: int, stop: int) -> List[str]:
        """Get a range of elements from a list."""
        with FileLock(self.lock_file):
            state = self._load_state()
            lst = state.lists.get(name, [])

            # Handle negative indices like Redis
            if stop == -1:
                return lst[start:]
            return lst[start:stop+1]

    def delete(self, *names: str) -> int:
        """Delete keys."""
        with FileLock(self.lock_file):
            state = self._load_state()
            count = 0

            for name in names:
                if name in state.keys:
                    del state.keys[name]
                    count += 1
                if name in state.hashes:
                    del state.hashes[name]
                    count += 1
                if name in state.lists:
                    del state.lists[name]
                    count += 1

            self._save_state(state)
            return count

    def pubsub(self) -> 'PubSubEmulator':
        """Get a pub/sub object."""
        if self._pubsub is None:
            self._pubsub = PubSubEmulator(self.state_file, self.lock_file, self.client_id)
        return self._pubsub


# =============================================================================
# PUB/SUB EMULATOR
# =============================================================================

class PubSubEmulator:
    """
    Emulates Redis pub/sub using polling.

    NOT true pub/sub - polls the file for new messages.
    Good enough for 2-3 agents, but not scalable.
    """

    def __init__(self, state_file: Path, lock_file: Path, client_id: str):
        self.state_file = state_file
        self.lock_file = lock_file
        self.client_id = client_id
        self.subscribed_channels: Set[str] = set()
        self.read_positions: Dict[str, int] = {}  # channel -> last_read_index

    def subscribe(self, *channels: str):
        """Subscribe to channels."""
        with FileLock(self.lock_file):
            state = StateData.from_dict(json.load(open(self.state_file)))

            if self.client_id not in state.subscriptions:
                state.subscriptions[self.client_id] = set()

            for channel in channels:
                state.subscriptions[self.client_id].add(channel)
                self.subscribed_channels.add(channel)

                # Initialize read position to current message count
                if channel not in self.read_positions:
                    current_count = len(state.messages.get(channel, []))
                    self.read_positions[channel] = current_count

            # Save subscription state
            if self.client_id not in state.read_positions:
                state.read_positions[self.client_id] = {}
            state.read_positions[self.client_id].update(self.read_positions)

            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

    def unsubscribe(self, *channels: str):
        """Unsubscribe from channels."""
        with FileLock(self.lock_file):
            state = StateData.from_dict(json.load(open(self.state_file)))

            if self.client_id in state.subscriptions:
                for channel in channels:
                    state.subscriptions[self.client_id].discard(channel)
                    self.subscribed_channels.discard(channel)

            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

    def get_message(self, timeout: float = 0) -> Optional[Dict]:
        """
        Get next message from subscribed channels.

        This POLLS the file - not real pub/sub.
        timeout: How long to wait for messages (in seconds).

        Returns:
            {
                "type": "message",
                "channel": "channel_name",
                "data": "message_data"
            }
            or None if no messages
        """
        start_time = time.time()

        while True:
            # Check for new messages
            with FileLock(self.lock_file):
                state = StateData.from_dict(json.load(open(self.state_file)))

                # Check each subscribed channel
                for channel in self.subscribed_channels:
                    messages = state.messages.get(channel, [])
                    last_read = self.read_positions.get(channel, 0)

                    # New messages available?
                    if len(messages) > last_read:
                        msg = messages[last_read]
                        self.read_positions[channel] = last_read + 1

                        # Update read position in state
                        if self.client_id not in state.read_positions:
                            state.read_positions[self.client_id] = {}
                        state.read_positions[self.client_id][channel] = last_read + 1

                        with open(self.state_file, 'w') as f:
                            json.dump(state.to_dict(), f, indent=2)

                        return {
                            "type": "message",
                            "channel": channel,
                            "data": msg["data"],
                            "timestamp": msg.get("timestamp")
                        }

            # Check timeout
            elapsed = time.time() - start_time
            if timeout and elapsed >= timeout:
                return None

            # No messages, sleep a bit before polling again
            time.sleep(0.1)  # 100ms polling interval


# =============================================================================
# UTILITIES
# =============================================================================

def cleanup_old_messages(state_file: Path, max_age_hours: int = 24):
    """
    Clean up old messages from state file.

    Args:
        state_file: Path to state file
        max_age_hours: Remove messages older than this
    """
    lock_file = state_file.with_suffix('.lock')

    with FileLock(lock_file):
        with open(state_file, 'r') as f:
            data = json.load(f)

        state = StateData.from_dict(data)
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        # Clean up messages
        for channel in state.messages:
            state.messages[channel] = [
                msg for msg in state.messages[channel]
                if datetime.fromisoformat(msg["timestamp"]) > cutoff
            ]

        with open(state_file, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)


def get_stats(state_file: Path) -> Dict:
    """
    Get statistics about the state file.

    Returns:
        {
            "total_messages": int,
            "channels": int,
            "subscribers": int,
            "keys": int,
            "hashes": int,
            "lists": int,
            "file_size_kb": float,
            "last_updated": str
        }
    """
    lock_file = state_file.with_suffix('.lock')

    with FileLock(lock_file):
        with open(state_file, 'r') as f:
            data = json.load(f)

        state = StateData.from_dict(data)

        total_messages = sum(len(msgs) for msgs in state.messages.values())
        file_size = state_file.stat().st_size / 1024  # KB

        return {
            "total_messages": total_messages,
            "channels": len(state.messages),
            "subscribers": len(state.subscriptions),
            "keys": len(state.keys),
            "hashes": len(state.hashes),
            "lists": len(state.lists),
            "file_size_kb": round(file_size, 2),
            "last_updated": state.last_updated
        }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys

    # Example: Basic pub/sub
    print("=== File-Based Power Mode Demo ===\n")

    # Create client
    client = FileBasedPowerMode()

    # Test connection
    if client.ping():
        print(f"[OK] Connected to file-based storage: {client.state_file}")
    else:
        print("[FAIL] Failed to connect")
        sys.exit(1)

    print()

    # Test key-value operations
    print("=== Key-Value Operations ===")
    client.set("test:key", "hello world")
    value = client.get("test:key")
    print(f"Set/Get: {value}")
    print()

    # Test hash operations
    print("=== Hash Operations ===")
    client.hset("agent:123", mapping={
        "name": "code-reviewer",
        "status": "active",
        "progress": "0.5"
    })
    agent_data = client.hgetall("agent:123")
    print(f"Hash data: {agent_data}")
    print()

    # Test list operations
    print("=== List Operations ===")
    client.lpush("tasks:pending", "task-1", "task-2", "task-3")
    tasks = client.lrange("tasks:pending", 0, -1)
    print(f"Tasks: {tasks}")
    print()

    # Test pub/sub
    print("=== Pub/Sub Operations ===")

    # Publisher
    pubsub = client.pubsub()
    pubsub.subscribe("pop:broadcast")
    print("[OK] Subscribed to pop:broadcast")

    # Publish a message
    count = client.publish("pop:broadcast", json.dumps({
        "type": "HEARTBEAT",
        "from": "agent-1",
        "timestamp": datetime.now().isoformat()
    }))
    print(f"[OK] Published message (reached {count} subscribers)")

    # Receive message
    msg = pubsub.get_message(timeout=1)
    if msg:
        print(f"[OK] Received: {msg['data'][:50]}...")
    else:
        print("[FAIL] No message received")

    print()

    # Stats
    print("=== Storage Stats ===")
    stats = get_stats(client.state_file)
    for key, value in stats.items():
        print(f"{key}: {value}")

    print(f"\n[OK] State file: {client.state_file}")
