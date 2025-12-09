"""
Consensus Mode - Multi-Agent Consensus Protocol

A structured consensus mechanism for multi-agent collaboration,
inspired by network consensus protocols (Raft, PBFT, Paxos, Token Ring).

Main Components:
- ConsensusCoordinator: Manages consensus sessions
- ConsensusTrigger: Various mechanisms to trigger consensus
- ConsensusMonitor: Watches for situations requiring consensus
- ConsensusAgentHook: Enables agents to participate

Usage:
    from consensus import ConsensusCoordinator, TriggerType

    # Create coordinator
    coordinator = ConsensusCoordinator()
    coordinator.connect()
    coordinator.start()

    # Create a session
    session = coordinator.create_session(
        topic="Architecture Decision",
        description="Should we use event-driven or request-response?",
        trigger_type=TriggerType.USER_REQUESTED,
        invited_agents=["agent-1", "agent-2", "agent-3"]
    )

    # Start discussion (agents take turns via token ring)
    coordinator.start_discussion(session.id)
"""

from consensus.protocol import (
    # Enums
    ConsensusMessageType,
    ConsensusPhase,
    VoteType,
    TriggerType,
    ReactionType,

    # Data classes
    ConsensusSession,
    ConsensusMessage,
    ConsensusParticipant,
    Contribution,
    Proposal,
    Amendment,
    Vote,
    TokenState,
    ConsensusRules,

    # Factory
    ConsensusMessageFactory,

    # Channels
    ConsensusChannels,

    # Utilities
    create_session,
    calculate_vote_result,
)

from consensus.coordinator import (
    ConsensusCoordinator,
    TokenRingManager,
    VoteCollector,
)

from consensus.triggers import (
    ConsensusTrigger,
    TriggerManager,
    TriggerContext,
    TriggerConfig,
    TriggerPublisher,

    # Trigger implementations
    UserRequestTrigger,
    AgentRequestTrigger,
    ConflictTrigger,
    ThresholdTrigger,
    CheckpointTrigger,
    PhaseTransitionTrigger,
    ScheduledTrigger,
)

from consensus.monitor import (
    ConsensusMonitor,
    AgentTracker,
    MessageAnalyzer,
    DetectionPattern,
    DETECTION_PATTERNS,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "ConsensusCoordinator",
    "ConsensusSession",
    "ConsensusMessage",

    # Enums
    "ConsensusMessageType",
    "ConsensusPhase",
    "VoteType",
    "TriggerType",
    "ReactionType",

    # Data
    "ConsensusParticipant",
    "Contribution",
    "Proposal",
    "Amendment",
    "Vote",
    "TokenState",
    "ConsensusRules",

    # Factory/Channels
    "ConsensusMessageFactory",
    "ConsensusChannels",

    # Coordinator components
    "TokenRingManager",
    "VoteCollector",

    # Triggers
    "ConsensusTrigger",
    "TriggerManager",
    "TriggerContext",
    "TriggerConfig",
    "TriggerPublisher",
    "UserRequestTrigger",
    "AgentRequestTrigger",
    "ConflictTrigger",
    "ThresholdTrigger",
    "CheckpointTrigger",
    "PhaseTransitionTrigger",
    "ScheduledTrigger",

    # Monitor
    "ConsensusMonitor",
    "AgentTracker",
    "MessageAnalyzer",
    "DetectionPattern",
    "DETECTION_PATTERNS",

    # Utilities
    "create_session",
    "calculate_vote_result",
]
