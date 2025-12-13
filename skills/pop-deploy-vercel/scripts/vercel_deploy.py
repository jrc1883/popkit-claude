#!/usr/bin/env python3
"""
Vercel Deployment Script.

Deploy projects to Vercel with preview and production support.

Usage:
    python vercel_deploy.py [--prod] [--project PROJECT] [--prebuilt]

Output:
    JSON object with deployment details
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def check_vercel_cli() -> bool:
    """Check if Vercel CLI is installed."""
    try:
        result = subprocess.run(
            ["vercel", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_project_info() -> Optional[Dict[str, Any]]:
    """Get linked Vercel project information."""
    vercel_json = Path(".vercel/project.json")
    if vercel_json.exists():
        try:
            return json.loads(vercel_json.read_text())
        except:
            pass
    return None


def deploy(
    production: bool = False,
    project: str = None,
    prebuilt: bool = False,
    env: Dict[str, str] = None,
    build_env: Dict[str, str] = None,
    confirm: bool = True
) -> Dict[str, Any]:
    """Deploy to Vercel."""

    cmd = ["vercel"]

    if production:
        cmd.append("--prod")

    if project:
        cmd.extend(["--name", project])

    if prebuilt:
        cmd.append("--prebuilt")

    if confirm:
        cmd.append("--yes")

    # Add environment variables
    if env:
        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])

    if build_env:
        for key, value in build_env.items():
            cmd.extend(["-b", f"{key}={value}"])

    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        # Extract URL from output
        url = result.stdout.strip().split('\n')[-1]
        return {
            "success": True,
            "production": production,
            "url": url,
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip() or result.stdout.strip()
        }


def promote(url: str) -> Dict[str, Any]:
    """Promote a preview deployment to production."""
    result = subprocess.run(
        ["vercel", "promote", url, "--yes"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return {
            "success": True,
            "action": "promote",
            "url": url
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip()
        }


def rollback(project: str = None, deployment_id: str = None) -> Dict[str, Any]:
    """Rollback to previous production deployment."""
    cmd = ["vercel", "rollback"]

    if project:
        cmd.extend(["--scope", project])

    if deployment_id:
        cmd.append(deployment_id)

    cmd.append("--yes")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return {
            "success": True,
            "action": "rollback",
            "deployment_id": deployment_id or "previous"
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip()
        }


def list_deployments(project: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """List recent deployments."""
    cmd = ["vercel", "ls", "--json"]

    if project:
        cmd.extend(["--scope", project])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            return [{
                "url": d.get("url"),
                "state": d.get("state"),
                "created": d.get("created"),
                "target": d.get("target")
            } for d in deployments[:limit]]
    except:
        pass
    return []


def get_deployment_info(url: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific deployment."""
    try:
        result = subprocess.run(
            ["vercel", "inspect", url, "--json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except:
        pass
    return None


def set_env(key: str, value: str, target: str = "production") -> Dict[str, Any]:
    """Set environment variable."""
    result = subprocess.run(
        ["vercel", "env", "add", key, target],
        input=value,
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0,
        "action": "set_env",
        "key": key,
        "target": target,
        "error": result.stderr.strip() if result.returncode != 0 else None
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deploy to Vercel")
    parser.add_argument("--prod", action="store_true", help="Deploy to production")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--prebuilt", action="store_true", help="Use prebuilt output")
    parser.add_argument("--promote", help="Promote deployment URL to production")
    parser.add_argument("--rollback", nargs="?", const="previous", help="Rollback deployment")
    parser.add_argument("--list", action="store_true", help="List recent deployments")
    parser.add_argument("--inspect", help="Inspect deployment URL")
    parser.add_argument("--env", nargs=2, action="append", metavar=("KEY", "VALUE"), help="Set env var")
    parser.add_argument("--build-env", nargs=2, action="append", metavar=("KEY", "VALUE"), help="Set build env")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    # Check CLI
    if not check_vercel_cli():
        print(json.dumps({
            "operation": "vercel_deploy",
            "success": False,
            "error": "Vercel CLI not installed. Run: npm i -g vercel"
        }, indent=2))
        return 1

    # List deployments
    if args.list:
        deployments = list_deployments(args.project)
        print(json.dumps({
            "operation": "list_deployments",
            "deployments": deployments
        }, indent=2))
        return 0

    # Inspect deployment
    if args.inspect:
        info = get_deployment_info(args.inspect)
        print(json.dumps({
            "operation": "inspect",
            "deployment": info
        }, indent=2))
        return 0

    # Promote
    if args.promote:
        result = promote(args.promote)
        print(json.dumps({
            "operation": "vercel_promote",
            **result
        }, indent=2))
        return 0 if result["success"] else 1

    # Rollback
    if args.rollback:
        deployment_id = args.rollback if args.rollback != "previous" else None
        result = rollback(args.project, deployment_id)
        print(json.dumps({
            "operation": "vercel_rollback",
            **result
        }, indent=2))
        return 0 if result["success"] else 1

    # Dry run
    if args.dry_run:
        print(json.dumps({
            "operation": "vercel_deploy",
            "dry_run": True,
            "production": args.prod,
            "project": args.project or "(linked project)",
            "prebuilt": args.prebuilt,
            "env_vars": dict(args.env) if args.env else None,
            "build_env": dict(args.build_env) if args.build_env else None
        }, indent=2))
        return 0

    # Deploy
    env_vars = dict(args.env) if args.env else None
    build_env = dict(args.build_env) if args.build_env else None

    result = deploy(
        production=args.prod,
        project=args.project,
        prebuilt=args.prebuilt,
        env=env_vars,
        build_env=build_env
    )

    print(json.dumps({
        "operation": "vercel_deploy",
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
