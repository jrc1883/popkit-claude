#!/usr/bin/env python3
"""
Workspace Configuration Loader

Detects and parses monorepo workspace configurations:
- pnpm-workspace.yaml (pnpm workspaces)
- package.json workspaces (npm/yarn)
- lerna.json (Lerna monorepo)
- .claude/workspace.json (PopKit custom config)

Part of the popkit plugin system.
"""

import os
import json
import glob
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


# =============================================================================
# Workspace Detection
# =============================================================================

def find_workspace_root(start_path: str) -> Optional[str]:
    """Walk up directory tree to find workspace root.

    Args:
        start_path: Starting directory path

    Returns:
        Path to workspace root or None if not in workspace
    """
    current = os.path.abspath(start_path)

    while True:
        # Check for workspace markers
        if (os.path.isfile(os.path.join(current, "pnpm-workspace.yaml")) or
            os.path.isfile(os.path.join(current, "lerna.json")) or
            os.path.isfile(os.path.join(current, ".claude", "workspace.json"))):
            return current

        # Check for package.json with workspaces field
        package_json = os.path.join(current, "package.json")
        if os.path.isfile(package_json):
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "workspaces" in data:
                        return current
            except (json.JSONDecodeError, IOError):
                pass

        # Move up one directory
        parent = os.path.dirname(current)
        if parent == current:  # Reached root
            return None
        current = parent


def detect_workspace_type(workspace_root: str) -> Optional[str]:
    """Detect workspace type.

    Args:
        workspace_root: Path to workspace root

    Returns:
        Workspace type: 'pnpm', 'npm', 'yarn', 'lerna', 'popkit', or None
    """
    if os.path.isfile(os.path.join(workspace_root, "pnpm-workspace.yaml")):
        return "pnpm"

    if os.path.isfile(os.path.join(workspace_root, "lerna.json")):
        return "lerna"

    if os.path.isfile(os.path.join(workspace_root, ".claude", "workspace.json")):
        return "popkit"

    package_json = os.path.join(workspace_root, "package.json")
    if os.path.isfile(package_json):
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "workspaces" in data:
                    # Detect pnpm vs npm/yarn by lock file
                    if os.path.isfile(os.path.join(workspace_root, "pnpm-lock.yaml")):
                        return "pnpm"
                    elif os.path.isfile(os.path.join(workspace_root, "yarn.lock")):
                        return "yarn"
                    else:
                        return "npm"
        except (json.JSONDecodeError, IOError):
            pass

    return None


# =============================================================================
# Workspace Config Parsers
# =============================================================================

def parse_pnpm_workspace(workspace_root: str) -> List[str]:
    """Parse pnpm-workspace.yaml to get workspace patterns.

    Args:
        workspace_root: Path to workspace root

    Returns:
        List of workspace glob patterns
    """
    yaml_path = os.path.join(workspace_root, "pnpm-workspace.yaml")

    if not os.path.isfile(yaml_path):
        return []

    try:
        # Simple YAML parsing for the packages list
        # This avoids dependency on PyYAML
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        patterns = []
        in_packages = False

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("packages:"):
                in_packages = True
                continue

            if in_packages:
                if line.startswith("-"):
                    # Extract pattern from "- 'pattern'" or '- "pattern"'
                    pattern = line[1:].strip().strip("'\"")
                    if pattern:
                        patterns.append(pattern)
                elif line and not line.startswith("#"):
                    # End of packages section
                    break

        return patterns

    except IOError:
        return []


def parse_package_json_workspaces(workspace_root: str) -> List[str]:
    """Parse package.json workspaces field.

    Args:
        workspace_root: Path to workspace root

    Returns:
        List of workspace glob patterns
    """
    package_json = os.path.join(workspace_root, "package.json")

    if not os.path.isfile(package_json):
        return []

    try:
        with open(package_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        workspaces = data.get("workspaces", [])

        # Handle both array and object format
        if isinstance(workspaces, list):
            return workspaces
        elif isinstance(workspaces, dict):
            return workspaces.get("packages", [])

        return []

    except (json.JSONDecodeError, IOError):
        return []


def parse_lerna_json(workspace_root: str) -> List[str]:
    """Parse lerna.json to get workspace patterns.

    Args:
        workspace_root: Path to workspace root

    Returns:
        List of workspace glob patterns
    """
    lerna_json = os.path.join(workspace_root, "lerna.json")

    if not os.path.isfile(lerna_json):
        return []

    try:
        with open(lerna_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("packages", ["packages/*"])

    except (json.JSONDecodeError, IOError):
        return []


def parse_popkit_workspace(workspace_root: str) -> Dict[str, Any]:
    """Parse .claude/workspace.json configuration.

    Args:
        workspace_root: Path to workspace root

    Returns:
        Workspace configuration dict
    """
    config_path = os.path.join(workspace_root, ".claude", "workspace.json")

    if not os.path.isfile(config_path):
        return {"apps": []}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"apps": []}


# =============================================================================
# Project Discovery
# =============================================================================

def resolve_workspace_patterns(workspace_root: str, patterns: List[str]) -> List[str]:
    """Resolve glob patterns to actual directory paths.

    Args:
        workspace_root: Path to workspace root
        patterns: List of glob patterns

    Returns:
        List of resolved directory paths
    """
    resolved = []

    for pattern in patterns:
        # Handle negation patterns (starting with !)
        if pattern.startswith("!"):
            continue

        # Resolve glob pattern
        full_pattern = os.path.join(workspace_root, pattern)
        matches = glob.glob(full_pattern)

        # Filter to directories only
        for match in matches:
            if os.path.isdir(match):
                resolved.append(os.path.abspath(match))

    return sorted(set(resolved))


def get_workspace_projects(workspace_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all projects in the workspace.

    Args:
        workspace_root: Path to workspace root (auto-detected if None)

    Returns:
        List of project info dicts with name, path, type
    """
    if workspace_root is None:
        workspace_root = find_workspace_root(os.getcwd())

    if workspace_root is None:
        return []

    workspace_type = detect_workspace_type(workspace_root)

    if workspace_type is None:
        return []

    # Get patterns based on workspace type
    if workspace_type == "popkit":
        config = parse_popkit_workspace(workspace_root)
        # PopKit config has explicit app list
        projects = []
        for app in config.get("apps", []):
            app_path = os.path.join(workspace_root, app.get("path", ""))
            if os.path.isdir(app_path):
                projects.append({
                    "name": app.get("name", os.path.basename(app_path)),
                    "path": app_path,
                    "type": app.get("tier", "unknown"),
                    "description": app.get("description", "")
                })
        return projects

    # Get patterns for other workspace types
    if workspace_type == "pnpm":
        patterns = parse_pnpm_workspace(workspace_root)
    elif workspace_type in ("npm", "yarn"):
        patterns = parse_package_json_workspaces(workspace_root)
    elif workspace_type == "lerna":
        patterns = parse_lerna_json(workspace_root)
    else:
        patterns = []

    # Resolve patterns to actual directories
    project_dirs = resolve_workspace_patterns(workspace_root, patterns)

    # Build project info
    projects = []
    for project_dir in project_dirs:
        name = os.path.basename(project_dir)

        # Try to get name from package.json
        package_json = os.path.join(project_dir, "package.json")
        description = ""

        if os.path.isfile(package_json):
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = data.get("name", name)
                    description = data.get("description", "")
            except (json.JSONDecodeError, IOError):
                pass

        projects.append({
            "name": name,
            "path": project_dir,
            "type": workspace_type,
            "description": description
        })

    return projects


def find_project_by_name(name: str, workspace_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find a project by name in the workspace.

    Args:
        name: Project name to find
        workspace_root: Path to workspace root (auto-detected if None)

    Returns:
        Project info dict or None if not found
    """
    projects = get_workspace_projects(workspace_root)
    name_lower = name.lower()

    for project in projects:
        if project["name"].lower() == name_lower:
            return project
        # Also check basename of path
        if os.path.basename(project["path"]).lower() == name_lower:
            return project

    return None


# =============================================================================
# Project Context Loading
# =============================================================================

def load_project_context(project_path: str) -> Dict[str, Optional[str]]:
    """Load context files from a project.

    Args:
        project_path: Path to project directory

    Returns:
        Dict with file contents: claude_md, package_json, readme, status
    """
    context = {
        "claude_md": None,
        "package_json": None,
        "readme": None,
        "status": None
    }

    # Load CLAUDE.md
    claude_md_path = os.path.join(project_path, "CLAUDE.md")
    if os.path.isfile(claude_md_path):
        try:
            with open(claude_md_path, "r", encoding="utf-8") as f:
                context["claude_md"] = f.read()
        except IOError:
            pass

    # Load package.json
    package_json_path = os.path.join(project_path, "package.json")
    if os.path.isfile(package_json_path):
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                context["package_json"] = f.read()
        except IOError:
            pass

    # Load README.md
    readme_path = os.path.join(project_path, "README.md")
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                context["readme"] = f.read()
        except IOError:
            pass

    # Load .claude/STATUS.json
    status_path = os.path.join(project_path, ".claude", "STATUS.json")
    if os.path.isfile(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                context["status"] = f.read()
        except IOError:
            pass

    return context


def format_project_context(project_name: str, project_path: str, context: Dict[str, Optional[str]]) -> str:
    """Format project context for display.

    Args:
        project_name: Project name
        project_path: Project path
        context: Context dict from load_project_context

    Returns:
        Formatted context string
    """
    lines = []

    lines.append("")
    lines.append("=" * 67)
    lines.append(f"Project: {project_name}".center(67))
    lines.append("=" * 67)
    lines.append("")
    lines.append(f"Path: {project_path}")
    lines.append("")

    # CLAUDE.md
    if context["claude_md"]:
        lines.append("-" * 67)
        lines.append("CLAUDE.md")
        lines.append("-" * 67)
        lines.append(context["claude_md"])
        lines.append("")

    # package.json
    if context["package_json"]:
        lines.append("-" * 67)
        lines.append("package.json")
        lines.append("-" * 67)
        lines.append(context["package_json"])
        lines.append("")

    # README.md
    if context["readme"]:
        lines.append("-" * 67)
        lines.append("README.md")
        lines.append("-" * 67)
        lines.append(context["readme"])
        lines.append("")

    # STATUS.json
    if context["status"]:
        lines.append("-" * 67)
        lines.append(".claude/STATUS.json")
        lines.append("-" * 67)
        lines.append(context["status"])
        lines.append("")

    lines.append("=" * 67)
    lines.append("")
    lines.append(f"Context loaded. You can now ask questions about {project_name}")
    lines.append("without leaving your current directory.")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    # Fix Windows console encoding for Unicode output
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')

    if len(sys.argv) < 2:
        print("Usage: workspace_config.py <command> [args]")
        print("Commands: detect, list, find, load")
        sys.exit(1)

    command = sys.argv[1]

    if command == "detect":
        # Detect workspace root and type
        cwd = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        root = find_workspace_root(cwd)

        if root:
            ws_type = detect_workspace_type(root)
            print(f"Workspace root: {root}")
            print(f"Workspace type: {ws_type}")
        else:
            print("Not in a workspace")
            sys.exit(1)

    elif command == "list":
        # List all projects
        projects = get_workspace_projects()

        if projects:
            print(f"Found {len(projects)} projects:")
            for p in projects:
                print(f"  - {p['name']}: {p['path']}")
                if p.get('description'):
                    print(f"    {p['description']}")
        else:
            print("No projects found or not in a workspace")

    elif command == "find":
        # Find specific project
        if len(sys.argv) < 3:
            print("Usage: workspace_config.py find <name>")
            sys.exit(1)

        name = sys.argv[2]
        project = find_project_by_name(name)

        if project:
            print(f"Found project: {project['name']}")
            print(f"Path: {project['path']}")
            if project.get('description'):
                print(f"Description: {project['description']}")
        else:
            print(f"Project '{name}' not found")
            sys.exit(1)

    elif command == "load":
        # Load project context
        if len(sys.argv) < 3:
            print("Usage: workspace_config.py load <name>")
            sys.exit(1)

        name = sys.argv[2]
        project = find_project_by_name(name)

        if not project:
            print(f"Project '{name}' not found")
            sys.exit(1)

        context = load_project_context(project['path'])
        output = format_project_context(project['name'], project['path'], context)
        print(output)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
