#!/usr/bin/env python3
"""
Security Scanner Utility

Part of Issue #44 (Automated Security Vulnerability Detection)

Scans npm dependencies for vulnerabilities and creates GitHub issues.
Integrates with morning/nightly routines for automated tracking.
"""

import json
import subprocess
import sys
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    name: str
    severity: str  # critical, high, moderate, low
    title: str
    url: str
    vulnerable_versions: str
    patched_versions: Optional[str]
    cve: Optional[str] = None
    ghsa: Optional[str] = None
    fix_available: bool = False
    direct: bool = False  # Direct dependency vs transitive

    @property
    def identifier(self) -> str:
        """Get unique identifier for deduplication."""
        if self.cve:
            return self.cve
        if self.ghsa:
            return self.ghsa
        return f"{self.name}-{self.vulnerable_versions}"

    @property
    def severity_score(self) -> int:
        """Numeric severity for sorting."""
        scores = {"critical": 4, "high": 3, "moderate": 2, "low": 1}
        return scores.get(self.severity.lower(), 0)


@dataclass
class ScanResult:
    """Result of a security scan."""
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    total_packages: int = 0
    scan_time: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    @property
    def by_severity(self) -> Dict[str, List[Vulnerability]]:
        """Group vulnerabilities by severity."""
        result: Dict[str, List[Vulnerability]] = {
            "critical": [],
            "high": [],
            "moderate": [],
            "low": []
        }
        for vuln in self.vulnerabilities:
            severity = vuln.severity.lower()
            if severity in result:
                result[severity].append(vuln)
        return result

    @property
    def counts(self) -> Dict[str, int]:
        """Count by severity."""
        by_sev = self.by_severity
        return {k: len(v) for k, v in by_sev.items()}

    @property
    def fixable_count(self) -> int:
        """Count of auto-fixable vulnerabilities."""
        return sum(1 for v in self.vulnerabilities if v.fix_available)

    def score_impact(self) -> int:
        """Calculate score impact for routines."""
        impact = 0
        for vuln in self.vulnerabilities:
            if vuln.severity.lower() == "critical":
                impact += 20
            elif vuln.severity.lower() == "high":
                impact += 10
            elif vuln.severity.lower() == "moderate":
                impact += 5
            elif vuln.severity.lower() == "low":
                impact += 2
        return min(impact, 30)  # Cap at 30 points


@dataclass
class ExistingIssue:
    """Represents an existing GitHub issue."""
    number: int
    title: str
    state: str
    url: str


# =============================================================================
# SCANNER
# =============================================================================

class SecurityScanner:
    """
    Scans npm dependencies for security vulnerabilities.

    Features:
    - npm audit integration
    - GitHub issue creation
    - Duplicate detection
    - Routine integration
    """

    def __init__(self, project_path: Optional[str] = None):
        """Initialize scanner with project path."""
        self.project_path = project_path or os.getcwd()

    def scan(self) -> ScanResult:
        """
        Run npm audit and parse results.

        Returns:
            ScanResult with vulnerabilities
        """
        result = ScanResult()

        # Check for package.json
        package_json = Path(self.project_path) / "package.json"
        if not package_json.exists():
            result.error = "No package.json found"
            return result

        try:
            # Run npm audit
            proc = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            # npm audit returns non-zero if vulnerabilities found
            audit_data = json.loads(proc.stdout) if proc.stdout else {}

            # Parse metadata
            result.total_packages = audit_data.get("metadata", {}).get("totalDependencies", 0)

            # Parse vulnerabilities
            vulnerabilities = audit_data.get("vulnerabilities", {})

            for name, vuln_data in vulnerabilities.items():
                # Skip if it's just severity info without actual vulnerability
                if not vuln_data.get("via"):
                    continue

                # Get the first advisory (primary vulnerability)
                via = vuln_data.get("via", [])
                if isinstance(via, list) and via:
                    advisory = via[0] if isinstance(via[0], dict) else {}
                else:
                    advisory = {}

                vuln = Vulnerability(
                    name=name,
                    severity=vuln_data.get("severity", "unknown"),
                    title=advisory.get("title", f"Vulnerability in {name}"),
                    url=advisory.get("url", ""),
                    vulnerable_versions=vuln_data.get("range", "*"),
                    patched_versions=vuln_data.get("fixAvailable", {}).get("version") if isinstance(vuln_data.get("fixAvailable"), dict) else None,
                    cve=advisory.get("cve"),
                    ghsa=advisory.get("ghsa") or self._extract_ghsa(advisory.get("url", "")),
                    fix_available=bool(vuln_data.get("fixAvailable")),
                    direct=vuln_data.get("isDirect", False)
                )

                result.vulnerabilities.append(vuln)

            # Sort by severity
            result.vulnerabilities.sort(key=lambda v: v.severity_score, reverse=True)

        except subprocess.TimeoutExpired:
            result.error = "npm audit timed out"
        except json.JSONDecodeError as e:
            result.error = f"Failed to parse npm audit output: {e}"
        except FileNotFoundError:
            result.error = "npm not found in PATH"
        except Exception as e:
            result.error = str(e)

        return result

    def _extract_ghsa(self, url: str) -> Optional[str]:
        """Extract GHSA ID from advisory URL."""
        if "GHSA-" in url:
            parts = url.split("/")
            for part in parts:
                if part.startswith("GHSA-"):
                    return part
        return None

    def get_existing_issues(self) -> List[ExistingIssue]:
        """
        Get existing security issues from GitHub.

        Returns:
            List of existing security issues
        """
        issues = []

        try:
            proc = subprocess.run(
                ["gh", "issue", "list", "--label", "security", "--json", "number,title,state,url", "--limit", "100"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout)
                for item in data:
                    issues.append(ExistingIssue(
                        number=item["number"],
                        title=item["title"],
                        state=item["state"],
                        url=item["url"]
                    ))
        except Exception:
            pass  # Silently fail if gh not available

        return issues

    def find_existing_issue(self, vuln: Vulnerability, existing: List[ExistingIssue]) -> Optional[ExistingIssue]:
        """
        Check if vulnerability already has a tracking issue.

        Args:
            vuln: Vulnerability to check
            existing: List of existing issues

        Returns:
            Matching issue or None
        """
        identifier = vuln.identifier
        name = vuln.name.lower()

        for issue in existing:
            title_lower = issue.title.lower()
            # Check for CVE/GHSA in title
            if identifier and identifier.lower() in title_lower:
                return issue
            # Check for package name in title
            if name in title_lower and ("vulnerability" in title_lower or "security" in title_lower):
                return issue

        return None

    def create_issue(self, vuln: Vulnerability, dry_run: bool = False) -> Optional[int]:
        """
        Create GitHub issue for vulnerability.

        Args:
            vuln: Vulnerability to create issue for
            dry_run: If True, don't actually create

        Returns:
            Issue number or None
        """
        # Build title
        id_part = vuln.cve or vuln.ghsa or ""
        title = f"[{vuln.severity.upper()}] {id_part}: {vuln.name} vulnerability" if id_part else f"[{vuln.severity.upper()}] Security vulnerability in {vuln.name}"

        # Build body
        body = f"""## Security Vulnerability: {vuln.name}

**Severity:** {vuln.severity.upper()}
**Package:** {vuln.name}
**Vulnerable Versions:** {vuln.vulnerable_versions}
"""

        if vuln.patched_versions:
            body += f"**Patched Version:** {vuln.patched_versions}\n"

        if vuln.cve:
            body += f"**CVE:** {vuln.cve}\n"

        if vuln.ghsa:
            body += f"**GHSA:** {vuln.ghsa}\n"

        body += f"""
### Description

{vuln.title}

### Remediation

```bash
npm update {vuln.name}
"""

        if vuln.patched_versions:
            body += f"# or\nnpm install {vuln.name}@{vuln.patched_versions}\n"

        body += "```\n"

        if vuln.url:
            body += f"""
### References

- [Advisory]({vuln.url})
"""

        body += """
---
*Auto-generated by PopKit Security Scan*
*Run `/popkit:security fix` to attempt automatic remediation*
"""

        if dry_run:
            return None

        # Determine labels
        labels = ["security", "automated"]
        if vuln.severity.lower() == "critical":
            labels.append("priority:critical")
        elif vuln.severity.lower() == "high":
            labels.append("priority:high")

        try:
            proc = subprocess.run(
                ["gh", "issue", "create", "--title", title, "--body", body, "--label", ",".join(labels)],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if proc.returncode == 0:
                # Extract issue number from output
                output = proc.stdout.strip()
                if "/issues/" in output:
                    return int(output.split("/issues/")[-1])
        except Exception:
            pass

        return None

    def run_fix(self, force: bool = False) -> Dict[str, Any]:
        """
        Run npm audit fix.

        Args:
            force: Include breaking changes

        Returns:
            Fix result
        """
        cmd = ["npm", "audit", "fix"]
        if force:
            cmd.append("--force")

        result = {
            "success": False,
            "fixed": [],
            "remaining": [],
            "error": None
        }

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            result["success"] = proc.returncode == 0
            result["output"] = proc.stdout

            # Re-scan to see what's left
            post_scan = self.scan()
            result["remaining"] = [v.name for v in post_scan.vulnerabilities]

        except Exception as e:
            result["error"] = str(e)

        return result


# =============================================================================
# REPORT FORMATTING
# =============================================================================

def format_scan_report(result: ScanResult, existing_issues: List[ExistingIssue] = None) -> str:
    """Format scan result as human-readable report."""
    existing_issues = existing_issues or []

    lines = [
        "Security Scan Report",
        "=" * 50,
        f"Date: {result.scan_time[:10]}",
        f"Packages Scanned: {result.total_packages}",
        "",
    ]

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    # Summary
    counts = result.counts
    lines.extend([
        "Vulnerabilities Found:",
        f"  Critical: {counts['critical']}",
        f"  High: {counts['high']}",
        f"  Moderate: {counts['moderate']}",
        f"  Low: {counts['low']}",
        "",
        f"Auto-Fixable: {result.fixable_count} of {len(result.vulnerabilities)}",
        "",
    ])

    # Details for high+ severity
    high_plus = result.by_severity["critical"] + result.by_severity["high"]
    if high_plus:
        lines.append("High Priority Vulnerabilities:")
        for vuln in high_plus:
            id_str = vuln.cve or vuln.ghsa or "N/A"
            lines.append(f"  [{vuln.severity.upper()}] {vuln.name}")
            lines.append(f"    ID: {id_str}")
            lines.append(f"    Versions: {vuln.vulnerable_versions}")
            if vuln.patched_versions:
                lines.append(f"    Fix: {vuln.patched_versions}")
            lines.append("")

    # Score impact
    impact = result.score_impact()
    if impact > 0:
        lines.append(f"Score Impact: -{impact} points")

    return "\n".join(lines)


def format_github_issue_body(vuln: Vulnerability) -> str:
    """Format vulnerability as GitHub issue body."""
    scanner = SecurityScanner()
    # Reuse the create_issue logic but return body only
    # This is a simplified version
    return f"""## Security Vulnerability: {vuln.name}

**Severity:** {vuln.severity.upper()}
**Package:** {vuln.name}
**Vulnerable Versions:** {vuln.vulnerable_versions}
**CVE:** {vuln.cve or 'N/A'}

### Description
{vuln.title}

### Advisory
{vuln.url}

---
*Auto-generated by PopKit Security Scan*
"""


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Security vulnerability scanner")
    parser.add_argument("--path", "-p", help="Project path", default=os.getcwd())
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Don't create issues")
    parser.add_argument("--severity", "-s", choices=["low", "moderate", "high", "critical"], help="Minimum severity")

    args = parser.parse_args()

    scanner = SecurityScanner(args.path)
    result = scanner.scan()

    if args.json:
        output = {
            "vulnerabilities": [
                {
                    "name": v.name,
                    "severity": v.severity,
                    "cve": v.cve,
                    "ghsa": v.ghsa,
                    "fix_available": v.fix_available
                }
                for v in result.vulnerabilities
            ],
            "counts": result.counts,
            "total_packages": result.total_packages,
            "error": result.error
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_scan_report(result))
