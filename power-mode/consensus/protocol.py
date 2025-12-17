#!/usr/bin/env python3
"""
Consensus Mode Protocol
Message types, data structures, and protocol rules for multi-agent consensus.

Inspired by network consensus protocols:
- Raft: Term management, leader election, log replication
- PBFT: Pre-prepare, prepare, commit phases
- Paxos: Proposer, acceptor, learner roles
- Token Ring: Sequential, deterministic ordering for discussion
- Nakamoto: Eventually consistent with confidence scoring

Usage:
    Agents participate in structured discussions where they take turns
    contributing to a topic until consensus is reached.
"""

import json
import hashlib
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set


# =============================================================================
# CONSENSUS MESSAGE TYPES
# =============================================================================

class ConsensusMessageType(Enum):
    """Types of messages specific to consensus mode."""

    # Session lifecycle
    CONSENSUS_START = "CONSENSUS_START"          # Coordinator starts consensus
    CONSENSUS_END = "CONSENSUS_END"              # Consensus completed/aborted

    # Token ring operations
    TOKEN_GRANT = "TOKEN_GRANT"                  # Agent receives speaking turn
    TOKEN_RELEASE = "TOKEN_RELEASE"              # Agent finishes turn
    TOKEN_TIMEOUT = "TOKEN_TIMEOUT"              # Agent took too long
    TOKEN_SKIP = "TOKEN_SKIP"                    # Agent voluntarily skips

    # Discussion contributions
    CONTRIBUTION = "CONTRIBUTION"                # Agent's substantive input
    REACTION = "REACTION"                        # Quick reaction (agree/disagree/clarify)
    QUESTION = "QUESTION"                        # Agent asks for clarification
    PROPOSAL = "PROPOSAL"                        # Formal proposal for vote
    AMENDMENT = "AMENDMENT"                      # Modification to existing proposal

    # Voting
    VOTE_START = "VOTE_START"                    # Begin voting on proposal
    VOTE = "VOTE"                                # Individual vote
    VOTE_RESULT = "VOTE_RESULT"                  # Voting outcome

    # Consensus state
    CONSENSUS_REACHED = "CONSENSUS_REACHED"      # Agreement achieved
    CONSENSUS_BLOCKED = "CONSENSUS_BLOCKED"      # Cannot reach agreement
    CONSENSUS_DEFERRED = "CONSENSUS_DEFERRED"    # Need more info/time

    # Monitoring
    CONSENSUS_TRIGGER = "CONSENSUS_TRIGGER"      # External trigger event
    DEADLOCK_DETECTED = "DEADLOCK_DETECTED"      # Monitor detects stall
    DIVERGENCE_ALERT = "DIVERGENCE_ALERT"        # Agents too far apart


class ConsensusPhase(Enum):
    """Phases of a consensus session."""
    GATHERING = "gathering"          # Agents joining session
    PROPOSING = "proposing"          # Initial proposals being made
    DISCUSSING = "discussing"        # Open discussion (token ring)
    CONVERGING = "converging"        # Narrowing down to agreement
    VOTING = "voting"                # Formal voting
    COMMITTED = "committed"          # Consensus achieved
    ABORTED = "aborted"              # Consensus failed


class VoteType(Enum):
    """Types of votes agents can cast."""
    APPROVE = "approve"              # Fully support
    APPROVE_WITH_CONCERNS = "approve_with_concerns"  # Support with reservations
    ABSTAIN = "abstain"              # No opinion
    REQUEST_CHANGES = "request_changes"  # Support if modified
    REJECT = "reject"                # Cannot support


class TriggerType(Enum):
    """Types of events that can trigger consensus."""
    USER_REQUESTED = "user_requested"          # User explicitly asks for consensus
    AGENT_REQUESTED = "agent_requested"        # Agent detects need for consensus
    MONITOR_DETECTED = "monitor_detected"      # Monitor agent triggers
    CHECKPOINT_REACHED = "checkpoint_reached"  # System checkpoint
    CONFLICT_DETECTED = "conflict_detected"    # Conflicting agent outputs
    THRESHOLD_EXCEEDED = "threshold_exceeded"  # Disagreement threshold hit
    SCHEDULED = "scheduled"                    # Periodic consensus check
    PHASE_TRANSITION = "phase_transition"      # Between Power Mode phases


class ReactionType(Enum):
    """Quick reactions agents can make (like Slack emoji reactions)."""
    AGREE = "agree"                  # +1
    DISAGREE = "disagree"            # -1
    NEED_CLARIFICATION = "need_clarification"
    INTERESTING = "interesting"
    CONCERNING = "concerning"
    PARTIALLY_AGREE = "partially_agree"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConsensusParticipant:
    """An agent participating in consensus."""
    agent_id: str
    agent_name: str
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True
    contributions: int = 0
    votes_cast: int = 0
    current_stance: Optional[str] = None    # Brief summary of position
    confidence: float = 0.5                  # How confident in their stance

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'ConsensusParticipant':
        return cls(**d)


@dataclass
class Contribution:
    """A substantive contribution to the discussion."""
    id: str
    author_id: str
    author_name: str
    content: str
    contribution_type: str  # proposal, opinion, analysis, synthesis
    round_number: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    references: List[str] = field(default_factory=list)  # IDs of referenced contributions
    tags: List[str] = field(default_factory=list)
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # reaction_type -> agent_ids
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'Contribution':
        return cls(**d)


@dataclass
class Proposal:
    """A formal proposal for voting."""
    id: str
    author_id: str
    title: str
    description: str
    rationale: str
    implications: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    amendments: List['Amendment'] = field(default_factory=list)
    votes: Dict[str, 'Vote'] = field(default_factory=dict)  # agent_id -> vote
    status: str = "pending"  # pending, voting, approved, rejected, amended
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['amendments'] = [a.to_dict() for a in self.amendments]
        d['votes'] = {k: v.to_dict() for k, v in self.votes.items()}
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Proposal':
        d['amendments'] = [Amendment.from_dict(a) for a in d.get('amendments', [])]
        d['votes'] = {k: Vote.from_dict(v) for k, v in d.get('votes', {}).items()}
        return cls(**d)


@dataclass
class Amendment:
    """A modification to an existing proposal."""
    id: str
    proposal_id: str
    author_id: str
    change_description: str
    original_text: str
    proposed_text: str
    rationale: str
    accepted: Optional[bool] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'Amendment':
        return cls(**d)


@dataclass
class Vote:
    """An individual vote on a proposal."""
    agent_id: str
    vote_type: VoteType
    rationale: Optional[str] = None
    conditions: List[str] = field(default_factory=list)  # For approve_with_concerns
    requested_changes: List[str] = field(default_factory=list)  # For request_changes
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['vote_type'] = self.vote_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Vote':
        d['vote_type'] = VoteType(d['vote_type'])
        return cls(**d)


@dataclass
class TokenState:
    """State of the speaking token."""
    current_holder: Optional[str] = None
    holder_name: Optional[str] = None
    granted_at: Optional[str] = None
    turn_order: List[str] = field(default_factory=list)  # agent_ids in order
    current_index: int = 0
    skipped_agents: Set[str] = field(default_factory=set)
    timeout_seconds: int = 120

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['skipped_agents'] = list(self.skipped_agents)
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'TokenState':
        d['skipped_agents'] = set(d.get('skipped_agents', []))
        return cls(**d)


@dataclass
class ConsensusSession:
    """A complete consensus discussion session."""
    id: str
    topic: str
    description: str
    trigger_type: TriggerType
    trigger_context: Dict[str, Any] = field(default_factory=dict)

    # State
    phase: ConsensusPhase = ConsensusPhase.GATHERING
    round_number: int = 0
    max_rounds: int = 5

    # Participants
    participants: Dict[str, ConsensusParticipant] = field(default_factory=dict)
    min_participants: int = 2
    quorum: float = 0.67  # Percentage needed for quorum

    # Token ring
    token: TokenState = field(default_factory=TokenState)

    # Discussion history
    contributions: List[Contribution] = field(default_factory=list)
    proposals: Dict[str, Proposal] = field(default_factory=dict)

    # Outcome
    consensus_result: Optional[str] = None
    final_decision: Optional[Dict] = None

    # Timing
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    timeout_minutes: int = 30

    def to_dict(self) -> Dict:
        d = {
            'id': self.id,
            'topic': self.topic,
            'description': self.description,
            'trigger_type': self.trigger_type.value,
            'trigger_context': self.trigger_context,
            'phase': self.phase.value,
            'round_number': self.round_number,
            'max_rounds': self.max_rounds,
            'participants': {k: v.to_dict() for k, v in self.participants.items()},
            'min_participants': self.min_participants,
            'quorum': self.quorum,
            'token': self.token.to_dict(),
            'contributions': [c.to_dict() for c in self.contributions],
            'proposals': {k: v.to_dict() for k, v in self.proposals.items()},
            'consensus_result': self.consensus_result,
            'final_decision': self.final_decision,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'timeout_minutes': self.timeout_minutes,
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'ConsensusSession':
        session = cls(
            id=d['id'],
            topic=d['topic'],
            description=d['description'],
            trigger_type=TriggerType(d['trigger_type']),
            trigger_context=d.get('trigger_context', {}),
            phase=ConsensusPhase(d.get('phase', 'gathering')),
            round_number=d.get('round_number', 0),
            max_rounds=d.get('max_rounds', 5),
            min_participants=d.get('min_participants', 2),
            quorum=d.get('quorum', 0.67),
            consensus_result=d.get('consensus_result'),
            final_decision=d.get('final_decision'),
            created_at=d.get('created_at', datetime.now().isoformat()),
            started_at=d.get('started_at'),
            ended_at=d.get('ended_at'),
            timeout_minutes=d.get('timeout_minutes', 30),
        )

        # Reconstruct participants
        for agent_id, p_data in d.get('participants', {}).items():
            session.participants[agent_id] = ConsensusParticipant.from_dict(p_data)

        # Reconstruct token state
        if 'token' in d:
            session.token = TokenState.from_dict(d['token'])

        # Reconstruct contributions
        for c_data in d.get('contributions', []):
            session.contributions.append(Contribution.from_dict(c_data))

        # Reconstruct proposals
        for prop_id, prop_data in d.get('proposals', {}).items():
            session.proposals[prop_id] = Proposal.from_dict(prop_data)

        return session


@dataclass
class ConsensusMessage:
    """A message in the consensus protocol."""
    id: str
    type: ConsensusMessageType
    session_id: str
    from_agent: str
    to_agent: str  # "*" for broadcast
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    round_number: int = 0
    requires_ack: bool = False
    ttl_seconds: int = 300

    def to_json(self) -> str:
        d = asdict(self)
        d['type'] = self.type.value
        return json.dumps(d)

    @classmethod
    def from_json(cls, json_str: str) -> 'ConsensusMessage':
        d = json.loads(json_str)
        d['type'] = ConsensusMessageType(d['type'])
        return cls(**d)


# =============================================================================
# MESSAGE FACTORY
# =============================================================================

class ConsensusMessageFactory:
    """Factory for creating consensus messages."""

    @staticmethod
    def _generate_id(prefix: str = "cmsg") -> str:
        """Generate a unique message ID."""
        return f"{prefix}-{hashlib.md5(f'{datetime.now().isoformat()}{id(object())}'.encode()).hexdigest()[:10]}"

    @classmethod
    def consensus_start(
        cls,
        session: ConsensusSession,
        invited_agents: List[str]
    ) -> ConsensusMessage:
        """Create a consensus start message."""
        return ConsensusMessage(
            id=cls._generate_id("start"),
            type=ConsensusMessageType.CONSENSUS_START,
            session_id=session.id,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "topic": session.topic,
                "description": session.description,
                "trigger_type": session.trigger_type.value,
                "invited_agents": invited_agents,
                "max_rounds": session.max_rounds,
                "timeout_minutes": session.timeout_minutes,
                "quorum": session.quorum,
            },
            requires_ack=True
        )

    @classmethod
    def token_grant(
        cls,
        session_id: str,
        to_agent: str,
        round_number: int,
        context: Dict[str, Any],
        timeout_seconds: int = 120
    ) -> ConsensusMessage:
        """Grant speaking token to an agent."""
        return ConsensusMessage(
            id=cls._generate_id("token"),
            type=ConsensusMessageType.TOKEN_GRANT,
            session_id=session_id,
            from_agent="coordinator",
            to_agent=to_agent,
            round_number=round_number,
            payload={
                "instruction": "You have the token. Review context, think, then contribute.",
                "previous_contributions": context.get("previous_contributions", []),
                "current_proposals": context.get("current_proposals", []),
                "discussion_summary": context.get("discussion_summary", ""),
                "your_previous_stance": context.get("your_previous_stance"),
                "timeout_seconds": timeout_seconds,
            },
            requires_ack=True,
            ttl_seconds=timeout_seconds + 30
        )

    @classmethod
    def contribution(
        cls,
        session_id: str,
        from_agent: str,
        content: str,
        contribution_type: str,
        round_number: int,
        references: List[str] = None,
        confidence: float = 0.5
    ) -> ConsensusMessage:
        """Agent submits a contribution."""
        return ConsensusMessage(
            id=cls._generate_id("contrib"),
            type=ConsensusMessageType.CONTRIBUTION,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="*",
            round_number=round_number,
            payload={
                "content": content,
                "contribution_type": contribution_type,
                "references": references or [],
                "confidence": confidence,
            }
        )

    @classmethod
    def proposal(
        cls,
        session_id: str,
        from_agent: str,
        title: str,
        description: str,
        rationale: str,
        implications: List[str] = None
    ) -> ConsensusMessage:
        """Agent submits a formal proposal."""
        return ConsensusMessage(
            id=cls._generate_id("prop"),
            type=ConsensusMessageType.PROPOSAL,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="*",
            payload={
                "title": title,
                "description": description,
                "rationale": rationale,
                "implications": implications or [],
            },
            requires_ack=True
        )

    @classmethod
    def vote(
        cls,
        session_id: str,
        from_agent: str,
        proposal_id: str,
        vote_type: VoteType,
        rationale: str = None,
        conditions: List[str] = None,
        requested_changes: List[str] = None
    ) -> ConsensusMessage:
        """Agent casts a vote."""
        return ConsensusMessage(
            id=cls._generate_id("vote"),
            type=ConsensusMessageType.VOTE,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="coordinator",
            payload={
                "proposal_id": proposal_id,
                "vote_type": vote_type.value,
                "rationale": rationale,
                "conditions": conditions or [],
                "requested_changes": requested_changes or [],
            }
        )

    @classmethod
    def vote_start(
        cls,
        session_id: str,
        proposal_id: str,
        proposal_summary: str,
        voting_agents: List[str],
        deadline_seconds: int = 60
    ) -> ConsensusMessage:
        """Start voting on a proposal."""
        return ConsensusMessage(
            id=cls._generate_id("vstart"),
            type=ConsensusMessageType.VOTE_START,
            session_id=session_id,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "proposal_id": proposal_id,
                "proposal_summary": proposal_summary,
                "voting_agents": voting_agents,
                "deadline_seconds": deadline_seconds,
                "vote_options": [v.value for v in VoteType],
            },
            requires_ack=True
        )

    @classmethod
    def vote_result(
        cls,
        session_id: str,
        proposal_id: str,
        approved: bool,
        vote_breakdown: Dict[str, int],
        total_votes: int,
        quorum_met: bool
    ) -> ConsensusMessage:
        """Announce voting results."""
        return ConsensusMessage(
            id=cls._generate_id("vresult"),
            type=ConsensusMessageType.VOTE_RESULT,
            session_id=session_id,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "proposal_id": proposal_id,
                "approved": approved,
                "vote_breakdown": vote_breakdown,
                "total_votes": total_votes,
                "quorum_met": quorum_met,
            }
        )

    @classmethod
    def consensus_reached(
        cls,
        session_id: str,
        decision: Dict[str, Any],
        winning_proposal_id: Optional[str],
        confidence: float
    ) -> ConsensusMessage:
        """Announce consensus reached."""
        return ConsensusMessage(
            id=cls._generate_id("reached"),
            type=ConsensusMessageType.CONSENSUS_REACHED,
            session_id=session_id,
            from_agent="coordinator",
            to_agent="*",
            payload={
                "decision": decision,
                "winning_proposal_id": winning_proposal_id,
                "confidence": confidence,
                "summary": decision.get("summary", ""),
            }
        )

    @classmethod
    def consensus_trigger(
        cls,
        trigger_type: TriggerType,
        topic: str,
        context: Dict[str, Any],
        suggested_agents: List[str] = None
    ) -> ConsensusMessage:
        """Trigger a new consensus session."""
        return ConsensusMessage(
            id=cls._generate_id("trigger"),
            type=ConsensusMessageType.CONSENSUS_TRIGGER,
            session_id="",  # Will be set by coordinator
            from_agent=context.get("trigger_source", "system"),
            to_agent="coordinator",
            payload={
                "trigger_type": trigger_type.value,
                "topic": topic,
                "context": context,
                "suggested_agents": suggested_agents or [],
                "priority": context.get("priority", "normal"),
            }
        )

    @classmethod
    def reaction(
        cls,
        session_id: str,
        from_agent: str,
        contribution_id: str,
        reaction_type: ReactionType,
        comment: str = None
    ) -> ConsensusMessage:
        """Quick reaction to a contribution."""
        return ConsensusMessage(
            id=cls._generate_id("react"),
            type=ConsensusMessageType.REACTION,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="*",
            payload={
                "contribution_id": contribution_id,
                "reaction_type": reaction_type.value,
                "comment": comment,
            }
        )

    @classmethod
    def token_release(
        cls,
        session_id: str,
        from_agent: str,
        contribution_id: Optional[str] = None
    ) -> ConsensusMessage:
        """Agent releases the token after contributing."""
        return ConsensusMessage(
            id=cls._generate_id("release"),
            type=ConsensusMessageType.TOKEN_RELEASE,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="coordinator",
            payload={
                "contribution_id": contribution_id,
                "ready_for_next": True,
            }
        )

    @classmethod
    def token_skip(
        cls,
        session_id: str,
        from_agent: str,
        reason: str = "nothing to add"
    ) -> ConsensusMessage:
        """Agent skips their turn."""
        return ConsensusMessage(
            id=cls._generate_id("skip"),
            type=ConsensusMessageType.TOKEN_SKIP,
            session_id=session_id,
            from_agent=from_agent,
            to_agent="coordinator",
            payload={
                "reason": reason,
            }
        )


# =============================================================================
# CONSENSUS CHANNELS
# =============================================================================

class ConsensusChannels:
    """Redis channel names for consensus mode."""

    PREFIX = "pop:consensus"

    @classmethod
    def session(cls, session_id: str) -> str:
        """Channel for a specific consensus session."""
        return f"{cls.PREFIX}:session:{session_id}"

    @classmethod
    def broadcast(cls) -> str:
        """Channel for consensus broadcasts."""
        return f"{cls.PREFIX}:broadcast"

    @classmethod
    def triggers(cls) -> str:
        """Channel for consensus triggers."""
        return f"{cls.PREFIX}:triggers"

    @classmethod
    def votes(cls, session_id: str) -> str:
        """Channel for votes in a session."""
        return f"{cls.PREFIX}:votes:{session_id}"

    @classmethod
    def agent(cls, agent_id: str) -> str:
        """Channel for direct consensus messages to an agent."""
        return f"{cls.PREFIX}:agent:{agent_id}"

    # Redis keys (not pub/sub)
    @classmethod
    def session_key(cls, session_id: str) -> str:
        """Redis key for session state."""
        return f"{cls.PREFIX}:state:{session_id}"

    @classmethod
    def active_sessions_key(cls) -> str:
        """Redis key for list of active sessions."""
        return f"{cls.PREFIX}:active"

    @classmethod
    def history_key(cls) -> str:
        """Redis key for consensus history."""
        return f"{cls.PREFIX}:history"


# =============================================================================
# CONSENSUS RULES
# =============================================================================

@dataclass
class ConsensusRules:
    """
    Rules governing consensus behavior.

    Based on network consensus protocol principles:
    - Quorum requirements (like Raft's majority)
    - Timeout handling (like PBFT view changes)
    - Finality conditions (like blockchain confirmations)
    """

    # Quorum rules
    min_participants: int = 2
    quorum_percentage: float = 0.67  # 2/3 majority (PBFT-inspired)
    approval_threshold: float = 0.60  # 60% approval to pass

    # Token rules
    token_timeout_seconds: int = 120
    max_consecutive_skips: int = 2  # Force contribution after 2 skips

    # Round rules
    max_rounds: int = 5
    rounds_before_forcing_vote: int = 3
    min_contributions_per_round: int = 1

    # Voting rules
    vote_timeout_seconds: int = 60
    allow_vote_change: bool = False
    anonymous_voting: bool = False

    # Convergence rules
    early_consensus_threshold: float = 0.90  # Skip remaining if 90% agree
    stagnation_threshold: int = 2  # Rounds without progress

    # Time limits
    session_timeout_minutes: int = 30
    max_contribution_length: int = 2000  # Characters

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'ConsensusRules':
        return cls(**d)

    @classmethod
    def permissive(cls) -> 'ConsensusRules':
        """Permissive rules for quick consensus."""
        return cls(
            quorum_percentage=0.50,
            approval_threshold=0.50,
            max_rounds=3,
            token_timeout_seconds=60,
        )

    @classmethod
    def strict(cls) -> 'ConsensusRules':
        """Strict rules for important decisions."""
        return cls(
            quorum_percentage=0.80,
            approval_threshold=0.75,
            max_rounds=7,
            early_consensus_threshold=0.95,
        )


# =============================================================================
# UTILITIES
# =============================================================================

def create_session(
    topic: str,
    description: str,
    trigger_type: TriggerType,
    trigger_context: Dict[str, Any] = None,
    rules: ConsensusRules = None
) -> ConsensusSession:
    """
    Create a new consensus session.

    Args:
        topic: Brief topic identifier
        description: Detailed description of what needs consensus
        trigger_type: What triggered this consensus
        trigger_context: Context about the trigger
        rules: Optional custom rules
    """
    rules = rules or ConsensusRules()

    session_id = hashlib.md5(
        f"{topic}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:12]

    return ConsensusSession(
        id=session_id,
        topic=topic,
        description=description,
        trigger_type=trigger_type,
        trigger_context=trigger_context or {},
        max_rounds=rules.max_rounds,
        min_participants=rules.min_participants,
        quorum=rules.quorum_percentage,
        timeout_minutes=rules.session_timeout_minutes,
    )


def calculate_vote_result(
    proposal: Proposal,
    rules: ConsensusRules,
    total_participants: int
) -> Dict[str, Any]:
    """
    Calculate voting result for a proposal.

    Returns result including whether approved, breakdown, and quorum status.
    """
    votes = proposal.votes

    # Count votes by type
    breakdown = {v.value: 0 for v in VoteType}
    for vote in votes.values():
        breakdown[vote.vote_type.value] += 1

    total_votes = len(votes)
    quorum_needed = int(total_participants * rules.quorum_percentage)
    quorum_met = total_votes >= quorum_needed

    # Calculate approval
    approvals = breakdown[VoteType.APPROVE.value] + breakdown[VoteType.APPROVE_WITH_CONCERNS.value]
    rejections = breakdown[VoteType.REJECT.value]

    approval_rate = approvals / total_votes if total_votes > 0 else 0
    approved = quorum_met and approval_rate >= rules.approval_threshold

    return {
        "approved": approved,
        "approval_rate": approval_rate,
        "total_votes": total_votes,
        "quorum_needed": quorum_needed,
        "quorum_met": quorum_met,
        "breakdown": breakdown,
        "has_concerns": breakdown[VoteType.APPROVE_WITH_CONCERNS.value] > 0,
        "change_requests": breakdown[VoteType.REQUEST_CHANGES.value],
    }


if __name__ == "__main__":
    # Example usage
    session = create_session(
        topic="Architecture Decision: Event-Driven vs Request-Response",
        description="Need to decide on communication pattern for microservices",
        trigger_type=TriggerType.AGENT_REQUESTED,
        trigger_context={"requested_by": "code-architect", "reason": "conflicting opinions"}
    )

    print("Session created:")
    print(json.dumps(session.to_dict(), indent=2, default=str))

    # Test message factory
    msg = ConsensusMessageFactory.token_grant(
        session_id=session.id,
        to_agent="agent-123",
        round_number=1,
        context={"previous_contributions": [], "discussion_summary": "Starting discussion..."}
    )

    print("\nToken grant message:")
    print(msg.to_json())
