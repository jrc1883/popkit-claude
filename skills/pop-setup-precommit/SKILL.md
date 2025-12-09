---
name: setup-precommit
description: "Use when setting up code quality automation for a project - configures pre-commit hooks and quality gates including linting, type checking, tests, and commit message validation. Supports Node.js (husky), Python (pre-commit), and Rust (cargo-husky). Do NOT use if project already has pre-commit configured - check for existing .husky/ or .pre-commit-config.yaml first."
---

# Setup Pre-commit Hooks

## Overview

Configure comprehensive pre-commit hooks to catch issues before they reach the repository. Quality gates that run automatically on every commit.

**Core principle:** Catch problems early. Every commit should be deployable.

**Trigger:** `/setup-precommit` command

## What Gets Configured

### For JavaScript/TypeScript Projects

**.husky/pre-commit:**
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# Run type check
npx tsc --noEmit

# Run lint on staged files
npx lint-staged

# Run affected tests
npx jest --onlyChanged --passWithNoTests
```

**.lintstagedrc.json:**
```json
{
  "*.{ts,tsx}": [
    "eslint --fix",
    "prettier --write"
  ],
  "*.{json,md}": [
    "prettier --write"
  ]
}
```

**.husky/commit-msg:**
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx --no -- commitlint --edit "$1"
```

**commitlint.config.js:**
```javascript
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor',
      'perf', 'test', 'chore', 'revert', 'ci'
    ]],
    'subject-case': [2, 'always', 'lower-case'],
    'header-max-length': [2, 'always', 72]
  }
};
```

### For Python Projects

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Setup Process

### Step 1: Detect Project Type

```bash
if [ -f "package.json" ]; then
  PROJECT_TYPE="node"
elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  PROJECT_TYPE="python"
elif [ -f "Cargo.toml" ]; then
  PROJECT_TYPE="rust"
else
  PROJECT_TYPE="generic"
fi
```

### Step 2: Install Dependencies

**Node.js:**
```bash
npm install -D husky lint-staged @commitlint/cli @commitlint/config-conventional
npx husky init
```

**Python:**
```bash
pip install pre-commit
pre-commit install
```

**Rust:**
```bash
cargo install cargo-husky
```

### Step 3: Create Hook Files

Generate appropriate hook files based on project type.

### Step 4: Verify Installation

```bash
# Test pre-commit hook
echo "test" > test-file.txt
git add test-file.txt
git commit -m "test: verify pre-commit hooks" --dry-run

# Clean up
rm test-file.txt
```

### Step 5: Configure CI Integration

Add to CI workflow to run same checks:

**.github/workflows/quality.yml:**
```yaml
name: Quality Checks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Type check
        run: npx tsc --noEmit

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm test
```

## Quality Gate Levels

### Level 1: Basic (Default)
- Trailing whitespace
- End of file newline
- Check YAML/JSON syntax
- Large file warning

### Level 2: Standard
- Level 1 +
- Lint with auto-fix
- Format code
- Type checking

### Level 3: Strict
- Level 2 +
- Run tests
- Check test coverage
- Commit message validation

### Level 4: Enterprise
- Level 3 +
- Security scanning
- License compliance
- Dependency audit

## Post-Setup

```
Pre-commit hooks configured!

Hooks installed:
- pre-commit: Type check, lint, format, test
- commit-msg: Conventional commit validation

Quality level: [Standard]

Commands:
- Skip hooks once: git commit --no-verify
- Run manually: npx lint-staged
- Bypass specific: HUSKY=0 git commit

Would you like to:
1. Test the hooks with a sample commit
2. Upgrade to Strict quality level
3. Configure CI to match
```

## Troubleshooting

### Hook Not Running

```bash
# Check husky installation
ls .husky/

# Reinstall hooks
npx husky install

# Make executable (Unix)
chmod +x .husky/*
```

### Too Slow

- Use lint-staged to only check changed files
- Configure test runner to only run affected tests
- Cache TypeScript compilation

### Bypassing When Needed

```bash
# Skip all hooks
git commit --no-verify -m "emergency fix"

# Skip specific hooks (set in hook script)
SKIP=eslint git commit -m "fix: bypass lint"
```

## Integration

**Requires:**
- Project analysis (detects appropriate hooks)

**Enables:**
- Consistent code quality
- Automatic formatting
- Early bug detection
- Standardized commits
