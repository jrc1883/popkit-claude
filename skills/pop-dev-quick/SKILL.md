---
name: dev-quick-mode
description: "Minimal ceremony implementation for small tasks and quick fixes. Use when task is simple, greenfield, or clearly defined. 5-step process: Understand → Find → Fix → Verify → Commit. Invoked via /popkit:dev with orchestrator routing to simple tasks."
---

# Dev Quick Mode

Minimal ceremony implementation for small, well-defined tasks.

## When to Use

**Orchestrator routes here when:**
- Task is simple (< 50 words, clear requirements)
- Intent is "build" with clear scope
- No existing codebase exploration needed
- Single file or few file changes
- Greenfield implementation (no refactoring)

**Explicitly invoked via:**
```
/popkit:dev "add loading spinner"
/popkit:dev "fix timezone bug"
/popkit:dev --mode quick "complex task"  # Force quick even if complex
```

## When NOT to Use

- Complex multi-file refactoring → use full mode
- Unclear requirements → use brainstorm mode
- Existing codebase needs exploration → use full mode
- Architecture decisions needed → use full mode

## The 5-Step Process

### Step 1: Understand
**Goal:** Quick context gathering

```
1. Read the task description
2. Check for existing files mentioned (if any)
3. Identify: What needs to be built/fixed?
4. Note: No deep exploration, just surface-level context
```

**Example:**
```
Task: "Create bouncing balls animation"

Context:
- Files: index.html, balls.js (starter files)
- Need: Canvas animation with physics
- Scope: Single feature, clear requirements
```

### Step 2: Find
**Goal:** Locate relevant code (if modifying existing code)

```
If modifying existing code:
1. Use Grep to find relevant functions/components
2. Use Read to examine key files
3. Identify: Where does the change go?

If greenfield:
1. Identify: What files need to be created?
2. Check: Any dependencies needed?
```

**Example (existing code):**
```
Task: "Fix timezone bug in user profiles"

Found:
- src/utils/formatDate.ts:45 - formatDate function
- src/components/UserProfile.tsx:23 - calls formatDate
```

**Example (greenfield):**
```
Task: "Create bouncing balls animation"

Files needed:
- balls.js (implement Ball class, physics, animation)
- index.html (already exists, may need updates)
```

### Step 3: Fix
**Goal:** Make the change

```
1. Write or Edit the files
2. Keep it simple and focused
3. Follow existing patterns (if modifying)
4. Add minimal comments (only where needed)
```

**Guidelines:**
- Don't over-engineer
- Don't add features beyond scope
- Don't refactor unrelated code
- Do follow existing code style

### Step 4: Verify
**Goal:** Quick validation

```
1. Check: Does it compile/run? (if applicable)
2. Check: Does it meet requirements?
3. Run tests if they exist
4. Quick manual verification if needed
```

**Example:**
```
✓ JavaScript syntax valid (node --check)
✓ All 5 balls render
✓ Physics simulation works
✓ Animation is smooth
```

### Step 5: Commit
**Goal:** Offer to save work

```
Use AskUserQuestion tool with:
- question: "Quick mode complete. Commit these changes?"
- header: "Commit"
- options:
  1. label: "Yes, commit"
     description: "Create commit with descriptive message"
  2. label: "No, keep working"
     description: "Continue without committing"
- multiSelect: false
```

**If user selects "Yes, commit":**
```bash
git add [changed files]
git commit -m "feat: [concise description]

[Details if needed]

🤖 Generated with Claude Code via /popkit:dev quick
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Completion

After commit (or if user skips):

```
Use AskUserQuestion tool with:
- question: "What would you like to do next?"
- header: "Next Action"
- options:
  1. label: "Done for now"
     description: "Exit and save session"
  2. label: "Another quick task"
     description: "Run /popkit:dev quick again"
  3. label: "Review code"
     description: "Invoke code-reviewer agent"
- multiSelect: false
```

## Benchmark Mode

When `POPKIT_BENCHMARK_MODE` environment variable is set:

1. **Auto-approve prompts:**
   - "Commit changes?" → Yes
   - "What would you like to do next?" → Done for now

2. **Skip GitHub operations:**
   - No PR creation
   - No issue updates
   - No remote push

3. **Use benchmark responses:**
   - Check `POPKIT_BENCHMARK_RESPONSES` file
   - Match question headers to responses
   - Auto-select without prompting

## Output Format

```
[QUICK MODE] Creating bouncing balls animation

Step 1: Understand
- Task: Canvas animation with 5 balls, physics, collisions
- Files: balls.js (implement), index.html (starter)
- Scope: Single feature, greenfield

Step 2: Find
- balls.js: Empty starter (// TODO comment)
- index.html: Canvas element ready

Step 3: Fix
Writing balls.js:
- Ball class with position, velocity, mass
- Gravity and damping physics
- Wall collision detection
- Ball-to-ball collision
- Animation loop with requestAnimationFrame

Step 4: Verify
✓ JavaScript syntax valid
✓ 5 balls created with random colors/sizes
✓ Physics simulation working
✓ Smooth 60fps animation

Step 5: Complete
Quick mode finished!
Files changed: balls.js, index.html
Lines added: 135
```

## Error Handling

**If task is too complex for quick mode:**

```
⚠️ This task may be too complex for quick mode.

Detected complexity indicators:
- Multiple architectural decisions needed
- Requires exploration of large codebase
- Unclear requirements

Recommend:
/popkit:dev --mode full "[task]"  # Use full 7-phase workflow
/popkit:dev brainstorm "[task]"   # Clarify requirements first
```

**If stuck or blocked:**

```
⚠️ Quick mode blocked: [reason]

Options:
1. Switch to full mode for deeper analysis
2. Ask user for clarification
3. Report what's blocking and exit
```

## Examples

### Example 1: Greenfield Feature

```
/popkit:dev "create password strength meter"

[QUICK MODE] Creating password strength meter

Step 1: Understand
- Component: Password strength indicator
- Visual: Progress bar with color coding
- Logic: Check length, characters, common passwords

Step 2: Find
- Create: src/components/PasswordStrength.tsx
- Pattern: Follow existing component structure

Step 3: Fix
[Creates component with strength calculation logic]

Step 4: Verify
✓ TypeScript compiles
✓ Weak password → red
✓ Medium password → yellow
✓ Strong password → green

Commit? [Yes/No]
```

### Example 2: Bug Fix

```
/popkit:dev "fix timezone bug in date display"

[QUICK MODE] Fixing timezone bug

Step 1: Understand
- Issue: Dates showing in UTC instead of user timezone
- Impact: User profile, post timestamps

Step 2: Find
Found: src/utils/formatDate.ts:45
- formatDate(date) - missing timezone parameter

Step 3: Fix
Updated formatDate to use user.timezone:
- formatDate(date, user.timezone)
- Update all call sites (3 files)

Step 4: Verify
✓ Displays correct timezone
✓ Existing tests pass

Commit? [Yes/No]
```

## Integration with Orchestrator

The orchestrator (`agent-orchestrator.py`) routes to quick mode when:

```python
analysis = {
    'intent': 'build',
    'complexity': 'simple',  # < 50 words
    'domains': ['frontend'],
    'suggested_agents': []    # No specific agents needed
}

# Routes to: pop-dev-quick skill
```

## Quality Gates

Quick mode is fast but maintains quality:

✓ Syntax validation (if applicable)
✓ Basic functionality testing
✓ Requirements check
✗ Deep code review (use full mode for this)
✗ Comprehensive test coverage (use full mode for this)
✗ Architecture validation (use full mode for this)

## Related Skills

- **pop-feature-dev** - Full 7-phase workflow for complex features
- **pop-brainstorming** - Clarify unclear requirements
- **pop-finish-branch** - Complete work and merge/PR
- **code-reviewer** - Deep code review after quick implementation

---

*Quick mode: Get it done, get it working, get it committed.*
