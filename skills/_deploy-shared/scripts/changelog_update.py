#!/usr/bin/env python3
"""
Changelog Update Script.

Generate and update changelog entries.

Usage:
    python changelog_update.py [version] [--generate] [--dry-run]

Output:
    JSON object with changelog updates
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / "CHANGELOG.md").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def get_commits_since_tag(project_dir: Path) -> List[Dict[str, str]]:
    """Get commits since the last tag."""
    try:
        # Get last tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        last_tag = result.stdout.strip() if result.returncode == 0 else ""

        # Get commits since tag (or all commits if no tag)
        if last_tag:
            cmd = ["git", "log", f"{last_tag}..HEAD", "--pretty=format:%h|%s|%an|%ad", "--date=short"]
        else:
            cmd = ["git", "log", "--pretty=format:%h|%s|%an|%ad", "--date=short", "-50"]

        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3]
                    })

        return commits
    except Exception as e:
        return []


def categorize_commits(commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize commits by type (conventional commits)."""
    categories = {
        "breaking": [],
        "features": [],
        "fixes": [],
        "docs": [],
        "chore": [],
        "other": []
    }

    for commit in commits:
        message = commit["message"].lower()

        if "!" in message.split(":")[0] or "breaking" in message:
            categories["breaking"].append(commit)
        elif message.startswith("feat"):
            categories["features"].append(commit)
        elif message.startswith("fix"):
            categories["fixes"].append(commit)
        elif message.startswith("docs"):
            categories["docs"].append(commit)
        elif message.startswith(("chore", "ci", "build", "test", "refactor")):
            categories["chore"].append(commit)
        else:
            categories["other"].append(commit)

    return categories


def generate_changelog_entry(version: str, categories: Dict[str, List[Dict]]) -> str:
    """Generate a changelog entry for a version."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## [{version}] - {today}", ""]

    if categories["breaking"]:
        lines.append("### Breaking Changes")
        lines.append("")
        for commit in categories["breaking"]:
            lines.append(f"- {commit['message']} ({commit['hash']})")
        lines.append("")

    if categories["features"]:
        lines.append("### Features")
        lines.append("")
        for commit in categories["features"]:
            # Clean up message
            msg = re.sub(r"^feat(\([^)]+\))?:\s*", "", commit["message"])
            lines.append(f"- {msg} ({commit['hash']})")
        lines.append("")

    if categories["fixes"]:
        lines.append("### Bug Fixes")
        lines.append("")
        for commit in categories["fixes"]:
            msg = re.sub(r"^fix(\([^)]+\))?:\s*", "", commit["message"])
            lines.append(f"- {msg} ({commit['hash']})")
        lines.append("")

    if categories["docs"]:
        lines.append("### Documentation")
        lines.append("")
        for commit in categories["docs"]:
            msg = re.sub(r"^docs(\([^)]+\))?:\s*", "", commit["message"])
            lines.append(f"- {msg} ({commit['hash']})")
        lines.append("")

    if categories["chore"]:
        lines.append("### Maintenance")
        lines.append("")
        for commit in categories["chore"]:
            msg = re.sub(r"^(chore|ci|build|test|refactor)(\([^)]+\))?:\s*", "", commit["message"])
            lines.append(f"- {msg} ({commit['hash']})")
        lines.append("")

    return "\n".join(lines)


def update_changelog(project_dir: Path, entry: str, dry_run: bool = False) -> bool:
    """Update CHANGELOG.md with new entry."""
    changelog_path = project_dir / "CHANGELOG.md"

    if changelog_path.exists():
        content = changelog_path.read_text()

        # Find insertion point (after header, before first version)
        match = re.search(r"(# Changelog.*?\n\n)", content, re.DOTALL)
        if match:
            header = match.group(1)
            rest = content[len(header):]
            new_content = header + entry + "\n" + rest
        else:
            # No header found, prepend
            new_content = f"# Changelog\n\n{entry}\n{content}"
    else:
        # Create new changelog
        new_content = f"# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n{entry}"

    if not dry_run:
        changelog_path.write_text(new_content)

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Update changelog")
    parser.add_argument("version", nargs="?", help="Version number")
    parser.add_argument("--generate", action="store_true",
                       help="Generate entry from commits")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would change")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    # Get version
    version = args.version
    if not version:
        # Try to read from package.json
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            version = pkg.get("version", "0.0.0")
        else:
            version = "0.0.0"

    if args.generate:
        # Generate from commits
        commits = get_commits_since_tag(project_dir)
        categories = categorize_commits(commits)
        entry = generate_changelog_entry(version, categories)

        success = update_changelog(project_dir, entry, args.dry_run)

        report = {
            "operation": "changelog_update",
            "version": version,
            "dry_run": args.dry_run,
            "commits_processed": len(commits),
            "categories": {k: len(v) for k, v in categories.items()},
            "entry_preview": entry[:500] + "..." if len(entry) > 500 else entry,
            "success": success
        }
    else:
        # Just report current state
        commits = get_commits_since_tag(project_dir)
        categories = categorize_commits(commits)

        report = {
            "operation": "changelog_preview",
            "version": version,
            "commits_since_last_tag": len(commits),
            "categories": {k: len(v) for k, v in categories.items()},
            "commits": commits[:10]
        }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
