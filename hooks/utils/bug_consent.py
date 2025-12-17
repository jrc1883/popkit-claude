#!/usr/bin/env python3
"""
Bug Consent Handler

Part of Issue #90 (Automatic Bug Reporting System)

Handles user consent prompts for bug sharing using AskUserQuestion integration.
Provides formatted questions for Claude to present to users.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import sys
from pathlib import Path

# Ensure utils directory is in path
utils_dir = Path(__file__).parent
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))

# Import from same module that will be used elsewhere
from utils.bug_store import get_bug_store, ShareStatus, ConsentLevel


class ConsentAction(Enum):
    """Actions from consent prompts"""
    SHARE_NOW = "share_now"           # Share this bug
    SHARE_ALWAYS = "share_always"     # Share this and future bugs automatically
    LOCAL_ONLY = "local_only"         # Keep local only
    NEVER_ASK = "never_ask"           # Never ask about sharing again


@dataclass
class ConsentQuestion:
    """Formatted question for AskUserQuestion tool"""
    question: str
    header: str
    options: List[Dict[str, str]]
    multi_select: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for AskUserQuestion tool"""
        return {
            "question": self.question,
            "header": self.header,
            "options": self.options,
            "multiSelect": self.multi_select
        }


def get_share_consent_question(bug_summary: str) -> ConsentQuestion:
    """
    Generate a consent question for sharing a detected bug.

    Args:
        bug_summary: Brief summary of the detected bug

    Returns:
        ConsentQuestion formatted for AskUserQuestion
    """
    return ConsentQuestion(
        question=f"A bug was detected: {bug_summary[:60]}... Would you like to share this pattern to help improve suggestions for everyone?",
        header="Bug sharing",
        options=[
            {
                "label": "Share this bug",
                "description": "Anonymize and share this pattern to the collective learning database"
            },
            {
                "label": "Always share",
                "description": "Share this and automatically share future bugs (can be changed later)"
            },
            {
                "label": "Keep local",
                "description": "Keep this bug report local, don't share"
            },
            {
                "label": "Never ask",
                "description": "Don't ask about sharing - keep everything local"
            }
        ],
        multi_select=False
    )


def get_first_time_consent_question() -> ConsentQuestion:
    """
    Generate the first-time consent setup question.

    Returns:
        ConsentQuestion for initial consent level selection
    """
    return ConsentQuestion(
        question="PopKit can automatically detect and log bugs to help you debug. How would you like to handle bug sharing?",
        header="Bug privacy",
        options=[
            {
                "label": "Strict (default)",
                "description": "All bugs stay local. You manually choose what to share."
            },
            {
                "label": "Moderate",
                "description": "Auto-detect bugs, ask before sharing anonymized patterns"
            },
            {
                "label": "Minimal",
                "description": "Auto-share anonymized patterns to help improve collective learning"
            }
        ],
        multi_select=False
    )


def get_auto_detect_consent_question() -> ConsentQuestion:
    """
    Generate question about enabling auto-detection.

    Returns:
        ConsentQuestion for auto-detection preference
    """
    return ConsentQuestion(
        question="Would you like PopKit to automatically detect and log bugs during your session?",
        header="Auto-detect",
        options=[
            {
                "label": "Enable",
                "description": "Automatically detect errors and stuck patterns, log locally"
            },
            {
                "label": "Disable",
                "description": "Only log bugs when you manually report them"
            }
        ],
        multi_select=False
    )


def process_share_response(response: str, bug_id: str) -> Dict[str, Any]:
    """
    Process user response to share consent question.

    Args:
        response: User's selected option label
        bug_id: The bug ID to update

    Returns:
        Dict with action taken and updated preferences
    """
    store = get_bug_store()
    result = {
        "bug_id": bug_id,
        "action": None,
        "sharing_enabled": store.is_sharing_enabled(),
        "ask_before_share": store.should_ask_before_share()
    }

    response_lower = response.lower()

    if "share this" in response_lower:
        # Share this specific bug
        store.update_share_status(bug_id, ShareStatus.SHARED)
        result["action"] = "shared"

    elif "always share" in response_lower:
        # Enable automatic sharing
        store.update_share_status(bug_id, ShareStatus.SHARED)
        store.set_sharing_enabled(True)
        store.set_ask_before_share(False)
        store.set_consent_level(ConsentLevel.MINIMAL)
        result["action"] = "shared"
        result["sharing_enabled"] = True
        result["ask_before_share"] = False

    elif "keep local" in response_lower:
        # Keep local only
        store.update_share_status(bug_id, ShareStatus.LOCAL_ONLY)
        result["action"] = "local_only"

    elif "never ask" in response_lower:
        # Never ask again
        store.update_share_status(bug_id, ShareStatus.NEVER_ASK)
        store.set_sharing_enabled(False)
        store.set_ask_before_share(False)
        result["action"] = "never_ask"
        result["sharing_enabled"] = False
        result["ask_before_share"] = False

    return result


def process_consent_level_response(response: str) -> Dict[str, Any]:
    """
    Process user response to consent level question.

    Args:
        response: User's selected option label

    Returns:
        Dict with updated consent configuration
    """
    store = get_bug_store()
    result = {
        "consent_level": None,
        "sharing_enabled": False,
        "ask_before_share": True,
        "auto_detect": True
    }

    response_lower = response.lower()

    if "strict" in response_lower:
        store.set_consent_level(ConsentLevel.STRICT)
        store.set_sharing_enabled(False)
        store.set_ask_before_share(True)
        result["consent_level"] = "strict"

    elif "moderate" in response_lower:
        store.set_consent_level(ConsentLevel.MODERATE)
        store.set_sharing_enabled(True)
        store.set_ask_before_share(True)
        result["consent_level"] = "moderate"
        result["sharing_enabled"] = True

    elif "minimal" in response_lower:
        store.set_consent_level(ConsentLevel.MINIMAL)
        store.set_sharing_enabled(True)
        store.set_ask_before_share(False)
        result["consent_level"] = "minimal"
        result["sharing_enabled"] = True
        result["ask_before_share"] = False

    return result


def process_auto_detect_response(response: str) -> Dict[str, Any]:
    """
    Process user response to auto-detect question.

    Args:
        response: User's selected option label

    Returns:
        Dict with updated auto-detect preference
    """
    store = get_bug_store()
    result = {"auto_detect_enabled": False}

    response_lower = response.lower()

    if "enable" in response_lower:
        store.set_auto_detect_enabled(True)
        result["auto_detect_enabled"] = True
    else:
        store.set_auto_detect_enabled(False)
        result["auto_detect_enabled"] = False

    return result


def should_ask_for_sharing(bug_id: str) -> bool:
    """
    Check if we should ask the user about sharing a bug.

    Args:
        bug_id: The bug ID to check

    Returns:
        True if we should ask, False otherwise
    """
    store = get_bug_store()

    # If sharing is disabled entirely, don't ask
    if not store.is_sharing_enabled():
        return False

    # If user said never ask, don't ask
    if not store.should_ask_before_share():
        return False

    # Check if bug exists and is pending
    bug = store.get_bug(bug_id)
    if bug and bug.share_status == "pending":
        return True

    return False


def get_pending_bugs_for_consent(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get bugs that need consent for sharing.

    Args:
        limit: Maximum number of bugs to return

    Returns:
        List of bug info dicts needing consent
    """
    store = get_bug_store()

    # Only get pending bugs if sharing is enabled and we should ask
    if not store.is_sharing_enabled() or not store.should_ask_before_share():
        return []

    bugs = store.list_bugs(limit=limit, share_status="pending")
    return [
        {
            "id": bug.id,
            "error_type": bug.error_type,
            "summary": bug.context_summary,
            "confidence": bug.confidence,
            "created_at": bug.created_at
        }
        for bug in bugs
    ]


def format_consent_summary() -> str:
    """
    Format a summary of current consent preferences.

    Returns:
        Human-readable consent summary
    """
    store = get_bug_store()
    stats = store.get_stats()

    lines = [
        "Bug Reporting Preferences",
        "=" * 30,
        f"Consent Level: {stats['consent_level']}",
        f"Sharing Enabled: {'Yes' if stats['sharing_enabled'] else 'No'}",
        f"Auto-Detect: {'Enabled' if store.is_auto_detect_enabled() else 'Disabled'}",
        f"Ask Before Share: {'Yes' if store.should_ask_before_share() else 'No'}",
        "",
        f"Total Bugs Captured: {stats['total_bugs']}",
    ]

    if stats.get('by_share_status'):
        lines.append("Share Status:")
        for status, count in stats['by_share_status'].items():
            lines.append(f"  {status}: {count}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test the consent functions
    print("Bug Consent Handler Test")
    print("=" * 50)

    # Generate consent questions
    share_q = get_share_consent_question("TypeError in authentication module")
    print("\nShare consent question:")
    print(f"  Header: {share_q.header}")
    print(f"  Question: {share_q.question}")
    for opt in share_q.options:
        print(f"    - {opt['label']}: {opt['description']}")

    first_q = get_first_time_consent_question()
    print(f"\nFirst-time question header: {first_q.header}")

    # Show consent summary
    print("\n" + format_consent_summary())
