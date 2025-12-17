#!/usr/bin/env python3
"""
Deployment History Script.

Track and query deployment history across platforms.

Usage:
    python deployment_history.py [--platform PLATFORM] [--limit N] [--format FORMAT]

Output:
    JSON object with deployment history
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_git_tags() -> List[Dict[str, Any]]:
    """Get git tags as deployment markers."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "--sort=-v:refname", "--format=%(refname:short)|%(creatordate:iso)|%(subject)"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return []

        tags = []
        for line in result.stdout.strip().split('\n')[:20]:
            if line:
                parts = line.split('|', 2)
                tags.append({
                    "tag": parts[0],
                    "date": parts[1] if len(parts) > 1 else "",
                    "message": parts[2] if len(parts) > 2 else ""
                })
        return tags
    except:
        return []


def get_github_releases(limit: int = 10) -> List[Dict[str, Any]]:
    """Get GitHub releases."""
    try:
        result = subprocess.run(
            ["gh", "release", "list", "--limit", str(limit), "--json", "tagName,name,publishedAt,isDraft,isPrerelease"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            releases = json.loads(result.stdout)
            return [{
                "platform": "github-releases",
                "tag": r.get("tagName"),
                "name": r.get("name"),
                "date": r.get("publishedAt"),
                "draft": r.get("isDraft"),
                "prerelease": r.get("isPrerelease")
            } for r in releases]
    except:
        pass
    return []


def get_vercel_deployments(limit: int = 10) -> List[Dict[str, Any]]:
    """Get Vercel deployment history."""
    try:
        result = subprocess.run(
            ["vercel", "ls", "--json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            return [{
                "platform": "vercel",
                "url": d.get("url"),
                "state": d.get("state"),
                "target": d.get("target"),
                "date": d.get("created")
            } for d in deployments[:limit]]
    except:
        pass
    return []


def get_netlify_deployments(limit: int = 10) -> List[Dict[str, Any]]:
    """Get Netlify deployment history."""
    try:
        result = subprocess.run(
            ["netlify", "api", "listSiteDeploys", "--data", json.dumps({"per_page": limit})],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            return [{
                "platform": "netlify",
                "id": d.get("id"),
                "deploy_url": d.get("deploy_url"),
                "state": d.get("state"),
                "context": d.get("context"),
                "date": d.get("created_at")
            } for d in deployments[:limit]]
    except:
        pass
    return []


def get_npm_versions(package_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get npm package version history."""
    try:
        result = subprocess.run(
            ["npm", "view", package_name, "versions", "time", "--json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            versions = data.get("versions", []) if isinstance(data, dict) else data
            times = data.get("time", {}) if isinstance(data, dict) else {}

            history = []
            for v in versions[-limit:]:
                history.append({
                    "platform": "npm",
                    "version": v,
                    "date": times.get(v, "")
                })
            return list(reversed(history))
    except:
        pass
    return []


def get_docker_tags(image: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get Docker image tags (from local)."""
    try:
        result = subprocess.run(
            ["docker", "image", "ls", image, "--format", "{{.Tag}}|{{.CreatedAt}}|{{.Size}}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            tags = []
            for line in result.stdout.strip().split('\n')[:limit]:
                if line:
                    parts = line.split('|')
                    tags.append({
                        "platform": "docker",
                        "tag": parts[0],
                        "date": parts[1] if len(parts) > 1 else "",
                        "size": parts[2] if len(parts) > 2 else ""
                    })
            return tags
    except:
        pass
    return []


def get_local_history(history_file: Path = None) -> List[Dict[str, Any]]:
    """Get deployment history from local file."""
    if history_file is None:
        history_file = Path(".deployment-history.json")

    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except:
            pass
    return []


def record_deployment(
    platform: str,
    version: str,
    status: str,
    url: str = None,
    metadata: Dict[str, Any] = None,
    history_file: Path = None
) -> Dict[str, Any]:
    """Record a new deployment to history."""
    if history_file is None:
        history_file = Path(".deployment-history.json")

    # Load existing history
    history = get_local_history(history_file)

    # Create new entry
    entry = {
        "id": f"{platform}-{version}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "platform": platform,
        "version": version,
        "status": status,
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }

    # Add to history (newest first)
    history.insert(0, entry)

    # Keep last 100 entries
    history = history[:100]

    # Save
    history_file.write_text(json.dumps(history, indent=2))

    return entry


def main():
    import argparse
    parser = argparse.ArgumentParser(description="View deployment history")
    parser.add_argument("--platform", choices=["all", "github", "vercel", "netlify", "npm", "docker", "local"],
                        default="all", help="Platform to query")
    parser.add_argument("--limit", type=int, default=10, help="Number of entries to show")
    parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")
    parser.add_argument("--package", help="Package name (for npm)")
    parser.add_argument("--image", help="Docker image name")
    parser.add_argument("--record", action="store_true", help="Record a new deployment")
    parser.add_argument("--version", help="Version for recording")
    parser.add_argument("--status", help="Status for recording")
    parser.add_argument("--url", help="URL for recording")
    args = parser.parse_args()

    # Record new deployment
    if args.record:
        if not args.platform or not args.version or not args.status:
            print(json.dumps({
                "success": False,
                "error": "Recording requires --platform, --version, and --status"
            }, indent=2))
            return 1

        entry = record_deployment(
            platform=args.platform,
            version=args.version,
            status=args.status,
            url=args.url
        )
        print(json.dumps({
            "operation": "record_deployment",
            "success": True,
            "entry": entry
        }, indent=2))
        return 0

    # Collect history from requested platforms
    history = []

    if args.platform in ["all", "github"]:
        history.extend(get_github_releases(args.limit))

    if args.platform in ["all", "vercel"]:
        history.extend(get_vercel_deployments(args.limit))

    if args.platform in ["all", "netlify"]:
        history.extend(get_netlify_deployments(args.limit))

    if args.platform in ["all", "npm"] and args.package:
        history.extend(get_npm_versions(args.package, args.limit))

    if args.platform in ["all", "docker"] and args.image:
        history.extend(get_docker_tags(args.image, args.limit))

    if args.platform in ["all", "local"]:
        history.extend(get_local_history())

    # Sort by date if available
    def get_date(item):
        date_str = item.get("date") or item.get("timestamp") or ""
        return date_str

    history.sort(key=get_date, reverse=True)
    history = history[:args.limit]

    # Output
    if args.format == "table":
        print(f"{'Platform':<15} {'Version/Tag':<20} {'Date':<25} {'Status':<10}")
        print("-" * 70)
        for entry in history:
            platform = entry.get("platform", "")
            version = entry.get("version") or entry.get("tag") or entry.get("id", "")[:15]
            date = entry.get("date") or entry.get("timestamp", "")[:19]
            status = entry.get("status") or entry.get("state") or entry.get("target", "")
            print(f"{platform:<15} {version:<20} {date:<25} {status:<10}")
    else:
        print(json.dumps({
            "operation": "deployment_history",
            "platforms": args.platform,
            "count": len(history),
            "deployments": history
        }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
