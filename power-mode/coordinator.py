#!/usr/bin/env python3
"""
Pop Power Mode Coordinator
The mesh brain that orchestrates multi-agent collaboration via Redis pub/sub.

Inspired by ZigBee mesh coordinators and DeepMind's objective-driven systems.
"""

import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from cloud_client import PopKitCloudClient, CloudConfig
    CLOUD_CLIENT_AVAILABLE = True
except ImportError:
    CLOUD_CLIENT_AVAILABLE = False

from protocol import (
    Message, MessageType, MessageFactory,
    Objective, AgentState, Insight, InsightType,
    AgentIdentity, Guardrails, Channels,
    create_objective, StreamChunk
)
from stream_manager import StreamManager, StreamSession

try:
    from metrics import MetricsCollector, save_session_metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


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


# =============================================================================
# AGENT REGISTRY
# =============================================================================

@dataclass
class RegisteredAgent:
    """An agent registered with the coordinator."""
    identity: AgentIdentity
    state: Optional[AgentState] = None
    last_heartbeat: datetime = field(default_factory=datetime.now)
    assigned_task: Optional[Dict] = None
    heartbeat_misses: int = 0
    is_active: bool = True


class AgentRegistry:
    """Tracks all agents in the mesh."""

    def __init__(self):
        self.agents: Dict[str, RegisteredAgent] = {}
        self._lock = threading.Lock()

    def register(self, identity: AgentIdentity) -> RegisteredAgent:
        """Register a new agent."""
        with self._lock:
            agent = RegisteredAgent(identity=identity)
            self.agents[identity.id] = agent
            return agent

    def unregister(self, agent_id: str):
        """Remove an agent from the registry."""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]

    def update_heartbeat(self, agent_id: str, state: Optional[AgentState] = None):
        """Update agent's last heartbeat time."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].last_heartbeat = datetime.now()
                self.agents[agent_id].heartbeat_misses = 0
                if state:
                    self.agents[agent_id].state = state

    def increment_heartbeat_miss(self, agent_id: str) -> int:
        """Increment heartbeat miss count, return new count."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].heartbeat_misses += 1
                return self.agents[agent_id].heartbeat_misses
            return 0

    def mark_inactive(self, agent_id: str):
        """Mark an agent as inactive."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].is_active = False

    def get_active_agents(self) -> List[RegisteredAgent]:
        """Get all active agents."""
        with self._lock:
            return [a for a in self.agents.values() if a.is_active]

    def get_agent(self, agent_id: str) -> Optional[RegisteredAgent]:
        """Get a specific agent."""
        return self.agents.get(agent_id)

    def assign_task(self, agent_id: str, task: Dict):
        """Assign a task to an agent."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].assigned_task = task


# =============================================================================
# SYNC BARRIERS
# =============================================================================

@dataclass
class SyncBarrier:
    """A synchronization point for agents."""
    id: str
    required_agents: Set[str]
    acknowledged_agents: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 120
    on_complete: Optional[Callable] = None

    def acknowledge(self, agent_id: str) -> bool:
        """Agent acknowledges the barrier. Returns True if all acknowledged."""
        if agent_id in self.required_agents:
            self.acknowledged_agents.add(agent_id)
        return self.is_complete()

    def is_complete(self) -> bool:
        """Check if all required agents have acknowledged."""
        return self.required_agents == self.acknowledged_agents

    def is_expired(self) -> bool:
        """Check if barrier has timed out."""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def missing_agents(self) -> Set[str]:
        """Get agents that haven't acknowledged yet."""
        return self.required_agents - self.acknowledged_agents


class SyncManager:
    """Manages synchronization barriers."""

    def __init__(self):
        self.barriers: Dict[str, SyncBarrier] = {}
        self._lock = threading.Lock()

    def create_barrier(
        self,
        barrier_id: str,
        required_agents: List[str],
        timeout: int = 120,
        on_complete: Optional[Callable] = None
    ) -> SyncBarrier:
        """Create a new sync barrier."""
        with self._lock:
            barrier = SyncBarrier(
                id=barrier_id,
                required_agents=set(required_agents),
                timeout_seconds=timeout,
                on_complete=on_complete
            )
            self.barriers[barrier_id] = barrier
            return barrier

    def acknowledge(self, barrier_id: str, agent_id: str) -> Optional[bool]:
        """
        Acknowledge a barrier.
        Returns True if complete, False if not, None if barrier doesn't exist.
        """
        with self._lock:
            if barrier_id not in self.barriers:
                return None

            barrier = self.barriers[barrier_id]
            complete = barrier.acknowledge(agent_id)

            if complete and barrier.on_complete:
                barrier.on_complete()

            return complete

    def cleanup_expired(self) -> List[str]:
        """Remove expired barriers, return their IDs."""
        with self._lock:
            expired = [bid for bid, b in self.barriers.items() if b.is_expired()]
            for bid in expired:
                del self.barriers[bid]
            return expired


# =============================================================================
# DOCUMENTATION BARRIER (Issue #87)
# =============================================================================

class DocumentationBarrier:
    """
    Sync barrier for documentation phase in Power Mode.

    Ensures documentation is updated before advancing to review/summary phases.
    Spawns documentation-maintainer agent if needed.

    Part of Documentation Automation Epic (#81).
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.required_agent = self.config.get("required_agent", "documentation-maintainer")
        self.timeout_seconds = self.config.get("timeout_seconds", 300)
        self.checks = self.config.get("checks", [
            "claude_md_updated",
            "readme_version_match",
            "no_autogen_drift"
        ])
        self.status: Dict[str, bool] = {}
        self.docs_needed_insights: List[str] = []
        self.docs_updated_insights: List[str] = []
        self._lock = threading.Lock()

    def record_docs_needed(self, agent_id: str, description: str):
        """Record that an agent flagged documentation as needed."""
        with self._lock:
            self.docs_needed_insights.append(f"{agent_id}: {description}")

    def record_docs_updated(self, agent_id: str, description: str):
        """Record that documentation was updated."""
        with self._lock:
            self.docs_updated_insights.append(f"{agent_id}: {description}")

    def check_claude_md_updated(self, files_touched: List[str]) -> bool:
        """Check if CLAUDE.md was updated when code changed."""
        code_changed = any(
            f.endswith(('.py', '.ts', '.js', '.tsx', '.jsx'))
            for f in files_touched
        )
        claude_md_updated = 'CLAUDE.md' in files_touched

        # If code changed but CLAUDE.md not updated, flag it
        if code_changed and not claude_md_updated:
            return False
        return True

    def check_readme_version_match(self) -> bool:
        """Check if README version matches plugin.json."""
        # This would be implemented by reading files
        # For now, return True (assumes verified externally)
        return True

    def check_no_autogen_drift(self) -> bool:
        """Check for drift in auto-generated sections."""
        # This would invoke doc_sync.py
        # For now, return True (assumes verified externally)
        return True

    def run_checks(self, files_touched: List[str]) -> Dict[str, bool]:
        """Run all documentation checks."""
        with self._lock:
            self.status = {
                "claude_md_updated": self.check_claude_md_updated(files_touched),
                "readme_version_match": self.check_readme_version_match(),
                "no_autogen_drift": self.check_no_autogen_drift()
            }
            return self.status

    def is_complete(self) -> bool:
        """Check if all documentation requirements are satisfied."""
        with self._lock:
            if not self.status:
                return False
            return all(self.status.values())

    def get_missing_checks(self) -> List[str]:
        """Get list of checks that failed."""
        with self._lock:
            return [check for check, passed in self.status.items() if not passed]

    def needs_documentation_agent(self) -> bool:
        """Determine if documentation-maintainer should be spawned."""
        with self._lock:
            # If docs were flagged as needed but not yet updated
            return len(self.docs_needed_insights) > len(self.docs_updated_insights)

    def get_summary(self) -> Dict:
        """Get summary of documentation barrier status."""
        with self._lock:
            return {
                "required_agent": self.required_agent,
                "timeout_seconds": self.timeout_seconds,
                "checks": self.checks,
                "status": self.status,
                "is_complete": self.is_complete(),
                "missing_checks": self.get_missing_checks(),
                "needs_documentation_agent": self.needs_documentation_agent(),
                "docs_needed_count": len(self.docs_needed_insights),
                "docs_updated_count": len(self.docs_updated_insights)
            }


# =============================================================================
# INSIGHT POOL
# =============================================================================

class InsightPool:
    """Manages shared insights between agents."""

    def __init__(self, max_insights: int = 100, on_insight_added: Optional[Callable] = None):
        self.insights: List[Insight] = []
        self.max_insights = max_insights
        self.on_insight_added = on_insight_added  # Callback for documentation tracking
        self._lock = threading.Lock()

    def add(self, insight: Insight):
        """Add an insight to the pool."""
        with self._lock:
            # Deduplication check
            for existing in self.insights:
                if self._is_duplicate(existing, insight):
                    return

            self.insights.append(insight)

            # Notify callback (for documentation barrier tracking - Issue #87)
            if self.on_insight_added:
                self.on_insight_added(insight)

            # Trim if over limit
            if len(self.insights) > self.max_insights:
                self.insights = self.insights[-self.max_insights:]

    def get_relevant(
        self,
        tags: List[str],
        exclude_agent: Optional[str] = None,
        limit: int = 3
    ) -> List[Insight]:
        """Get insights relevant to the given tags."""
        with self._lock:
            relevant = []
            for insight in reversed(self.insights):  # Most recent first
                # Skip if from the requesting agent
                if exclude_agent and insight.from_agent == exclude_agent:
                    continue

                # Check tag overlap
                tag_overlap = set(insight.relevance_tags) & set(tags)
                if tag_overlap:
                    relevant.append(insight)
                    if len(relevant) >= limit:
                        break

            return relevant

    def mark_consumed(self, insight_id: str, agent_id: str):
        """Mark an insight as consumed by an agent."""
        with self._lock:
            for insight in self.insights:
                if insight.id == insight_id:
                    insight.consumed_by.append(agent_id)
                    break

    def _is_duplicate(self, a: Insight, b: Insight) -> bool:
        """Check if two insights are duplicates."""
        # Simple content similarity check
        return (
            a.type == b.type and
            a.content.lower().strip() == b.content.lower().strip()
        )


# =============================================================================
# PATTERN LEARNING
# =============================================================================

@dataclass
class LearnedPattern:
    """A pattern learned from agent behavior."""
    id: str
    approach: str
    context: str
    outcome: str  # "success", "failed", "partial"
    confidence: float
    learned_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0


class PatternLearner:
    """Tracks and learns from successful/failed approaches."""

    def __init__(self):
        self.patterns: Dict[str, LearnedPattern] = {}
        self._lock = threading.Lock()

    def record(self, approach: str, context: str, outcome: str, confidence: float = 0.5):
        """Record a pattern from agent behavior."""
        pattern_id = hashlib.md5(f"{approach}{context}".encode()).hexdigest()[:8]

        with self._lock:
            if pattern_id in self.patterns:
                # Update existing pattern
                existing = self.patterns[pattern_id]
                existing.usage_count += 1
                # Adjust confidence based on new outcome
                if outcome == existing.outcome:
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                else:
                    existing.confidence = max(0.0, existing.confidence - 0.2)
            else:
                # New pattern
                self.patterns[pattern_id] = LearnedPattern(
                    id=pattern_id,
                    approach=approach,
                    context=context,
                    outcome=outcome,
                    confidence=confidence
                )

    def get_recommendations(self, context: str, limit: int = 3) -> List[Dict]:
        """Get pattern recommendations for a given context."""
        with self._lock:
            recommendations = []
            context_lower = context.lower()

            for pattern in self.patterns.values():
                if pattern.context.lower() in context_lower:
                    if pattern.outcome == "success" and pattern.confidence > 0.6:
                        recommendations.append({
                            "approach": pattern.approach,
                            "confidence": pattern.confidence,
                            "reason": f"Worked {pattern.usage_count} times in similar context"
                        })
                    elif pattern.outcome == "failed" and pattern.confidence > 0.6:
                        recommendations.append({
                            "avoid": pattern.approach,
                            "confidence": pattern.confidence,
                            "reason": f"Failed in similar context"
                        })

            # Sort by confidence
            recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            return recommendations[:limit]


# =============================================================================
# COORDINATOR
# =============================================================================

class PowerModeCoordinator:
    """
    The mesh brain that orchestrates multi-agent collaboration.

    Responsibilities:
    - Track agent states and heartbeats
    - Route messages between agents
    - Manage sync barriers
    - Share insights intelligently
    - Detect and handle agent failures
    - Enforce guardrails
    - Track objective progress
    """

    def __init__(self, objective: Optional[Objective] = None):
        self.objective = objective
        self.session_id = self._generate_session_id()
        self._init_components(objective)

    def _generate_session_id(self) -> str:
        """Generate a stable session ID (Issue #66 - bug fix).

        Uses git HEAD hash + date for consistency across agents.
        Falls back to timestamp-only if not in a git repo.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=7", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                git_hash = result.stdout.strip()
                date_str = datetime.now().strftime("%Y%m%d")
                return hashlib.md5(f"{git_hash}-{date_str}".encode()).hexdigest()[:8]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: timestamp-based
        return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]

    def _init_components(self, objective: Optional[Objective]):
        """Initialize coordinator components after session_id is set."""
        # Documentation barrier (Issue #87) - create first for callback
        doc_barrier_config = CONFIG.get("phases", {}).get("documentation_barrier", {})
        self.documentation_barrier = DocumentationBarrier(doc_barrier_config)

        # Core components
        self.registry = AgentRegistry()
        self.sync_manager = SyncManager()
        self.insight_pool = InsightPool(on_insight_added=self._on_insight_added)
        self.pattern_learner = PatternLearner()
        self.guardrails = Guardrails(objective)

        # Streaming support (Issue #23)
        self.stream_manager = StreamManager(
            on_chunk=self._on_stream_chunk,
            on_session_complete=self._on_stream_complete
        )

        # Redis connection
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

        # Cloud workflow integration (Issue #103 Phase 3)
        self.cloud_client: Optional[PopKitCloudClient] = None
        self.cloud_workflow_id: Optional[str] = None
        self.use_cloud_workflows: bool = CONFIG.get("cloud", {}).get("use_workflows", True)

        # State
        self.is_running = False
        self.current_phase = 0
        self.phase_results: Dict[str, List[Dict]] = {}
        self.human_pending: List[Message] = []

        # Threads
        self._listener_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None

        # Metrics collector (Issue #108)
        if METRICS_AVAILABLE:
            self.metrics_collector = MetricsCollector(self.session_id)
        else:
            self.metrics_collector = None

    def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            print("Redis not available. Install with: pip install redis", file=sys.stderr)
            return False

        try:
            redis_config = CONFIG.get("redis", {})
            self.redis = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                socket_timeout=redis_config.get("socket_timeout", 5),
                retry_on_timeout=redis_config.get("retry_on_timeout", True),
                decode_responses=True
            )
            self.redis.ping()
            self.pubsub = self.redis.pubsub()
            return True
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}", file=sys.stderr)
            return False

    def start(self):
        """Start the coordinator."""
        if not self.redis:
            if not self.connect():
                return False

        self.is_running = True

        # Subscribe to coordinator channel
        self.pubsub.subscribe(Channels.coordinator())
        self.pubsub.subscribe(Channels.heartbeat())
        self.pubsub.subscribe(Channels.results())
        self.pubsub.subscribe(Channels.insights())
        self.pubsub.subscribe(Channels.human())

        # Start listener thread
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        # Store objective in Redis
        if self.objective:
            self.redis.set(
                Channels.objective_key(),
                json.dumps(self.objective.to_dict())
            )

        # Issue #103 Phase 3: Start cloud workflow for durable tracking
        if self.use_cloud_workflows and CLOUD_CLIENT_AVAILABLE:
            self._start_cloud_workflow()

        print(f"Coordinator started. Session: {self.session_id}")
        return True

    def _start_cloud_workflow(self):
        """
        Start a cloud workflow for durable state tracking.

        Issue #103 Phase 3: Cloud workflows provide:
        - Durable state persistence (survives crashes)
        - Progress tracking across sessions
        - Coordination between phases
        - Crash recovery
        """
        config = CloudConfig.from_env()
        if not config:
            return

        self.cloud_client = PopKitCloudClient(config)
        if not self.cloud_client.connect():
            self.cloud_client = None
            return

        # Get agent names from registry
        agent_names = [
            agent.identity.name
            for agent in self.registry.get_active_agents()
        ]

        # If no agents yet, use objective phases as placeholder
        if not agent_names and self.objective:
            agent_names = self.objective.phases[:3]  # First 3 phases

        task_description = self.objective.description if self.objective else "Power Mode session"

        result = self.cloud_client.start_power_mode_workflow(
            task=task_description,
            agents=agent_names or ["coordinator"],
            session_id=self.session_id,
            consensus_threshold=CONFIG.get("consensus", {}).get("threshold", 0.7)
        )

        if result:
            self.cloud_workflow_id = result.get("workflowId")
            print(f"Cloud workflow started: {self.cloud_workflow_id}")

    def _update_cloud_workflow(self, agent_results: Optional[List[Dict]] = None):
        """
        Push local progress to cloud workflow.

        Called when agents complete work to sync state with cloud.
        """
        if not self.cloud_client or not self.cloud_workflow_id:
            return

        # Gather agent results from registry
        if agent_results is None:
            agent_results = []
            for agent in self.registry.get_active_agents():
                if agent.state and agent.state.progress >= 1.0:
                    agent_results.append({
                        "agent": agent.identity.name,
                        "output": json.dumps(agent.assigned_task) if agent.assigned_task else "",
                        "confidence": agent.state.progress if agent.state else 0.5
                    })

        self.cloud_client.update_workflow(
            run_id=self.cloud_workflow_id,
            agent_results=agent_results
        )

    def stop(self):
        """Stop the coordinator."""
        self.is_running = False

        if self.pubsub:
            self.pubsub.unsubscribe()

        if self._listener_thread:
            self._listener_thread.join(timeout=2)

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        # Issue #103 Phase 3: Final sync to cloud workflow
        if self.cloud_client and self.cloud_workflow_id:
            self._update_cloud_workflow()
            self.cloud_client.disconnect()

        # Issue #108: End session and save metrics
        if self.metrics_collector:
            self.metrics_collector.end_session()
            if self.redis:
                save_session_metrics(self.metrics_collector.metrics, self.redis)
            # Print metrics report
            print(self.metrics_collector.format_cli_report())

        print("Coordinator stopped.")

    def _listen_loop(self):
        """Main message listening loop."""
        while self.is_running:
            try:
                message = self.pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    self._handle_message(message["channel"], message["data"])
            except Exception as e:
                print(f"Listener error: {e}", file=sys.stderr)

    def _monitor_loop(self):
        """Monitor agent health and sync barriers."""
        while self.is_running:
            try:
                self._check_agent_health()
                self._cleanup_expired_barriers()
                time.sleep(CONFIG.get("intervals", {}).get("heartbeat_seconds", 15))
            except Exception as e:
                print(f"Monitor error: {e}", file=sys.stderr)

    def _handle_message(self, channel: str, data: str):
        """Handle an incoming message."""
        try:
            msg = Message.from_json(data)
        except json.JSONDecodeError:
            return

        handlers = {
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.PROGRESS: self._handle_progress,
            MessageType.RESULT: self._handle_result,
            MessageType.INSIGHT: self._handle_insight,
            MessageType.SYNC_ACK: self._handle_sync_ack,
            MessageType.HUMAN_REQUIRED: self._handle_human_required,
            MessageType.BOUNDARY_ALERT: self._handle_boundary_alert,
            # Streaming handlers (Issue #23)
            MessageType.STREAM_START: self._handle_stream_start,
            MessageType.STREAM_CHUNK: self._handle_stream_chunk,
            MessageType.STREAM_END: self._handle_stream_end,
            MessageType.STREAM_ERROR: self._handle_stream_error,
        }

        handler = handlers.get(msg.type)
        if handler:
            handler(msg)

    def _handle_heartbeat(self, msg: Message):
        """Handle agent heartbeat."""
        agent_id = msg.from_agent
        state_data = msg.payload

        # Update registry
        self.registry.update_heartbeat(agent_id)

        # Store state in Redis
        if state_data:
            self.redis.hset(
                Channels.state_key(agent_id),
                mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                         for k, v in state_data.items()}
            )

            # Check for drift
            if "agent" in state_data:
                state = AgentState(**state_data)
                drift = self.guardrails.check_drift(state)
                if drift:
                    self._broadcast_drift_alert(agent_id, drift)

    def _handle_progress(self, msg: Message):
        """Handle progress update."""
        agent_id = msg.from_agent
        progress = msg.payload.get("progress", 0)

        agent = self.registry.get_agent(agent_id)
        if agent and agent.state:
            agent.state.progress = progress

        # Broadcast progress to other agents (they might be waiting)
        self._broadcast(MessageFactory.progress(
            "coordinator",
            progress,
            {"agent": agent_id, "phase": self.current_phase}
        ))

    def _handle_result(self, msg: Message):
        """Handle task completion result."""
        agent_id = msg.from_agent
        result = msg.payload

        # Store phase results
        phase = self.objective.phases[self.current_phase] if self.objective else "default"
        if phase not in self.phase_results:
            self.phase_results[phase] = []
        self.phase_results[phase].append({
            "agent": agent_id,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        # Learn from result
        if result.get("approach"):
            self.pattern_learner.record(
                approach=result["approach"],
                context=result.get("context", ""),
                outcome="success" if result.get("success") else "failed",
                confidence=result.get("confidence", 0.5)
            )

        # Issue #103 Phase 3: Sync result to cloud workflow
        if self.cloud_client and self.cloud_workflow_id:
            agent = self.registry.get_agent(agent_id)
            agent_name = agent.identity.name if agent else agent_id
            self._update_cloud_workflow([{
                "agent": agent_name,
                "output": json.dumps(result) if isinstance(result, dict) else str(result),
                "confidence": result.get("confidence", 0.8) if isinstance(result, dict) else 0.8
            }])

        # Check if phase is complete
        self._check_phase_completion()

    def _handle_insight(self, msg: Message):
        """Handle shared insight."""
        insight_data = msg.payload

        try:
            insight = Insight.from_dict(insight_data)
            self.insight_pool.add(insight)

            # Route to relevant agents
            for agent in self.registry.get_active_agents():
                if agent.identity.id == msg.from_agent:
                    continue  # Don't send back to sender

                if agent.assigned_task:
                    task_tags = agent.assigned_task.get("tags", [])
                    if set(insight.relevance_tags) & set(task_tags):
                        self._send_to_agent(agent.identity.id, msg)

        except Exception as e:
            print(f"Error handling insight: {e}", file=sys.stderr)

    def _handle_sync_ack(self, msg: Message):
        """Handle sync barrier acknowledgment."""
        barrier_id = msg.payload.get("barrier_id")
        agent_id = msg.from_agent

        complete = self.sync_manager.acknowledge(barrier_id, agent_id)
        if complete:
            # Issue #108: Track sync barrier wait time
            if self.metrics_collector and barrier_id in self.sync_manager.barriers:
                barrier = self.sync_manager.barriers[barrier_id]
                wait_time = (datetime.now() - barrier.created_at).total_seconds()
                self.metrics_collector.record_sync_barrier_wait(wait_time)

            # Broadcast that barrier is complete
            self._broadcast(Message(
                id=hashlib.md5(f"sync-complete-{barrier_id}".encode()).hexdigest()[:12],
                type=MessageType.SYNC,
                from_agent="coordinator",
                to_agent="*",
                payload={"barrier_id": barrier_id, "status": "complete"}
            ))

    def _handle_human_required(self, msg: Message):
        """Handle request for human decision."""
        self.human_pending.append(msg)

        # Store in Redis for human to see
        self.redis.lpush(
            Channels.human(),
            msg.to_json()
        )

        # Pause the requesting agent
        self._send_to_agent(msg.from_agent, Message(
            id=hashlib.md5(f"pause-{msg.from_agent}".encode()).hexdigest()[:12],
            type=MessageType.COURSE_CORRECT,
            from_agent="coordinator",
            to_agent=msg.from_agent,
            payload={
                "action": "pause",
                "reason": "Waiting for human decision",
                "decision_id": msg.id
            }
        ))

    def _handle_boundary_alert(self, msg: Message):
        """Handle boundary violation alert."""
        violation = msg.payload

        # Log violation
        self.guardrails.violations.append({
            "agent": msg.from_agent,
            "violation": violation,
            "timestamp": datetime.now().isoformat()
        })

        # Determine action based on severity
        if violation.get("requires_human"):
            self._handle_human_required(MessageFactory.human_required(
                msg.from_agent,
                {
                    "description": f"Boundary violation: {violation.get('description')}",
                    "context": violation,
                    "recommendation": "Review and decide whether to allow"
                }
            ))
        else:
            # Send course correction
            self._send_to_agent(msg.from_agent, Message(
                id=hashlib.md5(f"correct-{msg.from_agent}".encode()).hexdigest()[:12],
                type=MessageType.COURSE_CORRECT,
                from_agent="coordinator",
                to_agent=msg.from_agent,
                payload={
                    "action": "redirect",
                    "reason": violation.get("reason", "Stay within boundaries"),
                    "suggestion": violation.get("suggestion")
                }
            ))

    # =========================================================================
    # STREAM HANDLERS (Issue #23)
    # =========================================================================

    def _handle_stream_start(self, msg: Message):
        """Handle stream start message from agent."""
        agent_id = msg.from_agent
        payload = msg.payload

        # Start tracking session
        session_id = self.stream_manager.start_session(
            agent_id=agent_id,
            tool_name=payload.get("tool_name"),
            metadata=payload.get("metadata", {})
        )

        # Store session mapping in Redis for other agents
        if self.redis:
            self.redis.hset(
                f"pop:streams:{self.session_id}",
                agent_id,
                json.dumps({
                    "session_id": session_id,
                    "tool_name": payload.get("tool_name"),
                    "started_at": datetime.now().isoformat()
                })
            )

        # Broadcast stream start to interested agents
        self._broadcast(Message(
            id=hashlib.md5(f"stream-start-{session_id}".encode()).hexdigest()[:12],
            type=MessageType.STREAM_START,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "agent_id": agent_id,
                "session_id": session_id,
                "tool_name": payload.get("tool_name")
            }
        ))

    def _handle_stream_chunk(self, msg: Message):
        """Handle stream chunk from agent."""
        try:
            chunk = StreamChunk.from_message(msg)
            self.stream_manager.add_chunk(chunk)
        except Exception as e:
            print(f"Error handling stream chunk: {e}", file=sys.stderr)

    def _handle_stream_end(self, msg: Message):
        """Handle stream end message."""
        payload = msg.payload
        session_id = payload.get("session_id")

        if session_id:
            session = self.stream_manager.end_session(session_id)

            if session and self.redis:
                # Clean up Redis tracking
                self.redis.hdel(f"pop:streams:{self.session_id}", msg.from_agent)

                # Store completed stream summary
                self.redis.hset(
                    f"pop:streams:completed:{self.session_id}",
                    session_id,
                    json.dumps(session.to_dict())
                )

    def _handle_stream_error(self, msg: Message):
        """Handle stream error message."""
        payload = msg.payload
        session_id = payload.get("session_id")
        error = payload.get("error", "Unknown error")

        if session_id:
            self.stream_manager.end_session(session_id, error=error)

        # Log the error
        print(f"Stream error from {msg.from_agent}: {error}", file=sys.stderr)

    def _on_stream_chunk(self, chunk: StreamChunk):
        """Callback when chunk is added to stream manager."""
        # Update status line state
        self.stream_manager.save_state()

        # Forward to interested agents if configured
        if CONFIG.get("streaming", {}).get("broadcast_chunks"):
            self._broadcast(chunk.to_message())

    def _on_stream_complete(self, session: StreamSession):
        """Callback when stream session completes."""
        # Update status line state
        self.stream_manager.save_state()

        # Create insight from completed stream if substantial
        if session.chunk_count > 5:
            insight = Insight(
                id=hashlib.md5(f"stream-{session.session_id}".encode()).hexdigest()[:12],
                type=InsightType.PATTERN,
                from_agent=session.agent_id,
                content=f"Completed {session.tool_name or 'tool'} stream: {session.content_length} bytes in {session.chunk_count} chunks",
                relevance_tags=[session.tool_name or "stream"],
                confidence=0.7
            )
            self.insight_pool.add(insight)

    def _on_insight_added(self, insight: Insight):
        """
        Callback when an insight is added to the pool.
        Tracks documentation-related insights for the DocumentationBarrier (Issue #87).
        """
        # Issue #108: Track insight sharing
        if self.metrics_collector:
            self.metrics_collector.record_insight_shared()

        # Check for documentation-related insight types
        if insight.type == InsightType.DOCS_NEEDED:
            self.documentation_barrier.record_docs_needed(
                insight.from_agent,
                insight.content
            )
        elif insight.type == InsightType.DOCS_UPDATED:
            self.documentation_barrier.record_docs_updated(
                insight.from_agent,
                insight.content
            )

    def _check_agent_health(self):
        """Check agent health and handle failures."""
        timeout = CONFIG.get("intervals", {}).get("agent_timeout_seconds", 60)
        max_misses = CONFIG.get("failover", {}).get("heartbeat_miss_threshold", 3)

        for agent in self.registry.get_active_agents():
            elapsed = (datetime.now() - agent.last_heartbeat).total_seconds()

            if elapsed > timeout:
                misses = self.registry.increment_heartbeat_miss(agent.identity.id)

                if misses >= max_misses:
                    self._handle_agent_failure(agent)

    def _handle_agent_failure(self, agent: RegisteredAgent):
        """Handle an agent that has failed."""
        self.registry.mark_inactive(agent.identity.id)

        # Issue #108: Track agent stop
        if self.metrics_collector:
            self.metrics_collector.agent_stopped(agent.identity.id)

        # Broadcast agent down
        self._broadcast(Message(
            id=hashlib.md5(f"down-{agent.identity.id}".encode()).hexdigest()[:12],
            type=MessageType.AGENT_DOWN,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "agent": agent.identity.id,
                "agent_name": agent.identity.name,
                "last_state": agent.state.to_dict() if agent.state else None,
                "assigned_task": agent.assigned_task
            }
        ))

        # Create orphaned task if there was work in progress
        if agent.assigned_task and CONFIG.get("failover", {}).get("auto_reassign_orphaned"):
            self._create_orphaned_task(agent)

    def _create_orphaned_task(self, agent: RegisteredAgent):
        """Create an orphaned task for reassignment."""
        orphaned = {
            "original_agent": agent.identity.id,
            "original_agent_name": agent.identity.name,
            "task": agent.assigned_task,
            "progress": agent.state.progress if agent.state else 0,
            "context": agent.state.to_dict() if agent.state else {},
            "created_at": datetime.now().isoformat()
        }

        # Store in Redis
        self.redis.lpush("pop:tasks:orphaned", json.dumps(orphaned))

        # Broadcast availability
        self._broadcast(Message(
            id=hashlib.md5(f"orphan-{agent.identity.id}".encode()).hexdigest()[:12],
            type=MessageType.TASK_ORPHANED,
            from_agent="coordinator",
            to_agent="*",
            payload=orphaned
        ))

    def _cleanup_expired_barriers(self):
        """Clean up expired sync barriers."""
        expired = self.sync_manager.cleanup_expired()
        for barrier_id in expired:
            self._broadcast(Message(
                id=hashlib.md5(f"barrier-expired-{barrier_id}".encode()).hexdigest()[:12],
                type=MessageType.SYNC,
                from_agent="coordinator",
                to_agent="*",
                payload={"barrier_id": barrier_id, "status": "expired"}
            ))

    def _check_phase_completion(self):
        """Check if current phase is complete."""
        if not self.objective:
            return

        active_agents = self.registry.get_active_agents()
        all_complete = all(
            agent.state and agent.state.progress >= 1.0
            for agent in active_agents
            if agent.assigned_task
        )

        if all_complete:
            self._advance_phase()

    def _advance_phase(self):
        """Advance to the next phase."""
        if not self.objective:
            return

        # Issue #108: End previous phase timing
        if self.metrics_collector and self.current_phase < len(self.objective.phases):
            prev_phase = self.objective.phases[self.current_phase]
            self.metrics_collector.end_phase(prev_phase)

        self.current_phase += 1

        if self.current_phase >= len(self.objective.phases):
            self._complete_objective()
            return

        phase_name = self.objective.phases[self.current_phase]

        # Create sync barrier for phase transition
        active_ids = [a.identity.id for a in self.registry.get_active_agents()]
        self.sync_manager.create_barrier(
            f"phase-{self.current_phase}",
            active_ids,
            on_complete=lambda: self._start_phase(phase_name)
        )

        # Broadcast phase transition
        self._broadcast(MessageFactory.sync(
            f"phase-{self.current_phase}",
            active_ids
        ))

    def _start_phase(self, phase_name: str):
        """Start a new phase."""
        # Issue #108: Track phase timing
        if self.metrics_collector:
            self.metrics_collector.start_phase(phase_name)

        # Aggregate insights from previous phase
        recommendations = self.pattern_learner.get_recommendations(phase_name)

        self._broadcast(Message(
            id=hashlib.md5(f"phase-start-{phase_name}".encode()).hexdigest()[:12],
            type=MessageType.OBJECTIVE_UPDATE,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "phase": phase_name,
                "phase_index": self.current_phase,
                "recommendations": recommendations,
                "previous_results": self.phase_results.get(
                    self.objective.phases[self.current_phase - 1], []
                ) if self.current_phase > 0 else []
            }
        ))

    def _complete_objective(self):
        """Handle objective completion."""
        # Aggregate all results
        final_results = {
            "objective": self.objective.description,
            "phases_completed": len(self.objective.phases),
            "results_by_phase": self.phase_results,
            "patterns_learned": len(self.pattern_learner.patterns),
            "insights_shared": len(self.insight_pool.insights),
            "violations": len(self.guardrails.violations),
            "completed_at": datetime.now().isoformat()
        }

        # Store final results
        self.redis.set(
            f"pop:completed:{self.session_id}",
            json.dumps(final_results)
        )

        # Broadcast completion
        self._broadcast(Message(
            id=hashlib.md5(f"complete-{self.session_id}".encode()).hexdigest()[:12],
            type=MessageType.OBJECTIVE_UPDATE,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "status": "complete",
                "summary": final_results
            }
        ))

    def _broadcast(self, msg: Message):
        """Broadcast a message to all agents."""
        self.redis.publish(Channels.broadcast(), msg.to_json())

    def _broadcast_drift_alert(self, agent_id: str, drift: Dict):
        """Broadcast a drift alert."""
        self._send_to_agent(agent_id, Message(
            id=hashlib.md5(f"drift-{agent_id}".encode()).hexdigest()[:12],
            type=MessageType.DRIFT_ALERT,
            from_agent="coordinator",
            to_agent=agent_id,
            payload=drift
        ))

    def _send_to_agent(self, agent_id: str, msg: Message):
        """Send a message to a specific agent."""
        self.redis.publish(Channels.agent(agent_id), msg.to_json())

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def register_agent(self, name: str) -> AgentIdentity:
        """Register a new agent with the coordinator."""
        identity = AgentIdentity(
            id=hashlib.md5(f"{name}{datetime.now()}".encode()).hexdigest()[:8],
            name=name,
            session_id=self.session_id
        )
        self.registry.register(identity)

        # Issue #108: Track agent start
        if self.metrics_collector:
            self.metrics_collector.agent_started(identity.id)

        return identity

    def assign_task(self, agent_id: str, task: Dict):
        """Assign a task to an agent."""
        self.registry.assign_task(agent_id, task)

        msg = MessageFactory.task("coordinator", agent_id, task)
        self._send_to_agent(agent_id, msg)

    def create_sync_barrier(self, name: str, agents: List[str]) -> str:
        """Create a sync barrier and notify agents."""
        barrier_id = f"{name}-{hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:6]}"

        # Issue #103 Phase 3: Use cloud sync barrier if available
        if self.cloud_client and self.cloud_client.connected:
            result = self.cloud_client.create_sync_barrier(
                barrier_id=barrier_id,
                required_agents=agents,
                timeout_seconds=CONFIG.get("intervals", {}).get("sync_timeout_seconds", 120)
            )
            if result:
                print(f"Cloud sync barrier created: {barrier_id}")

        # Also create local barrier for redundancy
        self.sync_manager.create_barrier(barrier_id, agents)

        msg = MessageFactory.sync(barrier_id, agents)
        self._broadcast(msg)

        return barrier_id

    def get_insights_for_agent(self, agent_id: str, tags: List[str]) -> List[Dict]:
        """Get relevant insights for an agent."""
        insights = self.insight_pool.get_relevant(
            tags=tags,
            exclude_agent=agent_id,
            limit=CONFIG.get("limits", {}).get("max_insights_per_pull", 3)
        )
        return [i.to_dict() for i in insights]

    def get_pattern_recommendations(self, context: str) -> List[Dict]:
        """Get pattern recommendations for a context."""
        return self.pattern_learner.get_recommendations(context)

    def get_human_pending(self) -> List[Dict]:
        """Get pending human decisions."""
        return [m.payload for m in self.human_pending]

    def resolve_human_decision(self, decision_id: str, approved: bool, notes: str = ""):
        """Resolve a pending human decision."""
        for msg in self.human_pending:
            if msg.id == decision_id:
                self.human_pending.remove(msg)

                # Send resolution to agent
                self._send_to_agent(msg.from_agent, Message(
                    id=hashlib.md5(f"resolve-{decision_id}".encode()).hexdigest()[:12],
                    type=MessageType.COURSE_CORRECT,
                    from_agent="coordinator",
                    to_agent=msg.from_agent,
                    payload={
                        "action": "resume" if approved else "abort",
                        "decision_id": decision_id,
                        "approved": approved,
                        "notes": notes
                    }
                ))
                break

    def get_metrics_report(self) -> Optional[Dict]:
        """Get the current metrics report (Issue #108)."""
        if self.metrics_collector:
            return self.metrics_collector.generate_report()
        return None

    def get_metrics_cli_report(self) -> Optional[str]:
        """Get CLI-formatted metrics report (Issue #108)."""
        if self.metrics_collector:
            return self.metrics_collector.format_cli_report()
        return None

    def get_status(self) -> Dict:
        """Get coordinator status."""
        status = {
            "session_id": self.session_id,
            "is_running": self.is_running,
            "objective": self.objective.description if self.objective else None,
            "current_phase": self.current_phase,
            "phase_name": self.objective.phases[self.current_phase] if self.objective and self.current_phase < len(self.objective.phases) else None,
            "active_agents": len(self.registry.get_active_agents()),
            "insights_pooled": len(self.insight_pool.insights),
            "patterns_learned": len(self.pattern_learner.patterns),
            "human_pending": len(self.human_pending),
            "violations": len(self.guardrails.violations)
        }

        # Issue #103 Phase 3: Include cloud workflow status
        if self.cloud_workflow_id:
            status["cloud_workflow"] = {
                "id": self.cloud_workflow_id,
                "connected": self.cloud_client.connected if self.cloud_client else False
            }

            # Fetch cloud status if available
            if self.cloud_client and self.cloud_client.connected:
                cloud_status = self.cloud_client.get_workflow_status(self.cloud_workflow_id)
                if cloud_status:
                    status["cloud_workflow"]["status"] = cloud_status.get("status")
                    status["cloud_workflow"]["currentPhase"] = cloud_status.get("currentPhase")

        return status


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point for the coordinator."""
    import argparse

    parser = argparse.ArgumentParser(description="Pop Power Mode Coordinator")
    parser.add_argument("command", choices=["start", "status", "stop", "metrics"])
    parser.add_argument("--objective", help="Objective description")
    parser.add_argument("--phases", nargs="+", help="Phase names")
    parser.add_argument("--success-criteria", nargs="+", help="Success criteria")
    parser.add_argument("--session", help="Session ID for metrics lookup")

    args = parser.parse_args()

    if args.command == "start":
        objective = None
        if args.objective:
            objective = create_objective(
                description=args.objective,
                success_criteria=args.success_criteria or ["Task completed"],
                phases=args.phases or ["explore", "implement", "review"]
            )

        coordinator = PowerModeCoordinator(objective)
        if coordinator.start():
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                coordinator.stop()
        else:
            print("Failed to start coordinator")
            sys.exit(1)

    elif args.command == "status":
        # Check Redis for coordinator status
        if not REDIS_AVAILABLE:
            print("Redis not available")
            sys.exit(1)

        r = redis.Redis(decode_responses=True)
        status = r.get("pop:coordinator:status")
        if status:
            print(json.dumps(json.loads(status), indent=2))
        else:
            print("No active coordinator found")

    elif args.command == "stop":
        # Signal coordinator to stop
        if not REDIS_AVAILABLE:
            print("Redis not available")
            sys.exit(1)

        r = redis.Redis(decode_responses=True)
        r.publish("pop:coordinator", json.dumps({"command": "stop"}))
        print("Stop signal sent")

    elif args.command == "metrics":
        # Issue #108: Display metrics for a session
        if not REDIS_AVAILABLE:
            print("Redis not available")
            sys.exit(1)

        r = redis.Redis(decode_responses=True)

        if args.session:
            # Load specific session
            data = load_session_metrics(args.session, r)
            if data:
                # Create collector from loaded data and display
                collector = MetricsCollector(args.session)
                collector.metrics = SessionMetrics(**data) if isinstance(data, dict) else data
                print(collector.format_cli_report())
            else:
                print(f"No metrics found for session: {args.session}")
        else:
            # List available sessions
            keys = r.keys("popkit:metrics:*")
            if keys:
                print("Available sessions:")
                for key in keys:
                    session_id = key.replace("popkit:metrics:", "")
                    print(f"  - {session_id}")
            else:
                print("No metrics sessions found")


if __name__ == "__main__":
    main()
