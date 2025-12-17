#!/usr/bin/env python3
"""
Scan for Hardcoded Secrets

Detects hardcoded API keys, passwords, tokens, and credentials.

Usage:
    python scan_secrets.py [plugin_dir]

Output:
    JSON object with findings and score
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


# Secret detection patterns with CWE mappings
SECRET_PATTERNS = {
    "SD-001": {
        "name": "API Key",
        "pattern": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
        "severity": "critical",
        "cwe": "CWE-798",
        "deduction": 25,
        "description": "Hardcoded API key detected"
    },
    "SD-002": {
        "name": "AWS Access Key",
        "pattern": r"(?i)(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}",
        "severity": "critical",
        "cwe": "CWE-798",
        "deduction": 25,
        "description": "AWS access key ID detected"
    },
    "SD-003": {
        "name": "AWS Secret Key",
        "pattern": r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
        "severity": "critical",
        "cwe": "CWE-798",
        "deduction": 25,
        "description": "AWS secret access key detected"
    },
    "SD-004": {
        "name": "Password Assignment",
        "pattern": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "severity": "high",
        "cwe": "CWE-259",
        "deduction": 20,
        "description": "Hardcoded password detected"
    },
    "SD-005": {
        "name": "Private Key",
        "pattern": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "critical",
        "cwe": "CWE-321",
        "deduction": 25,
        "description": "Private key detected in code"
    },
    "SD-006": {
        "name": "JWT Token",
        "pattern": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        "severity": "high",
        "cwe": "CWE-798",
        "deduction": 20,
        "description": "JWT token detected in code"
    },
    "SD-007": {
        "name": "GitHub Token",
        "pattern": r"(?i)(gh[pousr]_[A-Za-z0-9_]{36}|github[_-]?token\s*[:=]\s*['\"][^'\"]+['\"])",
        "severity": "critical",
        "cwe": "CWE-798",
        "deduction": 25,
        "description": "GitHub token detected"
    },
    "SD-008": {
        "name": "Database Connection String",
        "pattern": r"(?i)(mongodb|mysql|postgres|redis)://[^\s'\"]+:[^\s'\"]+@",
        "severity": "critical",
        "cwe": "CWE-798",
        "deduction": 25,
        "description": "Database credentials in connection string"
    },
    "SD-009": {
        "name": "Bearer Token",
        "pattern": r"(?i)bearer\s+[a-zA-Z0-9_-]{20,}",
        "severity": "high",
        "cwe": "CWE-798",
        "deduction": 20,
        "description": "Bearer token detected"
    },
    "SD-010": {
        "name": "Generic Secret",
        "pattern": r"(?i)(secret|token|credential)[_-]?(key|value)?\s*[:=]\s*['\"][a-zA-Z0-9_-]{16,}['\"]",
        "severity": "high",
        "cwe": "CWE-798",
        "deduction": 15,
        "description": "Generic secret pattern detected"
    }
}

# File patterns to scan
SCAN_PATTERNS = [
    "**/*.py",
    "**/*.js",
    "**/*.ts",
    "**/*.json",
    "**/*.yml",
    "**/*.yaml",
    "**/*.md",
    "**/*.env*",
    "**/*.config.*"
]

# Files to exclude
EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/__pycache__/**",
    "**/test-data/**",
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
        # Simple glob-like matching
        pattern_parts = pattern.replace("**", ".*").replace("*", "[^/]*")
        if re.match(pattern_parts, rel_path):
            return True

    return False


def is_likely_example(line: str, filepath: Path) -> bool:
    """Check if the match is likely an example or placeholder."""
    # Common placeholder patterns
    placeholders = [
        r"your[_-]?api[_-]?key",
        r"xxx+",
        r"<[^>]+>",
        r"\$\{[^}]+\}",
        r"example",
        r"placeholder",
        r"dummy",
        r"test",
        r"sample"
    ]

    line_lower = line.lower()
    for placeholder in placeholders:
        if re.search(placeholder, line_lower):
            return True

    # Check if in a documentation file
    if filepath.suffix in ['.md', '.rst', '.txt']:
        return True

    return False


def scan_file(filepath: Path, plugin_dir: Path) -> List[Dict]:
    """Scan a single file for secrets."""
    findings = []

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
    except Exception:
        return findings

    rel_path = str(filepath.relative_to(plugin_dir))

    for check_id, check in SECRET_PATTERNS.items():
        pattern = check["pattern"]

        for line_num, line in enumerate(lines, 1):
            if re.search(pattern, line):
                # Skip likely examples
                if is_likely_example(line, filepath):
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
            "category": "secret-detection",
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

    # Summary
    by_severity = {}
    for f in all_findings:
        sev = f["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    result = {
        "category": "secret-detection",
        "plugin_dir": str(plugin_dir),
        "score": score,
        "max_score": 100,
        "summary": {
            "files_scanned": len(files_to_scan),
            "secrets_found": len(all_findings),
            "critical": by_severity.get("critical", 0),
            "high": by_severity.get("high", 0),
            "medium": by_severity.get("medium", 0),
            "total_deduction": total_deduction
        },
        "patterns_checked": list(SECRET_PATTERNS.keys()),
        "findings": all_findings
    }

    print(json.dumps(result, indent=2))
    return 0 if len(all_findings) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
