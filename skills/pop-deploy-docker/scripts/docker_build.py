#!/usr/bin/env python3
"""
Docker Build Script.

Build and tag Docker images with consistent naming.

Usage:
    python docker_build.py [--tag TAG] [--registry REGISTRY] [--push]

Output:
    JSON object with build results
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / "Dockerfile").exists():
            return current
        if (current / "docker-compose.yml").exists():
            return current
        if (current / "package.json").exists():
            return current
        current = current.parent

    return start_path


def get_version(project_dir: Path) -> str:
    """Get version from package.json or pyproject.toml."""
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            return pkg.get("version", "latest")
        except:
            pass

    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            import re
            content = pyproject.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        except:
            pass

    return "latest"


def get_git_sha() -> Optional[str]:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def build_image(
    project_dir: Path,
    image_name: str,
    tags: List[str],
    dockerfile: str = "Dockerfile",
    build_args: Dict[str, str] = None,
    platform: str = None
) -> Dict[str, Any]:
    """Build Docker image with specified tags."""

    # Build command
    cmd = ["docker", "build"]

    # Add tags
    for tag in tags:
        cmd.extend(["-t", tag])

    # Add build args
    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

    # Add platform if specified
    if platform:
        cmd.extend(["--platform", platform])

    # Add dockerfile and context
    cmd.extend(["-f", dockerfile, "."])

    # Execute build
    start_time = datetime.now()
    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    return {
        "success": result.returncode == 0,
        "command": " ".join(cmd),
        "tags": tags,
        "duration_seconds": round(duration, 2),
        "stdout": result.stdout[-1000:] if result.stdout else "",
        "stderr": result.stderr[-1000:] if result.stderr else ""
    }


def get_image_info(tag: str) -> Dict[str, Any]:
    """Get information about built image."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", tag, "--format",
             "{{.Id}} {{.Size}} {{.Created}}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            return {
                "id": parts[0][:12] if parts else "unknown",
                "size_bytes": int(parts[1]) if len(parts) > 1 else 0,
                "created": parts[2] if len(parts) > 2 else "unknown"
            }
    except:
        pass
    return {}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Docker image")
    parser.add_argument("--name", help="Image name")
    parser.add_argument("--tag", help="Version tag")
    parser.add_argument("--registry", help="Container registry (e.g., ghcr.io/user)")
    parser.add_argument("--dockerfile", default="Dockerfile", help="Dockerfile path")
    parser.add_argument("--platform", help="Target platform (e.g., linux/amd64)")
    parser.add_argument("--push", action="store_true", help="Push after build")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = find_project_root()

    # Determine image name
    image_name = args.name
    if not image_name:
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            image_name = pkg.get("name", project_dir.name)
        else:
            image_name = project_dir.name

    # Clean up name
    image_name = image_name.replace("@", "").replace("/", "-")

    # Determine version
    version = args.tag or get_version(project_dir)
    git_sha = get_git_sha()

    # Build tag list
    tags = []
    base = f"{args.registry}/{image_name}" if args.registry else image_name

    tags.append(f"{base}:{version}")
    tags.append(f"{base}:latest")
    if git_sha:
        tags.append(f"{base}:{git_sha}")

    # Build image
    build_result = build_image(
        project_dir,
        image_name,
        tags,
        args.dockerfile,
        platform=args.platform
    )

    if build_result["success"]:
        # Get image info
        image_info = get_image_info(tags[0])

        # Push if requested
        push_results = []
        if args.push:
            for tag in tags:
                push_result = subprocess.run(
                    ["docker", "push", tag],
                    capture_output=True,
                    text=True
                )
                push_results.append({
                    "tag": tag,
                    "success": push_result.returncode == 0
                })

        report = {
            "operation": "docker_build",
            "success": True,
            "image_name": image_name,
            "version": version,
            "tags": tags,
            "image_info": image_info,
            "build_duration": build_result["duration_seconds"],
            "pushed": push_results if args.push else None
        }
    else:
        report = {
            "operation": "docker_build",
            "success": False,
            "error": build_result["stderr"][:500],
            "command": build_result["command"]
        }

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
