---
name: security-audit-report
description: Security vulnerability assessment with severity ratings and remediation guidance
used_by:
  - security-auditor
  - /popkit:security-scan
---

# Security Audit Report Style

## Purpose

Document security vulnerabilities, assess risks, and provide actionable remediation guidance. Enables tracking and verification of security fixes.

## Format

```markdown
## Security Audit Report: [Project/Scope]

**Audit Date:** [YYYY-MM-DD]
**Auditor:** security-auditor
**Scope:** [Full codebase|Module|Feature|PR]

---

### Executive Summary

**Security Score:** [0-100] [emoji indicator]

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical | [n] | [Blocked until fixed] |
| 🟠 High | [n] | [Fix this sprint] |
| 🟡 Medium | [n] | [Schedule fix] |
| 🟢 Low | [n] | [Monitor] |
| ℹ️ Info | [n] | [Best practice notes] |

**Recommendation:** [Pass|Pass with conditions|Fail - remediation required]

---

### Critical Vulnerabilities

#### VULN-001: [Vulnerability Title]

**Severity:** 🔴 Critical
**CVSS Score:** [0.0-10.0]
**CWE:** [CWE-XXX] [Name]
**OWASP:** [Category]

**Location:**
```
File: src/path/to/file.ts
Lines: 45-52
Function: processUserInput()
```

**Description:**
[Clear explanation of the vulnerability]

**Proof of Concept:**
```typescript
// Vulnerable code
const query = `SELECT * FROM users WHERE id = ${userId}`;
```

**Impact:**
- [What an attacker could do]
- [Data at risk]
- [Systems affected]

**Remediation:**
```typescript
// Fixed code
const query = 'SELECT * FROM users WHERE id = $1';
const result = await db.query(query, [userId]);
```

**Verification:**
```bash
# Command to verify fix
npm run test:security
```

**References:**
- [OWASP Link]
- [CWE Link]

---

### High Severity Vulnerabilities

#### VULN-002: [Title]
[Same structure as above]

---

### Medium Severity Vulnerabilities

#### VULN-003: [Title]
[Abbreviated structure]

---

### Low Severity Issues

| ID | Issue | Location | Recommendation |
|----|-------|----------|----------------|
| VULN-004 | [title] | `file:line` | [fix] |
| VULN-005 | [title] | `file:line` | [fix] |

---

### Informational Notes

| Topic | Observation | Recommendation |
|-------|-------------|----------------|
| [Headers] | Missing X-Frame-Options | Add security headers |
| [Logging] | Passwords in debug logs | Sanitize sensitive data |

---

### Security Checklist

#### Authentication
- [ ] Passwords hashed with bcrypt/argon2
- [ ] Session tokens are secure random
- [ ] Session expiry implemented
- [ ] MFA available for sensitive operations

#### Authorization
- [ ] Role-based access control
- [ ] Resource ownership verified
- [ ] Admin functions protected
- [ ] API endpoints authorized

#### Input Validation
- [ ] All user input validated
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] CSRF tokens used

#### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] TLS for data in transit
- [ ] PII handling compliant
- [ ] Secrets not in code

#### Dependencies
- [ ] No known vulnerabilities
- [ ] Dependencies up to date
- [ ] Lock file present
- [ ] Audit ran recently

---

### Dependency Vulnerabilities

#### npm audit Summary

| Severity | Count | Packages |
|----------|-------|----------|
| Critical | [n] | [list] |
| High | [n] | [list] |
| Moderate | [n] | [list] |

#### Actionable Fixes

```bash
# Auto-fixable
npm audit fix

# Manual intervention required
npm install package@version  # [vulnerability details]
```

---

### Compliance Check

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | [Pass/Fail] | [details] |
| PCI-DSS | [N/A/Pass/Fail] | [details] |
| GDPR | [N/A/Pass/Fail] | [details] |
| SOC 2 | [N/A/Pass/Fail] | [details] |

---

### Remediation Priority

#### Immediate (Before Deploy)
1. [ ] VULN-001: [title] - [owner]
2. [ ] VULN-002: [title] - [owner]

#### This Sprint
1. [ ] VULN-003: [title]
2. [ ] VULN-004: [title]

#### Backlog
1. [ ] VULN-005: [title]

---

### Verification Plan

After remediation:

1. **Automated Scans**
   ```bash
   npm audit
   npm run test:security
   ```

2. **Manual Verification**
   - [ ] SQL injection test
   - [ ] XSS test
   - [ ] Authentication bypass test

3. **Re-audit Required:** [Yes/No]

---

**Audit Confidence:** [0-100]
**Next Audit Recommended:** [date or trigger]
```

## Severity Definitions

| Level | CVSS | Description | Response |
|-------|------|-------------|----------|
| 🔴 Critical | 9.0-10.0 | Immediate exploitation possible, severe impact | Block deploy, fix immediately |
| 🟠 High | 7.0-8.9 | Likely exploitable, significant impact | Fix before next release |
| 🟡 Medium | 4.0-6.9 | Requires conditions, moderate impact | Fix this sprint |
| 🟢 Low | 0.1-3.9 | Difficult to exploit, minimal impact | Backlog |
| ℹ️ Info | N/A | Best practice recommendation | Consider |

## Common Vulnerability Categories

### OWASP Top 10 (2021)

| ID | Category | Common Issues |
|----|----------|---------------|
| A01 | Broken Access Control | Missing auth, IDOR, privilege escalation |
| A02 | Cryptographic Failures | Weak encryption, exposed secrets |
| A03 | Injection | SQL, NoSQL, OS command, LDAP |
| A04 | Insecure Design | Business logic flaws |
| A05 | Security Misconfiguration | Default creds, verbose errors |
| A06 | Vulnerable Components | Outdated dependencies |
| A07 | Auth Failures | Weak passwords, session issues |
| A08 | Data Integrity Failures | Insecure deserialization |
| A09 | Logging Failures | Missing audit trails |
| A10 | SSRF | Server-side request forgery |

## Example: API Security Audit

```markdown
## Security Audit Report: User API Endpoints

**Audit Date:** 2025-01-28
**Auditor:** security-auditor
**Scope:** src/api/users/

---

### Executive Summary

**Security Score:** 65/100 🟠

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical | 1 | Blocked until fixed |
| 🟠 High | 2 | Fix this sprint |
| 🟡 Medium | 3 | Schedule fix |
| 🟢 Low | 2 | Monitor |

**Recommendation:** Fail - remediation required before deploy

---

### Critical Vulnerabilities

#### VULN-001: SQL Injection in User Search

**Severity:** 🔴 Critical
**CVSS Score:** 9.8
**CWE:** CWE-89 SQL Injection
**OWASP:** A03:2021 Injection

**Location:**
```
File: src/api/users/search.ts
Lines: 23-25
Function: searchUsers()
```

**Description:**
User-supplied search term is directly concatenated into SQL query without sanitization, allowing arbitrary SQL execution.

**Proof of Concept:**
```typescript
// Vulnerable code
const query = `SELECT * FROM users WHERE name LIKE '%${searchTerm}%'`;
// Attack: searchTerm = "'; DROP TABLE users; --"
```

**Impact:**
- Full database access
- Data exfiltration
- Data destruction
- Authentication bypass

**Remediation:**
```typescript
// Fixed code
const query = 'SELECT * FROM users WHERE name LIKE $1';
const result = await db.query(query, [`%${searchTerm}%`]);
```

**Verification:**
```bash
# Run security tests
npm run test:injection
```

---

### High Severity Vulnerabilities

#### VULN-002: Missing Rate Limiting on Login

**Severity:** 🟠 High
**CWE:** CWE-307 Brute Force
**Location:** `src/api/auth/login.ts`

**Description:**
No rate limiting on login endpoint allows brute force attacks.

**Remediation:**
Add rate limiting middleware (e.g., express-rate-limit).

---

### Security Checklist

#### Authentication
- [x] Passwords hashed with bcrypt
- [x] Session tokens are secure random
- [x] Session expiry implemented
- [ ] MFA available ⚠️

#### Input Validation
- [ ] All user input validated ❌
- [ ] SQL injection prevented ❌
- [x] XSS prevented (React escaping)
- [x] CSRF tokens used

---

**Audit Confidence:** 90
**Next Audit Recommended:** After remediation complete
```

## Integration

### In Agent Definition

```yaml
---
name: security-auditor
output_style: security-audit-report
---
```

### Workflow Integration

1. Security audit triggered (PR, schedule, or manual)
2. security-auditor agent activated
3. Scans code, dependencies, configuration
4. Generates security-audit-report
5. Blocks merge if critical issues found
6. Creates issues for each vulnerability
7. Tracks remediation progress
