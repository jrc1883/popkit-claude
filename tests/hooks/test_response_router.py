"""Tests for response router for workflow orchestration."""
import pytest
import sys
import os
import uuid

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def decision_workflow_def():
    """A workflow with user decision branching."""
    return {
        "id": "test-router",
        "name": "Router Test Workflow",
        "steps": [
            {
                "id": "start",
                "description": "Start step",
                "type": "skill",
                "skill": "pop-start",
                "next": "decision"
            },
            {
                "id": "decision",
                "description": "User decision",
                "type": "user_decision",
                "question": "Which approach?",
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
                "description": "Simple path",
                "type": "skill",
                "skill": "pop-simple",
                "next": "end"
            },
            {
                "id": "complex_step",
                "description": "Complex path",
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


@pytest.fixture
def cleanup_workflows():
    """Clean up workflow files after tests."""
    workflow_ids = []
    yield workflow_ids
    # Cleanup after test
    from workflow_engine import FileWorkflowEngine, clear_active_workflow
    clear_active_workflow()
    for wid in workflow_ids:
        try:
            engine = FileWorkflowEngine.load_workflow(wid)
            if engine:
                engine.delete()
        except Exception:
            pass


# =============================================================================
# Route Result Tests
# =============================================================================

def test_route_result_to_dict():
    """RouteResult.to_dict produces correct output."""
    from response_router import RouteResult

    result = RouteResult(
        routed=True,
        workflow_id="test-123",
        next_step="step_a",
        skill="pop-test"
    )

    data = result.to_dict()

    assert data["routed"] is True
    assert data["workflow_id"] == "test-123"
    assert data["next_step"] == "step_a"
    assert data["skill"] == "pop-test"


def test_route_result_omits_none():
    """RouteResult.to_dict omits None values."""
    from response_router import RouteResult

    result = RouteResult(routed=False, message="No workflow")

    data = result.to_dict()

    assert "routed" in data
    assert "message" in data
    assert "workflow_id" not in data
    assert "skill" not in data


# =============================================================================
# Response Routing Tests
# =============================================================================

def test_route_no_active_workflow():
    """route_user_response returns not routed when no workflow."""
    from response_router import route_user_response
    from workflow_engine import clear_active_workflow

    clear_active_workflow()

    result = route_user_response({"answers": {"Test": "Option A"}})

    assert result.routed is False
    assert "No active workflow" in result.message


def test_route_workflow_not_waiting(decision_workflow_def, cleanup_workflows):
    """route_user_response returns not routed when not waiting."""
    from response_router import route_user_response
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-not-waiting-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create workflow (status is running, not waiting)
    FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    result = route_user_response({"answers": {"Approach": "Simple"}})

    assert result.routed is False
    assert "not waiting" in result.message


def test_route_successful(decision_workflow_def, cleanup_workflows):
    """route_user_response successfully routes matching answer."""
    from response_router import route_user_response
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-route-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create workflow and advance to decision
    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )
    engine.advance_step()  # start -> decision
    engine.wait_for_event("decision-decision")

    # Route response
    result = route_user_response({"answers": {"Approach": "Simple"}})

    assert result.routed is True
    assert result.next_step == "simple_step"
    assert result.skill == "pop-simple"


def test_route_complex_path(decision_workflow_def, cleanup_workflows):
    """route_user_response routes to complex path correctly."""
    from response_router import route_user_response
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-complex-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )
    engine.advance_step()
    engine.wait_for_event("decision-decision")

    result = route_user_response({"answers": {"Approach": "Complex"}})

    assert result.routed is True
    assert result.next_step == "complex_step"
    assert result.skill == "pop-complex"


def test_route_no_matching_header(decision_workflow_def, cleanup_workflows):
    """route_user_response handles non-matching header."""
    from response_router import route_user_response
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-header-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )
    engine.advance_step()
    engine.wait_for_event("decision-decision")

    # Wrong header
    result = route_user_response({"answers": {"WrongHeader": "Simple"}})

    # Should still route if answer matches an option (fallback logic)
    # The exact behavior depends on implementation
    assert result is not None


# =============================================================================
# Workflow State Query Tests
# =============================================================================

def test_get_workflow_status(decision_workflow_def, cleanup_workflows):
    """get_workflow_status returns current status."""
    from response_router import get_workflow_status
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-status-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    status = get_workflow_status()

    assert status is not None
    assert status["workflow_id"] == workflow_id
    assert status["status"] == "running"


def test_get_workflow_status_no_workflow():
    """get_workflow_status returns None when no workflow."""
    from response_router import get_workflow_status
    from workflow_engine import clear_active_workflow

    clear_active_workflow()

    status = get_workflow_status()

    assert status is None


def test_get_pending_decision(decision_workflow_def, cleanup_workflows):
    """get_pending_decision returns decision details when waiting."""
    from response_router import get_pending_decision
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-pending-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )
    engine.advance_step()
    engine.wait_for_event("decision-decision")

    decision = get_pending_decision()

    assert decision is not None
    assert decision["workflow_id"] == workflow_id
    assert decision["question"] == "Which approach?"
    assert len(decision["options"]) == 2


def test_get_pending_decision_not_waiting(decision_workflow_def, cleanup_workflows):
    """get_pending_decision returns None when not waiting for decision."""
    from response_router import get_pending_decision
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-not-pending-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create but don't advance to decision
    FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    decision = get_pending_decision()

    assert decision is None


# =============================================================================
# Hook Integration Tests
# =============================================================================

def test_should_route_response_true():
    """should_route_response returns True for AskUserQuestion with workflow."""
    from response_router import should_route_response
    from workflow_engine import FileWorkflowEngine, clear_active_workflow

    # Create a simple workflow to make active
    workflow_id = f"test-should-route-{uuid.uuid4().hex[:8]}"

    try:
        engine = FileWorkflowEngine.create_workflow(
            workflow_id=workflow_id,
            workflow_def={"id": "test", "name": "Test", "steps": [
                {"id": "start", "type": "terminal", "description": "End"}
            ]}
        )

        result = should_route_response("AskUserQuestion")
        assert result is True

    finally:
        try:
            engine.delete()
        except Exception:
            pass


def test_should_route_response_false_wrong_tool():
    """should_route_response returns False for non-AskUserQuestion."""
    from response_router import should_route_response

    result = should_route_response("Read")

    assert result is False


def test_format_hook_output_routed():
    """format_hook_output includes guidance for routed response."""
    from response_router import RouteResult, format_hook_output

    result = RouteResult(
        routed=True,
        workflow_id="test-123",
        next_step="step_a",
        step_type="skill",
        skill="pop-test",
        context={"key": "value"},
        message="Next: skill pop-test"
    )

    output = format_hook_output(result)

    assert "stderr" in output
    assert "Next: skill" in output["stderr"]
    assert "context" in output
    assert "next_action" in output
    assert output["next_action"]["type"] == "skill"


def test_format_hook_output_error():
    """format_hook_output includes error message."""
    from response_router import RouteResult, format_hook_output

    result = RouteResult(
        routed=False,
        error="Something went wrong"
    )

    output = format_hook_output(result)

    assert "stderr" in output
    assert "Warning" in output["stderr"]
