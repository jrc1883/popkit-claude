---
name: debugging-report
description: Root cause analysis and debugging session findings
used_by:
  - bug-whisperer
  - /popkit:debug
---

# Debugging Report Style

## Purpose

Document the complete debugging journey from symptoms to root cause to fix. Enables knowledge transfer and prevents future regressions.

## Format

```markdown
## Debugging Report: [Issue Title]

**Status:** [Identified|Fixed|Partially Fixed|Unresolved]
**Severity:** [Critical|High|Medium|Low]
**Time Spent:** [duration]

---

### Symptom

**What was observed:**
<Clear description of the bug behavior>

**Error message (if any):**
```
[exact error text]
```

**Steps to reproduce:**
1. [Step 1]
2. [Step 2]
3. [Observe: behavior]

**Expected behavior:**
<What should have happened>

---

### Investigation

#### Hypothesis 1: [Initial theory]
**Test:** [How it was tested]
**Result:** [Confirmed|Rejected|Partial]
**Evidence:** [What was found]

#### Hypothesis 2: [Second theory]
**Test:** [How it was tested]
**Result:** [Confirmed|Rejected|Partial]
**Evidence:** [What was found]

---

### Root Cause

**Location:** `path/to/file.ts:line`

**What went wrong:**
<Technical explanation of the bug>

**Why it happened:**
<Context on how this bug was introduced>

**Code causing the issue:**
```typescript
// path/to/file.ts:45-50
[problematic code]
```

---

### Fix

**Solution:**
<Description of the fix approach>

**Changes made:**
```typescript
// path/to/file.ts:45-50
[fixed code]
```

**Verification:**
```bash
# Command to verify fix
[test command]
```

**Result:** [PASS|FAIL]

---

### Prevention

**Regression test added:**
- [ ] Unit test in `tests/path/file.test.ts`
- [ ] Integration test (if applicable)

**Code quality improvements:**
- [ ] Added input validation
- [ ] Added error handling
- [ ] Added type safety

**Documentation updates:**
- [ ] Updated comments
- [ ] Updated API docs

---

### Related

- **Issue:** #[number]
- **PR:** #[number]
- **Similar bugs:** #[numbers]
```

## Severity Definitions

| Level | Impact | Response Time |
|-------|--------|---------------|
| Critical | System down, data loss risk | Immediate |
| High | Major feature broken | Same day |
| Medium | Feature degraded | This sprint |
| Low | Minor inconvenience | Backlog |

## Investigation Patterns

### The 5 Whys

```markdown
#### Root Cause Analysis (5 Whys)

1. **Why did the error occur?**
   → [immediate cause]

2. **Why did [immediate cause] happen?**
   → [deeper cause]

3. **Why did [deeper cause] happen?**
   → [even deeper]

4. **Why did [even deeper] happen?**
   → [systemic issue]

5. **Why did [systemic issue] exist?**
   → [root cause]
```

### Binary Search

```markdown
#### Binary Search Investigation

- Last known good: commit `abc123` (2 days ago)
- First known bad: commit `def456` (today)
- Bisect result: Bug introduced in `xyz789`
- Specific change: [description]
```

### Trace Analysis

```markdown
#### Execution Trace

1. Entry: `src/api/handler.ts:10` - Request received
2. Call: `src/services/user.ts:45` - User lookup
3. Call: `src/db/queries.ts:30` - Database query
4. **FAIL**: `src/db/queries.ts:35` - Null pointer
5. Propagate: Error bubbles up without handling
```

## Example: Null Pointer Bug

```markdown
## Debugging Report: Profile page crashes for new users

**Status:** Fixed
**Severity:** High
**Time Spent:** 45 minutes

---

### Symptom

**What was observed:**
New users see a blank page when accessing /profile. Console shows "Cannot read property 'name' of undefined".

**Error message:**
```
TypeError: Cannot read property 'name' of undefined
    at ProfileHeader (src/components/ProfileHeader.tsx:15)
    at renderWithHooks (react-dom.js:1234)
```

**Steps to reproduce:**
1. Create a new account
2. Navigate to /profile before adding profile data
3. Observe: Blank page with console error

**Expected behavior:**
Show profile page with placeholder data for missing fields.

---

### Investigation

#### Hypothesis 1: User object not loaded
**Test:** Added console.log before render
**Result:** Rejected - User object exists
**Evidence:** `console.log(user)` shows `{ id: 123, email: "test@test.com" }`

#### Hypothesis 2: Profile relation not included
**Test:** Checked Prisma include statement
**Result:** Confirmed
**Evidence:** Query uses `include: { profile: true }` but profile can be null for new users

---

### Root Cause

**Location:** `src/components/ProfileHeader.tsx:15`

**What went wrong:**
Component assumes `user.profile` always exists, but it's null for new users who haven't completed onboarding.

**Why it happened:**
Original implementation only tested with seeded users who all had profiles. Edge case of new users was missed.

**Code causing the issue:**
```typescript
// src/components/ProfileHeader.tsx:15
const { name, avatar } = user.profile; // profile is null!
```

---

### Fix

**Solution:**
Add null check with fallback values.

**Changes made:**
```typescript
// src/components/ProfileHeader.tsx:15-18
const name = user.profile?.name ?? user.email.split('@')[0];
const avatar = user.profile?.avatar ?? '/default-avatar.png';
```

**Verification:**
```bash
npm test -- ProfileHeader.test.tsx
```

**Result:** PASS (5 tests, including new edge case)

---

### Prevention

**Regression test added:**
- [x] Unit test: "renders correctly for user without profile"
- [x] Unit test: "shows email prefix when name missing"

**Code quality improvements:**
- [x] Added TypeScript strict null checks to component
- [x] Added PropTypes for profile shape

**Documentation updates:**
- [x] Added comment explaining profile can be null

---

### Related

- **Issue:** #67
- **PR:** #68
- **Similar bugs:** #45 (same pattern in settings page)
```

## Integration

### In Agent Definition

```yaml
---
name: bug-whisperer
output_style: debugging-report
---
```

### Workflow

1. Bug reported → bug-whisperer activated
2. Investigation using 5 Whys, binary search, or trace
3. Root cause identified
4. Fix implemented
5. Regression test added
6. Debugging report generated
7. Report attached to issue/PR
