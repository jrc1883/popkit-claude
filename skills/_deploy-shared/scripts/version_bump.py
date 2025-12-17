#!/usr/bin/env python3
"""
Semantic Version Bumping.

Bump version numbers consistently across files.

Usage:
    python version_bump.py [bump_type] [--dry-run]

    bump_type: major | minor | patch | prerelease

Output:
    JSON object with version changes
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def parse_version(version: str) -> Tuple[int, int, int, Optional[str]]:
    """Parse semantic version string."""
    # Remove leading 'v' if present
    version = version.lstrip("v")

    # Match semver pattern
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(.+))?", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4)

    return major, minor, patch, prerelease


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to type."""
    major, minor, patch, prerelease = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "prerelease":
        if prerelease:
            # Increment prerelease number
            match = re.match(r"(.+?)(\d+)$", prerelease)
            if match:
                prefix, num = match.groups()
                return f"{major}.{minor}.{patch}-{prefix}{int(num) + 1}"
            else:
                return f"{major}.{minor}.{patch}-{prerelease}.1"
        else:
            return f"{major}.{minor}.{patch}-alpha.1"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


def find_version_files(project_dir: Path) -> List[Dict[str, Any]]:
    """Find files containing version numbers."""
    version_files = []

    # package.json
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            content = json.loads(pkg_json.read_text())
            version_files.append({
                "path": str(pkg_json),
                "type": "package.json",
                "version": content.get("version"),
                "pattern": r'"version"\s*:\s*"([^"]+)"'
            })
        except:
            pass

    # pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version_files.append({
                    "path": str(pyproject),
                    "type": "pyproject.toml",
                    "version": match.group(1),
                    "pattern": r'version\s*=\s*["\']([^"\']+)["\']'
                })
        except:
            pass

    # setup.py
    setup_py = project_dir / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version_files.append({
                    "path": str(setup_py),
                    "type": "setup.py",
                    "version": match.group(1),
                    "pattern": r'version\s*=\s*["\']([^"\']+)["\']'
                })
        except:
            pass

    # __version__ in Python
    for py_file in project_dir.glob("*/__init__.py"):
        try:
            content = py_file.read_text()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version_files.append({
                    "path": str(py_file),
                    "type": "python __version__",
                    "version": match.group(1),
                    "pattern": r'__version__\s*=\s*["\']([^"\']+)["\']'
                })
        except:
            pass

    # plugin.json (PopKit specific)
    plugin_json = project_dir / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            content = json.loads(plugin_json.read_text())
            version_files.append({
                "path": str(plugin_json),
                "type": "plugin.json",
                "version": content.get("version"),
                "pattern": r'"version"\s*:\s*"([^"]+)"'
            })
        except:
            pass

    # marketplace.json (PopKit specific)
    marketplace_json = project_dir / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            content = json.loads(marketplace_json.read_text())
            version_files.append({
                "path": str(marketplace_json),
                "type": "marketplace.json",
                "version": content.get("version"),
                "pattern": r'"version"\s*:\s*"([^"]+)"'
            })
        except:
            pass

    return version_files


def update_file_version(file_info: Dict[str, Any], new_version: str, dry_run: bool = False) -> bool:
    """Update version in a single file."""
    path = Path(file_info["path"])
    pattern = file_info["pattern"]
    old_version = file_info["version"]

    try:
        content = path.read_text()

        if file_info["type"] in ["package.json", "plugin.json", "marketplace.json"]:
            # JSON files - use proper JSON handling
            data = json.loads(content)
            data["version"] = new_version
            new_content = json.dumps(data, indent=2) + "\n"
        else:
            # Text files - use regex replacement
            def replacer(match):
                return match.group(0).replace(old_version, new_version)
            new_content = re.sub(pattern, replacer, content)

        if not dry_run:
            path.write_text(new_content)

        return True
    except Exception as e:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bump semantic version")
    parser.add_argument("bump_type", nargs="?", default="patch",
                       choices=["major", "minor", "patch", "prerelease"],
                       help="Type of version bump")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would change without making changes")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Find all version files
    version_files = find_version_files(project_dir)

    if not version_files:
        print(json.dumps({"error": "No version files found"}))
        return 1

    # Get current version (use first file as source of truth)
    current_version = version_files[0]["version"]

    # Calculate new version
    try:
        new_version = bump_version(current_version, args.bump_type)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1

    # Update all files
    results = []
    for file_info in version_files:
        success = update_file_version(file_info, new_version, args.dry_run)
        results.append({
            "path": file_info["path"],
            "type": file_info["type"],
            "old_version": file_info["version"],
            "new_version": new_version,
            "updated": success
        })

    report = {
        "operation": "version_bump",
        "bump_type": args.bump_type,
        "dry_run": args.dry_run,
        "current_version": current_version,
        "new_version": new_version,
        "files_updated": results,
        "success": all(r["updated"] for r in results)
    }

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
