#!/usr/bin/env python3
"""
Context Discovery Script.

Find and gather context from various sources for session restoration.

Usage:
    python find_context.py [--source SOURCE] [--focus AREA]

Sources:
    status       - Load from STATUS.json
    recent-files - Find recently modified files
    git          - Gather git history context
    project-state - Get current project state
    all          - All sources

Output:
    JSON object with gathered context from specified sources
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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


def load_status_context() -> Dict[str, Any]:
    """Load context from STATUS.json."""
    status_paths = [
        Path(".claude/STATUS.json"),
        Path("STATUS.json"),
        Path.home() / ".claude" / "STATUS.json"
    ]

    for path in status_paths:
        if path.exists():
            try:
                content = path.read_text()
                status = json.loads(content)
                return {
                    "found": True,
                    "path": str(path),
                    "project": status.get("project", "unknown"),
                    "lastUpdate": status.get("lastUpdate"),
                    "focusArea": status.get("context", {}).get("focusArea", ""),
                    "nextAction": status.get("context", {}).get("nextAction", ""),
                    "keyDecisions": status.get("context", {}).get("keyDecisions", []),
                    "blocker": status.get("context", {}).get("blocker"),
                    "tasks": status.get("tasks", {}),
                    "git": status.get("git", {})
                }
            except Exception as e:
                return {"found": False, "error": str(e)}

    return {"found": False, "searched": [str(p) for p in status_paths]}


def find_recent_files(hours: int = 24, limit: int = 10) -> Dict[str, Any]:
    """Find files modified within the specified time window."""
    result = {
        "files": [],
        "total_found": 0
    }

    # Use git to find recently modified files
    cmd = f"git diff --name-only HEAD~10 2>/dev/null || git ls-files -m"
    output, ok = run_command(cmd)

    if ok and output:
        files = output.split('\n')[:limit]
        result["files"] = [{"path": f, "source": "git"} for f in files if f]
        result["total_found"] = len(files)

    # Also check for uncommitted changes
    status_output, ok = run_command("git status --porcelain")
    if ok and status_output:
        for line in status_output.split('\n'):
            if line.strip():
                status_code = line[:2]
                file_path = line[3:].strip()
                result["files"].append({
                    "path": file_path,
                    "status": status_code,
                    "source": "uncommitted"
                })

    return result


def gather_git_context() -> Dict[str, Any]:
    """Gather context from git history."""
    context = {
        "branch": "",
        "recent_commits": [],
        "uncommitted_changes": [],
        "stash_count": 0
    }

    # Current branch
    branch, ok = run_command("git branch --show-current")
    if ok:
        context["branch"] = branch

    # Recent commits with details
    commits_output, ok = run_command(
        "git log --oneline -10 --format='%h|%s|%ar'"
    )
    if ok and commits_output:
        for line in commits_output.split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    context["recent_commits"].append({
                        "hash": parts[0],
                        "message": parts[1],
                        "time": parts[2]
                    })

    # Uncommitted changes with details
    diff_stat, ok = run_command("git diff --stat")
    if ok and diff_stat:
        context["uncommitted_summary"] = diff_stat

    status_output, ok = run_command("git status --porcelain")
    if ok and status_output:
        for line in status_output.split('\n'):
            if line.strip():
                status_code = line[:2].strip()
                file_path = line[3:].strip()

                status_meaning = {
                    'M': 'modified',
                    'A': 'added',
                    'D': 'deleted',
                    '??': 'untracked',
                    'R': 'renamed'
                }

                context["uncommitted_changes"].append({
                    "file": file_path,
                    "status": status_meaning.get(status_code, status_code)
                })

    # Check stash
    stash_output, ok = run_command("git stash list | wc -l")
    if ok:
        try:
            context["stash_count"] = int(stash_output.strip())
        except ValueError:
            pass

    return context


def get_project_state() -> Dict[str, Any]:
    """Get current project state (tests, build, lint)."""
    state = {
        "tests": {"status": "unknown"},
        "build": {"status": "unknown"},
        "lint": {"status": "unknown"}
    }

    # Quick test check (just see if command exists)
    test_check, ok = run_command("npm run test --if-present 2>&1 | head -20", timeout=60)
    if ok:
        if "passing" in test_check.lower():
            state["tests"]["status"] = "passing"
        elif "failing" in test_check.lower() or "failed" in test_check.lower():
            state["tests"]["status"] = "failing"
        state["tests"]["output"] = test_check[:500]

    # Build check
    build_check, ok = run_command("npm run build --if-present 2>&1 | tail -5", timeout=120)
    if ok:
        state["build"]["status"] = "passing"
    else:
        state["build"]["status"] = "failing" if build_check else "not configured"
    state["build"]["output"] = build_check[:500] if build_check else ""

    # Lint check
    lint_check, ok = run_command("npm run lint --if-present 2>&1 | tail -10", timeout=60)
    if ok:
        state["lint"]["status"] = "passing"
        state["lint"]["errors"] = 0
    else:
        state["lint"]["status"] = "errors"
        # Try to extract error count
        import re
        errors = re.findall(r'(\d+)\s+error', lint_check)
        state["lint"]["errors"] = int(errors[0]) if errors else -1

    return state


def build_mental_model(
    status_context: Dict,
    git_context: Dict,
    recent_files: Dict,
    project_state: Dict
) -> Dict[str, Any]:
    """Build a mental model from all gathered context."""
    model = {
        "what_we_are_building": "",
        "where_we_are": {},
        "key_files": [],
        "decisions_made": [],
        "whats_next": [],
        "potential_issues": []
    }

    # What we're building
    if status_context.get("found"):
        model["what_we_are_building"] = status_context.get("focusArea", "")

    # Where we are
    model["where_we_are"] = {
        "branch": git_context.get("branch", "unknown"),
        "last_commit": git_context["recent_commits"][0] if git_context.get("recent_commits") else None,
        "uncommitted_files": len(git_context.get("uncommitted_changes", []))
    }

    # Key files (from recent and uncommitted)
    seen_files = set()
    for f in recent_files.get("files", []):
        path = f.get("path", "")
        if path and path not in seen_files:
            model["key_files"].append(path)
            seen_files.add(path)

    # Decisions made
    if status_context.get("found"):
        model["decisions_made"] = status_context.get("keyDecisions", [])

    # What's next
    if status_context.get("found") and status_context.get("nextAction"):
        model["whats_next"].append(status_context["nextAction"])

    # Potential issues
    if project_state["tests"]["status"] == "failing":
        model["potential_issues"].append("Tests are failing")
    if project_state["build"]["status"] == "failing":
        model["potential_issues"].append("Build is failing")
    if project_state["lint"]["status"] == "errors":
        errors = project_state["lint"].get("errors", -1)
        model["potential_issues"].append(f"Lint errors: {errors}")
    if status_context.get("blocker"):
        model["potential_issues"].append(f"Blocker: {status_context['blocker']}")

    return model


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Find context for session restoration")
    parser.add_argument("--source", choices=["status", "recent-files", "git", "project-state", "all"],
                        default="all", help="Context source to gather")
    parser.add_argument("--focus", help="Focus area to filter relevant files")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back for recent files")
    parser.add_argument("--build-model", action="store_true", help="Build mental model from all sources")
    args = parser.parse_args()

    result = {
        "operation": "find_context",
        "source": args.source,
        "timestamp": datetime.now().isoformat()
    }

    status_context = {}
    git_context = {}
    recent_files = {}
    project_state = {}

    if args.source in ["status", "all"]:
        status_context = load_status_context()
        result["status"] = status_context

    if args.source in ["recent-files", "all"]:
        recent_files = find_recent_files(args.hours)
        result["recent_files"] = recent_files

    if args.source in ["git", "all"]:
        git_context = gather_git_context()
        result["git"] = git_context

    if args.source in ["project-state", "all"]:
        project_state = get_project_state()
        result["project_state"] = project_state

    if args.build_model or args.source == "all":
        mental_model = build_mental_model(
            status_context or load_status_context(),
            git_context or gather_git_context(),
            recent_files or find_recent_files(),
            project_state or get_project_state()
        )
        result["mental_model"] = mental_model

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
