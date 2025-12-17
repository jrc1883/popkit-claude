---
name: implementation-plan
description: Task-based implementation plan format
---

# Implementation Plan Style

## Format

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use executing-plans skill to implement.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Estimated Tasks:** [N tasks]

---

## Task 1: [Component Name]

**Files:**
- Create: `exact/path/to/file.ts`
- Modify: `existing/path/to/file.ts:50-75`
- Test: `tests/path/to/file.test.ts`

**Step 1: Write the failing test**

```typescript
describe('ComponentName', () => {
  it('should do specific thing', () => {
    const result = doThing(input);
    expect(result).toBe(expected);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- file.test.ts`
Expected: FAIL with "doThing is not defined"

**Step 3: Write minimal implementation**

```typescript
export function doThing(input: InputType): OutputType {
  return expected;
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- file.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/path/file.ts tests/path/file.test.ts
git commit -m "feat(component): add specific feature"
```

---

## Task 2: [Next Component]
...

---

## Verification

After all tasks complete:

```bash
# Run full test suite
npm test

# Run type check
npm run typecheck

# Run lint
npm run lint

# Build
npm run build
```

## Rollback Plan

If issues arise:
1. `git log` to find last good commit
2. `git revert HEAD~N` where N is number of commits
3. Or `git reset --soft HEAD~N` to undo but keep changes
```

## Principles

### Bite-Sized Tasks
Each step should take 2-5 minutes:
- Write test (one step)
- Run test (one step)
- Implement (one step)
- Verify (one step)
- Commit (one step)

### Complete Information
- Exact file paths
- Complete code (not "add validation")
- Exact commands
- Expected output

### TDD Always
- Test first
- Watch it fail
- Implement minimal
- Watch it pass

### Frequent Commits
- After each task
- Meaningful messages
- Atomic changes

## Example

```markdown
# User Authentication Implementation Plan

> **For Claude:** Use executing-plans skill to implement.

**Goal:** Add email/password authentication with session management

**Architecture:** NextAuth.js with Supabase adapter, JWT sessions,
middleware for protected routes

**Tech Stack:** Next.js 14, NextAuth.js, Supabase, TypeScript

**Estimated Tasks:** 6 tasks

---

## Task 1: Setup NextAuth Configuration

**Files:**
- Create: `src/lib/auth.ts`
- Create: `src/app/api/auth/[...nextauth]/route.ts`
- Modify: `package.json` (add dependencies)

**Step 1: Install dependencies**

Run: `npm install next-auth @auth/supabase-adapter`
Expected: Dependencies added to package.json

**Step 2: Create auth configuration**

```typescript
// src/lib/auth.ts
import { SupabaseAdapter } from "@auth/supabase-adapter";
import NextAuth from "next-auth";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: SupabaseAdapter({
    url: process.env.SUPABASE_URL!,
    secret: process.env.SUPABASE_SERVICE_KEY!,
  }),
  providers: [],
});
```

**Step 3: Create API route**
...

---

## Task 2: Add Credentials Provider
...
```
