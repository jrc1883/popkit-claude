"""Tests for workflow orchestration engine."""
import pytest
import sys
import os
import json
import uuid
import shutil
from pathlib import Path

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def simple_workflow_def():
    """A simple test workflow definition."""
    return {
        "id": "test-simple",
        "name": "Simple Test Workflow",
        "version": 1,
        "description": "A simple test workflow",
        "steps": [
            {
                "id": "start",
                "description": "Start step",
                "type": "skill",
                "skill": "pop-test-start",
                "next": "end"
            },
            {
                "id": "end",
                "description": "End step",
                "type": "terminal"
            }
        ]
    }


@pytest.fixture
def decision_workflow_def():
    """A workflow with user decision branching."""
    return {
        "id": "test-decision",
        "name": "Decision Test Workflow",
        "version": 1,
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
                    {"id": "simple", "label": "Simple", "next": "simple_path"},
                    {"id": "complex", "label": "Complex", "next": "complex_path"}
                ],
                "next_map": {
                    "simple": "simple_path",
                    "complex": "complex_path"
                }
            },
            {
                "id": "simple_path",
                "description": "Simple path",
                "type": "skill",
                "skill": "pop-simple",
                "next": "end"
            },
            {
                "id": "complex_path",
                "description": "Complex path",
                "type": "skill",
                "skill": "pop-complex",
                "next": "end"
            },
            {
                "id": "end",
                "description": "End step",
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
    from workflow_engine import FileWorkflowEngine
    for wid in workflow_ids:
        try:
            engine = FileWorkflowEngine.load_workflow(wid)
            if engine:
                engine.delete()
        except Exception:
            pass


# =============================================================================
# WorkflowDefinition Tests
# =============================================================================

def test_workflow_definition_from_dict(simple_workflow_def):
    """WorkflowDefinition can be created from dict."""
    from workflow_engine import WorkflowDefinition

    definition = WorkflowDefinition.from_dict(simple_workflow_def)

    assert definition.id == "test-simple"
    assert definition.name == "Simple Test Workflow"
    assert definition.version == 1
    assert len(definition.steps) == 2


def test_workflow_definition_get_step(simple_workflow_def):
    """WorkflowDefinition.get_step returns correct step."""
    from workflow_engine import WorkflowDefinition

    definition = WorkflowDefinition.from_dict(simple_workflow_def)

    start_step = definition.get_step("start")
    assert start_step is not None
    assert start_step.id == "start"
    assert start_step.skill == "pop-test-start"

    missing_step = definition.get_step("nonexistent")
    assert missing_step is None


def test_workflow_definition_get_first_step(simple_workflow_def):
    """WorkflowDefinition.get_first_step returns first step."""
    from workflow_engine import WorkflowDefinition

    definition = WorkflowDefinition.from_dict(simple_workflow_def)

    first = definition.get_first_step()
    assert first is not None
    assert first.id == "start"


# =============================================================================
# WorkflowStep Tests
# =============================================================================

def test_workflow_step_from_dict():
    """WorkflowStep can be created from dict."""
    from workflow_engine import WorkflowStep

    data = {
        "id": "test-step",
        "description": "Test step",
        "type": "skill",
        "skill": "pop-test"
    }

    step = WorkflowStep.from_dict(data)

    assert step.id == "test-step"
    assert step.description == "Test step"
    assert step.step_type == "skill"
    assert step.skill == "pop-test"


def test_workflow_step_user_decision():
    """WorkflowStep correctly parses user_decision type."""
    from workflow_engine import WorkflowStep

    data = {
        "id": "decision",
        "description": "Choose",
        "type": "user_decision",
        "question": "Which option?",
        "header": "Options",
        "options": [
            {"id": "a", "label": "Option A"},
            {"id": "b", "label": "Option B"}
        ],
        "next_map": {"a": "step_a", "b": "step_b"}
    }

    step = WorkflowStep.from_dict(data)

    assert step.step_type == "user_decision"
    assert step.question == "Which option?"
    assert step.header == "Options"
    assert len(step.options) == 2
    assert step.next_map["a"] == "step_a"


# =============================================================================
# FileWorkflowEngine Tests
# =============================================================================

def test_create_workflow(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.create_workflow creates a new workflow."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-create-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def,
        initial_context={"test": True}
    )

    assert engine is not None
    assert engine.workflow_id == workflow_id
    assert engine.get_status() == WorkflowStatus.RUNNING.value

    state = engine.get_state()
    assert state.current_step == "start"
    assert state.context == {"test": True}


def test_load_workflow(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.load_workflow loads existing workflow."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-load-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create workflow
    FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def,
        initial_context={"test": True}
    )

    # Load it
    loaded = FileWorkflowEngine.load_workflow(workflow_id)

    assert loaded is not None
    assert loaded.workflow_id == workflow_id
    assert loaded.definition is not None
    assert loaded.definition.id == "test-simple"


def test_get_active_workflow(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.get_active_workflow returns active workflow."""
    from workflow_engine import FileWorkflowEngine, get_active_workflow, clear_active_workflow

    # Clear any existing active workflow
    clear_active_workflow()

    workflow_id = f"test-active-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create workflow (sets as active)
    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    # Get active
    active = get_active_workflow()

    assert active is not None
    assert active.workflow_id == workflow_id


def test_advance_step(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.advance_step advances to next step."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-advance-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    # Start at 'start' step
    current = engine.get_current_step()
    assert current.id == "start"

    # Advance
    next_step = engine.advance_step({"result": "done"})

    assert next_step is not None
    assert next_step.id == "end"


def test_workflow_complete_on_terminal(simple_workflow_def, cleanup_workflows):
    """Workflow completes when reaching terminal step."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-complete-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    # Advance through workflow
    engine.advance_step()  # start -> end
    engine.advance_step()  # terminal -> complete

    assert engine.get_status() == WorkflowStatus.COMPLETE.value


def test_wait_for_event(decision_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.wait_for_event sets waiting status."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-wait-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    # Advance to decision step
    engine.advance_step()

    # Wait for event
    engine.wait_for_event("user-decision")

    assert engine.get_status() == WorkflowStatus.WAITING.value
    assert "user-decision" in engine.get_state().pending_events


def test_notify_event(decision_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.notify_event processes event."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-notify-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    # Advance to decision step and wait
    engine.advance_step()
    engine.wait_for_event("user-decision")

    # Notify event
    result = engine.notify_event("user-decision", {"answer": "Simple"})

    assert result is True
    assert engine.get_status() == WorkflowStatus.RUNNING.value


def test_decision_branching(decision_workflow_def, cleanup_workflows):
    """User decision branches to correct path."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-branch-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def
    )

    # Advance to decision
    engine.advance_step()
    engine.wait_for_event("decision")
    engine.notify_event("decision", {"answer": "Simple"})

    # Advance with decision result
    next_step = engine.advance_step({"answer": "Simple", "option_id": "simple"})

    assert next_step.id == "simple_path"


def test_workflow_context_accumulation(decision_workflow_def, cleanup_workflows):
    """Context accumulates through workflow steps."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-context-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def,
        initial_context={"initial": True}
    )

    # Add context at each step
    engine.advance_step({"context": {"step1": "done"}})

    context = engine.get_context()
    assert context["initial"] is True
    assert context["step1"] == "done"


def test_workflow_delete(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.delete removes all workflow files."""
    from workflow_engine import FileWorkflowEngine, _get_workflow_state_file

    workflow_id = f"test-delete-{uuid.uuid4().hex[:8]}"
    # Don't add to cleanup - we're testing delete

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    # Verify file exists
    state_file = _get_workflow_state_file(workflow_id)
    assert state_file.exists()

    # Delete
    engine.delete()

    # Verify file removed
    assert not state_file.exists()


def test_workflow_error_handling(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.set_error marks workflow as errored."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-error-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    engine.set_error("Something went wrong")

    assert engine.get_status() == WorkflowStatus.ERROR.value
    assert engine.get_state().error_message == "Something went wrong"


def test_workflow_cancel(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.cancel marks workflow as cancelled."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-cancel-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    engine.cancel()

    assert engine.get_status() == WorkflowStatus.CANCELLED.value


def test_workflow_summary(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.get_summary returns workflow summary."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-summary-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    engine = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def,
        github_issue=123
    )

    summary = engine.get_summary()

    assert summary["workflow_id"] == workflow_id
    assert summary["workflow_type"] == "test-simple"
    assert summary["github_issue"] == 123
    assert summary["total_steps"] == 2


def test_list_workflows(simple_workflow_def, cleanup_workflows):
    """FileWorkflowEngine.list_workflows returns all workflows."""
    from workflow_engine import FileWorkflowEngine

    # Create multiple workflows
    for i in range(3):
        workflow_id = f"test-list-{i}-{uuid.uuid4().hex[:8]}"
        cleanup_workflows.append(workflow_id)
        FileWorkflowEngine.create_workflow(
            workflow_id=workflow_id,
            workflow_def=simple_workflow_def
        )

    workflows = FileWorkflowEngine.list_workflows()

    # Should have at least our 3 workflows
    assert len(workflows) >= 3


# =============================================================================
# Cross-Session Persistence Tests
# =============================================================================

def test_workflow_persists_across_loads(decision_workflow_def, cleanup_workflows):
    """Workflow state persists across engine reloads."""
    from workflow_engine import FileWorkflowEngine, WorkflowStatus

    workflow_id = f"test-persist-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create and advance workflow
    engine1 = FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=decision_workflow_def,
        initial_context={"test": True}
    )
    engine1.advance_step({"result": "step1"})
    engine1.wait_for_event("decision")

    # Load workflow fresh
    engine2 = FileWorkflowEngine.load_workflow(workflow_id)

    assert engine2 is not None
    assert engine2.get_status() == WorkflowStatus.WAITING.value
    assert engine2.get_state().current_step == "decision"
    assert engine2.get_context()["test"] is True
    assert "decision" in engine2.get_state().pending_events


def test_definition_persists_across_loads(simple_workflow_def, cleanup_workflows):
    """Workflow definition persists with state."""
    from workflow_engine import FileWorkflowEngine

    workflow_id = f"test-def-persist-{uuid.uuid4().hex[:8]}"
    cleanup_workflows.append(workflow_id)

    # Create workflow
    FileWorkflowEngine.create_workflow(
        workflow_id=workflow_id,
        workflow_def=simple_workflow_def
    )

    # Load fresh and verify definition
    engine = FileWorkflowEngine.load_workflow(workflow_id)

    assert engine.definition is not None
    assert engine.definition.id == "test-simple"
    assert len(engine.definition.steps) == 2
