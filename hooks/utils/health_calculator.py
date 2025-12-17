#!/usr/bin/env python3
"""
Project Health Score Calculator

Calculates health scores for projects based on:
- Git status (20 pts): Clean working tree, uncommitted changes, unpushed commits
- Build status (20 pts): Last build result, warnings
- Test coverage (20 pts): Coverage percentage
- Issue health (20 pts): Stale issues
- Activity (20 pts): Recent activity

Part of the popkit plugin system.
"""

import os
import subprocess
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone, timedelta
from pathlib import Path


# Score weights (total = 100)
WEIGHTS = {
    "git": 20,
    "build": 20,
    "tests": 20,
    "issues": 20,
    "activity": 20
}


def run_command(cmd: List[str], cwd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr.

    Args:
        cmd: Command as list of strings
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# =============================================================================
# Individual Score Calculators
# =============================================================================

def calculate_git_score(project_path: str) -> Tuple[int, Dict[str, Any]]:
    """Calculate git status score.

    Score breakdown:
    - Clean working tree: +20
    - Uncommitted changes: -5 per 10 files
    - Unpushed commits: -5 per commit

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (score, details dict)
    """
    if not os.path.isdir(os.path.join(project_path, ".git")):
        return WEIGHTS["git"], {"status": "not_git", "message": "Not a git repository"}

    score = WEIGHTS["git"]
    details = {}

    # Check for uncommitted changes
    code, stdout, _ = run_command(["git", "status", "--porcelain"], project_path)
    if code != 0:
        return 0, {"status": "error", "message": "Failed to run git status"}

    uncommitted = len([line for line in stdout.strip().split("\n") if line.strip()])
    details["uncommitted_files"] = uncommitted

    if uncommitted > 0:
        penalty = min(15, (uncommitted // 10 + 1) * 5)
        score -= penalty
        details["uncommitted_penalty"] = penalty

    # Check for unpushed commits
    code, stdout, _ = run_command(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        project_path
    )

    if code == 0:
        try:
            unpushed = int(stdout.strip())
            details["unpushed_commits"] = unpushed
            if unpushed > 0:
                penalty = min(10, unpushed * 5)
                score -= penalty
                details["unpushed_penalty"] = penalty
        except ValueError:
            details["unpushed_commits"] = 0
    else:
        # No upstream configured
        details["unpushed_commits"] = "no upstream"

    details["score"] = max(0, score)
    return max(0, score), details


def calculate_build_score(project_path: str) -> Tuple[int, Dict[str, Any]]:
    """Calculate build status score.

    Score breakdown:
    - Last build passed: +20
    - Build warnings: -2 per warning (max -10)
    - Build failed: 0

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (score, details dict)
    """
    details = {}

    # Check for various build systems
    has_package = os.path.isfile(os.path.join(project_path, "package.json"))
    has_pyproject = os.path.isfile(os.path.join(project_path, "pyproject.toml"))
    has_cargo = os.path.isfile(os.path.join(project_path, "Cargo.toml"))

    if not (has_package or has_pyproject or has_cargo):
        return WEIGHTS["build"], {"status": "no_build", "message": "No build system detected"}

    # For now, check TypeScript compilation for Node projects
    if has_package:
        # Check if there's a tsconfig
        if os.path.isfile(os.path.join(project_path, "tsconfig.json")):
            code, stdout, stderr = run_command(
                ["npx", "tsc", "--noEmit"],
                project_path,
                timeout=120
            )

            if code == 0:
                details["status"] = "passed"
                details["message"] = "TypeScript compilation successful"
                return WEIGHTS["build"], details
            else:
                # Count errors
                error_count = stderr.count("error TS")
                warning_count = stderr.count("warning TS")

                details["errors"] = error_count
                details["warnings"] = warning_count

                if error_count > 0:
                    details["status"] = "failed"
                    details["message"] = f"{error_count} TypeScript errors"
                    return 0, details
                else:
                    # Only warnings
                    penalty = min(10, warning_count * 2)
                    details["status"] = "warnings"
                    details["message"] = f"{warning_count} warnings"
                    return max(0, WEIGHTS["build"] - penalty), details
        else:
            # No TypeScript, assume OK
            details["status"] = "no_typescript"
            return WEIGHTS["build"], details

    # For Python projects
    if has_pyproject:
        # Try running type check with mypy if installed
        code, stdout, stderr = run_command(
            ["python", "-m", "mypy", "--version"],
            project_path,
            timeout=10
        )

        if code == 0:
            # mypy is installed, run it
            code, stdout, stderr = run_command(
                ["python", "-m", "mypy", "."],
                project_path,
                timeout=120
            )

            if code == 0:
                details["status"] = "passed"
                return WEIGHTS["build"], details
            else:
                error_count = stderr.count("error:")
                details["status"] = "failed" if error_count > 0 else "passed"
                details["errors"] = error_count
                return 0 if error_count > 0 else WEIGHTS["build"], details
        else:
            details["status"] = "no_mypy"
            return WEIGHTS["build"], details

    # For Rust projects
    if has_cargo:
        code, stdout, stderr = run_command(
            ["cargo", "check"],
            project_path,
            timeout=300
        )

        if code == 0:
            details["status"] = "passed"
            return WEIGHTS["build"], details
        else:
            details["status"] = "failed"
            return 0, details

    return WEIGHTS["build"], {"status": "unknown", "message": "Could not determine build status"}


def calculate_test_score(project_path: str) -> Tuple[int, Dict[str, Any]]:
    """Calculate test coverage score.

    Score breakdown:
    - >80% coverage: +20
    - 60-80%: +15
    - 40-60%: +10
    - <40%: +5
    - No tests: +5

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (score, details dict)
    """
    details = {}

    # Check for test directories
    test_dirs = [
        "tests", "test", "__tests__", "spec",
        "src/tests", "src/__tests__"
    ]

    has_tests = False
    for test_dir in test_dirs:
        if os.path.isdir(os.path.join(project_path, test_dir)):
            has_tests = True
            break

    # Also check for test files
    has_package = os.path.isfile(os.path.join(project_path, "package.json"))
    if has_package:
        # Check for common test file patterns
        for root, dirs, files in os.walk(project_path):
            if "node_modules" in root:
                continue
            for f in files:
                if f.endswith(".test.ts") or f.endswith(".spec.ts") or f.endswith(".test.js"):
                    has_tests = True
                    break
            if has_tests:
                break

    if not has_tests:
        details["status"] = "no_tests"
        details["message"] = "No test directory or files found"
        return 5, details

    # Try to get coverage info
    # For Node.js projects, check for coverage directory
    coverage_path = os.path.join(project_path, "coverage", "coverage-summary.json")
    if os.path.isfile(coverage_path):
        try:
            with open(coverage_path, "r", encoding="utf-8") as f:
                coverage_data = json.load(f)
                total = coverage_data.get("total", {})
                lines = total.get("lines", {}).get("pct", 0)
                branches = total.get("branches", {}).get("pct", 0)
                functions = total.get("functions", {}).get("pct", 0)

                avg_coverage = (lines + branches + functions) / 3

                details["status"] = "coverage_found"
                details["lines"] = lines
                details["branches"] = branches
                details["functions"] = functions
                details["average"] = avg_coverage

                if avg_coverage >= 80:
                    return WEIGHTS["tests"], details
                elif avg_coverage >= 60:
                    return 15, details
                elif avg_coverage >= 40:
                    return 10, details
                else:
                    return 5, details
        except (json.JSONDecodeError, IOError):
            pass

    # No coverage data, but tests exist
    details["status"] = "tests_exist"
    details["message"] = "Tests found but no coverage data"
    return 10, details  # Middle score for having tests without coverage


def calculate_issue_score(project_path: str) -> Tuple[int, Dict[str, Any]]:
    """Calculate issue health score.

    Score breakdown:
    - No stale issues: +20
    - -2 per stale issue (>30 days)
    - Max penalty: -15

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (score, details dict)
    """
    details = {}

    # Check if it's a GitHub repo
    if not os.path.isdir(os.path.join(project_path, ".git")):
        return WEIGHTS["issues"], {"status": "no_git", "message": "Not a git repository"}

    # Try to get repo from remote
    code, stdout, _ = run_command(
        ["git", "config", "--get", "remote.origin.url"],
        project_path
    )

    if code != 0 or not stdout.strip():
        return WEIGHTS["issues"], {"status": "no_remote", "message": "No remote configured"}

    import re
    match = re.search(r'github\.com[:/]([^/]+/[^/\.]+)', stdout.strip())
    if not match:
        return WEIGHTS["issues"], {"status": "not_github", "message": "Not a GitHub repository"}

    repo = match.group(1)
    details["repo"] = repo

    # Use gh CLI to get open issues
    code, stdout, stderr = run_command(
        ["gh", "issue", "list", "--repo", repo, "--state", "open", "--json", "number,createdAt", "--limit", "100"],
        project_path,
        timeout=30
    )

    if code != 0:
        details["status"] = "gh_error"
        details["message"] = "Failed to fetch issues (gh CLI not available or not authenticated)"
        return WEIGHTS["issues"], details

    try:
        issues = json.loads(stdout)
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(days=30)

        stale_count = 0
        for issue in issues:
            created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
            if created < stale_threshold:
                stale_count += 1

        details["total_open"] = len(issues)
        details["stale_count"] = stale_count
        details["status"] = "success"

        if stale_count == 0:
            return WEIGHTS["issues"], details
        else:
            penalty = min(15, stale_count * 2)
            return max(5, WEIGHTS["issues"] - penalty), details

    except (json.JSONDecodeError, KeyError):
        details["status"] = "parse_error"
        return WEIGHTS["issues"], details


def calculate_activity_score(project_path: str, last_active: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Calculate activity score.

    Score breakdown:
    - Active today: +20
    - This week: +15
    - This month: +10
    - Older: +5

    Args:
        project_path: Path to project directory
        last_active: Optional ISO timestamp override

    Returns:
        Tuple of (score, details dict)
    """
    details = {}
    now = datetime.now(timezone.utc)

    # Try to get from git log
    code, stdout, _ = run_command(
        ["git", "log", "-1", "--format=%cI"],
        project_path
    )

    if code == 0 and stdout.strip():
        try:
            last_commit = datetime.fromisoformat(stdout.strip())
            diff = now - last_commit

            details["last_commit"] = stdout.strip()
            details["days_ago"] = diff.days

            if diff.days == 0:
                details["status"] = "active_today"
                return WEIGHTS["activity"], details
            elif diff.days <= 7:
                details["status"] = "active_week"
                return 15, details
            elif diff.days <= 30:
                details["status"] = "active_month"
                return 10, details
            else:
                details["status"] = "inactive"
                return 5, details

        except ValueError:
            pass

    # Fallback to last_active parameter or file modification time
    if last_active:
        try:
            dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            diff = now - dt

            details["last_active"] = last_active
            details["days_ago"] = diff.days

            if diff.days == 0:
                return WEIGHTS["activity"], details
            elif diff.days <= 7:
                return 15, details
            elif diff.days <= 30:
                return 10, details
            else:
                return 5, details
        except ValueError:
            pass

    details["status"] = "unknown"
    return 10, details  # Default middle score


# =============================================================================
# Main Health Calculator
# =============================================================================

def calculate_health_score(
    project_path: str,
    last_active: Optional[str] = None,
    skip_slow: bool = False
) -> Dict[str, Any]:
    """Calculate overall health score for a project.

    Args:
        project_path: Path to project directory
        last_active: Optional last active timestamp
        skip_slow: Skip slow checks (build, issues)

    Returns:
        Dict with total score and breakdown
    """
    project_path = os.path.abspath(project_path)

    if not os.path.isdir(project_path):
        return {
            "score": 0,
            "error": "Project directory not found",
            "path": project_path
        }

    # Calculate individual scores
    git_score, git_details = calculate_git_score(project_path)

    if skip_slow:
        build_score = WEIGHTS["build"]
        build_details = {"status": "skipped"}
        issue_score = WEIGHTS["issues"]
        issue_details = {"status": "skipped"}
    else:
        build_score, build_details = calculate_build_score(project_path)
        issue_score, issue_details = calculate_issue_score(project_path)

    test_score, test_details = calculate_test_score(project_path)
    activity_score, activity_details = calculate_activity_score(project_path, last_active)

    total_score = git_score + build_score + test_score + issue_score + activity_score

    return {
        "score": total_score,
        "path": project_path,
        "breakdown": {
            "git": {"score": git_score, "max": WEIGHTS["git"], "details": git_details},
            "build": {"score": build_score, "max": WEIGHTS["build"], "details": build_details},
            "tests": {"score": test_score, "max": WEIGHTS["tests"], "details": test_details},
            "issues": {"score": issue_score, "max": WEIGHTS["issues"], "details": issue_details},
            "activity": {"score": activity_score, "max": WEIGHTS["activity"], "details": activity_details}
        },
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


def calculate_quick_health(project_path: str) -> int:
    """Calculate a quick health score (git + activity only).

    Args:
        project_path: Path to project directory

    Returns:
        Quick health score (0-40, scaled to 0-100)
    """
    git_score, _ = calculate_git_score(project_path)
    activity_score, _ = calculate_activity_score(project_path)

    # Scale from 0-40 to 0-100
    quick_score = git_score + activity_score
    return int(quick_score * 2.5)


def format_health_report(result: Dict[str, Any]) -> str:
    """Format health calculation result as readable report.

    Args:
        result: Health calculation result dict

    Returns:
        Formatted report string
    """
    lines = []

    score = result.get("score", 0)
    path = result.get("path", "Unknown")

    lines.append("")
    lines.append(f"Health Report: {os.path.basename(path)}")
    lines.append("=" * 50)
    lines.append("")

    # Overall score with visual bar
    bar_filled = int(score / 5)  # 20 segments for 100 points
    bar = "+" * bar_filled + "-" * (20 - bar_filled)
    lines.append(f"Overall Score: {score}/100  [{bar}]")
    lines.append("")

    # Breakdown
    lines.append("Breakdown:")
    lines.append("-" * 30)

    breakdown = result.get("breakdown", {})
    for category, data in breakdown.items():
        score_val = data.get("score", 0)
        max_val = data.get("max", 20)
        status = data.get("details", {}).get("status", "")

        icon = "+" if score_val >= max_val * 0.8 else ("~" if score_val >= max_val * 0.5 else "!")
        lines.append(f"  {icon} {category.capitalize():12} {score_val:>2}/{max_val}  ({status})")

    lines.append("")
    lines.append(f"Calculated: {result.get('timestamp', 'unknown')}")

    return "\n".join(lines)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        path = os.getcwd()
    else:
        path = sys.argv[1]

    # Check for --quick flag
    quick = "--quick" in sys.argv

    if quick:
        score = calculate_quick_health(path)
        print(f"Quick Health Score: {score}/100")
    else:
        result = calculate_health_score(path)
        print(format_health_report(result))
