---
description: "quarterly | yearly | stale | duplicates | health | ip-leak [--verbose, --fix]"
---

# /popkit:audit - Project Audit & Review

Perform periodic audits to review project health, find stale issues, detect duplicates, scan for IP leaks, and generate actionable recommendations.

## Usage

```
/popkit:audit <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `quarterly` | Q1/Q2/Q3/Q4 audit report (default) |
| `yearly` | Full year audit |
| `stale` | Find stale issues |
| `duplicates` | Find potential duplicate issues |
| `health` | Overall project health check |
| `ip-leak` | Scan for intellectual property leaks |

---

## Subcommand: quarterly (default)

Generate a quarterly audit report with metrics and recommendations.

```
/popkit:audit                        # Current quarter
/popkit:audit quarterly              # Same as above
/popkit:audit quarterly Q4           # Specific quarter
/popkit:audit quarterly Q4 2024      # Specific quarter and year
/popkit:audit quarterly --verbose    # Include issue-level details
```

### Flags

| Flag | Description |
|------|-------------|
| `--verbose` | Include detailed issue breakdown |
| `--json` | Output as JSON |

### Output

```markdown
# Q4 2024 Audit Report
*Generated: December 10, 2024*

## Summary

| Metric | Q4 2024 | Q3 2024 | Change |
|--------|---------|---------|--------|
| Issues Created | 125 | 89 | +40% |
| Issues Closed | 98 | 72 | +36% |
| Close Rate | 78% | 81% | -3% |
| Avg Time to Close | 5.2 days | 4.8 days | +8% |

## Milestone Progress

| Milestone | Status | Progress |
|-----------|--------|----------|
| v1.0.0 | ✅ Completed | 100% (45/45) |
| v1.1.0 | 🔄 Active | 35% (7/20) |

## Issue Distribution

By Type:
- 🐛 Bug: 32 (26%)
- ✨ Enhancement: 68 (54%)
- 📚 Documentation: 15 (12%)
- ❓ Other: 10 (8%)

By Priority:
- P0 Critical: 2 (2%)
- P1 High: 18 (14%)
- P2 Medium: 65 (52%)
- P3 Low: 40 (32%)

## Stale Issues

Found 7 stale issues (no activity >30 days):
- #42: Old feature request (45 days)
- #67: Superseded by #89 (62 days)
- ...

**Action:** Review and close or update these issues.

## Recommendations

1. **Close Stale Issues** - 7 issues have no activity for 30+ days
2. **Scope Check** - v1.1.0 has 20 issues but only 35% complete
3. **Priority Balance** - Consider promoting more P3 issues or closing them
4. **Documentation** - Only 12% of issues are docs-related, consider improving coverage

## Health Score

**Overall: 🟢 85/100 (Good)**

| Category | Score | Notes |
|----------|-------|-------|
| Velocity | 90 | Strong close rate |
| Staleness | 75 | 7 stale issues |
| Balance | 85 | Good priority mix |
| Documentation | 80 | Adequate coverage |
```

### Quarter Detection

Current quarter is automatically detected:
- Q1: January - March
- Q2: April - June
- Q3: July - September
- Q4: October - December

---

## Subcommand: yearly

Generate a full year audit report.

```
/popkit:audit yearly
/popkit:audit yearly 2024
/popkit:audit yearly --compare 2023
```

### Flags

| Flag | Description |
|------|-------------|
| `--compare` | Compare with previous year |
| `--verbose` | Include quarterly breakdowns |

### Output

```markdown
# 2024 Annual Audit Report
*Generated: December 10, 2024*

## Year in Review

| Metric | 2024 | 2023 | Change |
|--------|------|------|--------|
| Issues Created | 350 | 0 | New project |
| Issues Closed | 280 | 0 | New project |
| Contributors | 1 | 0 | New project |
| Releases | 1 | 0 | v1.0.0 |

## Quarterly Breakdown

| Quarter | Created | Closed | Rate |
|---------|---------|--------|------|
| Q1 | 50 | 35 | 70% |
| Q2 | 75 | 60 | 80% |
| Q3 | 100 | 87 | 87% |
| Q4 | 125 | 98 | 78% |

## Major Accomplishments

1. **v1.0.0 Release** - First stable release (December 2024)
2. **Cloud API Launch** - PopKit Cloud with billing
3. **Power Mode** - Multi-agent orchestration
4. **125+ Issues** - Comprehensive project management

## Areas for Improvement

1. Documentation coverage could be higher
2. Test automation not yet implemented
3. Community engagement (0 external contributors)

## 2025 Planning Recommendations

1. Focus on v1.1.0 completion (Q1)
2. Build community (GitHub Discussions, docs)
3. Implement comprehensive testing
4. Explore multi-model support (v2.0.0)
```

---

## Subcommand: stale

Find and report stale issues.

```
/popkit:audit stale
/popkit:audit stale --days 60           # Custom threshold
/popkit:audit stale --fix               # Auto-apply stale label
/popkit:audit stale --close             # Close stale issues
```

### Flags

| Flag | Description |
|------|-------------|
| `--days` | Days of inactivity to consider stale (default: 30) |
| `--fix` | Apply "stale" label to found issues |
| `--close` | Close stale issues (requires confirmation) |
| `--exclude` | Labels to exclude (comma-separated) |

### Output

```
🕐 Stale Issue Report

Threshold: 30 days of inactivity
Found: 7 stale issues

| # | Title | Last Activity | Age |
|---|-------|---------------|-----|
| 42 | Old feature request | Nov 5 | 35 days |
| 67 | Superseded by #89 | Oct 8 | 63 days |
| 71 | Documentation gap | Nov 1 | 39 days |
| 84 | Nice to have feature | Oct 20 | 51 days |
| 88 | Research: Alt providers | Nov 10 | 30 days |
| 95 | Refactor suggestion | Oct 15 | 56 days |
| 99 | Blocked by external | Nov 3 | 37 days |

Actions:
- Use --fix to apply 'stale' label
- Use --close to close (with confirmation)
- Exempt with 'keep-open' label
```

### Process

1. Fetch all open issues
2. Calculate last activity (comments, events)
3. Filter by threshold
4. Exclude exempt labels (P0, P1, blocked, keep-open)
5. Display or apply fixes

**Execute:**
```bash
gh issue list --state open --json number,title,updatedAt,labels \
  --jq 'map(select(.updatedAt | fromdateiso8601 < (now - 2592000)))'
```

---

## Subcommand: duplicates

Find potential duplicate issues.

```
/popkit:audit duplicates
/popkit:audit duplicates --threshold 0.8   # Similarity threshold
/popkit:audit duplicates --interactive     # Review each potential duplicate
```

### Flags

| Flag | Description |
|------|-------------|
| `--threshold` | Similarity threshold (0.0-1.0, default: 0.7) |
| `--interactive` | Review each duplicate interactively |

### Output

```
🔍 Potential Duplicates Report

Found 3 potential duplicate pairs:

1. **High Confidence (92%)**
   - #45: "Add dark mode support"
   - #78: "Implement dark theme toggle"
   Action: Consider closing #78 as duplicate of #45

2. **Medium Confidence (75%)**
   - #52: "Improve error messages"
   - #89: "Better error handling UX"
   Action: Review - may be related but distinct

3. **Medium Confidence (71%)**
   - #33: "Add keyboard shortcuts"
   - #101: "Vim-style keybindings"
   Action: Review - #101 may be subset of #33
```

### Similarity Detection

Uses multiple signals:
1. **Title similarity** - Levenshtein distance
2. **Body similarity** - TF-IDF or embeddings
3. **Label overlap** - Common labels
4. **Reference patterns** - Same files mentioned

---

## Subcommand: health

Overall project health check.

```
/popkit:audit health
/popkit:audit health --verbose
```

### Output

```
🏥 Project Health Report

Overall Health: 🟢 Good (85/100)

## Metrics

| Category | Score | Status | Notes |
|----------|-------|--------|-------|
| Issue Velocity | 90/100 | 🟢 | Closing 2.3/day |
| Staleness | 75/100 | 🟡 | 7 stale issues |
| Documentation | 80/100 | 🟢 | README, CLAUDE.md current |
| Test Coverage | 60/100 | 🟡 | Limited automated tests |
| Code Quality | 85/100 | 🟢 | TypeScript, linting |
| Security | 90/100 | 🟢 | No known vulnerabilities |

## Recent Activity

- Last commit: 2 hours ago
- Last release: v1.0.0 (1 day ago)
- Active milestone: v1.1.0 (35% complete)

## Alerts

⚠️ **Test Coverage** - Consider adding automated tests
⚠️ **Stale Issues** - 7 issues need attention
ℹ️ **Milestone** - v1.1.0 may miss due date at current velocity

## Recommendations

1. Add unit tests for critical paths (hooks, cloud API)
2. Review and close stale issues
3. Consider scope reduction for v1.1.0
4. Enable Dependabot for security alerts
```

---

## Scheduling Audits

### Automated Reminders

Create a skill to remind about audits:

```python
# In pop-next-action skill
def check_audit_due():
    last_audit = get_last_audit_date()
    days_since = (now - last_audit).days

    if days_since > 90:
        return "Quarterly audit overdue - run /popkit:audit quarterly"
    return None
```

### GitHub Action (Optional)

```yaml
# .github/workflows/quarterly-audit.yml
name: Quarterly Audit Reminder
on:
  schedule:
    - cron: '0 0 1 1,4,7,10 *'  # First of each quarter

jobs:
  remind:
    runs-on: ubuntu-latest
    steps:
      - name: Create audit reminder issue
        uses: actions/github-script@v7
        with:
          script: |
            const quarter = Math.ceil((new Date().getMonth() + 1) / 3);
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Q${quarter} ${new Date().getFullYear()} Audit Due`,
              body: 'Time for quarterly audit!\n\nRun: `/popkit:audit quarterly`',
              labels: ['chore']
            });
```

---

## Examples

```bash
# Run quarterly audit
/popkit:audit

# Check for stale issues
/popkit:audit stale

# Find duplicates with lower threshold
/popkit:audit duplicates --threshold 0.6

# Full year review
/popkit:audit yearly 2024

# Quick health check
/popkit:audit health

# Fix stale issues automatically
/popkit:audit stale --fix

# Scan for IP leaks before publishing
/popkit:audit ip-leak
/popkit:audit ip-leak --deep
```

---

## Subcommand: ip-leak

Scan for intellectual property that should NOT appear in the public repository.

```
/popkit:audit ip-leak                 # Scan plugin directory
/popkit:audit ip-leak --deep          # Include git history scan
/popkit:audit ip-leak --path <dir>    # Scan specific directory
/popkit:audit ip-leak --json          # Output as JSON
/popkit:audit ip-leak --pre-publish   # Pre-publish validation mode
```

### Purpose

PopKit uses a **split-repo model**:
- **Private** (`jrc1883/popkit`): Full monorepo with cloud, billing, proprietary code
- **Public** (`jrc1883/popkit-claude`): Plugin only (declarative content)

This command ensures we don't accidentally leak private content when publishing.

### Flags

| Flag | Description |
|------|-------------|
| `--deep` | Include git history scan (slower, more thorough) |
| `--path <dir>` | Scan specific directory (default: packages/plugin) |
| `--json` | Output findings as JSON |
| `--pre-publish` | Pre-publish mode (blocks on critical/high issues) |

### What Gets Scanned

#### Critical (Blocks Publish)

| Pattern | Description |
|---------|-------------|
| `packages/cloud/` | Cloud API implementation |
| `packages/cloud-billing/` | Billing/payment code |
| `STRIPE_*` secrets | Stripe API keys |
| `UPSTASH_*_TOKEN` | Redis credentials |
| Hardcoded API keys | API keys in code |
| Bearer tokens | Hardcoded auth tokens |

#### High Priority

| Pattern | Description |
|---------|-------------|
| `PROPRIETARY` markers | Explicit proprietary tags |
| `# SECRET:` comments | Secret markers |
| `do-not-publish` | Explicit markers |

#### Medium Priority

| Pattern | Description |
|---------|-------------|
| `internal-only` | Internal content markers |
| Premium detection logic | `is_premium`, `check_premium` |
| Production API URLs | Cloud API endpoints |

#### Low Priority

| Pattern | Description |
|---------|-------------|
| Private repo refs | References to `jrc1883/popkit` |

### Output

```
# IP Leak Scan Report

**Found 3 potential issues**
- Critical: 0
- High: 1
- Medium: 2
- Low: 0

## High Priority Issues

- **hooks/utils/some_file.py:45** - `PROPRIETARY`
  Proprietary content marker

## Medium Priority Issues

- **skills/pop-premium/SKILL.md:12** - `is_premium`
  Premium feature detection logic

- **agents/config.json:156** - `https://api.popkit.cloud`
  Production API URL
```

### Pre-Publish Mode

When used with `--pre-publish`:
- **Critical or High findings**: Returns exit code 1 (blocks publish)
- **Medium or Low findings**: Returns exit code 0 (warns but allows)
- **No findings**: Returns exit code 0 (safe to publish)

This is automatically invoked by `/popkit:git publish`.

### Deep Scan

The `--deep` flag scans git history for leaked secrets:
- Checks added files in the last 100 commits
- Detects secrets that were committed and later removed
- Slower but more thorough

```
/popkit:audit ip-leak --deep
```

### Integration Points

1. **Pre-Publish Hook**: Automatically runs before `/popkit:git publish`
2. **Nightly Routine**: Part of `/popkit:routine nightly` checks
3. **CI/CD**: GitHub Action on public repo validates on every push

### Allowed Exceptions

Some files are allowed to contain patterns for documentation:
- `ip_protection.py` - The scanner itself
- `CLAUDE.md` - Documents what's private
- `audit.md` - Documents the feature
- Test files - For testing the scanner

### Execute

```bash
# Run from command line
python packages/plugin/hooks/utils/ip_protection.py packages/plugin/

# With deep scan
python packages/plugin/hooks/utils/ip_protection.py packages/plugin/ --deep

# Pre-publish mode
python packages/plugin/hooks/utils/ip_protection.py packages/plugin/ --pre-publish
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| GitHub API | Issue, milestone, event fetching |
| Embeddings | Duplicate detection (semantic) |
| Analytics | Velocity, trends calculation |
| Reports | Markdown formatting |
| IP Scanner | `hooks/utils/ip_protection.py` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:milestone` | Milestone-specific management |
| `/popkit:issue` | Individual issue management |
| `/popkit:stats` | Quick project statistics |
| `/popkit:git publish` | Uses ip-leak scan before publishing |
| `/popkit:routine nightly` | Includes ip-leak check |
