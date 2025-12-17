#!/usr/bin/env python3
"""
Research Branch Detector Utility

Detects and processes research branches created by Claude Code Web sessions.
Part of issue #181: Auto-Process Research Branches in /popkit:next

Patterns detected:
- origin/claude/research-*
- origin/claude/*-research-*
- Branches with research docs (*.md in root or docs/research/)
"""

import subprocess
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class ResearchBranch:
    """Represents a detected research branch."""
    full_name: str  # e.g., origin/claude/research-claude-code-features-01Wp...
    short_name: str  # e.g., research-claude-code-features
    topic: str  # e.g., claude-code-features
    created_ago: str  # e.g., "2 hours ago"
    commit_count: int
    files_changed: List[str]
    has_docs: bool
    doc_paths: List[str]


def run_git(args: List[str], check: bool = False) -> Tuple[bool, str]:
    """Run a git command and return success status and output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        if check and result.returncode != 0:
            return False, result.stderr
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def fetch_remotes() -> bool:
    """Fetch all remotes and prune deleted branches."""
    success, _ = run_git(["fetch", "--all", "--prune"])
    return success


def get_research_branches() -> List[ResearchBranch]:
    """
    Detect research branches matching known patterns.

    Patterns:
    1. origin/claude/research-*
    2. origin/claude/*-research-*
    3. Any branch with docs/research/*.md or RESEARCH*.md
    """
    branches: List[ResearchBranch] = []

    # Get all remote branches
    success, output = run_git(["branch", "-r", "--format=%(refname:short)"])
    if not success:
        return branches

    all_remotes = output.split("\n") if output else []

    # Pattern 1 & 2: Claude research branches
    research_patterns = [
        r"origin/claude/research-(.+)",
        r"origin/claude/(.+)-research-(.+)",
    ]

    for branch in all_remotes:
        branch = branch.strip()
        if not branch:
            continue

        # Check pattern matches
        for pattern in research_patterns:
            match = re.match(pattern, branch)
            if match:
                research_branch = _analyze_branch(branch, match)
                if research_branch:
                    branches.append(research_branch)
                break

    return branches


def _analyze_branch(full_name: str, match: re.Match) -> Optional[ResearchBranch]:
    """Analyze a branch to extract research information."""

    # Extract topic from match groups
    groups = match.groups()
    if len(groups) == 1:
        topic = groups[0]
    else:
        topic = "-".join(groups)

    # Remove session ID suffix (e.g., -01WpyQzGrNeGx7cSNqM91iqP)
    topic_clean = re.sub(r"-[A-Za-z0-9]{20,}$", "", topic)

    # Get commit info
    success, commit_time = run_git([
        "log", "-1", "--format=%ar", full_name
    ])
    created_ago = commit_time if success else "unknown"

    # Get commit count ahead of master
    success, count = run_git([
        "rev-list", "--count", f"master..{full_name}"
    ])
    commit_count = int(count) if success and count.isdigit() else 0

    # Get files changed
    success, diff_stat = run_git([
        "diff", "--stat", "--name-only", f"master...{full_name}"
    ])
    files_changed = diff_stat.split("\n") if success and diff_stat else []
    files_changed = [f.strip() for f in files_changed if f.strip()]

    # Detect doc files
    doc_patterns = [
        r"docs/research/.*\.md",
        r"docs/.*RESEARCH.*\.md",
        r"RESEARCH.*\.md",
        r".*_RESEARCH\.md",
    ]

    doc_paths = []
    for f in files_changed:
        for pattern in doc_patterns:
            if re.match(pattern, f, re.IGNORECASE):
                doc_paths.append(f)
                break

    has_docs = len(doc_paths) > 0 or any("docs" in f.lower() for f in files_changed)

    # Generate short name
    short_name = full_name.replace("origin/claude/", "").replace("origin/", "")
    short_name = re.sub(r"-[A-Za-z0-9]{20,}$", "", short_name)  # Remove session ID

    return ResearchBranch(
        full_name=full_name,
        short_name=short_name,
        topic=topic_clean,
        created_ago=created_ago,
        commit_count=commit_count,
        files_changed=files_changed,
        has_docs=has_docs,
        doc_paths=doc_paths
    )


def format_branch_table(branches: List[ResearchBranch]) -> str:
    """Format research branches as a markdown table."""
    if not branches:
        return "No research branches detected."

    lines = [
        "| Branch | Topic | Created | Files |",
        "|--------|-------|---------|-------|"
    ]

    for b in branches:
        files_summary = f"{len(b.files_changed)} files"
        if b.has_docs:
            files_summary += " (has docs)"
        lines.append(f"| `{b.short_name}` | {b.topic} | {b.created_ago} | {files_summary} |")

    return "\n".join(lines)


def get_branch_content_preview(branch: ResearchBranch, max_lines: int = 50) -> Dict[str, str]:
    """Get preview of doc content from a research branch."""
    previews = {}

    for doc_path in branch.doc_paths[:3]:  # Limit to 3 docs
        success, content = run_git([
            "show", f"{branch.full_name}:{doc_path}"
        ])
        if success:
            lines = content.split("\n")[:max_lines]
            previews[doc_path] = "\n".join(lines)

    return previews


def parse_research_doc(content: str) -> Dict[str, str]:
    """
    Parse a research document to extract structured information.

    Expected format:
    # Research: [Topic Name]

    **Research Date:** YYYY-MM-DD
    **Status:** Research Document
    **Priority:** P1-high | P2-medium | P3-low

    ## Executive Summary
    [This becomes the issue body]

    ## Implementation Tasks
    - [ ] Task 1
    - [ ] Task 2
    """
    result = {
        "title": "",
        "date": "",
        "priority": "P2-medium",
        "summary": "",
        "tasks": [],
        "raw_content": content
    }

    lines = content.split("\n")

    # Extract title
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            # Clean up "Research: " prefix
            title = re.sub(r"^Research:\s*", "", title)
            result["title"] = title
            break

    # Extract metadata
    for line in lines:
        if "**Research Date:**" in line or "**Date:**" in line or "Date:" in line:
            match = re.search(r"(\d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d{1,2}, \d{4})", line)
            if match:
                result["date"] = match.group(0)
        elif "**Priority:**" in line:
            match = re.search(r"P[0-3]-(critical|high|medium|low)", line, re.IGNORECASE)
            if match:
                result["priority"] = match.group(0)

    # Extract executive summary
    in_summary = False
    summary_lines = []
    for line in lines:
        if "## Executive Summary" in line:
            in_summary = True
            continue
        elif in_summary and line.startswith("## "):
            break
        elif in_summary:
            summary_lines.append(line)

    result["summary"] = "\n".join(summary_lines).strip()

    # Extract implementation tasks
    in_tasks = False
    for line in lines:
        if "## Implementation" in line or "## Tasks" in line:
            in_tasks = True
            continue
        elif in_tasks and line.startswith("## "):
            break
        elif in_tasks:
            task_match = re.match(r"^\s*-\s*\[[ x]\]\s*(.+)", line)
            if task_match:
                result["tasks"].append(task_match.group(1))

    return result


def generate_issue_body(branch: ResearchBranch, parsed_docs: List[Dict[str, str]]) -> str:
    """Generate a GitHub issue body from research branch content."""

    # Use first doc for primary content
    primary = parsed_docs[0] if parsed_docs else {}

    body_parts = [
        f"## Summary",
        "",
        primary.get("summary", "Research findings from Claude Code Web session."),
        "",
        f"## Source",
        f"- **Branch:** `{branch.full_name}`",
        f"- **Created:** {branch.created_ago}",
        f"- **Files:** {len(branch.files_changed)} changed",
    ]

    if branch.doc_paths:
        body_parts.extend([
            "",
            "## Documentation",
            "",
        ])
        for path in branch.doc_paths:
            body_parts.append(f"- `{path}`")

    tasks = primary.get("tasks", [])
    if tasks:
        body_parts.extend([
            "",
            "## Implementation Tasks",
            "",
        ])
        for task in tasks:
            body_parts.append(f"- [ ] {task}")

    body_parts.extend([
        "",
        "---",
        "*Auto-generated from research branch by PopKit*"
    ])

    return "\n".join(body_parts)


# CLI interface for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: research_branch_detector.py <command>")
        print("Commands: detect, preview <branch>, parse <file>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "detect":
        print("Fetching remotes...")
        fetch_remotes()
        branches = get_research_branches()
        print(format_branch_table(branches))

    elif command == "preview" and len(sys.argv) > 2:
        branch_name = sys.argv[2]
        fetch_remotes()
        branches = get_research_branches()
        for b in branches:
            if branch_name in b.full_name or branch_name in b.short_name:
                print(f"Branch: {b.full_name}")
                print(f"Topic: {b.topic}")
                print(f"Created: {b.created_ago}")
                print(f"Files: {b.files_changed}")
                print("\nDoc previews:")
                previews = get_branch_content_preview(b)
                for path, content in previews.items():
                    print(f"\n--- {path} ---")
                    print(content)
                break
        else:
            print(f"Branch '{branch_name}' not found")

    elif command == "parse" and len(sys.argv) > 2:
        with open(sys.argv[2], "r") as f:
            content = f.read()
        result = parse_research_doc(content)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
