#!/usr/bin/env python3
"""
NPM Publish Script.

Publish packages to npm with pre-publish validation.

Usage:
    python npm_publish.py [--tag TAG] [--access ACCESS] [--dry-run]

Output:
    JSON object with publish results
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def check_npm_auth() -> bool:
    """Check if authenticated with npm."""
    try:
        result = subprocess.run(
            ["npm", "whoami"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def get_npm_user() -> Optional[str]:
    """Get current npm user."""
    try:
        result = subprocess.run(
            ["npm", "whoami"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def get_package_info(project_dir: Path = None) -> Optional[Dict[str, Any]]:
    """Get package.json information."""
    if project_dir is None:
        project_dir = Path.cwd()

    pkg_json = project_dir / "package.json"
    if not pkg_json.exists():
        return None

    try:
        return json.loads(pkg_json.read_text())
    except:
        return None


def get_registry_version(package_name: str) -> Optional[str]:
    """Get latest version from npm registry."""
    try:
        result = subprocess.run(
            ["npm", "view", package_name, "version"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def validate_package(project_dir: Path = None) -> Dict[str, Any]:
    """Validate package before publishing."""
    if project_dir is None:
        project_dir = Path.cwd()

    issues = []
    warnings = []

    pkg = get_package_info(project_dir)
    if not pkg:
        issues.append("package.json not found")
        return {"valid": False, "issues": issues, "warnings": warnings}

    # Required fields
    required_fields = ["name", "version", "description", "main"]
    for field in required_fields:
        if not pkg.get(field):
            issues.append(f"Missing required field: {field}")

    # Check for private
    if pkg.get("private"):
        issues.append("Package is marked as private")

    # Check for readme
    readme = project_dir / "README.md"
    if not readme.exists():
        warnings.append("README.md not found")

    # Check for license
    if not pkg.get("license"):
        warnings.append("No license specified")

    license_file = project_dir / "LICENSE"
    if not license_file.exists():
        warnings.append("LICENSE file not found")

    # Check for repository
    if not pkg.get("repository"):
        warnings.append("No repository field in package.json")

    # Check version not published
    registry_version = get_registry_version(pkg.get("name", ""))
    local_version = pkg.get("version")
    if registry_version == local_version:
        issues.append(f"Version {local_version} already published")

    # Check for .npmignore or files field
    npmignore = project_dir / ".npmignore"
    if not npmignore.exists() and not pkg.get("files"):
        warnings.append("No .npmignore or files field - may publish unnecessary files")

    return {
        "valid": len(issues) == 0,
        "package_name": pkg.get("name"),
        "version": pkg.get("version"),
        "registry_version": registry_version,
        "issues": issues,
        "warnings": warnings
    }


def publish(
    project_dir: Path = None,
    tag: str = None,
    access: str = None,
    dry_run: bool = False,
    otp: str = None
) -> Dict[str, Any]:
    """Publish package to npm."""
    if project_dir is None:
        project_dir = Path.cwd()

    cmd = ["npm", "publish"]

    if tag:
        cmd.extend(["--tag", tag])

    if access:
        cmd.extend(["--access", access])

    if dry_run:
        cmd.append("--dry-run")

    if otp:
        cmd.extend(["--otp", otp])

    start_time = datetime.now()
    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    pkg = get_package_info(project_dir)

    if result.returncode == 0:
        return {
            "success": True,
            "package": pkg.get("name") if pkg else "unknown",
            "version": pkg.get("version") if pkg else "unknown",
            "tag": tag or "latest",
            "dry_run": dry_run,
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "package": pkg.get("name") if pkg else "unknown",
            "error": result.stderr.strip()
        }


def deprecate(package_name: str, version: str, message: str) -> Dict[str, Any]:
    """Deprecate a package version."""
    result = subprocess.run(
        ["npm", "deprecate", f"{package_name}@{version}", message],
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0,
        "action": "deprecate",
        "package": package_name,
        "version": version,
        "message": message,
        "error": result.stderr.strip() if result.returncode != 0 else None
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Publish to npm")
    parser.add_argument("--tag", help="Publish tag (e.g., beta, next)")
    parser.add_argument("--access", choices=["public", "restricted"], help="Package access level")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run")
    parser.add_argument("--otp", help="One-time password for 2FA")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't publish")
    parser.add_argument("--deprecate", nargs=2, metavar=("VERSION", "MESSAGE"), help="Deprecate a version")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()

    # Check auth
    if not check_npm_auth():
        print(json.dumps({
            "operation": "npm_publish",
            "success": False,
            "error": "Not authenticated with npm. Run: npm login"
        }, indent=2))
        return 1

    # Deprecate
    if args.deprecate:
        pkg = get_package_info(project_dir)
        if not pkg:
            print(json.dumps({
                "operation": "npm_deprecate",
                "success": False,
                "error": "package.json not found"
            }, indent=2))
            return 1

        result = deprecate(pkg["name"], args.deprecate[0], args.deprecate[1])
        print(json.dumps({
            "operation": "npm_deprecate",
            **result
        }, indent=2))
        return 0 if result["success"] else 1

    # Validate
    validation = validate_package(project_dir)

    if args.validate_only:
        print(json.dumps({
            "operation": "npm_validate",
            **validation
        }, indent=2))
        return 0 if validation["valid"] else 1

    # Show warnings but continue
    if validation["warnings"]:
        for warning in validation["warnings"]:
            print(f"Warning: {warning}", file=sys.stderr)

    # Stop on issues
    if not validation["valid"]:
        print(json.dumps({
            "operation": "npm_publish",
            "success": False,
            "validation_failed": True,
            **validation
        }, indent=2))
        return 1

    # Publish
    result = publish(
        project_dir=project_dir,
        tag=args.tag,
        access=args.access,
        dry_run=args.dry_run,
        otp=args.otp
    )

    print(json.dumps({
        "operation": "npm_publish",
        "user": get_npm_user(),
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
