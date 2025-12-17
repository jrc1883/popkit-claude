# Error Message Standards

Standards for creating helpful, actionable error messages.

## Core Principles

### EM-001: Clear Problem Description

Errors must clearly state what went wrong.

**Structure:**
```
[What happened] [Where it happened] [With what context]
```

**Examples:**
| Good | Bad |
|------|-----|
| File 'config.json' not found in /project | File not found |
| Invalid JSON syntax at line 42, column 5 | Parse error |
| Connection to database timed out after 30s | Connection failed |

### EM-002: Avoid Technical Jargon

Use plain language that users understand.

**Translations:**
| Technical | User-Friendly |
|-----------|---------------|
| ENOENT | File not found |
| EACCES | Permission denied |
| ECONNREFUSED | Cannot connect to server |
| null reference | Value is missing |
| stack overflow | Operation too complex |

**When Technical Details Help:**
```
# Include both
Cannot connect to database.
Technical: ECONNREFUSED 127.0.0.1:5432
```

### EM-003: Include Context

Provide relevant context for the error.

**Context Elements:**
- File path where error occurred
- Line number (for syntax errors)
- Value that caused the error
- Expected vs actual

**Example:**
```
Invalid configuration value.
  File: config.json
  Field: timeout
  Value: "fast"
  Expected: number (in milliseconds)
```

### EM-004: Suggest Solution

Tell users how to fix the problem.

**Pattern:**
```
[Problem]. [Solution].
```

**Examples:**
```
# Good
Missing API key. Set POPKIT_API_KEY in your environment.

# Bad
Missing API key.
```

### EM-005: Provide Next Steps

Tell users what to do next.

**Patterns:**
```
# Command suggestion
Run 'npm install' to install missing dependencies.

# Action list
To fix this:
1. Check your network connection
2. Verify the API endpoint is correct
3. Try again with --verbose for more details

# Documentation reference
See https://docs.example.com/auth for setup guide.
```

### EM-006: Include Documentation Link

Link to relevant docs for complex errors.

**Format:**
```
[Error message]
For more information, see: [URL]
```

**When to Include:**
- Configuration errors
- Setup/installation issues
- Complex troubleshooting
- First-time user errors

### EM-007: Professional Tone

Errors should be helpful, not blaming.

**Guidelines:**
- Use passive voice or "we" language
- Focus on the problem, not the user
- Avoid accusatory language

**Examples:**
| Good | Bad |
|------|-----|
| Invalid input format | You entered wrong format |
| Configuration missing | You forgot to configure |
| Unexpected value received | You provided wrong value |

### EM-008: Consistent Format

All errors follow the same structure.

**Standard Format:**
```
[Category] Description.
Context: [details]
Solution: [how to fix]
```

**Categories:**
- `[Config]` - Configuration issues
- `[Input]` - Invalid user input
- `[Network]` - Connection problems
- `[Auth]` - Authentication/authorization
- `[File]` - File system issues
- `[System]` - System-level errors

## Error Levels

### Error Severity

| Level | Use When |
|-------|----------|
| Error | Operation cannot continue |
| Warning | Operation continues but may have issues |
| Info | Informational, no action needed |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of command |
| 126 | Permission problem |
| 127 | Command not found |

## Anti-Patterns

### Avoid These

1. **Generic Messages**
   ```
   # Bad
   Error occurred
   Something went wrong
   Operation failed
   ```

2. **Technical Dumps**
   ```
   # Bad
   Error: TypeError: Cannot read property 'x' of undefined
       at Object.<anonymous> (/app/src/index.js:15:23)
       at Module._compile (internal/modules/cjs/loader.js:1063:30)
   ```

3. **Blaming Language**
   ```
   # Bad
   You made an error
   Wrong input provided
   User error detected
   ```

## Quality Metrics

| Metric | Target |
|--------|--------|
| Actionable errors | >90% |
| Context included | >80% |
| Plain language | 100% |
| Consistent format | 100% |
