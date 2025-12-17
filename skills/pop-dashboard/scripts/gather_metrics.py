#!/usr/bin/env python3
"""
Dashboard Metrics Gathering Script.

Gather metrics for multi-project dashboard display.

Usage:
    python gather_metrics.py [--operation OPERATION] [--project PROJECT]

Operations:
    load_registry   - Load project registry
    health_check    - Calculate health scores for all projects
    activity        - Gather recent activity
    add             - Add a project
    remove          - Remove a project
    refresh         - Refresh health scores
    full            - Full dashboard data

Output:
    JSON object with requested metrics
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_registry_path() -> Path:
    """Get path to project registry."""
    home = Path(os.path.expanduser("~"))
    return home / ".claude" / "popkit" / "projects.json"


def load_registry() -> Dict[str, Any]:
    """Load project registry from file."""
    registry_path = get_registry_path()
    if registry_path.exists():
        return json.loads(registry_path.read_text())

    return {
        "version": "1.0.0",
        "projects": [],
        "settings": {
            "autoDiscover": True,
            "healthCheckInterval": "daily",
            "maxInactiveProjects": 20
        }
    }


def save_registry(registry: Dict[str, Any]) -> None:
    """Save registry to file."""
    registry_path = get_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2))


def run_command(cmd: str, cwd: Optional[str] = None, timeout: int = 30) -> Tuple[str, bool]:
    """Run a shell command and return output and success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        return result.stdout.strip(), result.returncode == 0
    except subprocess.TimeoutExpired:
        return "Command timed out", False
    except Exception as e:
        return str(e), False


def detect_project_info(path: str) -> Dict[str, Any]:
    """Auto-detect project information from manifest files."""
    project_path = Path(path).resolve()
    info = {
        "name": project_path.name,
        "path": str(project_path),
        "type": "unknown",
        "repo": None
    }

    # Try package.json
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text())
            info["name"] = pkg.get("name", info["name"])
            info["type"] = "node"
        except Exception:
            pass

    # Try pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        info["type"] = "python"
        # Could parse TOML for name, but keep it simple

    # Try getting git remote
    remote, ok = run_command("git remote get-url origin", cwd=path)
    if ok and remote:
        info["repo"] = remote

    return info


def calculate_health_score(path: str) -> Dict[str, Any]:
    """Calculate full health score for a project."""
    result = {
        "score": 0,
        "components": {},
        "details": []
    }

    if not Path(path).exists():
        result["error"] = "Project path not found"
        return result

    # Git status (20 points)
    git_score = 20
    status, ok = run_command("git status --porcelain", cwd=path)
    if ok:
        if status:
            uncommitted = len(status.split('\n'))
            penalty = min(uncommitted, 4) * 5  # Max 20 point penalty
            git_score -= penalty
            result["details"].append(f"{uncommitted} uncommitted files")

        # Check unpushed commits
        ahead, ok = run_command("git rev-list @{u}..HEAD --count 2>/dev/null", cwd=path)
        if ok and ahead.isdigit() and int(ahead) > 0:
            git_score -= min(int(ahead), 4) * 5
            result["details"].append(f"{ahead} unpushed commits")
    else:
        git_score = 0
        result["details"].append("Not a git repository")

    result["components"]["git_status"] = max(0, git_score)
    result["score"] += result["components"]["git_status"]

    # Build status (20 points) - simplified
    build_score = 20
    # Check for TypeScript errors if tsconfig exists
    if (Path(path) / "tsconfig.json").exists():
        ts_errors, ok = run_command("npx tsc --noEmit 2>&1 | grep -c 'error TS' || echo 0", cwd=path, timeout=60)
        try:
            error_count = int(ts_errors.strip())
            if error_count > 0:
                build_score = 0
                result["details"].append(f"{error_count} TypeScript errors")
        except ValueError:
            pass

    result["components"]["build_status"] = build_score
    result["score"] += build_score

    # Test coverage (20 points) - simplified, check if tests exist
    test_score = 5  # Base score for having tests
    test_dirs = ["tests", "test", "__tests__", "spec"]
    for test_dir in test_dirs:
        if (Path(path) / test_dir).exists():
            test_score = 15
            break

    # Check for coverage report
    if (Path(path) / "coverage").exists():
        test_score = 20

    result["components"]["test_coverage"] = test_score
    result["score"] += test_score

    # Issue health (20 points) - check via gh CLI
    issue_score = 20
    issues, ok = run_command("gh issue list --state open --limit 20 --json createdAt", cwd=path)
    if ok and issues:
        try:
            issue_list = json.loads(issues)
            stale_count = 0
            now = datetime.now()
            for issue in issue_list:
                created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                age_days = (now - created.replace(tzinfo=None)).days
                if age_days > 30:
                    stale_count += 1

            if stale_count > 0:
                issue_score -= min(stale_count, 10) * 2
                result["details"].append(f"{stale_count} stale issues (>30 days)")
        except Exception:
            pass

    result["components"]["issue_health"] = max(0, issue_score)
    result["score"] += result["components"]["issue_health"]

    # Activity (20 points)
    activity_score = 5  # Default for inactive
    last_commit, ok = run_command("git log -1 --format=%ci", cwd=path)
    if ok and last_commit:
        try:
            commit_date = datetime.strptime(last_commit.split()[0], "%Y-%m-%d")
            days_ago = (datetime.now() - commit_date).days

            if days_ago == 0:
                activity_score = 20
            elif days_ago <= 7:
                activity_score = 15
            elif days_ago <= 30:
                activity_score = 10
            else:
                activity_score = 5
                result["details"].append(f"Last commit {days_ago} days ago")
        except Exception:
            pass

    result["components"]["activity"] = activity_score
    result["score"] += activity_score

    return result


def calculate_quick_health(path: str) -> int:
    """Calculate quick health score (git + activity only)."""
    score = 0

    if not Path(path).exists():
        return 0

    # Git status (50 points)
    status, ok = run_command("git status --porcelain", cwd=path)
    if ok:
        if not status:
            score += 50
        else:
            uncommitted = len(status.split('\n'))
            score += max(0, 50 - uncommitted * 10)

    # Activity (50 points)
    last_commit, ok = run_command("git log -1 --format=%ci", cwd=path)
    if ok and last_commit:
        try:
            commit_date = datetime.strptime(last_commit.split()[0], "%Y-%m-%d")
            days_ago = (datetime.now() - commit_date).days

            if days_ago == 0:
                score += 50
            elif days_ago <= 7:
                score += 40
            elif days_ago <= 30:
                score += 25
            else:
                score += 10
        except Exception:
            score += 10

    return score


def get_recent_activity(projects: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent activity across all projects."""
    activities = []

    for project in projects:
        path = project.get("path")
        if not path or not Path(path).exists():
            continue

        # Get recent commits
        commits, ok = run_command(
            "git log -3 --format='%h|%s|%ar' 2>/dev/null",
            cwd=path
        )
        if ok and commits:
            for line in commits.split('\n')[:3]:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        activities.append({
                            "project": project.get("name", "unknown"),
                            "action": f"Commit: {parts[1][:50]}",
                            "time": parts[2],
                            "type": "commit"
                        })

    # Sort by recency (would need proper timestamp parsing for accuracy)
    return activities[:limit]


def get_unhealthy_projects(projects: List[Dict[str, Any]], threshold: int = 70) -> List[Dict[str, Any]]:
    """Get projects with health below threshold."""
    return [p for p in projects if p.get("healthScore", 0) < threshold]


def add_project(path: str, tags: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Add a project to the registry."""
    registry = load_registry()

    # Check if already registered
    abs_path = str(Path(path).resolve())
    for project in registry["projects"]:
        if project.get("path") == abs_path:
            return False, f"Project already registered: {project.get('name')}"

    # Detect project info
    info = detect_project_info(path)

    # Calculate initial health
    health = calculate_health_score(path)

    project = {
        "name": info["name"],
        "path": abs_path,
        "type": info["type"],
        "repo": info["repo"],
        "healthScore": health["score"],
        "healthComponents": health["components"],
        "tags": tags or [],
        "addedAt": datetime.now().isoformat(),
        "lastAccessed": datetime.now().isoformat()
    }

    registry["projects"].append(project)
    save_registry(registry)

    return True, f"Added project: {info['name']} (Health: {health['score']}/100)"


def remove_project(name: str) -> Tuple[bool, str]:
    """Remove a project from the registry."""
    registry = load_registry()

    for i, project in enumerate(registry["projects"]):
        if project.get("name") == name:
            registry["projects"].pop(i)
            save_registry(registry)
            return True, f"Removed project: {name}"

    return False, f"Project not found: {name}"


def touch_project(path: str) -> None:
    """Update last accessed timestamp for a project."""
    registry = load_registry()

    for project in registry["projects"]:
        if project.get("path") == path:
            project["lastAccessed"] = datetime.now().isoformat()
            save_registry(registry)
            break


def refresh_all_health_scores() -> Dict[str, Any]:
    """Refresh health scores for all projects."""
    registry = load_registry()
    results = {}

    for project in registry["projects"]:
        path = project.get("path")
        if path and Path(path).exists():
            health = calculate_health_score(path)
            project["healthScore"] = health["score"]
            project["healthComponents"] = health["components"]
            project["lastHealthCheck"] = datetime.now().isoformat()
            results[project["name"]] = health["score"]
        else:
            results[project["name"]] = "path_not_found"

    save_registry(registry)
    return results


def generate_dashboard_data() -> Dict[str, Any]:
    """Generate full dashboard data."""
    registry = load_registry()
    projects = registry.get("projects", [])

    # Calculate summary
    total = len(projects)
    healthy = sum(1 for p in projects if p.get("healthScore", 0) >= 80)
    warning = sum(1 for p in projects if 50 <= p.get("healthScore", 0) < 80)
    critical = sum(1 for p in projects if p.get("healthScore", 0) < 50)

    # Sort projects by health (descending)
    sorted_projects = sorted(
        projects,
        key=lambda p: (p.get("healthScore", 0), p.get("lastAccessed", "")),
        reverse=True
    )

    # Get unhealthy projects
    alerts = get_unhealthy_projects(projects, threshold=70)

    # Get recent activity
    activity = get_recent_activity(projects)

    return {
        "summary": {
            "total": total,
            "healthy": healthy,
            "warning": warning,
            "critical": critical
        },
        "projects": sorted_projects,
        "alerts": [
            {
                "project": p["name"],
                "health": p.get("healthScore", 0),
                "reason": "Health score below threshold"
            }
            for p in alerts
        ],
        "activity": activity,
        "settings": registry.get("settings", {})
    }


def format_dashboard_display(data: Dict[str, Any]) -> str:
    """Format dashboard data for display."""
    lines = []
    summary = data["summary"]

    lines.append("+===============================================================+")
    lines.append("|                      PopKit Dashboard                          |")
    lines.append("+===============================================================+")
    lines.append("")
    lines.append(f"  Total: {summary['total']}  |  Healthy: {summary['healthy']}  |  Warning: {summary['warning']}  |  Critical: {summary['critical']}")
    lines.append("")
    lines.append("  -------------------------------------------------------------")
    lines.append("  | Project          | Health | Issues | Last Active   |")
    lines.append("  -------------------------------------------------------------")

    for project in data["projects"][:10]:  # Top 10
        name = project.get("name", "unknown")[:16].ljust(16)
        health = project.get("healthScore", 0)

        # Health indicator
        if health >= 80:
            health_str = f"+ {health}"
        elif health >= 50:
            health_str = f"~ {health}"
        else:
            health_str = f"! {health}"
        health_str = health_str.ljust(6)

        # Last accessed
        last_accessed = project.get("lastAccessed", "")
        if last_accessed:
            try:
                dt = datetime.fromisoformat(last_accessed)
                delta = datetime.now() - dt
                if delta.days > 0:
                    last_str = f"{delta.days} days ago"
                elif delta.seconds > 3600:
                    last_str = f"{delta.seconds // 3600} hours ago"
                else:
                    last_str = f"{delta.seconds // 60} min ago"
            except Exception:
                last_str = "unknown"
        else:
            last_str = "unknown"
        last_str = last_str[:13].ljust(13)

        lines.append(f"  | {name} | {health_str} |   --   | {last_str} |")

    lines.append("  -------------------------------------------------------------")
    lines.append("")
    lines.append("  Commands: add <path> | remove <name> | refresh | switch <name>")

    if data["alerts"]:
        lines.append("")
        lines.append("  Alerts:")
        for alert in data["alerts"][:3]:
            lines.append(f"    ! {alert['project']}: Health {alert['health']}/100")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gather dashboard metrics")
    parser.add_argument("--operation", "-o",
                        choices=["load_registry", "health_check", "activity",
                                "add", "remove", "refresh", "full"],
                        default="full", help="Operation to perform")
    parser.add_argument("--project", "-p", help="Project path or name")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    parser.add_argument("--tags", help="Comma-separated tags (for add)")
    args = parser.parse_args()

    result = {
        "operation": f"dashboard_{args.operation}",
        "timestamp": datetime.now().isoformat()
    }

    if args.operation == "load_registry":
        result["registry"] = load_registry()

    elif args.operation == "health_check":
        if args.project:
            result["health"] = calculate_health_score(args.project)
        else:
            result["health_scores"] = refresh_all_health_scores()

    elif args.operation == "activity":
        registry = load_registry()
        result["activity"] = get_recent_activity(registry.get("projects", []))

    elif args.operation == "add":
        if not args.project:
            result["success"] = False
            result["error"] = "Project path required"
        else:
            tags = args.tags.split(",") if args.tags else None
            success, message = add_project(args.project, tags)
            result["success"] = success
            result["message"] = message

    elif args.operation == "remove":
        if not args.project:
            result["success"] = False
            result["error"] = "Project name required"
        else:
            success, message = remove_project(args.project)
            result["success"] = success
            result["message"] = message

    elif args.operation == "refresh":
        result["health_scores"] = refresh_all_health_scores()

    elif args.operation == "full":
        data = generate_dashboard_data()
        result["dashboard"] = data

        if args.format == "display":
            print(format_dashboard_display(data))
            return 0

    result["success"] = result.get("success", True)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
