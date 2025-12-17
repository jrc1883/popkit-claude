#!/usr/bin/env python3
"""
Tests for Feedback Triggers module

Part of Issue #91 - User Feedback Collection System
"""

import sys
import unittest
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from utils.feedback_triggers import (
    FeedbackTrigger,
    FeedbackTriggerManager,
    TriggerType,
    TriggerPriority,
    create_feedback_prompt,
    create_never_ask_prompt,
    get_trigger_manager,
)


class TestFeedbackTrigger(unittest.TestCase):
    """Tests for FeedbackTrigger dataclass"""

    def test_to_ask_user_question_format(self):
        """Should convert to AskUserQuestion format"""
        trigger = FeedbackTrigger(
            trigger_type=TriggerType.AGENT_COMPLETION,
            priority=TriggerPriority.MEDIUM,
            context_type="agent",
            context_id="code-reviewer",
            agent_name="code-reviewer",
            command_name=None,
            workflow_phase=None,
            question_text="How helpful was the code-reviewer?"
        )

        result = trigger.to_ask_user_question()

        self.assertIn("questions", result)
        self.assertEqual(len(result["questions"]), 1)

        question = result["questions"][0]
        self.assertEqual(question["question"], "How helpful was the code-reviewer?")
        self.assertEqual(question["header"], "Feedback")
        self.assertEqual(len(question["options"]), 4)
        self.assertFalse(question["multiSelect"])

    def test_options_have_correct_labels(self):
        """Should have 0-3 rating options"""
        trigger = FeedbackTrigger(
            trigger_type=TriggerType.AGENT_COMPLETION,
            priority=TriggerPriority.MEDIUM,
            context_type="agent",
            context_id="test",
            agent_name="test",
            command_name=None,
            workflow_phase=None,
            question_text="Test question?"
        )

        result = trigger.to_ask_user_question()
        options = result["questions"][0]["options"]

        labels = [opt["label"] for opt in options]
        self.assertIn("0 - Not at all", labels)
        self.assertIn("1 - Slightly", labels)
        self.assertIn("2 - Moderately", labels)
        self.assertIn("3 - Very", labels)


class TestFeedbackTriggerManager(unittest.TestCase):
    """Tests for FeedbackTriggerManager"""

    def setUp(self):
        self.manager = FeedbackTriggerManager()

    def test_evaluate_significant_agent(self):
        """Should trigger for significant agents"""
        trigger = self.manager.evaluate_agent_completion("code-reviewer")

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.agent_name, "code-reviewer")
        self.assertEqual(trigger.priority, TriggerPriority.MEDIUM)

    def test_evaluate_insignificant_agent(self):
        """Should not trigger for non-significant agents"""
        trigger = self.manager.evaluate_agent_completion("some-random-agent")
        self.assertIsNone(trigger)

    def test_error_recovery_high_priority(self):
        """Should give high priority to error recovery"""
        trigger = self.manager.evaluate_agent_completion(
            "any-agent",
            error_occurred=True
        )

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.priority, TriggerPriority.HIGH)
        self.assertEqual(trigger.trigger_type, TriggerType.ERROR_RECOVERY)

    def test_evaluate_significant_command(self):
        """Should trigger for significant commands"""
        trigger = self.manager.evaluate_command_execution("/popkit:dev")

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.command_name, "/popkit:dev")

    def test_evaluate_insignificant_command(self):
        """Should not trigger for non-significant commands"""
        trigger = self.manager.evaluate_command_execution("/help")
        self.assertIsNone(trigger)

    def test_failed_command_high_priority(self):
        """Should give high priority to failed commands"""
        trigger = self.manager.evaluate_command_execution(
            "/popkit:dev",  # Use a significant command
            success=False
        )

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.priority, TriggerPriority.HIGH)

    def test_evaluate_significant_workflow_phase(self):
        """Should trigger for significant workflow phases"""
        trigger = self.manager.evaluate_workflow_phase("implementation")

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.workflow_phase, "implementation")

    def test_evaluate_insignificant_workflow_phase(self):
        """Should not trigger for discovery phase"""
        trigger = self.manager.evaluate_workflow_phase("discovery")
        self.assertIsNone(trigger)

    def test_evaluate_session_end_substantial(self):
        """Should trigger for substantial sessions"""
        trigger = self.manager.evaluate_session_end(
            session_duration_minutes=10,
            tool_call_count=25,
            feedback_count=0
        )

        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.trigger_type, TriggerType.SESSION_END)

    def test_evaluate_session_end_short(self):
        """Should not trigger for short sessions"""
        trigger = self.manager.evaluate_session_end(
            session_duration_minutes=2,
            tool_call_count=5,
            feedback_count=0
        )

        self.assertIsNone(trigger)

    def test_evaluate_session_end_feedback_fatigue(self):
        """Should not trigger if already gave lots of feedback"""
        trigger = self.manager.evaluate_session_end(
            session_duration_minutes=30,
            tool_call_count=100,
            feedback_count=5
        )

        self.assertIsNone(trigger)


class TestShouldShowFeedback(unittest.TestCase):
    """Tests for should_show_feedback decision"""

    def setUp(self):
        self.manager = FeedbackTriggerManager()
        self.trigger = FeedbackTrigger(
            trigger_type=TriggerType.AGENT_COMPLETION,
            priority=TriggerPriority.MEDIUM,
            context_type="agent",
            context_id="test",
            agent_name="test",
            command_name=None,
            workflow_phase=None,
            question_text="Test?"
        )

    def test_should_show_when_threshold_met(self):
        """Should show when tool call threshold is met"""
        should_show, reason = self.manager.should_show_feedback(
            self.trigger,
            tool_calls_since_last=15,
            dismissed_count=0
        )

        self.assertTrue(should_show)

    def test_should_not_show_below_threshold(self):
        """Should not show below tool call threshold"""
        should_show, reason = self.manager.should_show_feedback(
            self.trigger,
            tool_calls_since_last=5,
            dismissed_count=0
        )

        self.assertFalse(should_show)
        self.assertIn("tool calls", reason.lower())

    def test_should_not_show_after_dismissals(self):
        """Should stop showing after max dismissals"""
        should_show, reason = self.manager.should_show_feedback(
            self.trigger,
            tool_calls_since_last=15,
            dismissed_count=3
        )

        self.assertFalse(should_show)
        self.assertIn("dismissed", reason.lower())

    def test_never_ask_session_respected(self):
        """Should respect never_ask_session flag"""
        should_show, reason = self.manager.should_show_feedback(
            self.trigger,
            tool_calls_since_last=15,
            dismissed_count=0,
            never_ask_session=True
        )

        self.assertFalse(should_show)
        self.assertIn("opted out", reason.lower())

    def test_high_priority_always_shows(self):
        """High priority triggers should always show"""
        high_priority_trigger = FeedbackTrigger(
            trigger_type=TriggerType.ERROR_RECOVERY,
            priority=TriggerPriority.HIGH,
            context_type="agent",
            context_id="test",
            agent_name="test",
            command_name=None,
            workflow_phase=None,
            question_text="Did this help?"
        )

        should_show, reason = self.manager.should_show_feedback(
            high_priority_trigger,
            tool_calls_since_last=2,  # Below threshold
            dismissed_count=0
        )

        self.assertTrue(should_show)
        self.assertIn("high priority", reason.lower())


class TestResponseParsing(unittest.TestCase):
    """Tests for parsing feedback responses"""

    def setUp(self):
        self.manager = FeedbackTriggerManager()

    def test_parse_numeric_response(self):
        """Should parse numeric responses"""
        rating, comment = self.manager.parse_feedback_response("0 - Not at all")
        self.assertEqual(rating, 0)
        self.assertIsNone(comment)

        rating, comment = self.manager.parse_feedback_response("3 - Very")
        self.assertEqual(rating, 3)
        self.assertIsNone(comment)

    def test_parse_keyword_response(self):
        """Should parse keyword responses"""
        rating, comment = self.manager.parse_feedback_response("very helpful")
        self.assertEqual(rating, 3)

        rating, comment = self.manager.parse_feedback_response("not at all helpful")
        self.assertEqual(rating, 0)

    def test_parse_other_response(self):
        """Should handle 'Other' responses as comments"""
        rating, comment = self.manager.parse_feedback_response(
            "Other: The response was partially helpful"
        )

        self.assertIsNone(rating)
        self.assertIsNotNone(comment)
        self.assertIn("partially helpful", comment)

    def test_parse_empty_response(self):
        """Should handle empty response"""
        rating, comment = self.manager.parse_feedback_response("")
        self.assertIsNone(rating)
        self.assertIsNone(comment)

    def test_parse_unparseable_as_comment(self):
        """Should return unparseable text as comment"""
        rating, comment = self.manager.parse_feedback_response(
            "I have mixed feelings"
        )

        self.assertIsNone(rating)
        self.assertEqual(comment, "I have mixed feelings")


class TestPromptCreation(unittest.TestCase):
    """Tests for prompt creation utilities"""

    def test_create_feedback_prompt(self):
        """Should create valid feedback prompt"""
        prompt = create_feedback_prompt("How was this response?")

        self.assertIn("questions", prompt)
        question = prompt["questions"][0]
        self.assertEqual(question["question"], "How was this response?")
        self.assertEqual(len(question["options"]), 4)

    def test_create_feedback_prompt_with_skip(self):
        """Should include skip option when requested"""
        prompt = create_feedback_prompt(
            "How was this?",
            include_comment_option=True
        )

        options = prompt["questions"][0]["options"]
        labels = [opt["label"] for opt in options]
        self.assertIn("Skip", labels)

    def test_create_never_ask_prompt(self):
        """Should create never ask prompt"""
        prompt = create_never_ask_prompt()

        self.assertIn("questions", prompt)
        question = prompt["questions"][0]
        self.assertIn("pause", question["question"].lower())

        options = question["options"]
        labels = [opt["label"] for opt in options]
        self.assertIn("Keep asking", labels)
        self.assertIn("Pause for now", labels)
        self.assertIn("Disable", labels)


class TestSingleton(unittest.TestCase):
    """Tests for singleton pattern"""

    def test_get_trigger_manager_returns_same_instance(self):
        """Should return same instance"""
        manager1 = get_trigger_manager()
        manager2 = get_trigger_manager()

        self.assertIs(manager1, manager2)


if __name__ == "__main__":
    unittest.main()
