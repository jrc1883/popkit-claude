"""Tests for workflow parser and YAML frontmatter parsing."""
import pytest
import sys
import os

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))


# =============================================================================
# YAML Frontmatter Parsing Tests
# =============================================================================

def test_parse_simple_frontmatter():
    """Parse simple YAML frontmatter."""
    from workflow_parser import _parse_yaml_frontmatter

    content = """---
name: test-skill
description: A test skill
version: 1
---

# Body content
"""
    frontmatter, body = _parse_yaml_frontmatter(content)

    assert frontmatter["name"] == "test-skill"
    assert frontmatter["description"] == "A test skill"
    assert frontmatter["version"] == 1
    assert "Body content" in body


def test_parse_frontmatter_with_arrays():
    """Parse frontmatter with arrays."""
    from workflow_parser import _parse_yaml_frontmatter

    content = """---
name: test
triggers:
  - trigger1
  - trigger2
inputs:
  - from: any
    field: topic
---
"""
    frontmatter, _ = _parse_yaml_frontmatter(content)

    assert len(frontmatter["triggers"]) == 2
    assert frontmatter["triggers"][0] == "trigger1"
    assert len(frontmatter["inputs"]) == 1
    assert frontmatter["inputs"][0]["from"] == "any"


def test_parse_frontmatter_with_workflow():
    """Parse frontmatter with workflow definition."""
    from workflow_parser import _parse_yaml_frontmatter

    content = """---
name: feature-dev
workflow:
  id: feature-development
  name: Feature Development
  steps:
    - id: start
      type: skill
      skill: pop-start
      next: end
    - id: end
      type: terminal
---
"""
    frontmatter, _ = _parse_yaml_frontmatter(content)

    assert "workflow" in frontmatter
    assert frontmatter["workflow"]["id"] == "feature-development"
    assert len(frontmatter["workflow"]["steps"]) == 2


def test_parse_nested_options():
    """Parse deeply nested workflow options."""
    from workflow_parser import _parse_yaml_frontmatter

    content = """---
name: decision-test
workflow:
  id: decision-workflow
  steps:
    - id: decision
      type: user_decision
      question: Which path?
      header: Path
      options:
        - id: a
          label: Path A
          next: step_a
        - id: b
          label: Path B
          next: step_b
---
"""
    frontmatter, _ = _parse_yaml_frontmatter(content)

    options = frontmatter["workflow"]["steps"][0]["options"]
    assert len(options) == 2
    assert options[0]["id"] == "a"
    assert options[0]["label"] == "Path A"
    assert options[1]["next"] == "step_b"


def test_parse_quoted_strings():
    """Parse quoted strings correctly."""
    from workflow_parser import _parse_yaml_frontmatter

    content = '''---
name: "quoted-skill"
description: 'single quoted'
---
'''
    frontmatter, _ = _parse_yaml_frontmatter(content)

    assert frontmatter["name"] == "quoted-skill"
    assert frontmatter["description"] == "single quoted"


def test_parse_no_frontmatter():
    """Handle content without frontmatter."""
    from workflow_parser import _parse_yaml_frontmatter

    content = """# Just markdown
No frontmatter here.
"""
    frontmatter, body = _parse_yaml_frontmatter(content)

    assert frontmatter == {}
    assert "Just markdown" in body


# =============================================================================
# Workflow Validation Tests
# =============================================================================

def test_validate_valid_workflow():
    """Valid workflow passes validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test-workflow",
        "steps": [
            {"id": "start", "type": "skill", "skill": "pop-start", "next": "end"},
            {"id": "end", "type": "terminal"}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_missing_id():
    """Workflow without id fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "steps": [
            {"id": "start", "type": "skill", "skill": "test"}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("id" in err for err in result.errors)


def test_validate_missing_steps():
    """Workflow without steps fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {"id": "test"}

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("steps" in err for err in result.errors)


def test_validate_duplicate_step_ids():
    """Duplicate step IDs fail validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "skill", "skill": "test"},
            {"id": "step1", "type": "terminal"}  # Duplicate
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("Duplicate" in err for err in result.errors)


def test_validate_invalid_step_type():
    """Invalid step type fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "invalid_type"}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("invalid type" in err for err in result.errors)


def test_validate_skill_step_missing_skill():
    """Skill step without skill field fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "skill"}  # Missing skill
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("'skill' field" in err for err in result.errors)


def test_validate_user_decision_missing_question():
    """User decision without question fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "user_decision", "options": []}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("'question' field" in err for err in result.errors)


def test_validate_invalid_next_reference():
    """Invalid next step reference fails validation."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "skill", "skill": "test", "next": "nonexistent"}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert result.valid is False
    assert any("unknown step" in err for err in result.errors)


def test_validate_warning_no_terminal():
    """Workflow without terminal step gets warning."""
    from workflow_parser import validate_workflow_definition

    workflow = {
        "id": "test",
        "steps": [
            {"id": "step1", "type": "skill", "skill": "test"}
        ]
    }

    result = validate_workflow_definition(workflow)

    assert len(result.warnings) > 0
    assert any("terminal" in warn for warn in result.warnings)


# =============================================================================
# Workflow Registry Tests
# =============================================================================

def test_workflow_registry_loads():
    """WorkflowRegistry can be loaded."""
    from workflow_parser import WorkflowRegistry

    registry = WorkflowRegistry.load(force_scan=True)

    assert registry is not None
    # May have 0 workflows if no skills have workflow definitions


def test_workflow_registry_list():
    """WorkflowRegistry.list_workflows returns entries."""
    from workflow_parser import WorkflowRegistry

    registry = WorkflowRegistry.load()
    workflows = registry.list_workflows()

    # Should be a list (possibly empty)
    assert isinstance(workflows, list)


# =============================================================================
# Convenience Function Tests
# =============================================================================

def test_skill_has_workflow_false():
    """skill_has_workflow returns False for unknown skill."""
    from workflow_parser import skill_has_workflow

    result = skill_has_workflow("nonexistent-skill-xyz")

    assert result is False


def test_list_available_workflows():
    """list_available_workflows returns list."""
    from workflow_parser import list_available_workflows

    result = list_available_workflows()

    assert isinstance(result, list)
