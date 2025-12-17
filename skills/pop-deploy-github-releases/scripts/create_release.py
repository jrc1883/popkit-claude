#!/usr/bin/env python3
"""
GitHub Release Creation Script.

Create GitHub releases with automated changelog and asset uploads.

Usage:
    python create_release.py TAG [--title TITLE] [--notes NOTES] [--draft] [--prerelease]

Output:
    JSON object with release details
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_previous_tag() -> Optional[str]:
    """Get the previous release tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def get_commits_since_tag(tag: str) -> List[Dict[str, str]]:
    """Get commits since the specified tag."""
    try:
        result = subprocess.run(
            ["git", "log", f"{tag}..HEAD", "--pretty=format:%H|%s|%an"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 2)
                if len(parts) >= 2:
                    commits.append({
                        "sha": parts[0][:8],
                        "message": parts[1],
                        "author": parts[2] if len(parts) > 2 else "Unknown"
                    })
        return commits
    except:
        return []


def categorize_commits(commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize commits by conventional commit type."""
    categories = {
        "breaking": [],
        "features": [],
        "fixes": [],
        "docs": [],
        "chore": [],
        "other": []
    }

    for commit in commits:
        msg = commit["message"].lower()
        if msg.startswith("feat!") or "breaking" in msg:
            categories["breaking"].append(commit)
        elif msg.startswith("feat"):
            categories["features"].append(commit)
        elif msg.startswith("fix"):
            categories["fixes"].append(commit)
        elif msg.startswith("docs"):
            categories["docs"].append(commit)
        elif msg.startswith("chore") or msg.startswith("refactor") or msg.startswith("style"):
            categories["chore"].append(commit)
        else:
            categories["other"].append(commit)

    return categories


def generate_release_notes(tag: str, categories: Dict[str, List[Dict[str, str]]]) -> str:
    """Generate release notes from categorized commits."""
    notes = []

    if categories["breaking"]:
        notes.append("## ⚠️ Breaking Changes\n")
        for commit in categories["breaking"]:
            notes.append(f"- {commit['message']} ({commit['sha']})")
        notes.append("")

    if categories["features"]:
        notes.append("## ✨ Features\n")
        for commit in categories["features"]:
            notes.append(f"- {commit['message']} ({commit['sha']})")
        notes.append("")

    if categories["fixes"]:
        notes.append("## 🐛 Bug Fixes\n")
        for commit in categories["fixes"]:
            notes.append(f"- {commit['message']} ({commit['sha']})")
        notes.append("")

    if categories["docs"]:
        notes.append("## 📚 Documentation\n")
        for commit in categories["docs"]:
            notes.append(f"- {commit['message']} ({commit['sha']})")
        notes.append("")

    if categories["chore"]:
        notes.append("## 🔧 Maintenance\n")
        for commit in categories["chore"]:
            notes.append(f"- {commit['message']} ({commit['sha']})")
        notes.append("")

    if not any(categories.values()):
        notes.append("No notable changes in this release.")

    return "\n".join(notes)


def create_release(
    tag: str,
    title: str = None,
    notes: str = None,
    draft: bool = False,
    prerelease: bool = False,
    assets: List[str] = None
) -> Dict[str, Any]:
    """Create a GitHub release."""

    # Build command
    cmd = ["gh", "release", "create", tag]

    if title:
        cmd.extend(["--title", title])
    else:
        cmd.extend(["--title", f"Release {tag}"])

    if notes:
        cmd.extend(["--notes", notes])
    else:
        cmd.append("--generate-notes")

    if draft:
        cmd.append("--draft")

    if prerelease:
        cmd.append("--prerelease")

    # Add assets
    if assets:
        for asset in assets:
            if Path(asset).exists():
                cmd.append(asset)

    # Execute
    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        # Get release URL from output
        release_url = result.stdout.strip()
        return {
            "success": True,
            "tag": tag,
            "title": title or f"Release {tag}",
            "url": release_url,
            "draft": draft,
            "prerelease": prerelease,
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "tag": tag,
            "error": result.stderr.strip()
        }


def get_release_info(tag: str) -> Optional[Dict[str, Any]]:
    """Get information about an existing release."""
    try:
        result = subprocess.run(
            ["gh", "release", "view", tag, "--json", "tagName,name,isDraft,isPrerelease,createdAt,url"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except:
        pass
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create GitHub release")
    parser.add_argument("tag", help="Release tag (e.g., v1.0.0)")
    parser.add_argument("--title", help="Release title")
    parser.add_argument("--notes", help="Release notes (or path to file)")
    parser.add_argument("--draft", action="store_true", help="Create as draft")
    parser.add_argument("--prerelease", action="store_true", help="Mark as pre-release")
    parser.add_argument("--assets", nargs="+", help="Assets to upload")
    parser.add_argument("--auto-notes", action="store_true", help="Auto-generate notes from commits")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    args = parser.parse_args()

    # Generate notes if requested
    notes = args.notes
    if args.auto_notes:
        prev_tag = get_previous_tag()
        if prev_tag:
            commits = get_commits_since_tag(prev_tag)
            categories = categorize_commits(commits)
            notes = generate_release_notes(args.tag, categories)
        else:
            notes = "Initial release."

    # If notes is a file path, read it
    if notes and Path(notes).exists():
        notes = Path(notes).read_text()

    if args.dry_run:
        print(json.dumps({
            "operation": "github_release",
            "dry_run": True,
            "tag": args.tag,
            "title": args.title or f"Release {args.tag}",
            "draft": args.draft,
            "prerelease": args.prerelease,
            "notes_preview": notes[:500] if notes else "(auto-generated)",
            "assets": args.assets or []
        }, indent=2))
        return 0

    # Create release
    result = create_release(
        tag=args.tag,
        title=args.title,
        notes=notes,
        draft=args.draft,
        prerelease=args.prerelease,
        assets=args.assets
    )

    print(json.dumps({
        "operation": "github_release",
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
