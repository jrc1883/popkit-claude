---
description: "scan | list | fix | report [--dry-run, --severity, --fix]"
argument-hint: "<subcommand> [options]"
---

# /popkit:security - Security Vulnerability Management

Automated security scanning, issue creation, and vulnerability tracking.

## Usage

```
/popkit:security [subcommand] [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `scan` (default) | Full security scan with issue creation |
| `list` | List tracked vulnerabilities and issues |
| `fix` | Attempt automatic remediation |
| `report` | Generate detailed report |

---

## Scan (Default)

Run a comprehensive security audit and create GitHub issues for tracking.

```
/popkit:security                        # Full scan, create issues
/popkit:security scan                   # Same as above
/popkit:security scan --dry-run         # Preview without creating issues
/popkit:security scan --severity high   # Only HIGH+ severity
/popkit:security scan --no-issues       # Scan only, no issue creation
```

### Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview what issues would be created |
| `--severity <level>` | Minimum severity: `low`, `moderate`, `high`, `critical` |
| `--no-issues` | Scan and report only, skip issue creation |
| `--json` | Output in JSON format |

### Scan Process

1. **Run npm audit** - Parse `npm audit --json` output
2. **Check duplicates** - Search existing GitHub issues by CVE/GHSA ID
3. **Create issues** - For HIGH/CRITICAL without existing tracking
4. **Generate report** - Summary with recommendations

### Example Output

```
Security Scan - popkit
======================
Date: 2024-12-09

Scanning npm dependencies...
Analyzing 847 packages

Vulnerabilities Found:
  Critical: 0
  High: 2
  Moderate: 5
  Low: 3

Checking GitHub for existing issues...

Issues Created:
  #42 - CVE-2024-1234: nodemailer DoS vulnerability (HIGH)

Already Tracked:
  #38 - lodash prototype pollution (open)

Auto-Fixable: 7 of 10

Recommendations:
  1. Run `/popkit:security fix` to resolve 7 vulnerabilities
  2. Review #42 for manual remediation steps
  3. Consider upgrading lodash (breaking changes)

Score Impact: -10 points (Sleep Score / Ready to Code)
```

---

## List

View tracked vulnerabilities and their status.

```
/popkit:security list                   # All tracked vulnerabilities
/popkit:security list --open            # Only open issues
/popkit:security list --resolved        # Fixed vulnerabilities
/popkit:security list --severity high   # Filter by severity
```

### Example Output

```
Security Issues - popkit
========================

Open (3):
  #42 [HIGH] CVE-2024-1234: nodemailer DoS vulnerability
      Package: nodemailer <=7.0.10
      Fix: npm update nodemailer

  #38 [HIGH] GHSA-abcd: lodash prototype pollution
      Package: lodash <4.17.21
      Fix: npm update lodash (breaking changes)

  #35 [MOD] CVE-2024-5678: express-session fixation
      Package: express-session <1.18.0
      Fix: npm update express-session

Resolved (2):
  #30 [HIGH] CVE-2024-0001: axios SSRF (fixed in 1.6.0)
  #28 [MOD] GHSA-wxyz: json5 prototype pollution (fixed)

Summary: 3 open, 2 resolved
```

---

## Fix

Attempt automatic remediation of vulnerabilities.

```
/popkit:security fix                    # Run npm audit fix
/popkit:security fix --force            # Include breaking changes
/popkit:security fix --pr               # Create PR with fixes
/popkit:security fix --dry-run          # Preview what would change
```

### Flags

| Flag | Description |
|------|-------------|
| `--force` | Apply fixes even with breaking changes |
| `--pr` | Create a Pull Request with the fixes |
| `--dry-run` | Show what would be fixed without applying |
| `--package <name>` | Fix specific package only |

### Example Output

```
Security Fix - popkit
=====================

Running npm audit fix...

Fixed (4):
  lodash: 4.17.19 -> 4.17.21
  minimist: 1.2.5 -> 1.2.8
  json5: 2.2.0 -> 2.2.3
  semver: 6.3.0 -> 6.3.1

Remaining (2):
  nodemailer: Requires major version upgrade (breaking)
  mdast-util-to-hast: Peer dependency conflict

Next Steps:
  - Run `/popkit:security fix --force` for breaking changes
  - Or manually update: npm install nodemailer@latest

Updated package-lock.json
Run `npm test` to verify changes
```

---

## Report

Generate a detailed security report without creating issues.

```
/popkit:security report                 # Human-readable report
/popkit:security report --json          # JSON format
/popkit:security report --md            # Markdown format
/popkit:security report --output file   # Save to file
```

### Example Output (Markdown)

```markdown
# Security Report: popkit
Generated: 2024-12-09T10:30:00Z

## Summary

| Severity | Count | Auto-Fixable |
|----------|-------|--------------|
| Critical | 0 | - |
| High | 2 | 1 |
| Moderate | 5 | 4 |
| Low | 3 | 2 |
| **Total** | **10** | **7** |

## Critical & High Vulnerabilities

### nodemailer (HIGH)
- **CVE:** CVE-2024-1234
- **Versions:** <=7.0.10
- **Fix:** 7.0.11
- **Type:** Denial of Service
- **Advisory:** https://github.com/advisories/GHSA-xxxx

### lodash (HIGH)
- **CVE:** CVE-2024-5678
- **Versions:** <4.17.21
- **Fix:** 4.17.21
- **Type:** Prototype Pollution
- **Advisory:** https://github.com/advisories/GHSA-yyyy

## Recommendations

1. Run `npm audit fix` to resolve 7 auto-fixable issues
2. Manually update nodemailer to 7.0.11
3. Test thoroughly after lodash upgrade (potential breaking)

## Compliance Status

- OWASP Top 10: 2 related vulnerabilities
- PCI-DSS: No violations detected
- SOC2: Review recommended
```

---

## Integration

### With Routines

Security scans are integrated into PopKit routines:

```
# Nightly (automatic)
/popkit:routine nightly security

# Morning (status check)
/popkit:routine morning --full
```

### Score Impact

| Severity | Points |
|----------|--------|
| Critical | -20 |
| High | -10 |
| Moderate | -5 |
| Low | -2 |

Maximum deduction: 30 points

### With Bug Reporter

Security issues can be reported via bug system:

```
/popkit:bug "Security vulnerability in auth module" --issue
```

---

## Examples

```bash
# Quick scan
/popkit:security

# Preview without creating issues
/popkit:security --dry-run

# Fix what can be auto-fixed
/popkit:security fix

# Full report for compliance
/popkit:security report --md > security-report.md

# Check only critical issues
/popkit:security scan --severity critical
```

---

## Architecture

| Component | Purpose |
|-----------|---------|
| `npm audit --json` | Vulnerability data |
| `gh issue create` | Issue creation |
| `gh issue list` | Duplicate detection |
| `pop-security-scan` skill | Core logic |
| Routine integration | Automated scanning |
