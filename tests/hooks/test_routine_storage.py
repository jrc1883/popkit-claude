"""Tests for routine storage management utility."""
import pytest
import json
import os
import sys
import shutil
from pathlib import Path

# Add hooks/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hooks', 'utils'))

from routine_storage import (
    generate_prefix,
    get_project_name,
    list_routines,
    create_routine,
    delete_routine,
    set_default_routine,
    get_next_routine_id,
    format_routine_list,
    format_startup_banner,
    load_config,
    save_config,
    initialize_config,
    get_or_create_config,
    get_routine,
    get_default_routine,
    get_routine_path,
    get_available_slots,
    ensure_directory_structure,
    MAX_CUSTOM_ROUTINES,
    RESERVED_PREFIX
)


# =============================================================================
# Prefix Generation Tests
# =============================================================================

def test_generate_prefix_single_word():
    """Single word should use first 3 characters."""
    assert generate_prefix("genesis") == "gen"
    assert generate_prefix("project") == "pro"
    assert generate_prefix("app") == "app"


def test_generate_prefix_multiple_words():
    """Multiple words should use first letter of each."""
    assert generate_prefix("Reseller Central") == "rc"
    assert generate_prefix("My Awesome App") == "maa"
    assert generate_prefix("Super Cool Project") == "scp"


def test_generate_prefix_hyphenated():
    """Hyphenated names should be split into words."""
    assert generate_prefix("my-cool-app") == "mca"
    assert generate_prefix("api-server-v2") == "asv"


def test_generate_prefix_underscore_separated():
    """Underscore-separated names should be split."""
    assert generate_prefix("my_cool_app") == "mca"
    assert generate_prefix("api_server") == "as"


def test_generate_prefix_reserved_collision():
    """Reserved prefix 'pk' should be handled."""
    # Single word that starts with 'pk'
    prefix = generate_prefix("pk")
    assert prefix != RESERVED_PREFIX
    assert prefix == "pk1"  # Collision fallback


def test_generate_prefix_reserved_multi_word():
    """Multi-word name that generates 'pk' should fallback."""
    # "Popkit Kit" -> "pk" collision
    prefix = generate_prefix("Popkit Kit")
    assert prefix != RESERVED_PREFIX
    assert len(prefix) == 3


def test_generate_prefix_empty_string():
    """Empty string should return default."""
    assert generate_prefix("") == "proj"
    assert generate_prefix("   ") == "proj"


def test_generate_prefix_mixed_case():
    """Mixed case should be lowercased."""
    assert generate_prefix("MyApp") == "mya"
    assert generate_prefix("SUPER COOL") == "sc"


def test_generate_prefix_special_characters():
    """Special characters should be stripped."""
    assert generate_prefix("my cool app") == "mca"
    assert generate_prefix("api-server_v2") == "asv"


# =============================================================================
# Project Name Detection Tests
# =============================================================================

def test_get_project_name_from_package_json(tmp_path):
    """Detect project name from package.json."""
    pkg = {"name": "my-awesome-project"}
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text(json.dumps(pkg))

    name = get_project_name(str(tmp_path))
    assert name == "my-awesome-project"


def test_get_project_name_from_pyproject_toml(tmp_path):
    """Detect project name from pyproject.toml."""
    content = '''[tool.poetry]
name = "my-python-project"
version = "1.0.0"
'''
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content)

    name = get_project_name(str(tmp_path))
    assert name == "my-python-project"


def test_get_project_name_fallback_to_directory(tmp_path):
    """Fall back to directory name when no config files."""
    name = get_project_name(str(tmp_path))
    assert name == tmp_path.name


def test_get_project_name_invalid_json(tmp_path):
    """Handle invalid JSON gracefully."""
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text("{invalid json")

    name = get_project_name(str(tmp_path))
    assert name == tmp_path.name


def test_get_project_name_missing_name_field(tmp_path):
    """Handle package.json without name field."""
    pkg = {"version": "1.0.0"}
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text(json.dumps(pkg))

    name = get_project_name(str(tmp_path))
    assert name == tmp_path.name


# =============================================================================
# Config Management Tests
# =============================================================================

def test_initialize_config_creates_file(tmp_path):
    """Initialize config should create config.json."""
    config = initialize_config(str(tmp_path))

    assert "project_name" in config
    assert "prefix" in config
    assert "defaults" in config
    assert "routines" in config

    config_file = tmp_path / ".claude" / "popkit" / "config.json"
    assert config_file.exists()


def test_load_config_returns_empty_if_not_exists(tmp_path):
    """Load config should return empty dict if file doesn't exist."""
    config = load_config(str(tmp_path))
    assert config == {}


def test_save_config_persists_to_disk(tmp_path):
    """Save config should persist to disk."""
    config = {
        "project_name": "test-project",
        "prefix": "tp",
        "defaults": {"morning": "pk", "nightly": "pk"},
        "routines": {"morning": [], "nightly": []}
    }

    save_config(config, str(tmp_path))

    config_file = tmp_path / ".claude" / "popkit" / "config.json"
    assert config_file.exists()

    loaded = json.loads(config_file.read_text())
    assert loaded == config


def test_get_or_create_config_creates_new(tmp_path):
    """Get or create should create new config if not exists."""
    config = get_or_create_config(str(tmp_path))

    assert config is not None
    assert "prefix" in config


def test_get_or_create_config_loads_existing(tmp_path):
    """Get or create should load existing config."""
    existing = {
        "project_name": "existing-project",
        "prefix": "ep"
    }
    save_config(existing, str(tmp_path))

    config = get_or_create_config(str(tmp_path))
    assert config["project_name"] == "existing-project"
    assert config["prefix"] == "ep"


# =============================================================================
# Routine CRUD Tests
# =============================================================================

def test_create_routine_success(tmp_path):
    """Create routine should succeed with valid params."""
    initialize_config(str(tmp_path))

    routine_id, routine_path = create_routine(
        name="My Morning Routine",
        description="Custom checks for my project",
        routine_type="morning",
        based_on="pk",
        project_root=str(tmp_path)
    )

    assert routine_id is not None
    assert routine_id.endswith("-1")  # First custom routine
    assert routine_path is not None
    assert os.path.exists(routine_path)


def test_create_routine_creates_files(tmp_path):
    """Create routine should create routine.md and config.json."""
    initialize_config(str(tmp_path))

    routine_id, routine_path = create_routine(
        name="Test Routine",
        description="Test description",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    routine_md = os.path.join(routine_path, "routine.md")
    routine_config = os.path.join(routine_path, "config.json")
    checks_dir = os.path.join(routine_path, "checks")

    assert os.path.exists(routine_md)
    assert os.path.exists(routine_config)
    assert os.path.isdir(checks_dir)


def test_create_routine_at_max_limit(tmp_path):
    """Create routine should fail at MAX_CUSTOM_ROUTINES limit."""
    initialize_config(str(tmp_path))

    # Create max routines
    for i in range(MAX_CUSTOM_ROUTINES):
        routine_id, _ = create_routine(
            name=f"Routine {i+1}",
            description="Test",
            routine_type="morning",
            project_root=str(tmp_path)
        )
        assert routine_id is not None

    # Try to create one more
    routine_id, error = create_routine(
        name="Extra Routine",
        description="Should fail",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    assert routine_id is None
    assert "Maximum" in error


def test_create_routine_nightly_type(tmp_path):
    """Create nightly routine should create scripts directory."""
    initialize_config(str(tmp_path))

    routine_id, routine_path = create_routine(
        name="Nightly Cleanup",
        description="End of day tasks",
        routine_type="nightly",
        project_root=str(tmp_path)
    )

    scripts_dir = os.path.join(routine_path, "scripts")
    assert os.path.isdir(scripts_dir)


def test_list_routines_includes_pk(tmp_path):
    """List routines should always include 'pk' built-in."""
    initialize_config(str(tmp_path))

    routines = list_routines("morning", str(tmp_path))

    assert len(routines) >= 1
    pk_routine = next((r for r in routines if r["id"] == "pk"), None)
    assert pk_routine is not None
    assert pk_routine["mutable"] is False


def test_list_routines_includes_custom(tmp_path):
    """List routines should include custom routines."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="Custom Morning",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    routines = list_routines("morning", str(tmp_path))

    custom = next((r for r in routines if r["id"] == routine_id), None)
    assert custom is not None
    assert custom["mutable"] is True


def test_delete_routine_success(tmp_path):
    """Delete routine should remove custom routine."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="To Delete",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    success, message = delete_routine(routine_id, "morning", str(tmp_path))

    assert success is True
    assert "deleted" in message.lower()

    # Verify removed from list
    routines = list_routines("morning", str(tmp_path))
    deleted = next((r for r in routines if r["id"] == routine_id), None)
    assert deleted is None


def test_delete_routine_cannot_delete_pk(tmp_path):
    """Cannot delete built-in 'pk' routine."""
    initialize_config(str(tmp_path))

    success, message = delete_routine("pk", "morning", str(tmp_path))

    assert success is False
    assert "Cannot delete built-in" in message


def test_delete_routine_cannot_delete_default(tmp_path):
    """Cannot delete routine that is set as default."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="Default Routine",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    # Set as default
    set_default_routine(routine_id, "morning", str(tmp_path))

    # Try to delete
    success, message = delete_routine(routine_id, "morning", str(tmp_path))

    assert success is False
    assert "default" in message.lower()


def test_delete_routine_removes_directory(tmp_path):
    """Delete routine should remove filesystem directory."""
    initialize_config(str(tmp_path))

    routine_id, routine_path = create_routine(
        name="To Remove",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    assert os.path.exists(routine_path)

    delete_routine(routine_id, "morning", str(tmp_path))

    assert not os.path.exists(routine_path)


def test_set_default_routine_success(tmp_path):
    """Set default routine should update config."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="New Default",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    success = set_default_routine(routine_id, "morning", str(tmp_path))
    assert success is True

    # Verify default is updated
    default = get_default_routine("morning", str(tmp_path))
    assert default == routine_id


def test_set_default_routine_invalid_id(tmp_path):
    """Set default should fail for non-existent routine."""
    initialize_config(str(tmp_path))

    success = set_default_routine("invalid-id", "morning", str(tmp_path))
    assert success is False


def test_set_default_routine_reflects_in_list(tmp_path):
    """Set default should be reflected in routine list."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="Custom",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    set_default_routine(routine_id, "morning", str(tmp_path))

    routines = list_routines("morning", str(tmp_path))
    custom = next((r for r in routines if r["id"] == routine_id), None)
    assert custom["is_default"] is True

    pk = next((r for r in routines if r["id"] == "pk"), None)
    assert pk["is_default"] is False


# =============================================================================
# Helper Function Tests
# =============================================================================

def test_get_next_routine_id_first(tmp_path):
    """Get next routine ID should return prefix-1 for first routine."""
    config = initialize_config(str(tmp_path))

    next_id = get_next_routine_id(config, "morning")

    assert next_id is not None
    assert next_id.endswith("-1")


def test_get_next_routine_id_sequential(tmp_path):
    """Get next routine ID should increment sequentially."""
    initialize_config(str(tmp_path))

    # Create first routine
    routine_id_1, _ = create_routine(
        name="First",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    # Create second routine
    routine_id_2, _ = create_routine(
        name="Second",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    assert routine_id_1.endswith("-1")
    assert routine_id_2.endswith("-2")


def test_get_next_routine_id_at_limit(tmp_path):
    """Get next routine ID should return None at limit."""
    config = initialize_config(str(tmp_path))

    # Manually fill up routines list
    config["routines"]["morning"] = [
        {"id": f"{config['prefix']}-{i}"} for i in range(1, MAX_CUSTOM_ROUTINES + 1)
    ]

    next_id = get_next_routine_id(config, "morning")
    assert next_id is None


def test_get_routine_finds_by_id(tmp_path):
    """Get routine should find routine by ID."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="Findable",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    routine = get_routine(routine_id, "morning", str(tmp_path))

    assert routine is not None
    assert routine["id"] == routine_id
    assert routine["name"] == "Findable"


def test_get_routine_returns_none_for_invalid(tmp_path):
    """Get routine should return None for invalid ID."""
    initialize_config(str(tmp_path))

    routine = get_routine("invalid-id", "morning", str(tmp_path))
    assert routine is None


def test_get_routine_path_returns_path(tmp_path):
    """Get routine path should return filesystem path."""
    initialize_config(str(tmp_path))

    routine_id, routine_path = create_routine(
        name="Test",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    path = get_routine_path(routine_id, "morning", str(tmp_path))

    assert path == routine_path
    assert os.path.exists(path)


def test_get_routine_path_pk_returns_none(tmp_path):
    """Get routine path should return None for pk."""
    initialize_config(str(tmp_path))

    path = get_routine_path("pk", "morning", str(tmp_path))
    assert path is None


def test_get_available_slots_full(tmp_path):
    """Get available slots should return correct count."""
    initialize_config(str(tmp_path))

    slots = get_available_slots("morning", str(tmp_path))
    assert slots == MAX_CUSTOM_ROUTINES


def test_get_available_slots_partial(tmp_path):
    """Get available slots should decrease after creating routines."""
    initialize_config(str(tmp_path))

    create_routine("Test 1", "Test", "morning", project_root=str(tmp_path))
    create_routine("Test 2", "Test", "morning", project_root=str(tmp_path))

    slots = get_available_slots("morning", str(tmp_path))
    assert slots == MAX_CUSTOM_ROUTINES - 2


def test_get_available_slots_zero(tmp_path):
    """Get available slots should return 0 at limit."""
    initialize_config(str(tmp_path))

    for i in range(MAX_CUSTOM_ROUTINES):
        create_routine(f"Test {i}", "Test", "morning", project_root=str(tmp_path))

    slots = get_available_slots("morning", str(tmp_path))
    assert slots == 0


# =============================================================================
# Formatting Tests
# =============================================================================

def test_format_routine_list_includes_header(tmp_path):
    """Format routine list should include header."""
    initialize_config(str(tmp_path))

    routines = list_routines("morning", str(tmp_path))
    formatted = format_routine_list(routines, "morning")

    assert "Morning Routines" in formatted
    assert "| ID" in formatted
    assert "| Name" in formatted


def test_format_routine_list_shows_default(tmp_path):
    """Format routine list should show default marker."""
    initialize_config(str(tmp_path))

    routines = list_routines("morning", str(tmp_path))
    formatted = format_routine_list(routines, "morning")

    # pk is default by default
    assert "yes" in formatted


def test_format_routine_list_shows_slots(tmp_path):
    """Format routine list should show available slots."""
    initialize_config(str(tmp_path))

    create_routine("Test", "Test", "morning", project_root=str(tmp_path))

    routines = list_routines("morning", str(tmp_path))
    formatted = format_routine_list(routines, "morning")

    assert f"Slots available: {MAX_CUSTOM_ROUTINES - 1}" in formatted


def test_format_startup_banner_includes_routine_info(tmp_path):
    """Format startup banner should include routine information."""
    routine = {
        "id": "rc-1",
        "name": "Reseller Central Morning"
    }

    banner = format_startup_banner(
        routine=routine,
        routine_type="morning",
        project_name="Reseller Central",
        other_ids=["rc-2", "rc-3"]
    )

    assert "rc-1" in banner
    assert "Reseller Central Morning" in banner
    assert "Project: Reseller Central" in banner


def test_format_startup_banner_shows_other_routines(tmp_path):
    """Format startup banner should show other available routines."""
    routine = {"id": "pk", "name": "PopKit Standard"}

    banner = format_startup_banner(
        routine=routine,
        routine_type="morning",
        project_name="Test",
        other_ids=["rc-1", "rc-2"]
    )

    assert "rc-1" in banner
    assert "rc-2" in banner


def test_format_startup_banner_truncates_long_list(tmp_path):
    """Format startup banner should truncate long routine lists."""
    routine = {"id": "pk", "name": "PopKit Standard"}

    many_ids = [f"rc-{i}" for i in range(1, 10)]
    banner = format_startup_banner(
        routine=routine,
        routine_type="morning",
        project_name="Test",
        other_ids=many_ids
    )

    assert "+6 more" in banner or "+5 more" in banner  # Truncation indicator


def test_format_startup_banner_no_other_routines(tmp_path):
    """Format startup banner should show tip when no other routines."""
    routine = {"id": "pk", "name": "PopKit Standard"}

    banner = format_startup_banner(
        routine=routine,
        routine_type="morning",
        project_name="Test",
        other_ids=[]
    )

    assert "Tip:" in banner
    assert "generate" in banner


# =============================================================================
# Directory Structure Tests
# =============================================================================

def test_ensure_directory_structure_creates_dirs(tmp_path):
    """Ensure directory structure should create all necessary directories."""
    popkit_dir = ensure_directory_structure(str(tmp_path))

    assert os.path.exists(popkit_dir)
    assert os.path.exists(os.path.join(popkit_dir, "routines"))
    assert os.path.exists(os.path.join(popkit_dir, "routines", "morning"))
    assert os.path.exists(os.path.join(popkit_dir, "routines", "nightly"))
    assert os.path.exists(os.path.join(popkit_dir, "routines", "shared"))


def test_ensure_directory_structure_idempotent(tmp_path):
    """Ensure directory structure should be idempotent."""
    dir1 = ensure_directory_structure(str(tmp_path))
    dir2 = ensure_directory_structure(str(tmp_path))

    assert dir1 == dir2
    assert os.path.exists(dir1)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

def test_create_routine_updates_config(tmp_path):
    """Create routine should update project config."""
    initialize_config(str(tmp_path))

    routine_id, _ = create_routine(
        name="Test",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    config = load_config(str(tmp_path))
    morning_routines = config["routines"]["morning"]

    found = any(r["id"] == routine_id for r in morning_routines)
    assert found is True


def test_delete_nonexistent_routine(tmp_path):
    """Delete nonexistent routine should return error."""
    initialize_config(str(tmp_path))

    success, message = delete_routine("nonexistent", "morning", str(tmp_path))

    assert success is False
    assert "not found" in message.lower()


def test_routine_isolation_by_type(tmp_path):
    """Morning and nightly routines should be isolated."""
    initialize_config(str(tmp_path))

    morning_id, _ = create_routine(
        name="Morning",
        description="Test",
        routine_type="morning",
        project_root=str(tmp_path)
    )

    nightly_id, _ = create_routine(
        name="Nightly",
        description="Test",
        routine_type="nightly",
        project_root=str(tmp_path)
    )

    morning_routines = list_routines("morning", str(tmp_path))
    nightly_routines = list_routines("nightly", str(tmp_path))

    # Extract custom (non-pk) routine IDs
    morning_custom = [r for r in morning_routines if r["id"] != "pk"]
    nightly_custom = [r for r in nightly_routines if r["id"] != "pk"]

    # Verify each type has exactly one custom routine
    assert len(morning_custom) == 1
    assert len(nightly_custom) == 1

    # Verify the custom routines are correctly named
    assert morning_custom[0]["name"] == "Morning"
    assert nightly_custom[0]["name"] == "Nightly"

    # Both will have ID "prefix-1" since they're the first in their type
    # This is expected behavior - IDs are scoped to routine type


def test_prefix_consistency_across_routines(tmp_path):
    """All custom routines should share same prefix."""
    config = initialize_config(str(tmp_path))
    prefix = config["prefix"]

    id1, _ = create_routine("Test 1", "Test", "morning", project_root=str(tmp_path))
    id2, _ = create_routine("Test 2", "Test", "morning", project_root=str(tmp_path))

    assert id1.startswith(prefix)
    assert id2.startswith(prefix)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
