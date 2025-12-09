#!/usr/bin/env python3
"""
Consensus Agent Hook
PostToolUse hook that enables agents to participate in consensus sessions.

This hook:
1. Checks if agent has been granted a consensus token
2. Retrieves context (previous contributions, discussion summary)
3. Provides structured prompts for agent to think and contribute
4. Submits contributions back to the consensus coordinator

Usage:
    Add to hooks.json:
    {
        "event": "PostToolUse",
        "hooks": [
            {
                "command": "python",
                "args": ["power-mode/consensus/agent_hook.py"]
            }
        ]
    }
"""

import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from consensus.protocol import (
    ConsensusChannels, ConsensusMessage, ConsensusMessageType,
    ConsensusMessageFactory, VoteType, ReactionType
)


# =============================================================================
# AGENT STATE
# =============================================================================

class ConsensusAgentState:
    """Tracks consensus-related state for an agent."""

    def __init__(self, agent_id: str = None, agent_name: str = None):
        self.agent_id = agent_id or self._generate_id()
        self.agent_name = agent_name or "agent"
        self.active_session: Optional[str] = None
        self.has_token: bool = False
        self.token_context: Dict = {}
        self.pending_vote: Optional[str] = None  # proposal_id if voting
        self.contribution_ready: bool = False
        self.last_check: Optional[datetime] = None

    @staticmethod
    def _generate_id() -> str:
        return hashlib.md5(f"agent-{datetime.now().isoformat()}".encode()).hexdigest()[:8]

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "active_session": self.active_session,
            "has_token": self.has_token,
            "pending_vote": self.pending_vote,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'ConsensusAgentState':
        state = cls(
            agent_id=d.get("agent_id"),
            agent_name=d.get("agent_name", "agent")
        )
        state.active_session = d.get("active_session")
        state.has_token = d.get("has_token", False)
        state.pending_vote = d.get("pending_vote")
        if d.get("last_check"):
            state.last_check = datetime.fromisoformat(d["last_check"])
        return state


# =============================================================================
# STATE FILE MANAGEMENT
# =============================================================================

def get_agent_state_path() -> Path:
    """Get path for agent consensus state file."""
    # Prefer project-local
    project_path = Path.cwd() / ".claude" / "popkit" / "consensus-agent-state.json"
    if project_path.parent.exists():
        return project_path

    # Fallback to home
    home_path = Path.home() / ".claude" / "popkit" / "consensus-agent-state.json"
    home_path.parent.mkdir(parents=True, exist_ok=True)
    return home_path


def load_state() -> ConsensusAgentState:
    """Load agent state from file."""
    state_path = get_agent_state_path()
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text())
            return ConsensusAgentState.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return ConsensusAgentState()


def save_state(state: ConsensusAgentState):
    """Save agent state to file."""
    state_path = get_agent_state_path()
    state_path.write_text(json.dumps(state.to_dict(), indent=2))


# =============================================================================
# REDIS CLIENT
# =============================================================================

class ConsensusClient:
    """Client for interacting with consensus coordinator."""

    def __init__(self, host: str = "localhost", port: int = 16379):
        self.host = host
        self.port = port
        self.redis: Optional['redis.Redis'] = None

    def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            return False

        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True
            )
            self.redis.ping()
            return True
        except Exception:
            return False

    def check_for_token(self, agent_id: str) -> Optional[Dict]:
        """Check if agent has been granted a token."""
        if not self.redis:
            return None

        try:
            # Check agent-specific channel for messages
            channel = ConsensusChannels.agent(agent_id)

            # Use list to store pending messages
            msg_data = self.redis.lpop(f"{channel}:pending")
            if msg_data:
                msg = ConsensusMessage.from_json(msg_data)
                if msg.type == ConsensusMessageType.TOKEN_GRANT:
                    return {
                        "session_id": msg.session_id,
                        "round_number": msg.round_number,
                        "context": msg.payload
                    }
        except Exception:
            pass

        return None

    def check_for_vote_request(self, agent_id: str) -> Optional[Dict]:
        """Check if agent has a pending vote request."""
        if not self.redis:
            return None

        try:
            # Check for vote start messages
            channel = ConsensusChannels.agent(agent_id)
            msg_data = self.redis.lpop(f"{channel}:votes")
            if msg_data:
                msg = ConsensusMessage.from_json(msg_data)
                if msg.type == ConsensusMessageType.VOTE_START:
                    return {
                        "session_id": msg.session_id,
                        "proposal_id": msg.payload["proposal_id"],
                        "proposal_summary": msg.payload["proposal_summary"],
                        "deadline_seconds": msg.payload["deadline_seconds"]
                    }
        except Exception:
            pass

        return None

    def submit_contribution(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        contribution_type: str = "opinion",
        confidence: float = 0.5
    ) -> bool:
        """Submit a contribution to the session."""
        if not self.redis:
            return False

        try:
            msg = ConsensusMessageFactory.contribution(
                session_id=session_id,
                from_agent=agent_id,
                content=content,
                contribution_type=contribution_type,
                round_number=0,  # Coordinator will set correct round
                confidence=confidence
            )

            self.redis.publish(
                ConsensusChannels.session(session_id),
                msg.to_json()
            )

            # Release token
            release_msg = ConsensusMessageFactory.token_release(
                session_id=session_id,
                from_agent=agent_id,
                contribution_id=msg.id
            )
            self.redis.publish(
                ConsensusChannels.session(session_id),
                release_msg.to_json()
            )

            return True
        except Exception:
            return False

    def skip_turn(self, session_id: str, agent_id: str, reason: str = "nothing to add") -> bool:
        """Skip this turn."""
        if not self.redis:
            return False

        try:
            msg = ConsensusMessageFactory.token_skip(
                session_id=session_id,
                from_agent=agent_id,
                reason=reason
            )
            self.redis.publish(
                ConsensusChannels.session(session_id),
                msg.to_json()
            )
            return True
        except Exception:
            return False

    def submit_vote(
        self,
        session_id: str,
        agent_id: str,
        proposal_id: str,
        vote_type: VoteType,
        rationale: str = None
    ) -> bool:
        """Submit a vote on a proposal."""
        if not self.redis:
            return False

        try:
            msg = ConsensusMessageFactory.vote(
                session_id=session_id,
                from_agent=agent_id,
                proposal_id=proposal_id,
                vote_type=vote_type,
                rationale=rationale
            )
            self.redis.publish(
                ConsensusChannels.votes(session_id),
                msg.to_json()
            )
            return True
        except Exception:
            return False

    def submit_proposal(
        self,
        session_id: str,
        agent_id: str,
        title: str,
        description: str,
        rationale: str
    ) -> bool:
        """Submit a formal proposal."""
        if not self.redis:
            return False

        try:
            msg = ConsensusMessageFactory.proposal(
                session_id=session_id,
                from_agent=agent_id,
                title=title,
                description=description,
                rationale=rationale
            )
            self.redis.publish(
                ConsensusChannels.session(session_id),
                msg.to_json()
            )
            return True
        except Exception:
            return False


# =============================================================================
# HOOK LOGIC
# =============================================================================

def process_hook(input_data: Dict) -> Dict:
    """
    Process the PostToolUse hook for consensus participation.

    This is called after each tool use and checks if the agent
    needs to participate in a consensus session.
    """
    # Load state
    state = load_state()
    state.last_check = datetime.now()

    # Get agent identity from context
    if "session" in input_data:
        session = input_data["session"]
        if "agent_id" not in state.to_dict() or not state.agent_id:
            state.agent_id = session.get("id", state.agent_id)
            state.agent_name = session.get("agent_name", "agent")

    # Try to connect
    client = ConsensusClient()
    if not client.connect():
        save_state(state)
        return {"action": "continue"}

    # Check if we have a token
    if not state.has_token:
        token_info = client.check_for_token(state.agent_id)
        if token_info:
            state.has_token = True
            state.active_session = token_info["session_id"]
            state.token_context = token_info["context"]
            save_state(state)

            # Return prompt for agent to contribute
            return build_token_response(state, token_info)

    # Check if we have a pending vote
    if not state.pending_vote:
        vote_info = client.check_for_vote_request(state.agent_id)
        if vote_info:
            state.pending_vote = vote_info["proposal_id"]
            state.active_session = vote_info["session_id"]
            save_state(state)

            # Return prompt for agent to vote
            return build_vote_response(state, vote_info)

    # Nothing pending
    save_state(state)
    return {"action": "continue"}


def build_token_response(state: ConsensusAgentState, token_info: Dict) -> Dict:
    """Build response when agent receives a token."""
    context = token_info.get("context", {})

    # Build prompt for agent
    prompt = f"""
## Consensus Discussion - Your Turn

You have been granted the speaking token in a consensus session.

**Session ID:** {token_info['session_id']}
**Round:** {token_info['round_number']}

### Discussion Context

{context.get('discussion_summary', 'No summary available.')}

### Previous Contributions

"""

    previous = context.get("previous_contributions", [])
    if previous:
        for i, contrib in enumerate(previous[-3:], 1):
            prompt += f"{i}. **{contrib.get('author_name', 'Unknown')}**: {contrib.get('content', '')[:200]}\n"
    else:
        prompt += "No previous contributions yet. You're starting the discussion!\n"

    prompt += """
### Current Proposals

"""
    proposals = context.get("current_proposals", [])
    if proposals:
        for prop in proposals:
            prompt += f"- **{prop.get('title', 'Untitled')}** (by {prop.get('author', 'unknown')})\n"
    else:
        prompt += "No proposals yet. Consider making one!\n"

    if context.get("your_previous_stance"):
        prompt += f"\n### Your Previous Stance\n\n{context['your_previous_stance']}\n"

    prompt += f"""
### Your Turn

Please provide your contribution. You can:

1. **Share an opinion** - Express your view on the topic
2. **Ask a question** - Seek clarification from others
3. **Make a proposal** - Suggest a specific decision
4. **Synthesize** - Summarize points of agreement/disagreement
5. **Skip** - Pass if you have nothing to add

Timeout: {context.get('timeout_seconds', 120)} seconds

**To contribute**, respond with your thoughts. The system will capture your contribution.
"""

    return {
        "action": "prompt",
        "prompt": prompt,
        "metadata": {
            "consensus_mode": True,
            "session_id": state.active_session,
            "has_token": True,
            "round": token_info["round_number"]
        }
    }


def build_vote_response(state: ConsensusAgentState, vote_info: Dict) -> Dict:
    """Build response when agent needs to vote."""
    prompt = f"""
## Consensus Voting Required

A proposal in your consensus session requires your vote.

**Session ID:** {vote_info['session_id']}
**Proposal ID:** {vote_info['proposal_id']}

### Proposal Summary

{vote_info.get('proposal_summary', 'No summary available.')}

### Vote Options

1. **APPROVE** - Fully support this proposal
2. **APPROVE_WITH_CONCERNS** - Support, but have reservations
3. **ABSTAIN** - No strong opinion either way
4. **REQUEST_CHANGES** - Would approve if modified
5. **REJECT** - Cannot support this proposal

**Deadline:** {vote_info.get('deadline_seconds', 60)} seconds

**To vote**, respond with your choice and rationale.
"""

    return {
        "action": "prompt",
        "prompt": prompt,
        "metadata": {
            "consensus_mode": True,
            "session_id": state.active_session,
            "voting": True,
            "proposal_id": vote_info["proposal_id"]
        }
    }


def handle_contribution(state: ConsensusAgentState, content: str, contribution_type: str = "opinion"):
    """Handle agent's contribution submission."""
    client = ConsensusClient()
    if not client.connect():
        return {"success": False, "error": "Cannot connect to consensus system"}

    success = client.submit_contribution(
        session_id=state.active_session,
        agent_id=state.agent_id,
        content=content,
        contribution_type=contribution_type,
        confidence=0.7
    )

    if success:
        state.has_token = False
        state.token_context = {}
        save_state(state)

    return {"success": success}


def handle_vote(state: ConsensusAgentState, vote_choice: str, rationale: str = None):
    """Handle agent's vote submission."""
    client = ConsensusClient()
    if not client.connect():
        return {"success": False, "error": "Cannot connect to consensus system"}

    # Map string to VoteType
    vote_map = {
        "approve": VoteType.APPROVE,
        "approve_with_concerns": VoteType.APPROVE_WITH_CONCERNS,
        "abstain": VoteType.ABSTAIN,
        "request_changes": VoteType.REQUEST_CHANGES,
        "reject": VoteType.REJECT
    }

    vote_type = vote_map.get(vote_choice.lower())
    if not vote_type:
        return {"success": False, "error": f"Invalid vote: {vote_choice}"}

    success = client.submit_vote(
        session_id=state.active_session,
        agent_id=state.agent_id,
        proposal_id=state.pending_vote,
        vote_type=vote_type,
        rationale=rationale
    )

    if success:
        state.pending_vote = None
        save_state(state)

    return {"success": success}


def handle_skip(state: ConsensusAgentState, reason: str = "nothing to add"):
    """Handle agent skipping their turn."""
    client = ConsensusClient()
    if not client.connect():
        return {"success": False, "error": "Cannot connect to consensus system"}

    success = client.skip_turn(
        session_id=state.active_session,
        agent_id=state.agent_id,
        reason=reason
    )

    if success:
        state.has_token = False
        state.token_context = {}
        save_state(state)

    return {"success": success}


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for the hook."""
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    # Process hook
    result = process_hook(input_data)

    # Output result
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
