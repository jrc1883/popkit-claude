#!/usr/bin/env python3
"""
Consensus Coordinator
Manages consensus sessions using token-ring style turn-taking.

The coordinator:
1. Creates and manages consensus sessions
2. Distributes speaking tokens in round-robin order
3. Collects and aggregates contributions
4. Manages voting and calculates results
5. Determines when consensus is reached or blocked

Inspired by:
- Token Ring networks (IEEE 802.5) for ordered turn-taking
- Raft consensus for term management
- PBFT for multi-phase agreement
"""

import json
import hashlib
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from consensus.protocol import (
    ConsensusSession, ConsensusMessage, ConsensusMessageType,
    ConsensusPhase, ConsensusMessageFactory, ConsensusChannels,
    ConsensusRules, ConsensusParticipant, Contribution, Proposal,
    Vote, VoteType, TriggerType, TokenState, Amendment,
    create_session, calculate_vote_result
)


# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config() -> Dict:
    """Load consensus configuration."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)

    # Also check parent power-mode config
    parent_config = Path(__file__).parent.parent / "config.json"
    if parent_config.exists():
        with open(parent_config) as f:
            return json.load(f)

    return {}


CONFIG = load_config()


# =============================================================================
# STATE FILE MANAGEMENT
# =============================================================================

def get_state_file_path() -> Path:
    """Get path for consensus state file."""
    # Prefer project-local path
    project_path = Path.cwd() / ".claude" / "popkit" / "consensus-state.json"
    if project_path.parent.exists():
        return project_path

    # Fall back to home directory
    home_path = Path.home() / ".claude" / "popkit" / "consensus-state.json"
    home_path.parent.mkdir(parents=True, exist_ok=True)
    return home_path


# =============================================================================
# TOKEN RING MANAGER
# =============================================================================

class TokenRingManager:
    """
    Manages the speaking token in round-robin fashion.

    Like IEEE 802.5 Token Ring:
    - Only the token holder can "transmit" (contribute)
    - Token passes sequentially through participants
    - Timeouts prevent indefinite holding
    """

    def __init__(self, timeout_seconds: int = 120):
        self.state = TokenState(timeout_seconds=timeout_seconds)
        self._lock = threading.Lock()
        self._token_timer: Optional[threading.Timer] = None
        self._on_timeout: Optional[Callable[[str], None]] = None

    def initialize(self, participants: List[str]):
        """Initialize token ring with participants."""
        with self._lock:
            self.state.turn_order = list(participants)
            self.state.current_index = 0
            self.state.current_holder = None
            self.state.skipped_agents = set()

    def add_participant(self, agent_id: str, position: int = -1):
        """Add a participant to the ring."""
        with self._lock:
            if agent_id not in self.state.turn_order:
                if position < 0:
                    self.state.turn_order.append(agent_id)
                else:
                    self.state.turn_order.insert(position, agent_id)

    def remove_participant(self, agent_id: str):
        """Remove a participant from the ring."""
        with self._lock:
            if agent_id in self.state.turn_order:
                idx = self.state.turn_order.index(agent_id)
                self.state.turn_order.remove(agent_id)
                # Adjust current index if needed
                if idx <= self.state.current_index and self.state.current_index > 0:
                    self.state.current_index -= 1

    def grant_token(self, on_timeout: Callable[[str], None] = None) -> Optional[str]:
        """
        Grant token to next agent in line.

        Returns the agent_id who now holds the token, or None if no agents.
        """
        with self._lock:
            if not self.state.turn_order:
                return None

            # Cancel existing timer
            if self._token_timer:
                self._token_timer.cancel()

            # Get next agent
            agent_id = self.state.turn_order[self.state.current_index]
            self.state.current_holder = agent_id
            self.state.granted_at = datetime.now().isoformat()

            # Set up timeout
            self._on_timeout = on_timeout
            if on_timeout:
                self._token_timer = threading.Timer(
                    self.state.timeout_seconds,
                    self._handle_timeout
                )
                self._token_timer.start()

            return agent_id

    def release_token(self, agent_id: str) -> bool:
        """
        Release token and advance to next agent.

        Returns True if token was held by this agent.
        """
        with self._lock:
            if self.state.current_holder != agent_id:
                return False

            # Cancel timer
            if self._token_timer:
                self._token_timer.cancel()
                self._token_timer = None

            # Clear skip record for this agent
            self.state.skipped_agents.discard(agent_id)

            # Advance index
            self._advance_index()

            self.state.current_holder = None
            self.state.granted_at = None

            return True

    def skip_turn(self, agent_id: str) -> bool:
        """
        Agent skips their turn.

        Returns True if this was their turn to skip.
        """
        with self._lock:
            if self.state.current_holder != agent_id:
                return False

            # Record skip
            self.state.skipped_agents.add(agent_id)

            # Release token
            return self.release_token(agent_id)

    def _advance_index(self):
        """Advance to next participant."""
        self.state.current_index = (self.state.current_index + 1) % len(self.state.turn_order)

    def _handle_timeout(self):
        """Handle token timeout."""
        with self._lock:
            if self.state.current_holder and self._on_timeout:
                agent_id = self.state.current_holder
                self._advance_index()
                self.state.current_holder = None
                self.state.granted_at = None

        if agent_id and self._on_timeout:
            self._on_timeout(agent_id)

    def is_round_complete(self) -> bool:
        """Check if all agents have had a turn this round."""
        with self._lock:
            return self.state.current_index == 0 and self.state.current_holder is None

    def get_current_holder(self) -> Optional[str]:
        """Get current token holder."""
        return self.state.current_holder

    def get_turn_order(self) -> List[str]:
        """Get current turn order."""
        return list(self.state.turn_order)

    def get_remaining_this_round(self) -> List[str]:
        """Get agents who haven't had a turn this round."""
        with self._lock:
            return self.state.turn_order[self.state.current_index:]


# =============================================================================
# VOTE COLLECTOR
# =============================================================================

class VoteCollector:
    """Collects and tallies votes on proposals."""

    def __init__(self, rules: ConsensusRules):
        self.rules = rules
        self.votes: Dict[str, Dict[str, Vote]] = {}  # proposal_id -> agent_id -> vote
        self._lock = threading.Lock()

    def start_voting(self, proposal_id: str):
        """Start collecting votes for a proposal."""
        with self._lock:
            self.votes[proposal_id] = {}

    def record_vote(self, proposal_id: str, vote: Vote) -> bool:
        """
        Record a vote.

        Returns True if vote was recorded (new vote or change allowed).
        """
        with self._lock:
            if proposal_id not in self.votes:
                return False

            if vote.agent_id in self.votes[proposal_id] and not self.rules.allow_vote_change:
                return False

            self.votes[proposal_id][vote.agent_id] = vote
            return True

    def get_result(self, proposal_id: str, total_participants: int) -> Optional[Dict]:
        """Get voting result for a proposal."""
        with self._lock:
            if proposal_id not in self.votes:
                return None

            votes = self.votes[proposal_id]

            # Create a mock proposal with votes for calculation
            mock_proposal = Proposal(
                id=proposal_id,
                author_id="",
                title="",
                description="",
                rationale="",
                votes=votes
            )

            return calculate_vote_result(mock_proposal, self.rules, total_participants)

    def has_voted(self, proposal_id: str, agent_id: str) -> bool:
        """Check if agent has voted on proposal."""
        with self._lock:
            return (
                proposal_id in self.votes and
                agent_id in self.votes[proposal_id]
            )

    def get_pending_voters(self, proposal_id: str, all_agents: List[str]) -> List[str]:
        """Get agents who haven't voted yet."""
        with self._lock:
            if proposal_id not in self.votes:
                return all_agents
            voted = set(self.votes[proposal_id].keys())
            return [a for a in all_agents if a not in voted]


# =============================================================================
# CONSENSUS COORDINATOR
# =============================================================================

class ConsensusCoordinator:
    """
    Orchestrates multi-agent consensus sessions.

    Main responsibilities:
    1. Session lifecycle management
    2. Token ring coordination
    3. Contribution aggregation
    4. Vote management
    5. Consensus detection and declaration
    """

    def __init__(self, rules: ConsensusRules = None):
        self.rules = rules or ConsensusRules()
        self.sessions: Dict[str, ConsensusSession] = {}
        self.token_managers: Dict[str, TokenRingManager] = {}
        self.vote_collectors: Dict[str, VoteCollector] = {}

        # Redis connection
        self.redis: Optional['redis.Redis'] = None
        self.pubsub: Optional['redis.client.PubSub'] = None

        # State
        self.is_running = False
        self._lock = threading.Lock()

        # Callbacks
        self.on_consensus_reached: Optional[Callable[[ConsensusSession], None]] = None
        self.on_consensus_blocked: Optional[Callable[[ConsensusSession, str], None]] = None
        self.on_contribution: Optional[Callable[[str, Contribution], None]] = None

        # Threads
        self._listener_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            print("Redis not available. Using file-based fallback.", file=sys.stderr)
            return self._init_file_mode()

        try:
            redis_config = CONFIG.get("redis", {})
            self.redis = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 16379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                socket_timeout=redis_config.get("socket_timeout", 5),
                decode_responses=True
            )
            self.redis.ping()
            self.pubsub = self.redis.pubsub()
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}. Using file-based fallback.", file=sys.stderr)
            return self._init_file_mode()

    def _init_file_mode(self) -> bool:
        """Initialize file-based mode for consensus."""
        # Use the existing file fallback from power-mode
        try:
            from file_fallback import FileBasedPowerMode
            self.redis = FileBasedPowerMode()
            return True
        except ImportError:
            print("File fallback not available", file=sys.stderr)
            return False

    def start(self):
        """Start the consensus coordinator."""
        if not self.redis:
            if not self.connect():
                return False

        self.is_running = True

        # Subscribe to consensus channels
        if self.pubsub:
            self.pubsub.subscribe(
                ConsensusChannels.triggers(),
                ConsensusChannels.broadcast()
            )

            # Start listener thread
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()

        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        print("Consensus Coordinator started")
        return True

    def stop(self):
        """Stop the coordinator."""
        self.is_running = False

        if self.pubsub:
            self.pubsub.unsubscribe()

        if self._listener_thread:
            self._listener_thread.join(timeout=2)

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        # Save state
        self._save_state()

        print("Consensus Coordinator stopped")

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def create_session(
        self,
        topic: str,
        description: str,
        trigger_type: TriggerType,
        invited_agents: List[str],
        trigger_context: Dict[str, Any] = None,
        rules: ConsensusRules = None
    ) -> ConsensusSession:
        """
        Create a new consensus session.

        Args:
            topic: Brief topic identifier
            description: Full description requiring consensus
            trigger_type: What triggered this consensus
            invited_agents: Agent IDs to participate
            trigger_context: Context about trigger
            rules: Optional custom rules
        """
        rules = rules or self.rules

        session = create_session(
            topic=topic,
            description=description,
            trigger_type=trigger_type,
            trigger_context=trigger_context or {},
            rules=rules
        )

        # Initialize token ring
        token_manager = TokenRingManager(rules.token_timeout_seconds)
        token_manager.initialize(invited_agents)

        # Initialize vote collector
        vote_collector = VoteCollector(rules)

        with self._lock:
            self.sessions[session.id] = session
            self.token_managers[session.id] = token_manager
            self.vote_collectors[session.id] = vote_collector

        # Store in Redis
        self._store_session(session)

        # Broadcast session start
        self._broadcast(ConsensusMessageFactory.consensus_start(
            session=session,
            invited_agents=invited_agents
        ))

        return session

    def join_session(self, session_id: str, agent_id: str, agent_name: str) -> bool:
        """
        Agent joins a consensus session.

        Returns True if successfully joined.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            if session.phase not in (ConsensusPhase.GATHERING, ConsensusPhase.PROPOSING):
                return False

            # Add participant
            session.participants[agent_id] = ConsensusParticipant(
                agent_id=agent_id,
                agent_name=agent_name
            )

            # Add to token ring
            token_manager = self.token_managers.get(session_id)
            if token_manager:
                token_manager.add_participant(agent_id)

            self._store_session(session)
            return True

    def start_discussion(self, session_id: str) -> bool:
        """
        Start the discussion phase (begin token rotation).

        Returns True if discussion started.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            if len(session.participants) < session.min_participants:
                return False

            session.phase = ConsensusPhase.DISCUSSING
            session.started_at = datetime.now().isoformat()
            session.round_number = 1

            self._store_session(session)

        # Grant first token
        self._grant_next_token(session_id)

        return True

    def _grant_next_token(self, session_id: str):
        """Grant token to next agent in line."""
        with self._lock:
            session = self.sessions.get(session_id)
            token_manager = self.token_managers.get(session_id)

            if not session or not token_manager:
                return

            # Check if round is complete
            if token_manager.is_round_complete():
                session.round_number += 1

                # Check if max rounds reached
                if session.round_number > session.max_rounds:
                    self._transition_to_voting(session_id)
                    return

            # Grant token
            agent_id = token_manager.grant_token(
                on_timeout=lambda aid: self._handle_token_timeout(session_id, aid)
            )

            if agent_id:
                # Build context for agent
                context = self._build_token_context(session, agent_id)

                # Send token grant message
                msg = ConsensusMessageFactory.token_grant(
                    session_id=session_id,
                    to_agent=agent_id,
                    round_number=session.round_number,
                    context=context,
                    timeout_seconds=self.rules.token_timeout_seconds
                )

                self._send_to_agent(agent_id, msg)

                # Update session
                session.token = token_manager.state
                self._store_session(session)

    def _build_token_context(self, session: ConsensusSession, agent_id: str) -> Dict:
        """Build context to send with token grant."""
        # Get last N contributions
        recent = session.contributions[-5:] if session.contributions else []

        # Get current proposals
        proposals = [
            {"id": p.id, "title": p.title, "author": p.author_id}
            for p in session.proposals.values()
            if p.status == "pending"
        ]

        # Get agent's previous stance if any
        participant = session.participants.get(agent_id)
        previous_stance = participant.current_stance if participant else None

        # Summarize discussion
        summary = self._summarize_discussion(session)

        return {
            "previous_contributions": [c.to_dict() for c in recent],
            "current_proposals": proposals,
            "discussion_summary": summary,
            "your_previous_stance": previous_stance,
            "round_number": session.round_number,
            "remaining_rounds": session.max_rounds - session.round_number,
        }

    def _summarize_discussion(self, session: ConsensusSession) -> str:
        """Create a brief summary of the discussion so far."""
        if not session.contributions:
            return f"Discussion starting on: {session.topic}"

        # Count contributions by type
        type_counts = {}
        for c in session.contributions:
            type_counts[c.contribution_type] = type_counts.get(c.contribution_type, 0) + 1

        # Get unique stances
        stances = set()
        for p in session.participants.values():
            if p.current_stance:
                stances.add(p.current_stance[:50])

        summary = f"Round {session.round_number}/{session.max_rounds}. "
        summary += f"{len(session.contributions)} contributions "
        summary += f"({len(session.proposals)} proposals). "

        if stances:
            summary += f"Key positions: {'; '.join(list(stances)[:3])}"

        return summary

    def receive_contribution(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        contribution_type: str = "opinion",
        references: List[str] = None,
        confidence: float = 0.5
    ) -> Optional[Contribution]:
        """
        Receive a contribution from an agent.

        Returns the contribution if valid, None otherwise.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            token_manager = self.token_managers.get(session_id)

            if not session or not token_manager:
                return None

            # Verify agent has token
            if token_manager.get_current_holder() != agent_id:
                return None

            # Create contribution
            contrib = Contribution(
                id=hashlib.md5(f"{agent_id}{datetime.now()}".encode()).hexdigest()[:10],
                author_id=agent_id,
                author_name=session.participants[agent_id].agent_name,
                content=content[:self.rules.max_contribution_length],
                contribution_type=contribution_type,
                round_number=session.round_number,
                references=references or [],
                confidence=confidence
            )

            session.contributions.append(contrib)

            # Update participant stats
            if agent_id in session.participants:
                session.participants[agent_id].contributions += 1

            # Release token
            token_manager.release_token(agent_id)
            session.token = token_manager.state

            self._store_session(session)

        # Callback
        if self.on_contribution:
            self.on_contribution(session_id, contrib)

        # Broadcast contribution
        self._broadcast(ConsensusMessageFactory.contribution(
            session_id=session_id,
            from_agent=agent_id,
            content=content,
            contribution_type=contribution_type,
            round_number=session.round_number,
            references=references,
            confidence=confidence
        ))

        # Grant next token
        self._grant_next_token(session_id)

        return contrib

    def receive_proposal(
        self,
        session_id: str,
        agent_id: str,
        title: str,
        description: str,
        rationale: str,
        implications: List[str] = None
    ) -> Optional[Proposal]:
        """
        Receive a formal proposal from an agent.

        Returns the proposal if valid.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            # Create proposal
            proposal = Proposal(
                id=hashlib.md5(f"{agent_id}{title}{datetime.now()}".encode()).hexdigest()[:10],
                author_id=agent_id,
                title=title,
                description=description,
                rationale=rationale,
                implications=implications or []
            )

            session.proposals[proposal.id] = proposal
            self._store_session(session)

        # Broadcast proposal
        self._broadcast(ConsensusMessageFactory.proposal(
            session_id=session_id,
            from_agent=agent_id,
            title=title,
            description=description,
            rationale=rationale,
            implications=implications
        ))

        return proposal

    def skip_turn(self, session_id: str, agent_id: str, reason: str = "nothing to add") -> bool:
        """Agent skips their turn."""
        with self._lock:
            token_manager = self.token_managers.get(session_id)
            if not token_manager:
                return False

            if not token_manager.skip_turn(agent_id):
                return False

            session = self.sessions.get(session_id)
            if session:
                session.token = token_manager.state
                self._store_session(session)

        # Broadcast skip
        self._broadcast(ConsensusMessageFactory.token_skip(
            session_id=session_id,
            from_agent=agent_id,
            reason=reason
        ))

        # Grant next token
        self._grant_next_token(session_id)

        return True

    def _handle_token_timeout(self, session_id: str, agent_id: str):
        """Handle token timeout for an agent."""
        # Broadcast timeout
        self._broadcast(ConsensusMessage(
            id=hashlib.md5(f"timeout-{session_id}-{agent_id}".encode()).hexdigest()[:12],
            type=ConsensusMessageType.TOKEN_TIMEOUT,
            session_id=session_id,
            from_agent="coordinator",
            to_agent="*",
            payload={"agent_id": agent_id, "reason": "Token timeout"}
        ))

        # Grant next token
        self._grant_next_token(session_id)

    # =========================================================================
    # VOTING
    # =========================================================================

    def _transition_to_voting(self, session_id: str):
        """Transition session to voting phase."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            if not session.proposals:
                # No proposals - consensus blocked
                self._end_session(session_id, ConsensusPhase.ABORTED, "No proposals submitted")
                return

            session.phase = ConsensusPhase.VOTING
            self._store_session(session)

        # Start voting on each proposal
        for proposal_id, proposal in session.proposals.items():
            self._start_proposal_vote(session_id, proposal_id)

    def _start_proposal_vote(self, session_id: str, proposal_id: str):
        """Start voting on a specific proposal."""
        with self._lock:
            session = self.sessions.get(session_id)
            vote_collector = self.vote_collectors.get(session_id)

            if not session or not vote_collector:
                return

            proposal = session.proposals.get(proposal_id)
            if not proposal:
                return

            proposal.status = "voting"
            vote_collector.start_voting(proposal_id)

            self._store_session(session)

        # Broadcast vote start
        self._broadcast(ConsensusMessageFactory.vote_start(
            session_id=session_id,
            proposal_id=proposal_id,
            proposal_summary=f"{proposal.title}: {proposal.description}",
            voting_agents=list(session.participants.keys()),
            deadline_seconds=self.rules.vote_timeout_seconds
        ))

    def receive_vote(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        vote_type: VoteType,
        rationale: str = None,
        conditions: List[str] = None,
        requested_changes: List[str] = None
    ) -> bool:
        """
        Receive a vote from an agent.

        Returns True if vote was recorded.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            vote_collector = self.vote_collectors.get(session_id)

            if not session or not vote_collector:
                return False

            if session.phase != ConsensusPhase.VOTING:
                return False

            vote = Vote(
                agent_id=agent_id,
                vote_type=vote_type,
                rationale=rationale,
                conditions=conditions or [],
                requested_changes=requested_changes or []
            )

            if not vote_collector.record_vote(proposal_id, vote):
                return False

            # Update participant stats
            if agent_id in session.participants:
                session.participants[agent_id].votes_cast += 1

            # Check if all votes are in
            pending = vote_collector.get_pending_voters(
                proposal_id,
                list(session.participants.keys())
            )

            if not pending:
                self._finalize_proposal_vote(session_id, proposal_id)

            return True

    def _finalize_proposal_vote(self, session_id: str, proposal_id: str):
        """Finalize voting on a proposal."""
        with self._lock:
            session = self.sessions.get(session_id)
            vote_collector = self.vote_collectors.get(session_id)

            if not session or not vote_collector:
                return

            result = vote_collector.get_result(proposal_id, len(session.participants))
            if not result:
                return

            proposal = session.proposals.get(proposal_id)
            if proposal:
                proposal.status = "approved" if result["approved"] else "rejected"

            self._store_session(session)

        # Broadcast result
        self._broadcast(ConsensusMessageFactory.vote_result(
            session_id=session_id,
            proposal_id=proposal_id,
            approved=result["approved"],
            vote_breakdown=result["breakdown"],
            total_votes=result["total_votes"],
            quorum_met=result["quorum_met"]
        ))

        # Check if consensus is reached
        self._check_consensus(session_id)

    def _check_consensus(self, session_id: str):
        """Check if consensus has been reached."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            # Count approved proposals
            approved = [
                p for p in session.proposals.values()
                if p.status == "approved"
            ]

            pending = [
                p for p in session.proposals.values()
                if p.status == "voting"
            ]

            if pending:
                return  # Still voting

            if approved:
                # Consensus reached!
                winning = approved[0]  # Take first approved (could implement ranking)

                session.consensus_result = "approved"
                session.final_decision = {
                    "proposal_id": winning.id,
                    "title": winning.title,
                    "description": winning.description,
                    "summary": f"Consensus reached: {winning.title}"
                }

                self._end_session(session_id, ConsensusPhase.COMMITTED)

            else:
                # All rejected - blocked
                self._end_session(session_id, ConsensusPhase.ABORTED, "All proposals rejected")

    def _end_session(self, session_id: str, phase: ConsensusPhase, reason: str = None):
        """End a consensus session."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            session.phase = phase
            session.ended_at = datetime.now().isoformat()

            if reason and not session.consensus_result:
                session.consensus_result = reason

            self._store_session(session)

        # Callbacks
        if phase == ConsensusPhase.COMMITTED and self.on_consensus_reached:
            self.on_consensus_reached(session)
        elif phase == ConsensusPhase.ABORTED and self.on_consensus_blocked:
            self.on_consensus_blocked(session, reason or "Unknown reason")

        # Broadcast end
        if phase == ConsensusPhase.COMMITTED:
            self._broadcast(ConsensusMessageFactory.consensus_reached(
                session_id=session_id,
                decision=session.final_decision or {},
                winning_proposal_id=session.final_decision.get("proposal_id") if session.final_decision else None,
                confidence=0.8
            ))
        else:
            self._broadcast(ConsensusMessage(
                id=hashlib.md5(f"end-{session_id}".encode()).hexdigest()[:12],
                type=ConsensusMessageType.CONSENSUS_END,
                session_id=session_id,
                from_agent="coordinator",
                to_agent="*",
                payload={
                    "phase": phase.value,
                    "reason": reason,
                    "final_decision": session.final_decision
                }
            ))

    # =========================================================================
    # COMMUNICATION
    # =========================================================================

    def _broadcast(self, msg: ConsensusMessage):
        """Broadcast a message to all participants."""
        if self.redis:
            self.redis.publish(
                ConsensusChannels.session(msg.session_id),
                msg.to_json()
            )

    def _send_to_agent(self, agent_id: str, msg: ConsensusMessage):
        """Send a message to a specific agent."""
        if self.redis:
            self.redis.publish(
                ConsensusChannels.agent(agent_id),
                msg.to_json()
            )

    def _listen_loop(self):
        """Listen for incoming messages."""
        while self.is_running:
            try:
                message = self.pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    self._handle_message(message["channel"], message["data"])
            except Exception as e:
                print(f"Listener error: {e}", file=sys.stderr)

    def _handle_message(self, channel: str, data: str):
        """Handle an incoming message."""
        try:
            msg = ConsensusMessage.from_json(data)
        except (json.JSONDecodeError, KeyError):
            return

        handlers = {
            ConsensusMessageType.CONSENSUS_TRIGGER: self._handle_trigger,
            ConsensusMessageType.TOKEN_RELEASE: self._handle_token_release,
            ConsensusMessageType.TOKEN_SKIP: self._handle_token_skip_msg,
            ConsensusMessageType.CONTRIBUTION: self._handle_contribution_msg,
            ConsensusMessageType.PROPOSAL: self._handle_proposal_msg,
            ConsensusMessageType.VOTE: self._handle_vote_msg,
        }

        handler = handlers.get(msg.type)
        if handler:
            handler(msg)

    def _handle_trigger(self, msg: ConsensusMessage):
        """Handle consensus trigger message."""
        payload = msg.payload
        trigger_type = TriggerType(payload["trigger_type"])

        # Create session from trigger
        self.create_session(
            topic=payload["topic"],
            description=payload.get("context", {}).get("description", payload["topic"]),
            trigger_type=trigger_type,
            invited_agents=payload.get("suggested_agents", []),
            trigger_context=payload.get("context", {})
        )

    def _handle_token_release(self, msg: ConsensusMessage):
        """Handle token release message."""
        # Token release is handled in receive_contribution
        pass

    def _handle_token_skip_msg(self, msg: ConsensusMessage):
        """Handle token skip message."""
        self.skip_turn(
            msg.session_id,
            msg.from_agent,
            msg.payload.get("reason", "nothing to add")
        )

    def _handle_contribution_msg(self, msg: ConsensusMessage):
        """Handle contribution message."""
        self.receive_contribution(
            session_id=msg.session_id,
            agent_id=msg.from_agent,
            content=msg.payload["content"],
            contribution_type=msg.payload.get("contribution_type", "opinion"),
            references=msg.payload.get("references", []),
            confidence=msg.payload.get("confidence", 0.5)
        )

    def _handle_proposal_msg(self, msg: ConsensusMessage):
        """Handle proposal message."""
        self.receive_proposal(
            session_id=msg.session_id,
            agent_id=msg.from_agent,
            title=msg.payload["title"],
            description=msg.payload["description"],
            rationale=msg.payload["rationale"],
            implications=msg.payload.get("implications", [])
        )

    def _handle_vote_msg(self, msg: ConsensusMessage):
        """Handle vote message."""
        self.receive_vote(
            session_id=msg.session_id,
            agent_id=msg.from_agent,
            proposal_id=msg.payload["proposal_id"],
            vote_type=VoteType(msg.payload["vote_type"]),
            rationale=msg.payload.get("rationale"),
            conditions=msg.payload.get("conditions", []),
            requested_changes=msg.payload.get("requested_changes", [])
        )

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    def _store_session(self, session: ConsensusSession):
        """Store session state in Redis."""
        if self.redis:
            self.redis.set(
                ConsensusChannels.session_key(session.id),
                json.dumps(session.to_dict())
            )

            # Update active sessions list
            if session.phase not in (ConsensusPhase.COMMITTED, ConsensusPhase.ABORTED):
                self.redis.sadd(ConsensusChannels.active_sessions_key(), session.id)
            else:
                self.redis.srem(ConsensusChannels.active_sessions_key(), session.id)
                # Add to history
                self.redis.lpush(
                    ConsensusChannels.history_key(),
                    json.dumps(session.to_dict())
                )
                self.redis.ltrim(ConsensusChannels.history_key(), 0, 99)

    def _load_session(self, session_id: str) -> Optional[ConsensusSession]:
        """Load session from Redis."""
        if not self.redis:
            return self.sessions.get(session_id)

        data = self.redis.get(ConsensusChannels.session_key(session_id))
        if data:
            return ConsensusSession.from_dict(json.loads(data))
        return None

    def _save_state(self):
        """Save coordinator state to file."""
        state_file = get_state_file_path()
        state = {
            "active_sessions": list(self.sessions.keys()),
            "timestamp": datetime.now().isoformat()
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _monitor_loop(self):
        """Monitor sessions for timeouts and deadlocks."""
        while self.is_running:
            try:
                self._check_session_timeouts()
                self._check_deadlocks()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"Monitor error: {e}", file=sys.stderr)

    def _check_session_timeouts(self):
        """Check for timed out sessions."""
        with self._lock:
            now = datetime.now()
            for session_id, session in list(self.sessions.items()):
                if session.phase in (ConsensusPhase.COMMITTED, ConsensusPhase.ABORTED):
                    continue

                if session.started_at:
                    started = datetime.fromisoformat(session.started_at)
                    elapsed = (now - started).total_seconds() / 60

                    if elapsed > session.timeout_minutes:
                        self._end_session(session_id, ConsensusPhase.ABORTED, "Session timeout")

    def _check_deadlocks(self):
        """Check for stalled sessions (potential deadlocks)."""
        with self._lock:
            for session_id, session in self.sessions.items():
                if session.phase != ConsensusPhase.DISCUSSING:
                    continue

                # Check if no progress in recent rounds
                if len(session.contributions) > 0:
                    last_contrib = session.contributions[-1]
                    if session.round_number - last_contrib.round_number >= self.rules.stagnation_threshold:
                        # Stagnation detected - consider forcing vote
                        if session.round_number >= self.rules.rounds_before_forcing_vote:
                            self._transition_to_voting(session_id)

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def get_session(self, session_id: str) -> Optional[ConsensusSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id) or self._load_session(session_id)

    def get_active_sessions(self) -> List[ConsensusSession]:
        """Get all active consensus sessions."""
        return [
            s for s in self.sessions.values()
            if s.phase not in (ConsensusPhase.COMMITTED, ConsensusPhase.ABORTED)
        ]

    def get_status(self) -> Dict:
        """Get coordinator status."""
        return {
            "is_running": self.is_running,
            "active_sessions": len(self.get_active_sessions()),
            "total_sessions": len(self.sessions),
            "sessions": [
                {
                    "id": s.id,
                    "topic": s.topic,
                    "phase": s.phase.value,
                    "round": s.round_number,
                    "participants": len(s.participants)
                }
                for s in self.sessions.values()
            ]
        }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Consensus Mode Coordinator")
    parser.add_argument("command", choices=["start", "status", "stop", "create"])
    parser.add_argument("--topic", help="Consensus topic (for create)")
    parser.add_argument("--description", help="Topic description (for create)")
    parser.add_argument("--agents", nargs="+", help="Agent IDs to invite (for create)")

    args = parser.parse_args()

    coordinator = ConsensusCoordinator()

    if args.command == "start":
        if coordinator.start():
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                coordinator.stop()

    elif args.command == "status":
        if coordinator.connect():
            print(json.dumps(coordinator.get_status(), indent=2))

    elif args.command == "create":
        if not args.topic:
            print("--topic is required for create")
            sys.exit(1)

        if coordinator.connect():
            session = coordinator.create_session(
                topic=args.topic,
                description=args.description or args.topic,
                trigger_type=TriggerType.USER_REQUESTED,
                invited_agents=args.agents or []
            )
            print(f"Created session: {session.id}")
            print(json.dumps(session.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
