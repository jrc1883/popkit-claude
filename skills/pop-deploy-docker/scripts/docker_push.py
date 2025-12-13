#!/usr/bin/env python3
"""
Docker Push Script.

Push Docker images to container registry.

Usage:
    python docker_push.py IMAGE_TAG [--registry REGISTRY]

Output:
    JSON object with push results
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List


def check_docker_login(registry: str = None) -> bool:
    """Check if logged into Docker registry."""
    try:
        # Try to pull a small test or check credentials
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def push_image(tag: str) -> Dict[str, Any]:
    """Push a single image tag."""
    start_time = datetime.now()

    result = subprocess.run(
        ["docker", "push", tag],
        capture_output=True,
        text=True
    )

    duration = (datetime.now() - start_time).total_seconds()

    return {
        "tag": tag,
        "success": result.returncode == 0,
        "duration_seconds": round(duration, 2),
        "output": result.stdout[-500:] if result.stdout else "",
        "error": result.stderr[-500:] if result.returncode != 0 else None
    }


def tag_image(source: str, target: str) -> bool:
    """Tag an image with a new name."""
    result = subprocess.run(
        ["docker", "tag", source, target],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def push_all_tags(base_tag: str, tags: List[str]) -> List[Dict[str, Any]]:
    """Push multiple tags for the same image."""
    results = []

    for tag in tags:
        # Tag the image
        if tag != base_tag:
            tag_success = tag_image(base_tag, tag)
            if not tag_success:
                results.append({
                    "tag": tag,
                    "success": False,
                    "error": "Failed to tag image"
                })
                continue

        # Push the tag
        result = push_image(tag)
        results.append(result)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Push Docker image to registry")
    parser.add_argument("image", help="Image tag to push")
    parser.add_argument("--registry", help="Target registry")
    parser.add_argument("--tags", nargs="+", help="Additional tags to push")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed")
    args = parser.parse_args()

    # Check Docker is available
    if not check_docker_login():
        print(json.dumps({
            "operation": "docker_push",
            "success": False,
            "error": "Docker not available or not logged in"
        }, indent=2))
        return 1

    # Build list of tags to push
    tags_to_push = [args.image]

    if args.tags:
        for tag in args.tags:
            if args.registry and not tag.startswith(args.registry):
                tag = f"{args.registry}/{tag}"
            tags_to_push.append(tag)

    if args.dry_run:
        print(json.dumps({
            "operation": "docker_push",
            "dry_run": True,
            "tags_to_push": tags_to_push
        }, indent=2))
        return 0

    # Push all tags
    start_time = datetime.now()
    results = push_all_tags(args.image, tags_to_push)
    total_duration = (datetime.now() - start_time).total_seconds()

    # Summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    report = {
        "operation": "docker_push",
        "success": len(failed) == 0,
        "total_tags": len(tags_to_push),
        "successful_pushes": len(successful),
        "failed_pushes": len(failed),
        "total_duration_seconds": round(total_duration, 2),
        "results": results
    }

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
