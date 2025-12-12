#!/usr/bin/env python3
"""
Upstash Redis Adapter for Power Mode

Provides a Redis-like interface over Upstash REST API, allowing Power Mode
to work without local Docker/Redis installation.

Part of Issue #191: Power Mode Upstash Migration

Usage:
    from upstash_adapter import get_redis_client

    # Auto-detects: Upstash REST API if env vars set, else local Redis
    client = get_redis_client()

    # Use like regular redis client
    client.set("key", "value")
    client.publish("channel", "message")
"""

import json
import os
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Union
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from dataclasses import dataclass
from abc import ABC, abstractmethod


# =============================================================================
# CONFIGURATION
# =============================================================================

UPSTASH_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Default TTL for pub/sub simulation (7 days)
DEFAULT_TTL = 86400 * 7


# =============================================================================
# ABSTRACT BASE CLIENT
# =============================================================================

class BaseRedisClient(ABC):
    """Abstract base for Redis clients (local and Upstash)."""

    @abstractmethod
    def ping(self) -> bool:
        """Check connection health."""
        pass

    @abstractmethod
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        pass

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        pass

    @abstractmethod
    def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        pass

    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass

    @abstractmethod
    def hset(self, name: str, mapping: Dict[str, str]) -> int:
        """Set hash fields."""
        pass

    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        pass

    @abstractmethod
    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        pass

    @abstractmethod
    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        pass

    @abstractmethod
    def rpush(self, name: str, *values: str) -> int:
        """Push to end of list."""
        pass

    @abstractmethod
    def lpush(self, name: str, *values: str) -> int:
        """Push to start of list."""
        pass

    @abstractmethod
    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get list range."""
        pass

    @abstractmethod
    def lpop(self, name: str) -> Optional[str]:
        """Pop from start of list."""
        pass

    @abstractmethod
    def expire(self, name: str, time: int) -> bool:
        """Set key expiration."""
        pass

    @abstractmethod
    def ttl(self, name: str) -> int:
        """Get time to live."""
        pass

    @abstractmethod
    def publish(self, channel: str, message: str) -> int:
        """Publish message to channel (simulated via streams for Upstash)."""
        pass

    @abstractmethod
    def pubsub(self) -> 'BasePubSub':
        """Get pub/sub interface."""
        pass

    # Stream operations (native Redis Streams)
    @abstractmethod
    def xadd(self, name: str, fields: Dict[str, str], id: str = "*", maxlen: Optional[int] = None) -> str:
        """Add to stream."""
        pass

    @abstractmethod
    def xread(self, streams: Dict[str, str], count: Optional[int] = None, block: Optional[int] = None) -> List:
        """Read from streams."""
        pass

    @abstractmethod
    def xrange(self, name: str, min: str = "-", max: str = "+", count: Optional[int] = None) -> List:
        """Get stream range."""
        pass


class BasePubSub(ABC):
    """Abstract base for pub/sub interface."""

    @abstractmethod
    def subscribe(self, *channels: str) -> None:
        """Subscribe to channels."""
        pass

    @abstractmethod
    def unsubscribe(self, *channels: str) -> None:
        """Unsubscribe from channels."""
        pass

    @abstractmethod
    def listen(self) -> Any:
        """Get message generator."""
        pass

    @abstractmethod
    def get_message(self, timeout: float = 0.0) -> Optional[Dict]:
        """Get next message if available."""
        pass


# =============================================================================
# UPSTASH REST API CLIENT
# =============================================================================

class UpstashRedisClient(BaseRedisClient):
    """
    Redis client using Upstash REST API.

    Implements pub/sub using Redis Streams for cloud compatibility.
    All operations use HTTP REST API - no socket connections required.
    """

    # Stream-based pub/sub prefix
    PUBSUB_STREAM_PREFIX = "popkit:pubsub:"

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = url or UPSTASH_REST_URL
        self.token = token or UPSTASH_REST_TOKEN

        if not self.url or not self.token:
            raise ValueError(
                "Upstash credentials required. Set UPSTASH_REDIS_REST_URL and "
                "UPSTASH_REDIS_REST_TOKEN environment variables."
            )

        # Ensure URL ends properly
        self.url = self.url.rstrip("/")

    def _execute(self, *args: str) -> Any:
        """Execute Redis command via Upstash REST API."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        request = Request(self.url, method="POST")
        for key, value in headers.items():
            request.add_header(key, value)

        # Command as JSON array
        body = json.dumps(list(args)).encode('utf-8')

        try:
            with urlopen(request, body, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("result")
        except HTTPError as e:
            if e.code == 401:
                raise ValueError("Invalid Upstash credentials")
            return None
        except URLError:
            return None

    def ping(self) -> bool:
        return self._execute("PING") == "PONG"

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if ex:
            result = self._execute("SET", key, value, "EX", str(ex))
        else:
            result = self._execute("SET", key, value)
        return result == "OK"

    def get(self, key: str) -> Optional[str]:
        return self._execute("GET", key)

    def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        result = self._execute("DEL", *keys)
        return result if isinstance(result, int) else 0

    def exists(self, *keys: str) -> int:
        if not keys:
            return 0
        result = self._execute("EXISTS", *keys)
        return result if isinstance(result, int) else 0

    def keys(self, pattern: str = "*") -> List[str]:
        result = self._execute("KEYS", pattern)
        return result if isinstance(result, list) else []

    def hset(self, name: str, mapping: Dict[str, str]) -> int:
        if not mapping:
            return 0
        args = ["HSET", name]
        for k, v in mapping.items():
            args.extend([k, v])
        result = self._execute(*args)
        return result if isinstance(result, int) else 0

    def hget(self, name: str, key: str) -> Optional[str]:
        return self._execute("HGET", name, key)

    def hgetall(self, name: str) -> Dict[str, str]:
        result = self._execute("HGETALL", name)
        if not result or not isinstance(result, list):
            return {}
        # Convert flat list to dict
        return {result[i]: result[i+1] for i in range(0, len(result), 2)}

    def hdel(self, name: str, *keys: str) -> int:
        if not keys:
            return 0
        result = self._execute("HDEL", name, *keys)
        return result if isinstance(result, int) else 0

    def rpush(self, name: str, *values: str) -> int:
        if not values:
            return 0
        result = self._execute("RPUSH", name, *values)
        return result if isinstance(result, int) else 0

    def lpush(self, name: str, *values: str) -> int:
        if not values:
            return 0
        result = self._execute("LPUSH", name, *values)
        return result if isinstance(result, int) else 0

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        result = self._execute("LRANGE", name, str(start), str(end))
        return result if isinstance(result, list) else []

    def lpop(self, name: str) -> Optional[str]:
        return self._execute("LPOP", name)

    def expire(self, name: str, time: int) -> bool:
        result = self._execute("EXPIRE", name, str(time))
        return result == 1

    def ttl(self, name: str) -> int:
        result = self._execute("TTL", name)
        return result if isinstance(result, int) else -2

    # =========================================================================
    # PUB/SUB VIA STREAMS
    # =========================================================================

    def publish(self, channel: str, message: str) -> int:
        """
        Publish message using Redis Streams.

        Since Upstash REST API doesn't support traditional pub/sub,
        we simulate it using streams. Each channel is a stream.
        """
        stream_key = f"{self.PUBSUB_STREAM_PREFIX}{channel}"

        # XADD with MAXLEN to prevent unbounded growth
        result = self._execute(
            "XADD", stream_key, "MAXLEN", "~", "1000", "*",
            "message", message,
            "timestamp", str(int(time.time() * 1000))
        )

        # Set TTL on stream
        self._execute("EXPIRE", stream_key, str(DEFAULT_TTL))

        return 1 if result else 0

    def pubsub(self) -> 'UpstashPubSub':
        """Get pub/sub interface using streams."""
        return UpstashPubSub(self)

    # =========================================================================
    # STREAM OPERATIONS
    # =========================================================================

    def xadd(self, name: str, fields: Dict[str, str], id: str = "*", maxlen: Optional[int] = None) -> str:
        args = ["XADD", name]
        if maxlen:
            args.extend(["MAXLEN", "~", str(maxlen)])
        args.append(id)
        for k, v in fields.items():
            args.extend([k, v])
        result = self._execute(*args)
        return result if isinstance(result, str) else ""

    def xread(self, streams: Dict[str, str], count: Optional[int] = None, block: Optional[int] = None) -> List:
        args = ["XREAD"]
        if count:
            args.extend(["COUNT", str(count)])
        if block is not None:
            args.extend(["BLOCK", str(block)])
        args.append("STREAMS")
        args.extend(streams.keys())
        args.extend(streams.values())
        result = self._execute(*args)
        return result if isinstance(result, list) else []

    def xrange(self, name: str, min: str = "-", max: str = "+", count: Optional[int] = None) -> List:
        args = ["XRANGE", name, min, max]
        if count:
            args.extend(["COUNT", str(count)])
        result = self._execute(*args)
        return result if isinstance(result, list) else []

    def xrevrange(self, name: str, max: str = "+", min: str = "-", count: Optional[int] = None) -> List:
        args = ["XREVRANGE", name, max, min]
        if count:
            args.extend(["COUNT", str(count)])
        result = self._execute(*args)
        return result if isinstance(result, list) else []


class UpstashPubSub(BasePubSub):
    """
    Pub/Sub interface using Redis Streams.

    Simulates traditional pub/sub by polling streams.
    Each subscription tracks its last-read ID.
    """

    def __init__(self, client: UpstashRedisClient):
        self.client = client
        self.subscribed_channels: Set[str] = set()
        self.last_ids: Dict[str, str] = {}  # channel -> last read ID
        self._running = False
        self._message_queue: List[Dict] = []

    def subscribe(self, *channels: str) -> None:
        for channel in channels:
            self.subscribed_channels.add(channel)
            # Start from current time (don't get old messages)
            self.last_ids[channel] = f"{int(time.time() * 1000)}-0"

    def unsubscribe(self, *channels: str) -> None:
        for channel in channels:
            self.subscribed_channels.discard(channel)
            self.last_ids.pop(channel, None)

    def listen(self):
        """
        Generator that yields messages.

        Polls streams periodically since Upstash REST doesn't support
        long-polling XREAD BLOCK.
        """
        self._running = True

        while self._running:
            for message in self._poll_messages():
                yield message

            # Small delay between polls
            time.sleep(0.1)

    def get_message(self, timeout: float = 0.0) -> Optional[Dict]:
        """Get next message if available."""
        # Check queue first
        if self._message_queue:
            return self._message_queue.pop(0)

        # Poll for new messages
        messages = self._poll_messages()
        if messages:
            self._message_queue.extend(messages[1:])
            return messages[0]

        return None

    def _poll_messages(self) -> List[Dict]:
        """Poll all subscribed streams for new messages."""
        if not self.subscribed_channels:
            return []

        messages = []

        for channel in self.subscribed_channels:
            stream_key = f"{self.client.PUBSUB_STREAM_PREFIX}{channel}"
            last_id = self.last_ids.get(channel, "0")

            # Read new entries since last_id
            result = self.client.xrange(stream_key, f"({last_id}", "+", count=10)

            if result:
                for entry in result:
                    if not isinstance(entry, list) or len(entry) < 2:
                        continue

                    entry_id = entry[0]
                    fields = entry[1]

                    # Update last read ID
                    self.last_ids[channel] = entry_id

                    # Extract message from fields
                    msg_data = {}
                    for i in range(0, len(fields), 2):
                        msg_data[fields[i]] = fields[i + 1]

                    messages.append({
                        "type": "message",
                        "channel": channel,
                        "data": msg_data.get("message", ""),
                        "pattern": None
                    })

        return messages

    def close(self):
        """Stop listening."""
        self._running = False


# =============================================================================
# LOCAL REDIS WRAPPER (for compatibility)
# =============================================================================

class LocalRedisClient(BaseRedisClient):
    """
    Wrapper around local redis-py client.

    Provides same interface as UpstashRedisClient for consistency.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, **kwargs):
        try:
            import redis
            self._client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                **kwargs
            )
        except ImportError:
            raise ImportError("redis package required. Install with: pip install redis")

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        return self._client.set(key, value, ex=ex)

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return self._client.delete(*keys)

    def exists(self, *keys: str) -> int:
        if not keys:
            return 0
        return self._client.exists(*keys)

    def keys(self, pattern: str = "*") -> List[str]:
        return self._client.keys(pattern)

    def hset(self, name: str, mapping: Dict[str, str]) -> int:
        return self._client.hset(name, mapping=mapping)

    def hget(self, name: str, key: str) -> Optional[str]:
        return self._client.hget(name, key)

    def hgetall(self, name: str) -> Dict[str, str]:
        return self._client.hgetall(name)

    def hdel(self, name: str, *keys: str) -> int:
        if not keys:
            return 0
        return self._client.hdel(name, *keys)

    def rpush(self, name: str, *values: str) -> int:
        if not values:
            return 0
        return self._client.rpush(name, *values)

    def lpush(self, name: str, *values: str) -> int:
        if not values:
            return 0
        return self._client.lpush(name, *values)

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        return self._client.lrange(name, start, end)

    def lpop(self, name: str) -> Optional[str]:
        return self._client.lpop(name)

    def expire(self, name: str, time: int) -> bool:
        return self._client.expire(name, time)

    def ttl(self, name: str) -> int:
        return self._client.ttl(name)

    def publish(self, channel: str, message: str) -> int:
        return self._client.publish(channel, message)

    def pubsub(self) -> 'LocalPubSub':
        return LocalPubSub(self._client.pubsub())

    def xadd(self, name: str, fields: Dict[str, str], id: str = "*", maxlen: Optional[int] = None) -> str:
        return self._client.xadd(name, fields, id=id, maxlen=maxlen, approximate=True)

    def xread(self, streams: Dict[str, str], count: Optional[int] = None, block: Optional[int] = None) -> List:
        return self._client.xread(streams, count=count, block=block) or []

    def xrange(self, name: str, min: str = "-", max: str = "+", count: Optional[int] = None) -> List:
        return self._client.xrange(name, min=min, max=max, count=count) or []


class LocalPubSub(BasePubSub):
    """Wrapper around local redis pubsub."""

    def __init__(self, pubsub):
        self._pubsub = pubsub

    def subscribe(self, *channels: str) -> None:
        self._pubsub.subscribe(*channels)

    def unsubscribe(self, *channels: str) -> None:
        self._pubsub.unsubscribe(*channels)

    def listen(self):
        return self._pubsub.listen()

    def get_message(self, timeout: float = 0.0) -> Optional[Dict]:
        return self._pubsub.get_message(timeout=timeout)

    def close(self):
        self._pubsub.close()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_redis_client(
    prefer: Optional[str] = None,
    local_host: str = "localhost",
    local_port: int = 6379
) -> BaseRedisClient:
    """
    Get appropriate Redis client based on environment.

    Priority:
    1. If prefer="upstash", use Upstash (requires env vars)
    2. If prefer="local", use local Redis
    3. Auto-detect: Upstash env vars -> Local Redis

    Args:
        prefer: "upstash", "local", or None for auto-detect
        local_host: Host for local Redis
        local_port: Port for local Redis

    Returns:
        Redis client (Upstash or Local)

    Raises:
        ValueError: If preferred backend unavailable
    """
    # Explicit preference
    if prefer == "upstash":
        return UpstashRedisClient()
    elif prefer == "local":
        return LocalRedisClient(host=local_host, port=local_port)

    # Auto-detect
    if UPSTASH_REST_URL and UPSTASH_REST_TOKEN:
        try:
            client = UpstashRedisClient()
            if client.ping():
                return client
        except Exception:
            pass

    # Fall back to local
    try:
        client = LocalRedisClient(host=local_host, port=local_port)
        if client.ping():
            return client
    except Exception:
        pass

    raise ValueError(
        "No Redis connection available. Either:\n"
        "1. Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN for cloud Redis\n"
        "2. Start local Redis (docker-compose up -d)\n"
    )


def is_upstash_available() -> bool:
    """Check if Upstash credentials are configured."""
    return bool(UPSTASH_REST_URL and UPSTASH_REST_TOKEN)


def is_local_redis_available(host: str = "localhost", port: int = 6379) -> bool:
    """Check if local Redis is available."""
    try:
        client = LocalRedisClient(host=host, port=port)
        return client.ping()
    except Exception:
        return False


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upstash Redis Adapter")
    parser.add_argument("--test", action="store_true", help="Run connection test")
    parser.add_argument("--prefer", choices=["upstash", "local"], help="Preferred backend")
    parser.add_argument("--ping", action="store_true", help="Just ping")

    args = parser.parse_args()

    if args.ping:
        try:
            client = get_redis_client(prefer=args.prefer)
            if client.ping():
                print("[OK] Redis connection successful")
                print(f"Backend: {'Upstash' if isinstance(client, UpstashRedisClient) else 'Local'}")
            else:
                print("[FAIL] Ping failed")
        except Exception as e:
            print(f"[FAIL] {e}")

    elif args.test:
        print("Testing Redis Adapter...")
        print()

        # Check availability
        print(f"Upstash available: {is_upstash_available()}")
        print(f"Local Redis available: {is_local_redis_available()}")
        print()

        try:
            client = get_redis_client(prefer=args.prefer)
            backend = "Upstash" if isinstance(client, UpstashRedisClient) else "Local"
            print(f"Using backend: {backend}")
            print()

            # Test operations
            test_key = "popkit:test:adapter"

            # SET/GET
            client.set(test_key, "test_value", ex=60)
            value = client.get(test_key)
            assert value == "test_value", f"GET failed: {value}"
            print("[OK] SET/GET")

            # HSET/HGET
            hash_key = f"{test_key}:hash"
            client.hset(hash_key, {"field1": "value1", "field2": "value2"})
            h_value = client.hget(hash_key, "field1")
            assert h_value == "value1", f"HGET failed: {h_value}"
            print("[OK] HSET/HGET")

            # RPUSH/LRANGE
            list_key = f"{test_key}:list"
            client.rpush(list_key, "item1", "item2")
            items = client.lrange(list_key, 0, -1)
            assert len(items) == 2, f"LRANGE failed: {items}"
            print("[OK] RPUSH/LRANGE")

            # PUBLISH (stream-based)
            result = client.publish("test:channel", "test message")
            assert result > 0, "PUBLISH failed"
            print("[OK] PUBLISH (via streams)")

            # Cleanup
            client.delete(test_key, hash_key, list_key)
            print("[OK] DELETE")

            print()
            print("All tests passed!")

        except Exception as e:
            print(f"[FAIL] {e}")
            import traceback
            traceback.print_exc()

    else:
        parser.print_help()
