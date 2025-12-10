#!/usr/bin/env python3
"""
Skill state tracking for AskUserQuestion enforcement (Issue #159).

Follows Anthropic's recommendation from the Hooks Guide:
"By encoding these rules as hooks rather than prompting instructions,
you turn suggestions into app-level code that executes every time."

This module tracks:
- Which skill is currently active
- Which required decisions have been made
- Whether completion decisions are pending
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SkillState:
    """State for a single skill execution."""
    skill_name: str
    decisions_made: Set[str] = field(default_factory=set)
    tool_calls: int = 0


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

    def start_skill(self, skill_name: str) -> None:
        """Called when a skill is invoked via Skill tool."""
        self.state = SkillState(skill_name=skill_name)

    def end_skill(self) -> None:
        """Called when skill completes."""
        self.state = None

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

    def record_tool_use(self, tool_name: str) -> None:
        """Record that a tool was used (for step counting if needed later)."""
        if self.state:
            self.state.tool_calls += 1

    def get_pending_completion_decisions(self) -> List[dict]:
        """Get completion decisions that haven't been made yet."""
        if not self.state:
            return []

        skill_config = self.get_skill_config(self.state.skill_name)
        completion_decisions = skill_config.get("completion_decisions", [])

        pending = []
        for decision in completion_decisions:
            if decision["id"] not in self.state.decisions_made:
                pending.append(decision)

        return pending

    def has_pending_decisions(self) -> bool:
        """Check if there are any pending completion decisions."""
        return len(self.get_pending_completion_decisions()) > 0

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
    print(f"Loaded config: {json.dumps(tracker.config, indent=2)}")

    # Test skill tracking
    tracker.start_skill("pop-project-init")
    print(f"Active skill: {tracker.get_active_skill()}")
    print(f"Pending decisions: {tracker.get_pending_completion_decisions()}")

    # Simulate decision made
    tracker.record_decision("next_action")
    print(f"After decision - pending: {tracker.get_pending_completion_decisions()}")

    tracker.end_skill()
    print(f"After end - active: {tracker.get_active_skill()}")
