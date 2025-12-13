#!/usr/bin/env python3
"""
Response Router for Workflow Orchestration

Routes AskUserQuestion responses to active workflows, enabling:
- Automatic workflow advancement on user decisions
- Context injection for next skill/agent steps
- Decision audit trail and logging
- Graceful handling of invalid responses

Part of Issue #206: File-Based Workflow Engine
Part of Workflow Orchestration System (Phase 1)

Usage:
    # In post-tool-use.py hook
    from utils.response_router import route_user_response

    def handle_tool_output(tool_name, tool_input, tool_output):
        if tool_name == "AskUserQuestion":
            result = route_user_response(tool_output)
            if result:
                # Include workflow guidance in output
                return result
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import workflow engine
try:
    from .workflow_engine import (
        FileWorkflowEngine,
        WorkflowStep,
        WorkflowStatus,
        StepType,
        get_active_workflow,
        has_active_workflow,
    )
except ImportError:
    from workflow_engine import (
        FileWorkflowEngine,
        WorkflowStep,
        WorkflowStatus,
        StepType,
        get_active_workflow,
        has_active_workflow,
    )


# =============================================================================
# Response Router Result
# =============================================================================

@dataclass
class RouteResult:
    """Result of routing a user response."""
    routed: bool                          # Whether response was routed to workflow
    workflow_id: Optional[str] = None     # Active workflow ID
    current_step: Optional[str] = None    # Current step ID
    next_step: Optional[str] = None       # Next step to execute
    step_type: Optional[str] = None       # Type of next step
    skill: Optional[str] = None           # Skill to invoke (if step_type=skill)
    agent: Optional[str] = None           # Agent to use (if step_type=agent)
    context: Optional[Dict[str, Any]] = None  # Context for next step
    message: Optional[str] = None         # Guidance message for Claude
    error: Optional[str] = None           # Error message if routing failed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result = {"routed": self.routed}
        if self.workflow_id:
            result["workflow_id"] = self.workflow_id
        if self.current_step:
            result["current_step"] = self.current_step
        if self.next_step:
            result["next_step"] = self.next_step
        if self.step_type:
            result["step_type"] = self.step_type
        if self.skill:
            result["skill"] = self.skill
        if self.agent:
            result["agent"] = self.agent
        if self.context:
            result["context"] = self.context
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        return result


# =============================================================================
# Response Routing
# =============================================================================

def route_user_response(
    tool_output: Dict[str, Any],
    question_header: Optional[str] = None
) -> RouteResult:
    """Route an AskUserQuestion response to the active workflow.

    Called when a user responds to an AskUserQuestion tool. If there's an
    active workflow waiting for a user_decision, the response is matched
    to workflow options and the workflow is advanced.

    Args:
        tool_output: Output from AskUserQuestion tool (contains 'answers' dict)
        question_header: Optional header to match (for disambiguation)

    Returns:
        RouteResult with routing outcome
    """
    # Check for active workflow
    workflow = get_active_workflow()
    if not workflow:
        return RouteResult(
            routed=False,
            message="No active workflow"
        )

    # Check workflow is waiting for a decision
    state = workflow.get_state()
    if not state or state.status != WorkflowStatus.WAITING.value:
        return RouteResult(
            routed=False,
            workflow_id=workflow.workflow_id,
            message="Workflow not waiting for input"
        )

    # Get current step
    current_step = workflow.get_current_step()
    if not current_step:
        return RouteResult(
            routed=False,
            workflow_id=workflow.workflow_id,
            error="Workflow has no current step"
        )

    # Verify current step is a user_decision
    if current_step.step_type != StepType.USER_DECISION.value:
        return RouteResult(
            routed=False,
            workflow_id=workflow.workflow_id,
            current_step=current_step.id,
            message=f"Current step is {current_step.step_type}, not user_decision"
        )

    # Extract answers from tool output
    answers = tool_output.get("answers", {})
    if not answers:
        return RouteResult(
            routed=False,
            workflow_id=workflow.workflow_id,
            current_step=current_step.id,
            error="No answers in tool output"
        )

    # Find matching answer
    selected_answer, option_id = _match_answer(
        answers,
        current_step,
        question_header
    )

    if not selected_answer:
        return RouteResult(
            routed=False,
            workflow_id=workflow.workflow_id,
            current_step=current_step.id,
            error=f"No matching answer found for step '{current_step.id}'"
        )

    # Notify workflow of the decision event
    event_id = f"decision-{current_step.id}"
    workflow.notify_event(event_id, {
        "answer": selected_answer,
        "option_id": option_id,
        "timestamp": datetime.now().isoformat()
    })

    # Advance the workflow
    next_step = workflow.advance_step({
        "answer": selected_answer,
        "option_id": option_id,
        "decided_at": datetime.now().isoformat()
    })

    # Build result
    if next_step:
        result = RouteResult(
            routed=True,
            workflow_id=workflow.workflow_id,
            current_step=current_step.id,
            next_step=next_step.id,
            step_type=next_step.step_type,
            context=workflow.get_context(),
            message=_build_guidance_message(next_step, workflow)
        )

        # Add skill/agent info if applicable
        if next_step.step_type == StepType.SKILL.value:
            result.skill = next_step.skill
        elif next_step.step_type == StepType.AGENT.value:
            result.agent = next_step.agent

        return result
    else:
        # Workflow completed
        return RouteResult(
            routed=True,
            workflow_id=workflow.workflow_id,
            current_step=current_step.id,
            step_type="complete",
            context=workflow.get_context(),
            message=f"Workflow '{workflow.workflow_id}' completed successfully"
        )


def _match_answer(
    answers: Dict[str, Any],
    step: WorkflowStep,
    required_header: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Match an answer from AskUserQuestion to workflow options.

    Args:
        answers: Dict of header -> answer from tool output
        step: Current user_decision step
        required_header: Optional specific header to match

    Returns:
        Tuple of (selected_answer, option_id) or (None, None) if no match
    """
    step_header = step.header or "Decision"
    options = step.options or []

    # Try to match by header
    for header, answer in answers.items():
        # Skip if header doesn't match when required
        if required_header and header.lower() != required_header.lower():
            continue

        # Check if header matches step header
        if header.lower() == step_header.lower():
            # Find matching option
            for option in options:
                opt_id = option.get("id", "")
                opt_label = option.get("label", "")

                # Match by label (case-insensitive)
                if opt_label.lower() == str(answer).lower():
                    return str(answer), opt_id

                # Match by ID
                if opt_id.lower() == str(answer).lower():
                    return opt_label or str(answer), opt_id

            # If no exact option match, return the raw answer
            return str(answer), None

    # Try matching without header restriction (fallback)
    if not required_header:
        for header, answer in answers.items():
            for option in options:
                opt_id = option.get("id", "")
                opt_label = option.get("label", "")

                if opt_label.lower() == str(answer).lower():
                    return str(answer), opt_id

    return None, None


def _build_guidance_message(step: WorkflowStep, workflow: FileWorkflowEngine) -> str:
    """Build a guidance message for Claude about the next step.

    Args:
        step: Next workflow step
        workflow: Active workflow

    Returns:
        Guidance message string
    """
    step_type = step.step_type
    state = workflow.get_state()
    completed = len(state.completed_steps) if state else 0
    total = len(workflow.definition.steps) if workflow.definition else 0

    base_msg = f"[Workflow Progress: {completed}/{total}]"

    if step_type == StepType.SKILL.value:
        return f"{base_msg} Next: Invoke skill '{step.skill}' - {step.description}"

    elif step_type == StepType.AGENT.value:
        return f"{base_msg} Next: Use agent '{step.agent}' - {step.description}"

    elif step_type == StepType.USER_DECISION.value:
        return f"{base_msg} Next: Ask user - {step.question}"

    elif step_type == StepType.SPAWN_AGENTS.value:
        agents = [a.get("type", "unknown") for a in (step.agents or [])]
        return f"{base_msg} Next: Spawn parallel agents: {', '.join(agents)}"

    elif step_type == StepType.TERMINAL.value:
        return f"{base_msg} Workflow completing - {step.description}"

    return f"{base_msg} Next step: {step.id} - {step.description}"


# =============================================================================
# Workflow State Queries
# =============================================================================

def get_workflow_status() -> Optional[Dict[str, Any]]:
    """Get the current workflow status for display.

    Returns:
        Dict with workflow status or None if no active workflow
    """
    workflow = get_active_workflow()
    if not workflow:
        return None

    return workflow.get_summary()


def get_pending_decision() -> Optional[Dict[str, Any]]:
    """Get details of pending user decision if any.

    Returns:
        Dict with decision details or None if not waiting
    """
    workflow = get_active_workflow()
    if not workflow:
        return None

    state = workflow.get_state()
    if not state or state.status != WorkflowStatus.WAITING.value:
        return None

    current_step = workflow.get_current_step()
    if not current_step or current_step.step_type != StepType.USER_DECISION.value:
        return None

    return {
        "workflow_id": workflow.workflow_id,
        "step_id": current_step.id,
        "question": current_step.question,
        "header": current_step.header,
        "options": current_step.options,
        "context": workflow.get_context()
    }


# =============================================================================
# Hook Integration Helpers
# =============================================================================

def should_route_response(tool_name: str) -> bool:
    """Check if a tool output should be routed.

    Args:
        tool_name: Name of the tool that was called

    Returns:
        True if response should be checked for routing
    """
    if tool_name != "AskUserQuestion":
        return False

    return has_active_workflow()


def format_hook_output(result: RouteResult) -> Dict[str, Any]:
    """Format a RouteResult for hook output.

    Produces output suitable for post-tool-use.py hook.

    Args:
        result: Routing result

    Returns:
        Dict suitable for hook JSON output
    """
    output = {}

    if result.routed:
        # Include workflow guidance in stderr for Claude
        if result.message:
            output["stderr"] = result.message

        # Include context for next step
        if result.context:
            output["context"] = result.context

        # Indicate next action
        if result.skill:
            output["next_action"] = {
                "type": "skill",
                "skill": result.skill,
                "description": result.message
            }
        elif result.agent:
            output["next_action"] = {
                "type": "agent",
                "agent": result.agent,
                "description": result.message
            }

    elif result.error:
        output["stderr"] = f"[Workflow Warning] {result.error}"

    return output


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import uuid

    # Import workflow engine for testing
    try:
        from workflow_engine import FileWorkflowEngine
    except ImportError:
        from .workflow_engine import FileWorkflowEngine

    print("Testing response_router.py...\n")

    # Create a test workflow with user decision
    test_workflow_def = {
        "id": "test-router-workflow",
        "name": "Test Router Workflow",
        "steps": [
            {
                "id": "start",
                "description": "Start step",
                "type": "skill",
                "skill": "pop-test",
                "next": "decision"
            },
            {
                "id": "decision",
                "description": "Choose approach",
                "type": "user_decision",
                "question": "Which approach should we use?",
                "header": "Approach",
                "options": [
                    {"id": "simple", "label": "Simple", "next": "simple_step"},
                    {"id": "complex", "label": "Complex", "next": "complex_step"}
                ],
                "next_map": {
                    "simple": "simple_step",
                    "complex": "complex_step"
                }
            },
            {
                "id": "simple_step",
                "description": "Simple implementation",
                "type": "skill",
                "skill": "pop-simple",
                "next": "end"
            },
            {
                "id": "complex_step",
                "description": "Complex implementation",
                "type": "skill",
                "skill": "pop-complex",
                "next": "end"
            },
            {
                "id": "end",
                "description": "End",
                "type": "terminal"
            }
        ]
    }

    # Test 1: No active workflow
    print("1. Testing with no active workflow")
    result = route_user_response({"answers": {"Test": "Option A"}})
    assert not result.routed, "Expected no routing without workflow"
    print(f"   Result: routed={result.routed}, message={result.message}")

    # Test 2: Create workflow and advance to decision
    print("\n2. Creating test workflow")
    workflow_id = f"test-router-{uuid.uuid4().hex[:8]}"
    workflow = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=test_workflow_def,
        initial_context={"test": True}
    )
    print(f"   Workflow created: {workflow_id}")

    # Advance past start step to decision
    print("\n3. Advancing to decision step")
    workflow.advance_step({"result": "done"})
    workflow.wait_for_event("decision-decision")
    state = workflow.get_state()
    print(f"   Current step: {state.current_step}")
    print(f"   Status: {state.status}")

    # Test 3: Route response with matching answer
    print("\n4. Testing response routing")
    result = route_user_response({
        "answers": {"Approach": "Simple"}
    })
    print(f"   Result: routed={result.routed}")
    print(f"   Next step: {result.next_step}")
    print(f"   Step type: {result.step_type}")
    print(f"   Skill: {result.skill}")
    assert result.routed, "Expected routing to succeed"
    assert result.next_step == "simple_step", f"Expected simple_step, got {result.next_step}"

    # Test 4: Check workflow advanced
    print("\n5. Verifying workflow advanced")
    state = workflow.get_state()
    print(f"   Current step: {state.current_step}")
    print(f"   Status: {state.status}")
    print(f"   Completed steps: {state.completed_steps}")

    # Test 5: Format for hook output
    print("\n6. Testing hook output formatting")
    hook_output = format_hook_output(result)
    print(f"   Hook output: {json.dumps(hook_output, indent=2)}")

    # Clean up
    print("\n7. Cleaning up")
    workflow.delete()
    print("   Test workflow deleted")

    print("\n[OK] All tests passed!")
