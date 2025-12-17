#!/usr/bin/env python3
"""
Validate Hook Protocol Compliance

Checks all Python hooks for JSON stdin/stdout protocol compliance.

Usage:
    python validate_hooks.py [plugin_dir]

Output:
    JSON object with findings and score
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


def find_plugin_root(start_path: Path = None) -> Path:
    """Find the plugin root directory."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path
    for _ in range(5):
        if (current / ".claude-plugin" / "plugin.json").exists():
            return current
        if (current / "packages" / "plugin" / ".claude-plugin" / "plugin.json").exists():
            return current / "packages" / "plugin"
        current = current.parent

    return start_path


def check_hook_file(filepath: Path) -> Dict:
    """Check a single hook file for protocol compliance."""
    findings = {
        "file": str(filepath.name),
        "path": str(filepath),
        "checks": [],
        "status": "PASS",
        "deduction": 0
    }

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
    except Exception as e:
        findings["status"] = "ERROR"
        findings["checks"].append({
            "id": "HP-000",
            "check": "File readable",
            "status": "FAIL",
            "message": str(e),
            "severity": "critical",
            "deduction": 20
        })
        findings["deduction"] = 20
        return findings

    # HP-001: Check shebang
    if lines and lines[0].strip() == "#!/usr/bin/env python3":
        findings["checks"].append({
            "id": "HP-001",
            "check": "Has shebang",
            "status": "PASS",
            "message": "#!/usr/bin/env python3",
            "severity": "critical",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-001",
            "check": "Has shebang",
            "status": "FAIL",
            "message": f"First line: {lines[0][:50] if lines else 'empty'}",
            "severity": "critical",
            "deduction": 20
        })
        findings["deduction"] += 20
        findings["status"] = "FAIL"

    # HP-002: Check JSON stdin reading
    stdin_patterns = [
        r"json\.load\s*\(\s*sys\.stdin\s*\)",
        r"json\.loads\s*\(\s*sys\.stdin\.read\s*\(\s*\)\s*\)"
    ]
    has_stdin = any(re.search(p, content) for p in stdin_patterns)

    if has_stdin:
        findings["checks"].append({
            "id": "HP-002",
            "check": "Reads JSON from stdin",
            "status": "PASS",
            "message": "Uses json.load(sys.stdin) or equivalent",
            "severity": "critical",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-002",
            "check": "Reads JSON from stdin",
            "status": "FAIL",
            "message": "No json.load(sys.stdin) pattern found",
            "severity": "critical",
            "deduction": 20
        })
        findings["deduction"] += 20
        findings["status"] = "FAIL"

    # HP-003: Check JSON stdout output
    stdout_patterns = [
        r"print\s*\(\s*json\.dumps\s*\(",
        r"json\.dump\s*\([^,]+,\s*sys\.stdout",
        r"sys\.stdout\.write\s*\(\s*json\.dumps"
    ]
    has_stdout = any(re.search(p, content) for p in stdout_patterns)

    if has_stdout:
        findings["checks"].append({
            "id": "HP-003",
            "check": "Outputs JSON to stdout",
            "status": "PASS",
            "message": "Uses print(json.dumps()) or equivalent",
            "severity": "critical",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-003",
            "check": "Outputs JSON to stdout",
            "status": "FAIL",
            "message": "No JSON output pattern found",
            "severity": "critical",
            "deduction": 20
        })
        findings["deduction"] += 20
        findings["status"] = "FAIL"

    # HP-004: Check try/except
    has_try = re.search(r"\btry\s*:", content) is not None

    if has_try:
        findings["checks"].append({
            "id": "HP-004",
            "check": "Has try/except",
            "status": "PASS",
            "message": "Error handling present",
            "severity": "high",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-004",
            "check": "Has try/except",
            "status": "WARN",
            "message": "No try/except block found",
            "severity": "high",
            "deduction": 10
        })
        findings["deduction"] += 10
        if findings["status"] == "PASS":
            findings["status"] = "WARN"

    # HP-005: Check sys.exit(0) on error
    has_exit_0 = re.search(r"sys\.exit\s*\(\s*0\s*\)", content) is not None

    if has_exit_0:
        findings["checks"].append({
            "id": "HP-005",
            "check": "Uses sys.exit(0) on error",
            "status": "PASS",
            "message": "Clean exit on error",
            "severity": "high",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-005",
            "check": "Uses sys.exit(0) on error",
            "status": "WARN",
            "message": "No sys.exit(0) found - may break pipeline on error",
            "severity": "high",
            "deduction": 10
        })
        findings["deduction"] += 10
        if findings["status"] == "PASS":
            findings["status"] = "WARN"

    # HP-006: Check stderr for messages
    has_stderr = re.search(r"file\s*=\s*sys\.stderr", content) is not None

    if has_stderr:
        findings["checks"].append({
            "id": "HP-006",
            "check": "Uses stderr for messages",
            "status": "PASS",
            "message": "User messages go to stderr",
            "severity": "medium",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-006",
            "check": "Uses stderr for messages",
            "status": "INFO",
            "message": "No stderr output (may be intentional)",
            "severity": "medium",
            "deduction": 0
        })

    # HP-007: Check action field in output
    action_patterns = [
        r"['\"]action['\"]\s*:",
        r"action\s*=",
        r"\"action\"\s*:"
    ]
    has_action = any(re.search(p, content) for p in action_patterns)

    if has_action:
        findings["checks"].append({
            "id": "HP-007",
            "check": "Output has action field",
            "status": "PASS",
            "message": "Action field present in output",
            "severity": "critical",
            "deduction": 0
        })
    else:
        findings["checks"].append({
            "id": "HP-007",
            "check": "Output has action field",
            "status": "WARN",
            "message": "No 'action' field pattern found",
            "severity": "critical",
            "deduction": 5
        })
        findings["deduction"] += 5
        if findings["status"] == "PASS":
            findings["status"] = "WARN"

    return findings


def main():
    # Get plugin directory
    if len(sys.argv) > 1:
        plugin_dir = Path(sys.argv[1])
    else:
        plugin_dir = find_plugin_root()

    hooks_dir = plugin_dir / "hooks"

    if not hooks_dir.exists():
        result = {
            "category": "hook-protocol",
            "plugin_dir": str(plugin_dir),
            "score": 100,
            "max_score": 100,
            "summary": {
                "hooks_checked": 0,
                "passes": 0,
                "fails": 0,
                "warnings": 0,
                "message": "No hooks directory found"
            },
            "findings": []
        }
        print(json.dumps(result, indent=2))
        return 0

    # Find all Python hook files (excluding utils/)
    hook_files = [f for f in hooks_dir.glob("*.py")
                  if f.is_file() and not f.name.startswith("__")]

    all_findings = []
    total_deduction = 0

    for hook_file in sorted(hook_files):
        finding = check_hook_file(hook_file)
        all_findings.append(finding)
        total_deduction += finding["deduction"]

    # Calculate score (cap deduction per hook to avoid going negative)
    score = max(0, 100 - min(total_deduction, 100))

    # Summary
    passes = len([f for f in all_findings if f["status"] == "PASS"])
    fails = len([f for f in all_findings if f["status"] == "FAIL"])
    warns = len([f for f in all_findings if f["status"] == "WARN"])

    result = {
        "category": "hook-protocol",
        "plugin_dir": str(plugin_dir),
        "score": score,
        "max_score": 100,
        "summary": {
            "hooks_checked": len(hook_files),
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
