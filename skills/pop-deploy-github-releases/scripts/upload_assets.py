#!/usr/bin/env python3
"""
GitHub Release Asset Upload Script.

Upload assets to existing GitHub releases.

Usage:
    python upload_assets.py TAG ASSET [ASSET...]

Output:
    JSON object with upload results
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get information about a file."""
    if not file_path.exists():
        return {"exists": False}

    stat = file_path.stat()
    return {
        "exists": True,
        "name": file_path.name,
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size)
    }


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def upload_asset(tag: str, asset_path: str) -> Dict[str, Any]:
    """Upload a single asset to a release."""
    path = Path(asset_path)

    if not path.exists():
        return {
            "asset": asset_path,
            "success": False,
            "error": "File not found"
        }

    file_info = get_file_info(path)

    start_time = datetime.now()
    result = subprocess.run(
        ["gh", "release", "upload", tag, str(path), "--clobber"],
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        return {
            "asset": path.name,
            "success": True,
            "size": file_info["size_human"],
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "asset": path.name,
            "success": False,
            "error": result.stderr.strip()
        }


def upload_assets(tag: str, assets: List[str]) -> List[Dict[str, Any]]:
    """Upload multiple assets to a release."""
    results = []
    for asset in assets:
        result = upload_asset(tag, asset)
        results.append(result)
    return results


def list_release_assets(tag: str) -> List[Dict[str, Any]]:
    """List existing assets on a release."""
    try:
        result = subprocess.run(
            ["gh", "release", "view", tag, "--json", "assets"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("assets", [])
    except:
        pass
    return []


def delete_asset(tag: str, asset_name: str) -> bool:
    """Delete an asset from a release."""
    result = subprocess.run(
        ["gh", "release", "delete-asset", tag, asset_name, "--yes"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Upload assets to GitHub release")
    parser.add_argument("tag", help="Release tag")
    parser.add_argument("assets", nargs="*", help="Asset files to upload")
    parser.add_argument("--list", action="store_true", help="List existing assets")
    parser.add_argument("--delete", help="Delete asset by name")
    parser.add_argument("--pattern", help="Glob pattern for assets (e.g., dist/*.zip)")
    args = parser.parse_args()

    # List assets
    if args.list:
        assets = list_release_assets(args.tag)
        print(json.dumps({
            "operation": "list_assets",
            "tag": args.tag,
            "assets": assets
        }, indent=2))
        return 0

    # Delete asset
    if args.delete:
        success = delete_asset(args.tag, args.delete)
        print(json.dumps({
            "operation": "delete_asset",
            "tag": args.tag,
            "asset": args.delete,
            "success": success
        }, indent=2))
        return 0 if success else 1

    # Collect assets
    asset_files = list(args.assets) if args.assets else []

    # Add glob pattern matches
    if args.pattern:
        import glob
        matches = glob.glob(args.pattern)
        asset_files.extend(matches)

    if not asset_files:
        print(json.dumps({
            "operation": "upload_assets",
            "success": False,
            "error": "No assets specified"
        }, indent=2))
        return 1

    # Upload assets
    start_time = datetime.now()
    results = upload_assets(args.tag, asset_files)
    total_duration = (datetime.now() - start_time).total_seconds()

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    report = {
        "operation": "upload_assets",
        "tag": args.tag,
        "success": len(failed) == 0,
        "total_assets": len(asset_files),
        "successful_uploads": len(successful),
        "failed_uploads": len(failed),
        "total_duration_seconds": round(total_duration, 2),
        "results": results
    }

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
