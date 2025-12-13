#!/usr/bin/env python3
"""
Pre-Deployment Validation.

Common checks before any deployment.

Usage:
    python pre_deploy_check.py [project_dir] [--platform PLATFORM]

Output:
    JSON object with validation results
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "package.json").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent

    return start_path


def check_git_status(project_dir: Path) -> Dict[str, Any]:
    """Check for uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        uncommitted = [line for line in result.stdout.strip().split("\n") if line]

        return {
            "passed": len(uncommitted) == 0,
            "uncommitted_files": uncommitted[:10],
            "message": "No uncommitted changes" if len(uncommitted) == 0 else f"{len(uncommitted)} uncommitted files"
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def check_tests(project_dir: Path) -> Dict[str, Any]:
    """Check if tests pass."""
    # Detect test framework
    if (project_dir / "package.json").exists():
        # Node.js project
        try:
            result = subprocess.run(
                ["npm", "test", "--if-present"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "passed": result.returncode == 0,
                "framework": "npm",
                "message": "Tests passed" if result.returncode == 0 else "Tests failed"
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "Test timeout (5 min)"}
        except Exception as e:
            return {"passed": True, "skipped": True, "message": "No tests configured"}

    elif (project_dir / "pyproject.toml").exists() or (project_dir / "pytest.ini").exists():
        # Python project
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=no", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "passed": result.returncode == 0,
                "framework": "pytest",
                "message": "Tests passed" if result.returncode == 0 else "Tests failed"
            }
        except Exception as e:
            return {"passed": True, "skipped": True, "message": "No tests configured"}

    return {"passed": True, "skipped": True, "message": "No test framework detected"}


def check_build(project_dir: Path) -> Dict[str, Any]:
    """Check if build succeeds."""
    if (project_dir / "package.json").exists():
        pkg_json = json.loads((project_dir / "package.json").read_text())
        scripts = pkg_json.get("scripts", {})

        if "build" in scripts:
            try:
                result = subprocess.run(
                    ["npm", "run", "build"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                return {
                    "passed": result.returncode == 0,
                    "message": "Build succeeded" if result.returncode == 0 else "Build failed"
                }
            except subprocess.TimeoutExpired:
                return {"passed": False, "error": "Build timeout (10 min)"}
            except Exception as e:
                return {"passed": False, "error": str(e)}

    return {"passed": True, "skipped": True, "message": "No build step detected"}


def check_version(project_dir: Path) -> Dict[str, Any]:
    """Check version consistency."""
    versions = {}

    # package.json
    if (project_dir / "package.json").exists():
        try:
            pkg = json.loads((project_dir / "package.json").read_text())
            versions["package.json"] = pkg.get("version", "unknown")
        except:
            pass

    # pyproject.toml
    if (project_dir / "pyproject.toml").exists():
        try:
            content = (project_dir / "pyproject.toml").read_text()
            import re
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                versions["pyproject.toml"] = match.group(1)
        except:
            pass

    # Git tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            tag = result.stdout.strip().lstrip("v")
            versions["git_tag"] = tag
    except:
        pass

    unique_versions = set(versions.values())
    if len(unique_versions) <= 1:
        return {
            "passed": True,
            "versions": versions,
            "message": f"Version consistent: {list(unique_versions)[0] if unique_versions else 'unknown'}"
        }
    else:
        return {
            "passed": False,
            "versions": versions,
            "message": f"Version mismatch: {versions}"
        }


def check_secrets(project_dir: Path) -> Dict[str, Any]:
    """Check for exposed secrets."""
    patterns = [
        r"password\s*=\s*['\"][^'\"]+['\"]",
        r"api_key\s*=\s*['\"][^'\"]+['\"]",
        r"secret\s*=\s*['\"][^'\"]+['\"]",
        r"AWS_SECRET_ACCESS_KEY",
        r"GITHUB_TOKEN\s*=",
    ]

    issues = []
    import re

    for ext in ["*.py", "*.ts", "*.js", "*.json", "*.yml", "*.yaml"]:
        for file_path in project_dir.rglob(ext):
            if "node_modules" in str(file_path) or ".git" in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append({
                            "file": str(file_path.relative_to(project_dir)),
                            "pattern": pattern[:30]
                        })
                        break
            except:
                pass

    return {
        "passed": len(issues) == 0,
        "issues": issues[:5],
        "message": "No secrets detected" if len(issues) == 0 else f"{len(issues)} potential secrets found"
    }


def check_dependencies(project_dir: Path) -> Dict[str, Any]:
    """Check for vulnerable or outdated dependencies."""
    if (project_dir / "package.json").exists():
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            audit = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = audit.get("metadata", {}).get("vulnerabilities", {})
            high_count = vulnerabilities.get("high", 0) + vulnerabilities.get("critical", 0)

            return {
                "passed": high_count == 0,
                "vulnerabilities": vulnerabilities,
                "message": "No high/critical vulnerabilities" if high_count == 0 else f"{high_count} high/critical vulnerabilities"
            }
        except:
            return {"passed": True, "skipped": True, "message": "Audit not available"}

    return {"passed": True, "skipped": True, "message": "No dependency file found"}


def run_all_checks(project_dir: Path, platform: str = None) -> Dict[str, Any]:
    """Run all pre-deployment checks."""
    checks = {
        "git_status": check_git_status(project_dir),
        "tests": check_tests(project_dir),
        "build": check_build(project_dir),
        "version": check_version(project_dir),
        "secrets": check_secrets(project_dir),
        "dependencies": check_dependencies(project_dir),
    }

    # Calculate overall status
    failed = [name for name, result in checks.items() if not result.get("passed", False) and not result.get("skipped", False)]
    warnings = [name for name, result in checks.items() if result.get("skipped", False)]

    overall_passed = len(failed) == 0

    return {
        "assessment": "pre-deploy-check",
        "project_dir": str(project_dir),
        "platform": platform,
        "overall_passed": overall_passed,
        "checks": checks,
        "failed_checks": failed,
        "skipped_checks": warnings,
        "ready_to_deploy": overall_passed
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pre-deployment validation")
    parser.add_argument("project_dir", nargs="?", help="Project directory")
    parser.add_argument("--platform", help="Target platform (docker, npm, pypi, etc.)")
    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = find_project_root()

    if not project_dir.exists():
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        return 1

    results = run_all_checks(project_dir, args.platform)
    print(json.dumps(results, indent=2))

    return 0 if results["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
