#!/usr/bin/env python3
"""
Pop Power Mode Check-In Hook
PostToolUse hook that enables periodic agent check-ins via Redis pub/sub.

This hook fires after every tool use and:
1. Tracks tool call count
2. At intervals, pushes agent state to Redis
3. Pulls relevant insights from other agents
4. Checks for drift from objective
5. Injects context for the agent's next action
"""

import json
import sys
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add power-mode to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from protocol import (
        Message, MessageType, MessageFactory,
        AgentState, AgentIdentity, Insight, InsightType,
        Channels, Guardrails, StreamChunk
    )
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False

try:
    from stream_manager import StreamManager, get_manager
    STREAM_MANAGER_AVAILABLE = True
except ImportError:
    STREAM_MANAGER_AVAILABLE = False

try:
    from insight_embedder import InsightEmbedder
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

try:
    # Bug detector from hooks/utils
    import sys
    hooks_utils = Path(__file__).parent.parent / "hooks" / "utils"
    sys.path.insert(0, str(hooks_utils))
    from bug_detector import BugDetector, format_detection_result
    BUG_DETECTOR_AVAILABLE = True
except ImportError:
    BUG_DETECTOR_AVAILABLE = False

try:
    from pattern_client import PatternClient
    PATTERN_CLIENT_AVAILABLE = True
except ImportError:
    PATTERN_CLIENT_AVAILABLE = False

try:
    from logger import get_logger, log_checkin, log_info, log_error
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False
    # Stubs if logger not available
    def get_logger(session_id=None): return None
    def log_checkin(agent_id, state): pass
    def log_info(agent_id, message, details=None): pass
    def log_error(agent_id, message, details=None): pass

try:
    # Efficiency tracker from hooks/utils
    from efficiency_tracker import get_tracker as get_efficiency_tracker
    EFFICIENCY_TRACKER_AVAILABLE = True
except ImportError:
    try:
        # Try alternate import path
        efficiency_utils = Path(__file__).parent.parent / "hooks" / "utils"
        sys.path.insert(0, str(efficiency_utils))
        from efficiency_tracker import get_tracker as get_efficiency_tracker
        EFFICIENCY_TRACKER_AVAILABLE = True
    except ImportError:
        EFFICIENCY_TRACKER_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config() -> Dict:
    """Load power mode configuration."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


CONFIG = load_config()


def get_git_root() -> Optional[Path]:
    """Get the git repository root directory.

    Returns:
        Path to git root, or None if not in a git repo.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_project_root() -> Path:
    """Get project root directory (Issue #66 - bug fix).

    Priority:
    1. Git repository root (most reliable)
    2. Directory containing .claude/
    3. Current working directory (fallback)

    Returns:
        Path to project root.
    """
    # Try git root first
    git_root = get_git_root()
    if git_root:
        return git_root

    # Look for .claude directory walking up from cwd
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".claude").exists():
            return parent

    # Fallback to cwd
    return cwd


def generate_session_id() -> str:
    """Generate a stable session ID (Issue #66 - bug fix).

    Uses git HEAD hash + date for consistency across agents.
    Falls back to timestamp-only if not in a git repo.

    Returns:
        8-character session ID.
    """
    import subprocess

    # Try to get git HEAD hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
            # Combine with date (not time) for daily session stability
            date_str = datetime.now().strftime("%Y%m%d")
            return hashlib.md5(f"{git_hash}-{date_str}".encode()).hexdigest()[:8]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: timestamp-based
    return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]


# =============================================================================
# STATE TRACKER
# =============================================================================

class AgentStateTracker:
    """
    Tracks agent state across tool calls.
    Uses a local file for persistence within a session.
    Prefers project-local state file for status line integration.
    """

    HOME_STATE_FILE = Path.home() / ".claude" / "popkit" / "power-mode-state.json"

    def __init__(self, agent_id: str, agent_name: str, session_id: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.session_id = session_id

        # Determine state file path (project-local preferred)
        self.STATE_FILE = self._get_state_file_path()

        # Load or initialize state
        self.state = self._load_state()

    def _get_state_file_path(self) -> Path:
        """Get path to power mode state file (Issue #66 - bug fix).

        Uses get_project_root() instead of Path.cwd() for consistency.
        This ensures state persists correctly when cwd changes.
        """
        project_root = get_project_root()
        local_state = project_root / ".claude" / "popkit" / "power-mode-state.json"

        # Try project-local first
        if local_state.exists():
            return local_state

        # Check if project .claude/popkit directory exists (create state there)
        local_popkit_dir = project_root / ".claude" / "popkit"
        if local_popkit_dir.exists():
            return local_state

        # Fall back to home directory
        return self.HOME_STATE_FILE

    def _load_state(self) -> Dict:
        """Load state from file or create new.

        Merges agent tracking data with existing Power Mode state if present.
        """
        existing_state = {}
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE) as f:
                    existing_state = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # If existing state has same session, return agent tracking portion
        if existing_state.get("session_id") == self.session_id:
            # Merge: keep Power Mode fields, return agent tracking fields
            return {
                # Agent tracking fields
                "agent_id": existing_state.get("agent_id", self.agent_id),
                "agent_name": existing_state.get("agent_name", self.agent_name),
                "session_id": self.session_id,
                "tool_call_count": existing_state.get("tool_call_count", 0),
                "files_touched": existing_state.get("files_touched", []),
                "tools_used": existing_state.get("tools_used", []),
                "decisions": existing_state.get("decisions", []),
                "blockers": existing_state.get("blockers", []),
                "progress": existing_state.get("progress", 0.0),
                "current_task": existing_state.get("current_task", ""),
                "last_checkin": existing_state.get("last_checkin"),
                "insights_received": existing_state.get("insights_received", []),
                "insights_shared": existing_state.get("insights_shared", []),
                # Streaming fields (Issue #23)
                "active_streams": existing_state.get("active_streams", {}),
                "completed_streams": existing_state.get("completed_streams", 0),
                "total_stream_chunks": existing_state.get("total_stream_chunks", 0),
                "total_stream_bytes": existing_state.get("total_stream_bytes", 0)
            }

        # New state (agent tracking portion only)
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "tool_call_count": 0,
            "files_touched": [],
            "tools_used": [],
            "decisions": [],
            "blockers": [],
            "progress": 0.0,
            "current_task": "",
            "last_checkin": None,
            "insights_received": [],
            "insights_shared": [],
            # Streaming fields (Issue #23)
            "active_streams": {},
            "completed_streams": 0,
            "total_stream_chunks": 0,
            "total_stream_bytes": 0
        }

    def _save_state(self):
        """Save state to file.

        Merges agent tracking data with existing Power Mode state to preserve
        status line fields (active, current_phase, phase_index, etc.).
        """
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state to preserve Power Mode fields
        existing_state = {}
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE) as f:
                    existing_state = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Merge: preserve Power Mode fields, update agent tracking fields
        merged_state = existing_state.copy()
        merged_state.update(self.state)

        # Preserve Power Mode status line fields from existing state
        power_mode_fields = [
            "active", "activated_at", "source", "active_issue",
            "current_phase", "phase_index", "total_phases", "phases_completed", "config"
        ]
        for field in power_mode_fields:
            if field in existing_state:
                merged_state[field] = existing_state[field]

        with open(self.STATE_FILE, "w") as f:
            json.dump(merged_state, f, indent=2)

    def record_tool_use(self, tool_name: str, tool_input: Dict, tool_result: Any):
        """Record a tool use."""
        self.state["tool_call_count"] += 1

        # Track tool
        if tool_name not in self.state["tools_used"]:
            self.state["tools_used"].append(tool_name)

        # Track files
        if file_path := tool_input.get("file_path"):
            if file_path not in self.state["files_touched"]:
                self.state["files_touched"].append(file_path)

        self._save_state()

    def record_decision(self, decision: str, reasoning: str, confidence: float):
        """Record a decision made by the agent."""
        self.state["decisions"].append({
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        self._save_state()

    def record_blocker(self, blocker: str):
        """Record a blocker encountered."""
        if blocker not in self.state["blockers"]:
            self.state["blockers"].append(blocker)
        self._save_state()

    def update_progress(self, progress: float):
        """Update progress (0.0 to 1.0)."""
        self.state["progress"] = max(0.0, min(1.0, progress))
        self._save_state()

    def set_current_task(self, task: str):
        """Set the current task description."""
        self.state["current_task"] = task
        self._save_state()

    def record_checkin(self):
        """Record that a check-in occurred."""
        self.state["last_checkin"] = datetime.now().isoformat()
        self._save_state()

    def record_insight_received(self, insight_id: str):
        """Record an insight received from another agent."""
        if insight_id not in self.state["insights_received"]:
            self.state["insights_received"].append(insight_id)
        self._save_state()

    def record_insight_shared(self, insight_id: str):
        """Record an insight shared with other agents."""
        if insight_id not in self.state["insights_shared"]:
            self.state["insights_shared"].append(insight_id)
        self._save_state()

    # =========================================================================
    # STREAMING METHODS (Issue #23)
    # =========================================================================

    def start_stream(self, session_id: str, tool_name: str):
        """Record start of a streaming session."""
        self.state["active_streams"][session_id] = {
            "tool_name": tool_name,
            "started_at": datetime.now().isoformat(),
            "chunks": 0,
            "bytes": 0
        }
        self._save_state()

    def record_stream_chunk(self, session_id: str, content: str):
        """Record a streaming chunk."""
        if session_id in self.state["active_streams"]:
            self.state["active_streams"][session_id]["chunks"] += 1
            self.state["active_streams"][session_id]["bytes"] += len(content)
            self.state["total_stream_chunks"] += 1
            self.state["total_stream_bytes"] += len(content)
            self._save_state()

    def end_stream(self, session_id: str, error: Optional[str] = None):
        """Record end of a streaming session."""
        if session_id in self.state["active_streams"]:
            stream_info = self.state["active_streams"].pop(session_id)
            self.state["completed_streams"] += 1
            if error:
                self.record_blocker(f"Stream error ({session_id}): {error}")
            self._save_state()
            return stream_info
        return None

    def get_active_stream_count(self) -> int:
        """Get count of active streams."""
        return len(self.state.get("active_streams", {}))

    def get_stream_stats(self) -> Dict:
        """Get streaming statistics."""
        return {
            "active_streams": len(self.state.get("active_streams", {})),
            "completed_streams": self.state.get("completed_streams", 0),
            "total_chunks": self.state.get("total_stream_chunks", 0),
            "total_bytes": self.state.get("total_stream_bytes", 0)
        }

    def should_checkin(self) -> bool:
        """Check if it's time for a check-in."""
        interval = CONFIG.get("intervals", {}).get("checkin_every_n_tools", 5)
        return self.state["tool_call_count"] % interval == 0

    def get_tool_call_count(self) -> int:
        """Get current tool call count."""
        return self.state["tool_call_count"]

    def to_agent_state(self) -> AgentState:
        """Convert to AgentState for protocol."""
        if not PROTOCOL_AVAILABLE:
            return None

        identity = AgentIdentity(
            id=self.agent_id,
            name=self.agent_name,
            session_id=self.session_id
        )

        return AgentState(
            agent=identity,
            progress=self.state["progress"],
            current_task=self.state["current_task"],
            files_touched=self.state["files_touched"],
            tools_used=self.state["tools_used"],
            tool_call_count=self.state["tool_call_count"],
            decisions=self.state["decisions"],
            blockers=self.state["blockers"]
        )


# =============================================================================
# REDIS CLIENT
# =============================================================================

class PowerModeRedisClient:
    """Redis client for power mode operations."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            return False

        try:
            redis_config = CONFIG.get("redis", {})
            self.redis = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                socket_timeout=redis_config.get("socket_timeout", 5),
                decode_responses=True
            )
            self.redis.ping()
            self.connected = True
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            self.connected = False
            return False

    def push_state(self, agent_id: str, state: Dict):
        """Push agent state to Redis (Issue #66 - bug fix).

        Properly handles None values to prevent "None" string in Redis.
        """
        if not self.connected:
            return

        key = f"pop:state:{agent_id}"

        # Serialize values properly, handling None (Issue #66)
        def serialize_value(v):
            if v is None:
                return json.dumps(None)  # Becomes JSON "null"
            elif isinstance(v, (dict, list)):
                return json.dumps(v)
            elif isinstance(v, bool):
                return json.dumps(v)  # "true"/"false" not "True"/"False"
            else:
                return str(v)

        self.redis.hset(key, mapping={
            k: serialize_value(v)
            for k, v in state.items()
        })
        self.redis.expire(key, 600)  # 10 min TTL

    def push_insight(self, insight: Dict):
        """Push an insight to Redis."""
        if not self.connected:
            return

        self.redis.lpush("pop:insights", json.dumps(insight))
        self.redis.ltrim("pop:insights", 0, 99)  # Keep last 100

    def pull_insights(self, tags: List[str], exclude_agent: str, limit: int = 3) -> List[Dict]:
        """Pull relevant insights from Redis."""
        if not self.connected:
            return []

        insights = []
        all_insights = self.redis.lrange("pop:insights", 0, 99)

        for insight_json in all_insights:
            try:
                insight = json.loads(insight_json)

                # Skip own insights
                if insight.get("from_agent") == exclude_agent:
                    continue

                # Check tag relevance
                insight_tags = set(insight.get("relevance_tags", []))
                if insight_tags & set(tags):
                    insights.append(insight)
                    if len(insights) >= limit:
                        break

            except json.JSONDecodeError:
                continue

        return insights

    def push_heartbeat(self, agent_id: str, state: AgentState):
        """Push heartbeat to Redis."""
        if not self.connected or not PROTOCOL_AVAILABLE:
            return

        msg = MessageFactory.heartbeat(agent_id, state)
        self.redis.publish(Channels.heartbeat(), msg.to_json())

    def check_for_messages(self, agent_id: str) -> List[Dict]:
        """Check for messages directed at this agent."""
        if not self.connected:
            return []

        messages = []
        channel = f"pop:agent:{agent_id}"

        # Use a short-lived pubsub to check for messages
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)

        # Get any pending messages (non-blocking)
        while True:
            msg = pubsub.get_message(timeout=0.1)
            if msg is None:
                break
            if msg["type"] == "message":
                try:
                    messages.append(json.loads(msg["data"]))
                except json.JSONDecodeError:
                    pass

        pubsub.unsubscribe()
        return messages

    def get_objective(self) -> Optional[Dict]:
        """Get the current objective."""
        if not self.connected:
            return None

        obj_json = self.redis.get("pop:objective")
        if obj_json:
            try:
                return json.loads(obj_json)
            except json.JSONDecodeError:
                pass
        return None

    def get_patterns(self, context: str) -> List[Dict]:
        """Get learned patterns for a context."""
        if not self.connected:
            return []

        patterns = []
        all_patterns = self.redis.hgetall("pop:patterns") or {}

        for pattern_id, pattern_json in all_patterns.items():
            try:
                pattern = json.loads(pattern_json)
                if context.lower() in pattern.get("context", "").lower():
                    patterns.append(pattern)
            except json.JSONDecodeError:
                continue

        return patterns

    # =========================================================================
    # STREAMING METHODS (Issue #23)
    # =========================================================================

    def publish_stream_start(self, agent_id: str, session_id: str, tool_name: str):
        """Publish stream start message."""
        if not self.connected or not PROTOCOL_AVAILABLE:
            return

        msg = Message(
            id=hashlib.md5(f"stream-start-{session_id}".encode()).hexdigest()[:12],
            type=MessageType.STREAM_START,
            from_agent=agent_id,
            to_agent="coordinator",
            payload={
                "session_id": session_id,
                "tool_name": tool_name,
                "started_at": datetime.now().isoformat()
            }
        )
        self.redis.publish(Channels.coordinator(), msg.to_json())

    def publish_stream_chunk(self, chunk: 'StreamChunk'):
        """Publish a stream chunk."""
        if not self.connected or not PROTOCOL_AVAILABLE:
            return

        msg = chunk.to_message()
        self.redis.publish(Channels.coordinator(), msg.to_json())

    def publish_stream_end(self, agent_id: str, session_id: str, error: Optional[str] = None):
        """Publish stream end message."""
        if not self.connected or not PROTOCOL_AVAILABLE:
            return

        msg = Message(
            id=hashlib.md5(f"stream-end-{session_id}".encode()).hexdigest()[:12],
            type=MessageType.STREAM_END if not error else MessageType.STREAM_ERROR,
            from_agent=agent_id,
            to_agent="coordinator",
            payload={
                "session_id": session_id,
                "ended_at": datetime.now().isoformat(),
                "error": error
            }
        )
        self.redis.publish(Channels.coordinator(), msg.to_json())


# =============================================================================
# INSIGHT EXTRACTOR
# =============================================================================

class InsightExtractor:
    """Extracts insights from tool results."""

    # Patterns that indicate discoveries
    DISCOVERY_PATTERNS = [
        ("found", "discovery"),
        ("exists", "discovery"),
        ("located", "discovery"),
        ("discovered", "discovery"),
        ("using", "pattern"),
        ("convention", "pattern"),
        ("error", "blocker"),
        ("failed", "blocker"),
        ("cannot", "blocker"),
        ("permission denied", "blocker"),
    ]

    def extract(self, tool_name: str, tool_input: Dict, tool_result: Any) -> Optional[Dict]:
        """Extract insight from tool result if present."""
        result_str = str(tool_result).lower() if tool_result else ""

        # Check for discovery patterns
        for keyword, insight_type in self.DISCOVERY_PATTERNS:
            if keyword in result_str:
                return self._create_insight(
                    insight_type=insight_type,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_result=tool_result
                )

        # File-specific discoveries
        if tool_name in ["Read", "Glob", "Grep"]:
            return self._extract_file_insight(tool_name, tool_input, tool_result)

        return None

    def _create_insight(
        self,
        insight_type: str,
        tool_name: str,
        tool_input: Dict,
        tool_result: Any
    ) -> Dict:
        """Create an insight dictionary."""
        content = self._summarize_result(tool_name, tool_input, tool_result)
        tags = self._extract_tags(tool_input, tool_result)

        return {
            "id": hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:8],
            "type": insight_type,
            "content": content,
            "relevance_tags": tags,
            "confidence": 0.7,
            "timestamp": datetime.now().isoformat()
        }

    def _extract_file_insight(
        self,
        tool_name: str,
        tool_input: Dict,
        tool_result: Any
    ) -> Optional[Dict]:
        """Extract file-related insights."""
        file_path = tool_input.get("file_path", tool_input.get("path", ""))

        if not file_path:
            return None

        # Extract directory/module info
        path_parts = file_path.split("/")

        # Check for common patterns
        if "test" in file_path.lower():
            return {
                "id": hashlib.md5(f"test-{file_path}".encode()).hexdigest()[:8],
                "type": "pattern",
                "content": f"Tests located at: {'/'.join(path_parts[:-1])}",
                "relevance_tags": ["test", "testing"],
                "confidence": 0.8,
                "timestamp": datetime.now().isoformat()
            }

        if "config" in file_path.lower():
            return {
                "id": hashlib.md5(f"config-{file_path}".encode()).hexdigest()[:8],
                "type": "discovery",
                "content": f"Configuration at: {file_path}",
                "relevance_tags": ["config", "configuration"],
                "confidence": 0.8,
                "timestamp": datetime.now().isoformat()
            }

        return None

    def _summarize_result(self, tool_name: str, tool_input: Dict, tool_result: Any) -> str:
        """Create a concise summary of the tool result."""
        result_str = str(tool_result)[:200]  # Truncate

        if tool_name == "Read":
            file_path = tool_input.get("file_path", "unknown")
            return f"Read {file_path}: {result_str[:50]}..."

        if tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"Found files matching {pattern}"

        if tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"Search for '{pattern}' found matches"

        return f"{tool_name}: {result_str[:100]}"

    def _extract_tags(self, tool_input: Dict, tool_result: Any) -> List[str]:
        """Extract relevance tags from context."""
        tags = []

        # From file paths
        file_path = tool_input.get("file_path", tool_input.get("path", ""))
        if file_path:
            parts = file_path.lower().split("/")
            for part in parts:
                if part in ["src", "lib", "test", "tests", "docs", "config", "api", "auth", "components"]:
                    tags.append(part)

        # From patterns
        pattern = tool_input.get("pattern", "")
        if pattern:
            tags.append(pattern.split("*")[0].strip("."))

        return list(set(tags))[:5]  # Max 5 tags


# =============================================================================
# MAIN HOOK
# =============================================================================

class PowerModeCheckInHook:
    """Main hook class for power mode check-ins."""

    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.insight_extractor = InsightExtractor()
        self.insight_embedder: Optional['InsightEmbedder'] = None
        self.bug_detector: Optional['BugDetector'] = None
        self.pattern_client: Optional['PatternClient'] = None
        self.state_tracker: Optional[AgentStateTracker] = None
        self.guardrails: Optional[Guardrails] = None
        self.tool_history: List[Dict] = []
        self.efficiency_tracker = None

        # Initialize embedder if available
        if EMBEDDINGS_AVAILABLE:
            try:
                self.insight_embedder = InsightEmbedder()
            except Exception:
                pass

        # Initialize pattern client for collective search
        if PATTERN_CLIENT_AVAILABLE:
            try:
                self.pattern_client = PatternClient()
            except Exception:
                pass

        # Initialize bug detector with pattern client
        if BUG_DETECTOR_AVAILABLE:
            try:
                self.bug_detector = BugDetector(pattern_client=self.pattern_client)
            except Exception:
                pass

        # Initialize efficiency tracker (Issue #78)
        if EFFICIENCY_TRACKER_AVAILABLE:
            try:
                self.efficiency_tracker = get_efficiency_tracker()
            except Exception:
                pass

    def _get_redis_client(self):
        """
        Get the appropriate Redis client (cloud or local).

        Priority:
        1. If POPKIT_API_KEY is set → PopKit Cloud
        2. If local Redis available → Local Redis
        3. Fall back to local-only client
        """
        # Check for cloud configuration
        api_key = os.environ.get("POPKIT_API_KEY")
        cloud_enabled = os.environ.get("POPKIT_CLOUD_ENABLED", "true").lower() != "false"

        if api_key and cloud_enabled:
            try:
                from cloud_client import PopKitCloudClient
                client = PopKitCloudClient.from_env()
                if client:
                    return client
            except ImportError:
                pass

        # Fall back to local Redis client
        return PowerModeRedisClient()

    def initialize(self, agent_id: str, agent_name: str, session_id: str):
        """Initialize the hook for an agent."""
        self.state_tracker = AgentStateTracker(agent_id, agent_name, session_id)
        self.redis_client.connect()

        # Initialize session logger (Issue #66 - visibility)
        if LOGGER_AVAILABLE:
            get_logger(session_id)
            log_info(agent_id, f"Agent initialized: {agent_name}")

        # Load objective and set up guardrails
        if PROTOCOL_AVAILABLE:
            objective = self.redis_client.get_objective()
            if objective:
                from protocol import Objective
                self.guardrails = Guardrails(Objective.from_dict(objective))

    def process(self, data: Dict) -> Dict:
        """Process a PostToolUse event."""
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        tool_result = data.get("tool_output", data.get("result", ""))

        # Initialize if needed
        if not self.state_tracker:
            agent_id = data.get("agent_id", hashlib.md5(str(data).encode()).hexdigest()[:8])
            agent_name = data.get("agent_name", "unknown")
            session_id = data.get("session_id", "default")
            self.initialize(agent_id, agent_name, session_id)

        # Record tool use
        self.state_tracker.record_tool_use(tool_name, tool_input, tool_result)

        # Track efficiency (Issue #78)
        if self.efficiency_tracker:
            self.efficiency_tracker.record_tool_call()

        response = {
            "status": "success",
            "decision": "allow",
            "tool_call_count": self.state_tracker.get_tool_call_count()
        }

        # Check if it's time for a check-in
        if self.state_tracker.should_checkin():
            checkin_result = self._perform_checkin(tool_name, tool_input, tool_result)
            response["checkin"] = checkin_result

        return response

    def _perform_checkin(self, tool_name: str, tool_input: Dict, tool_result: Any) -> Dict:
        """Perform a check-in with the coordinator."""
        checkin = {
            "performed": True,
            "timestamp": datetime.now().isoformat(),
            "insights_pushed": 0,
            "insights_pulled": 0,
            "context_injected": []
        }

        # 1. PUSH: Share state
        if self.redis_client.connected:
            agent_state = self.state_tracker.to_agent_state()
            if agent_state:
                self.redis_client.push_heartbeat(
                    self.state_tracker.agent_id,
                    agent_state
                )
                self.redis_client.push_state(
                    self.state_tracker.agent_id,
                    self.state_tracker.state
                )

        # Log check-in (Issue #66 - visibility)
        if LOGGER_AVAILABLE:
            log_checkin(self.state_tracker.agent_id, self.state_tracker.state)

        # 2. PUSH: Extract and share insights (with embedding if available)
        insight = self.insight_extractor.extract(tool_name, tool_input, tool_result)
        if insight:
            insight["from_agent"] = self.state_tracker.agent_id

            # Try to embed the insight for semantic search
            if self.insight_embedder and self.insight_embedder.available:
                try:
                    insight_id, embed_result = self.insight_embedder.embed_insight(
                        content=insight["content"],
                        from_agent=self.state_tracker.agent_id,
                        insight_type=insight.get("type", "discovery")
                    )

                    # Update insight with embedding info
                    insight["id"] = insight_id
                    insight["embedded"] = embed_result.get("status") == "created"
                    insight["summary"] = embed_result.get("summary", insight["content"][:50])

                    # Skip if duplicate
                    if embed_result.get("status") == "duplicate":
                        checkin["duplicate_insight"] = {
                            "id": insight_id,
                            "duplicate_of": embed_result.get("duplicate", {}).get("id"),
                            "similarity": embed_result.get("duplicate", {}).get("similarity")
                        }
                        # Track efficiency: duplicate skipped (Issue #78)
                        if self.efficiency_tracker:
                            self.efficiency_tracker.record_duplicate_skipped(
                                embed_result.get("duplicate", {}).get("similarity", 0.0)
                            )
                        # Don't push duplicate insights
                        insight = None
                except Exception as e:
                    # Fall back to non-embedded insight
                    checkin["embedding_error"] = str(e)

            if insight:
                self.redis_client.push_insight(insight)
                self.state_tracker.record_insight_shared(insight["id"])
                checkin["insights_pushed"] = 1
                # Track efficiency: insight shared (Issue #78)
                if self.efficiency_tracker:
                    self.efficiency_tracker.record_insight_shared(insight.get("content", ""))

        # 3. PULL: Get relevant insights (semantic search if available)
        pulled_insights = []

        if self.insight_embedder and self.insight_embedder.available:
            # Use semantic search for relevance
            try:
                context = self._get_current_context()
                pulled_insights = self.insight_embedder.search_relevant(
                    context=context,
                    exclude_agent=self.state_tracker.agent_id,
                    limit=CONFIG.get("limits", {}).get("max_insights_per_pull", 3)
                )
                checkin["search_mode"] = "semantic"
            except Exception:
                pass

        # Fall back to tag-based search if semantic didn't work
        if not pulled_insights:
            current_tags = self._get_current_tags()
            pulled_insights = self.redis_client.pull_insights(
                tags=current_tags,
                exclude_agent=self.state_tracker.agent_id,
                limit=CONFIG.get("limits", {}).get("max_insights_per_pull", 3)
            )
            checkin["search_mode"] = "tag-based"

        for pulled in pulled_insights:
            self.state_tracker.record_insight_received(pulled.get("id", "unknown"))
            checkin["context_injected"].append({
                "type": pulled.get("type"),
                "content": pulled.get("content") or pulled.get("summary"),
                "similarity": pulled.get("similarity"),
                "from": pulled.get("from_agent") or pulled.get("from")
            })
            # Track efficiency: insight received (Issue #78)
            if self.efficiency_tracker:
                content = pulled.get("content") or pulled.get("summary") or ""
                self.efficiency_tracker.record_insight_received(content)

        checkin["insights_pulled"] = len(pulled_insights)

        # Track efficiency: context reuse via semantic search (Issue #78)
        if pulled_insights and checkin.get("search_mode") == "semantic" and self.efficiency_tracker:
            self.efficiency_tracker.record_context_reuse()

        # 4. CHECK: Get any messages from coordinator
        messages = self.redis_client.check_for_messages(self.state_tracker.agent_id)
        if messages:
            checkin["coordinator_messages"] = messages

            # Handle course corrections
            for msg in messages:
                if msg.get("type") == "COURSE_CORRECT":
                    checkin["course_correction"] = msg.get("payload", {})

                elif msg.get("type") == "DRIFT_ALERT":
                    checkin["drift_alert"] = msg.get("payload", {})

        # 5. BUG DETECTION: Check for errors and stuck patterns (Issue #72)
        if self.bug_detector:
            try:
                # Convert tool_result to string for detection
                tool_output = str(tool_result)[:2000] if tool_result else ""

                detection_result = self.bug_detector.detect(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_output,
                    history=self.tool_history
                )

                # Store tool in history for pattern detection
                self.tool_history.append({
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_output": tool_output[:500]
                })
                # Keep only last 20 tools
                self.tool_history = self.tool_history[-20:]

                if detection_result.detected:
                    checkin["bug_detection"] = {
                        "detected": True,
                        "action": detection_result.action,
                        "bugs": [
                            {
                                "type": b.detection_type,
                                "error_type": b.error_type,
                                "message": b.error_message,
                                "pattern": b.stuck_pattern,
                                "confidence": b.confidence,
                                "suggestions": b.suggestions
                            }
                            for b in detection_result.bugs
                        ],
                        "matched_patterns": detection_result.matched_patterns[:2]
                    }

                    # Track efficiency: bugs detected (Issue #78)
                    if self.efficiency_tracker:
                        for bug in detection_result.bugs:
                            if bug.detection_type == "error":
                                self.efficiency_tracker.record_bug_detected(bug.error_type or "")
                            elif bug.detection_type == "stuck":
                                self.efficiency_tracker.record_stuck_pattern()

                    # If patterns matched with high similarity, inject hint
                    if detection_result.matched_patterns:
                        best_match = detection_result.matched_patterns[0]
                        if best_match.get("similarity", 0) >= 0.7:
                            checkin["context_injected"].append({
                                "type": "pattern_hint",
                                "content": f"[Collective] {best_match.get('solution', '')}",
                                "similarity": best_match.get("similarity"),
                                "from": "collective_learning"
                            })
                            # Track efficiency: pattern match (Issue #78)
                            if self.efficiency_tracker:
                                self.efficiency_tracker.record_pattern_match(
                                    best_match.get("id", ""),
                                    best_match.get("similarity", 0)
                                )

            except Exception as e:
                checkin["bug_detection_error"] = str(e)

        # 6. CHECK: Get pattern recommendations
        patterns = self.redis_client.get_patterns(self.state_tracker.state.get("current_task", ""))
        if patterns:
            checkin["pattern_recommendations"] = patterns[:2]  # Top 2

        # Record check-in
        self.state_tracker.record_checkin()

        # 7. EFFICIENCY: Add efficiency summary (Issue #78)
        if self.efficiency_tracker:
            try:
                summary = self.efficiency_tracker.get_summary()
                checkin["efficiency"] = {
                    "tokens_estimated_saved": summary["tokens_estimated_saved"],
                    "efficiency_score": summary["efficiency_score"],
                    "compact": self.efficiency_tracker.get_compact_summary()
                }
            except Exception:
                pass

        return checkin

    def _get_current_tags(self) -> List[str]:
        """Get tags representing current work context."""
        tags = []

        # From files touched
        for file_path in self.state_tracker.state.get("files_touched", [])[-5:]:
            parts = file_path.lower().split("/")
            for part in parts:
                if part in ["src", "lib", "test", "auth", "api", "components", "config"]:
                    tags.append(part)

        # From current task
        task = self.state_tracker.state.get("current_task", "").lower()
        keywords = ["test", "auth", "api", "config", "database", "ui", "docs"]
        for kw in keywords:
            if kw in task:
                tags.append(kw)

        return list(set(tags))

    def _get_current_context(self) -> str:
        """Get current work context as a string for semantic search."""
        parts = []

        # Current task
        task = self.state_tracker.state.get("current_task", "")
        if task:
            parts.append(f"Current task: {task}")

        # Recent files
        files = self.state_tracker.state.get("files_touched", [])[-5:]
        if files:
            parts.append(f"Working with files: {', '.join(files)}")

        # Tools used
        tools = self.state_tracker.state.get("tools_used", [])
        if tools:
            parts.append(f"Using: {', '.join(tools)}")

        return " ".join(parts) if parts else "general development"

    # =========================================================================
    # STREAMING METHODS (Issue #23)
    # =========================================================================

    def start_stream(self, tool_name: str) -> str:
        """
        Start a new streaming session.

        Args:
            tool_name: Name of the tool being streamed

        Returns:
            Session ID for the stream
        """
        if not self.state_tracker:
            return ""

        # Generate session ID
        session_id = hashlib.md5(
            f"{self.state_tracker.agent_id}{tool_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        # Track locally
        self.state_tracker.start_stream(session_id, tool_name)

        # Publish to coordinator
        self.redis_client.publish_stream_start(
            self.state_tracker.agent_id,
            session_id,
            tool_name
        )

        return session_id

    def send_chunk(self, session_id: str, content: str, chunk_index: int, is_final: bool = False) -> bool:
        """
        Send a streaming chunk.

        Args:
            session_id: Stream session ID
            content: Chunk content
            chunk_index: Index of this chunk
            is_final: Whether this is the final chunk

        Returns:
            True if sent successfully
        """
        if not self.state_tracker:
            return False

        # Track locally
        self.state_tracker.record_stream_chunk(session_id, content)

        # Publish to coordinator
        if PROTOCOL_AVAILABLE:
            chunk = StreamChunk(
                session_id=session_id,
                agent_id=self.state_tracker.agent_id,
                chunk_index=chunk_index,
                content=content,
                tool_name=self.state_tracker.state.get("active_streams", {}).get(session_id, {}).get("tool_name"),
                is_final=is_final
            )
            self.redis_client.publish_stream_chunk(chunk)

        return True

    def end_stream(self, session_id: str, error: Optional[str] = None) -> Dict:
        """
        End a streaming session.

        Args:
            session_id: Stream session ID
            error: Optional error message

        Returns:
            Stream summary statistics
        """
        if not self.state_tracker:
            return {}

        # Get stream info before ending
        stream_info = self.state_tracker.end_stream(session_id, error)

        # Publish to coordinator
        self.redis_client.publish_stream_end(
            self.state_tracker.agent_id,
            session_id,
            error
        )

        return stream_info or {}

    def get_stream_status(self) -> Dict:
        """Get current streaming status for status line."""
        if not self.state_tracker:
            return {}

        return {
            "streaming": self.state_tracker.get_stream_stats(),
            "agent_id": self.state_tracker.agent_id if self.state_tracker else None
        }


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the hook."""
    try:
        # Read JSON input from stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data) if input_data.strip() else {}

        # Check if power mode is enabled
        if not is_power_mode_enabled():
            # Pass through without processing
            print(json.dumps({"status": "skipped", "decision": "allow", "reason": "power mode not enabled"}))
            return 0

        # Process the hook
        hook = PowerModeCheckInHook()
        result = hook.process(data)

        print(json.dumps(result, indent=2))
        return 0

    except json.JSONDecodeError as e:
        response = {"status": "error", "error": f"Invalid JSON: {e}", "decision": "allow"}
        print(json.dumps(response))
        return 1

    except Exception as e:
        response = {"status": "error", "error": str(e), "decision": "allow"}
        print(json.dumps(response))
        return 1


def is_power_mode_enabled() -> bool:
    """Check if power mode is currently enabled (Issue #66 - bug fix).

    Uses get_project_root() for consistent state file location.
    """
    # Check environment variable
    if os.environ.get("POP_POWER_MODE") == "1":
        return True

    # Check project-local state file first (Issue #66 - use project root)
    project_root = get_project_root()
    local_state = project_root / ".claude" / "popkit" / "power-mode-state.json"
    if local_state.exists():
        try:
            with open(local_state) as f:
                state = json.load(f)
                if state.get("active"):
                    return True
        except (json.JSONDecodeError, IOError):
            pass

    # Check home state file
    home_state = Path.home() / ".claude" / "popkit" / "power-mode-state.json"
    if home_state.exists():
        try:
            with open(home_state) as f:
                state = json.load(f)
                if state.get("active"):
                    return True
        except (json.JSONDecodeError, IOError):
            pass

    # Check legacy enabled flag
    enabled_file = Path.home() / ".claude" / "power-mode-enabled"
    return enabled_file.exists()


if __name__ == "__main__":
    sys.exit(main())
