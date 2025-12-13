#!/usr/bin/env python3
"""
Nightly Sleep Score Calculator.

Calculate Sleep Score and identify cleanup targets.

Usage:
    python calculate_sleep_score.py [--section SECTION] [--mode MODE]

Sections:
    git      - Git status and uncommitted changes
    branches - Stale branch detection
    cleanup  - Cleanup target identification
    security - Security audit status
    all      - All sections

Modes:
    check - Run checks only
    score - Calculate Sleep Score

Output:
    JSON object with audit status and score
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
    """Check git status for uncommitted changes."""
    status = {
        "clean": True,
        "uncommitted_count": 0,
        "staged_count": 0,
        "untracked_count": 0,
        "issues": []
    }

    # Check uncommitted changes
    output, ok = run_command("git status --porcelain")
    if ok and output:
        lines = output.split('\n')
        for line in lines:
            if line.strip():
                if line.startswith('??'):
                    status["untracked_count"] += 1
                elif line.startswith('A ') or line.startswith('M ') or line.startswith('D '):
                    status["staged_count"] += 1
                else:
                    status["uncommitted_count"] += 1

        total = status["uncommitted_count"] + status["staged_count"] + status["untracked_count"]
        if total > 0:
            status["clean"] = False
            status["issues"].append(f"{total} uncommitted changes")

    return status


def check_stale_branches() -> Dict[str, Any]:
    """Check for stale branches that could be cleaned up."""
    result = {
        "merged_branches": [],
        "stale_branches": [],
        "total_branches": 0
    }

    # Get all local branches
    branches, ok = run_command("git branch")
    if ok:
        result["total_branches"] = len([b for b in branches.split('\n') if b.strip()])

    # Get merged branches
    merged, ok = run_command("git branch --merged main 2>/dev/null || git branch --merged master")
    if ok:
        for branch in merged.split('\n'):
            branch = branch.strip().lstrip('* ')
            if branch and branch not in ['main', 'master']:
                result["merged_branches"].append(branch)

    return result


def identify_cleanup_targets() -> Dict[str, Any]:
    """Identify files and directories that could be cleaned up."""
    targets = {
        "build_artifacts": [],
        "caches": [],
        "temp_files": [],
        "old_logs": [],
        "total_size_mb": 0
    }

    # Build artifacts
    build_dirs = ['.next', 'out', 'dist', 'build', 'target/debug']
    for dir_name in build_dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            size = get_directory_size(path)
            targets["build_artifacts"].append({
                "path": dir_name,
                "size_mb": round(size / (1024 * 1024), 2)
            })
            targets["total_size_mb"] += size / (1024 * 1024)

    # Caches
    cache_dirs = ['node_modules/.cache', '.eslintcache', '.tsbuildinfo', '.pytest_cache', '__pycache__']
    for dir_name in cache_dirs:
        path = Path(dir_name)
        if path.exists():
            if path.is_dir():
                size = get_directory_size(path)
            else:
                size = path.stat().st_size
            targets["caches"].append({
                "path": dir_name,
                "size_mb": round(size / (1024 * 1024), 2)
            })
            targets["total_size_mb"] += size / (1024 * 1024)

    # Old log files (older than 7 days)
    log_count = 0
    log_size = 0
    for log_file in Path('.').rglob('*.log'):
        try:
            if (datetime.now().timestamp() - log_file.stat().st_mtime) > (7 * 24 * 3600):
                log_count += 1
                log_size += log_file.stat().st_size
        except Exception:
            pass

    if log_count > 0:
        targets["old_logs"].append({
            "count": log_count,
            "size_mb": round(log_size / (1024 * 1024), 2)
        })
        targets["total_size_mb"] += log_size / (1024 * 1024)

    targets["total_size_mb"] = round(targets["total_size_mb"], 2)
    return targets


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


def check_security_audit() -> Dict[str, Any]:
    """Run security audit check."""
    result = {
        "clean": True,
        "vulnerabilities": 0,
        "critical": 0,
        "high": 0,
        "output": ""
    }

    # Run npm audit
    output, ok = run_command("npm audit --json 2>/dev/null")
    if output:
        try:
            audit_data = json.loads(output)
            metadata = audit_data.get("metadata", {}).get("vulnerabilities", {})
            result["critical"] = metadata.get("critical", 0)
            result["high"] = metadata.get("high", 0)
            result["vulnerabilities"] = sum(metadata.values())
            result["clean"] = result["vulnerabilities"] == 0
        except json.JSONDecodeError:
            # Parse text output
            if "found 0 vulnerabilities" in output.lower():
                result["clean"] = True
            elif "vulnerabilities" in output.lower():
                result["clean"] = False
            result["output"] = output[:500]

    return result


def check_session_saved() -> Dict[str, Any]:
    """Check if session state has been saved today."""
    result = {
        "saved": False,
        "last_update": None,
        "hours_ago": -1
    }

    status_paths = [
        Path(".claude/STATUS.json"),
        Path("STATUS.json"),
    ]

    for path in status_paths:
        if path.exists():
            try:
                status = json.loads(path.read_text())
                last_update = status.get("lastUpdate")
                if last_update:
                    result["last_update"] = last_update
                    # Parse timestamp
                    if last_update.endswith('Z'):
                        last_update = last_update[:-1]
                    dt = datetime.fromisoformat(last_update.replace('Z', ''))
                    hours_ago = (datetime.now() - dt).total_seconds() / 3600
                    result["hours_ago"] = round(hours_ago, 1)
                    result["saved"] = hours_ago < 24
                break
            except Exception:
                pass

    return result


def calculate_sleep_score(
    git: Dict, branches: Dict, cleanup: Dict, security: Dict, session: Dict
) -> Dict[str, Any]:
    """Calculate Sleep Score (0-100)."""
    score = 0
    breakdown = []

    # No uncommitted changes (30 points)
    git_points = 30 if git.get("clean", False) else 0
    score += git_points
    breakdown.append({"category": "No Uncommitted Changes", "points": git_points, "max": 30})

    # Session state saved (20 points)
    session_points = 20 if session.get("saved", False) else 0
    score += session_points
    breakdown.append({"category": "Session State Saved", "points": session_points, "max": 20})

    # Git maintenance (15 points) - give points if few merged branches
    branch_points = 15 if len(branches.get("merged_branches", [])) <= 2 else 5
    score += branch_points
    breakdown.append({"category": "Git Maintenance Done", "points": branch_points, "max": 15})

    # Security audit clean (15 points)
    security_points = 15 if security.get("clean", True) else 0
    if security.get("critical", 0) > 0:
        security_points = 0
    elif security.get("high", 0) > 0:
        security_points = 5
    score += security_points
    breakdown.append({"category": "Security Audit Clean", "points": security_points, "max": 15})

    # Caches under limit (10 points) - under 500MB
    cache_size = cleanup.get("total_size_mb", 0)
    cache_points = 10 if cache_size < 500 else (5 if cache_size < 1000 else 0)
    score += cache_points
    breakdown.append({"category": "Caches Under Limit", "points": cache_points, "max": 10})

    # Logs rotated (10 points)
    old_logs = cleanup.get("old_logs", [])
    log_points = 10 if not old_logs else 0
    score += log_points
    breakdown.append({"category": "Logs Rotated", "points": log_points, "max": 10})

    # Determine status
    if score >= 90:
        status = "excellent"
        message = "Ready for a restful night!"
    elif score >= 70:
        status = "good"
        message = "Good shape, minor items remain"
    elif score >= 50:
        status = "fair"
        message = "Some cleanup recommended"
    else:
        status = "needs_attention"
        message = "Please address issues before ending"

    return {
        "score": score,
        "max_score": 100,
        "status": status,
        "message": message,
        "breakdown": breakdown
    }


def generate_nightly_report(
    git: Dict, branches: Dict, cleanup: Dict, security: Dict, session: Dict, score_data: Dict
) -> str:
    """Generate formatted nightly report."""
    lines = [
        "┌─────────────────────────────────────────────┐",
        f"│ 🌙 Nightly Cleanup Report                    │",
        f"│ {datetime.now().strftime('%Y-%m-%d %H:%M')}                           │",
        "├─────────────────────────────────────────────┤",
    ]

    # Git status
    uncommitted = git.get("uncommitted_count", 0) + git.get("staged_count", 0) + git.get("untracked_count", 0)
    git_status = "✓ Clean" if uncommitted == 0 else f"✗ {uncommitted} changes"
    lines.append(f"│ Git: {git_status}{' ' * (38 - len(git_status))}│")

    # Merged branches
    merged = len(branches.get("merged_branches", []))
    if merged > 0:
        lines.append(f"│ Stale branches: {merged} can be deleted{' ' * (22 - len(str(merged)))}│")

    # Cleanup targets
    total_mb = cleanup.get("total_size_mb", 0)
    lines.append(f"│ Cleanup available: {total_mb:.1f} MB{' ' * (22 - len(f'{total_mb:.1f}'))}│")

    # Security
    vulns = security.get("vulnerabilities", 0)
    sec_status = "✓ Clean" if vulns == 0 else f"✗ {vulns} vulnerabilities"
    lines.append(f"│ Security: {sec_status}{' ' * (33 - len(sec_status))}│")

    # Score
    lines.append("├─────────────────────────────────────────────┤")
    score = score_data["score"]
    status = score_data["status"]
    lines.append(f"│ Sleep Score: {score}/100 ({status}){' ' * (20 - len(status))}│")
    lines.append("└─────────────────────────────────────────────┘")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Calculate nightly sleep score")
    parser.add_argument("--section", choices=["git", "branches", "cleanup", "security", "session", "all"],
                        default="all", help="Section to check")
    parser.add_argument("--mode", choices=["check", "score", "report"],
                        default="report", help="Output mode")
    parser.add_argument("--format", choices=["json", "display"], default="json",
                        help="Output format")
    args = parser.parse_args()

    result = {
        "operation": "calculate_sleep_score",
        "section": args.section,
        "timestamp": datetime.now().isoformat()
    }

    git_status = {}
    branches_status = {}
    cleanup_targets = {}
    security_status = {}
    session_status = {}

    if args.section in ["git", "all"]:
        git_status = check_git_status()
        result["git"] = git_status

    if args.section in ["branches", "all"]:
        branches_status = check_stale_branches()
        result["branches"] = branches_status

    if args.section in ["cleanup", "all"]:
        cleanup_targets = identify_cleanup_targets()
        result["cleanup"] = cleanup_targets

    if args.section in ["security", "all"]:
        security_status = check_security_audit()
        result["security"] = security_status

    if args.section in ["session", "all"]:
        session_status = check_session_saved()
        result["session"] = session_status

    if args.mode in ["score", "report"]:
        # Ensure all data is gathered
        if not git_status:
            git_status = check_git_status()
        if not branches_status:
            branches_status = check_stale_branches()
        if not cleanup_targets:
            cleanup_targets = identify_cleanup_targets()
        if not security_status:
            security_status = check_security_audit()
        if not session_status:
            session_status = check_session_saved()

        score_data = calculate_sleep_score(
            git_status, branches_status, cleanup_targets, security_status, session_status
        )
        result["score"] = score_data

    if args.mode == "report" and args.format == "display":
        report = generate_nightly_report(
            git_status, branches_status, cleanup_targets, security_status, session_status, score_data
        )
        print(report)
        return 0

    result["success"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
