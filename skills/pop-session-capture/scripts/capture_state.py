#!/usr/bin/env python3
"""
Session State Capture Script.

Capture current session state for STATUS.json.

Usage:
    python capture_state.py [--mode MODE] [--section SECTION] [--output PATH]

Modes:
    gather  - Collect state from all sources
    build   - Build STATUS.json structure
    write   - Write to file

Sections:
    git      - Git repository state
    services - Running services
    checks   - Project checks (tests, build, lint)
    all      - All sections

Output:
    JSON object with captured state
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_command(cmd: str, timeout: int = 30) -> tuple:
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


def gather_git_state() -> Dict[str, Any]:
    """Gather current git repository state."""
    state = {
        "branch": "",
        "lastCommit": "",
        "uncommittedFiles": 0,
        "stagedFiles": 0,
        "modifiedFiles": [],
        "untrackedFiles": []
    }

    # Get current branch
    branch, ok = run_command("git branch --show-current")
    if ok:
        state["branch"] = branch

    # Get last commit
    commit, ok = run_command("git log -1 --format='%h - %s'")
    if ok:
        state["lastCommit"] = commit

    # Count uncommitted changes
    status, ok = run_command("git status --porcelain")
    if ok:
        lines = [l for l in status.split('\n') if l.strip()]
        state["uncommittedFiles"] = len(lines)

        for line in lines:
            if line.startswith('??'):
                state["untrackedFiles"].append(line[3:].strip())
            else:
                state["modifiedFiles"].append(line[3:].strip())

    # Count staged files
    staged, ok = run_command("git diff --cached --name-only")
    if ok:
        staged_files = [f for f in staged.split('\n') if f.strip()]
        state["stagedFiles"] = len(staged_files)

    return state


def gather_service_state() -> Dict[str, Any]:
    """Check running services."""
    services = {}

    # Common service ports to check
    port_checks = [
        ("devServer", 3000, "Development server"),
        ("api", 8000, "API server"),
        ("database", 5432, "PostgreSQL"),
        ("redis", 6379, "Redis"),
        ("storybook", 6006, "Storybook"),
    ]

    for name, port, description in port_checks:
        # Check if port is in use
        if sys.platform == "win32":
            cmd = f"netstat -an | findstr :{port}"
        else:
            cmd = f"lsof -i :{port} -t 2>/dev/null || ss -tlnp 2>/dev/null | grep :{port}"

        output, ok = run_command(cmd)
        services[name] = {
            "running": bool(output.strip()),
            "port": port,
            "description": description
        }

    return services


def gather_project_checks() -> Dict[str, Any]:
    """Run project checks and gather results."""
    checks = {
        "testStatus": "unknown",
        "buildStatus": "unknown",
        "lintErrors": -1
    }

    # Run tests
    test_output, ok = run_command("npm test 2>&1 | tail -5", timeout=60)
    if ok:
        # Try to extract pass/fail counts
        if "passing" in test_output:
            checks["testStatus"] = "passing"
        elif "failing" in test_output or "failed" in test_output:
            checks["testStatus"] = "failing"
        else:
            checks["testStatus"] = test_output[-100:] if test_output else "no tests"

    # Check build
    build_output, ok = run_command("npm run build --if-present 2>&1 | tail -1", timeout=120)
    if ok:
        checks["buildStatus"] = "passing"
    else:
        checks["buildStatus"] = "failing" if build_output else "not configured"

    # Run lint
    lint_output, ok = run_command("npm run lint --if-present 2>&1 | tail -5", timeout=60)
    if ok:
        checks["lintErrors"] = 0
    else:
        # Try to count errors
        if lint_output:
            import re
            errors = re.findall(r'(\d+)\s+error', lint_output)
            if errors:
                checks["lintErrors"] = int(errors[0])
            else:
                checks["lintErrors"] = -1

    return checks


def gather_task_state(tasks: Optional[Dict] = None) -> Dict[str, Any]:
    """Gather task state (from provided tasks or empty)."""
    if tasks:
        return tasks

    return {
        "inProgress": [],
        "completed": [],
        "blocked": []
    }


def gather_context(context: Optional[Dict] = None) -> Dict[str, Any]:
    """Gather context information."""
    if context:
        return context

    return {
        "focusArea": "",
        "blocker": None,
        "nextAction": "",
        "keyDecisions": []
    }


def build_status_json(
    git_state: Dict,
    service_state: Dict,
    project_checks: Dict,
    task_state: Dict,
    context: Dict,
    project_name: Optional[str] = None
) -> Dict[str, Any]:
    """Build complete STATUS.json structure."""
    # Try to get project name from package.json
    if not project_name:
        try:
            pkg_path = Path("package.json")
            if pkg_path.exists():
                pkg = json.loads(pkg_path.read_text())
                project_name = pkg.get("name", Path.cwd().name)
            else:
                project_name = Path.cwd().name
        except Exception:
            project_name = Path.cwd().name

    return {
        "lastUpdate": datetime.now().isoformat() + "Z",
        "project": project_name,
        "sessionType": "Capture",
        "git": git_state,
        "tasks": task_state,
        "services": service_state,
        "context": context,
        "projectData": project_checks
    }


def write_status_json(status: Dict, output_path: Optional[str] = None) -> str:
    """Write STATUS.json to disk."""
    if output_path:
        path = Path(output_path)
    else:
        # Prefer .claude directory if it exists
        claude_dir = Path(".claude")
        if claude_dir.exists():
            path = claude_dir / "STATUS.json"
        else:
            path = Path("STATUS.json")

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting
    path.write_text(json.dumps(status, indent=2))

    return str(path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Capture session state")
    parser.add_argument("--mode", choices=["gather", "build", "write", "all"],
                        default="all", help="Operation mode")
    parser.add_argument("--section", choices=["git", "services", "checks", "all"],
                        default="all", help="Section to gather")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--project", help="Project name override")
    parser.add_argument("--context-json", help="Context as JSON string")
    parser.add_argument("--tasks-json", help="Tasks as JSON string")
    args = parser.parse_args()

    result = {
        "operation": "capture_state",
        "mode": args.mode,
        "timestamp": datetime.now().isoformat()
    }

    # Parse optional JSON inputs
    context = None
    tasks = None
    if args.context_json:
        try:
            context = json.loads(args.context_json)
        except json.JSONDecodeError:
            pass
    if args.tasks_json:
        try:
            tasks = json.loads(args.tasks_json)
        except json.JSONDecodeError:
            pass

    if args.mode in ["gather", "all"]:
        gathered = {}

        if args.section in ["git", "all"]:
            gathered["git"] = gather_git_state()

        if args.section in ["services", "all"]:
            gathered["services"] = gather_service_state()

        if args.section in ["checks", "all"]:
            gathered["checks"] = gather_project_checks()

        result["gathered"] = gathered

    if args.mode in ["build", "all"]:
        # Gather all sections for build
        git_state = gather_git_state()
        service_state = gather_service_state()
        project_checks = gather_project_checks()
        task_state = gather_task_state(tasks)
        context_state = gather_context(context)

        status = build_status_json(
            git_state=git_state,
            service_state=service_state,
            project_checks=project_checks,
            task_state=task_state,
            context=context_state,
            project_name=args.project
        )
        result["status"] = status

    if args.mode in ["write", "all"]:
        if "status" not in result:
            # Build status first
            git_state = gather_git_state()
            service_state = gather_service_state()
            project_checks = gather_project_checks()
            task_state = gather_task_state(tasks)
            context_state = gather_context(context)

            status = build_status_json(
                git_state=git_state,
                service_state=service_state,
                project_checks=project_checks,
                task_state=task_state,
                context=context_state,
                project_name=args.project
            )
        else:
            status = result["status"]

        output_path = write_status_json(status, args.output)
        result["output_path"] = output_path
        result["status"] = status

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
