---
name: pop-pattern-share
description: "Cross-project pattern sharing for learned corrections, error solutions, and workflow patterns. Enables sharing knowledge with team or community via PopKit Cloud. Privacy-first with full anonymization before sharing. Use when you've solved a problem that others might benefit from. Do NOT use for project-specific patterns that wouldn't generalize to other contexts."
---

# Cross-Project Pattern Sharing

## Overview

Share learned patterns, corrections, and solutions across projects via PopKit Cloud. Patterns are fully anonymized before sharing to protect privacy.

**Core principle:** Knowledge learned in one project should benefit others - but privacy comes first.

**Trigger:** User mentions "share", "help others", "contribute pattern", or has solved a generalizable problem.

## When to Use

Invoke this skill when:
- User has solved a problem that would help others
- Command correction would benefit the community
- Error solution is broadly applicable
- Workflow pattern is framework-agnostic
- User explicitly wants to share a pattern

## Do NOT Use When

Skip this skill when:
- Pattern is project-specific (won't generalize)
- Contains sensitive business logic
- User hasn't consented to sharing
- Pattern quality is uncertain

## Sharing Levels

| Level | Description | Tier Required | Visibility |
|-------|-------------|---------------|------------|
| **PRIVATE** | Stays local | Free | Only you |
| **TEAM** | Team members | Team | Your organization |
| **COMMUNITY** | Public database | Pro/Team | Everyone |

## Pattern Types

### Command Corrections

Platform-specific command corrections:

```python
from pattern_client import share_command_correction

# Example: cp -r doesn't work on Windows
pattern_id = share_command_correction(
    original="cp -r source/ dest/",
    corrected="xcopy /E source\\ dest\\",
    platform="windows"
)
```

### Error Solutions

Solutions for common errors:

```python
from pattern_client import get_pattern_client, PatternType, ShareLevel

client = get_pattern_client()

result = client.submit_pattern(
    pattern_type=PatternType.ERROR,
    content="Error: Cannot find module 'react'",
    solution="Run: npm install react or check package.json dependencies",
    share_level=ShareLevel.COMMUNITY,
    metadata={
        'language': 'typescript',
        'framework': 'react'
    }
)
```

### Workflow Patterns

Reusable workflow patterns:

```python
result = client.submit_pattern(
    pattern_type=PatternType.WORKFLOW,
    content="Setting up TypeScript with ESLint and Prettier",
    solution="""
    1. Install: npm install -D typescript eslint prettier @typescript-eslint/parser
    2. Create tsconfig.json with strict mode
    3. Create .eslintrc.js extending typescript-eslint
    4. Create .prettierrc with your preferences
    5. Add scripts to package.json
    """,
    share_level=ShareLevel.COMMUNITY,
    metadata={
        'language': 'typescript'
    }
)
```

## Anonymization Process

All patterns are automatically anonymized before sharing:

```python
from pattern_anonymizer import anonymize_pattern, validate_anonymization

# Original pattern
pattern = {
    'type': 'error',
    'content': 'Error in C:\\Users\\John\\my-secret-app: module not found',
    'solution': 'Install the missing module with npm install',
    'api_key': 'sk-12345...'  # Will be redacted
}

# Anonymize
anonymized = anonymize_pattern(pattern, project_root="C:\\Users\\John\\my-secret-app")

# Validate
issues = validate_anonymization(anonymized)
if issues['errors']:
    print("Cannot share - contains sensitive data")
```

### What Gets Anonymized

| Data Type | Before | After |
|-----------|--------|-------|
| User paths | `/Users/john/projects` | `/Users/[USER]/[PROJECT_DIR]` |
| API keys | `sk-12345...` | `[REDACTED_API_KEY]` |
| Emails | `john@example.com` | `[REDACTED_EMAIL]` |
| Project names | `my-secret-app` | `[PROJECT_abc123]` |
| IP addresses | `192.168.1.1` | `[REDACTED_IP]` |

## Sharing Workflow

### Step 1: Identify Shareable Pattern

After solving a problem, determine if it would help others:

```
Use AskUserQuestion tool with:
- question: "Would you like to share this solution with the community?"
- header: "Share"
- options:
  - label: "Yes, share with community"
    description: "Help others who face the same issue"
  - label: "Share with team only"
    description: "Keep within your organization"
  - label: "Keep private"
    description: "Don't share this solution"
- multiSelect: false
```

### Step 2: Capture Pattern Details

Gather the essential information:

```python
pattern_data = {
    'type': 'error',  # or 'command', 'workflow'
    'content': original_problem,
    'solution': working_solution,
    'platform': detect_platform(),  # windows, linux, darwin
    'language': detect_language(),  # from project files
    'framework': detect_framework(),  # react, nextjs, django, etc.
    'tags': ['npm', 'dependencies', 'typescript']
}
```

### Step 3: Anonymize and Validate

```python
from pattern_anonymizer import anonymize_pattern, validate_anonymization

# Anonymize
anonymized = anonymize_pattern(pattern_data, project_root=os.getcwd())

# Validate
issues = validate_anonymization(anonymized)

if issues['errors']:
    # Cannot share - contains sensitive data
    print("Pattern contains sensitive data that could not be anonymized:")
    for error in issues['errors']:
        print(f"  - {error}")
    return

if issues['warnings']:
    # Confirm with user
    print("Warnings:")
    for warning in issues['warnings']:
        print(f"  - {warning}")
```

### Step 4: Submit to Cloud

```python
from pattern_client import get_pattern_client, ShareLevel

client = get_pattern_client()

result = client.submit_pattern(
    pattern_type=pattern_data['type'],
    content=pattern_data['content'],
    solution=pattern_data['solution'],
    project_root=os.getcwd(),
    share_level=ShareLevel.COMMUNITY,
    metadata={
        'platform': pattern_data.get('platform'),
        'language': pattern_data.get('language'),
        'framework': pattern_data.get('framework'),
        'tags': pattern_data.get('tags', [])
    }
)

print(f"Pattern shared: {result.pattern_id}")
print(f"Quality score: {result.quality_score}")
```

### Step 5: Report Result

```markdown
## Pattern Shared

Your solution has been shared with the PopKit community!

**Pattern ID:** abc123-def456
**Type:** Error Solution
**Quality Score:** 8.5/10

### What You Shared
- **Problem:** [anonymized problem description]
- **Solution:** [your solution]
- **Tags:** npm, dependencies, typescript

### Impact
This pattern will help others who encounter the same issue.
You'll receive notifications when others find it helpful.

Thank you for contributing to the community!
```

## Finding Community Patterns

### Search for Solutions

```python
from pattern_client import get_pattern_client

client = get_pattern_client()

# Search for patterns
results = client.search_patterns(
    query="module not found typescript",
    pattern_type="error",
    language="typescript",
    min_score=7.0
)

for pattern in results.patterns:
    print(f"[{pattern['type']}] {pattern['content'][:50]}...")
    print(f"  Solution: {pattern['solution'][:100]}...")
    print(f"  Score: {pattern['quality_score']}/10")
```

### Find Similar Patterns

```python
# Find patterns similar to current error
similar = client.get_similar_patterns(
    content="Cannot read property 'map' of undefined",
    pattern_type="error",
    limit=3
)
```

### Get Trending Patterns

```python
trending = client.get_trending_patterns(
    platform="windows",
    limit=10
)
```

## Voting and Feedback

### Vote on Pattern Quality

```python
# Vote up a helpful pattern
client.vote_pattern(pattern_id, vote=+1)

# Vote down an unhelpful pattern
client.vote_pattern(pattern_id, vote=-1)
```

### Report Pattern Usage

```python
# Report that a pattern was helpful
client.report_pattern_usage(
    pattern_id=pattern_id,
    success=True,
    context="Used for React TypeScript project"
)
```

## Privacy Controls

### Check Privacy Settings

```python
from privacy import get_privacy_manager

privacy = get_privacy_manager()
sharing_level = privacy.get_setting('pattern_sharing')

if sharing_level == 'none':
    print("Pattern sharing is disabled")
elif sharing_level == 'team':
    print("Patterns shared with team only")
else:
    print("Community sharing enabled")
```

### Disable Pattern Sharing

Users can disable pattern sharing via `/popkit:privacy level strict`.

## Quality Scoring

Patterns are scored based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Votes** | 30% | Community up/down votes |
| **Usage** | 25% | How often pattern is applied |
| **Success Rate** | 25% | Whether pattern solved the problem |
| **Specificity** | 10% | Clear problem + solution |
| **Recency** | 10% | Fresh patterns scored higher |

## Error Handling

| Situation | Response |
|-----------|----------|
| No API key | Prompt user to authenticate |
| Anonymization fails | Show what couldn't be anonymized |
| Network error | Queue for later submission |
| Duplicate pattern | Link to existing pattern |
| Low quality | Suggest improvements |

## Related

- `hooks/utils/pattern_anonymizer.py` - Pattern anonymization
- `hooks/utils/pattern_client.py` - Cloud API client
- `/popkit:privacy` command - Privacy settings
- `/popkit:bug report` - Bug reporting (uses similar patterns)
