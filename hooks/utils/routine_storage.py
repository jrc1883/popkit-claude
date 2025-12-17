#!/usr/bin/env python3
"""
Routine Storage Management Utility

Manages project-specific routines stored in .claude/popkit/routines/.
Handles creation, retrieval, updates, and deletion of morning/nightly routines.

Part of the popkit plugin system.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone


# Constants
POPKIT_DIR = ".claude/popkit"
ROUTINES_DIR = "routines"
CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
MAX_CUSTOM_ROUTINES = 5
RESERVED_PREFIX = "pk"


def get_project_root() -> str:
    """Find the project root by looking for .git or package.json.

    Returns:
        Path to project root directory
    """
    cwd = os.getcwd()

    # Walk up looking for project markers
    current = cwd
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, ".git")):
            return current
        if os.path.exists(os.path.join(current, "package.json")):
            return current
        if os.path.exists(os.path.join(current, "pyproject.toml")):
            return current
        current = os.path.dirname(current)

    return cwd


def get_popkit_dir(project_root: Optional[str] = None) -> str:
    """Get the .claude/popkit directory path.

    Args:
        project_root: Optional project root override

    Returns:
        Path to .claude/popkit directory
    """
    if project_root is None:
        project_root = get_project_root()
    return os.path.join(project_root, POPKIT_DIR)


def get_routines_dir(project_root: Optional[str] = None, routine_type: str = "morning") -> str:
    """Get the routines directory for a specific type.

    Args:
        project_root: Optional project root override
        routine_type: "morning" or "nightly"

    Returns:
        Path to routines directory
    """
    popkit_dir = get_popkit_dir(project_root)
    return os.path.join(popkit_dir, ROUTINES_DIR, routine_type)


def ensure_directory_structure(project_root: Optional[str] = None) -> str:
    """Create the .claude/popkit directory structure if it doesn't exist.

    Args:
        project_root: Optional project root override

    Returns:
        Path to created popkit directory
    """
    popkit_dir = get_popkit_dir(project_root)

    # Create main directories
    dirs_to_create = [
        popkit_dir,
        os.path.join(popkit_dir, ROUTINES_DIR),
        os.path.join(popkit_dir, ROUTINES_DIR, "morning"),
        os.path.join(popkit_dir, ROUTINES_DIR, "nightly"),
        os.path.join(popkit_dir, ROUTINES_DIR, "shared"),
        os.path.join(popkit_dir, ROUTINES_DIR, "shared", "checks"),
        os.path.join(popkit_dir, ROUTINES_DIR, "shared", "templates"),
    ]

    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)

    return popkit_dir


# =============================================================================
# Prefix Generation
# =============================================================================

def generate_prefix(project_name: str) -> str:
    """Generate a prefix from project name (first letter of each word).

    Args:
        project_name: The project name (e.g., "Reseller Central")

    Returns:
        Generated prefix (e.g., "rc")

    Examples:
        "Reseller Central" -> "rc"
        "My Awesome App" -> "maa"
        "genesis" -> "gen"
        "popkit" -> "pop" (collision handling)
    """
    # Clean and split the name
    words = re.split(r'[\s\-_]+', project_name.strip())
    words = [w for w in words if w]  # Remove empty strings

    if not words:
        return "proj"

    # Single word: use first 3 characters
    if len(words) == 1:
        prefix = words[0][:3].lower()
    else:
        # Multiple words: first letter of each
        prefix = "".join(word[0] for word in words).lower()

    # Handle collision with reserved prefix
    if prefix == RESERVED_PREFIX:
        # Use first 3 chars of first word instead
        prefix = words[0][:3].lower()
        if prefix == RESERVED_PREFIX:
            prefix = f"{prefix}1"

    return prefix


def get_project_name(project_root: Optional[str] = None) -> str:
    """Detect project name from package.json, pyproject.toml, or directory name.

    Args:
        project_root: Optional project root override

    Returns:
        Project name
    """
    if project_root is None:
        project_root = get_project_root()

    # Try package.json
    package_json = os.path.join(project_root, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data:
                    return data["name"]
        except (json.JSONDecodeError, IOError):
            pass

    # Try pyproject.toml
    pyproject = os.path.join(project_root, "pyproject.toml")
    if os.path.exists(pyproject):
        try:
            with open(pyproject, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except IOError:
            pass

    # Fall back to directory name
    return os.path.basename(project_root)


# =============================================================================
# Config Management
# =============================================================================

def load_config(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Load the popkit config.json for this project.

    Args:
        project_root: Optional project root override

    Returns:
        Config dict (empty dict if file doesn't exist)
    """
    popkit_dir = get_popkit_dir(project_root)
    config_path = os.path.join(popkit_dir, CONFIG_FILE)

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config: Dict[str, Any], project_root: Optional[str] = None) -> str:
    """Save the popkit config.json for this project.

    Args:
        config: Config dict to save
        project_root: Optional project root override

    Returns:
        Path to saved config file
    """
    popkit_dir = ensure_directory_structure(project_root)
    config_path = os.path.join(popkit_dir, CONFIG_FILE)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return config_path


def initialize_config(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Initialize a new config.json with project defaults.

    Args:
        project_root: Optional project root override

    Returns:
        Initialized config dict
    """
    if project_root is None:
        project_root = get_project_root()

    project_name = get_project_name(project_root)
    prefix = generate_prefix(project_name)

    config = {
        "project_name": project_name,
        "prefix": prefix,
        "defaults": {
            "morning": "pk",
            "nightly": "pk"
        },
        "routines": {
            "morning": [],
            "nightly": []
        }
    }

    save_config(config, project_root)
    return config


def get_or_create_config(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Get existing config or create a new one.

    Args:
        project_root: Optional project root override

    Returns:
        Config dict
    """
    config = load_config(project_root)
    if not config:
        config = initialize_config(project_root)
    return config


# =============================================================================
# Routine Management
# =============================================================================

def get_next_routine_id(config: Dict[str, Any], routine_type: str) -> Optional[str]:
    """Get the next available routine ID for a type.

    Args:
        config: The project config
        routine_type: "morning" or "nightly"

    Returns:
        Next ID (e.g., "rc-1") or None if at limit
    """
    prefix = config.get("prefix", "proj")
    existing = config.get("routines", {}).get(routine_type, [])

    if len(existing) >= MAX_CUSTOM_ROUTINES:
        return None

    # Find highest existing number
    highest = 0
    for routine in existing:
        match = re.search(r'-(\d+)$', routine.get("id", ""))
        if match:
            num = int(match.group(1))
            if num > highest:
                highest = num

    return f"{prefix}-{highest + 1}"


def list_routines(routine_type: str, project_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all routines of a type (including pk).

    Args:
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        List of routine info dicts
    """
    config = load_config(project_root)
    default_id = config.get("defaults", {}).get(routine_type, "pk")

    routines = [
        {
            "id": "pk",
            "name": "PopKit Standard",
            "description": "Universal routine with flags for variation",
            "is_default": default_id == "pk",
            "created": "(built-in)",
            "mutable": False
        }
    ]

    # Add custom routines
    for routine in config.get("routines", {}).get(routine_type, []):
        routine["is_default"] = routine.get("id") == default_id
        routine["mutable"] = True
        routines.append(routine)

    return routines


def get_routine(routine_id: str, routine_type: str, project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a specific routine by ID.

    Args:
        routine_id: The routine ID (e.g., "pk", "rc-1")
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        Routine info dict or None
    """
    routines = list_routines(routine_type, project_root)
    for routine in routines:
        if routine.get("id") == routine_id:
            return routine
    return None


def get_default_routine(routine_type: str, project_root: Optional[str] = None) -> str:
    """Get the default routine ID for a type.

    Args:
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        Default routine ID (e.g., "pk", "rc-1")
    """
    config = load_config(project_root)
    return config.get("defaults", {}).get(routine_type, "pk")


def set_default_routine(routine_id: str, routine_type: str, project_root: Optional[str] = None) -> bool:
    """Set the default routine for a type.

    Args:
        routine_id: The routine ID to set as default
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        True if successful, False if routine doesn't exist
    """
    # Verify routine exists
    routine = get_routine(routine_id, routine_type, project_root)
    if not routine:
        return False

    config = get_or_create_config(project_root)
    if "defaults" not in config:
        config["defaults"] = {}
    config["defaults"][routine_type] = routine_id
    save_config(config, project_root)
    return True


def create_routine(
    name: str,
    description: str,
    routine_type: str,
    based_on: str = "pk",
    project_root: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Create a new custom routine.

    Args:
        name: Human-readable routine name
        description: Short description
        routine_type: "morning" or "nightly"
        based_on: ID of routine this is based on
        project_root: Optional project root override

    Returns:
        Tuple of (routine_id, routine_path) or (None, error_message)
    """
    config = get_or_create_config(project_root)

    # Get next ID
    routine_id = get_next_routine_id(config, routine_type)
    if not routine_id:
        return None, f"Maximum of {MAX_CUSTOM_ROUTINES} custom routines reached"

    # Create routine directory
    routines_dir = get_routines_dir(project_root, routine_type)
    routine_path = os.path.join(routines_dir, routine_id)

    os.makedirs(routine_path, exist_ok=True)
    os.makedirs(os.path.join(routine_path, "checks" if routine_type == "morning" else "scripts"), exist_ok=True)

    # Create routine.md
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    routine_content = f"""---
id: {routine_id}
name: {name}
type: {routine_type}
project: {config.get('project_name', 'Unknown')}
prefix: {config.get('prefix', 'proj')}
based_on: {based_on}
created: {now}
modified: {now}
---

# {routine_type.title()} Routine: {name}

{description}

## Checks

### Git Status
```bash
git status --porcelain
git log --oneline -3
```

### Code Quality
```bash
# Add project-specific quality checks here
```

## Score Calculation

| Check | Points | Criteria |
|-------|--------|----------|
| Git clean | 25 | No uncommitted changes |
| Quality | 25 | No errors |
| Services | 25 | All responding |
| Custom | 25 | Project-specific |

Total: 100 points
"""

    routine_md_path = os.path.join(routine_path, "routine.md")
    with open(routine_md_path, "w", encoding="utf-8") as f:
        f.write(routine_content)

    # Create routine config.json
    routine_config = {
        "id": routine_id,
        "name": name,
        "description": description,
        "based_on": based_on,
        "checks": [],
        "score_weights": {
            "git_clean": 25,
            "quality": 25,
            "services": 25,
            "custom": 25
        }
    }

    routine_config_path = os.path.join(routine_path, "config.json")
    with open(routine_config_path, "w", encoding="utf-8") as f:
        json.dump(routine_config, f, indent=2)

    # Update project config
    routine_entry = {
        "id": routine_id,
        "name": name,
        "description": description,
        "created": now,
        "based_on": based_on
    }

    if "routines" not in config:
        config["routines"] = {}
    if routine_type not in config["routines"]:
        config["routines"][routine_type] = []

    config["routines"][routine_type].append(routine_entry)
    save_config(config, project_root)

    return routine_id, routine_path


def delete_routine(routine_id: str, routine_type: str, project_root: Optional[str] = None) -> Tuple[bool, str]:
    """Delete a custom routine.

    Args:
        routine_id: The routine ID to delete
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        Tuple of (success, message)
    """
    # Cannot delete pk
    if routine_id == "pk":
        return False, "Cannot delete built-in PopKit routine"

    config = load_config(project_root)

    # Check if it's the default
    default_id = config.get("defaults", {}).get(routine_type, "pk")
    if routine_id == default_id:
        return False, f"Cannot delete default routine. Change default first with 'set' command"

    # Find and remove from config
    routines = config.get("routines", {}).get(routine_type, [])
    found = False
    for i, routine in enumerate(routines):
        if routine.get("id") == routine_id:
            routines.pop(i)
            found = True
            break

    if not found:
        return False, f"Routine '{routine_id}' not found"

    # Remove directory
    routines_dir = get_routines_dir(project_root, routine_type)
    routine_path = os.path.join(routines_dir, routine_id)

    if os.path.exists(routine_path):
        import shutil
        shutil.rmtree(routine_path)

    # Save updated config
    save_config(config, project_root)

    return True, f"Routine '{routine_id}' deleted"


def get_routine_path(routine_id: str, routine_type: str, project_root: Optional[str] = None) -> Optional[str]:
    """Get the filesystem path to a routine folder.

    Args:
        routine_id: The routine ID (e.g., "rc-1")
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        Path to routine folder or None if pk or not found
    """
    if routine_id == "pk":
        return None  # pk is built-in, no folder

    routines_dir = get_routines_dir(project_root, routine_type)
    routine_path = os.path.join(routines_dir, routine_id)

    if os.path.exists(routine_path):
        return routine_path
    return None


def get_available_slots(routine_type: str, project_root: Optional[str] = None) -> int:
    """Get number of available routine slots.

    Args:
        routine_type: "morning" or "nightly"
        project_root: Optional project root override

    Returns:
        Number of available slots (0-5)
    """
    config = load_config(project_root)
    existing = len(config.get("routines", {}).get(routine_type, []))
    return MAX_CUSTOM_ROUTINES - existing


# =============================================================================
# Formatting Utilities
# =============================================================================

def format_routine_list(routines: List[Dict[str, Any]], routine_type: str) -> str:
    """Format a list of routines as a table.

    Args:
        routines: List of routine dicts
        routine_type: "morning" or "nightly"

    Returns:
        Formatted table string
    """
    lines = []
    lines.append(f"\n{routine_type.title()} Routines\n")
    lines.append("| ID    | Name                  | Default | Created    |")
    lines.append("|-------|-----------------------|---------|------------|")

    for r in routines:
        default_mark = "yes" if r.get("is_default") else ""
        created = r.get("created", "")[:10] if r.get("created") else "(built-in)"
        name = r.get("name", "")[:21]
        lines.append(f"| {r.get('id', ''):<5} | {name:<21} | {default_mark:<7} | {created:<10} |")

    slots = MAX_CUSTOM_ROUTINES - len([r for r in routines if r.get("mutable")])
    lines.append(f"\nSlots available: {slots} of {MAX_CUSTOM_ROUTINES}")

    return "\n".join(lines)


def format_startup_banner(routine: Dict[str, Any], routine_type: str, project_name: str, other_ids: List[str]) -> str:
    """Format the startup banner shown when running a routine.

    Args:
        routine: The routine being run
        routine_type: "morning" or "nightly"
        project_name: The project name
        other_ids: List of other available routine IDs

    Returns:
        Formatted banner string
    """
    routine_id = routine.get("id", "pk")
    routine_name = routine.get("name", "PopKit Standard")

    others_str = ", ".join(other_ids[:3])
    if len(other_ids) > 3:
        others_str += f" (+{len(other_ids) - 3} more)"

    tip = f"Other routines: {others_str} | Run: /popkit:{routine_type} list" if other_ids else f"Tip: Create a custom routine with /popkit:{routine_type} generate"

    lines = [
        "+-------------------------------------------------------------+",
        f"| {routine_type.title()} Routine: {routine_id} ({routine_name})".ljust(61) + "|",
        f"| Project: {project_name}".ljust(61) + "|",
        f"| {tip}".ljust(61)[:61] + "|",
        "+-------------------------------------------------------------+",
    ]

    return "\n".join(lines)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: routine_storage.py <command> [args]")
        print("Commands: init, list, create, delete, set-default, prefix")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        config = initialize_config()
        print(f"Initialized config with prefix: {config['prefix']}")
        print(f"Project: {config['project_name']}")

    elif command == "list":
        routine_type = sys.argv[2] if len(sys.argv) > 2 else "morning"
        routines = list_routines(routine_type)
        print(format_routine_list(routines, routine_type))

    elif command == "prefix":
        name = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else get_project_name()
        print(f"Prefix for '{name}': {generate_prefix(name)}")

    elif command == "create":
        if len(sys.argv) < 5:
            print("Usage: routine_storage.py create <type> <name> <description>")
            sys.exit(1)
        routine_type = sys.argv[2]
        name = sys.argv[3]
        description = " ".join(sys.argv[4:])
        routine_id, result = create_routine(name, description, routine_type)
        if routine_id:
            print(f"Created routine: {routine_id} at {result}")
        else:
            print(f"Error: {result}")

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: routine_storage.py delete <type> <id>")
            sys.exit(1)
        routine_type = sys.argv[2]
        routine_id = sys.argv[3]
        success, message = delete_routine(routine_id, routine_type)
        print(message)

    elif command == "set-default":
        if len(sys.argv) < 4:
            print("Usage: routine_storage.py set-default <type> <id>")
            sys.exit(1)
        routine_type = sys.argv[2]
        routine_id = sys.argv[3]
        if set_default_routine(routine_id, routine_type):
            print(f"Default {routine_type} routine set to: {routine_id}")
        else:
            print(f"Error: Routine '{routine_id}' not found")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
