---
name: deploy-npm
description: "Use when publishing packages to npm - validates package.json, generates publish workflows, handles version bumps, and supports scoped packages and private registries. Includes changelog integration and dry-run support."
---

# npm Package Publishing

## Overview

Configure npm package publishing with proper validation, versioning, and secure authentication. Generates GitHub Actions workflows for automated releases.

**Core principle:** Never publish broken packages. Validate everything before release.

**Trigger:** `/popkit:deploy setup npm` command

## Critical Rules

1. **ALWAYS validate package.json** - Required fields must be present and correct
2. **NEVER publish without tests passing** - CI must gate releases
3. **Use NPM_TOKEN for auth** - Never commit tokens, use GitHub secrets
4. **Respect semver** - Breaking changes = major, features = minor, fixes = patch
5. **Include only necessary files** - Use `files` field or `.npmignore`

## Process

### Step 1: Validate package.json

```python
import os
import json
from pathlib import Path

def validate_package_json():
    """Validate package.json for npm publishing."""
    cwd = Path.cwd()
    pkg_path = cwd / "package.json"

    if not pkg_path.exists():
        return {"valid": False, "error": "No package.json found"}

    with open(pkg_path) as f:
        pkg = json.load(f)

    issues = []
    warnings = []

    # Required fields
    required = ["name", "version", "description"]
    for field in required:
        if field not in pkg:
            issues.append(f"Missing required field: {field}")

    # Recommended fields for publishing
    recommended = ["main", "repository", "license", "keywords", "author"]
    for field in recommended:
        if field not in pkg:
            warnings.append(f"Missing recommended field: {field}")

    # TypeScript package checks
    if "typescript" in pkg.get("devDependencies", {}):
        if "types" not in pkg and "typings" not in pkg:
            warnings.append("TypeScript package missing 'types' field")
        if "build" not in pkg.get("scripts", {}):
            warnings.append("Missing 'build' script for TypeScript compilation")

    # Files field or npmignore
    if "files" not in pkg:
        if not (cwd / ".npmignore").exists():
            warnings.append("No 'files' field or .npmignore - all files will be published")

    # Check for private flag
    if pkg.get("private", False):
        issues.append("Package is marked as private - remove 'private' field to publish")

    # Validate version format
    version = pkg.get("version", "")
    if version and not is_valid_semver(version):
        issues.append(f"Invalid version format: {version}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "package": pkg
    }

def is_valid_semver(version):
    """Check if version follows semver."""
    import re
    pattern = r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
    return bool(re.match(pattern, version))
```

### Step 2: Ask About Package Type

```
Use AskUserQuestion tool with:
- question: "What type of npm package are you publishing?"
- header: "Package Type"
- options:
  - label: "Public package (Recommended)"
    description: "Available to everyone on npmjs.com"
  - label: "Scoped public (@org/package)"
    description: "Namespaced but still public"
  - label: "Private package"
    description: "Requires npm Pro or organization"
- multiSelect: false
```

### Step 3: Generate Files

Based on validation and package type.

## package.json Enhancements

### Minimal Valid package.json

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "A useful package",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": [
    "dist"
  ],
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "prepublishOnly": "npm run build && npm run test"
  },
  "keywords": ["utility"],
  "author": "Your Name <email@example.com>",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/username/repo.git"
  },
  "bugs": {
    "url": "https://github.com/username/repo/issues"
  },
  "homepage": "https://github.com/username/repo#readme"
}
```

### TypeScript Package

```json
{
  "name": "my-ts-package",
  "version": "1.0.0",
  "description": "A TypeScript package",
  "main": "dist/index.js",
  "module": "dist/index.mjs",
  "types": "dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "files": [
    "dist",
    "src"
  ],
  "scripts": {
    "build": "tsup src/index.ts --format cjs,esm --dts",
    "test": "vitest run",
    "prepublishOnly": "npm run build && npm run test"
  },
  "engines": {
    "node": ">=18"
  }
}
```

### Scoped Package (@org/package)

```json
{
  "name": "@myorg/my-package",
  "version": "1.0.0",
  "publishConfig": {
    "access": "public"
  }
}
```

## GitHub Actions Workflow

### Automated Publish on Release

```yaml
# .github/workflows/npm-publish.yml
name: Publish to npm

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # For npm provenance

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Publish
        run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Manual Publish with Version Selection

```yaml
# .github/workflows/npm-publish-manual.yml
name: Manual npm Publish

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version bump type'
        required: true
        default: 'patch'
        type: choice
        options:
          - patch
          - minor
          - major
          - prerelease
      dry_run:
        description: 'Dry run (no actual publish)'
        required: false
        type: boolean
        default: false

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
          cache: 'npm'

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Bump version
        run: npm version ${{ github.event.inputs.version }} -m "chore: release v%s"

      - name: Push version bump
        if: ${{ !github.event.inputs.dry_run }}
        run: git push && git push --tags

      - name: Publish (dry run)
        if: ${{ github.event.inputs.dry_run }}
        run: npm publish --dry-run
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      - name: Publish
        if: ${{ !github.event.inputs.dry_run }}
        run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Publish from Tag

```yaml
# .github/workflows/npm-publish-tag.yml
name: Publish to npm on Tag

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
          cache: 'npm'

      - name: Verify tag matches package version
        run: |
          PKG_VERSION=$(node -p "require('./package.json').version")
          TAG_VERSION=${GITHUB_REF_NAME#v}
          if [ "$PKG_VERSION" != "$TAG_VERSION" ]; then
            echo "Tag version ($TAG_VERSION) doesn't match package.json ($PKG_VERSION)"
            exit 1
          fi

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Publish
        run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## .npmrc Template

```ini
# .npmrc - npm configuration

# Use npm registry (default)
registry=https://registry.npmjs.org/

# For GitHub Packages (optional)
# @myorg:registry=https://npm.pkg.github.com/

# For private registries
# //registry.npmjs.org/:_authToken=${NPM_TOKEN}

# Disable package-lock for libraries
# package-lock=false

# Always run scripts with strict-ssl
strict-ssl=true
```

## .npmignore Template

```
# .npmignore - Files to exclude from npm package

# Source files (if shipping compiled)
src/
*.ts
!*.d.ts

# Tests
test/
tests/
__tests__/
*.test.js
*.test.ts
*.spec.js
*.spec.ts
coverage/
.nyc_output/

# Build tools
tsconfig.json
tsup.config.ts
vite.config.ts
rollup.config.js
webpack.config.js
jest.config.js
vitest.config.ts

# Documentation
docs/
*.md
!README.md
!CHANGELOG.md
!LICENSE

# IDE and editor
.vscode/
.idea/
*.swp

# Git
.git/
.gitignore
.github/

# Environment
.env
.env.*

# Claude Code
.claude/
```

## Version Bump Helper

```markdown
## Version Bump Quick Reference

| Change Type | Command | Example |
|-------------|---------|---------|
| Bug fix | `npm version patch` | 1.0.0 → 1.0.1 |
| New feature | `npm version minor` | 1.0.0 → 1.1.0 |
| Breaking change | `npm version major` | 1.0.0 → 2.0.0 |
| Prerelease | `npm version prerelease` | 1.0.0 → 1.0.1-0 |
| Specific version | `npm version 1.2.3` | → 1.2.3 |

### Prerelease Tags

```bash
# Alpha release
npm version prerelease --preid alpha  # 1.0.0-alpha.0

# Beta release
npm version prerelease --preid beta   # 1.0.0-beta.0

# Release candidate
npm version prerelease --preid rc     # 1.0.0-rc.0
```

### Publish with Tags

```bash
# Latest (default)
npm publish

# Beta tag
npm publish --tag beta

# Next tag (for prereleases)
npm publish --tag next
```
```

## Environment Variables Template

```markdown
# npm Publishing Setup

## Required Secrets

| Secret | Description | How to Get |
|--------|-------------|------------|
| `NPM_TOKEN` | npm automation token | npmjs.com → Access Tokens |

## Creating npm Token

1. Go to https://www.npmjs.com/settings/tokens
2. Click "Generate New Token"
3. Select "Automation" type (for CI/CD)
4. Copy the token immediately (shown once)

## Adding to GitHub

1. Go to Repository → Settings → Secrets → Actions
2. Click "New repository secret"
3. Name: `NPM_TOKEN`
4. Value: Your npm token

## For Scoped Packages

If publishing @org/package, ensure:
1. Organization exists on npm
2. You're a member with publish rights
3. Token has access to the org

## For Private Packages

Requires npm Pro ($7/mo) or npm Organizations.
Add to package.json:
```json
{
  "publishConfig": {
    "access": "restricted"
  }
}
```
```

## Output Format

```
npm Package Publishing Setup
════════════════════════════

[1/4] Validating package.json...
      ✓ Name: @myorg/my-package
      ✓ Version: 1.0.0
      ✓ Description: present
      ✓ Main: dist/index.js
      ✓ Types: dist/index.d.ts
      ⚠️ Warning: Missing 'repository' field

[2/4] Package type...
      ✓ Scoped public package
      ✓ publishConfig.access = "public"

[3/4] Generating workflows...
      ✓ Automated publish on release
      ✓ Manual publish with version selection
      → .github/workflows/npm-publish.yml
      → .github/workflows/npm-publish-manual.yml

[4/4] Generating templates...
      → .npmrc created
      → .npmignore created
      → docs/NPM_SETUP.md created

Files Created:
├── .npmrc
├── .npmignore
├── .github/workflows/npm-publish.yml
├── .github/workflows/npm-publish-manual.yml
└── docs/NPM_SETUP.md

Required Secrets:
  NPM_TOKEN  - Automation token from npmjs.com

Quick Commands:
  npm pack                    # Preview package contents
  npm publish --dry-run       # Test publish without uploading
  npm version patch           # Bump patch version
  npm publish                 # Publish to registry

Would you like to commit these files?
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| Package valid | `npm pack --dry-run` |
| Files correct | `npm pack && tar -tf *.tgz` |
| Tests pass | `npm test` |
| Build works | `npm run build` |
| Dry run publish | `npm publish --dry-run` |

## Integration

**Command:** `/popkit:deploy setup npm`

**Agent:** Uses `devops-automator` for package configuration

**Followed by:**
- `/popkit:deploy validate` - Pre-publish checks
- `/popkit:deploy execute npm` - Publish to registry

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-pypi` | Python package equivalent |
| `pop-deploy-github-releases` | For binary releases |
