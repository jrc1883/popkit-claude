#!/usr/bin/env python3
"""
Netlify Deployment Script.

Deploy sites to Netlify with preview and production support.

Usage:
    python netlify_deploy.py [--prod] [--dir DIR] [--site SITE]

Output:
    JSON object with deployment details
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def check_netlify_cli() -> bool:
    """Check if Netlify CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["netlify", "status"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_site_info(site_name: str = None) -> Optional[Dict[str, Any]]:
    """Get information about the linked Netlify site."""
    try:
        cmd = ["netlify", "api", "getSite"]
        if site_name:
            cmd.extend(["--data", json.dumps({"site_id": site_name})])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except:
        pass
    return None


def deploy(
    directory: str = None,
    production: bool = False,
    site: str = None,
    message: str = None,
    functions: str = None
) -> Dict[str, Any]:
    """Deploy to Netlify."""

    cmd = ["netlify", "deploy", "--json"]

    if production:
        cmd.append("--prod")

    if directory:
        cmd.extend(["--dir", directory])

    if site:
        cmd.extend(["--site", site])

    if message:
        cmd.extend(["--message", message])

    if functions:
        cmd.extend(["--functions", functions])

    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        try:
            deploy_info = json.loads(result.stdout)
            return {
                "success": True,
                "production": production,
                "url": deploy_info.get("deploy_url") or deploy_info.get("url"),
                "deploy_id": deploy_info.get("deploy_id"),
                "site_name": deploy_info.get("site_name"),
                "logs": deploy_info.get("logs"),
                "duration_seconds": round(duration, 2)
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "production": production,
                "output": result.stdout.strip(),
                "duration_seconds": round(duration, 2)
            }
    else:
        return {
            "success": False,
            "error": result.stderr.strip() or result.stdout.strip()
        }


def rollback(deploy_id: str = None) -> Dict[str, Any]:
    """Rollback to a previous deployment."""

    if deploy_id:
        # Restore specific deploy
        cmd = ["netlify", "api", "restoreSiteDeploy",
               "--data", json.dumps({"deploy_id": deploy_id})]
    else:
        # Rollback to previous
        cmd = ["netlify", "rollback"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return {
            "success": True,
            "action": "rollback",
            "deploy_id": deploy_id or "previous"
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip()
        }


def list_deploys(limit: int = 10) -> list:
    """List recent deployments."""
    try:
        result = subprocess.run(
            ["netlify", "api", "listSiteDeploys",
             "--data", json.dumps({"per_page": limit})],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            deploys = json.loads(result.stdout)
            return [{
                "id": d.get("id"),
                "state": d.get("state"),
                "created_at": d.get("created_at"),
                "deploy_url": d.get("deploy_url"),
                "branch": d.get("branch"),
                "context": d.get("context")
            } for d in deploys[:limit]]
    except:
        pass
    return []


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deploy to Netlify")
    parser.add_argument("--prod", action="store_true", help="Deploy to production")
    parser.add_argument("--dir", help="Directory to deploy")
    parser.add_argument("--site", help="Site name or ID")
    parser.add_argument("--message", "-m", help="Deploy message")
    parser.add_argument("--functions", help="Functions directory")
    parser.add_argument("--rollback", nargs="?", const="previous", help="Rollback to deploy ID")
    parser.add_argument("--list", action="store_true", help="List recent deploys")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    # Check CLI
    if not check_netlify_cli():
        print(json.dumps({
            "operation": "netlify_deploy",
            "success": False,
            "error": "Netlify CLI not installed or not authenticated. Run: npm i -g netlify-cli && netlify login"
        }, indent=2))
        return 1

    # List deploys
    if args.list:
        deploys = list_deploys()
        print(json.dumps({
            "operation": "list_deploys",
            "deploys": deploys
        }, indent=2))
        return 0

    # Rollback
    if args.rollback:
        deploy_id = args.rollback if args.rollback != "previous" else None
        result = rollback(deploy_id)
        print(json.dumps({
            "operation": "netlify_rollback",
            **result
        }, indent=2))
        return 0 if result["success"] else 1

    # Dry run
    if args.dry_run:
        print(json.dumps({
            "operation": "netlify_deploy",
            "dry_run": True,
            "production": args.prod,
            "directory": args.dir or "(auto-detect)",
            "site": args.site or "(linked site)",
            "message": args.message
        }, indent=2))
        return 0

    # Deploy
    result = deploy(
        directory=args.dir,
        production=args.prod,
        site=args.site,
        message=args.message,
        functions=args.functions
    )

    print(json.dumps({
        "operation": "netlify_deploy",
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
