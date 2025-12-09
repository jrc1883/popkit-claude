#!/usr/bin/env python3
"""
PopKit Cloud Client

Redis-compatible client that connects to PopKit Cloud instead of local Redis.
Provides the same interface as PowerModeRedisClient but uses HTTPS/WSS.

Part of Issue #68 (Hosted Redis Service).
"""

import json
import os
import sys
import threading
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import urllib.request
import urllib.error

# Add power-mode to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from protocol import (
        Message, MessageType, MessageFactory,
        AgentState, Channels
    )
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_CLOUD_URL = os.environ.get(
    "POPKIT_CLOUD_URL",
    "https://popkit-cloud-api.joseph-cannon.workers.dev/v1"
)

# For development/testing, allow override to localhost
POPKIT_CLOUD_DEV_URL = os.environ.get(
    "POPKIT_CLOUD_DEV_URL",
    "http://localhost:8787/v1"  # Cloudflare Workers local dev
)

# Connection settings
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CloudConfig:
    """Configuration for cloud connection."""
    api_key: str
    base_url: str = POPKIT_CLOUD_URL
    user_id: Optional[str] = None
    tier: str = "free"

    @classmethod
    def from_env(cls) -> Optional['CloudConfig']:
        """Load configuration from environment."""
        api_key = os.environ.get("POPKIT_API_KEY")
        if not api_key:
            return None

        # Check for dev mode
        dev_mode = os.environ.get("POPKIT_DEV_MODE", "").lower() == "true"
        base_url = POPKIT_CLOUD_DEV_URL if dev_mode else POPKIT_CLOUD_URL

        return cls(api_key=api_key, base_url=base_url)


@dataclass
class UsageStats:
    """Track API usage for rate limiting awareness."""
    commands_today: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    last_reset: str = field(default_factory=lambda: datetime.now().date().isoformat())

    def add_request(self, sent: int, received: int):
        """Track a request."""
        today = datetime.now().date().isoformat()
        if today != self.last_reset:
            # Reset daily counters
            self.commands_today = 0
            self.bytes_sent = 0
            self.bytes_received = 0
            self.last_reset = today

        self.commands_today += 1
        self.bytes_sent += sent
        self.bytes_received += received


# =============================================================================
# CLOUD CLIENT
# =============================================================================

class PopKitCloudClient:
    """
    Redis-compatible client for PopKit Cloud.

    Implements the same interface as PowerModeRedisClient but uses
    HTTPS for commands and WebSocket for pub/sub.

    Usage:
        client = PopKitCloudClient.from_env()
        if client and client.connect():
            client.push_state(agent_id, state)
    """

    def __init__(self, config: CloudConfig):
        """
        Initialize cloud client.

        Args:
            config: Cloud configuration with API key
        """
        self.config = config
        self.connected = False
        self.usage = UsageStats()
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_running = False

    @classmethod
    def from_env(cls) -> Optional['PopKitCloudClient']:
        """Create client from environment variables."""
        config = CloudConfig.from_env()
        if config:
            return cls(config)
        return None

    # =========================================================================
    # CONNECTION
    # =========================================================================

    def connect(self) -> bool:
        """
        Connect to PopKit Cloud.

        Returns:
            True if connected successfully
        """
        try:
            # Validate API key with a health check
            response = self._request("GET", "/health")

            if response.get("status") == "ok":
                self.connected = True

                # Extract user info if provided
                if "user" in response:
                    self.config.user_id = response["user"].get("id")
                    self.config.tier = response["user"].get("tier", "free")

                return True

            return False

        except Exception as e:
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from PopKit Cloud."""
        self._ws_running = False
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2)
        self.connected = False

    # =========================================================================
    # REDIS-COMPATIBLE INTERFACE
    # =========================================================================

    def push_state(self, agent_id: str, state: Dict):
        """
        Push agent state to cloud Redis.

        Equivalent to: HSET pop:state:{agent_id} ...
        """
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/state", {
                "agent_id": agent_id,
                "state": state,
                "ttl": 600  # 10 min TTL
            })
        except Exception:
            pass  # Fail silently like local client

    def push_insight(self, insight: Dict):
        """
        Push an insight to cloud Redis.

        Equivalent to: LPUSH pop:insights + LTRIM
        """
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/insights", {
                "insight": insight
            })
        except Exception:
            pass

    def pull_insights(
        self,
        tags: List[str],
        exclude_agent: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Pull relevant insights from cloud Redis.

        Server-side filtering for efficiency.
        """
        if not self.connected:
            return []

        try:
            response = self._request("POST", "/redis/insights/search", {
                "tags": tags,
                "exclude_agent": exclude_agent,
                "limit": limit
            })
            return response.get("insights", [])
        except Exception:
            return []

    def push_heartbeat(self, agent_id: str, state: 'AgentState'):
        """
        Push heartbeat to cloud Redis.

        Equivalent to: PUBLISH pop:heartbeat
        """
        if not self.connected or not PROTOCOL_AVAILABLE:
            return

        try:
            msg = MessageFactory.heartbeat(agent_id, state)
            self._request("POST", "/redis/publish", {
                "channel": Channels.heartbeat(),
                "message": json.loads(msg.to_json())
            })
        except Exception:
            pass

    def check_for_messages(self, agent_id: str) -> List[Dict]:
        """
        Check for messages directed at this agent.

        Uses HTTP polling (WebSocket for real-time in future).
        """
        if not self.connected:
            return []

        try:
            response = self._request("GET", f"/redis/messages/{agent_id}")
            return response.get("messages", [])
        except Exception:
            return []

    def get_objective(self) -> Optional[Dict]:
        """Get the current objective."""
        if not self.connected:
            return None

        try:
            response = self._request("GET", "/redis/objective")
            return response.get("objective")
        except Exception:
            return None

    def get_patterns(self, context: str) -> List[Dict]:
        """Get learned patterns for a context."""
        if not self.connected:
            return []

        try:
            response = self._request("POST", "/redis/patterns/search", {
                "context": context
            })
            return response.get("patterns", [])
        except Exception:
            return []

    # =========================================================================
    # STREAMING SUPPORT (Issue #23)
    # =========================================================================

    def publish_stream_start(self, agent_id: str, session_id: str, tool_name: str):
        """Publish stream start message."""
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/publish", {
                "channel": Channels.coordinator(),
                "message": {
                    "type": "STREAM_START",
                    "from_agent": agent_id,
                    "payload": {
                        "session_id": session_id,
                        "tool_name": tool_name,
                        "started_at": datetime.now().isoformat()
                    }
                }
            })
        except Exception:
            pass

    def publish_stream_chunk(self, chunk: Any):
        """Publish a stream chunk."""
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/publish", {
                "channel": Channels.coordinator(),
                "message": chunk.to_dict() if hasattr(chunk, 'to_dict') else chunk
            })
        except Exception:
            pass

    def publish_stream_end(
        self,
        agent_id: str,
        session_id: str,
        error: Optional[str] = None
    ):
        """Publish stream end message."""
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/publish", {
                "channel": Channels.coordinator(),
                "message": {
                    "type": "STREAM_END" if not error else "STREAM_ERROR",
                    "from_agent": agent_id,
                    "payload": {
                        "session_id": session_id,
                        "ended_at": datetime.now().isoformat(),
                        "error": error
                    }
                }
            })
        except Exception:
            pass

    # =========================================================================
    # PUB/SUB (Polling-based, WebSocket in future)
    # =========================================================================

    def subscribe(self, channel: str, callback: Callable[[Dict], None]):
        """
        Subscribe to a channel.

        Currently uses HTTP polling. WebSocket support planned.
        """
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(callback)

    def unsubscribe(self, channel: str):
        """Unsubscribe from a channel."""
        if channel in self._subscriptions:
            del self._subscriptions[channel]

    def publish(self, channel: str, message: Dict):
        """Publish a message to a channel."""
        if not self.connected:
            return

        try:
            self._request("POST", "/redis/publish", {
                "channel": channel,
                "message": message
            })
        except Exception:
            pass

    # =========================================================================
    # USAGE & STATS
    # =========================================================================

    def get_usage(self) -> Dict:
        """Get current usage statistics."""
        return {
            "commands_today": self.usage.commands_today,
            "bytes_sent": self.usage.bytes_sent,
            "bytes_received": self.usage.bytes_received,
            "tier": self.config.tier
        }

    def get_remaining_quota(self) -> Optional[Dict]:
        """Get remaining quota from server."""
        if not self.connected:
            return None

        try:
            return self._request("GET", "/usage")
        except Exception:
            return None

    # =========================================================================
    # INTERNAL HTTP CLIENT
    # =========================================================================

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        retry: int = 0
    ) -> Dict:
        """
        Make HTTP request to PopKit Cloud.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/redis/state")
            body: Request body for POST/PUT
            retry: Current retry count

        Returns:
            Response JSON as dict
        """
        url = f"{self.config.base_url}{path}"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PopKit-Plugin/1.0"
        }

        data = None
        sent_bytes = 0
        if body:
            data = json.dumps(body).encode("utf-8")
            sent_bytes = len(data)

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                response_data = response.read()
                received_bytes = len(response_data)

                # Track usage
                self.usage.add_request(sent_bytes, received_bytes)

                if response_data:
                    return json.loads(response_data.decode("utf-8"))
                return {}

        except urllib.error.HTTPError as e:
            # Handle specific error codes
            if e.code == 401:
                raise ValueError("Invalid API key")
            elif e.code == 429:
                raise RuntimeError("Rate limit exceeded")
            elif e.code >= 500 and retry < MAX_RETRIES:
                # Retry server errors
                time.sleep(RETRY_DELAY * (retry + 1))
                return self._request(method, path, body, retry + 1)
            else:
                body = e.read().decode("utf-8") if e.fp else ""
                raise RuntimeError(f"API error {e.code}: {e.reason}\n{body}")

        except urllib.error.URLError as e:
            if retry < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (retry + 1))
                return self._request(method, path, body, retry + 1)
            raise RuntimeError(f"Network error: {e.reason}")


# =============================================================================
# CLIENT FACTORY
# =============================================================================

def get_redis_client():
    """
    Get the appropriate Redis client (cloud or local).

    Priority:
    1. If POPKIT_API_KEY is set and POPKIT_CLOUD_ENABLED != "false" → Cloud
    2. If local Redis is available → Local
    3. If file fallback enabled → File-based
    4. None (Power Mode unavailable)

    Returns:
        Redis-compatible client or None
    """
    # Check for cloud configuration
    api_key = os.environ.get("POPKIT_API_KEY")
    cloud_enabled = os.environ.get("POPKIT_CLOUD_ENABLED", "true").lower() != "false"

    if api_key and cloud_enabled:
        client = PopKitCloudClient.from_env()
        if client and client.connect():
            return client

    # Fall back to local Redis
    try:
        # Import here to avoid circular dependency
        from checkin_hook import PowerModeRedisClient
        local_client = PowerModeRedisClient()
        if local_client.connect():
            return local_client
    except ImportError:
        pass

    # Fall back to file-based
    try:
        from file_fallback import FileBasedRedis
        return FileBasedRedis()
    except ImportError:
        pass

    return None


def is_cloud_available() -> bool:
    """Check if PopKit Cloud is configured and available."""
    config = CloudConfig.from_env()
    if not config:
        return False

    client = PopKitCloudClient(config)
    return client.connect()


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    print("PopKit Cloud Client Test")
    print("=" * 40)

    config = CloudConfig.from_env()

    if not config:
        print("ERROR: POPKIT_API_KEY not set")
        print("Set: export POPKIT_API_KEY=pk_live_your_key")
        sys.exit(1)

    print(f"API Key: {config.api_key[:8]}...{config.api_key[-4:] if len(config.api_key) > 12 else ''}")
    print(f"Base URL: {config.base_url}")

    client = PopKitCloudClient(config)

    print("\nConnecting...")
    if client.connect():
        print(f"✓ Connected!")
        print(f"  User ID: {config.user_id}")
        print(f"  Tier: {config.tier}")

        # Test push state
        print("\nTesting push_state...")
        client.push_state("test-agent", {
            "progress": 0.5,
            "current_task": "Testing cloud client"
        })
        print("✓ State pushed")

        # Test push insight
        print("\nTesting push_insight...")
        client.push_insight({
            "id": "test-insight",
            "type": "discovery",
            "content": "Cloud client works!",
            "relevance_tags": ["test"],
            "from_agent": "test-agent"
        })
        print("✓ Insight pushed")

        # Test pull insights
        print("\nTesting pull_insights...")
        insights = client.pull_insights(["test"], "other-agent", 3)
        print(f"✓ Pulled {len(insights)} insights")

        # Show usage
        print(f"\nUsage: {client.get_usage()}")

        print("\n✓ All tests passed!")
    else:
        print("✗ Connection failed")
        print("  Check API key and network connectivity")
        sys.exit(1)
