#!/usr/bin/env python3
"""
Project State Analysis Script.

Analyze current project state for next action recommendations.

Usage:
    python analyze_state.py [--section SECTION]

Sections:
    git      - Git repository status
    code     - Code quality (TypeScript, lint)
    issues   - GitHub issues
    research - Research branches
    all      - All sections

Output:
    JSON object with project state analysis
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def run_command(cmd: str, timeout: int = 30) -> Tuple[str, bool]:
    """Run a shell command and return output and success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.returncode == 0
    except subprocess.TimeoutExpired:
        return "Command timed out", False
    except Exception as e:
        return str(e), False


def analyze_git_state() -> Dict[str, Any]:
    """Analyze git repository state."""
    state = {
        "is_repo": True,
        "branch": "",
        "uncommitted_count": 0,
        "uncommitted_files": [],
        "ahead_count": 0,
        "behind_count": 0,
        "recent_commits": [],
        "urgency": "LOW"
    }

    # Check if git repo
    _, is_repo = run_command("git rev-parse --git-dir 2>/dev/null")
    if not is_repo:
        state["is_repo"] = False
        return state

    # Get branch
    branch, ok = run_command("git branch --show-current")
    if ok:
        state["branch"] = branch

    # Get uncommitted changes
    status, ok = run_command("git status --porcelain")
    if ok and status:
        files = [l[3:].strip() for l in status.split('\n') if l.strip()]
        state["uncommitted_count"] = len(files)
        state["uncommitted_files"] = files[:5]  # First 5

        if len(files) > 0:
            state["urgency"] = "HIGH"

    # Get ahead/behind
    ahead_behind, ok = run_command("git rev-list --left-right --count @{u}...HEAD 2>/dev/null")
    if ok and '\t' in ahead_behind:
        parts = ahead_behind.split('\t')
        state["behind_count"] = int(parts[0]) if parts[0].isdigit() else 0
        state["ahead_count"] = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

        if state["ahead_count"] > 0:
            state["urgency"] = max(state["urgency"], "MEDIUM")

    # Get recent commits
    commits, ok = run_command("git log --oneline -5")
    if ok:
        state["recent_commits"] = commits.split('\n')[:5]

    return state


def analyze_code_state() -> Dict[str, Any]:
    """Analyze code quality state."""
    state = {
        "has_typescript": False,
        "typescript_errors": 0,
        "has_lint": False,
        "lint_errors": 0,
        "urgency": "LOW"
    }

    # Check for TypeScript
    if Path("tsconfig.json").exists():
        state["has_typescript"] = True

        # Run typecheck
        output, ok = run_command("npx tsc --noEmit 2>&1 | grep -c 'error TS' || echo 0", timeout=60)
        try:
            state["typescript_errors"] = int(output.strip())
        except ValueError:
            state["typescript_errors"] = 0 if ok else -1

        if state["typescript_errors"] > 0:
            state["urgency"] = "HIGH"

    # Check for lint
    if Path("package.json").exists():
        pkg_content = Path("package.json").read_text()
        if "eslint" in pkg_content or '"lint"' in pkg_content:
            state["has_lint"] = True

    return state


def analyze_issues() -> Dict[str, Any]:
    """Analyze GitHub issues."""
    state = {
        "has_gh": False,
        "open_count": 0,
        "issues": [],
        "urgency": "LOW"
    }

    # Check for gh CLI
    _, has_gh = run_command("gh --version")
    state["has_gh"] = has_gh

    if not has_gh:
        return state

    # Get open issues
    output, ok = run_command("gh issue list --state open --limit 10 --json number,title,labels")
    if ok and output:
        try:
            issues = json.loads(output)
            state["open_count"] = len(issues)
            state["issues"] = issues[:5]

            # Check for priority labels
            for issue in issues:
                labels = [l.get("name", "") for l in issue.get("labels", [])]
                if "P0-critical" in labels or "P1-high" in labels:
                    state["urgency"] = "HIGH"
                    break
                elif "P2-medium" in labels and state["urgency"] != "HIGH":
                    state["urgency"] = "MEDIUM"
        except json.JSONDecodeError:
            pass

    return state


def analyze_research_branches() -> Dict[str, Any]:
    """Analyze research branches from Claude Code Web sessions."""
    state = {
        "has_research_branches": False,
        "branches": [],
        "urgency": "LOW"
    }

    # Fetch to get all remote branches
    run_command("git fetch --all --prune 2>/dev/null")

    # Look for research-related branches
    branches, ok = run_command("git branch -r")
    if not ok:
        return state

    research_patterns = ["research-", "claude/research", "/research-"]

    for line in branches.split('\n'):
        branch = line.strip()
        if not branch or "HEAD" in branch:
            continue

        # Check if it matches research patterns
        if any(pattern in branch.lower() for pattern in research_patterns):
            # Get branch creation time
            date_output, _ = run_command(f"git log -1 --format='%ar' {branch} 2>/dev/null")

            state["branches"].append({
                "name": branch,
                "age": date_output or "unknown"
            })

    if state["branches"]:
        state["has_research_branches"] = True
        state["urgency"] = "HIGH"

    return state


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze project state")
    parser.add_argument("--section", choices=["git", "code", "issues", "research", "all"],
                        default="all", help="Section to analyze")
    args = parser.parse_args()

    result = {
        "operation": "analyze_state",
        "section": args.section,
        "timestamp": datetime.now().isoformat()
    }

    if args.section in ["git", "all"]:
        result["git"] = analyze_git_state()

    if args.section in ["code", "all"]:
        result["code"] = analyze_code_state()

    if args.section in ["issues", "all"]:
        result["issues"] = analyze_issues()

    if args.section in ["research", "all"]:
        result["research"] = analyze_research_branches()

    # Calculate overall urgency
    urgencies = []
    for section in ["git", "code", "issues", "research"]:
        if section in result:
            urgencies.append(result[section].get("urgency", "LOW"))

    if "HIGH" in urgencies:
        result["overall_urgency"] = "HIGH"
    elif "MEDIUM" in urgencies:
        result["overall_urgency"] = "MEDIUM"
    else:
        result["overall_urgency"] = "LOW"

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
