# Token Consumption Standards

Standards for efficient token usage in Claude Code plugins.

## Core Principles

### TC-001: Prompt Engineering

Design prompts for minimal token consumption.

**Guidelines:**
- Front-load critical information
- Use structured formats (tables, lists)
- Eliminate redundant language
- Reference instead of embed

**Token-Efficient Patterns:**
```markdown
# Instead of:
"This skill is designed to help users analyze their codebase
for potential security vulnerabilities. It works by scanning
all files and looking for common patterns that might indicate
security issues."

# Use:
"Scans codebase for security vulnerabilities using pattern matching."
```

### TC-002: Response Control

Control output token consumption.

**Techniques:**
- Request specific output format
- Set explicit length limits
- Use JSON for structured responses
- Specify required fields only

**Example:**
```markdown
## Output

Return JSON only:
- `score`: 0-100
- `issues`: [{file, line, severity}]
- `summary`: One sentence

No explanation needed.
```

### TC-003: Context Window Budget

Allocate token budget across components.

**Recommended Budget:**
| Component | Budget | Notes |
|-----------|--------|-------|
| System prompt | 30% | Core instructions |
| User context | 40% | Code, files, history |
| Agent/skill | 20% | Loaded prompts |
| Response | 10% | Expected output |

**Calculation:**
```
Total: 200K tokens (Claude 3.5 Sonnet)
System: 60K
User: 80K
Agent: 40K
Response: 20K
```

### TC-004: Incremental Loading

Load context incrementally.

**Phase Loading:**
```
Phase 1: Core instructions only
Phase 2: + Relevant agent prompt
Phase 3: + Specific file contents
Phase 4: + Additional context as needed
```

**On-Demand Details:**
```markdown
## Standards Reference

Standards available in `standards/` directory.
Load specific standard when needed:
- security.md for security reviews
- performance.md for optimization
```

### TC-005: Compression Techniques

Compress content where possible.

**Code Summarization:**
```python
# Full file: 500 lines
# Compressed summary:
"""
utils/parser.py (500 lines)
- Classes: Parser, Tokenizer, AST
- Main functions: parse(), tokenize(), build_ast()
- Dependencies: re, json, pathlib
"""
```

**Reference by Location:**
```markdown
# Instead of including full code:
See `src/auth/login.ts:45-60` for authentication logic.
```

### TC-006: Token Tracking

Monitor token consumption.

**Estimation:**
```python
def estimate_tokens(text: str) -> int:
    """Rough estimation: ~4 chars per token."""
    return len(text) // 4

def token_budget_check(content: str, budget: int) -> bool:
    estimated = estimate_tokens(content)
    return estimated <= budget
```

**Monitoring:**
```python
class TokenTracker:
    def __init__(self, budget: int):
        self.budget = budget
        self.used = 0

    def add(self, content: str) -> bool:
        tokens = estimate_tokens(content)
        if self.used + tokens > self.budget:
            return False
        self.used += tokens
        return True

    def remaining(self) -> int:
        return self.budget - self.used
```

## Optimization Strategies

### Content Deduplication

Remove repeated information:

```python
def deduplicate_imports(files: list) -> str:
    seen_imports = set()
    unique = []

    for file in files:
        imports = extract_imports(file)
        new_imports = [i for i in imports if i not in seen_imports]
        seen_imports.update(new_imports)
        unique.extend(new_imports)

    return format_imports(unique)
```

### Progressive Detail

Start minimal, add detail as needed:

```markdown
## Initial Context
File: auth.ts (200 lines)
Purpose: User authentication

## Detailed Context (on request)
[Full file content loaded here]
```

### Smart Truncation

Truncate intelligently:

```python
def smart_truncate(content: str, max_tokens: int) -> str:
    """Truncate preserving structure."""
    lines = content.split('\n')
    result = []
    tokens = 0

    for line in lines:
        line_tokens = estimate_tokens(line)
        if tokens + line_tokens > max_tokens:
            result.append("... [truncated]")
            break
        result.append(line)
        tokens += line_tokens

    return '\n'.join(result)
```

## Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Avg prompt tokens | <2000 | Per skill/agent |
| Context overhead | <30% | Non-essential content |
| Response efficiency | >50% | Useful / total output |
| Budget utilization | 70-90% | Using available context |

## Anti-Patterns

### Token Waste

```markdown
# Bad: Verbose
"The purpose of this skill is to help the user
understand and analyze their code for potential
issues that might cause problems in production."

# Good: Concise
"Analyzes code for production issues."
```

### Unnecessary Repetition

```markdown
# Bad: Repeated instructions
Step 1: Read the file carefully
Step 2: After reading the file carefully, analyze it
Step 3: Once you have analyzed the file you read...

# Good: Single instruction
1. Read file
2. Analyze patterns
3. Report findings
```

### Embedding vs Reference

```markdown
# Bad: Embedding full docs
[500 lines of documentation embedded]

# Good: Reference
See `docs/full-guide.md` for complete documentation.
For this task, focus on sections 3.1 and 3.2.
```
