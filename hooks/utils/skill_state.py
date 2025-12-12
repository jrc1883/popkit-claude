#!/usr/bin/env python3
"""
Skill state tracking for AskUserQuestion enforcement (Issue #159)
and activity ledger publishing (Issue #188).

Follows Anthropic's recommendation from the Hooks Guide:
"By encoding these rules as hooks rather than prompting instructions,
you turn suggestions into app-level code that executes every time."

This module tracks:
- Which skill is currently active
- Which required decisions have been made
- Whether completion decisions are pending
- Publishes skill lifecycle events to activity ledger
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field


@dataclass
class SkillState:
    """State for a single skill execution."""
    skill_name: str
    workflow_id: Optional[str] = None
    decisions_made: Set[str] = field(default_factory=set)
    tool_calls: int = 0
    error_occurred: bool = False
    last_error: Optional[str] = None
    activity_id: Optional[str] = None  # ID from activity stream


class SkillStateTracker:
    """Tracks active skill and enforces required decisions."""

    _instance: Optional['SkillStateTracker'] = None

    def __init__(self):
        self.state: Optional[SkillState] = None
        self._config: Optional[dict] = None

    @classmethod
    def get_instance(cls) -> 'SkillStateTracker':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def config(self) -> dict:
        """Lazy-load skill_decisions from config.json."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> dict:
        """Load skill_decisions section from agents/config.json."""
        # Find config.json relative to this file
        # hooks/utils/skill_state.py -> agents/config.json
        utils_dir = Path(__file__).parent
        hooks_dir = utils_dir.parent
        plugin_dir = hooks_dir.parent
        config_path = plugin_dir / "agents" / "config.json"

        if not config_path.exists():
            # Fallback: try relative to CLAUDE_PLUGIN_ROOT env var
            plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
            if plugin_root:
                config_path = Path(plugin_root) / "agents" / "config.json"

        if config_path.exists():
            try:
                full_config = json.loads(config_path.read_text(encoding="utf-8"))
                return full_config.get("skill_decisions", {})
            except (json.JSONDecodeError, OSError):
                pass

        return {}

    def get_skill_config(self, skill_name: str) -> dict:
        """Get configuration for a specific skill."""
        # Normalize skill name (remove 'pop-' prefix variations, handle namespacing)
        normalized = skill_name.replace("popkit:", "").strip()

        skills = self.config.get("skills", {})

        # Try exact match first
        if normalized in skills:
            return skills[normalized]

        # Try with 'pop-' prefix
        if f"pop-{normalized}" in skills:
            return skills[f"pop-{normalized}"]

        # Try without 'pop-' prefix
        if normalized.startswith("pop-"):
            bare_name = normalized[4:]
            if bare_name in skills:
                return skills[bare_name]

        return {}

    def start_skill(self, skill_name: str, workflow_id: Optional[str] = None) -> None:
        """Called when a skill is invoked via Skill tool.

        Publishes 'start' event to activity ledger for real-time awareness.
        """
        self.state = SkillState(skill_name=skill_name, workflow_id=workflow_id)

        # Publish to activity ledger (Issue #188)
        activity_id = self._publish_activity("start", {
            "skill": skill_name,
            "workflow": workflow_id
        })
        if activity_id and self.state:
            self.state.activity_id = activity_id

    def end_skill(self, status: str = "complete", output: Optional[Dict[str, Any]] = None) -> None:
        """Called when skill completes.

        Publishes 'complete' or 'error' event to activity ledger.

        Args:
            status: "complete" or "error"
            output: Optional output data to include in event
        """
        if self.state:
            event_data = {
                "skill": self.state.skill_name,
                "workflow": self.state.workflow_id,
                "tool_calls": self.state.tool_calls,
                "decisions_made": list(self.state.decisions_made),
                "output": output or {}
            }

            if self.state.error_occurred:
                status = "error"
                event_data["error"] = self.state.last_error

            self._publish_activity(status, event_data)

        self.state = None

    def _publish_activity(self, event_type: str, data: Dict[str, Any]) -> Optional[str]:
        """Publish activity event to storage backend.

        Tries to import context_storage lazily to avoid circular imports.
        Returns activity ID if successful.
        """
        try:
            from context_storage import get_context_storage
            storage = get_context_storage()

            skill_name = data.get("skill", "unknown")
            workflow_id = data.get("workflow")

            return storage.publish_activity(
                skill_name=skill_name,
                event_type=event_type,
                data=data,
                workflow_id=workflow_id
            )
        except ImportError:
            # context_storage not available, skip activity publishing
            return None
        except Exception:
            # Don't let activity publishing failures break skill tracking
            return None

    def record_decision(self, decision_id: str) -> None:
        """Record that a user decision was made."""
        if self.state:
            self.state.decisions_made.add(decision_id)

    def record_decision_by_header(self, header: str) -> None:
        """Record decision by matching header to decision ID."""
        if not self.state:
            return

        skill_config = self.get_skill_config(self.state.skill_name)
        completion_decisions = skill_config.get("completion_decisions", [])

        # Match header to decision
        normalized_header = header.lower().replace(" ", "_").replace("-", "_")
        for decision in completion_decisions:
            decision_header = decision.get("header", "").lower().replace(" ", "_").replace("-", "_")
            if normalized_header == decision_header:
                self.state.decisions_made.add(decision["id"])
                return

        # Also match by question substring
        for decision in completion_decisions:
            if header.lower() in decision.get("question", "").lower():
                self.state.decisions_made.add(decision["id"])
                return

    def record_tool_use(self, tool_name: str, publish_progress: bool = False) -> None:
        """Record that a tool was used.

        Args:
            tool_name: Name of the tool being used
            publish_progress: If True, publish progress event to activity ledger
                            (use sparingly to avoid excessive events)
        """
        if self.state:
            self.state.tool_calls += 1

            # Optionally publish progress (every 5th tool call by default)
            if publish_progress or (self.state.tool_calls % 5 == 0):
                self._publish_activity("progress", {
                    "skill": self.state.skill_name,
                    "workflow": self.state.workflow_id,
                    "tool": tool_name,
                    "tool_calls": self.state.tool_calls
                })

    def record_error(self, error_message: str) -> None:
        """Record that an error occurred during skill execution (Issue #183)."""
        if self.state:
            self.state.error_occurred = True
            self.state.last_error = error_message

    def has_error(self) -> bool:
        """Check if an error occurred during skill execution."""
        return self.state.error_occurred if self.state else False

    def get_pending_completion_decisions(self, include_on_error: bool = False) -> List[dict]:
        """Get completion decisions that haven't been made yet.

        Args:
            include_on_error: If True, include on_error decisions even if no error occurred.
                             If an error HAS occurred, on_error decisions are always included.
        """
        if not self.state:
            return []

        skill_config = self.get_skill_config(self.state.skill_name)
        completion_decisions = skill_config.get("completion_decisions", [])

        pending = []
        for decision in completion_decisions:
            if decision["id"] not in self.state.decisions_made:
                # Check if this is an on_error decision
                is_on_error = decision.get("on_error", False)

                # Include on_error decisions if:
                # - An error actually occurred, OR
                # - include_on_error flag is True (caller wants to see all)
                if is_on_error and not self.state.error_occurred and not include_on_error:
                    continue

                pending.append(decision)

        return pending

    def get_required_decisions(self) -> List[dict]:
        """Get required completion decisions that haven't been made yet (Issue #183).

        Required decisions MUST be presented even on error/early completion.
        """
        if not self.state:
            return []

        skill_config = self.get_skill_config(self.state.skill_name)
        completion_decisions = skill_config.get("completion_decisions", [])

        required = []
        for decision in completion_decisions:
            if decision["id"] not in self.state.decisions_made:
                # Check if this decision is required
                if decision.get("required", False):
                    required.append(decision)

        return required

    def get_error_recovery_decisions(self) -> List[dict]:
        """Get decisions specifically for error recovery (Issue #183).

        These are decisions marked with on_error=true that should be shown
        when skill execution encounters an error.
        """
        if not self.state or not self.state.error_occurred:
            return []

        skill_config = self.get_skill_config(self.state.skill_name)
        completion_decisions = skill_config.get("completion_decisions", [])

        recovery = []
        for decision in completion_decisions:
            if decision["id"] not in self.state.decisions_made:
                if decision.get("on_error", False):
                    recovery.append(decision)

        return recovery

    def has_pending_decisions(self) -> bool:
        """Check if there are any pending completion decisions."""
        return len(self.get_pending_completion_decisions()) > 0

    def has_required_pending(self) -> bool:
        """Check if there are required decisions that must be presented (Issue #183)."""
        return len(self.get_required_decisions()) > 0

    def is_skill_active(self) -> bool:
        """Check if a skill is currently being tracked."""
        return self.state is not None

    def get_active_skill(self) -> Optional[str]:
        """Get the name of the currently active skill."""
        return self.state.skill_name if self.state else None


def get_tracker() -> SkillStateTracker:
    """Get the singleton skill state tracker."""
    return SkillStateTracker.get_instance()


# For testing
if __name__ == "__main__":
    tracker = get_tracker()
    print(f"Loaded config skills: {list(tracker.config.get('skills', {}).keys())}")

    # Test skill tracking with pop-project-init
    print("\n=== Test: pop-project-init ===")
    tracker.start_skill("pop-project-init")
    print(f"Active skill: {tracker.get_active_skill()}")
    print(f"Pending decisions: {len(tracker.get_pending_completion_decisions())}")

    tracker.record_decision("next_action")
    print(f"After decision - pending: {len(tracker.get_pending_completion_decisions())}")
    tracker.end_skill()

    # Test required decisions with pop-research-merge (Issue #183)
    print("\n=== Test: pop-research-merge (required decisions) ===")
    tracker.start_skill("pop-research-merge")
    print(f"Required decisions: {len(tracker.get_required_decisions())}")
    print(f"Has required pending: {tracker.has_required_pending()}")

    # Simulate error
    tracker.record_error("Issue already closed")
    print(f"Has error: {tracker.has_error()}")
    print(f"Error recovery decisions: {len(tracker.get_error_recovery_decisions())}")

    tracker.end_skill()
    print(f"After end - active: {tracker.get_active_skill()}")
