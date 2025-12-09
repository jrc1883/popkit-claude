#!/usr/bin/env python3
"""
Feedback Triggers - Logic for When to Request Feedback

Part of Issue #91 (User Feedback Collection System)
Parent: Epic #88 (Self-Improvement & Learning System)

Determines when and how to request user feedback without causing
feedback fatigue. Integrates with AskUserQuestion for consistent UX.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class TriggerType(Enum):
    """Types of feedback triggers"""
    AGENT_COMPLETION = "agent_completion"
    WORKFLOW_PHASE = "workflow_phase"
    COMMAND_EXECUTION = "command_execution"
    SESSION_END = "session_end"
    ERROR_RECOVERY = "error_recovery"


class TriggerPriority(Enum):
    """Priority levels for feedback triggers"""
    HIGH = 3      # Always ask (e.g., after error recovery)
    MEDIUM = 2    # Ask if threshold met (e.g., agent completion)
    LOW = 1       # Ask only if long time since last (e.g., command)
    SKIP = 0      # Don't ask


@dataclass
class FeedbackTrigger:
    """Represents a feedback trigger opportunity"""
    trigger_type: TriggerType
    priority: TriggerPriority
    context_type: str
    context_id: Optional[str]
    agent_name: Optional[str]
    command_name: Optional[str]
    workflow_phase: Optional[str]
    question_text: str

    def to_ask_user_question(self) -> Dict[str, Any]:
        """
        Convert to AskUserQuestion format for consistent UX.

        Returns a dict that can be used with Claude's AskUserQuestion tool.
        """
        return {
            "questions": [{
                "question": self.question_text,
                "header": "Feedback",
                "options": [
                    {
                        "label": "0 - Not at all",
                        "description": "Wrong or harmful response"
                    },
                    {
                        "label": "1 - Slightly",
                        "description": "Mostly unhelpful"
                    },
                    {
                        "label": "2 - Moderately",
                        "description": "Somewhat useful"
                    },
                    {
                        "label": "3 - Very",
                        "description": "Exactly what I needed"
                    }
                ],
                "multiSelect": False
            }]
        }


class FeedbackTriggerManager:
    """
    Manages feedback trigger logic and decision making.

    Determines when to show feedback prompts based on:
    - Trigger type and priority
    - Time since last feedback
    - Number of dismissed prompts
    - Session state
    """

    # Significant agents that warrant feedback
    SIGNIFICANT_AGENTS = {
        "code-reviewer",
        "bug-whisperer",
        "security-auditor",
        "code-architect",
        "test-writer-fixer",
        "api-designer",
        "performance-optimizer",
        "power-coordinator"
    }

    # Significant commands that warrant feedback
    SIGNIFICANT_COMMANDS = {
        "/popkit:dev",
        "/popkit:git pr",
        "/popkit:git commit",
        "/popkit:debug",
        "/popkit:routine morning",
        "/popkit:routine nightly"
    }

    # Workflow phases that warrant feedback
    SIGNIFICANT_PHASES = {
        "brainstorming",
        "architecture",
        "implementation",
        "review",
        "summary"
    }

    def __init__(self):
        """Initialize the trigger manager"""
        pass

    def evaluate_agent_completion(
        self,
        agent_name: str,
        tool_output: Optional[str] = None,
        error_occurred: bool = False
    ) -> Optional[FeedbackTrigger]:
        """
        Evaluate whether to trigger feedback after agent completion.

        Args:
            agent_name: Name of the completed agent
            tool_output: Output from the agent (for significance detection)
            error_occurred: Whether an error occurred during execution

        Returns:
            FeedbackTrigger if feedback should be requested, None otherwise
        """
        # Always ask after error recovery
        if error_occurred:
            return FeedbackTrigger(
                trigger_type=TriggerType.ERROR_RECOVERY,
                priority=TriggerPriority.HIGH,
                context_type="agent",
                context_id=agent_name,
                agent_name=agent_name,
                command_name=None,
                workflow_phase=None,
                question_text=f"Did the {agent_name} help resolve the error?"
            )

        # Only ask for significant agents
        if agent_name not in self.SIGNIFICANT_AGENTS:
            return None

        return FeedbackTrigger(
            trigger_type=TriggerType.AGENT_COMPLETION,
            priority=TriggerPriority.MEDIUM,
            context_type="agent",
            context_id=agent_name,
            agent_name=agent_name,
            command_name=None,
            workflow_phase=None,
            question_text=f"How helpful was the {agent_name}?"
        )

    def evaluate_command_execution(
        self,
        command_name: str,
        success: bool = True,
        output_size: int = 0
    ) -> Optional[FeedbackTrigger]:
        """
        Evaluate whether to trigger feedback after command execution.

        Args:
            command_name: Name of the executed command
            success: Whether the command succeeded
            output_size: Size of command output (indicator of significance)

        Returns:
            FeedbackTrigger if feedback should be requested, None otherwise
        """
        # Normalize command name
        normalized = command_name.split()[0] if ' ' in command_name else command_name

        # Check if significant command
        is_significant = any(
            normalized.startswith(sig) for sig in self.SIGNIFICANT_COMMANDS
        )

        if not is_significant:
            return None

        # Higher priority for failures
        priority = TriggerPriority.HIGH if not success else TriggerPriority.LOW

        return FeedbackTrigger(
            trigger_type=TriggerType.COMMAND_EXECUTION,
            priority=priority,
            context_type="command",
            context_id=normalized,
            agent_name=None,
            command_name=command_name,
            workflow_phase=None,
            question_text=f"Was {normalized} useful?" if success else f"Did {normalized} work as expected?"
        )

    def evaluate_workflow_phase(
        self,
        phase_name: str,
        workflow_name: Optional[str] = None,
        phase_output: Optional[str] = None
    ) -> Optional[FeedbackTrigger]:
        """
        Evaluate whether to trigger feedback after a workflow phase.

        Args:
            phase_name: Name of the completed phase
            workflow_name: Name of the parent workflow
            phase_output: Output from the phase

        Returns:
            FeedbackTrigger if feedback should be requested, None otherwise
        """
        # Only significant phases
        if phase_name.lower() not in self.SIGNIFICANT_PHASES:
            return None

        return FeedbackTrigger(
            trigger_type=TriggerType.WORKFLOW_PHASE,
            priority=TriggerPriority.MEDIUM,
            context_type="workflow",
            context_id=phase_name,
            agent_name=None,
            command_name=None,
            workflow_phase=phase_name,
            question_text=f"Did the {phase_name} phase help?"
        )

    def evaluate_session_end(
        self,
        session_duration_minutes: int,
        tool_call_count: int,
        feedback_count: int
    ) -> Optional[FeedbackTrigger]:
        """
        Evaluate whether to request session-end feedback.

        Args:
            session_duration_minutes: How long the session lasted
            tool_call_count: Total tool calls in session
            feedback_count: How many feedback prompts already shown

        Returns:
            FeedbackTrigger if feedback should be requested, None otherwise
        """
        # Only ask for substantial sessions
        if session_duration_minutes < 5 or tool_call_count < 10:
            return None

        # Don't ask if already gave a lot of feedback
        if feedback_count >= 3:
            return None

        return FeedbackTrigger(
            trigger_type=TriggerType.SESSION_END,
            priority=TriggerPriority.LOW,
            context_type="session",
            context_id="overall",
            agent_name=None,
            command_name=None,
            workflow_phase=None,
            question_text="Overall, how helpful was this session?"
        )

    def should_show_feedback(
        self,
        trigger: FeedbackTrigger,
        tool_calls_since_last: int,
        dismissed_count: int,
        never_ask_session: bool = False,
        min_tool_calls: int = 10
    ) -> Tuple[bool, str]:
        """
        Final decision on whether to show feedback prompt.

        Args:
            trigger: The feedback trigger to evaluate
            tool_calls_since_last: Tool calls since last feedback
            dismissed_count: How many times user dismissed feedback
            never_ask_session: Whether user said "don't ask this session"
            min_tool_calls: Minimum tool calls between feedback requests

        Returns:
            Tuple of (should_show, reason)
        """
        # Check "never ask" flag
        if never_ask_session:
            return False, "User opted out of feedback this session"

        # High priority triggers always show (unless opted out)
        if trigger.priority == TriggerPriority.HIGH:
            return True, "High priority trigger (error recovery)"

        # Check dismissed count
        if dismissed_count >= 3:
            return False, f"User dismissed {dismissed_count} times, pausing feedback"

        # Check tool call threshold for medium/low priority
        if tool_calls_since_last < min_tool_calls:
            return False, f"Only {tool_calls_since_last} tool calls since last feedback (min: {min_tool_calls})"

        return True, "Threshold met"

    def parse_feedback_response(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Parse user's feedback response.

        Args:
            response: User's response string (e.g., "0 - Not at all")

        Returns:
            Tuple of (rating, optional_comment) or (None, None) if not parseable
        """
        if not response:
            return None, None

        # Handle "Other" responses as comments
        if response.lower().startswith("other"):
            parts = response.split(":", 1)
            comment = parts[1].strip() if len(parts) > 1 else response
            return None, comment

        # Parse rating from option label
        try:
            # Extract number from beginning (e.g., "0 - Not at all" -> 0)
            rating_str = response.split("-")[0].strip()
            rating = int(rating_str)
            if 0 <= rating <= 3:
                return rating, None
        except (ValueError, IndexError):
            pass

        # Try to match keywords
        response_lower = response.lower()
        if "not at all" in response_lower or "harmful" in response_lower:
            return 0, None
        elif "slightly" in response_lower or "unhelpful" in response_lower:
            return 1, None
        elif "moderately" in response_lower or "somewhat" in response_lower:
            return 2, None
        elif "very" in response_lower or "exactly" in response_lower:
            return 3, None

        return None, response  # Return as comment if can't parse


def create_feedback_prompt(
    question: str,
    include_comment_option: bool = False
) -> Dict[str, Any]:
    """
    Create a standard feedback prompt for AskUserQuestion.

    Args:
        question: The feedback question to ask
        include_comment_option: Whether to add explicit comment option

    Returns:
        Dict formatted for AskUserQuestion tool
    """
    options = [
        {"label": "0 - Not at all", "description": "Wrong or harmful response"},
        {"label": "1 - Slightly", "description": "Mostly unhelpful"},
        {"label": "2 - Moderately", "description": "Somewhat useful"},
        {"label": "3 - Very", "description": "Exactly what I needed"}
    ]

    if include_comment_option:
        options.append({
            "label": "Skip",
            "description": "Don't provide feedback right now"
        })

    return {
        "questions": [{
            "question": question,
            "header": "Feedback",
            "options": options,
            "multiSelect": False
        }]
    }


def create_never_ask_prompt() -> Dict[str, Any]:
    """
    Create prompt asking if user wants to disable feedback for session.

    Returns:
        Dict formatted for AskUserQuestion tool
    """
    return {
        "questions": [{
            "question": "Would you like to pause feedback prompts?",
            "header": "Feedback",
            "options": [
                {"label": "Keep asking", "description": "Continue showing feedback prompts"},
                {"label": "Pause for now", "description": "Don't ask again this session"},
                {"label": "Disable", "description": "Turn off feedback collection"}
            ],
            "multiSelect": False
        }]
    }


# Singleton instance
_manager: Optional[FeedbackTriggerManager] = None


def get_trigger_manager() -> FeedbackTriggerManager:
    """Get the singleton FeedbackTriggerManager instance"""
    global _manager
    if _manager is None:
        _manager = FeedbackTriggerManager()
    return _manager


if __name__ == "__main__":
    # Test the trigger manager
    manager = FeedbackTriggerManager()

    # Test agent completion trigger
    trigger = manager.evaluate_agent_completion("code-reviewer")
    if trigger:
        print(f"Agent trigger: {trigger.question_text}")
        print(f"AskUserQuestion format: {json.dumps(trigger.to_ask_user_question(), indent=2)}")

    # Test command trigger
    trigger = manager.evaluate_command_execution("/popkit:git commit", success=True)
    if trigger:
        print(f"\nCommand trigger: {trigger.question_text}")

    # Test should_show decision
    trigger = manager.evaluate_agent_completion("code-reviewer")
    if trigger:
        should_show, reason = manager.should_show_feedback(
            trigger,
            tool_calls_since_last=15,
            dismissed_count=0
        )
        print(f"\nShould show: {should_show} - {reason}")

    # Test response parsing
    test_responses = [
        "0 - Not at all",
        "3 - Very",
        "Other: The response was partially helpful but missed some context",
        "very helpful"
    ]

    print("\nResponse parsing:")
    for resp in test_responses:
        rating, comment = manager.parse_feedback_response(resp)
        print(f"  '{resp}' -> rating={rating}, comment={comment}")
