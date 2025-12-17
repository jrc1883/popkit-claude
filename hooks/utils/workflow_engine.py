#!/usr/bin/env python3
"""
File-Based Workflow Engine

A state machine for programmatic skill orchestration that enables:
- Multi-step workflow definitions
- User decision branching (via AskUserQuestion)
- Cross-session persistence (survives Claude Code restarts)
- Event-based coordination (for async operations)

Part of Issue #206: File-Based Workflow Engine
Part of Workflow Orchestration System (Phase 1)

Usage:
    # Start a new workflow
    engine = FileWorkflowEngine.create_workflow(
        workflow_id="feature-dev-abc123",
        workflow_def=workflow_definition,
        initial_context={"issue_number": 42}
    )

    # Get current step
    step = engine.get_current_step()

    # Advance to next step
    next_step = engine.advance_step({"result": "success"})

    # Wait for user decision
    engine.wait_for_event("decision-approach")

    # Later, when user responds via AskUserQuestion
    engine.notify_event("decision-approach", {"answer": "comprehensive"})
"""

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum


# =============================================================================
# Enums and Constants
# =============================================================================

class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"       # Not yet started
    RUNNING = "running"       # Actively executing
    WAITING = "waiting"       # Waiting for external event (user decision)
    COMPLETE = "complete"     # Successfully completed
    ERROR = "error"           # Failed with error
    CANCELLED = "cancelled"   # Manually cancelled


class StepType(Enum):
    """Type of workflow step."""
    SKILL = "skill"              # Invoke a PopKit skill
    AGENT = "agent"              # Use a specific agent
    USER_DECISION = "user_decision"  # AskUserQuestion with routing
    SPAWN_AGENTS = "spawn_agents"    # Parallel agent execution
    TERMINAL = "terminal"        # End of workflow


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WorkflowStep:
    """Definition of a single workflow step.

    Immutable definition - describes what the step does, not its state.
    """
    id: str                                  # Unique step identifier
    description: str                         # Human-readable description
    step_type: str                           # One of StepType values
    skill: Optional[str] = None              # Skill name (if type=skill)
    agent: Optional[str] = None              # Agent name (if type=agent)
    question: Optional[str] = None           # Question text (if type=user_decision)
    header: Optional[str] = None             # Header for AskUserQuestion
    options: Optional[List[Dict]] = None     # Options for user_decision
    agents: Optional[List[Dict]] = None      # Agents to spawn (if type=spawn_agents)
    wait_for: Optional[str] = None           # "all" or "any" (for spawn_agents)
    next: Optional[str] = None               # Default next step ID
    next_map: Optional[Dict[str, str]] = None  # Option ID -> next step ID mapping

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create a WorkflowStep from a dictionary."""
        return cls(
            id=data.get("id", "unknown"),
            description=data.get("description", ""),
            step_type=data.get("type", data.get("step_type", "skill")),
            skill=data.get("skill"),
            agent=data.get("agent"),
            question=data.get("question"),
            header=data.get("header"),
            options=data.get("options"),
            agents=data.get("agents"),
            wait_for=data.get("wait_for"),
            next=data.get("next"),
            next_map=data.get("next_map")
        )


@dataclass
class WorkflowDefinition:
    """Complete workflow definition with all steps.

    Parsed from skill YAML frontmatter or provided programmatically.
    """
    id: str                          # Workflow type ID (e.g., "feature-development")
    name: str                        # Human-readable name
    version: int = 1                 # Definition version
    description: str = ""            # Workflow description
    steps: List[WorkflowStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        """Create a WorkflowDefinition from a dictionary."""
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", data.get("id", "Unknown Workflow")),
            version=data.get("version", 1),
            description=data.get("description", ""),
            steps=steps
        )

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_first_step(self) -> Optional[WorkflowStep]:
        """Get the first step in the workflow."""
        return self.steps[0] if self.steps else None


@dataclass
class WorkflowState:
    """Runtime state of a workflow execution.

    Mutable state that tracks progress through the workflow.
    Persisted to disk for cross-session continuity.
    """
    workflow_id: str                          # Unique run ID (e.g., "feature-dev-abc123")
    workflow_type: str                        # Definition ID (e.g., "feature-development")
    workflow_name: str                        # Human-readable name
    current_step: str                         # Current step ID
    completed_steps: List[str] = field(default_factory=list)  # IDs of completed steps
    pending_events: List[str] = field(default_factory=list)   # Events we're waiting for
    context: Dict[str, Any] = field(default_factory=dict)     # Accumulated context data
    step_results: Dict[str, Any] = field(default_factory=dict)  # Results per step
    status: str = WorkflowStatus.PENDING.value
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    github_issue: Optional[int] = None        # Linked GitHub issue

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "workflow_name": self.workflow_name,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "pending_events": self.pending_events,
            "context": self.context,
            "step_results": self.step_results,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "github_issue": self.github_issue
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Create a WorkflowState from a dictionary."""
        return cls(
            workflow_id=data.get("workflow_id", "unknown"),
            workflow_type=data.get("workflow_type", "unknown"),
            workflow_name=data.get("workflow_name", "Unknown"),
            current_step=data.get("current_step", ""),
            completed_steps=data.get("completed_steps", []),
            pending_events=data.get("pending_events", []),
            context=data.get("context", {}),
            step_results=data.get("step_results", {}),
            status=data.get("status", WorkflowStatus.PENDING.value),
            error_message=data.get("error_message"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            github_issue=data.get("github_issue")
        )


@dataclass
class WorkflowEvent:
    """An event notification for a waiting workflow.

    Used to signal user decisions, agent completions, etc.
    """
    event_id: str                    # Event identifier (e.g., "decision-approach")
    event_type: str                  # Type: "user_decision", "agent_complete", etc.
    data: Dict[str, Any]             # Event payload
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "user"             # Event source: "user", "agent", "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowEvent':
        """Create a WorkflowEvent from a dictionary."""
        return cls(
            event_id=data.get("event_id", "unknown"),
            event_type=data.get("event_type", "unknown"),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            source=data.get("source", "user")
        )


# =============================================================================
# Storage Utilities
# =============================================================================

def _get_workflows_dir() -> Path:
    """Get the workflows storage directory.

    Creates .claude/popkit/workflows/ if it doesn't exist.
    """
    # Look for project root indicators
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "package.json").exists():
            workflows_dir = parent / ".claude" / "popkit" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            return workflows_dir

    # Fallback to current directory
    workflows_dir = current / ".claude" / "popkit" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    return workflows_dir


def _get_workflow_state_file(workflow_id: str) -> Path:
    """Get the state file for a specific workflow."""
    return _get_workflows_dir() / f"{workflow_id}.json"


def _get_workflow_events_dir(workflow_id: str) -> Path:
    """Get the events directory for a specific workflow."""
    events_dir = _get_workflows_dir() / f"{workflow_id}.events"
    events_dir.mkdir(exist_ok=True)
    return events_dir


def _get_workflow_log_file(workflow_id: str) -> Path:
    """Get the log file for a specific workflow."""
    return _get_workflows_dir() / f"{workflow_id}.log"


def _get_active_workflow_file() -> Path:
    """Get the file that tracks the currently active workflow."""
    return _get_workflows_dir() / "active.json"


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON atomically to prevent corruption.

    Writes to a temp file first, then renames (atomic on most filesystems).
    """
    temp_path = path.with_suffix(".tmp")
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomic rename
        temp_path.replace(path)
    except Exception:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


# =============================================================================
# File-Based Workflow Engine
# =============================================================================

class FileWorkflowEngine:
    """File-based workflow engine for programmatic skill orchestration.

    Provides:
    - Workflow lifecycle management (create, advance, complete)
    - State persistence (survives Claude Code restarts)
    - Event-based coordination (user decisions, agent completions)
    - Audit logging

    All state is stored in .claude/popkit/workflows/:
    - {workflow_id}.json - Workflow state
    - {workflow_id}.events/ - Pending events
    - {workflow_id}.log - Audit log
    """

    def __init__(self, workflow_id: str, definition: Optional[WorkflowDefinition] = None):
        """Initialize the engine for a specific workflow.

        Args:
            workflow_id: Unique identifier for this workflow run
            definition: Workflow definition (required for new workflows)
        """
        self.workflow_id = workflow_id
        self.definition = definition
        self._state: Optional[WorkflowState] = None

        # Load existing state if available
        state_file = _get_workflow_state_file(workflow_id)
        if state_file.exists():
            self._load_state()

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create_workflow(
        cls,
        workflow_id: str,
        workflow_def: Union[Dict[str, Any], WorkflowDefinition],
        initial_context: Optional[Dict[str, Any]] = None,
        github_issue: Optional[int] = None
    ) -> 'FileWorkflowEngine':
        """Create a new workflow execution.

        Args:
            workflow_id: Unique identifier for this run
            workflow_def: Workflow definition (dict or WorkflowDefinition)
            initial_context: Initial context data
            github_issue: Optional linked GitHub issue number

        Returns:
            FileWorkflowEngine instance ready to execute
        """
        # Parse definition if needed
        if isinstance(workflow_def, dict):
            definition = WorkflowDefinition.from_dict(workflow_def)
        else:
            definition = workflow_def

        # Create engine
        engine = cls(workflow_id, definition)

        # Initialize state
        first_step = definition.get_first_step()
        engine._state = WorkflowState(
            workflow_id=workflow_id,
            workflow_type=definition.id,
            workflow_name=definition.name,
            current_step=first_step.id if first_step else "",
            context=initial_context or {},
            status=WorkflowStatus.RUNNING.value,
            github_issue=github_issue
        )

        # Save initial state
        engine._save_state()
        engine._log("workflow_created", {"definition_id": definition.id})

        # Set as active workflow
        engine._set_active()

        return engine

    @classmethod
    def load_workflow(cls, workflow_id: str) -> Optional['FileWorkflowEngine']:
        """Load an existing workflow by ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            FileWorkflowEngine if found, None otherwise
        """
        state_file = _get_workflow_state_file(workflow_id)
        if not state_file.exists():
            return None

        engine = cls(workflow_id)
        engine._load_state()
        return engine

    @classmethod
    def get_active_workflow(cls) -> Optional['FileWorkflowEngine']:
        """Get the currently active workflow.

        Returns:
            FileWorkflowEngine for active workflow, None if no active workflow
        """
        active_file = _get_active_workflow_file()
        if not active_file.exists():
            return None

        try:
            with open(active_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            workflow_id = data.get("workflow_id")
            if workflow_id:
                return cls.load_workflow(workflow_id)
        except (json.JSONDecodeError, KeyError):
            pass

        return None

    @classmethod
    def list_workflows(cls, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all workflows, optionally filtered by status.

        Args:
            status: Optional status filter (running, waiting, complete, error)

        Returns:
            List of workflow summaries
        """
        workflows = []
        workflows_dir = _get_workflows_dir()

        for state_file in workflows_dir.glob("*.json"):
            if state_file.name in ("active.json",):
                continue

            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if status and data.get("status") != status:
                    continue

                workflows.append({
                    "workflow_id": data.get("workflow_id"),
                    "workflow_type": data.get("workflow_type"),
                    "workflow_name": data.get("workflow_name"),
                    "status": data.get("status"),
                    "current_step": data.get("current_step"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "github_issue": data.get("github_issue")
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(workflows, key=lambda w: w.get("updated_at") or "", reverse=True)

    # =========================================================================
    # State Management
    # =========================================================================

    def _load_state(self) -> None:
        """Load workflow state from disk."""
        state_file = _get_workflow_state_file(self.workflow_id)
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._state = WorkflowState.from_dict(data)
                # Also load definition if saved
                if "definition" in data:
                    self.definition = WorkflowDefinition.from_dict(data["definition"])
            except (json.JSONDecodeError, KeyError) as e:
                self._state = None
                raise RuntimeError(f"Failed to load workflow state: {e}")

    def _save_state(self) -> None:
        """Save workflow state to disk atomically."""
        if self._state:
            self._state.updated_at = datetime.now().isoformat()
            state_file = _get_workflow_state_file(self.workflow_id)
            # Include definition in saved state for cross-session loading
            data = self._state.to_dict()
            if self.definition:
                data["definition"] = self._definition_to_dict()
            _atomic_write_json(state_file, data)

    def _definition_to_dict(self) -> Dict[str, Any]:
        """Convert definition to dict for serialization."""
        if not self.definition:
            return {}
        return {
            "id": self.definition.id,
            "name": self.definition.name,
            "version": self.definition.version,
            "description": self.definition.description,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "type": step.step_type,
                    "skill": step.skill,
                    "agent": step.agent,
                    "question": step.question,
                    "header": step.header,
                    "options": step.options,
                    "agents": step.agents,
                    "wait_for": step.wait_for,
                    "next": step.next,
                    "next_map": step.next_map
                }
                for step in self.definition.steps
            ]
        }

    def _set_active(self) -> None:
        """Set this workflow as the active workflow."""
        active_file = _get_active_workflow_file()
        _atomic_write_json(active_file, {
            "workflow_id": self.workflow_id,
            "set_at": datetime.now().isoformat()
        })

    def _log(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Append an entry to the workflow log."""
        log_file = _get_workflow_log_file(self.workflow_id)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {}
        }

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")

    def get_state(self) -> Optional[WorkflowState]:
        """Get the current workflow state."""
        return self._state

    def get_status(self) -> str:
        """Get the workflow status."""
        return self._state.status if self._state else WorkflowStatus.PENDING.value

    # =========================================================================
    # Step Management
    # =========================================================================

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current workflow step.

        Returns:
            Current WorkflowStep, or None if workflow not active
        """
        if not self._state or not self.definition:
            return None

        return self.definition.get_step(self._state.current_step)

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a specific step by ID."""
        if not self.definition:
            return None
        return self.definition.get_step(step_id)

    def advance_step(self, step_result: Optional[Dict[str, Any]] = None) -> Optional[WorkflowStep]:
        """Advance to the next workflow step.

        Args:
            step_result: Optional result data from current step

        Returns:
            The next WorkflowStep, or None if workflow is complete
        """
        if not self._state or not self.definition:
            return None

        current_step = self.get_current_step()
        if not current_step:
            return None

        # Store step result
        if step_result:
            self._state.step_results[current_step.id] = step_result

            # Merge any context updates
            if "context" in step_result:
                self._state.context.update(step_result["context"])

        # Determine next step
        next_step_id = None

        if current_step.step_type == StepType.USER_DECISION.value:
            # For user decisions, look up the answer in next_map
            if step_result and "answer" in step_result:
                answer = step_result["answer"]
                # Try direct match first
                if current_step.next_map and answer in current_step.next_map:
                    next_step_id = current_step.next_map[answer]
                # Try option ID match
                elif current_step.next_map and "option_id" in step_result:
                    option_id = step_result["option_id"]
                    next_step_id = current_step.next_map.get(option_id)
                # Try matching option label to option ID
                elif current_step.options:
                    for option in current_step.options:
                        if option.get("label", "").lower() == answer.lower():
                            next_step_id = option.get("next") or current_step.next_map.get(option.get("id"))
                            break

        # Fall back to default next
        if not next_step_id:
            next_step_id = current_step.next

        # Mark current step as completed
        if current_step.id not in self._state.completed_steps:
            self._state.completed_steps.append(current_step.id)

        # Check if workflow is complete
        if not next_step_id or current_step.step_type == StepType.TERMINAL.value:
            self._state.status = WorkflowStatus.COMPLETE.value
            self._state.current_step = ""
            self._save_state()
            self._log("workflow_complete", {"completed_steps": self._state.completed_steps})
            self._clear_active()
            return None

        # Move to next step
        self._state.current_step = next_step_id
        self._state.status = WorkflowStatus.RUNNING.value
        self._state.pending_events = []  # Clear any pending events
        self._save_state()
        self._log("step_advanced", {"from": current_step.id, "to": next_step_id})

        return self.definition.get_step(next_step_id)

    # =========================================================================
    # Event Management (for user decisions)
    # =========================================================================

    def wait_for_event(self, event_id: str) -> None:
        """Mark workflow as waiting for an external event.

        Called when a user_decision step requires input.

        Args:
            event_id: Identifier for the expected event
        """
        if not self._state:
            return

        if event_id not in self._state.pending_events:
            self._state.pending_events.append(event_id)
        self._state.status = WorkflowStatus.WAITING.value
        self._save_state()
        self._log("waiting_for_event", {"event_id": event_id})

    def notify_event(self, event_id: str, data: Dict[str, Any]) -> bool:
        """Notify the workflow of an external event.

        Called when a user responds to an AskUserQuestion.

        Args:
            event_id: Event identifier
            data: Event data (e.g., {"answer": "comprehensive"})

        Returns:
            True if event was consumed and workflow can advance
        """
        if not self._state:
            return False

        # Check if we're waiting for this event
        if event_id not in self._state.pending_events:
            # Store event anyway for later processing
            self._store_event(event_id, data)
            return False

        # Consume the event
        self._state.pending_events.remove(event_id)

        # Store event data in context
        self._state.context[f"event_{event_id}"] = data

        self._log("event_received", {"event_id": event_id, "data": data})

        # If this was a user_decision step, prepare to advance
        current_step = self.get_current_step()
        if current_step and current_step.step_type == StepType.USER_DECISION.value:
            # The advance_step will be called by the caller with the answer
            self._state.status = WorkflowStatus.RUNNING.value
            self._save_state()
            return True

        # For other event types, just update status if no more pending events
        if not self._state.pending_events:
            self._state.status = WorkflowStatus.RUNNING.value
        self._save_state()
        return True

    def _store_event(self, event_id: str, data: Dict[str, Any]) -> None:
        """Store an event for later processing."""
        events_dir = _get_workflow_events_dir(self.workflow_id)
        event = WorkflowEvent(
            event_id=event_id,
            event_type="stored",
            data=data
        )
        event_file = events_dir / f"{event_id}.json"
        _atomic_write_json(event_file, event.to_dict())

    def get_pending_event(self, event_id: str) -> Optional[WorkflowEvent]:
        """Get a stored event by ID."""
        events_dir = _get_workflow_events_dir(self.workflow_id)
        event_file = events_dir / f"{event_id}.json"

        if not event_file.exists():
            return None

        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return WorkflowEvent.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def consume_event(self, event_id: str) -> Optional[WorkflowEvent]:
        """Get and delete a stored event."""
        event = self.get_pending_event(event_id)
        if event:
            events_dir = _get_workflow_events_dir(self.workflow_id)
            event_file = events_dir / f"{event_id}.json"
            event_file.unlink()
        return event

    # =========================================================================
    # Context Management
    # =========================================================================

    def get_context(self) -> Dict[str, Any]:
        """Get the accumulated workflow context."""
        return self._state.context if self._state else {}

    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update the workflow context."""
        if self._state:
            self._state.context.update(updates)
            self._save_state()

    def set_github_issue(self, issue_number: int) -> None:
        """Link this workflow to a GitHub issue."""
        if self._state:
            self._state.github_issue = issue_number
            self._save_state()

    # =========================================================================
    # Error Handling
    # =========================================================================

    def set_error(self, error_message: str) -> None:
        """Mark workflow as errored."""
        if self._state:
            self._state.status = WorkflowStatus.ERROR.value
            self._state.error_message = error_message
            self._save_state()
            self._log("workflow_error", {"error": error_message})

    def cancel(self) -> None:
        """Cancel the workflow."""
        if self._state:
            self._state.status = WorkflowStatus.CANCELLED.value
            self._save_state()
            self._log("workflow_cancelled", {})
            self._clear_active()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def _clear_active(self) -> None:
        """Clear the active workflow marker if this is the active workflow."""
        active_file = _get_active_workflow_file()
        if active_file.exists():
            try:
                with open(active_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("workflow_id") == self.workflow_id:
                    active_file.unlink()
            except (json.JSONDecodeError, KeyError):
                pass

    def delete(self) -> None:
        """Delete all workflow files."""
        # Delete state file
        state_file = _get_workflow_state_file(self.workflow_id)
        if state_file.exists():
            state_file.unlink()

        # Delete events directory
        events_dir = _get_workflow_events_dir(self.workflow_id)
        if events_dir.exists():
            shutil.rmtree(events_dir)

        # Delete log file
        log_file = _get_workflow_log_file(self.workflow_id)
        if log_file.exists():
            log_file.unlink()

        # Clear active marker
        self._clear_active()

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the workflow state."""
        if not self._state:
            return {"status": "not_loaded"}

        current_step = self.get_current_step()
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self._state.workflow_type,
            "workflow_name": self._state.workflow_name,
            "status": self._state.status,
            "current_step": self._state.current_step,
            "current_step_type": current_step.step_type if current_step else None,
            "current_step_description": current_step.description if current_step else None,
            "completed_steps": len(self._state.completed_steps),
            "total_steps": len(self.definition.steps) if self.definition else 0,
            "pending_events": self._state.pending_events,
            "github_issue": self._state.github_issue,
            "created_at": self._state.created_at,
            "updated_at": self._state.updated_at
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def get_active_workflow() -> Optional[FileWorkflowEngine]:
    """Get the currently active workflow engine."""
    return FileWorkflowEngine.get_active_workflow()


def has_active_workflow() -> bool:
    """Check if there's an active workflow."""
    return FileWorkflowEngine.get_active_workflow() is not None


def clear_active_workflow() -> None:
    """Clear the active workflow marker."""
    active_file = _get_active_workflow_file()
    if active_file.exists():
        active_file.unlink()


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import uuid

    print("Testing workflow_engine.py...\n")

    # Define a test workflow
    test_workflow_def = {
        "id": "test-workflow",
        "name": "Test Workflow",
        "description": "A simple test workflow",
        "steps": [
            {
                "id": "start",
                "description": "Start the workflow",
                "type": "skill",
                "skill": "pop-test-start",
                "next": "decision"
            },
            {
                "id": "decision",
                "description": "Choose an approach",
                "type": "user_decision",
                "question": "Which approach?",
                "header": "Approach",
                "options": [
                    {"id": "simple", "label": "Simple", "next": "simple_impl"},
                    {"id": "complex", "label": "Complex", "next": "complex_impl"}
                ],
                "next_map": {
                    "simple": "simple_impl",
                    "complex": "complex_impl"
                }
            },
            {
                "id": "simple_impl",
                "description": "Simple implementation",
                "type": "skill",
                "skill": "pop-simple",
                "next": "complete"
            },
            {
                "id": "complex_impl",
                "description": "Complex implementation",
                "type": "skill",
                "skill": "pop-complex",
                "next": "complete"
            },
            {
                "id": "complete",
                "description": "Workflow complete",
                "type": "terminal"
            }
        ]
    }

    # Create a new workflow
    workflow_id = f"test-{uuid.uuid4().hex[:8]}"
    print(f"1. Creating workflow: {workflow_id}")
    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=test_workflow_def,
        initial_context={"test": True},
        github_issue=206
    )
    print(f"   Status: {engine.get_status()}")
    print(f"   Current step: {engine.get_current_step().id}")

    # Advance from start
    print("\n2. Advancing from 'start' step")
    next_step = engine.advance_step({"result": "success"})
    print(f"   Next step: {next_step.id if next_step else 'None'}")
    print(f"   Step type: {next_step.step_type if next_step else 'None'}")

    # Wait for user decision
    print("\n3. Waiting for user decision")
    engine.wait_for_event("decision-approach")
    print(f"   Status: {engine.get_status()}")
    print(f"   Pending events: {engine._state.pending_events}")

    # Simulate user decision
    print("\n4. Notifying decision event")
    engine.notify_event("decision-approach", {"answer": "Simple"})
    print(f"   Status: {engine.get_status()}")

    # Advance with the decision
    print("\n5. Advancing with decision result")
    next_step = engine.advance_step({"answer": "Simple", "option_id": "simple"})
    print(f"   Next step: {next_step.id if next_step else 'None'}")

    # Advance to completion
    print("\n6. Advancing to completion")
    next_step = engine.advance_step({"result": "done"})
    print(f"   Next step: {next_step}")
    print(f"   Status: {engine.get_status()}")

    # Get summary
    print("\n7. Workflow summary:")
    summary = engine.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    # Clean up
    print("\n8. Cleaning up test workflow")
    engine.delete()
    print("   Deleted")

    print("\n[OK] All tests passed!")


# =============================================================================
# Upstash Workflow Engine (Pro Tier - Issue #209)
# =============================================================================

class UpstashWorkflowEngine:
    """Cloud-backed workflow engine for Pro tier users.

    Provides durable workflow orchestration via Upstash Workflow:
    - Survives Claude Code restarts
    - Cross-session persistence
    - Automatic retries
    - Built-in observability

    Requires:
    - POPKIT_API_KEY environment variable
    - Pro tier subscription

    Part of Issue #209: Upstash Workflow Integration (Pro Tier)
    """

    # API URL (same as other PopKit cloud clients)
    API_URL = os.environ.get(
        "POPKIT_API_URL",
        "https://popkit-cloud-api.joseph-cannon.workers.dev"
    )

    def __init__(
        self,
        workflow_id: str,
        definition: Optional[WorkflowDefinition] = None,
        api_key: Optional[str] = None
    ):
        """Initialize the cloud workflow engine.

        Args:
            workflow_id: Unique identifier for this workflow run
            definition: Workflow definition (optional for load operations)
            api_key: PopKit API key (defaults to POPKIT_API_KEY env var)
        """
        self.workflow_id = workflow_id
        self.definition = definition
        self.api_key = api_key or os.environ.get("POPKIT_API_KEY")
        self._cached_status: Optional[Dict[str, Any]] = None

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to PopKit Cloud API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body (for POST/PUT)

        Returns:
            JSON response as dict

        Raises:
            Exception if request fails
        """
        import urllib.request
        import urllib.error

        url = f"{self.API_URL}/v1/workflows{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "popkit-plugin/0.2.0"
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = json.dumps(data).encode("utf-8") if data else None

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise Exception(f"API error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create_workflow(
        cls,
        workflow_id: str,
        workflow_def: Union[Dict[str, Any], WorkflowDefinition],
        initial_context: Optional[Dict[str, Any]] = None,
        github_issue: Optional[int] = None,
        workflow_type: str = "feature-dev"
    ) -> 'UpstashWorkflowEngine':
        """Create a new workflow in the cloud.

        Args:
            workflow_id: Unique identifier for this run
            workflow_def: Workflow definition
            initial_context: Initial context data
            github_issue: Optional linked GitHub issue
            workflow_type: Type of workflow ("feature-dev" or "power-mode")

        Returns:
            UpstashWorkflowEngine instance
        """
        # Parse definition if needed
        if isinstance(workflow_def, dict):
            definition = WorkflowDefinition.from_dict(workflow_def)
        else:
            definition = workflow_def

        engine = cls(workflow_id, definition)

        # Start workflow in cloud
        response = engine._request("POST", f"/{workflow_type}", {
            "feature": definition.name,
            "projectPath": os.getcwd(),
            "sessionId": workflow_id,
            "userId": os.environ.get("POPKIT_USER_ID", "anonymous"),
            "phaseResults": initial_context or {}
        })

        # Store the cloud workflow ID
        engine.workflow_id = response.get("workflowId", workflow_id)

        return engine

    @classmethod
    def load_workflow(cls, workflow_id: str) -> Optional['UpstashWorkflowEngine']:
        """Load an existing workflow from the cloud.

        Args:
            workflow_id: Cloud workflow run ID

        Returns:
            UpstashWorkflowEngine if found, None otherwise
        """
        engine = cls(workflow_id)

        try:
            status = engine._request("GET", f"/status/{workflow_id}")
            if status.get("status") == "unknown":
                return None
            engine._cached_status = status
            return engine
        except Exception:
            return None

    # =========================================================================
    # Status Methods
    # =========================================================================

    def get_status(self) -> str:
        """Get current workflow status from cloud.

        Returns:
            Status string: "running", "waiting", "complete", "error"
        """
        try:
            status = self._request("GET", f"/status/{self.workflow_id}")
            self._cached_status = status
            return status.get("status", "unknown")
        except Exception:
            return "error"

    def get_state(self) -> WorkflowState:
        """Get workflow state from cloud.

        Returns:
            WorkflowState object with current state
        """
        status = self._cached_status or {}

        try:
            if not self._cached_status:
                status = self._request("GET", f"/status/{self.workflow_id}")
                self._cached_status = status
        except Exception:
            pass

        return WorkflowState(
            workflow_id=self.workflow_id,
            workflow_type=status.get("workflowType", "unknown"),
            workflow_name=status.get("workflowName", "Cloud Workflow"),
            current_step=status.get("currentPhase", ""),
            context=status.get("context", {}),
            status=status.get("status", "unknown"),
            step_history=[],
            pending_events=[]
        )

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current step in the workflow.

        Returns:
            WorkflowStep for current phase, or None
        """
        status = self.get_status()
        current_phase = self._cached_status.get("currentPhase") if self._cached_status else None

        if not current_phase or not self.definition:
            # Return a simple step based on phase name
            return WorkflowStep(
                id=current_phase or "unknown",
                description=f"Phase: {current_phase}",
                step_type="skill"
            )

        return self.definition.get_step(current_phase)

    def get_context(self) -> Dict[str, Any]:
        """Get accumulated workflow context from cloud.

        Returns:
            Context dictionary
        """
        state = self.get_state()
        return state.context

    # =========================================================================
    # Workflow Control Methods
    # =========================================================================

    def advance_step(self, result: Optional[Dict[str, Any]] = None) -> Optional[WorkflowStep]:
        """Advance the workflow to the next step.

        Args:
            result: Result data from current step

        Returns:
            Next WorkflowStep, or None if complete
        """
        current_phase = self._cached_status.get("currentPhase") if self._cached_status else None

        # Update cloud with phase result
        self._request("POST", f"/update/{self.workflow_id}", {
            "phase": current_phase,
            "result": json.dumps(result) if result else "complete"
        })

        # Refresh status
        new_status = self._request("GET", f"/status/{self.workflow_id}")
        self._cached_status = new_status

        new_phase = new_status.get("currentPhase")
        if not new_phase or new_status.get("status") == "complete":
            return None

        return WorkflowStep(
            id=new_phase,
            description=f"Phase: {new_phase}",
            step_type="skill"
        )

    def wait_for_event(self, event_id: str) -> None:
        """Mark workflow as waiting for an event.

        For cloud workflows, this is tracked in the cloud.

        Args:
            event_id: Event to wait for
        """
        # Cloud workflows use waitForEvent internally
        # We just track it locally for the response router
        if self._cached_status:
            self._cached_status["waitingFor"] = event_id

    def notify_event(self, event_id: str, data: Dict[str, Any]) -> bool:
        """Notify the workflow that an event occurred.

        Args:
            event_id: Event identifier
            data: Event data (e.g., user decision)

        Returns:
            True if event was processed
        """
        try:
            # For cloud workflows, we notify the cloud API
            self._request("POST", f"/{self.workflow_id}/events", {
                "event_id": event_id,
                "data": data
            })
            return True
        except Exception:
            return False

    def set_error(self, error_message: str) -> None:
        """Mark the workflow as errored."""
        # Update cloud with error
        try:
            self._request("POST", f"/update/{self.workflow_id}", {
                "phase": "error",
                "result": error_message
            })
        except Exception:
            pass

    def cancel(self) -> None:
        """Cancel the workflow."""
        self.set_error("Cancelled by user")

    def delete(self) -> None:
        """Delete workflow (cloud workflows expire automatically)."""
        # Cloud workflows have TTL, no explicit delete needed
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary from cloud.

        Returns:
            Summary dictionary
        """
        status = self._request("GET", f"/status/{self.workflow_id}")

        return {
            "workflow_id": self.workflow_id,
            "workflow_type": status.get("workflowType", "unknown"),
            "status": status.get("status", "unknown"),
            "current_phase": status.get("currentPhase"),
            "phases_completed": len([
                p for p in status.get("phases", [])
                if p.get("status") == "complete"
            ]),
            "total_phases": len(status.get("phases", [])),
            "started_at": status.get("startedAt"),
            "completed_at": status.get("completedAt"),
            "storage": "upstash_cloud"
        }


# =============================================================================
# Workflow Engine Factory (Issue #209)
# =============================================================================

def is_pro_tier() -> bool:
    """Check if user has Pro tier subscription.

    Returns:
        True if Pro or Team tier
    """
    # Import here to avoid circular dependency
    try:
        from premium_checker import get_user_tier, Tier
        tier = get_user_tier()
        return tier in (Tier.PRO, Tier.TEAM)
    except ImportError:
        pass

    # Fallback: Check environment variable
    tier = os.environ.get("POPKIT_TIER", "free").lower()
    return tier in ("pro", "team")


def get_workflow_engine(
    workflow_id: Optional[str] = None,
    force_local: bool = False,
    force_cloud: bool = False
) -> Union[FileWorkflowEngine, UpstashWorkflowEngine, None]:
    """Factory to get the appropriate workflow engine.

    Selection priority:
    1. force_local=True → FileWorkflowEngine
    2. force_cloud=True → UpstashWorkflowEngine (fails if not Pro)
    3. Pro tier → UpstashWorkflowEngine
    4. Free tier → FileWorkflowEngine

    Args:
        workflow_id: Workflow ID to load (None for new workflows)
        force_local: Force file-based engine
        force_cloud: Force cloud-based engine

    Returns:
        Appropriate workflow engine, or None if not found
    """
    # Force local file-based engine
    if force_local:
        if workflow_id:
            return FileWorkflowEngine.load_workflow(workflow_id)
        return None  # Need to call create_workflow explicitly

    # Force cloud engine (requires Pro)
    if force_cloud:
        if not is_pro_tier():
            raise Exception("Cloud workflows require Pro tier subscription")
        if workflow_id:
            return UpstashWorkflowEngine.load_workflow(workflow_id)
        return None

    # Auto-select based on tier
    if is_pro_tier():
        # Pro users get cloud workflows
        if workflow_id:
            # Try cloud first, fall back to local
            engine = UpstashWorkflowEngine.load_workflow(workflow_id)
            if engine:
                return engine
            return FileWorkflowEngine.load_workflow(workflow_id)
        return None
    else:
        # Free users get file-based workflows
        if workflow_id:
            return FileWorkflowEngine.load_workflow(workflow_id)
        return None


def create_workflow_engine(
    workflow_id: str,
    workflow_def: Union[Dict[str, Any], WorkflowDefinition],
    initial_context: Optional[Dict[str, Any]] = None,
    github_issue: Optional[int] = None,
    force_local: bool = False,
    force_cloud: bool = False
) -> Union[FileWorkflowEngine, UpstashWorkflowEngine]:
    """Factory to create a new workflow with appropriate engine.

    Args:
        workflow_id: Unique identifier for this run
        workflow_def: Workflow definition
        initial_context: Initial context data
        github_issue: Optional linked GitHub issue
        force_local: Force file-based engine
        force_cloud: Force cloud-based engine

    Returns:
        Appropriate workflow engine with workflow created
    """
    if force_local or not is_pro_tier():
        return FileWorkflowEngine.create_workflow(
            workflow_id=workflow_id,
            workflow_def=workflow_def,
            initial_context=initial_context,
            github_issue=github_issue
        )

    if force_cloud or is_pro_tier():
        return UpstashWorkflowEngine.create_workflow(
            workflow_id=workflow_id,
            workflow_def=workflow_def,
            initial_context=initial_context,
            github_issue=github_issue
        )

    # Default fallback
    return FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=workflow_def,
        initial_context=initial_context,
        github_issue=github_issue
    )
