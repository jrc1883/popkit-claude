#!/usr/bin/env python3
"""
Project Deployment Detection Script.

Analyzes project state for deployment readiness.
Detects language, framework, GitHub configuration, and CI/CD setup.

Usage:
    python detect_project.py [--dir DIR] [--json]

Output:
    JSON object with detection results
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_language(project_dir: Path) -> Dict[str, str]:
    """Detect primary language and framework."""

    # JavaScript/TypeScript
    if (project_dir / "package.json").exists():
        try:
            pkg = json.loads((project_dir / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            # Check for TypeScript
            has_ts = "typescript" in deps or (project_dir / "tsconfig.json").exists()
            language = "typescript" if has_ts else "javascript"

            # Detect framework
            if "next" in deps:
                framework = "nextjs"
            elif "vite" in deps:
                framework = "vite"
            elif "react" in deps:
                framework = "react"
            elif "vue" in deps:
                framework = "vue"
            elif "svelte" in deps:
                framework = "svelte"
            elif "express" in deps:
                framework = "express"
            elif "@nestjs/core" in deps:
                framework = "nestjs"
            else:
                framework = "node"

            return {"language": language, "framework": framework}
        except Exception:
            return {"language": "javascript", "framework": "node"}

    # Python
    if (project_dir / "pyproject.toml").exists() or (project_dir / "requirements.txt").exists():
        framework = "python"

        # Check pyproject.toml
        if (project_dir / "pyproject.toml").exists():
            try:
                content = (project_dir / "pyproject.toml").read_text().lower()
                if "fastapi" in content:
                    framework = "fastapi"
                elif "django" in content:
                    framework = "django"
                elif "flask" in content:
                    framework = "flask"
            except Exception:
                pass

        # Check requirements.txt
        if framework == "python" and (project_dir / "requirements.txt").exists():
            try:
                content = (project_dir / "requirements.txt").read_text().lower()
                if "fastapi" in content:
                    framework = "fastapi"
                elif "django" in content:
                    framework = "django"
                elif "flask" in content:
                    framework = "flask"
            except Exception:
                pass

        # Check for Django manage.py
        if (project_dir / "manage.py").exists():
            framework = "django"

        return {"language": "python", "framework": framework}

    # Rust
    if (project_dir / "Cargo.toml").exists():
        return {"language": "rust", "framework": "cargo"}

    # Go
    if (project_dir / "go.mod").exists():
        return {"language": "go", "framework": "go"}

    # Java
    if (project_dir / "pom.xml").exists():
        return {"language": "java", "framework": "maven"}
    elif (project_dir / "build.gradle").exists():
        return {"language": "java", "framework": "gradle"}

    # C#
    if list(project_dir.glob("*.csproj")):
        return {"language": "csharp", "framework": "dotnet"}

    # Unknown
    return {"language": "unknown", "framework": "generic"}


def detect_github(project_dir: Path) -> Dict[str, Any]:
    """Detect GitHub configuration."""
    result = {
        "initialized": False,
        "repo": None,
        "default_branch": None,
        "has_actions": False
    }

    # Check if git is initialized
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        return result

    result["initialized"] = True

    try:
        # Get remote URL
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )

        if remote_result.returncode == 0:
            remote_url = remote_result.stdout.strip()

            # Extract repo from GitHub URL
            # Handles: git@github.com:owner/repo.git and https://github.com/owner/repo.git
            if "github.com" in remote_url:
                match = re.search(r'github\.com[:/](.+?)(?:\.git)?$', remote_url)
                if match:
                    result["repo"] = match.group(1)

        # Get default branch
        branch_result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )

        if branch_result.returncode == 0:
            branch_ref = branch_result.stdout.strip()
            # Extract branch name from refs/remotes/origin/main
            branch_match = re.search(r'refs/remotes/origin/(.+)$', branch_ref)
            if branch_match:
                result["default_branch"] = branch_match.group(1)

        # Fallback: try to get current branch
        if not result["default_branch"]:
            current_branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if current_branch_result.returncode == 0:
                current_branch = current_branch_result.stdout.strip()
                if current_branch:
                    result["default_branch"] = current_branch
                else:
                    # Default to 'main' if we can't detect
                    result["default_branch"] = "main"

    except (subprocess.TimeoutExpired, Exception):
        pass

    # Check for GitHub Actions
    workflows_dir = project_dir / ".github" / "workflows"
    if workflows_dir.exists() and workflows_dir.is_dir():
        result["has_actions"] = True

    return result


def detect_cicd(project_dir: Path) -> Dict[str, Any]:
    """Detect CI/CD configuration."""
    result = {
        "detected": False,
        "platform": None,
        "workflow_count": 0
    }

    # GitHub Actions
    workflows_dir = project_dir / ".github" / "workflows"
    if workflows_dir.exists() and workflows_dir.is_dir():
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        if workflow_files:
            result["detected"] = True
            result["platform"] = "github-actions"
            result["workflow_count"] = len(workflow_files)
            return result

    # GitLab CI
    if (project_dir / ".gitlab-ci.yml").exists():
        result["detected"] = True
        result["platform"] = "gitlab-ci"
        result["workflow_count"] = 1
        return result

    # CircleCI
    if (project_dir / ".circleci" / "config.yml").exists():
        result["detected"] = True
        result["platform"] = "circleci"
        result["workflow_count"] = 1
        return result

    # Azure Pipelines
    if (project_dir / "azure-pipelines.yml").exists():
        result["detected"] = True
        result["platform"] = "azure-pipelines"
        result["workflow_count"] = 1
        return result

    # Jenkins
    if (project_dir / "Jenkinsfile").exists():
        result["detected"] = True
        result["platform"] = "jenkins"
        result["workflow_count"] = 1
        return result

    return result


def analyze_gaps(github: Dict[str, Any], cicd: Dict[str, Any]) -> Dict[str, bool]:
    """Analyze what's missing for deployment."""
    return {
        "needs_github": not github["initialized"] or github["repo"] is None,
        "needs_cicd": not cicd["detected"],
        "needs_target_configs": True  # Always true initially, will be updated by setup
    }


def detect_project_state(project_dir: Path) -> Dict[str, Any]:
    """Full project deployment state detection."""

    # Detect all components
    lang_info = detect_language(project_dir)
    github_info = detect_github(project_dir)
    cicd_info = detect_cicd(project_dir)
    gaps = analyze_gaps(github_info, cicd_info)

    # Determine overall state
    if gaps["needs_github"]:
        state = "fresh"
    elif gaps["needs_cicd"]:
        state = "needs-cicd"
    else:
        state = "needs-targets"

    return {
        "language": lang_info["language"],
        "framework": lang_info["framework"],
        "github": github_info,
        "cicd": cicd_info,
        "gaps": gaps,
        "detected_state": state
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Detect project deployment state")
    parser.add_argument("--dir", default=".", help="Project directory")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()

    if not project_dir.exists():
        print(json.dumps({
            "error": "Directory not found",
            "path": str(project_dir)
        }))
        return 1

    # Run detection
    result = detect_project_state(project_dir)

    # Add metadata
    output = {
        "operation": "detect_project_state",
        "directory": str(project_dir),
        **result
    }

    # Output
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("Project Deployment Detection")
        print("=" * 50)
        print(f"Directory: {project_dir}")
        print(f"Language: {result['language']}")
        print(f"Framework: {result['framework']}")
        print(f"\nGitHub:")
        print(f"  Initialized: {result['github']['initialized']}")
        print(f"  Repo: {result['github']['repo'] or 'Not configured'}")
        print(f"  Branch: {result['github']['default_branch'] or 'N/A'}")
        print(f"  Actions: {'Yes' if result['github']['has_actions'] else 'No'}")
        print(f"\nCI/CD:")
        print(f"  Detected: {result['cicd']['detected']}")
        print(f"  Platform: {result['cicd']['platform'] or 'None'}")
        print(f"  Workflows: {result['cicd']['workflow_count']}")
        print(f"\nGaps:")
        print(f"  Needs GitHub: {result['gaps']['needs_github']}")
        print(f"  Needs CI/CD: {result['gaps']['needs_cicd']}")
        print(f"  Needs Target Configs: {result['gaps']['needs_target_configs']}")
        print(f"\nDetected State: {result['detected_state']}")
        print("\nJSON output:")
        print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
