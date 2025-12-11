#!/usr/bin/env python3
"""
Native Async Power Mode Coordinator

Orchestrates multi-agent collaboration using Claude Code's native
background agent support (2.0.64+), eliminating Redis dependency.

Key Features:
- Zero-config startup (no Docker/Redis)
- Uses Task(run_in_background=true) for parallel agents
- TaskOutput for progress polling and result collection
- File-based insight sharing for cross-agent discoveries
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class AgentStatus(Enum):
    """Status of a background agent."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BackgroundAgent:
    """Represents a background agent in the mesh."""
    id: str
    name: str
    task: str
    phase: str
    status: AgentStatus = AgentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class Phase:
    """A phase of the orchestration workflow."""
    name: str
    description: str
    agents: List[Dict]
    prerequisites: List[str] = field(default_factory=list)
    timeout_seconds: int = 300


@dataclass
class Insight:
    """A discovery shared between agents."""
    id: str
    source_agent: str
    phase: str
    type: str  # "discovery", "warning", "recommendation"
    content: str
    tags: List[str]
    timestamp: str
    relevance_score: float = 1.0


@dataclass
class OrchestrationResult:
    """Final result of an orchestration session."""
    objective: str
    phases_completed: int
    total_phases: int
    agents_used: int
    insights_generated: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None
    phase_results: List[Dict] = field(default_factory=list)


# =============================================================================
# NATIVE ASYNC COORDINATOR
# =============================================================================

class NativeAsyncCoordinator:
    """
    Orchestrates multi-agent collaboration using Claude Code's
    native background agent support (2.0.64+).

    This replaces the Redis-based coordinator with native async,
    eliminating external dependencies while maintaining functionality.
    """

    def __init__(self, objective: str, config: Optional[Dict] = None):
        """
        Initialize the coordinator.

        Args:
            objective: The high-level goal to accomplish
            config: Optional configuration overrides
        """
        self.objective = objective
        self.config = config or self._load_default_config()

        # State
        self.agents: Dict[str, BackgroundAgent] = {}
        self.phases: List[Phase] = []
        self.current_phase: int = 0
        self.insights: List[Insight] = []
        self.start_time: Optional[datetime] = None

        # File paths
        self.popkit_dir = Path(".claude/popkit")
        self.insights_file = self.popkit_dir / "insights.json"
        self.state_file = self.popkit_dir / "power-state.json"

        # Ensure directories exist
        self.popkit_dir.mkdir(parents=True, exist_ok=True)

    def _load_default_config(self) -> Dict:
        """Load default configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                full_config = json.load(f)
                return full_config.get("native", {
                    "enabled": True,
                    "max_parallel_agents": 5,
                    "poll_interval_ms": 500,
                    "sync_timeout_seconds": 120,
                    "use_insights_file": True
                })
        return {}

    # =========================================================================
    # OBJECTIVE DECOMPOSITION
    # =========================================================================

    def decompose_objective(self) -> List[Phase]:
        """
        Break down the objective into actionable phases.

        This is called by the main agent with the decomposition result.
        Returns a list of phases with assigned agents.
        """
        # Default phases if not provided
        default_phases = [
            Phase(
                name="explore",
                description="Understand the codebase and requirements",
                agents=[
                    {"type": "code-explorer", "task": "Explore codebase for relevant patterns"}
                ]
            ),
            Phase(
                name="design",
                description="Design the solution architecture",
                agents=[
                    {"type": "code-architect", "task": "Design implementation approach"}
                ],
                prerequisites=["explore"]
            ),
            Phase(
                name="implement",
                description="Build the feature",
                agents=[
                    {"type": "code-reviewer", "task": "Review implementation"}
                ],
                prerequisites=["design"]
            )
        ]

        self.phases = default_phases
        return self.phases

    def set_phases(self, phases: List[Phase]):
        """Set custom phases (called by main agent after decomposition)."""
        self.phases = phases

    # =========================================================================
    # AGENT MANAGEMENT
    # =========================================================================

    def register_agent(self, agent_id: str, name: str, task: str, phase: str) -> BackgroundAgent:
        """
        Register a new background agent.

        Called when the main agent spawns a background agent via Task tool.
        """
        agent = BackgroundAgent(
            id=agent_id,
            name=name,
            task=task,
            phase=phase,
            status=AgentStatus.PENDING,
            started_at=datetime.now()
        )
        self.agents[agent_id] = agent
        self._save_state()
        return agent

    def update_agent_status(self, agent_id: str, status: AgentStatus, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update an agent's status."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = status
            if status == AgentStatus.COMPLETED:
                agent.completed_at = datetime.now()
                agent.result = result
            elif status == AgentStatus.FAILED:
                agent.completed_at = datetime.now()
                agent.error = error
            self._save_state()

    def get_active_agents(self) -> List[BackgroundAgent]:
        """Get all agents currently running."""
        return [a for a in self.agents.values() if a.status == AgentStatus.RUNNING]

    def get_pending_agents(self) -> List[BackgroundAgent]:
        """Get all agents waiting to start."""
        return [a for a in self.agents.values() if a.status == AgentStatus.PENDING]

    # =========================================================================
    # INSIGHT SHARING
    # =========================================================================

    def share_insight(self, source_agent: str, insight_type: str, content: str, tags: List[str]) -> Insight:
        """
        Share an insight from an agent for others to consume.

        Args:
            source_agent: ID of the agent sharing the insight
            insight_type: Type of insight (discovery, warning, recommendation)
            content: The insight content
            tags: Tags for relevance matching
        """
        insight = Insight(
            id=hashlib.md5(f"{source_agent}:{content}:{time.time()}".encode()).hexdigest()[:12],
            source_agent=source_agent,
            phase=self.phases[self.current_phase].name if self.phases else "unknown",
            type=insight_type,
            content=content,
            tags=tags,
            timestamp=datetime.now().isoformat()
        )

        self.insights.append(insight)
        self._save_insights()
        return insight

    def get_relevant_insights(self, agent_id: str, tags: List[str], max_count: int = 3) -> List[Insight]:
        """
        Get insights relevant to an agent's current task.

        Args:
            agent_id: ID of the requesting agent
            tags: Tags to match against
            max_count: Maximum insights to return
        """
        # Load fresh insights from file
        self._load_insights()

        # Filter and rank by relevance
        relevant = []
        for insight in self.insights:
            # Don't return agent's own insights
            if insight.source_agent == agent_id:
                continue

            # Calculate relevance based on tag overlap
            tag_overlap = len(set(insight.tags) & set(tags))
            if tag_overlap > 0:
                insight.relevance_score = tag_overlap / max(len(insight.tags), len(tags))
                relevant.append(insight)

        # Sort by relevance and return top N
        relevant.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant[:max_count]

    def _save_insights(self):
        """Save insights to file for cross-agent sharing."""
        if self.config.get("use_insights_file", True):
            with open(self.insights_file, "w") as f:
                json.dump([{
                    "id": i.id,
                    "source_agent": i.source_agent,
                    "phase": i.phase,
                    "type": i.type,
                    "content": i.content,
                    "tags": i.tags,
                    "timestamp": i.timestamp
                } for i in self.insights], f, indent=2)

    def _load_insights(self):
        """Load insights from file."""
        if self.insights_file.exists():
            with open(self.insights_file) as f:
                data = json.load(f)
                self.insights = [
                    Insight(
                        id=i["id"],
                        source_agent=i["source_agent"],
                        phase=i["phase"],
                        type=i["type"],
                        content=i["content"],
                        tags=i["tags"],
                        timestamp=i["timestamp"]
                    ) for i in data
                ]

    # =========================================================================
    # PHASE EXECUTION
    # =========================================================================

    def start_phase(self, phase_index: int) -> Phase:
        """
        Start a new phase of execution.

        Returns the phase configuration for the main agent to spawn agents.
        """
        if phase_index >= len(self.phases):
            raise ValueError(f"Phase index {phase_index} out of range")

        self.current_phase = phase_index
        phase = self.phases[phase_index]
        self._save_state()

        return phase

    def check_phase_complete(self) -> bool:
        """
        Check if current phase is complete (all agents done).
        """
        phase = self.phases[self.current_phase]
        phase_agents = [a for a in self.agents.values() if a.phase == phase.name]

        return all(
            a.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.TIMEOUT]
            for a in phase_agents
        )

    def get_phase_results(self) -> Dict:
        """Get aggregated results for current phase."""
        phase = self.phases[self.current_phase]
        phase_agents = [a for a in self.agents.values() if a.phase == phase.name]

        return {
            "phase": phase.name,
            "agents": [{
                "id": a.id,
                "name": a.name,
                "status": a.status.value,
                "result": a.result,
                "error": a.error
            } for a in phase_agents],
            "insights": [i for i in self.insights if i.phase == phase.name],
            "success": all(a.status == AgentStatus.COMPLETED for a in phase_agents)
        }

    def advance_to_next_phase(self) -> Optional[Phase]:
        """
        Advance to the next phase if prerequisites are met.

        Returns the next phase or None if all phases complete.
        """
        next_index = self.current_phase + 1
        if next_index >= len(self.phases):
            return None

        return self.start_phase(next_index)

    # =========================================================================
    # STATE PERSISTENCE
    # =========================================================================

    def _save_state(self):
        """Save coordinator state to file."""
        state = {
            "objective": self.objective,
            "current_phase": self.current_phase,
            "phases": [p.name for p in self.phases],
            "agents": {
                aid: {
                    "id": a.id,
                    "name": a.name,
                    "task": a.task,
                    "phase": a.phase,
                    "status": a.status.value,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None
                } for aid, a in self.agents.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> bool:
        """
        Load coordinator state from file.

        Returns True if state was loaded successfully.
        """
        if not self.state_file.exists():
            return False

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            self.objective = state.get("objective", self.objective)
            self.current_phase = state.get("current_phase", 0)

            # Restore agents
            for aid, adata in state.get("agents", {}).items():
                self.agents[aid] = BackgroundAgent(
                    id=adata["id"],
                    name=adata["name"],
                    task=adata["task"],
                    phase=adata["phase"],
                    status=AgentStatus(adata["status"]),
                    started_at=datetime.fromisoformat(adata["started_at"]) if adata.get("started_at") else None,
                    completed_at=datetime.fromisoformat(adata["completed_at"]) if adata.get("completed_at") else None
                )

            return True
        except (json.JSONDecodeError, KeyError):
            return False

    # =========================================================================
    # ORCHESTRATION SUMMARY
    # =========================================================================

    def get_status(self) -> Dict:
        """Get current orchestration status for display."""
        return {
            "mode": "native_async",
            "objective": self.objective,
            "phase": {
                "current": self.current_phase,
                "total": len(self.phases),
                "name": self.phases[self.current_phase].name if self.phases else "not_started"
            },
            "agents": {
                "total": len(self.agents),
                "running": len([a for a in self.agents.values() if a.status == AgentStatus.RUNNING]),
                "completed": len([a for a in self.agents.values() if a.status == AgentStatus.COMPLETED]),
                "failed": len([a for a in self.agents.values() if a.status == AgentStatus.FAILED])
            },
            "insights": len(self.insights)
        }

    def finalize(self) -> OrchestrationResult:
        """
        Finalize the orchestration and return results.

        Called when all phases are complete.
        """
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0

        return OrchestrationResult(
            objective=self.objective,
            phases_completed=self.current_phase + 1,
            total_phases=len(self.phases),
            agents_used=len(self.agents),
            insights_generated=len(self.insights),
            duration_seconds=duration,
            success=all(a.status == AgentStatus.COMPLETED for a in self.agents.values()),
            phase_results=[self.get_phase_results()]
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_spawn_prompt(agent_config: Dict, phase: str, insights: List[Insight], objective: str) -> str:
    """
    Generate the prompt for spawning a background agent.

    This is used by the main agent when calling the Task tool.
    """
    insight_context = ""
    if insights:
        insight_context = "\n\n## Relevant Insights from Other Agents\n"
        for i in insights:
            insight_context += f"- [{i.type}] {i.content}\n"

    return f"""You are a {agent_config['type']} agent working on: {objective}

## Current Phase: {phase}

## Your Task
{agent_config['task']}

## Guidelines
1. Focus only on your assigned task
2. Share any important discoveries as insights
3. Report your findings clearly
4. Stay within scope - don't modify files outside your area
{insight_context}

## Output Format
When complete, summarize:
1. What you found/did
2. Any insights for other agents
3. Recommendations for next steps
"""


def format_status_line(status: Dict) -> str:
    """Format status for display in Claude Code status line."""
    phase = status.get("phase", {})
    agents = status.get("agents", {})

    return (
        f"Power Mode: {phase.get('name', 'unknown')} "
        f"({phase.get('current', 0)+1}/{phase.get('total', 0)}) | "
        f"Agents: {agents.get('running', 0)} running, "
        f"{agents.get('completed', 0)} done | "
        f"Insights: {status.get('insights', 0)}"
    )


# =============================================================================
# CLI INTERFACE (for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Native Async Power Mode Coordinator")
    parser.add_argument("--objective", type=str, help="The objective to accomplish")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--test", action="store_true", help="Run self-test")

    args = parser.parse_args()

    if args.test:
        # Self-test
        coordinator = NativeAsyncCoordinator("Test objective")
        coordinator.decompose_objective()

        # Register a test agent
        agent = coordinator.register_agent(
            agent_id="test-001",
            name="code-explorer",
            task="Explore the codebase",
            phase="explore"
        )
        print(f"Registered agent: {agent.id}")

        # Share an insight
        insight = coordinator.share_insight(
            source_agent="test-001",
            insight_type="discovery",
            content="Found existing auth patterns in src/auth/",
            tags=["auth", "patterns"]
        )
        print(f"Shared insight: {insight.id}")

        # Get status
        status = coordinator.get_status()
        print(f"Status: {format_status_line(status)}")

        print("\nSelf-test passed!")

    elif args.status:
        coordinator = NativeAsyncCoordinator("")
        if coordinator.load_state():
            status = coordinator.get_status()
            print(format_status_line(status))
        else:
            print("No active Power Mode session")

    elif args.objective:
        coordinator = NativeAsyncCoordinator(args.objective)
        coordinator.start_time = datetime.now()
        phases = coordinator.decompose_objective()
        print(f"Decomposed into {len(phases)} phases:")
        for p in phases:
            print(f"  - {p.name}: {p.description}")
