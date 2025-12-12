#!/usr/bin/env python3
"""
IP Protection Scanner

Scans for intellectual property that should NOT appear in public repositories.
Used by:
- /popkit:audit ip-leak
- /popkit:git publish (pre-publish scan)
- Nightly routine checks
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LeakFinding:
    """A potential IP leak finding."""
    file: str
    line_number: int
    pattern_name: str
    severity: str  # critical, high, medium, low
    matched_text: str
    description: str


# Patterns that should NEVER appear in the public repo
# These are checked against packages/plugin/ content before publish
FORBIDDEN_PATTERNS: Dict[str, Dict] = {
    # Cloud implementation paths (should never be in plugin)
    "cloud_code": {
        "pattern": r"packages/cloud/",
        "severity": "critical",
        "description": "Cloud API implementation code"
    },
    "cloud_billing": {
        "pattern": r"packages/cloud-billing/",
        "severity": "critical",
        "description": "Billing/payment code"
    },
    "cloud_team": {
        "pattern": r"packages/cloud-team/",
        "severity": "critical",
        "description": "Team coordination code"
    },
    "cloud_scripts": {
        "pattern": r"packages/cloud-scripts/",
        "severity": "critical",
        "description": "Cloud deployment scripts"
    },

    # Environment variables and secrets
    "stripe_key": {
        "pattern": r"STRIPE_[A-Z_]+\s*[:=]",
        "severity": "critical",
        "description": "Stripe API key reference"
    },
    "stripe_secret": {
        "pattern": r"sk_(?:live|test)_[a-zA-Z0-9]{24,}",
        "severity": "critical",
        "description": "Stripe secret key"
    },
    "upstash_token": {
        "pattern": r"UPSTASH_(?:REDIS|VECTOR)_(?:REST_)?(?:URL|TOKEN)\s*[:=]\s*['\"]?[a-zA-Z0-9_-]+",
        "severity": "critical",
        "description": "Upstash credentials"
    },
    "api_key_value": {
        "pattern": r"(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
        "severity": "critical",
        "description": "Hardcoded API key"
    },
    "bearer_token": {
        "pattern": r"Bearer\s+[a-zA-Z0-9_-]{20,}",
        "severity": "critical",
        "description": "Hardcoded bearer token"
    },

    # Explicit markers for internal content
    "proprietary_marker": {
        "pattern": r"(?i)(?:PROPRIETARY|CONFIDENTIAL|INTERNAL[_-]ONLY|SECRET[_-]SAUCE)",
        "severity": "high",
        "description": "Proprietary content marker"
    },
    "secret_comment": {
        "pattern": r"#\s*SECRET:",
        "severity": "high",
        "description": "Secret marker in comment"
    },
    "internal_only": {
        "pattern": r"(?i)internal[_-]?only",
        "severity": "medium",
        "description": "Internal-only marker"
    },
    "do_not_publish": {
        "pattern": r"(?i)do[_-]?not[_-]?publish",
        "severity": "high",
        "description": "Do-not-publish marker"
    },

    # Premium/paid feature detection logic
    "premium_logic": {
        "pattern": r"(?:is_?premium|check_?premium|premium_?only|paid_?feature)",
        "severity": "medium",
        "description": "Premium feature detection logic"
    },

    # Cloud URLs (production endpoints)
    "cloud_prod_url": {
        "pattern": r"https://api\.popkit\.cloud",
        "severity": "medium",
        "description": "Production API URL"
    },

    # Private repository references
    "private_repo_ref": {
        "pattern": r"jrc1883/popkit(?!\-claude)",
        "severity": "low",
        "description": "Reference to private repo (not popkit-claude)"
    },
}

# Files to always skip (not check)
SKIP_PATTERNS: List[str] = [
    r"\.git/",
    r"node_modules/",
    r"node_modules\\",  # Windows path separator
    r"__pycache__/",
    r"\.pyc$",
    r"\.pyo$",
    r"\.whl$",
    r"\.egg-info/",
    r"dist/",
    r"build/",
    r"\.DS_Store",
    r"\.env\.example$",  # Examples are OK
    r"\.lock$",          # Lock files
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"\.d\.ts$",         # Type definitions
    r"\.min\.js$",       # Minified files
    r"\.min\.css$",
]

# Files where certain patterns are allowed (false positive exclusions)
ALLOWED_EXCEPTIONS: Dict[str, List[str]] = {
    # This file itself can mention patterns
    "ip_protection.py": list(FORBIDDEN_PATTERNS.keys()),
    # CLAUDE.md documents what's private
    "CLAUDE.md": ["cloud_code", "cloud_billing", "private_repo_ref", "premium_logic",
                  "cloud_team", "cloud_scripts"],
    # Audit command documents the ip-leak feature (lists patterns as examples)
    "audit.md": list(FORBIDDEN_PATTERNS.keys()),
    # Git command documents publishing
    "git.md": ["private_repo_ref", "cloud_code"],
    # Project command documents architecture
    "project.md": ["cloud_code", "cloud_billing", "cloud_team", "cloud_scripts"],
    # Upgrade command has example API key placeholder
    "upgrade.md": ["api_key_value"],
    # Cloud setup docs have example placeholders
    "cloud-setup.md": ["api_key_value", "upstash_token"],
    # Power mode README has example env vars
    "README.md": ["upstash_token"],
    # Privacy module has test patterns
    "privacy.py": ["api_key_value", "stripe_secret"],
    # Plan documents can reference cloud structure
    "2025-12-08-monorepo-conversion.md": ["cloud_code", "cloud_billing", "cloud_team", "cloud_scripts"],
    # Test files can contain patterns
    "test_ip_protection.py": list(FORBIDDEN_PATTERNS.keys()),
    # Output styles mention terms in templates
    "pdf-report.md": ["proprietary_marker"],
    # Git command mentions proprietary
    "git.md": ["private_repo_ref", "cloud_code", "proprietary_marker"],
    # Routine command mentions proprietary
    "routine.md": ["proprietary_marker"],
    # Hooks that check premium status (legitimate functionality)
    "pre-tool-use.py": ["premium_logic"],
    "premium_checker.py": ["premium_logic"],
    "premium_client.py": ["premium_logic"],
    # Skills that mention premium as examples
    "SKILL.md": ["premium_logic"],
    # Plugin metadata references the private repo legitimately
    "plugin.json": ["private_repo_ref"],
    ".mcp.json": ["private_repo_ref"],
    "version.py": ["private_repo_ref"],
}


def should_skip_file(filepath: str) -> bool:
    """Check if a file should be skipped from scanning."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, filepath):
            return True
    return False


def is_exception(filepath: str, pattern_name: str) -> bool:
    """Check if a pattern is allowed as an exception in a specific file."""
    filename = Path(filepath).name
    if filename in ALLOWED_EXCEPTIONS:
        return pattern_name in ALLOWED_EXCEPTIONS[filename]
    return False


def scan_content(content: str, filepath: str = "") -> List[LeakFinding]:
    """Scan content for IP leaks."""
    findings: List[LeakFinding] = []
    lines = content.split('\n')

    for pattern_name, config in FORBIDDEN_PATTERNS.items():
        # Skip if this pattern is an allowed exception for this file
        if filepath and is_exception(filepath, pattern_name):
            continue

        regex = re.compile(config["pattern"], re.IGNORECASE if "(?i)" not in config["pattern"] else 0)

        for line_num, line in enumerate(lines, 1):
            match = regex.search(line)
            if match:
                findings.append(LeakFinding(
                    file=filepath,
                    line_number=line_num,
                    pattern_name=pattern_name,
                    severity=config["severity"],
                    matched_text=match.group(0)[:50] + "..." if len(match.group(0)) > 50 else match.group(0),
                    description=config["description"]
                ))

    return findings


def scan_file(filepath: Path) -> List[LeakFinding]:
    """Scan a single file for IP leaks."""
    if should_skip_file(str(filepath)):
        return []

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        return scan_content(content, str(filepath))
    except Exception:
        return []


def scan_directory(directory: Path, recursive: bool = True) -> List[LeakFinding]:
    """Scan a directory for IP leaks."""
    findings: List[LeakFinding] = []

    if recursive:
        files = directory.rglob('*')
    else:
        files = directory.glob('*')

    for filepath in files:
        if filepath.is_file():
            findings.extend(scan_file(filepath))

    return findings


def scan_git_history(directory: Path, depth: int = 100) -> List[LeakFinding]:
    """Scan git history for leaked secrets (deep scan)."""
    findings: List[LeakFinding] = []

    try:
        # Get recent commits
        result = subprocess.run(
            ['git', 'log', f'-{depth}', '--diff-filter=A', '--name-only', '--pretty=format:%H'],
            cwd=directory,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return findings

        # Parse commits and check added files
        current_commit = None
        for line in result.stdout.split('\n'):
            if len(line) == 40:  # Commit hash
                current_commit = line
            elif line and current_commit:
                # Get file content at that commit
                try:
                    file_result = subprocess.run(
                        ['git', 'show', f'{current_commit}:{line}'],
                        cwd=directory,
                        capture_output=True,
                        text=True
                    )
                    if file_result.returncode == 0:
                        content_findings = scan_content(file_result.stdout, f"{line} (commit {current_commit[:8]})")
                        findings.extend(content_findings)
                except Exception:
                    pass

    except Exception:
        pass

    return findings


def format_findings_report(findings: List[LeakFinding], format_type: str = "markdown") -> str:
    """Format findings into a report."""
    if not findings:
        return "No IP leaks detected."

    # Group by severity
    critical = [f for f in findings if f.severity == "critical"]
    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]
    low = [f for f in findings if f.severity == "low"]

    if format_type == "json":
        import json
        return json.dumps([{
            "file": f.file,
            "line": f.line_number,
            "pattern": f.pattern_name,
            "severity": f.severity,
            "matched": f.matched_text,
            "description": f.description
        } for f in findings], indent=2)

    # Markdown format
    lines = ["# IP Leak Scan Report", ""]
    lines.append(f"**Found {len(findings)} potential issues**")
    lines.append(f"- Critical: {len(critical)}")
    lines.append(f"- High: {len(high)}")
    lines.append(f"- Medium: {len(medium)}")
    lines.append(f"- Low: {len(low)}")
    lines.append("")

    def format_finding(f: LeakFinding) -> str:
        return f"- **{f.file}:{f.line_number}** - `{f.matched_text}`\n  {f.description}"

    if critical:
        lines.append("## Critical Issues")
        lines.append("")
        for f in critical:
            lines.append(format_finding(f))
        lines.append("")

    if high:
        lines.append("## High Priority Issues")
        lines.append("")
        for f in high:
            lines.append(format_finding(f))
        lines.append("")

    if medium:
        lines.append("## Medium Priority Issues")
        lines.append("")
        for f in medium:
            lines.append(format_finding(f))
        lines.append("")

    if low:
        lines.append("## Low Priority Issues")
        lines.append("")
        for f in low:
            lines.append(format_finding(f))
        lines.append("")

    return '\n'.join(lines)


def scan_pre_publish(plugin_dir: Path) -> Tuple[bool, str]:
    """
    Pre-publish scan for /popkit:git publish.
    Returns (is_safe, report).
    """
    findings = scan_directory(plugin_dir)

    # Critical or high findings block publish
    critical_or_high = [f for f in findings if f.severity in ("critical", "high")]

    if critical_or_high:
        report = format_findings_report(findings)
        return False, f"BLOCKED: Found {len(critical_or_high)} critical/high severity issues.\n\n{report}"

    if findings:
        report = format_findings_report(findings)
        return True, f"WARNING: Found {len(findings)} low/medium issues (allowing publish).\n\n{report}"

    return True, "No IP leaks detected. Safe to publish."


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Scan for IP leaks")
    parser.add_argument("path", nargs="?", default=".", help="Path to scan")
    parser.add_argument("--deep", action="store_true", help="Include git history scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--pre-publish", action="store_true", help="Pre-publish scan mode")

    args = parser.parse_args()
    path = Path(args.path)

    if args.pre_publish:
        is_safe, report = scan_pre_publish(path)
        print(report)
        sys.exit(0 if is_safe else 1)

    findings = scan_directory(path)

    if args.deep:
        findings.extend(scan_git_history(path))

    format_type = "json" if args.json else "markdown"
    print(format_findings_report(findings, format_type))

    # Exit with error if critical/high issues found
    critical_or_high = [f for f in findings if f.severity in ("critical", "high")]
    sys.exit(1 if critical_or_high else 0)
