---
name: pop-validation-engine
description: "Reusable validation pattern for scanning, comparing, reporting, and fixing plugin integrity issues. Implements the Scan-Compare-Report-Apply workflow for checking agents, routing, output styles, and hooks against their schemas. Use when validating plugin structure, debugging configuration issues, or building custom validators. Do NOT use for runtime validation or user input checking - this is specifically for popkit plugin component integrity."
---

# Validation Engine Skill

## Purpose

The validation engine provides a reusable pattern for validating any component of the popkit plugin. It follows the **Scan → Compare → Report → Recommend/Apply** workflow.

## When to Use

Invoke this skill when:
- Validating plugin structure after changes
- Checking agent frontmatter completeness
- Verifying routing keyword coverage
- Testing output style schema compliance
- Running pre-commit validation checks
- Debugging configuration issues

## The Pattern

### 1. Scan Phase

Collect current state from the filesystem:

```typescript
interface ScanResult {
  component: string;
  files: FileInfo[];
  metadata: Record<string, any>;
}

interface FileInfo {
  path: string;
  exists: boolean;
  content?: string;
  frontmatter?: Record<string, any>;
  schema?: object;
}
```

**Implementation:**
- Use Glob to find files matching patterns
- Use Read to extract content and frontmatter
- Parse YAML frontmatter from markdown files
- Parse JSON from configuration files

### 2. Compare Phase

Check current state against expected schema:

```typescript
interface CompareResult {
  file: string;
  checks: Check[];
}

interface Check {
  name: string;
  passed: boolean;
  expected: any;
  actual: any;
  severity: 'error' | 'warning' | 'info';
}
```

**Common Checks:**
- Required fields present
- Field values match allowed enums
- References resolve to existing files
- Syntax is valid (JSON, YAML, Python)
- Naming conventions followed

### 3. Report Phase

Generate structured findings:

```typescript
interface ValidationReport {
  timestamp: string;
  summary: {
    total_files: number;
    passed: number;
    warnings: number;
    errors: number;
  };
  issues: Issue[];
}

interface Issue {
  id: string;
  severity: 'error' | 'warning' | 'info';
  component: string;
  file: string;
  line?: number;
  message: string;
  suggestion?: string;
  autoFixable: boolean;
}
```

**Report Format:**
- Executive summary with counts
- Issues grouped by severity
- Clear actionable messages
- Auto-fix availability noted

### 4. Recommend/Apply Phase

Suggest or apply fixes:

```typescript
interface Fix {
  issue_id: string;
  action: 'add' | 'modify' | 'delete';
  file: string;
  change: string;
  safe: boolean;
}
```

**Safe Auto-Fixes:**
- Adding missing optional fields with defaults
- Creating template files from schemas
- Registering items in configuration
- Fixing whitespace/formatting

**Requires Human Decision:**
- Changing behavior/logic
- Removing content
- Modifying prompts or instructions
- Changing configuration values

## Component Validators

### Agent Validator

```typescript
const agentSchema = {
  required: ['name', 'description', 'tools'],
  optional: ['output_style', 'color'],
  checks: [
    'name matches filename',
    'tools are valid Claude tools',
    'output_style references existing style',
    'agent registered in config.json'
  ]
};
```

### Routing Validator

```typescript
const routingSchema = {
  required: ['keywords', 'filePatterns'],
  checks: [
    'keyword agents exist',
    'file patterns are valid globs',
    'no duplicate keywords',
    'all agents have routing paths'
  ]
};
```

### Output Style Validator

```typescript
const outputStyleSchema = {
  required: ['name', 'description'],
  optional: ['used_by'],
  checks: [
    'schema file exists if referenced',
    'example section present',
    'TypeScript interface matches schema'
  ]
};
```

### Hook Validator

```typescript
const hookSchema = {
  checks: [
    'file exists at hooks.json path',
    'Python syntax valid',
    'main() function present',
    'JSON stdin/stdout protocol used',
    'error handling with sys.exit(0)'
  ]
};
```

## Usage Example

```markdown
## Running Validation

1. Invoke this skill
2. Specify components to validate:
   - "all" for complete validation
   - "agents" for agent files only
   - "routing" for config.json
   - "hooks" for hook scripts

3. Review the report
4. Decide on fixes:
   - "apply safe" for auto-fixable issues
   - "apply all" with caution
   - Manual fixes for complex issues

## Example Session

User: Run validation on agents
Claude: [Uses Glob to find agent files]
Claude: [Uses Read to check frontmatter]
Claude: [Compares against schema]
Claude:

### Agent Validation Report

**Files Checked:** 29
**Passed:** 27
**Issues:** 2

#### Issues Found

1. **WARNING** `agents/tier-2-on-demand/new-agent.md`
   - Missing `output_style` field
   - Suggestion: Add `output_style: agent-handoff`
   - Auto-fixable: Yes

2. **ERROR** `agents/tier-2-on-demand/test-agent.md`
   - Agent not registered in config.json
   - Suggestion: Add to tier-2-on-demand array
   - Auto-fixable: Yes

Would you like me to apply the safe fixes?
```

## Integration Points

This skill integrates with:
- `/popkit:sync` command (invokes this skill)
- `/popkit:plugin-test` (uses validators)
- `pre-commit` hooks (optional validation)
- GitHub Actions (CI validation)

## Best Practices

1. **Run after changes**: Validate after modifying agents, routing, or hooks
2. **Before commits**: Run sync to catch issues early
3. **In CI**: Include validation in pull request checks
4. **Incremental fixes**: Apply safe fixes first, review complex issues

## Error Handling

If validation encounters errors:
1. Log the error with context
2. Continue checking other components
3. Include error in final report
4. Don't block on non-critical failures
