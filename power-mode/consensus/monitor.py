#!/usr/bin/env python3
"""
Consensus Monitor Agent
Monitors Redis messages and agent activity to detect when consensus is needed.

The monitor agent is a specialized agent that:
1. Watches all Power Mode channels for signs of conflict
2. Tracks agent disagreements and divergence
3. Detects deadlocks and stalls
4. Triggers consensus sessions when thresholds are exceeded

Inspired by:
- Distributed system failure detectors
- Network intrusion detection systems
- PBFT view change mechanisms
"""

import json
import hashlib
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Issue #191: Use unified adapter for Upstash/Local Redis
try:
    from upstash_adapter import get_redis_client, BaseRedisClient, BasePubSub
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False

from consensus.protocol import (
    TriggerType, ConsensusChannels, ConsensusSession,
    ConsensusMessageFactory, ReactionType
)
from consensus.triggers import (
    TriggerManager, TriggerContext, ConflictTrigger,
    ThresholdTrigger, TriggerPublisher
)

# Import Power Mode protocol for monitoring
from protocol import (
    Message, MessageType, Channels, InsightType
)


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

@dataclass
class DetectionPattern:
    """A pattern that indicates consensus might be needed."""
    name: str
    description: str
    trigger_type: TriggerType
    threshold: float
    window_seconds: int = 300  # Time window to consider
    enabled: bool = True


# Common patterns to watch for
DETECTION_PATTERNS = [
    DetectionPattern(
        name="conflicting_edits",
        description="Multiple agents editing same files",
        trigger_type=TriggerType.CONFLICT_DETECTED,
        threshold=2.0,  # 2 agents on same file
        window_seconds=300
    ),
    DetectionPattern(
        name="opinion_divergence",
        description="Agents expressing opposite opinions",
        trigger_type=TriggerType.CONFLICT_DETECTED,
        threshold=0.6,  # Divergence score
        window_seconds=600
    ),
    DetectionPattern(
        name="repeated_corrections",
        description="Coordinator repeatedly correcting same agent",
        trigger_type=TriggerType.THRESHOLD_EXCEEDED,
        threshold=3.0,  # 3 corrections
        window_seconds=300
    ),
    DetectionPattern(
        name="stalled_progress",
        description="No meaningful progress for extended period",
        trigger_type=TriggerType.CHECKPOINT_REACHED,
        threshold=5.0,  # 5 minutes of no progress
        window_seconds=300
    ),
    DetectionPattern(
        name="insight_contradictions",
        description="Agents sharing contradictory insights",
        trigger_type=TriggerType.CONFLICT_DETECTED,
        threshold=2.0,  # 2 contradicting insights
        window_seconds=300
    ),
    DetectionPattern(
        name="human_escalation_cluster",
        description="Multiple human-required decisions in short time",
        trigger_type=TriggerType.CHECKPOINT_REACHED,
        threshold=3.0,  # 3 escalations
        window_seconds=180
    ),
]


# =============================================================================
# AGENT TRACKER
# =============================================================================

@dataclass
class AgentActivity:
    """Tracks an agent's recent activity."""
    agent_id: str
    agent_name: str
    last_heartbeat: Optional[datetime] = None
    last_result: Optional[datetime] = None
    files_touched: Set[str] = field(default_factory=set)
    tools_used: List[str] = field(default_factory=list)
    insights_shared: List[Dict] = field(default_factory=list)
    opinions: Dict[str, str] = field(default_factory=dict)  # topic -> stance
    corrections_received: int = 0
    progress: float = 0.0


class AgentTracker:
    """Tracks activity of all agents in the mesh."""

    def __init__(self):
        self.agents: Dict[str, AgentActivity] = {}
        self._lock = threading.Lock()

    def update_from_heartbeat(self, agent_id: str, state: Dict):
        """Update agent activity from heartbeat."""
        with self._lock:
            if agent_id not in self.agents:
                self.agents[agent_id] = AgentActivity(
                    agent_id=agent_id,
                    agent_name=state.get("agent", {}).get("name", agent_id)
                )

            agent = self.agents[agent_id]
            agent.last_heartbeat = datetime.now()
            agent.progress = state.get("progress", 0.0)

            # Update files
            for f in state.get("files_touched", []):
                agent.files_touched.add(f)

            # Update tools
            agent.tools_used.extend(state.get("tools_used", []))
            agent.tools_used = agent.tools_used[-50:]  # Keep last 50

    def update_from_insight(self, agent_id: str, insight: Dict):
        """Update agent activity from shared insight."""
        with self._lock:
            if agent_id not in self.agents:
                return

            agent = self.agents[agent_id]
            agent.insights_shared.append({
                "insight": insight,
                "timestamp": datetime.now().isoformat()
            })
            agent.insights_shared = agent.insights_shared[-20:]  # Keep last 20

    def record_correction(self, agent_id: str):
        """Record that agent received a correction."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].corrections_received += 1

    def get_file_conflicts(self) -> List[Tuple[str, List[str]]]:
        """Get files being touched by multiple agents."""
        with self._lock:
            file_agents: Dict[str, List[str]] = defaultdict(list)

            for agent_id, activity in self.agents.items():
                for f in activity.files_touched:
                    file_agents[f].append(agent_id)

            return [
                (f, agents) for f, agents in file_agents.items()
                if len(agents) > 1
            ]

    def get_stalled_agents(self, threshold_seconds: int = 120) -> List[str]:
        """Get agents that haven't reported progress recently."""
        with self._lock:
            now = datetime.now()
            stalled = []

            for agent_id, activity in self.agents.items():
                if activity.last_heartbeat:
                    elapsed = (now - activity.last_heartbeat).total_seconds()
                    if elapsed > threshold_seconds:
                        stalled.append(agent_id)

            return stalled

    def get_heavily_corrected_agents(self, threshold: int = 3) -> List[str]:
        """Get agents that have been corrected multiple times."""
        with self._lock:
            return [
                agent_id for agent_id, activity in self.agents.items()
                if activity.corrections_received >= threshold
            ]


# =============================================================================
# MESSAGE ANALYZER
# =============================================================================

class MessageAnalyzer:
    """Analyzes messages for conflict and consensus indicators."""

    def __init__(self):
        self.message_history: List[Dict] = []
        self.max_history = 200
        self._lock = threading.Lock()

        # Tracking
        self.opinion_registry: Dict[str, Dict[str, str]] = defaultdict(dict)  # topic -> agent -> stance
        self.contradictions: List[Dict] = []

    def record_message(self, msg: Message):
        """Record a message for analysis."""
        with self._lock:
            self.message_history.append({
                "id": msg.id,
                "type": msg.type.value,
                "from": msg.from_agent,
                "to": msg.to_agent,
                "payload": msg.payload,
                "timestamp": datetime.now().isoformat()
            })

            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]

            # Analyze specific message types
            self._analyze_message(msg)

    def _analyze_message(self, msg: Message):
        """Analyze a specific message."""
        if msg.type == MessageType.INSIGHT:
            self._analyze_insight(msg)
        elif msg.type == MessageType.COURSE_CORRECT:
            self._record_correction(msg)

    def _analyze_insight(self, msg: Message):
        """Analyze an insight for potential conflicts."""
        payload = msg.payload
        insight_type = payload.get("type", "")
        content = payload.get("content", "").lower()

        # Look for opinion expressions
        opinion_words = {
            "approve": ["good", "recommend", "should", "yes", "agree", "better"],
            "reject": ["bad", "avoid", "shouldn't", "no", "disagree", "worse"],
        }

        # Check if insight expresses an opinion
        tags = payload.get("relevance_tags", [])
        for tag in tags:
            stance = "neutral"
            for opinion, words in opinion_words.items():
                if any(w in content for w in words):
                    stance = opinion
                    break

            if stance != "neutral":
                self._record_opinion(tag, msg.from_agent, stance)

    def _record_opinion(self, topic: str, agent_id: str, stance: str):
        """Record an agent's opinion on a topic."""
        # Check for contradiction
        if topic in self.opinion_registry:
            for other_agent, other_stance in self.opinion_registry[topic].items():
                if other_agent != agent_id:
                    if (stance == "approve" and other_stance == "reject") or \
                       (stance == "reject" and other_stance == "approve"):
                        self.contradictions.append({
                            "topic": topic,
                            "agents": [agent_id, other_agent],
                            "stances": {agent_id: stance, other_agent: other_stance},
                            "timestamp": datetime.now().isoformat()
                        })

        self.opinion_registry[topic][agent_id] = stance

    def _record_correction(self, msg: Message):
        """Record a course correction."""
        # Corrections are tracked in AgentTracker
        pass

    def get_divergence_score(self) -> float:
        """Calculate overall opinion divergence score."""
        with self._lock:
            if not self.opinion_registry:
                return 0.0

            total_topics = len(self.opinion_registry)
            conflicting_topics = 0

            for topic, opinions in self.opinion_registry.items():
                stances = set(opinions.values())
                if len(stances) > 1 and "approve" in stances and "reject" in stances:
                    conflicting_topics += 1

            return conflicting_topics / total_topics if total_topics > 0 else 0.0

    def get_recent_contradictions(self, window_seconds: int = 300) -> List[Dict]:
        """Get contradictions within time window."""
        with self._lock:
            cutoff = datetime.now() - timedelta(seconds=window_seconds)
            return [
                c for c in self.contradictions
                if datetime.fromisoformat(c["timestamp"]) > cutoff
            ]


# =============================================================================
# CONSENSUS MONITOR
# =============================================================================

class ConsensusMonitor:
    """
    Monitors the Power Mode mesh for situations requiring consensus.

    The monitor:
    1. Subscribes to all relevant Redis channels
    2. Tracks agent activity and messages
    3. Detects patterns indicating need for consensus
    4. Triggers consensus sessions when thresholds are exceeded
    """

    def __init__(self, patterns: List[DetectionPattern] = None):
        self.patterns = patterns or DETECTION_PATTERNS
        self.agent_tracker = AgentTracker()
        self.message_analyzer = MessageAnalyzer()
        self.trigger_manager = TriggerManager()
        self.trigger_publisher = TriggerPublisher()

        # Redis (Issue #191: supports Upstash or local)
        self.redis: Optional[BaseRedisClient] = None
        self.pubsub: Optional[BasePubSub] = None

        # State
        self.is_running = False
        self.detection_counts: Dict[str, int] = defaultdict(int)
        self.last_detection: Dict[str, datetime] = {}

        # Threads
        self._listener_thread: Optional[threading.Thread] = None
        self._analyzer_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_detection: Optional[callable] = None

    def connect(self) -> bool:
        """Connect to Upstash Redis.

        Issue #191: Uses Upstash cloud only (no local Redis).
        """
        if not REDIS_AVAILABLE:
            print("Redis adapter not available", file=sys.stderr)
            return False

        try:
            self.redis = get_redis_client()
            self.redis.ping()
            self.pubsub = self.redis.pubsub()
            self.trigger_publisher.redis = self.redis
            return True
        except Exception as e:
            print(f"Upstash connection failed: {e}", file=sys.stderr)
            return False

    def start(self):
        """Start monitoring."""
        if not self.redis:
            if not self.connect():
                return False

        self.is_running = True

        # Subscribe to Power Mode channels
        self.pubsub.subscribe(
            Channels.broadcast(),
            Channels.heartbeat(),
            Channels.results(),
            Channels.insights(),
            Channels.coordinator(),
        )

        # Start listener
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

        # Start analyzer
        self._analyzer_thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self._analyzer_thread.start()

        print("Consensus Monitor started")
        return True

    def stop(self):
        """Stop monitoring."""
        self.is_running = False

        if self.pubsub:
            self.pubsub.unsubscribe()

        if self._listener_thread:
            self._listener_thread.join(timeout=2)

        if self._analyzer_thread:
            self._analyzer_thread.join(timeout=2)

        print("Consensus Monitor stopped")

    def _listen_loop(self):
        """Listen for messages."""
        while self.is_running:
            try:
                message = self.pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    self._process_message(message["channel"], message["data"])
            except Exception as e:
                print(f"Monitor listener error: {e}", file=sys.stderr)

    def _process_message(self, channel: str, data: str):
        """Process an incoming message."""
        try:
            msg = Message.from_json(data)
            self.message_analyzer.record_message(msg)

            # Update agent tracker based on message type
            if msg.type == MessageType.HEARTBEAT:
                self.agent_tracker.update_from_heartbeat(
                    msg.from_agent,
                    msg.payload
                )
            elif msg.type == MessageType.INSIGHT:
                self.agent_tracker.update_from_insight(
                    msg.from_agent,
                    msg.payload
                )
            elif msg.type == MessageType.COURSE_CORRECT:
                self.agent_tracker.record_correction(msg.to_agent)

        except (json.JSONDecodeError, KeyError) as e:
            pass  # Ignore malformed messages

    def _analyze_loop(self):
        """Periodically analyze state for consensus triggers."""
        while self.is_running:
            try:
                self._check_patterns()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Monitor analyze error: {e}", file=sys.stderr)

    def _check_patterns(self):
        """Check all detection patterns."""
        for pattern in self.patterns:
            if not pattern.enabled:
                continue

            # Check cooldown
            if pattern.name in self.last_detection:
                elapsed = (datetime.now() - self.last_detection[pattern.name]).total_seconds()
                if elapsed < pattern.window_seconds:
                    continue

            # Check pattern
            detected, score, context = self._check_pattern(pattern)

            if detected and score >= pattern.threshold:
                self._handle_detection(pattern, score, context)

    def _check_pattern(self, pattern: DetectionPattern) -> Tuple[bool, float, Dict]:
        """Check a specific pattern. Returns (detected, score, context)."""

        if pattern.name == "conflicting_edits":
            conflicts = self.agent_tracker.get_file_conflicts()
            if conflicts:
                max_agents = max(len(agents) for _, agents in conflicts)
                return True, float(max_agents), {
                    "conflicts": [
                        {"file": f, "agents": a} for f, a in conflicts
                    ]
                }
            return False, 0.0, {}

        elif pattern.name == "opinion_divergence":
            score = self.message_analyzer.get_divergence_score()
            contradictions = self.message_analyzer.get_recent_contradictions(
                pattern.window_seconds
            )
            return score > 0, score, {"contradictions": contradictions}

        elif pattern.name == "repeated_corrections":
            agents = self.agent_tracker.get_heavily_corrected_agents(
                int(pattern.threshold)
            )
            if agents:
                return True, float(len(agents)), {"agents": agents}
            return False, 0.0, {}

        elif pattern.name == "stalled_progress":
            stalled = self.agent_tracker.get_stalled_agents(
                int(pattern.threshold * 60)  # Convert minutes to seconds
            )
            if stalled:
                return True, float(len(stalled)), {"stalled_agents": stalled}
            return False, 0.0, {}

        elif pattern.name == "insight_contradictions":
            contradictions = self.message_analyzer.get_recent_contradictions(
                pattern.window_seconds
            )
            return len(contradictions) > 0, float(len(contradictions)), {
                "contradictions": contradictions
            }

        elif pattern.name == "human_escalation_cluster":
            # Would need to track human escalations
            return False, 0.0, {}

        return False, 0.0, {}

    def _handle_detection(self, pattern: DetectionPattern, score: float, context: Dict):
        """Handle a pattern detection."""
        self.detection_counts[pattern.name] += 1
        self.last_detection[pattern.name] = datetime.now()

        # Build trigger context
        trigger_context = TriggerContext(
            trigger_type=pattern.trigger_type,
            source="monitor",
            topic=f"Monitor detected: {pattern.description}",
            description=f"{pattern.description} (score: {score:.2f})",
            priority="high" if score >= pattern.threshold * 1.5 else "normal",
            suggested_agents=context.get("agents", []),
            relevant_data={
                "pattern": pattern.name,
                "score": score,
                "threshold": pattern.threshold,
                "detection_data": context
            }
        )

        # Publish trigger
        self.trigger_publisher.publish_trigger(trigger_context)

        # Callback
        if self.on_detection:
            self.on_detection(pattern, score, context)

        print(f"Monitor detected {pattern.name}: score={score:.2f} threshold={pattern.threshold}")

    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            "is_running": self.is_running,
            "tracked_agents": len(self.agent_tracker.agents),
            "message_history_size": len(self.message_analyzer.message_history),
            "divergence_score": self.message_analyzer.get_divergence_score(),
            "detection_counts": dict(self.detection_counts),
            "last_detections": {
                k: v.isoformat() for k, v in self.last_detection.items()
            },
            "file_conflicts": self.agent_tracker.get_file_conflicts(),
            "recent_contradictions": self.message_analyzer.get_recent_contradictions()
        }

    def get_agents(self) -> Dict:
        """Get tracked agent information."""
        return {
            agent_id: {
                "name": activity.agent_name,
                "last_heartbeat": activity.last_heartbeat.isoformat() if activity.last_heartbeat else None,
                "progress": activity.progress,
                "files_touched": list(activity.files_touched),
                "corrections": activity.corrections_received
            }
            for agent_id, activity in self.agent_tracker.agents.items()
        }


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Consensus Monitor")
    parser.add_argument("command", choices=["start", "status"])
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=16379)

    args = parser.parse_args()

    monitor = ConsensusMonitor()

    if args.command == "start":
        if monitor.connect(args.host, args.port):
            monitor.start()
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop()
        else:
            print("Failed to connect")
            sys.exit(1)

    elif args.command == "status":
        if monitor.connect(args.host, args.port):
            print(json.dumps(monitor.get_status(), indent=2, default=str))


if __name__ == "__main__":
    main()
