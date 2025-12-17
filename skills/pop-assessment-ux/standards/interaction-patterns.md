# Interaction Pattern Standards

Standards for consistent, user-friendly interaction patterns.

## Core Principles

### IP-001: AskUserQuestion Usage

Use AskUserQuestion for all user decisions.

**Requirements:**
- Never present options as plain text
- Always use structured choices
- Provide clear descriptions for each option

**Format:**
```
AskUserQuestion tool with:
- question: Clear question ending with "?"
- header: Short label (max 12 chars)
- options: 2-4 choices with labels and descriptions
- multiSelect: false (unless multiple valid)
```

**Example:**
```python
{
  "question": "Which testing framework do you want to use?",
  "header": "Framework",
  "options": [
    {"label": "Jest (Recommended)", "description": "Fast, popular, great for React"},
    {"label": "Vitest", "description": "Vite-native, very fast"},
    {"label": "Mocha", "description": "Flexible, many plugins"}
  ],
  "multiSelect": false
}
```

### IP-002: Input Validation

Validate input before processing.

**Validation Order:**
1. Type checking
2. Format validation
3. Range/constraint checking
4. Business rule validation

**Error on Invalid:**
```
Invalid project name: 'my project'
- Names cannot contain spaces
- Use lowercase letters, numbers, and hyphens
- Example: my-project
```

### IP-003: Default Values

Provide sensible defaults.

**Guidelines:**
- Most common choice as default
- Safe option when uncertain
- Clearly indicate which is default

**Examples:**
```
Output format (default: json):
Branch name (default: main):
Timeout in seconds (default: 30):
```

### IP-004: Progress Indication

Show progress for long operations.

**Methods:**
1. **Status Line Updates**
   ```
   [Analyzing] 45 files processed...
   ```

2. **Phase Indicators**
   ```
   Phase 1/3: Scanning files...
   Phase 2/3: Analyzing patterns...
   Phase 3/3: Generating report...
   ```

3. **Progress Messages**
   ```
   ✓ Configuration loaded
   ✓ Dependencies checked
   → Running analysis...
   ```

### IP-005: Completion Confirmation

Confirm successful operations.

**Format:**
```
✓ Operation completed successfully.
  - 3 files created
  - 1 configuration updated
  - Next: Run 'npm install'
```

### IP-006: Operation Summary

Summarize what was done.

**Include:**
- Actions taken
- Files modified/created
- Settings changed
- Suggested next steps

**Example:**
```
Project created successfully!

Created:
  - package.json
  - src/index.ts
  - tsconfig.json

Modified:
  - .gitignore (added node_modules)

Next steps:
  1. cd my-project
  2. npm install
  3. npm run dev
```

### IP-007: Clear Entry Points

Make it easy to discover starting commands.

**Entry Points:**
- `/popkit:help` - Overview of all commands
- `/popkit:project init` - Common starting point
- `/popkit:next` - Context-aware suggestions

### IP-008: Consistent Workflows

Similar tasks follow similar patterns.

**Standard Flow:**
```
1. init    → Initialize/setup
2. config  → Configure options
3. execute → Run the operation
4. verify  → Check results
```

### IP-009: Escape Routes

Users can cancel or go back.

**Mechanisms:**
- `Ctrl+C` - Cancel current operation
- `--dry-run` - Preview without changes
- Confirmation prompts for destructive ops
- Undo for reversible operations

### IP-010: Guided Workflows

Multi-step tasks are guided.

**Features:**
- Step indicators
- What's next suggestions
- Related command recommendations

**Example:**
```
Step 2 of 4: Configure project settings

Would you like to:
1. Use default settings (Recommended)
2. Customize each setting
3. Load from existing config
```

## Feedback Patterns

### Success Feedback
```
✓ Task completed
  Summary of what was done
  Suggested next steps
```

### Warning Feedback
```
⚠ Operation completed with warnings
  - Warning 1
  - Warning 2
  Consider: [suggestions]
```

### Error Feedback
```
✗ Operation failed
  What went wrong
  How to fix it
  Where to get help
```

## Quality Metrics

| Metric | Target |
|--------|--------|
| AskUserQuestion usage | 100% for decisions |
| Input validation | 100% |
| Progress indication | All ops >2s |
| Completion confirmation | 100% |
| Escape routes | All destructive ops |
