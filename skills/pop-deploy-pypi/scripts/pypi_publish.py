#!/usr/bin/env python3
"""
PyPI Publish Script.

Publish packages to PyPI with pre-publish validation.

Usage:
    python pypi_publish.py [--test] [--repository URL] [--dry-run]

Output:
    JSON object with publish results
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re


def check_twine() -> bool:
    """Check if twine is installed."""
    try:
        result = subprocess.run(
            ["twine", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_pyproject_info(project_dir: Path = None) -> Optional[Dict[str, Any]]:
    """Get pyproject.toml information."""
    if project_dir is None:
        project_dir = Path.cwd()

    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return None

    try:
        content = pyproject.read_text()
        info = {}

        # Extract name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if name_match:
            info["name"] = name_match.group(1)

        # Extract version
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            info["version"] = version_match.group(1)

        # Extract description
        desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
        if desc_match:
            info["description"] = desc_match.group(1)

        return info
    except:
        return None


def get_setup_py_info(project_dir: Path = None) -> Optional[Dict[str, Any]]:
    """Get setup.py information (fallback)."""
    if project_dir is None:
        project_dir = Path.cwd()

    setup_py = project_dir / "setup.py"
    if not setup_py.exists():
        return None

    try:
        content = setup_py.read_text()
        info = {}

        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if name_match:
            info["name"] = name_match.group(1)

        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            info["version"] = version_match.group(1)

        return info
    except:
        return None


def get_pypi_version(package_name: str, test: bool = False) -> Optional[str]:
    """Get latest version from PyPI."""
    try:
        import urllib.request
        import urllib.error

        url = f"https://{'test.' if test else ''}pypi.org/pypi/{package_name}/json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("info", {}).get("version")
    except:
        return None


def build_package(project_dir: Path = None) -> Dict[str, Any]:
    """Build package distributions."""
    if project_dir is None:
        project_dir = Path.cwd()

    # Clean old builds
    dist_dir = project_dir / "dist"
    if dist_dir.exists():
        for f in dist_dir.glob("*"):
            f.unlink()

    start_time = datetime.now()
    result = subprocess.run(
        ["python", "-m", "build"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    if result.returncode == 0:
        # List built files
        built_files = list(dist_dir.glob("*")) if dist_dir.exists() else []
        return {
            "success": True,
            "files": [f.name for f in built_files],
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "error": result.stderr.strip()
        }


def validate_package(project_dir: Path = None, test: bool = False) -> Dict[str, Any]:
    """Validate package before publishing."""
    if project_dir is None:
        project_dir = Path.cwd()

    issues = []
    warnings = []

    # Get package info
    pkg = get_pyproject_info(project_dir) or get_setup_py_info(project_dir)
    if not pkg:
        issues.append("No pyproject.toml or setup.py found")
        return {"valid": False, "issues": issues, "warnings": warnings}

    # Required fields
    if not pkg.get("name"):
        issues.append("Package name not found")
    if not pkg.get("version"):
        issues.append("Package version not found")

    # Check for README
    readme = project_dir / "README.md"
    readme_rst = project_dir / "README.rst"
    if not readme.exists() and not readme_rst.exists():
        warnings.append("README.md or README.rst not found")

    # Check for LICENSE
    license_file = project_dir / "LICENSE"
    if not license_file.exists():
        warnings.append("LICENSE file not found")

    # Check version not published
    if pkg.get("name"):
        pypi_version = get_pypi_version(pkg["name"], test)
        if pypi_version == pkg.get("version"):
            issues.append(f"Version {pkg['version']} already published on {'TestPyPI' if test else 'PyPI'}")

    # Check dist files
    dist_dir = project_dir / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        warnings.append("No dist files found - run python -m build first")

    # Check twine
    result = subprocess.run(
        ["twine", "check", "dist/*"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        shell=True
    )
    if result.returncode != 0 and dist_dir.exists():
        issues.append(f"twine check failed: {result.stdout.strip()}")

    return {
        "valid": len(issues) == 0,
        "package_name": pkg.get("name"),
        "version": pkg.get("version"),
        "pypi_version": get_pypi_version(pkg.get("name", ""), test),
        "issues": issues,
        "warnings": warnings
    }


def publish(
    project_dir: Path = None,
    test: bool = False,
    repository_url: str = None,
    skip_existing: bool = False
) -> Dict[str, Any]:
    """Publish package to PyPI."""
    if project_dir is None:
        project_dir = Path.cwd()

    dist_dir = project_dir / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        return {
            "success": False,
            "error": "No dist files found. Run: python -m build"
        }

    cmd = ["twine", "upload"]

    if test:
        cmd.extend(["--repository", "testpypi"])
    elif repository_url:
        cmd.extend(["--repository-url", repository_url])

    if skip_existing:
        cmd.append("--skip-existing")

    cmd.append("dist/*")

    start_time = datetime.now()
    result = subprocess.run(
        " ".join(cmd),
        cwd=project_dir,
        capture_output=True,
        text=True,
        shell=True
    )
    duration = (datetime.now() - start_time).total_seconds()

    pkg = get_pyproject_info(project_dir) or get_setup_py_info(project_dir) or {}

    if result.returncode == 0:
        return {
            "success": True,
            "package": pkg.get("name", "unknown"),
            "version": pkg.get("version", "unknown"),
            "repository": "testpypi" if test else "pypi",
            "duration_seconds": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "package": pkg.get("name", "unknown"),
            "error": result.stderr.strip() or result.stdout.strip()
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Publish to PyPI")
    parser.add_argument("--test", action="store_true", help="Publish to TestPyPI")
    parser.add_argument("--repository-url", help="Custom repository URL")
    parser.add_argument("--skip-existing", action="store_true", help="Skip if version exists")
    parser.add_argument("--build", action="store_true", help="Build before publishing")
    parser.add_argument("--validate-only", action="store_true", help="Only validate")
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()

    # Check twine
    if not check_twine():
        print(json.dumps({
            "operation": "pypi_publish",
            "success": False,
            "error": "twine not installed. Run: pip install twine build"
        }, indent=2))
        return 1

    # Validate
    validation = validate_package(project_dir, args.test)

    if args.validate_only:
        print(json.dumps({
            "operation": "pypi_validate",
            **validation
        }, indent=2))
        return 0 if validation["valid"] else 1

    # Show warnings
    if validation["warnings"]:
        for warning in validation["warnings"]:
            print(f"Warning: {warning}", file=sys.stderr)

    # Build if requested
    if args.build:
        build_result = build_package(project_dir)
        if not build_result["success"]:
            print(json.dumps({
                "operation": "pypi_build",
                **build_result
            }, indent=2))
            return 1

    # Stop on issues
    if not validation["valid"]:
        print(json.dumps({
            "operation": "pypi_publish",
            "success": False,
            "validation_failed": True,
            **validation
        }, indent=2))
        return 1

    # Publish
    result = publish(
        project_dir=project_dir,
        test=args.test,
        repository_url=args.repository_url,
        skip_existing=args.skip_existing
    )

    print(json.dumps({
        "operation": "pypi_publish",
        **result
    }, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
