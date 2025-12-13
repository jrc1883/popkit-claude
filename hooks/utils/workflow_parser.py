#!/usr/bin/env python3
"""
Workflow Parser for PopKit Skills

Parses workflow definitions from skill YAML frontmatter, enabling:
- Multi-step workflow extraction from SKILL.md files
- Workflow definition validation
- Registry of available workflows
- Lookup by skill name or workflow ID

Part of Issue #206: File-Based Workflow Engine
Part of Workflow Orchestration System (Phase 2)

Usage:
    # Parse a single skill file
    workflow_def = parse_skill_workflow("packages/plugin/skills/pop-feature-dev/SKILL.md")

    # Load all workflows
    registry = WorkflowRegistry.load()

    # Get workflow by skill name
    workflow = registry.get_by_skill("pop-feature-dev")

    # Get workflow by ID
    workflow = registry.get_by_id("feature-development")
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import workflow classes
try:
    from .workflow_engine import WorkflowDefinition, WorkflowStep
except ImportError:
    from workflow_engine import WorkflowDefinition, WorkflowStep


# =============================================================================
# YAML Parser (Minimal - no external dependency)
# =============================================================================

def _parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown file.

    Uses a minimal parser to avoid yaml module dependency.
    Supports the subset of YAML used in PopKit skills.

    Args:
        content: Full file content

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    # Check for frontmatter
    if not content.startswith('---'):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    # Parse YAML (minimal subset)
    return _parse_yaml_dict(frontmatter_str), body


def _parse_yaml_dict(yaml_str: str, indent: int = 0) -> Dict[str, Any]:
    """Parse a YAML string into a dictionary.

    Supports:
    - Simple key: value pairs
    - Nested dictionaries (indentation-based)
    - Arrays with - prefix
    - Quoted strings
    - Multiline strings with > or |
    """
    result = {}
    lines = yaml_str.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            i += 1
            continue

        # Calculate indentation
        line_indent = len(line) - len(line.lstrip())

        # If less indented than expected, we're done with this block
        if line_indent < indent and indent > 0:
            break

        # Skip lines that don't match our indent level
        if line_indent != indent:
            i += 1
            continue

        stripped = line.strip()

        # Parse key: value
        if ':' in stripped:
            key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', stripped)
            if key_match:
                key = key_match.group(1)
                value_str = key_match.group(2).strip()

                if value_str == '':
                    # Could be a nested dict or array
                    # Look ahead to see what follows
                    j = i + 1
                    while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                        j += 1

                    if j < len(lines):
                        next_line = lines[j]
                        next_indent = len(next_line) - len(next_line.lstrip())

                        if next_indent > indent:
                            if next_line.strip().startswith('-'):
                                # Parse array
                                value, consumed = _parse_yaml_array('\n'.join(lines[j:]), next_indent)
                                result[key] = value
                                i = j + consumed
                                continue
                            else:
                                # Parse nested dict
                                nested_str = '\n'.join(lines[j:])
                                value = _parse_yaml_dict(nested_str, next_indent)
                                # Count consumed lines
                                consumed = 0
                                for k in range(j, len(lines)):
                                    if lines[k].strip() and not lines[k].strip().startswith('#'):
                                        k_indent = len(lines[k]) - len(lines[k].lstrip())
                                        if k_indent < next_indent:
                                            break
                                    consumed += 1
                                result[key] = value
                                i = j + consumed
                                continue
                    result[key] = None
                elif value_str.startswith('"') and value_str.endswith('"'):
                    result[key] = value_str[1:-1]
                elif value_str.startswith("'") and value_str.endswith("'"):
                    result[key] = value_str[1:-1]
                elif value_str.lower() == 'true':
                    result[key] = True
                elif value_str.lower() == 'false':
                    result[key] = False
                elif value_str.lower() == 'null' or value_str.lower() == '~':
                    result[key] = None
                elif re.match(r'^-?\d+$', value_str):
                    result[key] = int(value_str)
                elif re.match(r'^-?\d+\.\d+$', value_str):
                    result[key] = float(value_str)
                elif value_str.startswith('[') and value_str.endswith(']'):
                    # Inline array
                    result[key] = _parse_inline_array(value_str)
                elif value_str.startswith('{') and value_str.endswith('}'):
                    # Inline dict
                    result[key] = _parse_inline_dict(value_str)
                elif value_str in ('>', '|'):
                    # Multiline string - collect following indented lines
                    multiline = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        if next_line.strip() and not next_line.startswith(' ' * (indent + 2)):
                            break
                        if next_line.strip():
                            multiline.append(next_line.strip())
                        j += 1
                    result[key] = ' '.join(multiline) if value_str == '>' else '\n'.join(multiline)
                    i = j
                    continue
                else:
                    result[key] = value_str

        i += 1

    return result


def _parse_yaml_array(yaml_str: str, indent: int) -> Tuple[List[Any], int]:
    """Parse a YAML array starting at the given indentation."""
    result = []
    lines = yaml_str.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            i += 1
            continue

        line_indent = len(line) - len(line.lstrip())

        # Done if less indented
        if line_indent < indent:
            break

        # Skip non-matching indent
        if line_indent != indent:
            i += 1
            continue

        stripped = line.strip()

        if stripped.startswith('- '):
            item_str = stripped[2:].strip()

            if ':' in item_str:
                # Object item - check if more lines follow
                item_dict = {}
                key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', item_str)
                if key_match:
                    key = key_match.group(1)
                    value = key_match.group(2).strip()
                    if value:
                        item_dict[key] = _parse_yaml_value(value)
                    else:
                        item_dict[key] = None

                # Look for additional keys at item level
                j = i + 1
                item_indent = indent + 2
                while j < len(lines):
                    next_line = lines[j]
                    if not next_line.strip() or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent < item_indent:
                        break
                    if next_indent == item_indent:
                        key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', next_line.strip())
                        if key_match:
                            nested_key = key_match.group(1)
                            nested_value = key_match.group(2).strip()
                            if nested_value:
                                item_dict[nested_key] = _parse_yaml_value(nested_value)
                            else:
                                # Check for nested array or dict
                                k = j + 1
                                while k < len(lines) and (not lines[k].strip() or lines[k].strip().startswith('#')):
                                    k += 1
                                if k < len(lines):
                                    look_ahead = lines[k]
                                    look_indent = len(look_ahead) - len(look_ahead.lstrip())
                                    if look_indent > item_indent and look_ahead.strip().startswith('-'):
                                        # Nested array
                                        nested_arr, consumed = _parse_yaml_array('\n'.join(lines[k:]), look_indent)
                                        item_dict[nested_key] = nested_arr
                                        j = k + consumed - 1
                                    else:
                                        item_dict[nested_key] = None
                                else:
                                    item_dict[nested_key] = None
                    j += 1

                result.append(item_dict)
                i = j
                continue
            else:
                # Simple item
                result.append(_parse_yaml_value(item_str))
        elif stripped.startswith('-'):
            # Just a dash with value on next line or nested structure
            # Check if there's content after the dash
            after_dash = stripped[1:].strip()
            if after_dash:
                if ':' in after_dash:
                    # Parse as dict
                    item_dict = {}
                    key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', after_dash)
                    if key_match:
                        item_dict[key_match.group(1)] = _parse_yaml_value(key_match.group(2).strip())
                    result.append(item_dict)
                else:
                    result.append(_parse_yaml_value(after_dash))
            else:
                result.append(None)

        i += 1

    return result, i


def _parse_yaml_value(value_str: str) -> Any:
    """Parse a YAML value string."""
    if not value_str:
        return None
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str.startswith("'") and value_str.endswith("'"):
        return value_str[1:-1]
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    if value_str.lower() == 'null' or value_str == '~':
        return None
    if re.match(r'^-?\d+$', value_str):
        return int(value_str)
    if re.match(r'^-?\d+\.\d+$', value_str):
        return float(value_str)
    if value_str.startswith('[') and value_str.endswith(']'):
        return _parse_inline_array(value_str)
    return value_str


def _parse_inline_array(value_str: str) -> List[Any]:
    """Parse an inline YAML array like [a, b, c]."""
    inner = value_str[1:-1].strip()
    if not inner:
        return []

    # Simple split - doesn't handle nested structures
    items = []
    for item in inner.split(','):
        items.append(_parse_yaml_value(item.strip()))
    return items


def _parse_inline_dict(value_str: str) -> Dict[str, Any]:
    """Parse an inline YAML dict like {a: 1, b: 2}."""
    inner = value_str[1:-1].strip()
    if not inner:
        return {}

    result = {}
    for pair in inner.split(','):
        if ':' in pair:
            key, value = pair.split(':', 1)
            result[key.strip()] = _parse_yaml_value(value.strip())
    return result


# =============================================================================
# Workflow Validation
# =============================================================================

@dataclass
class ValidationResult:
    """Result of workflow validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_workflow_definition(workflow_data: Dict[str, Any]) -> ValidationResult:
    """Validate a workflow definition.

    Checks:
    - Required fields present
    - Valid step types
    - Step IDs are unique
    - Next step references exist
    - User decision options have required fields

    Args:
        workflow_data: Workflow definition dict from frontmatter

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(valid=True)

    # Check required fields
    if not workflow_data.get("id"):
        result.add_error("Workflow missing required 'id' field")

    if not workflow_data.get("steps"):
        result.add_error("Workflow missing required 'steps' field")
        return result

    steps = workflow_data.get("steps", [])
    if not isinstance(steps, list):
        result.add_error("Workflow 'steps' must be an array")
        return result

    if len(steps) == 0:
        result.add_error("Workflow must have at least one step")
        return result

    # Collect step IDs
    step_ids = set()
    valid_types = {"skill", "agent", "user_decision", "spawn_agents", "terminal"}

    for i, step in enumerate(steps):
        # Check step ID
        step_id = step.get("id")
        if not step_id:
            result.add_error(f"Step {i} missing required 'id' field")
            continue

        if step_id in step_ids:
            result.add_error(f"Duplicate step ID: {step_id}")
        step_ids.add(step_id)

        # Check step type
        step_type = step.get("type")
        if not step_type:
            result.add_error(f"Step '{step_id}' missing required 'type' field")
        elif step_type not in valid_types:
            result.add_error(f"Step '{step_id}' has invalid type: {step_type}")

        # Check type-specific requirements
        if step_type == "skill" and not step.get("skill"):
            result.add_error(f"Skill step '{step_id}' missing 'skill' field")

        if step_type == "agent" and not step.get("agent"):
            result.add_error(f"Agent step '{step_id}' missing 'agent' field")

        if step_type == "user_decision":
            if not step.get("question"):
                result.add_error(f"User decision step '{step_id}' missing 'question' field")

            options = step.get("options", [])
            if not options:
                result.add_error(f"User decision step '{step_id}' missing 'options' field")
            else:
                for j, opt in enumerate(options):
                    if not opt.get("id") and not opt.get("label"):
                        result.add_error(f"Option {j} in step '{step_id}' missing 'id' or 'label'")

        if step_type == "spawn_agents":
            if not step.get("agents"):
                result.add_error(f"Spawn agents step '{step_id}' missing 'agents' field")

    # Validate next step references
    for step in steps:
        step_id = step.get("id")

        # Check default next
        next_id = step.get("next")
        if next_id and next_id not in step_ids:
            result.add_error(f"Step '{step_id}' references unknown step: {next_id}")

        # Check next_map references
        next_map = step.get("next_map", {})
        for key, target_id in next_map.items():
            if target_id not in step_ids:
                result.add_error(f"Step '{step_id}' next_map[{key}] references unknown step: {target_id}")

        # Check option next references
        options = step.get("options") or []
        for opt in options:
            if opt:
                opt_next = opt.get("next")
                if opt_next and opt_next not in step_ids:
                    result.add_error(f"Step '{step_id}' option next references unknown step: {opt_next}")

    # Check for terminal step
    has_terminal = any(s.get("type") == "terminal" for s in steps)
    if not has_terminal:
        result.add_warning("Workflow has no terminal step - ensure all paths end properly")

    return result


# =============================================================================
# Skill File Parser
# =============================================================================

def parse_skill_workflow(skill_path: Path) -> Optional[Dict[str, Any]]:
    """Parse workflow definition from a skill file.

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        Workflow definition dict if present, None otherwise
    """
    if not skill_path.exists():
        return None

    try:
        content = skill_path.read_text(encoding='utf-8')
    except Exception:
        return None

    frontmatter, _ = _parse_yaml_frontmatter(content)

    if "workflow" not in frontmatter:
        return None

    workflow = frontmatter["workflow"]

    # Add skill name if not in workflow
    if "skill_name" not in workflow:
        workflow["skill_name"] = frontmatter.get("name", skill_path.parent.name)

    return workflow


def parse_skill_file(skill_path: Path) -> Dict[str, Any]:
    """Parse a skill file and return all frontmatter.

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        Dict with all frontmatter fields
    """
    if not skill_path.exists():
        return {}

    try:
        content = skill_path.read_text(encoding='utf-8')
    except Exception:
        return {}

    frontmatter, _ = _parse_yaml_frontmatter(content)
    return frontmatter


# =============================================================================
# Workflow Registry
# =============================================================================

@dataclass
class WorkflowRegistryEntry:
    """Entry in the workflow registry."""
    skill_name: str
    skill_path: str
    workflow_id: str
    workflow_name: str
    description: str
    version: int
    step_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "skill_path": self.skill_path,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "description": self.description,
            "version": self.version,
            "step_count": self.step_count
        }


class WorkflowRegistry:
    """Registry of available workflows from skills.

    Scans skill directories and caches workflow definitions.
    Provides lookup by skill name or workflow ID.
    """

    _instance: Optional['WorkflowRegistry'] = None
    _cache_file = ".claude/popkit/workflows/registry.json"

    def __init__(self):
        self.entries: Dict[str, WorkflowRegistryEntry] = {}  # workflow_id -> entry
        self.by_skill: Dict[str, str] = {}  # skill_name -> workflow_id
        self._definitions: Dict[str, Dict[str, Any]] = {}  # workflow_id -> definition
        self.last_scan: Optional[str] = None

    @classmethod
    def load(cls, force_scan: bool = False) -> 'WorkflowRegistry':
        """Load or create the workflow registry.

        Args:
            force_scan: Force rescanning skills even if cache exists

        Returns:
            WorkflowRegistry instance
        """
        if cls._instance is not None and not force_scan:
            return cls._instance

        registry = cls()

        # Try to load from cache
        cache_path = cls._get_cache_path()
        if cache_path.exists() and not force_scan:
            try:
                registry._load_cache(cache_path)
                cls._instance = registry
                return registry
            except Exception:
                pass

        # Scan skills directory
        registry._scan_skills()
        registry._save_cache(cache_path)

        cls._instance = registry
        return registry

    @classmethod
    def _get_cache_path(cls) -> Path:
        """Get the cache file path."""
        # Find project root
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "package.json").exists():
                cache_path = parent / cls._cache_file
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                return cache_path

        cache_path = current / cls._cache_file
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        return cache_path

    @classmethod
    def _get_skills_dir(cls) -> Optional[Path]:
        """Get the skills directory path."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            skills_dir = parent / "packages" / "plugin" / "skills"
            if skills_dir.exists():
                return skills_dir
            # Also check for flat plugin structure
            skills_dir = parent / "skills"
            if skills_dir.exists():
                return skills_dir
        return None

    def _load_cache(self, cache_path: Path) -> None:
        """Load registry from cache file."""
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.last_scan = data.get("last_scan")

        for entry_data in data.get("entries", []):
            entry = WorkflowRegistryEntry(
                skill_name=entry_data["skill_name"],
                skill_path=entry_data["skill_path"],
                workflow_id=entry_data["workflow_id"],
                workflow_name=entry_data["workflow_name"],
                description=entry_data.get("description", ""),
                version=entry_data.get("version", 1),
                step_count=entry_data.get("step_count", 0)
            )
            self.entries[entry.workflow_id] = entry
            self.by_skill[entry.skill_name] = entry.workflow_id

        self._definitions = data.get("definitions", {})

    def _save_cache(self, cache_path: Path) -> None:
        """Save registry to cache file."""
        data = {
            "last_scan": self.last_scan,
            "entries": [e.to_dict() for e in self.entries.values()],
            "definitions": self._definitions
        }

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _scan_skills(self) -> None:
        """Scan skills directory for workflow definitions."""
        skills_dir = self._get_skills_dir()
        if not skills_dir:
            return

        self.last_scan = datetime.now().isoformat()

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            # Parse workflow
            workflow = parse_skill_workflow(skill_file)
            if not workflow:
                continue

            # Validate
            validation = validate_workflow_definition(workflow)
            if not validation.valid:
                continue  # Skip invalid workflows

            # Create entry
            workflow_id = workflow.get("id", skill_dir.name)
            skill_name = workflow.get("skill_name", skill_dir.name)

            entry = WorkflowRegistryEntry(
                skill_name=skill_name,
                skill_path=str(skill_file.relative_to(skills_dir.parent.parent.parent)),
                workflow_id=workflow_id,
                workflow_name=workflow.get("name", workflow_id),
                description=workflow.get("description", ""),
                version=workflow.get("version", 1),
                step_count=len(workflow.get("steps", []))
            )

            self.entries[workflow_id] = entry
            self.by_skill[skill_name] = workflow_id
            self._definitions[workflow_id] = workflow

    def get_by_id(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID.

        Args:
            workflow_id: Workflow definition ID

        Returns:
            WorkflowDefinition if found
        """
        if workflow_id not in self._definitions:
            return None

        return WorkflowDefinition.from_dict(self._definitions[workflow_id])

    def get_by_skill(self, skill_name: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by skill name.

        Args:
            skill_name: Skill name (e.g., "pop-feature-dev")

        Returns:
            WorkflowDefinition if found
        """
        workflow_id = self.by_skill.get(skill_name)
        if not workflow_id:
            return None

        return self.get_by_id(workflow_id)

    def list_workflows(self) -> List[WorkflowRegistryEntry]:
        """List all registered workflows."""
        return list(self.entries.values())

    def has_workflow(self, skill_name: str) -> bool:
        """Check if a skill has a workflow defined."""
        return skill_name in self.by_skill

    def refresh(self) -> None:
        """Force refresh the registry by rescanning skills."""
        self.entries.clear()
        self.by_skill.clear()
        self._definitions.clear()
        self._scan_skills()
        self._save_cache(self._get_cache_path())


# =============================================================================
# Convenience Functions
# =============================================================================

def get_workflow_for_skill(skill_name: str) -> Optional[WorkflowDefinition]:
    """Get the workflow definition for a skill.

    Args:
        skill_name: Skill name (e.g., "pop-feature-dev")

    Returns:
        WorkflowDefinition if skill has a workflow
    """
    registry = WorkflowRegistry.load()
    return registry.get_by_skill(skill_name)


def skill_has_workflow(skill_name: str) -> bool:
    """Check if a skill has a workflow defined.

    Args:
        skill_name: Skill name

    Returns:
        True if skill has workflow
    """
    registry = WorkflowRegistry.load()
    return registry.has_workflow(skill_name)


def list_available_workflows() -> List[Dict[str, Any]]:
    """List all available workflows.

    Returns:
        List of workflow summaries
    """
    registry = WorkflowRegistry.load()
    return [e.to_dict() for e in registry.list_workflows()]


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("Testing workflow_parser.py...\n")

    # Test YAML parsing
    print("1. Testing YAML frontmatter parsing")
    test_yaml = """---
name: test-skill
description: "A test skill"
inputs:
  - from: any
    field: topic
workflow:
  id: test-workflow
  name: Test Workflow
  version: 1
  steps:
    - id: start
      type: skill
      skill: pop-test
      next: decision
    - id: decision
      type: user_decision
      question: "Which path?"
      options:
        - id: a
          label: "Path A"
          next: end
        - id: b
          label: "Path B"
          next: end
    - id: end
      type: terminal
---

# Test Skill

Body content here.
"""

    frontmatter, body = _parse_yaml_frontmatter(test_yaml)
    assert frontmatter.get("name") == "test-skill", f"Expected 'test-skill', got {frontmatter.get('name')}"
    assert "workflow" in frontmatter, "Expected 'workflow' in frontmatter"
    assert frontmatter["workflow"]["id"] == "test-workflow"
    print("   Frontmatter parsed correctly")
    print(f"   Found workflow: {frontmatter['workflow']['id']}")
    print(f"   Steps: {len(frontmatter['workflow']['steps'])}")

    # Test validation
    print("\n2. Testing workflow validation")
    validation = validate_workflow_definition(frontmatter["workflow"])
    assert validation.valid, f"Expected valid workflow, got errors: {validation.errors}"
    print("   Validation passed")

    # Test invalid workflow
    print("\n3. Testing invalid workflow detection")
    invalid_workflow = {
        "id": "invalid",
        "steps": [
            {"id": "step1", "type": "skill"},  # Missing skill field
            {"id": "step1", "type": "skill", "skill": "test"}  # Duplicate ID
        ]
    }
    validation = validate_workflow_definition(invalid_workflow)
    assert not validation.valid, "Expected invalid workflow"
    print(f"   Detected {len(validation.errors)} errors")
    for err in validation.errors:
        print(f"   - {err}")

    # Test registry (if skills directory exists)
    print("\n4. Testing workflow registry")
    try:
        registry = WorkflowRegistry.load(force_scan=True)
        workflows = registry.list_workflows()
        print(f"   Found {len(workflows)} workflows")
        for entry in workflows[:5]:  # Show first 5
            print(f"   - {entry.skill_name}: {entry.workflow_id}")
    except Exception as e:
        print(f"   Registry test skipped (no skills dir): {e}")

    print("\n[OK] All tests passed!")
