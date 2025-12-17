---
name: deploy-pypi
description: "Use when publishing packages to PyPI - validates pyproject.toml, generates publish workflows with Trusted Publisher support, handles version bumps, and supports both PyPI and TestPyPI. Includes changelog integration and dry-run support."
---

# PyPI Package Publishing

## Overview

Configure Python package publishing with proper validation, versioning, and secure authentication. Generates GitHub Actions workflows for automated releases using PyPI Trusted Publishers (OIDC).

**Core principle:** Use modern Python packaging standards (pyproject.toml) with Trusted Publisher authentication.

**Trigger:** `/popkit:deploy setup pypi` command

## Critical Rules

1. **ALWAYS use pyproject.toml** - Modern Python packaging standard (PEP 518, 621)
2. **NEVER use passwords** - Use Trusted Publishers (OIDC) for secure auth
3. **Test on TestPyPI first** - Verify package before production release
4. **Include py.typed** - For type-annotated packages
5. **Use src/ layout** - Prevents import issues during development

## Process

### Step 1: Validate pyproject.toml

```python
import os
from pathlib import Path

def validate_pyproject():
    """Validate pyproject.toml for PyPI publishing."""
    cwd = Path.cwd()
    pyproject_path = cwd / "pyproject.toml"

    if not pyproject_path.exists():
        # Check for legacy setup.py
        if (cwd / "setup.py").exists():
            return {
                "valid": False,
                "error": "Using legacy setup.py - recommend migrating to pyproject.toml"
            }
        return {"valid": False, "error": "No pyproject.toml found"}

    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    issues = []
    warnings = []

    # Check [project] section
    project = pyproject.get("project", {})

    # Required fields
    required = ["name", "version", "description"]
    for field in required:
        if field not in project:
            issues.append(f"Missing required field: project.{field}")

    # Recommended fields
    recommended = ["authors", "readme", "license", "classifiers", "keywords"]
    for field in recommended:
        if field not in project:
            warnings.append(f"Missing recommended field: project.{field}")

    # Check for dynamic version
    if "version" not in project:
        dynamic = project.get("dynamic", [])
        if "version" not in dynamic:
            issues.append("No version specified (static or dynamic)")

    # Check build system
    build_system = pyproject.get("build-system", {})
    if "requires" not in build_system:
        issues.append("Missing [build-system].requires")
    if "build-backend" not in build_system:
        issues.append("Missing [build-system].build-backend")

    # Check for src layout
    if (cwd / "src").exists():
        # Good - using src layout
        pass
    elif project.get("name") and (cwd / project["name"].replace("-", "_")).exists():
        warnings.append("Consider using src/ layout for better isolation")

    # Check for py.typed
    if (cwd / "py.typed").exists() or any((cwd / "src").rglob("py.typed")):
        pass
    else:
        warnings.append("No py.typed marker - package won't be recognized as typed")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "pyproject": pyproject
    }
```

### Step 2: Ask About Build Backend

```
Use AskUserQuestion tool with:
- question: "Which build backend should we configure?"
- header: "Build Backend"
- options:
  - label: "Hatchling (Recommended)"
    description: "Modern, fast, extensible - used by pip itself"
  - label: "Setuptools"
    description: "Classic, well-documented, wide compatibility"
  - label: "PDM"
    description: "PEP 582 support, lockfiles, monorepo friendly"
  - label: "Poetry"
    description: "Dependency management + publishing"
- multiSelect: false
```

### Step 3: Generate Files

Based on validation and build backend choice.

## pyproject.toml Templates

### Hatchling (Recommended)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
description = "A useful Python package"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
    { name = "Your Name", email = "email@example.com" }
]
keywords = ["utility", "library"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]
dependencies = [
    "requests>=2.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
]

[project.urls]
Homepage = "https://github.com/username/repo"
Documentation = "https://username.github.io/repo"
Repository = "https://github.com/username/repo"
Issues = "https://github.com/username/repo/issues"

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
]

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]
```

### Setuptools

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "1.0.0"
description = "A useful Python package"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.9"
authors = [
    { name = "Your Name", email = "email@example.com" }
]
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]
dependencies = [
    "requests>=2.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://github.com/username/repo"

[tool.setuptools.packages.find]
where = ["src"]
```

### With Dynamic Version (Git Tags)

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "my-package"
dynamic = ["version"]
description = "A useful Python package"
# ... rest of project config

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/my_package/_version.py"
```

## GitHub Actions Workflows

### Trusted Publisher Publish (Recommended)

```yaml
# .github/workflows/pypi-publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/p/${{ github.event.repository.name }}
    permissions:
      id-token: write

    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/${{ github.event.repository.name }}
    permissions:
      id-token: write

    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### Manual Publish with Version Selection

```yaml
# .github/workflows/pypi-publish-manual.yml
name: Manual PyPI Publish

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to publish'
        required: true
        type: string
      testpypi_only:
        description: 'Publish to TestPyPI only'
        required: false
        type: boolean
        default: true

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Verify version matches
        run: |
          PKG_VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
          if [ "$PKG_VERSION" != "${{ github.event.inputs.version }}" ]; then
            echo "Input version (${{ github.event.inputs.version }}) doesn't match pyproject.toml ($PKG_VERSION)"
            exit 1
          fi

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      id-token: write

    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    if: ${{ !github.event.inputs.testpypi_only }}
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write

    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### Test Package Before Publish

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run linter
        run: ruff check src tests

      - name: Run type checker
        run: mypy src

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
```

## Trusted Publisher Setup

```markdown
# PyPI Trusted Publisher Setup

PyPI Trusted Publishers use OIDC (OpenID Connect) for secure, tokenless publishing from GitHub Actions.

## Step 1: Create PyPI Account

1. Go to https://pypi.org/account/register/
2. Verify email
3. Enable 2FA (required for publishing)

## Step 2: Configure Trusted Publisher

**Before first publish:**

1. Go to https://pypi.org/manage/account/publishing/
2. Add "pending publisher" with:
   - PyPI project name: `my-package`
   - Owner: `username` (GitHub username/org)
   - Repository: `repo-name`
   - Workflow: `pypi-publish.yml`
   - Environment: `pypi` (optional but recommended)

**For TestPyPI:**

1. Go to https://test.pypi.org/manage/account/publishing/
2. Same configuration

## Step 3: Create GitHub Environments

1. Go to Repository → Settings → Environments
2. Create `pypi` environment
3. Create `testpypi` environment
4. (Optional) Add protection rules (required reviewers, etc.)

## Why Trusted Publishers?

| Aspect | API Tokens | Trusted Publishers |
|--------|------------|-------------------|
| Rotation | Manual | Automatic |
| Scope | Package or account | Workflow-specific |
| Storage | GitHub Secrets | None needed |
| Security | Token can leak | Cryptographic proof |
```

## Version Bump Helper

```markdown
## Version Bump Quick Reference

### Using Hatch

```bash
# Show current version
hatch version

# Bump version
hatch version patch   # 1.0.0 → 1.0.1
hatch version minor   # 1.0.0 → 1.1.0
hatch version major   # 1.0.0 → 2.0.0

# Set specific version
hatch version 1.2.3
```

### Using bump2version

```bash
# Install
pip install bump2version

# Bump
bump2version patch    # 1.0.0 → 1.0.1
bump2version minor    # 1.0.0 → 1.1.0
bump2version major    # 1.0.0 → 2.0.0
```

### Manual (edit pyproject.toml)

```toml
[project]
version = "1.0.1"  # Update this
```

### Prerelease Versions

```
1.0.0a1   # Alpha
1.0.0b1   # Beta
1.0.0rc1  # Release candidate
1.0.0     # Final release
```
```

## Output Format

```
PyPI Package Publishing Setup
═════════════════════════════

[1/4] Validating pyproject.toml...
      ✓ Name: my-package
      ✓ Version: 1.0.0
      ✓ Description: present
      ✓ Build system: hatchling
      ⚠️ Warning: No py.typed marker found

[2/4] Build backend...
      ✓ Using: Hatchling
      ✓ Source layout: src/

[3/4] Generating workflows...
      ✓ Trusted Publisher (OIDC) authentication
      ✓ TestPyPI → PyPI pipeline
      ✓ Manual publish with version input
      → .github/workflows/pypi-publish.yml
      → .github/workflows/pypi-publish-manual.yml
      → .github/workflows/test.yml

[4/4] Generating setup guide...
      → docs/PYPI_SETUP.md created

Files Created:
├── .github/workflows/pypi-publish.yml
├── .github/workflows/pypi-publish-manual.yml
├── .github/workflows/test.yml
└── docs/PYPI_SETUP.md

Next Steps:
1. Configure Trusted Publisher on PyPI
2. Create GitHub environments (pypi, testpypi)
3. Add py.typed marker for typed packages

Quick Commands:
  python -m build           # Build sdist and wheel
  twine check dist/*        # Verify package
  twine upload --repository testpypi dist/*  # Upload to TestPyPI

Would you like to commit these files?
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| pyproject.toml valid | `python -m build --dry-run` |
| Build succeeds | `python -m build` |
| Package checks pass | `twine check dist/*` |
| Tests pass | `pytest` |
| Types check | `mypy src` |

## Integration

**Command:** `/popkit:deploy setup pypi`

**Agent:** Uses `devops-automator` for package configuration

**Followed by:**
- `/popkit:deploy validate` - Pre-publish checks
- `/popkit:deploy execute pypi` - Publish to registry

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-npm` | JavaScript package equivalent |
| `pop-deploy-github-releases` | For binary releases |
