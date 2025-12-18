#!/usr/bin/env python3
"""
Morning Health Check Script.

Run health checks and calculate Ready to Code score.

Usage:
    python health_check.py [--section SECTION] [--mode MODE]

Sections:
    git      - Git repository status
    services - Service health checks
    quality  - Code quality (lint, types)
    all      - All sections

Modes:
    check - Run checks only
    score - Calculate Ready to Code score

Output:
    JSON object with health status and score
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def run_command(cmd: str, timeout: int = 60) -> Tuple[str, bool]:
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


def check_git_status() -> Dict[str, Any]:
    """Check git repository status."""
    status = {
        "healthy": True,
        "checks": {},
        "issues": []
    }

    # Check branch
    branch, ok = run_command("git branch --show-current")
    status["checks"]["branch"] = {
        "value": branch if ok else "unknown",
        "ok": ok
    }

    # Check uncommitted changes
    uncommitted, ok = run_command("git status --porcelain .")
    uncommitted_count = len([l for l in uncommitted.split('\n') if l.strip()]) if ok else -1
    status["checks"]["uncommitted"] = {
        "value": uncommitted_count,
        "ok": uncommitted_count == 0
    }
    if uncommitted_count > 0:
        status["issues"].append(f"{uncommitted_count} uncommitted changes")
        status["healthy"] = False

    # Check if up to date with remote
    fetch_output, _ = run_command("git fetch --dry-run 2>&1")
    status["checks"]["remote_sync"] = {
        "value": "up to date" if not fetch_output else "behind",
        "ok": not fetch_output
    }
    if fetch_output:
        status["issues"].append("Behind remote")

    # Check for merge conflicts
    conflicts, ok = run_command("git diff --check")
    has_conflicts = bool(conflicts) if ok else False
    status["checks"]["conflicts"] = {
        "value": "none" if not has_conflicts else "detected",
        "ok": not has_conflicts
    }
    if has_conflicts:
        status["issues"].append("Merge conflicts detected")
        status["healthy"] = False

    return status


def check_services() -> Dict[str, Any]:
    """Check service health."""
    status = {
        "healthy": True,
        "checks": {},
        "issues": []
    }

    # Common service ports to check
    services = [
        ("dev_server", [3000, 3001, 5173, 8000], "Development server"),
        ("database", [5432, 5433, 54322], "PostgreSQL"),
        ("redis", [6379], "Redis"),
        ("api", [5001, 8001, 8080], "API server"),
    ]

    for name, ports, description in services:
        running = False
        active_port = None

        for port in ports:
            if sys.platform == "win32":
                cmd = f'netstat -an | findstr ":{port}"'
            else:
                cmd = f"lsof -i :{port} -t 2>/dev/null || ss -tlnp 2>/dev/null | grep :{port}"

            output, ok = run_command(cmd)
            if output.strip():
                running = True
                active_port = port
                break

        status["checks"][name] = {
            "description": description,
            "running": running,
            "port": active_port,
            "ok": True  # Not required to be running
        }

    return status


def check_code_quality() -> Dict[str, Any]:
    """Check code quality (lint, types, tests)."""
    status = {
        "healthy": True,
        "checks": {},
        "issues": []
    }

    # TypeScript check
    ts_output, ts_ok = run_command("npm run typecheck --if-present 2>&1 | tail -5", timeout=120)
    if "tsc" in ts_output or "typescript" in ts_output.lower():
        has_errors = not ts_ok or "error" in ts_output.lower()
        status["checks"]["typescript"] = {
            "value": "clean" if not has_errors else "errors",
            "ok": not has_errors
        }
        if has_errors:
            status["issues"].append("TypeScript errors")
            status["healthy"] = False
    else:
        status["checks"]["typescript"] = {"value": "not configured", "ok": True}

    # Lint check
    lint_output, lint_ok = run_command("npm run lint --if-present 2>&1 | tail -5", timeout=60)
    has_lint_errors = not lint_ok and ("error" in lint_output.lower() or "warning" in lint_output.lower())
    status["checks"]["lint"] = {
        "value": "clean" if not has_lint_errors else "issues",
        "ok": not has_lint_errors
    }
    if has_lint_errors:
        status["issues"].append("Lint issues")

    # Test check (quick - just see if they run)
    test_output, test_ok = run_command("npm test --if-present 2>&1 | tail -10", timeout=120)
    if "passing" in test_output.lower() or "passed" in test_output.lower():
        status["checks"]["tests"] = {"value": "passing", "ok": True}
    elif "failing" in test_output.lower() or "failed" in test_output.lower():
        status["checks"]["tests"] = {"value": "failing", "ok": False}
        status["issues"].append("Tests failing")
        status["healthy"] = False
    else:
        status["checks"]["tests"] = {"value": "unknown", "ok": True}

    return status


def calculate_ready_score(git: Dict, services: Dict, quality: Dict) -> Dict[str, Any]:
    """Calculate Ready to Code score (0-100)."""
    score = 0
    breakdown = []

    # Services running (30 points)
    service_points = 0
    running_services = sum(1 for s in services["checks"].values() if s.get("running"))
    total_services = len(services["checks"])
    if running_services > 0:
        service_points = min(30, int(30 * (running_services / max(total_services, 1))))
    score += service_points
    breakdown.append({"category": "Services Running", "points": service_points, "max": 30})

    # Clean working directory (20 points)
    git_points = 20 if git["checks"].get("uncommitted", {}).get("ok", False) else 0
    score += git_points
    breakdown.append({"category": "Clean Working Directory", "points": git_points, "max": 20})

    # Remote sync (10 points)
    sync_points = 10 if git["checks"].get("remote_sync", {}).get("ok", False) else 0
    score += sync_points
    breakdown.append({"category": "Remote Sync", "points": sync_points, "max": 10})

    # Code quality (15 points)
    quality_points = 0
    if quality["checks"].get("typescript", {}).get("ok", True):
        quality_points += 10
    if quality["checks"].get("lint", {}).get("ok", True):
        quality_points += 5
    score += quality_points
    breakdown.append({"category": "Code Quality", "points": quality_points, "max": 15})

    # Tests passing (25 points)
    test_points = 25 if quality["checks"].get("tests", {}).get("ok", True) else 0
    score += test_points
    breakdown.append({"category": "Tests Passing", "points": test_points, "max": 25})

    # Determine status
    if score >= 90:
        status = "excellent"
        message = "Ready to code!"
    elif score >= 70:
        status = "good"
        message = "Ready with minor issues"
    elif score >= 50:
        status = "fair"
        message = "Some issues to address"
    else:
        status = "needs_attention"
        message = "Please address issues before coding"

    return {
        "score": score,
        "max_score": 100,
        "status": status,
        "message": message,
        "breakdown": breakdown
    }


def generate_morning_report(git: Dict, services: Dict, quality: Dict, score_data: Dict) -> str:
    """Generate formatted morning report."""
    lines = [
        "┌─────────────────────────────────────────────┐",
        f"│ 🌅 Morning Health Check                      │",
        f"│ {datetime.now().strftime('%Y-%m-%d %H:%M')}                           │",
        "├─────────────────────────────────────────────┤",
    ]

    # Git status
    branch = git["checks"].get("branch", {}).get("value", "unknown")
    uncommitted = git["checks"].get("uncommitted", {}).get("value", 0)
    lines.append(f"│ Git: {branch[:30]}{' ' * (38 - min(30, len(branch)))}│")
    lines.append(f"│   Uncommitted: {uncommitted}{' ' * (28 - len(str(uncommitted)))}│")

    # Services
    lines.append("├─────────────────────────────────────────────┤")
    for name, info in services["checks"].items():
        status = "✓" if info.get("running") else "✗"
        port = f":{info.get('port')}" if info.get("port") else ""
        line = f"│ {status} {info.get('description', name)}{port}"
        lines.append(f"{line}{' ' * (44 - len(line))}│")

    # Score
    lines.append("├─────────────────────────────────────────────┤")
    score = score_data["score"]
    status = score_data["status"]
    lines.append(f"│ Ready Score: {score}/100 ({status}){' ' * (20 - len(status))}│")
    lines.append("└─────────────────────────────────────────────┘")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run morning health check")
    parser.add_argument("--section", choices=["git", "services", "quality", "all"],
                        default="all", help="Section to check")
    parser.add_argument("--mode", choices=["check", "score", "report"],
                        default="report", help="Output mode")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    args = parser.parse_args()

    result = {
        "operation": "health_check",
        "section": args.section,
        "timestamp": datetime.now().isoformat()
    }

    git_status = {}
    service_status = {}
    quality_status = {}

    if args.section in ["git", "all"]:
        git_status = check_git_status()
        result["git"] = git_status

    if args.section in ["services", "all"]:
        service_status = check_services()
        result["services"] = service_status

    if args.section in ["quality", "all"]:
        quality_status = check_code_quality()
        result["quality"] = quality_status

    if args.mode in ["score", "report"]:
        if not git_status:
            git_status = check_git_status()
        if not service_status:
            service_status = check_services()
        if not quality_status:
            quality_status = check_code_quality()

        score_data = calculate_ready_score(git_status, service_status, quality_status)
        result["score"] = score_data

    if args.mode == "report" and args.format == "display":
        report = generate_morning_report(git_status, service_status, quality_status, score_data)
        print(report)
        return 0

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
