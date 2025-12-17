#!/usr/bin/env python3
"""
Scan for Injection Vulnerabilities

Detects command injection, path traversal, and other injection vulnerabilities.

Usage:
    python scan_injection.py [plugin_dir]

Output:
    JSON object with findings and score
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


# Injection patterns with CWE mappings
INJECTION_PATTERNS = {
    "IP-001": {
        "name": "Command Injection - os.system",
        "pattern": r"os\.system\s*\([^)]*\+",
        "severity": "critical",
        "cwe": "CWE-78",
        "deduction": 25,
        "description": "Potential command injection via os.system() with string concatenation"
    },
    "IP-002": {
        "name": "Command Injection - subprocess shell=True",
        "pattern": r"subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True",
        "severity": "critical",
        "cwe": "CWE-78",
        "deduction": 25,
        "description": "Potential command injection via subprocess with shell=True"
    },
    "IP-003": {
        "name": "Command Injection - eval",
        "pattern": r"\beval\s*\([^)]*(?:input|request|params|args|user)",
        "severity": "critical",
        "cwe": "CWE-94",
        "deduction": 25,
        "description": "Potential code injection via eval() with user input"
    },
    "IP-004": {
        "name": "Command Injection - exec",
        "pattern": r"\bexec\s*\([^)]*(?:input|request|params|args|user)",
        "severity": "critical",
        "cwe": "CWE-94",
        "deduction": 25,
        "description": "Potential code injection via exec() with user input"
    },
    "IP-005": {
        "name": "Path Traversal",
        "pattern": r"(?:open|read|write|Path)\s*\([^)]*(?:\+|\.format\(|f['\"])[^)]*(?:input|request|params|args|user)",
        "severity": "high",
        "cwe": "CWE-22",
        "deduction": 20,
        "description": "Potential path traversal via unsanitized file path"
    },
    "IP-006": {
        "name": "SQL Injection",
        "pattern": r"(?:execute|query|raw)\s*\([^)]*['\"].*%s.*['\"].*%",
        "severity": "critical",
        "cwe": "CWE-89",
        "deduction": 25,
        "description": "Potential SQL injection via string formatting"
    },
    "IP-007": {
        "name": "Template Injection",
        "pattern": r"(?:render|Template)\s*\([^)]*(?:\+|\.format\(|f['\"])[^)]*(?:input|request|params)",
        "severity": "high",
        "cwe": "CWE-94",
        "deduction": 20,
        "description": "Potential template injection via user input"
    },
    "IP-008": {
        "name": "Unsafe Deserialization",
        "pattern": r"(?:pickle\.loads?|yaml\.(?:unsafe_)?load|marshal\.loads?)\s*\([^)]*(?:input|request|data)",
        "severity": "critical",
        "cwe": "CWE-502",
        "deduction": 25,
        "description": "Potential unsafe deserialization"
    }
}

# Safe patterns that should not be flagged
SAFE_PATTERNS = [
    r"shell\s*=\s*False",
    r"shlex\.quote",
    r"shlex\.split",
    r"subprocess\.run\s*\(\s*\[",  # List form is safer
    r"parameterized",
    r"prepared_statement"
]

# File patterns to scan
SCAN_PATTERNS = [
    "**/*.py",
    "**/*.js",
    "**/*.ts"
]

# Files to exclude
EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/__pycache__/**",
    "**/test*/**",
    "**/*.test.*",
    "**/*.spec.*"
]


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


def should_exclude(filepath: Path, plugin_dir: Path) -> bool:
    """Check if file should be excluded from scanning."""
    rel_path = str(filepath.relative_to(plugin_dir))

    for pattern in EXCLUDE_PATTERNS:
        pattern_parts = pattern.replace("**", ".*").replace("*", "[^/]*")
        if re.match(pattern_parts, rel_path):
            return True

    return False


def has_safe_pattern(line: str) -> bool:
    """Check if line contains a safe pattern that mitigates the vulnerability."""
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def scan_file(filepath: Path, plugin_dir: Path) -> List[Dict]:
    """Scan a single file for injection vulnerabilities."""
    findings = []

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
    except Exception:
        return findings

    rel_path = str(filepath.relative_to(plugin_dir))

    for check_id, check in INJECTION_PATTERNS.items():
        pattern = check["pattern"]

        for line_num, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                # Check for safe patterns
                if has_safe_pattern(line):
                    continue

                # Check context (previous/next lines for mitigation)
                context_start = max(0, line_num - 3)
                context_end = min(len(lines), line_num + 2)
                context = '\n'.join(lines[context_start:context_end])

                if has_safe_pattern(context):
                    continue

                # Truncate line for display
                display_line = line.strip()[:80]
                if len(line.strip()) > 80:
                    display_line += "..."

                findings.append({
                    "id": check_id,
                    "name": check["name"],
                    "file": rel_path,
                    "line": line_num,
                    "content": display_line,
                    "severity": check["severity"],
                    "cwe": check["cwe"],
                    "description": check["description"],
                    "deduction": check["deduction"]
                })

    return findings


def main():
    # Get plugin directory
    if len(sys.argv) > 1:
        plugin_dir = Path(sys.argv[1])
    else:
        plugin_dir = find_plugin_root()

    if not plugin_dir.exists():
        result = {
            "category": "injection-prevention",
            "plugin_dir": str(plugin_dir),
            "score": 0,
            "max_score": 100,
            "error": "Plugin directory not found",
            "findings": []
        }
        print(json.dumps(result, indent=2))
        return 1

    # Collect all files to scan
    files_to_scan = []
    for pattern in SCAN_PATTERNS:
        for filepath in plugin_dir.glob(pattern):
            if filepath.is_file() and not should_exclude(filepath, plugin_dir):
                files_to_scan.append(filepath)

    # Scan all files
    all_findings = []
    for filepath in files_to_scan:
        findings = scan_file(filepath, plugin_dir)
        all_findings.extend(findings)

    # Calculate score
    total_deduction = sum(f["deduction"] for f in all_findings)
    score = max(0, 100 - min(total_deduction, 100))

    # Summary by severity
    by_severity = {}
    for f in all_findings:
        sev = f["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # Summary by CWE
    by_cwe = {}
    for f in all_findings:
        cwe = f["cwe"]
        by_cwe[cwe] = by_cwe.get(cwe, 0) + 1

    result = {
        "category": "injection-prevention",
        "plugin_dir": str(plugin_dir),
        "score": score,
        "max_score": 100,
        "summary": {
            "files_scanned": len(files_to_scan),
            "vulnerabilities_found": len(all_findings),
            "critical": by_severity.get("critical", 0),
            "high": by_severity.get("high", 0),
            "medium": by_severity.get("medium", 0),
            "by_cwe": by_cwe,
            "total_deduction": total_deduction
        },
        "patterns_checked": list(INJECTION_PATTERNS.keys()),
        "findings": all_findings
    }

    print(json.dumps(result, indent=2))
    return 0 if len(all_findings) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
