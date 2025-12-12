#!/usr/bin/env python3
"""
Consensus Triggers
Various mechanisms that can trigger a consensus session.

Trigger Types:
1. USER_REQUESTED - User explicitly requests consensus
2. AGENT_REQUESTED - Agent detects need for group decision
3. MONITOR_DETECTED - Monitor agent detects conflict/divergence
4. CHECKPOINT_REACHED - System checkpoint requires sync
5. CONFLICT_DETECTED - Conflicting outputs from agents
6. THRESHOLD_EXCEEDED - Disagreement threshold hit
7. SCHEDULED - Periodic consensus check
8. PHASE_TRANSITION - Between Power Mode phases

Inspired by:
- Event-driven architectures
- Distributed system failure detectors
- Consensus protocol view changes (PBFT)
"""

import json
import hashlib
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Issue #191: Use unified adapter for Upstash/Local Redis
try:
    from upstash_adapter import get_redis_client, BaseRedisClient
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False

from consensus.protocol import (
    TriggerType, ConsensusMessageFactory, ConsensusChannels,
    ConsensusMessage, ConsensusMessageType
)


# =============================================================================
# TRIGGER CONFIGURATIONS
# =============================================================================

@dataclass
class TriggerConfig:
    """Configuration for a trigger type."""
    enabled: bool = True
    priority: str = "normal"  # low, normal, high, critical
    cooldown_seconds: int = 300  # Min time between triggers of this type
    required_agents: int = 2     # Min agents needed
    auto_start: bool = False     # Auto-start discussion or wait for joins


@dataclass
class ConflictThresholds:
    """Thresholds for detecting conflicts."""
    disagreement_score: float = 0.6   # Score above which = conflict
    min_contributions: int = 3         # Min contributions to detect conflict
    sentiment_variance: float = 0.4    # Variance in sentiment = conflict
    opinion_clusters: int = 3          # Multiple clusters = fragmented


@dataclass
class TriggerContext:
    """Context passed when triggering consensus."""
    trigger_type: TriggerType
    source: str                         # What/who triggered it
    topic: str
    description: str
    priority: str = "normal"
    suggested_agents: List[str] = field(default_factory=list)
    relevant_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['trigger_type'] = self.trigger_type.value
        return d


# =============================================================================
# BASE TRIGGER CLASS
# =============================================================================

class ConsensusTrigger(ABC):
    """
    Abstract base class for consensus triggers.

    Each trigger type implements its own detection logic and
    generates appropriate context for the consensus session.
    """

    def __init__(self, config: TriggerConfig = None):
        self.config = config or TriggerConfig()
        self.last_triggered: Optional[datetime] = None
        self._callbacks: List[Callable[[TriggerContext], None]] = []

    @property
    @abstractmethod
    def trigger_type(self) -> TriggerType:
        """Return the type of this trigger."""
        pass

    @abstractmethod
    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """
        Check if consensus should be triggered.

        Args:
            context: Current system/agent context

        Returns:
            TriggerContext if consensus should be triggered, None otherwise
        """
        pass

    def can_trigger(self) -> bool:
        """Check if trigger is allowed (respects cooldown)."""
        if not self.config.enabled:
            return False

        if self.last_triggered:
            elapsed = (datetime.now() - self.last_triggered).total_seconds()
            if elapsed < self.config.cooldown_seconds:
                return False

        return True

    def trigger(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """
        Attempt to trigger consensus.

        Returns TriggerContext if triggered, None if not.
        """
        if not self.can_trigger():
            return None

        trigger_context = self.check(context)
        if trigger_context:
            self.last_triggered = datetime.now()
            self._notify_callbacks(trigger_context)

        return trigger_context

    def on_trigger(self, callback: Callable[[TriggerContext], None]):
        """Register callback for when trigger fires."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, context: TriggerContext):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(context)
            except Exception as e:
                print(f"Trigger callback error: {e}", file=sys.stderr)


# =============================================================================
# TRIGGER IMPLEMENTATIONS
# =============================================================================

class UserRequestTrigger(ConsensusTrigger):
    """
    Triggered when user explicitly requests consensus.

    Usage:
        trigger.request("Should we use event-driven architecture?", ["agent-1", "agent-2"])
    """

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.USER_REQUESTED

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """User triggers are always valid if requested."""
        if context.get("user_requested"):
            return TriggerContext(
                trigger_type=self.trigger_type,
                source="user",
                topic=context.get("topic", "User-requested consensus"),
                description=context.get("description", context.get("topic", "")),
                priority=context.get("priority", "normal"),
                suggested_agents=context.get("agents", []),
                relevant_data=context.get("data", {})
            )
        return None

    def request(
        self,
        topic: str,
        agents: List[str],
        description: str = None,
        priority: str = "normal"
    ) -> Optional[TriggerContext]:
        """Explicit user request for consensus."""
        return self.trigger({
            "user_requested": True,
            "topic": topic,
            "description": description or topic,
            "agents": agents,
            "priority": priority
        })


class AgentRequestTrigger(ConsensusTrigger):
    """
    Triggered when an agent detects need for consensus.

    Agents can request consensus when they:
    - Encounter a decision they can't make alone
    - Detect conflicting approaches with other agents
    - Need group input on architecture/design decisions
    """

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.AGENT_REQUESTED

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check if agent has valid reason to request consensus."""
        if not context.get("agent_id"):
            return None

        reason = context.get("reason", "")
        confidence = context.get("confidence", 0.5)

        # Validate reason is substantial
        valid_reasons = [
            "architecture", "design", "approach", "conflict",
            "decision", "trade-off", "security", "performance"
        ]

        reason_lower = reason.lower()
        is_valid = any(r in reason_lower for r in valid_reasons)

        if is_valid and confidence >= 0.6:
            return TriggerContext(
                trigger_type=self.trigger_type,
                source=context["agent_id"],
                topic=context.get("topic", f"Agent {context['agent_id']} requests consensus"),
                description=reason,
                priority="normal" if confidence < 0.8 else "high",
                suggested_agents=context.get("suggested_agents", []),
                relevant_data={
                    "requesting_agent": context["agent_id"],
                    "confidence": confidence,
                    "reason": reason
                }
            )
        return None


class ConflictTrigger(ConsensusTrigger):
    """
    Triggered when conflicting outputs are detected from agents.

    Monitors agent outputs and triggers when:
    - Agents propose incompatible changes
    - Agents have opposite opinions on same topic
    - Multiple agents edit same file differently
    """

    def __init__(self, config: TriggerConfig = None, thresholds: ConflictThresholds = None):
        super().__init__(config)
        self.thresholds = thresholds or ConflictThresholds()
        self.recent_outputs: List[Dict] = []
        self.max_history = 50

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.CONFLICT_DETECTED

    def record_output(self, agent_id: str, output: Dict):
        """Record an agent output for conflict detection."""
        self.recent_outputs.append({
            "agent_id": agent_id,
            "output": output,
            "timestamp": datetime.now().isoformat()
        })

        # Trim history
        if len(self.recent_outputs) > self.max_history:
            self.recent_outputs = self.recent_outputs[-self.max_history:]

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check for conflicts in recent outputs."""
        if len(self.recent_outputs) < self.thresholds.min_contributions:
            return None

        conflicts = self._detect_conflicts()
        if conflicts:
            agents_involved = list(set(c["agents"] for c in conflicts))
            return TriggerContext(
                trigger_type=self.trigger_type,
                source="conflict_detector",
                topic=f"Conflict detected: {conflicts[0]['type']}",
                description=conflicts[0]["description"],
                priority="high",
                suggested_agents=agents_involved[0] if agents_involved else [],
                relevant_data={
                    "conflicts": conflicts,
                    "outputs_analyzed": len(self.recent_outputs)
                }
            )
        return None

    def _detect_conflicts(self) -> List[Dict]:
        """Detect conflicts in recent outputs."""
        conflicts = []

        # Check for file edit conflicts
        file_edits = {}
        for record in self.recent_outputs:
            output = record["output"]
            if "file_path" in output:
                path = output["file_path"]
                if path not in file_edits:
                    file_edits[path] = []
                file_edits[path].append({
                    "agent": record["agent_id"],
                    "change": output.get("change_type", "edit")
                })

        for path, edits in file_edits.items():
            if len(edits) > 1:
                agents = [e["agent"] for e in edits]
                if len(set(agents)) > 1:
                    conflicts.append({
                        "type": "file_conflict",
                        "description": f"Multiple agents editing {path}",
                        "agents": tuple(set(agents)),
                        "path": path
                    })

        # Check for opinion conflicts (simplified)
        opinions = {}
        for record in self.recent_outputs:
            output = record["output"]
            if "opinion_on" in output:
                topic = output["opinion_on"]
                if topic not in opinions:
                    opinions[topic] = []
                opinions[topic].append({
                    "agent": record["agent_id"],
                    "stance": output.get("stance", "neutral")
                })

        for topic, stances in opinions.items():
            unique_stances = set(s["stance"] for s in stances)
            if len(unique_stances) > 1 and "approve" in unique_stances and "reject" in unique_stances:
                agents = tuple(set(s["agent"] for s in stances))
                conflicts.append({
                    "type": "opinion_conflict",
                    "description": f"Conflicting opinions on {topic}",
                    "agents": agents,
                    "topic": topic
                })

        return conflicts


class ThresholdTrigger(ConsensusTrigger):
    """
    Triggered when disagreement threshold is exceeded.

    Monitors a metric (e.g., disagreement score) and triggers
    consensus when it exceeds the configured threshold.
    """

    def __init__(self, config: TriggerConfig = None, threshold: float = 0.6):
        super().__init__(config)
        self.threshold = threshold
        self.current_value = 0.0
        self.history: List[float] = []

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.THRESHOLD_EXCEEDED

    def update_value(self, value: float, context: str = ""):
        """Update the monitored value."""
        self.current_value = value
        self.history.append(value)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check if threshold is exceeded."""
        value = context.get("value", self.current_value)

        if value >= self.threshold:
            return TriggerContext(
                trigger_type=self.trigger_type,
                source="threshold_monitor",
                topic=context.get("topic", f"Threshold exceeded: {value:.2f}"),
                description=f"Metric exceeded threshold of {self.threshold}: current value is {value:.2f}",
                priority="high" if value >= self.threshold * 1.5 else "normal",
                suggested_agents=context.get("agents", []),
                relevant_data={
                    "threshold": self.threshold,
                    "current_value": value,
                    "history": self.history[-10:]
                }
            )
        return None


class CheckpointTrigger(ConsensusTrigger):
    """
    Triggered at system checkpoints.

    Checkpoints include:
    - Power Mode phase transitions
    - Milestone completion
    - Time-based intervals
    - Before critical operations
    """

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.CHECKPOINT_REACHED

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check if checkpoint requires consensus."""
        checkpoint_type = context.get("checkpoint_type")
        if not checkpoint_type:
            return None

        # Determine if this checkpoint needs consensus
        needs_consensus = self._checkpoint_needs_consensus(checkpoint_type, context)

        if needs_consensus:
            return TriggerContext(
                trigger_type=self.trigger_type,
                source=f"checkpoint:{checkpoint_type}",
                topic=f"Checkpoint consensus: {checkpoint_type}",
                description=context.get("description", f"Consensus needed at {checkpoint_type} checkpoint"),
                priority=context.get("priority", "normal"),
                suggested_agents=context.get("agents", []),
                relevant_data={
                    "checkpoint_type": checkpoint_type,
                    "checkpoint_data": context.get("data", {})
                }
            )
        return None

    def _checkpoint_needs_consensus(self, checkpoint_type: str, context: Dict) -> bool:
        """Determine if checkpoint type requires consensus."""
        # Checkpoints that always need consensus
        mandatory = [
            "architecture_decision",
            "security_change",
            "breaking_change",
            "api_design",
            "deployment_approval"
        ]

        if checkpoint_type in mandatory:
            return True

        # Checkpoints that need consensus if flagged
        if context.get("requires_consensus"):
            return True

        # Phase transitions may need consensus
        if checkpoint_type == "phase_transition":
            return context.get("significant_changes", False)

        return False


class PhaseTransitionTrigger(ConsensusTrigger):
    """
    Triggered during Power Mode phase transitions.

    Before moving to the next phase, this trigger can force
    consensus on the results of the current phase.
    """

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.PHASE_TRANSITION

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check if phase transition needs consensus."""
        current_phase = context.get("current_phase")
        next_phase = context.get("next_phase")
        phase_results = context.get("phase_results", {})

        if not current_phase or not next_phase:
            return None

        # Phases that benefit from consensus before proceeding
        consensus_phases = ["design", "architecture", "planning"]

        if current_phase in consensus_phases:
            return TriggerContext(
                trigger_type=self.trigger_type,
                source="phase_coordinator",
                topic=f"Phase transition: {current_phase} → {next_phase}",
                description=f"Consensus needed before transitioning from {current_phase} to {next_phase}",
                priority="normal",
                suggested_agents=context.get("active_agents", []),
                relevant_data={
                    "current_phase": current_phase,
                    "next_phase": next_phase,
                    "phase_results": phase_results
                }
            )
        return None


class ScheduledTrigger(ConsensusTrigger):
    """
    Triggered on a schedule (periodic consensus checks).

    Useful for:
    - Regular sync meetings between agents
    - Periodic progress reviews
    - Scheduled decision points
    """

    def __init__(self, config: TriggerConfig = None, interval_minutes: int = 30):
        super().__init__(config)
        self.interval_minutes = interval_minutes
        self.last_check: Optional[datetime] = None

    @property
    def trigger_type(self) -> TriggerType:
        return TriggerType.SCHEDULED

    def check(self, context: Dict[str, Any]) -> Optional[TriggerContext]:
        """Check if scheduled consensus is due."""
        now = datetime.now()

        if self.last_check:
            elapsed = (now - self.last_check).total_seconds() / 60
            if elapsed < self.interval_minutes:
                return None

        self.last_check = now

        # Check if there's anything to discuss
        pending_decisions = context.get("pending_decisions", [])
        active_agents = context.get("active_agents", [])

        if pending_decisions and len(active_agents) >= 2:
            return TriggerContext(
                trigger_type=self.trigger_type,
                source="scheduler",
                topic=f"Scheduled sync ({len(pending_decisions)} pending decisions)",
                description=f"Regular scheduled consensus check with {len(pending_decisions)} pending items",
                priority="low",
                suggested_agents=active_agents,
                relevant_data={
                    "pending_decisions": pending_decisions,
                    "interval_minutes": self.interval_minutes
                }
            )
        return None


# =============================================================================
# TRIGGER MANAGER
# =============================================================================

class TriggerManager:
    """
    Manages all consensus triggers.

    Responsibilities:
    - Register and configure triggers
    - Route trigger events to coordinator
    - Prevent trigger storms (debouncing)
    - Priority-based trigger handling
    """

    def __init__(self):
        self.triggers: Dict[TriggerType, ConsensusTrigger] = {}
        self.global_cooldown_seconds = 60  # Min time between any triggers
        self.last_global_trigger: Optional[datetime] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[TriggerContext], None]] = []

        # Initialize default triggers
        self._init_default_triggers()

    def _init_default_triggers(self):
        """Initialize default trigger instances."""
        self.triggers = {
            TriggerType.USER_REQUESTED: UserRequestTrigger(),
            TriggerType.AGENT_REQUESTED: AgentRequestTrigger(),
            TriggerType.CONFLICT_DETECTED: ConflictTrigger(),
            TriggerType.THRESHOLD_EXCEEDED: ThresholdTrigger(),
            TriggerType.CHECKPOINT_REACHED: CheckpointTrigger(),
            TriggerType.PHASE_TRANSITION: PhaseTransitionTrigger(),
            TriggerType.SCHEDULED: ScheduledTrigger(),
        }

        # Register callbacks
        for trigger in self.triggers.values():
            trigger.on_trigger(self._handle_trigger)

    def register_trigger(self, trigger: ConsensusTrigger):
        """Register a custom trigger."""
        self.triggers[trigger.trigger_type] = trigger
        trigger.on_trigger(self._handle_trigger)

    def on_trigger(self, callback: Callable[[TriggerContext], None]):
        """Register callback for when any trigger fires."""
        self._callbacks.append(callback)

    def check_all(self, context: Dict[str, Any]) -> List[TriggerContext]:
        """
        Check all triggers and return any that fire.

        Returns list of TriggerContexts in priority order.
        """
        fired = []

        with self._lock:
            # Check global cooldown
            if self.last_global_trigger:
                elapsed = (datetime.now() - self.last_global_trigger).total_seconds()
                if elapsed < self.global_cooldown_seconds:
                    return []

            for trigger in self.triggers.values():
                result = trigger.trigger(context)
                if result:
                    fired.append(result)

            if fired:
                self.last_global_trigger = datetime.now()

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        fired.sort(key=lambda x: priority_order.get(x.priority, 2))

        return fired

    def trigger_by_type(
        self,
        trigger_type: TriggerType,
        context: Dict[str, Any]
    ) -> Optional[TriggerContext]:
        """Trigger a specific trigger type."""
        trigger = self.triggers.get(trigger_type)
        if trigger:
            return trigger.trigger(context)
        return None

    def _handle_trigger(self, context: TriggerContext):
        """Handle a fired trigger."""
        for callback in self._callbacks:
            try:
                callback(context)
            except Exception as e:
                print(f"Trigger manager callback error: {e}", file=sys.stderr)

    def get_trigger_status(self) -> Dict:
        """Get status of all triggers."""
        return {
            trigger_type.value: {
                "enabled": trigger.config.enabled,
                "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None,
                "can_trigger": trigger.can_trigger()
            }
            for trigger_type, trigger in self.triggers.items()
        }


# =============================================================================
# REDIS TRIGGER PUBLISHER
# =============================================================================

class TriggerPublisher:
    """
    Publishes consensus triggers to Redis.

    Allows any component to trigger consensus by publishing
    to the triggers channel.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def connect(self, host: str = "localhost", port: int = 16379):
        """Connect to Redis (Upstash or local).

        Issue #191: Uses unified adapter - auto-detects Upstash vs local Redis.
        """
        if REDIS_AVAILABLE:
            self.redis = get_redis_client(local_host=host, local_port=port)

    def publish_trigger(self, context: TriggerContext):
        """Publish a trigger to Redis."""
        if not self.redis:
            return False

        msg = ConsensusMessageFactory.consensus_trigger(
            trigger_type=context.trigger_type,
            topic=context.topic,
            context=context.to_dict(),
            suggested_agents=context.suggested_agents
        )

        self.redis.publish(ConsensusChannels.triggers(), msg.to_json())
        return True

    def request_consensus(
        self,
        topic: str,
        description: str,
        agents: List[str],
        trigger_type: TriggerType = TriggerType.USER_REQUESTED,
        priority: str = "normal"
    ) -> bool:
        """
        Request a consensus session.

        This is the main API for external components to trigger consensus.
        """
        context = TriggerContext(
            trigger_type=trigger_type,
            source="api",
            topic=topic,
            description=description,
            priority=priority,
            suggested_agents=agents
        )

        return self.publish_trigger(context)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing triggers."""
    import argparse

    parser = argparse.ArgumentParser(description="Consensus Trigger CLI")
    parser.add_argument("command", choices=["trigger", "status"])
    parser.add_argument("--topic", help="Consensus topic")
    parser.add_argument("--agents", nargs="+", help="Agent IDs")
    parser.add_argument("--type", choices=[t.value for t in TriggerType], default="user_requested")

    args = parser.parse_args()

    if args.command == "trigger":
        if not args.topic:
            print("--topic is required")
            return

        publisher = TriggerPublisher()
        publisher.connect()

        success = publisher.request_consensus(
            topic=args.topic,
            description=args.topic,
            agents=args.agents or [],
            trigger_type=TriggerType(args.type)
        )

        print("Trigger published" if success else "Failed to publish")

    elif args.command == "status":
        manager = TriggerManager()
        print(json.dumps(manager.get_trigger_status(), indent=2))


if __name__ == "__main__":
    main()
