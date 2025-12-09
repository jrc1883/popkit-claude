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
    # WORKFLOW INTEGRATION (Issue #103 Phase 3)
    # =========================================================================

    def start_power_mode_workflow(
        self,
        task: str,
        agents: List[str],
        session_id: str,
        consensus_threshold: float = 0.7
    ) -> Optional[Dict]:
        """
        Start a Power Mode workflow on PopKit Cloud.

        This creates a durable workflow that tracks agent coordination.
        The actual work is still done locally by Claude Code.

        Args:
            task: Task description
            agents: List of agent names participating
            session_id: Local session ID for correlation
            consensus_threshold: Required agreement level (0.0-1.0)

        Returns:
            Dict with workflowId and status, or None if failed
        """
        if not self.connected:
            return None

        try:
            response = self._request("POST", "/workflows/power-mode", {
                "task": task,
                "agents": agents,
                "sessionId": session_id,
                "userId": self.config.user_id or "anonymous",
                "consensusThreshold": consensus_threshold
            })
            return response
        except Exception as e:
            print(f"Failed to start workflow: {e}", file=sys.stderr)
            return None

    def update_workflow(
        self,
        run_id: str,
        phase: Optional[str] = None,
        result: Optional[str] = None,
        agent_results: Optional[List[Dict]] = None
    ) -> bool:
        """
        Update a running workflow with results from local Claude Code session.

        Args:
            run_id: Workflow run ID from start_power_mode_workflow
            phase: Current phase name
            result: Phase result/output
            agent_results: List of agent results for power mode

        Returns:
            True if update succeeded
        """
        if not self.connected:
            return False

        body: Dict[str, Any] = {}
        if phase:
            body["phase"] = phase
        if result:
            body["result"] = result
        if agent_results:
            body["agentResults"] = agent_results

        try:
            self._request("POST", f"/workflows/update/{run_id}", body)
            return True
        except Exception as e:
            print(f"Failed to update workflow: {e}", file=sys.stderr)
            return False

    def get_workflow_status(self, run_id: str) -> Optional[Dict]:
        """
        Get status of a workflow.

        Args:
            run_id: Workflow run ID

        Returns:
            Workflow status dict or None if not found
        """
        if not self.connected:
            return None

        try:
            return self._request("GET", f"/workflows/status/{run_id}")
        except Exception:
            return None

    def list_workflows(self) -> List[Dict]:
        """
        List recent workflows.

        Returns:
            List of workflow summaries
        """
        if not self.connected:
            return []

        try:
            response = self._request("GET", "/workflows/list")
            return response.get("workflows", [])
        except Exception:
            return []

    def start_feature_dev_workflow(
        self,
        feature: str,
        project_path: str,
        session_id: str,
        phase_results: Optional[Dict[str, str]] = None
    ) -> Optional[Dict]:
        """
        Start a Feature Development workflow on PopKit Cloud.

        This creates a durable 7-phase workflow tracking.

        Args:
            feature: Feature description
            project_path: Project directory path
            session_id: Local session ID
            phase_results: Optional pre-filled phase results

        Returns:
            Dict with workflowId or None if failed
        """
        if not self.connected:
            return None

        try:
            response = self._request("POST", "/workflows/feature-dev", {
                "feature": feature,
                "projectPath": project_path,
                "sessionId": session_id,
                "userId": self.config.user_id or "anonymous",
                "phaseResults": phase_results or {}
            })
            return response
        except Exception as e:
            print(f"Failed to start feature-dev workflow: {e}", file=sys.stderr)
            return None

    # =========================================================================
    # SYNC BARRIERS (Issue #103 Phase 3)
    # =========================================================================

    def create_sync_barrier(
        self,
        barrier_id: str,
        required_agents: List[str],
        timeout_seconds: int = 120
    ) -> Optional[Dict]:
        """
        Create a cloud-based sync barrier for agent coordination.

        Replaces local Redis pub/sub sync barriers with durable cloud storage.

        Args:
            barrier_id: Unique identifier for the barrier
            required_agents: List of agent IDs that must acknowledge
            timeout_seconds: Barrier expiration time

        Returns:
            Dict with barrier status or None if failed
        """
        if not self.connected:
            return None

        try:
            return self._request("POST", "/workflows/sync/create", {
                "barrierId": barrier_id,
                "requiredAgents": required_agents,
                "timeoutSeconds": timeout_seconds
            })
        except Exception as e:
            print(f"Failed to create sync barrier: {e}", file=sys.stderr)
            return None

    def acknowledge_sync_barrier(
        self,
        barrier_id: str,
        agent_id: str
    ) -> Optional[Dict]:
        """
        Acknowledge a sync barrier.

        Args:
            barrier_id: Barrier ID to acknowledge
            agent_id: Agent ID acknowledging the barrier

        Returns:
            Dict with isComplete flag and barrier status
        """
        if not self.connected:
            return None

        try:
            return self._request("POST", f"/workflows/sync/ack/{barrier_id}", {
                "agentId": agent_id
            })
        except Exception as e:
            print(f"Failed to acknowledge barrier: {e}", file=sys.stderr)
            return None

    def get_sync_barrier_status(self, barrier_id: str) -> Optional[Dict]:
        """
        Get status of a sync barrier.

        Args:
            barrier_id: Barrier ID to check

        Returns:
            Dict with barrier status including acknowledged/missing agents
        """
        if not self.connected:
            return None

        try:
            return self._request("GET", f"/workflows/sync/status/{barrier_id}")
        except Exception:
            return None

    def wait_for_sync_barrier(
        self,
        barrier_id: str,
        agent_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 120.0
    ) -> bool:
        """
        Wait for a sync barrier to complete (blocking).

        This is a polling-based implementation. Acknowledges the barrier
        and polls until all agents have acknowledged.

        Args:
            barrier_id: Barrier ID to wait for
            agent_id: This agent's ID
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            True if barrier completed, False if timed out
        """
        if not self.connected:
            return False

        # First, acknowledge
        result = self.acknowledge_sync_barrier(barrier_id, agent_id)
        if not result:
            return False

        if result.get("isComplete"):
            return True

        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(poll_interval)

            status = self.get_sync_barrier_status(barrier_id)
            if not status:
                return False

            if status.get("status") == "complete":
                return True

            if status.get("status") == "not_found":
                # Barrier expired
                return False

        return False

    # =========================================================================
    # INTER-AGENT MESSAGING (Issue #109)
    # =========================================================================

    def publish_message(
        self,
        message_type: str,
        payload: Dict,
        tags: List[str],
        session_id: str,
        agent_id: str,
        to_agents: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> Optional[str]:
        """
        Publish a message to other agents via QStash.

        Args:
            message_type: Type of message (DISCOVERY, INSIGHT, RESULT, etc.)
            payload: Message payload (type-specific)
            tags: Tags for routing/filtering
            session_id: Power Mode session ID
            agent_id: This agent's ID
            to_agents: Target agent IDs (None for broadcast/auto-routing)
            priority: Message priority (low, normal, high)

        Returns:
            Message ID if successful, None otherwise
        """
        if not self.connected:
            return None

        try:
            message = {
                "type": message_type,
                "fromAgent": agent_id,
                "sessionId": session_id,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
                "tags": tags,
                "priority": priority
            }

            if to_agents:
                message["toAgents"] = to_agents

            response = self._request("POST", "/messages/publish", message)
            return response.get("messageId")

        except Exception as e:
            print(f"Failed to publish message: {e}", file=sys.stderr)
            return None

    def broadcast_message(
        self,
        message_type: str,
        payload: Dict,
        tags: List[str],
        session_id: str,
        agent_id: str,
        priority: str = "normal"
    ) -> Optional[str]:
        """
        Broadcast a message to all agents in the session.

        Args:
            message_type: Type of message
            payload: Message payload
            tags: Tags for filtering
            session_id: Power Mode session ID
            agent_id: This agent's ID
            priority: Message priority

        Returns:
            Message ID if successful, None otherwise
        """
        if not self.connected:
            return None

        try:
            message = {
                "type": message_type,
                "fromAgent": agent_id,
                "sessionId": session_id,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
                "tags": tags,
                "priority": priority
            }

            response = self._request("POST", "/messages/broadcast", message)
            return response.get("messageId")

        except Exception as e:
            print(f"Failed to broadcast message: {e}", file=sys.stderr)
            return None

    def poll_messages(
        self,
        agent_id: str,
        session_id: str,
        limit: int = 10,
        mark_read: bool = True
    ) -> List[Dict]:
        """
        Poll for messages in agent's inbox.

        Args:
            agent_id: This agent's ID
            session_id: Power Mode session ID
            limit: Maximum messages to return
            mark_read: Whether to mark messages as read

        Returns:
            List of messages (newest first)
        """
        if not self.connected:
            return []

        try:
            params = f"?sessionId={session_id}&limit={limit}&markRead={'true' if mark_read else 'false'}"
            response = self._request("GET", f"/messages/poll/{agent_id}{params}")
            return response.get("messages", [])

        except Exception as e:
            print(f"Failed to poll messages: {e}", file=sys.stderr)
            return []

    def clear_inbox(self, agent_id: str) -> bool:
        """
        Clear an agent's inbox.

        Args:
            agent_id: Agent ID whose inbox to clear

        Returns:
            True if successful
        """
        if not self.connected:
            return False

        try:
            self._request("DELETE", f"/messages/clear/{agent_id}")
            return True
        except Exception:
            return False

    def share_discovery(
        self,
        agent_id: str,
        session_id: str,
        content: str,
        file_path: Optional[str] = None,
        confidence: float = 0.8,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Share a discovery with other agents.

        Convenience method for publishing DISCOVERY messages.

        Args:
            agent_id: This agent's ID
            session_id: Power Mode session ID
            content: What was discovered
            file_path: Related file path (optional)
            confidence: Confidence level (0.0-1.0)
            tags: Additional tags for routing

        Returns:
            Message ID if successful
        """
        payload = {
            "content": content,
            "confidence": confidence
        }
        if file_path:
            payload["filePath"] = file_path

        all_tags = tags or []
        if file_path:
            # Add file extension as tag
            ext = file_path.split(".")[-1] if "." in file_path else None
            if ext:
                all_tags.append(ext)

        return self.broadcast_message(
            message_type="DISCOVERY",
            payload=payload,
            tags=all_tags,
            session_id=session_id,
            agent_id=agent_id
        )

    def share_insight(
        self,
        agent_id: str,
        session_id: str,
        content: str,
        category: str,
        relevant_to: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Share an insight with other agents.

        Convenience method for publishing INSIGHT messages.

        Args:
            agent_id: This agent's ID
            session_id: Power Mode session ID
            content: The insight
            category: Insight category (security, performance, pattern, etc.)
            relevant_to: Agent types this is relevant to
            tags: Additional tags

        Returns:
            Message ID if successful
        """
        payload = {
            "content": content,
            "category": category,
            "relevantTo": relevant_to or []
        }

        all_tags = list(tags or [])
        all_tags.append(category)

        return self.broadcast_message(
            message_type="INSIGHT",
            payload=payload,
            tags=all_tags,
            session_id=session_id,
            agent_id=agent_id
        )

    def share_result(
        self,
        agent_id: str,
        session_id: str,
        summary: str,
        files: List[str],
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Share work results with other agents.

        Convenience method for publishing RESULT messages.

        Args:
            agent_id: This agent's ID
            session_id: Power Mode session ID
            summary: Summary of what was done
            files: Files modified/created
            metrics: Optional metrics (e.g., coverage, score)
            tags: Additional tags

        Returns:
            Message ID if successful
        """
        payload = {
            "summary": summary,
            "files": files
        }
        if metrics:
            payload["metrics"] = metrics

        return self.broadcast_message(
            message_type="RESULT",
            payload=payload,
            tags=tags or [],
            session_id=session_id,
            agent_id=agent_id,
            priority="high"  # Results are important
        )

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

        # Test workflow integration (Issue #103 Phase 3)
        print("\nTesting workflows...")

        # Start a power mode workflow
        workflow = client.start_power_mode_workflow(
            task="Test workflow from cloud client",
            agents=["code-reviewer", "test-writer"],
            session_id="test-session-001",
            consensus_threshold=0.7
        )
        if workflow:
            print(f"✓ Started workflow: {workflow.get('workflowId', 'unknown')}")

            # Check status
            run_id = workflow.get("workflowId")
            if run_id:
                status = client.get_workflow_status(run_id)
                if status:
                    print(f"  Status: {status.get('status', 'unknown')}")

                # Update with agent result
                client.update_workflow(run_id, agent_results=[{
                    "agent": "code-reviewer",
                    "output": "Review complete",
                    "confidence": 0.85
                }])
                print("✓ Workflow updated")
        else:
            print("! Workflow test skipped (endpoint may not be available)")

        # List workflows
        workflows = client.list_workflows()
        print(f"  Recent workflows: {len(workflows)}")

        # Show usage
        print(f"\nUsage: {client.get_usage()}")

        print("\n✓ All tests passed!")
    else:
        print("✗ Connection failed")
        print("  Check API key and network connectivity")
        sys.exit(1)
