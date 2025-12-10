#!/usr/bin/env python3
"""
Project Registry Management Utility

Manages the global PopKit project registry stored in ~/.claude/popkit/projects.json.
Handles registration, discovery, health tracking, and project switching.

Part of the popkit plugin system.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone


# Constants
GLOBAL_POPKIT_DIR = os.path.join(os.path.expanduser("~"), ".claude", "popkit")
PROJECTS_FILE = "projects.json"
DEFAULT_SETTINGS = {
    "autoDiscover": True,
    "healthCheckInterval": "daily",
    "maxInactiveProjects": 20
}


def get_global_dir() -> str:
    """Get the global ~/.claude/popkit directory.

    Returns:
        Path to global popkit directory
    """
    return GLOBAL_POPKIT_DIR


def ensure_global_dir() -> str:
    """Create the global popkit directory if it doesn't exist.

    Returns:
        Path to created directory
    """
    os.makedirs(GLOBAL_POPKIT_DIR, exist_ok=True)
    return GLOBAL_POPKIT_DIR


def get_projects_path() -> str:
    """Get the path to projects.json.

    Returns:
        Path to projects.json
    """
    return os.path.join(GLOBAL_POPKIT_DIR, PROJECTS_FILE)


# =============================================================================
# Registry Loading/Saving
# =============================================================================

def load_registry() -> Dict[str, Any]:
    """Load the project registry.

    Returns:
        Registry dict with 'projects' list and 'settings' dict
    """
    projects_path = get_projects_path()

    if not os.path.exists(projects_path):
        return {"projects": [], "settings": DEFAULT_SETTINGS.copy()}

    try:
        with open(projects_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure required keys exist
            if "projects" not in data:
                data["projects"] = []
            if "settings" not in data:
                data["settings"] = DEFAULT_SETTINGS.copy()
            return data
    except (json.JSONDecodeError, IOError):
        return {"projects": [], "settings": DEFAULT_SETTINGS.copy()}


def save_registry(registry: Dict[str, Any]) -> str:
    """Save the project registry.

    Args:
        registry: Registry dict to save

    Returns:
        Path to saved file
    """
    ensure_global_dir()
    projects_path = get_projects_path()

    with open(projects_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return projects_path


# =============================================================================
# Project Detection
# =============================================================================

def detect_project_info(path: str) -> Optional[Dict[str, Any]]:
    """Detect project information from a directory.

    Args:
        path: Path to project directory

    Returns:
        Project info dict or None if not a valid project
    """
    path = os.path.abspath(path)

    if not os.path.isdir(path):
        return None

    # Check for project markers
    has_git = os.path.isdir(os.path.join(path, ".git"))
    has_package = os.path.isfile(os.path.join(path, "package.json"))
    has_pyproject = os.path.isfile(os.path.join(path, "pyproject.toml"))
    has_claude = os.path.isdir(os.path.join(path, ".claude"))

    if not (has_git or has_package or has_pyproject):
        return None

    # Get project name
    name = os.path.basename(path)

    # Try to get name from package.json
    if has_package:
        try:
            with open(os.path.join(path, "package.json"), "r", encoding="utf-8") as f:
                pkg = json.load(f)
                if "name" in pkg:
                    name = pkg["name"]
        except (json.JSONDecodeError, IOError):
            pass

    # Try to get repo from git remote
    repo = None
    if has_git:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", path, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                remote = result.stdout.strip()
                # Parse GitHub URL
                match = re.search(r'github\.com[:/]([^/]+/[^/\.]+)', remote)
                if match:
                    repo = match.group(1)
        except Exception:
            pass

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "name": name,
        "path": path,
        "repo": repo,
        "hasGit": has_git,
        "hasPackage": has_package,
        "hasClaude": has_claude,
        "lastActive": now,
        "healthScore": None,
        "tags": []
    }


def discover_projects(search_dirs: Optional[List[str]] = None, max_depth: int = 2) -> List[Dict[str, Any]]:
    """Auto-discover projects in common locations.

    Args:
        search_dirs: List of directories to search (defaults to common dev dirs)
        max_depth: Maximum subdirectory depth to search

    Returns:
        List of discovered project info dicts
    """
    if search_dirs is None:
        home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(home, "projects"),
            os.path.join(home, "dev"),
            os.path.join(home, "code"),
            os.path.join(home, "workspace"),
            os.path.join(home, "Documents", "projects"),
            os.path.join(home, "Documents", "dev"),
        ]

    discovered = []
    seen_paths = set()

    for base_dir in search_dirs:
        if not os.path.isdir(base_dir):
            continue

        # Search directories up to max_depth
        for root, dirs, files in os.walk(base_dir):
            # Check depth
            rel_path = os.path.relpath(root, base_dir)
            depth = len(rel_path.split(os.sep)) if rel_path != "." else 0

            if depth >= max_depth:
                dirs[:] = []  # Don't recurse deeper
                continue

            # Check if this is a project root
            info = detect_project_info(root)
            if info and info["path"] not in seen_paths:
                seen_paths.add(info["path"])
                discovered.append(info)
                dirs[:] = []  # Don't search inside projects

    return discovered


# =============================================================================
# Project CRUD Operations
# =============================================================================

def list_projects() -> List[Dict[str, Any]]:
    """List all registered projects.

    Returns:
        List of project info dicts
    """
    registry = load_registry()
    return registry.get("projects", [])


def get_project(identifier: str) -> Optional[Dict[str, Any]]:
    """Get a project by name or path.

    Args:
        identifier: Project name or path

    Returns:
        Project info dict or None
    """
    projects = list_projects()
    identifier_lower = identifier.lower()
    identifier_abs = os.path.abspath(identifier) if os.path.exists(identifier) else None

    for project in projects:
        if project.get("name", "").lower() == identifier_lower:
            return project
        if identifier_abs and os.path.abspath(project.get("path", "")) == identifier_abs:
            return project

    return None


def add_project(path: str, tags: Optional[List[str]] = None, update_if_exists: bool = True) -> Tuple[bool, str]:
    """Add a project to the registry.

    Args:
        path: Path to project directory
        tags: Optional tags to apply
        update_if_exists: Whether to update if already registered

    Returns:
        Tuple of (success, message)
    """
    path = os.path.abspath(path)

    # Detect project info
    info = detect_project_info(path)
    if not info:
        return False, f"Not a valid project directory: {path}"

    if tags:
        info["tags"] = tags

    registry = load_registry()

    # Check if already exists
    for i, project in enumerate(registry["projects"]):
        if os.path.abspath(project.get("path", "")) == path:
            if update_if_exists:
                # Update existing entry
                info["healthScore"] = project.get("healthScore")  # Preserve health
                info["tags"] = list(set(project.get("tags", []) + (tags or [])))
                registry["projects"][i] = info
                save_registry(registry)
                return True, f"Updated project: {info['name']}"
            else:
                return False, f"Project already registered: {info['name']}"

    # Add new project
    registry["projects"].append(info)
    save_registry(registry)

    return True, f"Added project: {info['name']}"


def remove_project(identifier: str) -> Tuple[bool, str]:
    """Remove a project from the registry.

    Args:
        identifier: Project name or path

    Returns:
        Tuple of (success, message)
    """
    registry = load_registry()
    identifier_lower = identifier.lower()
    identifier_abs = os.path.abspath(identifier) if os.path.exists(identifier) else None

    for i, project in enumerate(registry["projects"]):
        name = project.get("name", "")
        path = project.get("path", "")

        if name.lower() == identifier_lower or (identifier_abs and os.path.abspath(path) == identifier_abs):
            removed = registry["projects"].pop(i)
            save_registry(registry)
            return True, f"Removed project: {removed['name']}"

    return False, f"Project not found: {identifier}"


def update_project(identifier: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Update a project's properties.

    Args:
        identifier: Project name or path
        updates: Dict of properties to update

    Returns:
        Tuple of (success, message)
    """
    registry = load_registry()
    identifier_lower = identifier.lower()
    identifier_abs = os.path.abspath(identifier) if os.path.exists(identifier) else None

    for i, project in enumerate(registry["projects"]):
        name = project.get("name", "")
        path = project.get("path", "")

        if name.lower() == identifier_lower or (identifier_abs and os.path.abspath(path) == identifier_abs):
            # Apply updates
            for key, value in updates.items():
                if key == "tags" and isinstance(value, list):
                    # Merge tags
                    existing = set(project.get("tags", []))
                    project["tags"] = list(existing.union(value))
                else:
                    project[key] = value

            registry["projects"][i] = project
            save_registry(registry)
            return True, f"Updated project: {name}"

    return False, f"Project not found: {identifier}"


def touch_project(path: str) -> None:
    """Update lastActive timestamp for a project.

    Args:
        path: Path to project directory
    """
    path = os.path.abspath(path)
    registry = load_registry()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for project in registry["projects"]:
        if os.path.abspath(project.get("path", "")) == path:
            project["lastActive"] = now
            save_registry(registry)
            return

    # Project not registered - auto-add if settings allow
    if registry.get("settings", {}).get("autoDiscover", True):
        add_project(path)


# =============================================================================
# Health Score Operations
# =============================================================================

def update_health_score(identifier: str, score: int) -> bool:
    """Update a project's health score.

    Args:
        identifier: Project name or path
        score: Health score (0-100)

    Returns:
        True if successful
    """
    success, _ = update_project(identifier, {"healthScore": max(0, min(100, score))})
    return success


def get_projects_by_health(ascending: bool = False) -> List[Dict[str, Any]]:
    """Get projects sorted by health score.

    Args:
        ascending: Sort ascending (lowest first) if True

    Returns:
        List of projects sorted by health
    """
    projects = list_projects()

    # Sort, treating None as -1 for ordering
    return sorted(
        projects,
        key=lambda p: (p.get("healthScore") is None, p.get("healthScore", 0)),
        reverse=not ascending
    )


def get_unhealthy_projects(threshold: int = 70) -> List[Dict[str, Any]]:
    """Get projects with health scores below threshold.

    Args:
        threshold: Health score threshold (default 70)

    Returns:
        List of unhealthy projects
    """
    return [
        p for p in list_projects()
        if p.get("healthScore") is not None and p["healthScore"] < threshold
    ]


# =============================================================================
# Tag Operations
# =============================================================================

def add_tag(identifier: str, tag: str) -> bool:
    """Add a tag to a project.

    Args:
        identifier: Project name or path
        tag: Tag to add

    Returns:
        True if successful
    """
    project = get_project(identifier)
    if not project:
        return False

    tags = set(project.get("tags", []))
    tags.add(tag.lower())

    success, _ = update_project(identifier, {"tags": list(tags)})
    return success


def remove_tag(identifier: str, tag: str) -> bool:
    """Remove a tag from a project.

    Args:
        identifier: Project name or path
        tag: Tag to remove

    Returns:
        True if successful
    """
    project = get_project(identifier)
    if not project:
        return False

    tags = set(project.get("tags", []))
    tags.discard(tag.lower())

    registry = load_registry()
    for p in registry["projects"]:
        if p.get("name") == project.get("name"):
            p["tags"] = list(tags)
            save_registry(registry)
            return True

    return False


def get_projects_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Get projects with a specific tag.

    Args:
        tag: Tag to filter by

    Returns:
        List of matching projects
    """
    tag_lower = tag.lower()
    return [
        p for p in list_projects()
        if tag_lower in [t.lower() for t in p.get("tags", [])]
    ]


def get_all_tags() -> List[str]:
    """Get all unique tags across projects.

    Returns:
        Sorted list of unique tags
    """
    tags = set()
    for project in list_projects():
        tags.update(project.get("tags", []))
    return sorted(tags)


# =============================================================================
# Activity Tracking
# =============================================================================

def get_recent_projects(limit: int = 5) -> List[Dict[str, Any]]:
    """Get most recently active projects.

    Args:
        limit: Maximum number to return

    Returns:
        List of recently active projects
    """
    projects = list_projects()

    # Sort by lastActive descending
    sorted_projects = sorted(
        projects,
        key=lambda p: p.get("lastActive", ""),
        reverse=True
    )

    return sorted_projects[:limit]


def get_inactive_projects(days: int = 30) -> List[Dict[str, Any]]:
    """Get projects inactive for more than N days.

    Args:
        days: Inactivity threshold in days

    Returns:
        List of inactive projects
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat().replace("+00:00", "Z")

    return [
        p for p in list_projects()
        if p.get("lastActive", "") < cutoff_str
    ]


# =============================================================================
# Formatting Utilities
# =============================================================================

def format_health_indicator(score: Optional[int]) -> str:
    """Format health score as colored indicator.

    Args:
        score: Health score (0-100) or None

    Returns:
        Formatted indicator string
    """
    if score is None:
        return "-- "
    elif score >= 80:
        return f"\033[32m{score:2d}\033[0m"  # Green
    elif score >= 60:
        return f"\033[33m{score:2d}\033[0m"  # Yellow
    else:
        return f"\033[31m{score:2d}\033[0m"  # Red


def format_activity(last_active: str) -> str:
    """Format last active time as relative string.

    Args:
        last_active: ISO timestamp string

    Returns:
        Relative time string (e.g., "2 hours ago")
    """
    if not last_active:
        return "never"

    try:
        dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt

        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            mins = int(diff.total_seconds() / 60)
            return f"{mins} min ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days < 30:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        else:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
    except (ValueError, TypeError):
        return "unknown"


def format_project_table(projects: List[Dict[str, Any]], show_path: bool = False) -> str:
    """Format projects as an ASCII table.

    Args:
        projects: List of project dicts
        show_path: Include path column

    Returns:
        Formatted table string
    """
    if not projects:
        return "No projects registered."

    lines = []

    if show_path:
        lines.append("| Project          | Health | Last Active   | Path                     |")
        lines.append("|------------------|--------|---------------|--------------------------|")
    else:
        lines.append("| Project          | Health | Last Active   | Tags                |")
        lines.append("|------------------|--------|---------------|---------------------|")

    for p in projects:
        name = p.get("name", "?")[:16].ljust(16)
        health = p.get("healthScore")
        health_str = f"{health:>3}" if health is not None else " --"
        activity = format_activity(p.get("lastActive", ""))[:13].ljust(13)

        if show_path:
            path = p.get("path", "")[:24].ljust(24)
            lines.append(f"| {name} | {health_str}  | {activity} | {path} |")
        else:
            tags = ", ".join(p.get("tags", []))[:19].ljust(19)
            lines.append(f"| {name} | {health_str}  | {activity} | {tags} |")

    return "\n".join(lines)


def format_dashboard(projects: List[Dict[str, Any]]) -> str:
    """Format full dashboard display.

    Args:
        projects: List of project dicts

    Returns:
        Formatted dashboard string
    """
    lines = []

    lines.append("")
    lines.append("+" + "=" * 63 + "+")
    lines.append("|" + "PopKit Dashboard".center(63) + "|")
    lines.append("+" + "=" * 63 + "+")
    lines.append("")

    # Summary stats
    total = len(projects)
    healthy = len([p for p in projects if (p.get("healthScore") or 0) >= 80])
    warning = len([p for p in projects if 60 <= (p.get("healthScore") or 0) < 80])
    critical = len([p for p in projects if 0 < (p.get("healthScore") or 0) < 60])
    unknown = len([p for p in projects if p.get("healthScore") is None])

    lines.append(f"  Total: {total}  |  Healthy: {healthy}  |  Warning: {warning}  |  Critical: {critical}  |  Unknown: {unknown}")
    lines.append("")

    # Projects table
    lines.append("  " + "-" * 61)
    lines.append("  | Project          | Health | Issues | Last Active   |")
    lines.append("  " + "-" * 61)

    for p in projects[:10]:  # Show top 10
        name = p.get("name", "?")[:16].ljust(16)
        health = p.get("healthScore")

        if health is None:
            health_icon = "?"
        elif health >= 80:
            health_icon = "+"
        elif health >= 60:
            health_icon = "~"
        else:
            health_icon = "!"

        health_str = f"{health:>2}" if health is not None else "--"
        issues = "--"  # TODO: Integrate with GitHub issues
        activity = format_activity(p.get("lastActive", ""))[:13].ljust(13)

        lines.append(f"  | {name} | {health_icon} {health_str}  | {issues:>6} | {activity} |")

    lines.append("  " + "-" * 61)

    if len(projects) > 10:
        lines.append(f"  ... and {len(projects) - 10} more projects")

    lines.append("")
    lines.append("  Commands: add <path> | remove <name> | refresh | switch <name>")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: project_registry.py <command> [args]")
        print("Commands: list, add, remove, discover, dashboard, touch, tag")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        projects = list_projects()
        print(format_project_table(projects))

    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: project_registry.py add <path> [tags...]")
            sys.exit(1)
        path = sys.argv[2]
        tags = sys.argv[3:] if len(sys.argv) > 3 else None
        success, msg = add_project(path, tags)
        print(msg)

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: project_registry.py remove <name|path>")
            sys.exit(1)
        success, msg = remove_project(sys.argv[2])
        print(msg)

    elif command == "discover":
        dirs = sys.argv[2:] if len(sys.argv) > 2 else None
        projects = discover_projects(dirs)
        print(f"Discovered {len(projects)} projects:")
        for p in projects:
            print(f"  - {p['name']}: {p['path']}")

    elif command == "dashboard":
        projects = list_projects()
        print(format_dashboard(projects))

    elif command == "touch":
        if len(sys.argv) < 3:
            path = os.getcwd()
        else:
            path = sys.argv[2]
        touch_project(path)
        print(f"Updated activity for: {path}")

    elif command == "tag":
        if len(sys.argv) < 4:
            print("Usage: project_registry.py tag <add|remove> <project> <tag>")
            sys.exit(1)
        action = sys.argv[2]
        project = sys.argv[3]
        tag = sys.argv[4] if len(sys.argv) > 4 else None

        if action == "add" and tag:
            add_tag(project, tag)
            print(f"Added tag '{tag}' to {project}")
        elif action == "remove" and tag:
            remove_tag(project, tag)
            print(f"Removed tag '{tag}' from {project}")
        else:
            print("Invalid tag command")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
