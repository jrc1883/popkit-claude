#!/usr/bin/env python3
"""
Deploy Configuration Validation Script.

Validates deploy.json against schema and checks for common errors.

Usage:
    python validate_config.py [--config PATH] [--strict]

Output:
    Validation report with errors and warnings
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ValidationError:
    """Represents a validation error or warning."""

    def __init__(self, level: str, field: str, message: str):
        self.level = level  # "error" or "warning"
        self.field = field
        self.message = message

    def __repr__(self):
        symbol = "❌" if self.level == "error" else "⚠️ "
        return f"{symbol} {self.field}: {self.message}"


def validate_required_fields(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate all required fields are present."""
    errors = []

    required_fields = [
        "version",
        "project_type",
        "language",
        "framework",
        "targets",
        "state",
        "initialized_at",
        "initialized_by",
        "github",
        "cicd",
        "gaps",
        "history"
    ]

    for field in required_fields:
        if field not in config:
            errors.append(ValidationError("error", field, "Required field missing"))

    return errors


def validate_version(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate version field."""
    errors = []

    if "version" in config:
        if config["version"] != "1.0":
            errors.append(ValidationError(
                "error",
                "version",
                f"Unsupported version: {config['version']} (expected: 1.0)"
            ))

    return errors


def validate_project_type(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate project_type field."""
    errors = []

    valid_types = ["web-app", "backend-api", "cli-tool", "library", "other"]

    if "project_type" in config:
        if config["project_type"] not in valid_types:
            errors.append(ValidationError(
                "warning",
                "project_type",
                f"Unknown project type: {config['project_type']}"
            ))

    return errors


def validate_targets(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate targets field."""
    errors = []

    valid_targets = ["docker", "vercel", "netlify", "npm", "pypi", "github-releases"]

    if "targets" not in config:
        return errors

    targets = config["targets"]

    if not isinstance(targets, list):
        errors.append(ValidationError("error", "targets", "Must be an array"))
        return errors

    if len(targets) == 0:
        errors.append(ValidationError("error", "targets", "Must have at least one target"))

    for target in targets:
        if target not in valid_targets:
            errors.append(ValidationError(
                "warning",
                "targets",
                f"Unknown target: {target}"
            ))

    return errors


def validate_github(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate github configuration."""
    errors = []

    if "github" not in config:
        return errors

    github = config["github"]

    required_github_fields = ["initialized", "repo", "default_branch", "has_actions"]
    for field in required_github_fields:
        if field not in github:
            errors.append(ValidationError(
                "error",
                f"github.{field}",
                "Required GitHub field missing"
            ))

    # Validate repo format
    if github.get("repo") is not None:
        repo = github["repo"]
        if not re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', repo):
            errors.append(ValidationError(
                "error",
                "github.repo",
                f"Invalid repo format: {repo} (expected: owner/repo)"
            ))

    return errors


def validate_cicd(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate CI/CD configuration."""
    errors = []

    if "cicd" not in config:
        return errors

    cicd = config["cicd"]

    required_cicd_fields = ["detected", "platform", "workflow_count"]
    for field in required_cicd_fields:
        if field not in cicd:
            errors.append(ValidationError(
                "error",
                f"cicd.{field}",
                "Required CI/CD field missing"
            ))

    # Validate platform
    if cicd.get("detected") and cicd.get("platform") is None:
        errors.append(ValidationError(
            "error",
            "cicd.platform",
            "Platform must be specified when detected=true"
        ))

    return errors


def validate_gaps(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate gaps configuration."""
    errors = []

    if "gaps" not in config:
        return errors

    gaps = config["gaps"]

    required_gap_fields = ["needs_github", "needs_cicd", "needs_target_configs"]
    for field in required_gap_fields:
        if field not in gaps:
            errors.append(ValidationError(
                "error",
                f"gaps.{field}",
                "Required gap field missing"
            ))

    return errors


def validate_history(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate history array."""
    errors = []

    if "history" not in config:
        return errors

    history = config["history"]

    if not isinstance(history, list):
        errors.append(ValidationError("error", "history", "Must be an array"))
        return errors

    if len(history) == 0:
        errors.append(ValidationError("error", "history", "Must have at least one entry"))
        return errors

    # Check for init entry
    has_init = any(entry.get("action") == "init" for entry in history)
    if not has_init:
        errors.append(ValidationError(
            "error",
            "history",
            "Must contain at least one 'init' action"
        ))

    # Validate each entry
    for i, entry in enumerate(history):
        required_entry_fields = ["action", "timestamp", "user", "version"]
        for field in required_entry_fields:
            if field not in entry:
                errors.append(ValidationError(
                    "error",
                    f"history[{i}].{field}",
                    "Required history entry field missing"
                ))

        # Validate timestamp format (ISO 8601)
        if "timestamp" in entry:
            try:
                datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                errors.append(ValidationError(
                    "error",
                    f"history[{i}].timestamp",
                    f"Invalid ISO 8601 timestamp: {entry.get('timestamp')}"
                ))

    return errors


def validate_timestamps(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate timestamp format."""
    errors = []

    if "initialized_at" in config:
        try:
            datetime.fromisoformat(config["initialized_at"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            errors.append(ValidationError(
                "error",
                "initialized_at",
                f"Invalid ISO 8601 timestamp: {config.get('initialized_at')}"
            ))

    return errors


def validate_config(config: Dict[str, Any], strict: bool = False) -> Tuple[List[ValidationError], bool]:
    """Run all validations on config."""
    errors = []

    # Run all validation functions
    errors.extend(validate_required_fields(config))
    errors.extend(validate_version(config))
    errors.extend(validate_project_type(config))
    errors.extend(validate_targets(config))
    errors.extend(validate_github(config))
    errors.extend(validate_cicd(config))
    errors.extend(validate_gaps(config))
    errors.extend(validate_history(config))
    errors.extend(validate_timestamps(config))

    # Determine if valid
    has_errors = any(e.level == "error" for e in errors)
    has_warnings = any(e.level == "warning" for e in errors)

    is_valid = not has_errors and (not strict or not has_warnings)

    return errors, is_valid


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate deploy.json configuration")
    parser.add_argument("--config", default=".claude/popkit/deploy.json", help="Path to config file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    config_path = Path(args.config)

    # Check if file exists
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}", file=sys.stderr)
        return 1

    # Load config
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Validate
    errors, is_valid = validate_config(config, strict=args.strict)

    # Output
    if args.json:
        result = {
            "valid": is_valid,
            "errors": [
                {"level": e.level, "field": e.field, "message": e.message}
                for e in errors
            ]
        }
        print(json.dumps(result, indent=2))
    else:
        print("Deploy Configuration Validation")
        print("=" * 50)
        print(f"File: {config_path}")
        print()

        if errors:
            error_count = sum(1 for e in errors if e.level == "error")
            warning_count = sum(1 for e in errors if e.level == "warning")

            print(f"Found {error_count} error(s) and {warning_count} warning(s):")
            print()

            for error in errors:
                print(f"  {error}")

            print()

        if is_valid:
            print("✅ Validation passed")
        else:
            print("❌ Validation failed")

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
