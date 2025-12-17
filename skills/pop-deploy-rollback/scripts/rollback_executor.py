#!/usr/bin/env python3
"""
Rollback Executor Script.

Execute rollbacks across different deployment platforms.

Usage:
    python rollback_executor.py PLATFORM [--target VERSION] [--dry-run]

Output:
    JSON object with rollback results
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional


def rollback_docker(target: str = None, registry: str = None) -> Dict[str, Any]:
    """Rollback Docker deployment."""
    start_time = datetime.now()

    if target:
        # Pull and tag specific version as latest
        pull_result = subprocess.run(
            ["docker", "pull", target],
            capture_output=True,
            text=True
        )
        if pull_result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to pull {target}: {pull_result.stderr}"
            }

        # Extract image name and tag as latest
        if ":" in target:
            image_name = target.rsplit(":", 1)[0]
        else:
            image_name = target

        tag_result = subprocess.run(
            ["docker", "tag", target, f"{image_name}:latest"],
            capture_output=True,
            text=True
        )
        if tag_result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to tag: {tag_result.stderr}"
            }

        # Push if registry specified
        if registry:
            push_result = subprocess.run(
                ["docker", "push", f"{image_name}:latest"],
                capture_output=True,
                text=True
            )
            if push_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to push: {push_result.stderr}"
                }

    duration = (datetime.now() - start_time).total_seconds()
    return {
        "success": True,
        "platform": "docker",
        "target": target or "previous",
        "duration_seconds": round(duration, 2)
    }


def rollback_kubernetes(deployment: str, revision: int = None, namespace: str = "default") -> Dict[str, Any]:
    """Rollback Kubernetes deployment."""
    start_time = datetime.now()

    cmd = ["kubectl", "rollout", "undo", f"deployment/{deployment}", "-n", namespace]
    if revision:
        cmd.extend(["--to-revision", str(revision)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Wait for rollout to complete
        status_result = subprocess.run(
            ["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace, "--timeout=300s"],
            capture_output=True,
            text=True
        )

        duration = (datetime.now() - start_time).total_seconds()
        return {
            "success": status_result.returncode == 0,
            "platform": "kubernetes",
            "deployment": deployment,
            "revision": revision or "previous",
            "duration_seconds": round(duration, 2),
            "status": status_result.stdout.strip()
        }
    else:
        return {
            "success": False,
            "platform": "kubernetes",
            "error": result.stderr.strip()
        }


def rollback_vercel(deployment_url: str = None) -> Dict[str, Any]:
    """Rollback Vercel deployment."""
    start_time = datetime.now()

    cmd = ["vercel", "rollback", "--yes"]
    if deployment_url:
        cmd.append(deployment_url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        return {
            "success": True,
            "platform": "vercel",
            "target": deployment_url or "previous",
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "platform": "vercel",
            "error": result.stderr.strip()
        }


def rollback_netlify(deploy_id: str = None) -> Dict[str, Any]:
    """Rollback Netlify deployment."""
    start_time = datetime.now()

    if deploy_id:
        cmd = ["netlify", "api", "restoreSiteDeploy",
               "--data", json.dumps({"deploy_id": deploy_id})]
    else:
        cmd = ["netlify", "rollback"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        return {
            "success": True,
            "platform": "netlify",
            "deploy_id": deploy_id or "previous",
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "platform": "netlify",
            "error": result.stderr.strip()
        }


def rollback_npm(package: str, bad_version: str, message: str = None) -> Dict[str, Any]:
    """Deprecate npm package version (closest to rollback)."""
    start_time = datetime.now()

    deprecation_msg = message or f"Critical bug in {bad_version}, please use previous version"
    result = subprocess.run(
        ["npm", "deprecate", f"{package}@{bad_version}", deprecation_msg],
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        return {
            "success": True,
            "platform": "npm",
            "action": "deprecate",
            "package": package,
            "version": bad_version,
            "message": deprecation_msg,
            "duration_seconds": round(duration, 2),
            "note": "npm packages cannot be unpublished after 72h. Deprecation warns users."
        }
    else:
        return {
            "success": False,
            "platform": "npm",
            "error": result.stderr.strip()
        }


def rollback_github_release(tag: str) -> Dict[str, Any]:
    """Mark GitHub release as pre-release (soft rollback)."""
    start_time = datetime.now()

    result = subprocess.run(
        ["gh", "release", "edit", tag, "--prerelease"],
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        return {
            "success": True,
            "platform": "github-releases",
            "action": "mark_prerelease",
            "tag": tag,
            "duration_seconds": round(duration, 2),
            "note": "Release marked as pre-release. Users will see previous stable release."
        }
    else:
        return {
            "success": False,
            "platform": "github-releases",
            "error": result.stderr.strip()
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Execute deployment rollback")
    parser.add_argument("platform", choices=["docker", "kubernetes", "vercel", "netlify", "npm", "github-releases"])
    parser.add_argument("--target", help="Target version/deployment to rollback to")
    parser.add_argument("--deployment", help="Kubernetes deployment name")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--revision", type=int, help="Kubernetes revision number")
    parser.add_argument("--package", help="npm package name")
    parser.add_argument("--message", help="Deprecation message for npm")
    parser.add_argument("--registry", help="Docker registry")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps({
            "operation": "rollback",
            "dry_run": True,
            "platform": args.platform,
            "target": args.target or "previous"
        }, indent=2))
        return 0

    # Execute platform-specific rollback
    if args.platform == "docker":
        result = rollback_docker(args.target, args.registry)
    elif args.platform == "kubernetes":
        if not args.deployment:
            print(json.dumps({
                "success": False,
                "error": "Kubernetes rollback requires --deployment"
            }, indent=2))
            return 1
        result = rollback_kubernetes(args.deployment, args.revision, args.namespace)
    elif args.platform == "vercel":
        result = rollback_vercel(args.target)
    elif args.platform == "netlify":
        result = rollback_netlify(args.target)
    elif args.platform == "npm":
        if not args.package or not args.target:
            print(json.dumps({
                "success": False,
                "error": "npm rollback requires --package and --target (version)"
            }, indent=2))
            return 1
        result = rollback_npm(args.package, args.target, args.message)
    elif args.platform == "github-releases":
        if not args.target:
            print(json.dumps({
                "success": False,
                "error": "github-releases rollback requires --target (tag)"
            }, indent=2))
            return 1
        result = rollback_github_release(args.target)
    else:
        result = {"success": False, "error": f"Unsupported platform: {args.platform}"}

    print(json.dumps({
        "operation": "rollback",
        "timestamp": datetime.now().isoformat(),
        **result
    }, indent=2))

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
