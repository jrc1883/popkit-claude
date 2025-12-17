#!/usr/bin/env python3
"""
Skill Context for Skill-to-Skill Handoff

Extends the HookContext pattern for skill-level coordination.
Skills can read context from previous skills and output context
for downstream skills - the "roundtable" pattern.

Part of Issue #188: Implement skill-to-skill context handoff system

Usage:
    # At skill start - check for upstream context
    ctx = load_skill_context()
    if ctx and ctx.previous_skill == "pop-brainstorming":
        design_doc = ctx.artifacts.get("design_document")

    # At skill end - save for downstream
    save_skill_context(SkillOutput(
        skill_name="pop-writing-plans",
        status="completed",
        output={"plan_file": "docs/plans/..."},
        artifacts=["docs/plans/feature-plan.md"],
        next_suggested="pop-executing-plans"
    ))
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SkillContext:
    """Context passed between skills in a workflow chain.

    Represents the "inbox" for a skill - what previous skills produced.
    Immutable once created to prevent accidental mutation.
    """
    workflow_id: str                    # Unique workflow run ID
    previous_skill: Optional[str]       # Name of upstream skill
    previous_output: Dict[str, Any]     # Structured output from upstream
    shared_decisions: List[Dict]        # User decisions already made (AskUserQuestion)
    artifacts: Dict[str, str]           # Files created: {"design_document": "path/to/file.md"}
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    github_issue: Optional[int] = None  # Linked GitHub issue number


@dataclass
class SkillOutput:
    """Output from a skill to pass to downstream skills.

    Represents the "outbox" - what this skill produced for others.
    """
    skill_name: str
    status: str                         # "completed", "needs_input", "error"
    output: Dict[str, Any]              # Structured data for downstream
    artifacts: List[str]                # Files created (paths)
    next_suggested: Optional[str] = None  # Suggested next skill
    error_message: Optional[str] = None   # If status is "error"
    decisions_made: List[Dict] = field(default_factory=list)  # AskUserQuestion results


# =============================================================================
# Storage Paths
# =============================================================================

def _get_popkit_dir() -> Path:
    """Get .popkit directory in current project."""
    # Look for project root indicators
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "package.json").exists():
            popkit_dir = parent / ".popkit"
            popkit_dir.mkdir(exist_ok=True)
            return popkit_dir
    # Fallback to current directory
    popkit_dir = current / ".popkit"
    popkit_dir.mkdir(exist_ok=True)
    return popkit_dir


def _get_context_dir() -> Path:
    """Get context storage directory."""
    context_dir = _get_popkit_dir() / "context"
    context_dir.mkdir(exist_ok=True)
    return context_dir


def _get_current_workflow_file() -> Path:
    """Get current workflow state file."""
    return _get_context_dir() / "current-workflow.json"


def _get_decisions_file() -> Path:
    """Get user decisions cache file."""
    return _get_context_dir() / "decisions.json"


def _get_artifacts_file() -> Path:
    """Get artifacts registry file."""
    return _get_context_dir() / "artifacts.json"


# =============================================================================
# File-Based Storage (Free Mode)
# =============================================================================

def load_skill_context() -> Optional[SkillContext]:
    """Load context from previous skill (file-based).

    Returns None if no context exists or workflow is fresh.

    Example:
        ctx = load_skill_context()
        if ctx and ctx.previous_skill == "pop-brainstorming":
            design = ctx.artifacts.get("design_document")
    """
    workflow_file = _get_current_workflow_file()

    if not workflow_file.exists():
        return None

    try:
        with open(workflow_file, 'r') as f:
            data = json.load(f)

        return SkillContext(
            workflow_id=data.get("workflow_id", "unknown"),
            previous_skill=data.get("previous_skill"),
            previous_output=data.get("previous_output", {}),
            shared_decisions=data.get("shared_decisions", []),
            artifacts=data.get("artifacts", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            github_issue=data.get("github_issue")
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_skill_context(output: SkillOutput) -> None:
    """Save skill output for downstream skills (file-based).

    Updates the workflow state file with this skill's output.

    Example:
        save_skill_context(SkillOutput(
            skill_name="pop-brainstorming",
            status="completed",
            output={"topic": "auth system"},
            artifacts=["docs/plans/auth-design.md"],
            next_suggested="pop-writing-plans"
        ))
    """
    workflow_file = _get_current_workflow_file()

    # Load existing or create new
    existing = {}
    if workflow_file.exists():
        try:
            with open(workflow_file, 'r') as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = {}

    # Generate workflow ID if new
    workflow_id = existing.get("workflow_id") or f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Merge artifacts (accumulate, don't replace)
    artifacts = existing.get("artifacts", {})
    for artifact_path in output.artifacts:
        # Key by filename for easy lookup
        filename = Path(artifact_path).name
        artifacts[filename] = artifact_path

    # Accumulate decisions
    decisions = existing.get("shared_decisions", [])
    decisions.extend(output.decisions_made)

    # Build new state
    state = {
        "workflow_id": workflow_id,
        "previous_skill": output.skill_name,
        "previous_output": output.output,
        "previous_status": output.status,
        "shared_decisions": decisions,
        "artifacts": artifacts,
        "next_suggested": output.next_suggested,
        "updated_at": datetime.now().isoformat(),
        "github_issue": existing.get("github_issue")
    }

    if output.error_message:
        state["last_error"] = output.error_message

    with open(workflow_file, 'w') as f:
        json.dump(state, f, indent=2)


def clear_workflow_context() -> None:
    """Clear the current workflow context (start fresh)."""
    workflow_file = _get_current_workflow_file()
    if workflow_file.exists():
        workflow_file.unlink()


def get_workflow_summary() -> Dict[str, Any]:
    """Get a summary of the current workflow state.

    Useful for status displays and debugging.
    """
    ctx = load_skill_context()
    if not ctx:
        return {"status": "no_active_workflow"}

    return {
        "workflow_id": ctx.workflow_id,
        "previous_skill": ctx.previous_skill,
        "artifact_count": len(ctx.artifacts),
        "decision_count": len(ctx.shared_decisions),
        "github_issue": ctx.github_issue,
        "created_at": ctx.created_at
    }


# =============================================================================
# Decision Caching
# =============================================================================

def cache_decision(decision_id: str, question: str, answer: str) -> None:
    """Cache a user decision to avoid re-asking.

    Called when AskUserQuestion is answered.
    """
    decisions_file = _get_decisions_file()

    decisions = {}
    if decisions_file.exists():
        try:
            with open(decisions_file, 'r') as f:
                decisions = json.load(f)
        except json.JSONDecodeError:
            decisions = {}

    decisions[decision_id] = {
        "question": question,
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    }

    with open(decisions_file, 'w') as f:
        json.dump(decisions, f, indent=2)


def get_cached_decision(decision_id: str) -> Optional[str]:
    """Get a previously cached decision.

    Returns None if decision hasn't been made.
    """
    decisions_file = _get_decisions_file()

    if not decisions_file.exists():
        return None

    try:
        with open(decisions_file, 'r') as f:
            decisions = json.load(f)
        return decisions.get(decision_id, {}).get("answer")
    except (json.JSONDecodeError, KeyError):
        return None


def has_decision(decision_id: str) -> bool:
    """Check if a decision has been made."""
    return get_cached_decision(decision_id) is not None


# =============================================================================
# Artifact Registry
# =============================================================================

def register_artifact(name: str, path: str, artifact_type: str = "file") -> None:
    """Register an artifact created during the workflow.

    Artifacts are files or resources created by skills that should
    be available to downstream skills.
    """
    artifacts_file = _get_artifacts_file()

    artifacts = {}
    if artifacts_file.exists():
        try:
            with open(artifacts_file, 'r') as f:
                artifacts = json.load(f)
        except json.JSONDecodeError:
            artifacts = {}

    artifacts[name] = {
        "path": path,
        "type": artifact_type,
        "created_at": datetime.now().isoformat()
    }

    with open(artifacts_file, 'w') as f:
        json.dump(artifacts, f, indent=2)


def get_artifact(name: str) -> Optional[str]:
    """Get the path to a registered artifact."""
    artifacts_file = _get_artifacts_file()

    if not artifacts_file.exists():
        return None

    try:
        with open(artifacts_file, 'r') as f:
            artifacts = json.load(f)
        return artifacts.get(name, {}).get("path")
    except (json.JSONDecodeError, KeyError):
        return None


# =============================================================================
# Link to GitHub Issue
# =============================================================================

def link_workflow_to_issue(issue_number: int) -> None:
    """Link the current workflow to a GitHub issue."""
    workflow_file = _get_current_workflow_file()

    state = {}
    if workflow_file.exists():
        try:
            with open(workflow_file, 'r') as f:
                state = json.load(f)
        except json.JSONDecodeError:
            state = {}

    state["github_issue"] = issue_number
    state["updated_at"] = datetime.now().isoformat()

    with open(workflow_file, 'w') as f:
        json.dump(state, f, indent=2)


def get_linked_issue() -> Optional[int]:
    """Get the GitHub issue linked to current workflow."""
    ctx = load_skill_context()
    return ctx.github_issue if ctx else None


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("Testing skill_context.py...")

    # Clear any existing context
    clear_workflow_context()

    # Test saving context
    save_skill_context(SkillOutput(
        skill_name="pop-brainstorming",
        status="completed",
        output={"topic": "authentication", "approach": "JWT"},
        artifacts=["docs/plans/auth-design.md"],
        next_suggested="pop-writing-plans",
        decisions_made=[{"id": "auth_method", "answer": "JWT"}]
    ))
    print("Saved brainstorming output")

    # Test loading context
    ctx = load_skill_context()
    assert ctx is not None
    assert ctx.previous_skill == "pop-brainstorming"
    assert ctx.artifacts.get("auth-design.md") == "docs/plans/auth-design.md"
    print(f"Loaded context: previous={ctx.previous_skill}, artifacts={list(ctx.artifacts.keys())}")

    # Test decision caching
    cache_decision("auth_method", "Which auth method?", "JWT")
    assert get_cached_decision("auth_method") == "JWT"
    assert has_decision("auth_method") is True
    print("Decision caching works")

    # Test artifact registry
    register_artifact("design_doc", "docs/plans/auth-design.md", "markdown")
    assert get_artifact("design_doc") == "docs/plans/auth-design.md"
    print("Artifact registry works")

    # Test workflow summary
    summary = get_workflow_summary()
    print(f"Summary: {summary}")

    # Clean up
    clear_workflow_context()
    print("\nAll tests passed!")
