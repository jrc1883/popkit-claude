#!/usr/bin/env python3
"""
Pop Power Mode Protocol
Message types, serialization, and guardrails for multi-agent Redis pub/sub orchestration.

Inspired by ZigBee mesh networks and DeepMind's objective-driven agent systems.
"""

import json
import hashlib
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class MessageType(Enum):
    """Types of messages in the power mode mesh network."""
    # Core operations
    TASK = "TASK"                    # Coordinator assigns work
    PROGRESS = "PROGRESS"            # Agent reports progress
    RESULT = "RESULT"                # Agent completes work
    HEARTBEAT = "HEARTBEAT"          # Agent is alive

    # Coordination
    SYNC = "SYNC"                    # Sync barrier (wait for all)
    SYNC_ACK = "SYNC_ACK"            # Agent acknowledges sync

    # Knowledge sharing
    INSIGHT = "INSIGHT"              # Agent shares discovery
    QUERY = "QUERY"                  # Agent asks for info
    RESPONSE = "RESPONSE"            # Response to query

    # Objective tracking
    OBJECTIVE_UPDATE = "OBJECTIVE_UPDATE"  # Goal clarification
    DRIFT_ALERT = "DRIFT_ALERT"            # Agent off track
    COURSE_CORRECT = "COURSE_CORRECT"      # Redirect agent

    # Failover
    AGENT_DOWN = "AGENT_DOWN"        # Agent stopped responding
    TASK_ORPHANED = "TASK_ORPHANED"  # Task needs reassignment
    TASK_CLAIMED = "TASK_CLAIMED"    # Agent picks up orphaned task

    # Guardrails
    HUMAN_REQUIRED = "HUMAN_REQUIRED"  # Need human decision
    BOUNDARY_ALERT = "BOUNDARY_ALERT"  # Agent approaching limits

    # Streaming (Issue #23)
    STREAM_START = "STREAM_START"      # Agent opens stream session
    STREAM_CHUNK = "STREAM_CHUNK"      # Incremental data chunk
    STREAM_END = "STREAM_END"          # Stream session complete
    STREAM_ERROR = "STREAM_ERROR"      # Stream failure

    # Embeddings (Issue #19)
    EMBEDDING_REQUEST = "EMBEDDING_REQUEST"    # Request embedding computation
    EMBEDDING_RESULT = "EMBEDDING_RESULT"      # Return computed embedding
    SIMILARITY_QUERY = "SIMILARITY_QUERY"      # Find similar content
    SIMILARITY_RESULT = "SIMILARITY_RESULT"    # Return similarity results


class InsightType(Enum):
    """Types of insights agents can share."""
    DISCOVERY = "discovery"      # Found something useful
    BLOCKER = "blocker"          # Hit a wall
    PATTERN = "pattern"          # Noticed a convention
    QUESTION = "question"        # Need clarification
    WARNING = "warning"          # Potential issue
    DOCS_NEEDED = "docs_needed"  # Documentation update required (Issue #87)
    DOCS_UPDATED = "docs_updated"  # Documentation completed (Issue #87)


class BoundaryType(Enum):
    """Types of boundaries agents must respect."""
    FILE_PATTERN = "file_pattern"      # Can only touch certain files
    TOOL_RESTRICTION = "tool_restriction"  # Limited tool access
    SCOPE_LIMIT = "scope_limit"        # Stay within task scope
    TIME_LIMIT = "time_limit"          # Don't run forever
    COST_LIMIT = "cost_limit"          # Token/API cost awareness
    HUMAN_GATE = "human_gate"          # Requires human approval


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentIdentity:
    """Identifies an agent in the mesh."""
    id: str                          # Unique instance ID
    name: str                        # Agent type (e.g., "code-reviewer")
    session_id: str                  # Power mode session
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __hash__(self):
        return hash(self.id)


@dataclass
class Boundary:
    """A constraint that agents must respect."""
    type: BoundaryType
    description: str
    value: Any                       # The actual constraint
    enforced: bool = True            # Hard vs soft boundary
    violation_action: str = "alert"  # "alert", "block", "human_required"


@dataclass
class Objective:
    """The goal agents are working toward."""
    id: str
    description: str                 # Human-readable goal
    success_criteria: List[str]      # How we know we're done
    boundaries: List[Boundary]       # What agents can't do
    phases: List[str]                # Ordered phases of work
    current_phase: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['boundaries'] = [asdict(b) for b in self.boundaries]
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Objective':
        d['boundaries'] = [Boundary(**b) for b in d.get('boundaries', [])]
        return cls(**d)


@dataclass
class AgentState:
    """Current state of an agent for check-ins."""
    agent: AgentIdentity
    progress: float                  # 0.0 to 1.0
    current_task: str
    files_touched: List[str]
    tools_used: List[str]
    tool_call_count: int
    decisions: List[Dict[str, Any]]  # {decision, reasoning, confidence}
    blockers: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['agent'] = asdict(self.agent)
        return d


@dataclass
class Insight:
    """A piece of knowledge to share with other agents."""
    id: str
    type: InsightType
    content: str
    from_agent: str
    relevance_tags: List[str]        # For filtering
    confidence: float                # 0.0 to 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    consumed_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['type'] = self.type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Insight':
        d['type'] = InsightType(d['type'])
        return cls(**d)


@dataclass
class Message:
    """A message in the power mode mesh network."""
    id: str
    type: MessageType
    from_agent: str                  # Agent ID or "coordinator"
    to_agent: str                    # Agent ID, "*" for broadcast, or "coordinator"
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    requires_ack: bool = False
    ttl_seconds: int = 300           # Message expires after 5 min

    def to_json(self) -> str:
        d = asdict(self)
        d['type'] = self.type.value
        return json.dumps(d)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        d = json.loads(json_str)
        d['type'] = MessageType(d['type'])
        return cls(**d)


@dataclass
class StreamChunk:
    """
    Represents a streaming data chunk (Issue #23).

    Used for real-time streaming updates during tool execution.
    """
    session_id: str                  # Unique stream session ID
    agent_id: str                    # Source agent
    chunk_index: int                 # Sequence number (0-based)
    content: str                     # Partial content
    tool_name: Optional[str] = None  # Tool being executed
    is_final: bool = False           # Last chunk in stream
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> Message:
        """Convert to a Message for pub/sub transmission."""
        return Message(
            id=f"{self.session_id}:{self.chunk_index}",
            type=MessageType.STREAM_CHUNK,
            from_agent=self.agent_id,
            to_agent="coordinator",
            payload={
                "session_id": self.session_id,
                "chunk_index": self.chunk_index,
                "content": self.content,
                "tool_name": self.tool_name,
                "is_final": self.is_final,
                "metadata": self.metadata
            },
            timestamp=self.timestamp
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'StreamChunk':
        """Create from dictionary."""
        return cls(**d)

    @classmethod
    def from_message(cls, msg: Message) -> 'StreamChunk':
        """Create from a Message payload."""
        payload = msg.payload
        return cls(
            session_id=payload["session_id"],
            agent_id=msg.from_agent,
            chunk_index=payload["chunk_index"],
            content=payload["content"],
            tool_name=payload.get("tool_name"),
            is_final=payload.get("is_final", False),
            timestamp=msg.timestamp,
            metadata=payload.get("metadata", {})
        )


# =============================================================================
# GUARDRAILS
# =============================================================================

class Guardrails:
    """
    Enforces boundaries and prevents agents from "cheating" or going rogue.

    Key principle: Agents can explore within constraints, but unconventional
    approaches require human approval.
    """

    # Actions that ALWAYS require human approval
    HUMAN_REQUIRED_ACTIONS = {
        "delete_production_data",
        "modify_security_config",
        "push_to_main",
        "deploy_to_production",
        "modify_payment_code",
        "access_credentials",
        "modify_auth_system",
        "bulk_delete_files",
        "external_api_with_cost",
    }

    # File patterns that are off-limits without explicit permission
    PROTECTED_PATHS = {
        ".env*",
        "**/secrets/**",
        "**/credentials/**",
        "**/.git/**",
        "**/node_modules/**",
        "**/prod.config.*",
    }

    # Maximum tool calls before forced check-in
    MAX_TOOLS_WITHOUT_CHECKIN = 10

    # Maximum time an agent can run without reporting
    MAX_SILENT_SECONDS = 60

    def __init__(self, objective: Optional[Objective] = None):
        self.objective = objective
        self.violations: List[Dict] = []
        self.human_decisions: Dict[str, bool] = {}  # Cache of human approvals

    def check_action(self, agent_id: str, action: str, context: Dict) -> Dict:
        """
        Check if an action is allowed.

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "requires_human": bool,
                "suggestion": str (if not allowed)
            }
        """
        # Check absolute prohibitions
        if action in self.HUMAN_REQUIRED_ACTIONS:
            return {
                "allowed": False,
                "reason": f"Action '{action}' requires human approval",
                "requires_human": True,
                "suggestion": "Ask the human to approve this action"
            }

        # Check file path restrictions
        file_path = context.get("file_path", "")
        if self._matches_protected_path(file_path):
            return {
                "allowed": False,
                "reason": f"Path '{file_path}' is protected",
                "requires_human": True,
                "suggestion": "Request human approval to modify protected files"
            }

        # Check objective boundaries if set
        if self.objective:
            for boundary in self.objective.boundaries:
                if not boundary.enforced:
                    continue

                violation = self._check_boundary(boundary, action, context)
                if violation:
                    self.violations.append({
                        "agent": agent_id,
                        "action": action,
                        "boundary": boundary.description,
                        "timestamp": datetime.now().isoformat()
                    })

                    if boundary.violation_action == "block":
                        return {
                            "allowed": False,
                            "reason": f"Boundary violation: {boundary.description}",
                            "requires_human": False,
                            "suggestion": violation.get("suggestion", "Stay within scope")
                        }
                    elif boundary.violation_action == "human_required":
                        return {
                            "allowed": False,
                            "reason": f"Boundary '{boundary.description}' requires human approval",
                            "requires_human": True,
                            "suggestion": "Ask human to expand boundaries"
                        }

        return {"allowed": True, "reason": "Action permitted", "requires_human": False}

    def check_drift(self, agent_state: AgentState) -> Optional[Dict]:
        """
        Check if an agent has drifted from the objective.

        Returns drift info if detected, None otherwise.
        """
        if not self.objective:
            return None

        # Check if agent is working on unrelated files
        allowed_patterns = self._get_allowed_patterns()
        if allowed_patterns:
            for file in agent_state.files_touched:
                if not self._matches_any_pattern(file, allowed_patterns):
                    return {
                        "type": "file_drift",
                        "message": f"Agent touching file outside scope: {file}",
                        "severity": "warning"
                    }

        # Check if agent has been silent too long
        last_update = datetime.fromisoformat(agent_state.timestamp)
        silent_seconds = (datetime.now() - last_update).total_seconds()
        if silent_seconds > self.MAX_SILENT_SECONDS:
            return {
                "type": "silence_drift",
                "message": f"Agent silent for {silent_seconds:.0f}s",
                "severity": "warning"
            }

        # Check tool call count
        if agent_state.tool_call_count > self.MAX_TOOLS_WITHOUT_CHECKIN:
            return {
                "type": "checkin_overdue",
                "message": f"Agent has made {agent_state.tool_call_count} tool calls without check-in",
                "severity": "info"
            }

        return None

    def is_unconventional(self, approach: str, context: Dict) -> Dict:
        """
        Detect if an approach is unconventional and might be "cheating".

        Unconventional approaches require discussion with the human.
        """
        unconventional_patterns = [
            ("deleting tests to make them pass", "test", "delete"),
            ("disabling linting rules", "eslint", "disable"),
            ("hardcoding values", "hardcode", None),
            ("skipping validation", "skip", "valid"),
            ("bypassing auth", "bypass", "auth"),
            ("mock everything", "mock", "all"),
        ]

        approach_lower = approach.lower()

        for description, keyword1, keyword2 in unconventional_patterns:
            if keyword1 in approach_lower:
                if keyword2 is None or keyword2 in approach_lower:
                    return {
                        "is_unconventional": True,
                        "pattern": description,
                        "recommendation": "Discuss with human before proceeding"
                    }

        return {"is_unconventional": False}

    def _matches_protected_path(self, path: str) -> bool:
        """Check if path matches any protected pattern."""
        import fnmatch
        for pattern in self.PROTECTED_PATHS:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _matches_any_pattern(self, path: str, patterns: Set[str]) -> bool:
        """Check if path matches any of the given patterns."""
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _get_allowed_patterns(self) -> Set[str]:
        """Get file patterns allowed by the objective."""
        if not self.objective:
            return set()

        patterns = set()
        for boundary in self.objective.boundaries:
            if boundary.type == BoundaryType.FILE_PATTERN:
                if isinstance(boundary.value, list):
                    patterns.update(boundary.value)
                else:
                    patterns.add(boundary.value)
        return patterns

    def _check_boundary(self, boundary: Boundary, action: str, context: Dict) -> Optional[Dict]:
        """Check if action violates a specific boundary."""
        if boundary.type == BoundaryType.SCOPE_LIMIT:
            # Check if action is within scope keywords
            scope_keywords = boundary.value if isinstance(boundary.value, list) else [boundary.value]
            if not any(kw.lower() in action.lower() for kw in scope_keywords):
                return {"suggestion": f"Stay focused on: {', '.join(scope_keywords)}"}

        elif boundary.type == BoundaryType.TOOL_RESTRICTION:
            restricted_tools = boundary.value if isinstance(boundary.value, list) else [boundary.value]
            tool_name = context.get("tool_name", "")
            if tool_name in restricted_tools:
                return {"suggestion": f"Tool '{tool_name}' is restricted for this task"}

        return None


# =============================================================================
# REDIS CHANNELS
# =============================================================================

class Channels:
    """Redis channel names for the power mode mesh."""

    PREFIX = "pop"

    @classmethod
    def broadcast(cls) -> str:
        """Channel for coordinator broadcasts to all agents."""
        return f"{cls.PREFIX}:broadcast"

    @classmethod
    def agent(cls, agent_id: str) -> str:
        """Channel for direct messages to a specific agent."""
        return f"{cls.PREFIX}:agent:{agent_id}"

    @classmethod
    def heartbeat(cls) -> str:
        """Channel for agent heartbeats."""
        return f"{cls.PREFIX}:heartbeat"

    @classmethod
    def results(cls) -> str:
        """Channel for agent results."""
        return f"{cls.PREFIX}:results"

    @classmethod
    def insights(cls) -> str:
        """Channel for shared insights."""
        return f"{cls.PREFIX}:insights"

    @classmethod
    def coordinator(cls) -> str:
        """Channel for messages to coordinator."""
        return f"{cls.PREFIX}:coordinator"

    @classmethod
    def human(cls) -> str:
        """Channel for human-required decisions."""
        return f"{cls.PREFIX}:human"

    # Redis keys (not pub/sub channels)
    @classmethod
    def state_key(cls, agent_id: str) -> str:
        """Redis key for agent state hash."""
        return f"{cls.PREFIX}:state:{agent_id}"

    @classmethod
    def objective_key(cls) -> str:
        """Redis key for current objective."""
        return f"{cls.PREFIX}:objective"

    @classmethod
    def patterns_key(cls) -> str:
        """Redis key for learned patterns."""
        return f"{cls.PREFIX}:patterns"

    @classmethod
    def sync_barrier_key(cls, barrier_id: str) -> str:
        """Redis key for sync barrier state."""
        return f"{cls.PREFIX}:sync:{barrier_id}"


# =============================================================================
# MESSAGE FACTORY
# =============================================================================

class MessageFactory:
    """Factory for creating properly formatted messages."""

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique message ID."""
        return hashlib.md5(
            f"{datetime.now().isoformat()}{id(object())}".encode()
        ).hexdigest()[:12]

    @classmethod
    def task(cls, from_agent: str, to_agent: str, task: Dict) -> Message:
        """Create a task assignment message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.TASK,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=task,
            requires_ack=True
        )

    @classmethod
    def progress(cls, from_agent: str, progress: float, details: Dict) -> Message:
        """Create a progress update message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.PROGRESS,
            from_agent=from_agent,
            to_agent="coordinator",
            payload={"progress": progress, **details}
        )

    @classmethod
    def result(cls, from_agent: str, result: Dict) -> Message:
        """Create a task completion message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.RESULT,
            from_agent=from_agent,
            to_agent="coordinator",
            payload=result,
            requires_ack=True
        )

    @classmethod
    def heartbeat(cls, from_agent: str, state: AgentState) -> Message:
        """Create a heartbeat message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.HEARTBEAT,
            from_agent=from_agent,
            to_agent="coordinator",
            payload=state.to_dict(),
            ttl_seconds=60
        )

    @classmethod
    def insight(cls, from_agent: str, insight: Insight) -> Message:
        """Create an insight sharing message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.INSIGHT,
            from_agent=from_agent,
            to_agent="*",
            payload=insight.to_dict()
        )

    @classmethod
    def sync(cls, barrier_id: str, agents_required: List[str]) -> Message:
        """Create a sync barrier message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.SYNC,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "barrier_id": barrier_id,
                "agents_required": agents_required,
                "instruction": "Acknowledge when ready to proceed"
            },
            requires_ack=True
        )

    @classmethod
    def human_required(cls, from_agent: str, decision: Dict) -> Message:
        """Create a human-required decision message."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.HUMAN_REQUIRED,
            from_agent=from_agent,
            to_agent="human",
            payload={
                "decision_needed": decision.get("description"),
                "context": decision.get("context"),
                "options": decision.get("options", ["approve", "deny"]),
                "recommendation": decision.get("recommendation")
            },
            requires_ack=True,
            ttl_seconds=3600  # Human has 1 hour to respond
        )

    @classmethod
    def boundary_alert(cls, from_agent: str, violation: Dict) -> Message:
        """Create a boundary violation alert."""
        return Message(
            id=cls._generate_id(),
            type=MessageType.BOUNDARY_ALERT,
            from_agent=from_agent,
            to_agent="coordinator",
            payload=violation
        )


# =============================================================================
# UTILITIES
# =============================================================================

def create_objective(
    description: str,
    success_criteria: List[str],
    phases: List[str],
    file_patterns: Optional[List[str]] = None,
    restricted_tools: Optional[List[str]] = None,
    scope_keywords: Optional[List[str]] = None
) -> Objective:
    """
    Helper to create an objective with common boundaries.

    Args:
        description: Human-readable goal
        success_criteria: List of conditions for completion
        phases: Ordered list of phase names
        file_patterns: Optional list of allowed file patterns
        restricted_tools: Optional list of tools agents can't use
        scope_keywords: Optional keywords defining the scope
    """
    boundaries = []

    if file_patterns:
        boundaries.append(Boundary(
            type=BoundaryType.FILE_PATTERN,
            description="Allowed file patterns",
            value=file_patterns,
            violation_action="alert"
        ))

    if restricted_tools:
        boundaries.append(Boundary(
            type=BoundaryType.TOOL_RESTRICTION,
            description="Restricted tools",
            value=restricted_tools,
            violation_action="block"
        ))

    if scope_keywords:
        boundaries.append(Boundary(
            type=BoundaryType.SCOPE_LIMIT,
            description="Task scope",
            value=scope_keywords,
            violation_action="alert"
        ))

    # Always add time limit
    boundaries.append(Boundary(
        type=BoundaryType.TIME_LIMIT,
        description="Maximum runtime",
        value=1800,  # 30 minutes default
        violation_action="human_required"
    ))

    return Objective(
        id=hashlib.md5(description.encode()).hexdigest()[:8],
        description=description,
        success_criteria=success_criteria,
        boundaries=boundaries,
        phases=phases
    )


if __name__ == "__main__":
    # Example usage
    objective = create_objective(
        description="Build user authentication with tests",
        success_criteria=[
            "Login endpoint works",
            "Tests pass",
            "Documentation updated"
        ],
        phases=["explore", "design", "implement", "test", "documentation", "review"],
        file_patterns=["src/auth/**", "tests/auth/**", "docs/auth.md"],
        scope_keywords=["auth", "login", "user", "session"]
    )

    print("Objective:", json.dumps(objective.to_dict(), indent=2))

    # Test guardrails
    guardrails = Guardrails(objective)

    result = guardrails.check_action("agent-1", "modify_security_config", {})
    print("\nSecurity config check:", result)

    result = guardrails.check_action("agent-1", "edit_file", {"file_path": ".env.local"})
    print("Env file check:", result)

    result = guardrails.is_unconventional("delete tests to make CI pass", {})
    print("Unconventional check:", result)
