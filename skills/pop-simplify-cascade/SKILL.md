---
name: simplification-cascades
description: "Use when complexity is spiraling, implementing the same concept multiple ways, or accumulating special cases - finds one insight that eliminates multiple components: 'if this is true, we don't need X, Y, or Z'. Do NOT use when code is already simple or when complexity is genuinely necessary - premature simplification can remove important edge case handling."
---

# Simplification Cascades

## Overview

When complexity spirals, stop adding code. Look for the ONE insight that eliminates multiple components at once.

**Core principle:** The best fix often isn't more code - it's realizing you don't need code you thought you did.

## When to Use

**Red flags triggering this skill:**
- Implementing the same concept multiple ways
- Accumulating special cases
- "While I'm here" improvements snowballing
- Each fix creates a new problem
- Code feels fragile and interconnected
- Requirements keep revealing new edge cases

## The Simplification Cascade

### Step 1: Stop Adding Code

When you notice complexity spiraling:
- Stop immediately
- Don't add "one more fix"
- Don't bandaid the current approach

### Step 2: List All Components

Write down everything the feature currently needs:
- Data models
- Functions/methods
- State variables
- Configuration options
- Special cases
- Edge case handlers

### Step 3: Ask the Key Question

For each component, ask: **"What assumption makes this necessary?"**

Examples:
- "We need a cache because loading is slow" -> What if we changed storage format?
- "We need validation because input is unreliable" -> What if we controlled the source?
- "We need retry logic because the API fails" -> What if we called a different API?

### Step 4: Find the Insight

Look for ONE change that eliminates MULTIPLE components:

```
If [X is true], we don't need:
- Component A
- Component B
- Component C
- Edge case handler D
```

The best insights:
- Challenge assumptions you didn't know you had
- Reframe the problem entirely
- Make "obvious" requirements no longer apply

### Step 5: Validate the Cascade

Before implementing:
- Check the insight doesn't break other features
- Verify it actually removes complexity, not just shifts it
- Ensure you're not trading one problem for a worse one

### Step 6: Implement Removal First

Counter-intuitive order:
1. Remove the components made unnecessary
2. Then implement the insight
3. Not vice versa

This ensures you actually get the simplification.

## Examples

### Example 1: State Synchronization

**Before (complex):**
- Local state
- Server state
- Sync engine
- Conflict resolution
- Offline queue
- Retry logic

**Insight:** "If we make the server the single source of truth and accept brief loading states, we don't need..."

**After (simple):**
- Server state
- Loading indicator

Removed: 5 components, ~500 lines

### Example 2: Configuration System

**Before (complex):**
- Config file parser
- Environment variable loader
- Default values
- Validation schema
- Migration logic
- Override system

**Insight:** "If we just use TypeScript constants and rebuild on change, we don't need..."

**After (simple):**
- TypeScript constants file

Removed: 5 components, ~300 lines

### Example 3: Permission System

**Before (complex):**
- Role definitions
- Permission matrices
- Inheritance logic
- Context-based rules
- Caching layer
- Override mechanism

**Insight:** "If users are either admin or not-admin for our use case, we don't need..."

**After (simple):**
- Single `isAdmin` boolean

Removed: 5 components, ~400 lines

## Anti-Patterns

**Don't confuse simplification with:**

| Wrong Approach | Why It Fails |
|---------------|--------------|
| Hiding complexity in abstractions | Complexity still exists, just hidden |
| Moving code to a library | Still maintaining it |
| "It's simple if you understand it" | Complexity for newcomers matters |
| Deferring problems | Technical debt grows |

**True simplification:**
- Actually removes code
- Removes entire concepts, not just lines
- Future developers won't need to understand removed parts

## The Cascade Test

After finding an insight, apply this test:

```
If I explain this feature to a new developer:
- Before: Need to explain X, Y, Z, and their interactions
- After: Just explain A

If "after" isn't dramatically simpler, keep looking.
```

## When Simplification Isn't Possible

Sometimes complexity is inherent:
- External API requirements
- Regulatory compliance
- Backwards compatibility
- Performance requirements

In these cases:
1. Document WHY complexity is necessary
2. Isolate complexity in one place
3. Create clear boundaries
4. Don't fight inherent complexity

## Key Questions

When stuck in complexity:

1. **What assumption am I not questioning?**
2. **What if I didn't need to handle this case?**
3. **What would a 10x simpler version look like?**
4. **What would I tell a new team member to not worry about?**
5. **If I started over, what wouldn't I build?**

## Remember

The goal isn't less code - it's fewer concepts.

100 lines of straightforward code > 20 lines of clever code
Removing a feature > Simplifying a feature
Saying "no" > Building a workaround
