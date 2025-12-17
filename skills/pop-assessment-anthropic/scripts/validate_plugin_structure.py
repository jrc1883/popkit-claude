#!/usr/bin/env python3
"""
Validate Plugin Structure

Checks plugin.json, hooks.json, .mcp.json, and config.json for required fields
and valid configurations.

Usage:
    python validate_plugin_structure.py [plugin_dir]

Output:
    JSON object with findings and score
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def find_plugin_root(start_path: Path = None) -> Path:
    """Find the plugin root directory."""
    if start_path is None:
        start_path = Path.cwd()

    # Look for .claude-plugin directory
    current = start_path
    for _ in range(5):  # Max 5 levels up
        if (current / ".claude-plugin" / "plugin.json").exists():
            return current
        if (current / "packages" / "plugin" / ".claude-plugin" / "plugin.json").exists():
            return current / "packages" / "plugin"
        current = current.parent

    return start_path


def load_json_file(filepath: Path) -> tuple[Any, str]:
    """Load a JSON file, return (data, error)."""
    if not filepath.exists():
        return None, f"File not found: {filepath}"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    except Exception as e:
        return None, str(e)


def check_plugin_json(plugin_dir: Path) -> List[Dict]:
    """Validate plugin.json."""
    findings = []
    filepath = plugin_dir / ".claude-plugin" / "plugin.json"

    # Check file exists
    if not filepath.exists():
        findings.append({
            "id": "PS-001",
            "check": "plugin.json exists",
            "status": "FAIL",
            "severity": "critical",
            "message": f"File not found: {filepath}",
            "deduction": 20
        })
        return findings

    findings.append({
        "id": "PS-001",
        "check": "plugin.json exists",
        "status": "PASS",
        "severity": "critical",
        "message": "File exists",
        "deduction": 0
    })

    # Load and validate
    data, error = load_json_file(filepath)
    if error:
        findings.append({
            "id": "PS-001b",
            "check": "plugin.json valid JSON",
            "status": "FAIL",
            "severity": "critical",
            "message": error,
            "deduction": 20
        })
        return findings

    # Check required fields
    required_fields = [
        ("name", "PS-002", "critical", 20),
        ("version", "PS-003", "critical", 20),
        ("description", "PS-004", "high", 10),
        ("author", "PS-005", "high", 10),
    ]

    for field, check_id, severity, deduction in required_fields:
        if field in data and data[field]:
            findings.append({
                "id": check_id,
                "check": f"plugin.json has {field}",
                "status": "PASS",
                "severity": severity,
                "message": f"{field}: {data[field]}",
                "deduction": 0
            })
        else:
            findings.append({
                "id": check_id,
                "check": f"plugin.json has {field}",
                "status": "FAIL",
                "severity": severity,
                "message": f"Missing {field} field",
                "deduction": deduction
            })

    return findings


def check_hooks_json(plugin_dir: Path) -> List[Dict]:
    """Validate hooks.json."""
    findings = []
    filepath = plugin_dir / "hooks" / "hooks.json"

    if not filepath.exists():
        findings.append({
            "id": "PS-006",
            "check": "hooks.json exists",
            "status": "SKIP",
            "severity": "info",
            "message": "No hooks.json (hooks may not be used)",
            "deduction": 0
        })
        return findings

    data, error = load_json_file(filepath)
    if error:
        findings.append({
            "id": "PS-006",
            "check": "hooks.json valid JSON",
            "status": "FAIL",
            "severity": "critical",
            "message": error,
            "deduction": 20
        })
        return findings

    # Check for schema
    if "$schema" in data:
        findings.append({
            "id": "PS-008",
            "check": "hooks.json has $schema",
            "status": "PASS",
            "severity": "low",
            "message": "Schema reference included",
            "deduction": 0
        })
    else:
        findings.append({
            "id": "PS-008",
            "check": "hooks.json has $schema",
            "status": "WARN",
            "severity": "low",
            "message": "No $schema reference",
            "deduction": 2
        })

    # Check valid event types
    valid_events = {"PreToolUse", "PostToolUse", "SessionStart", "Stop",
                    "SubagentStop", "Notification", "UserPromptSubmit"}

    hooks = data.get("hooks", [])
    invalid_events = []
    for hook in hooks:
        event = hook.get("event", "")
        if event not in valid_events:
            invalid_events.append(event)

    if invalid_events:
        findings.append({
            "id": "PS-006",
            "check": "hooks.json valid events",
            "status": "FAIL",
            "severity": "critical",
            "message": f"Invalid events: {invalid_events}",
            "deduction": 20
        })
    else:
        findings.append({
            "id": "PS-006",
            "check": "hooks.json valid events",
            "status": "PASS",
            "severity": "critical",
            "message": f"All {len(hooks)} hooks have valid events",
            "deduction": 0
        })

    # Check referenced scripts exist
    missing_scripts = []
    hooks_dir = plugin_dir / "hooks"
    for hook in hooks:
        command = hook.get("command", "")
        if command:
            script_path = hooks_dir / command
            if not script_path.exists():
                missing_scripts.append(command)

    if missing_scripts:
        findings.append({
            "id": "PS-007",
            "check": "Referenced scripts exist",
            "status": "FAIL",
            "severity": "critical",
            "message": f"Missing: {missing_scripts}",
            "deduction": 20
        })
    else:
        findings.append({
            "id": "PS-007",
            "check": "Referenced scripts exist",
            "status": "PASS",
            "severity": "critical",
            "message": f"All {len(hooks)} scripts found",
            "deduction": 0
        })

    return findings


def check_mcp_json(plugin_dir: Path) -> List[Dict]:
    """Validate .mcp.json."""
    findings = []
    filepath = plugin_dir / ".mcp.json"

    if not filepath.exists():
        findings.append({
            "id": "PS-009",
            "check": ".mcp.json exists",
            "status": "SKIP",
            "severity": "info",
            "message": "No .mcp.json (MCP may not be used)",
            "deduction": 0
        })
        return findings

    data, error = load_json_file(filepath)
    if error:
        findings.append({
            "id": "PS-009",
            "check": ".mcp.json valid JSON",
            "status": "FAIL",
            "severity": "high",
            "message": error,
            "deduction": 10
        })
        return findings

    # Check for schema
    if "$schema" in data:
        findings.append({
            "id": "PS-009",
            "check": ".mcp.json has $schema",
            "status": "PASS",
            "severity": "low",
            "message": "Schema reference included",
            "deduction": 0
        })
    else:
        findings.append({
            "id": "PS-009",
            "check": ".mcp.json has $schema",
            "status": "WARN",
            "severity": "low",
            "message": "No $schema reference",
            "deduction": 2
        })

    return findings


def check_config_json(plugin_dir: Path) -> List[Dict]:
    """Validate agents/config.json."""
    findings = []
    filepath = plugin_dir / "agents" / "config.json"

    if not filepath.exists():
        findings.append({
            "id": "PS-010",
            "check": "config.json exists",
            "status": "SKIP",
            "severity": "info",
            "message": "No agents/config.json",
            "deduction": 0
        })
        return findings

    data, error = load_json_file(filepath)
    if error:
        findings.append({
            "id": "PS-010",
            "check": "config.json valid JSON",
            "status": "FAIL",
            "severity": "high",
            "message": error,
            "deduction": 10
        })
        return findings

    findings.append({
        "id": "PS-010",
        "check": "config.json valid JSON",
        "status": "PASS",
        "severity": "high",
        "message": "Valid configuration",
        "deduction": 0
    })

    return findings


def main():
    # Get plugin directory
    if len(sys.argv) > 1:
        plugin_dir = Path(sys.argv[1])
    else:
        plugin_dir = find_plugin_root()

    # Run all checks
    all_findings = []
    all_findings.extend(check_plugin_json(plugin_dir))
    all_findings.extend(check_hooks_json(plugin_dir))
    all_findings.extend(check_mcp_json(plugin_dir))
    all_findings.extend(check_config_json(plugin_dir))

    # Calculate score
    total_deduction = sum(f.get("deduction", 0) for f in all_findings)
    score = max(0, 100 - total_deduction)

    # Summary
    passes = len([f for f in all_findings if f["status"] == "PASS"])
    fails = len([f for f in all_findings if f["status"] == "FAIL"])
    warns = len([f for f in all_findings if f["status"] == "WARN"])

    result = {
        "category": "plugin-structure",
        "plugin_dir": str(plugin_dir),
        "score": score,
        "max_score": 100,
        "summary": {
            "passes": passes,
            "fails": fails,
            "warnings": warns,
            "total_deduction": total_deduction
        },
        "findings": all_findings
    }

    print(json.dumps(result, indent=2))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
