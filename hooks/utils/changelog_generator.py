#!/usr/bin/env python3
"""
Changelog Generator Utility
Generates version history entries for CLAUDE.md from conventional commit messages.

Part of PopKit plugin - Issue #85 (Documentation Automation Epic #81)

Usage:
    python changelog_generator.py                    # Generate for next version
    python changelog_generator.py --version 0.9.9   # Specify version
    python changelog_generator.py --since v0.9.8    # From specific tag
    python changelog_generator.py --json            # Output as JSON
    python changelog_generator.py --preview         # Preview without updating
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


# Conventional commit type to display name mapping
COMMIT_TYPES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "style": "Styling",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Testing",
    "build": "Build System",
    "ci": "CI/CD",
    "chore": "Maintenance",
    "revert": "Reverts"
}

# Priority order for changelog sections
TYPE_PRIORITY = ["feat", "fix", "perf", "refactor", "docs", "test", "ci", "build", "chore", "style", "revert"]


class ChangelogGenerator:
    """Generates changelog entries from git commits."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()

    def run_git(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                encoding="utf-8"
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_latest_tag(self) -> Optional[str]:
        """Get the most recent version tag."""
        # Try to get tags that look like versions
        tags = self.run_git(["tag", "-l", "v*", "--sort=-v:refname"])
        if tags:
            return tags.split("\n")[0]
        return None

    def get_commits_since(self, since_ref: str = None) -> List[Dict[str, Any]]:
        """Get commits since a reference (tag or commit)."""
        if since_ref:
            range_spec = f"{since_ref}..HEAD"
        else:
            # Get all commits if no tag exists
            range_spec = "HEAD"

        # Format: hash|subject|body
        log_output = self.run_git([
            "log", range_spec,
            "--pretty=format:%H|%s|%b|||COMMIT_END|||"
        ])

        if not log_output:
            return []

        commits = []
        for entry in log_output.split("|||COMMIT_END|||"):
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split("|", 2)
            if len(parts) < 2:
                continue

            commit_hash = parts[0][:7]
            subject = parts[1]
            body = parts[2] if len(parts) > 2 else ""

            parsed = self.parse_commit(subject, body)
            if parsed:
                parsed["hash"] = commit_hash
                commits.append(parsed)

        return commits

    def parse_commit(self, subject: str, body: str = "") -> Optional[Dict[str, Any]]:
        """Parse a conventional commit message."""
        # Pattern: type(scope): description
        # or: type: description
        pattern = r'^(\w+)(?:\(([^)]+)\))?:\s*(.+)$'
        match = re.match(pattern, subject)

        if not match:
            # Non-conventional commit
            return {
                "type": "other",
                "scope": None,
                "description": subject,
                "issues": self.extract_issues(subject + " " + body),
                "breaking": "BREAKING" in subject.upper() or "BREAKING" in body.upper()
            }

        commit_type = match.group(1).lower()
        scope = match.group(2)
        description = match.group(3)

        return {
            "type": commit_type,
            "scope": scope,
            "description": description,
            "issues": self.extract_issues(subject + " " + body),
            "breaking": "BREAKING" in subject.upper() or "BREAKING" in body.upper()
        }

    def extract_issues(self, text: str) -> List[int]:
        """Extract issue/PR numbers from text."""
        # Match #N patterns
        pattern = r'#(\d+)'
        matches = re.findall(pattern, text)
        return sorted(set(int(m) for m in matches))

    def group_commits(self, commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group commits by type."""
        groups = defaultdict(list)
        for commit in commits:
            groups[commit["type"]].append(commit)
        return dict(groups)

    def generate_markdown(
        self,
        version: str,
        title: str = None,
        since_ref: str = None
    ) -> str:
        """Generate CLAUDE.md version history entry."""
        commits = self.get_commits_since(since_ref)
        if not commits:
            return f"### v{version}\n\nNo changes since last release.\n"

        grouped = self.group_commits(commits)

        # Collect all issue numbers
        all_issues = set()
        for commit_list in grouped.values():
            for commit in commit_list:
                all_issues.update(commit["issues"])

        # Build the changelog
        lines = []

        # Header with title
        if title:
            lines.append(f"### v{version} (Current) - {title}")
        else:
            lines.append(f"### v{version} (Current)")
        lines.append("")

        # Feature highlights (from feat commits)
        if "feat" in grouped:
            for commit in grouped["feat"]:
                scope = commit["scope"]
                desc = commit["description"]
                issues = commit["issues"]

                # Create feature bullet
                if scope:
                    scope_display = scope.replace("-", " ").title()
                    bullet = f"- **{scope_display}**"
                else:
                    bullet = f"- **{desc.split()[0].title()}**"

                if issues:
                    issue_refs = ", ".join(f"#{i}" for i in issues)
                    bullet += f" ({issue_refs}):"
                else:
                    bullet += ":"

                lines.append(bullet)
                lines.append(f"  - {desc}")

        # Bug fixes
        if "fix" in grouped:
            lines.append("- **Bug Fixes**:")
            for commit in grouped["fix"]:
                desc = commit["description"]
                issues = commit["issues"]
                if issues:
                    issue_refs = ", ".join(f"#{i}" for i in issues)
                    lines.append(f"  - {desc} ({issue_refs})")
                else:
                    lines.append(f"  - {desc}")

        # Performance improvements
        if "perf" in grouped:
            lines.append("- **Performance**:")
            for commit in grouped["perf"]:
                lines.append(f"  - {commit['description']}")

        # Refactoring
        if "refactor" in grouped:
            lines.append("- **Refactoring**:")
            for commit in grouped["refactor"]:
                desc = commit["description"]
                issues = commit["issues"]
                if issues:
                    issue_refs = ", ".join(f"#{i}" for i in issues)
                    lines.append(f"  - {desc} ({issue_refs})")
                else:
                    lines.append(f"  - {desc}")

        # Documentation
        if "docs" in grouped:
            lines.append("- **Documentation**:")
            for commit in grouped["docs"]:
                lines.append(f"  - {commit['description']}")

        # Maintenance/Chore
        if "chore" in grouped:
            lines.append("- **Maintenance**:")
            for commit in grouped["chore"]:
                lines.append(f"  - {commit['description']}")

        # GitHub issues closed
        if all_issues:
            sorted_issues = sorted(all_issues)
            # Format as ranges where possible
            issue_str = self.format_issue_ranges(sorted_issues)
            lines.append(f"- **GitHub Issues Closed** - {issue_str}")

        lines.append("")

        return "\n".join(lines)

    def format_issue_ranges(self, issues: List[int]) -> str:
        """Format issue numbers, using ranges where consecutive."""
        if not issues:
            return ""

        ranges = []
        start = issues[0]
        end = issues[0]

        for i in issues[1:]:
            if i == end + 1:
                end = i
            else:
                if start == end:
                    ranges.append(f"#{start}")
                else:
                    ranges.append(f"#{start}-{end}")
                start = i
                end = i

        # Add last range
        if start == end:
            ranges.append(f"#{start}")
        else:
            ranges.append(f"#{start}-{end}")

        return ", ".join(ranges)

    def update_claude_md(self, version: str, title: str = None, since_ref: str = None) -> bool:
        """Update CLAUDE.md with new version entry."""
        claude_md = self.project_root / "CLAUDE.md"
        if not claude_md.exists():
            return False

        try:
            content = claude_md.read_text(encoding="utf-8")
        except IOError:
            return False

        # Generate new entry
        new_entry = self.generate_markdown(version, title, since_ref)

        # Find where to insert (after "## Version History" header and note)
        # Look for the first ### entry
        pattern = r'(## Version History\s+\*\*Note:\*\*[^\n]+\n+)'
        match = re.search(pattern, content)

        if match:
            # Insert after the header and note
            insert_pos = match.end()
            updated = content[:insert_pos] + new_entry + "\n" + content[insert_pos:]

            # Update the "(Current)" marker on old versions
            # Remove (Current) from previous version
            updated = re.sub(r'### v[\d.]+ \(Current\)', lambda m: m.group(0).replace(" (Current)", ""), updated, count=1)

            try:
                claude_md.write_text(updated, encoding="utf-8")
                return True
            except IOError:
                return False

        return False

    def to_json(self, version: str = None, since_ref: str = None) -> str:
        """Output changelog data as JSON."""
        commits = self.get_commits_since(since_ref)
        grouped = self.group_commits(commits)

        all_issues = set()
        for commit_list in grouped.values():
            for commit in commit_list:
                all_issues.update(commit["issues"])

        return json.dumps({
            "version": version,
            "since_ref": since_ref,
            "commits": commits,
            "grouped": grouped,
            "issues_closed": sorted(all_issues),
            "commit_count": len(commits)
        }, indent=2)


def main():
    """CLI entry point."""
    import argparse
    import io

    # Handle Windows encoding
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="Generate changelog from git commits")
    parser.add_argument("--version", "-v", help="Version number (e.g., 0.9.9)")
    parser.add_argument("--title", "-t", help="Release title")
    parser.add_argument("--since", "-s", help="Generate since this tag/ref")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--preview", "-p", action="store_true", help="Preview without updating")
    parser.add_argument("--update", "-u", action="store_true", help="Update CLAUDE.md")
    args = parser.parse_args()

    generator = ChangelogGenerator()

    # Get since ref (default to latest tag)
    since_ref = args.since
    if not since_ref:
        since_ref = generator.get_latest_tag()

    # Get version (default to incrementing latest tag)
    version = args.version
    if not version and since_ref:
        # Try to increment patch version
        match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', since_ref)
        if match:
            major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
            version = f"{major}.{minor}.{patch + 1}"
    if not version:
        version = "0.0.1"

    if args.json:
        print(generator.to_json(version, since_ref))
    elif args.update:
        success = generator.update_claude_md(version, args.title, since_ref)
        if success:
            print(f"Updated CLAUDE.md with v{version} changelog")
        else:
            print("Failed to update CLAUDE.md", file=sys.stderr)
            sys.exit(1)
    else:
        # Preview mode (default)
        print(f"Changelog for v{version} (since {since_ref or 'beginning'}):")
        print("=" * 50)
        print(generator.generate_markdown(version, args.title, since_ref))


if __name__ == "__main__":
    main()
