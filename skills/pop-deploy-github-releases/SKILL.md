---
name: deploy-github-releases
description: "Use when releasing CLI tools and binary artifacts - generates cross-platform build workflows, checksum files, and changelog-based release notes. Supports Go, Rust, Node.js (pkg), Python (PyInstaller), and pre-built binaries."
---

# GitHub Releases Deployment

## Overview

Configure GitHub Releases for CLI tools and binary artifacts. Generates cross-platform build workflows, checksum files, and automated release notes.

**Core principle:** Every release should be reproducible and verifiable.

**Trigger:** `/popkit:deploy setup github-releases` command

## Critical Rules

1. **ALWAYS include checksums** - SHA256 for all artifacts
2. **Build for all major platforms** - linux, macos, windows (amd64 + arm64)
3. **Use conventional commits** - For automated changelog generation
4. **Sign releases when possible** - GPG or Sigstore for verification
5. **Include source tarball** - For reproducibility

## Process

### Step 1: Detect Project Type

```python
import os
import json
from pathlib import Path

def detect_release_type():
    """Detect project type for release configuration."""
    cwd = Path.cwd()

    # Check for Go
    if (cwd / "go.mod").exists():
        return "go"

    # Check for Rust
    if (cwd / "Cargo.toml").exists():
        return "rust"

    # Check for Python CLI
    if (cwd / "pyproject.toml").exists():
        with open(cwd / "pyproject.toml", "rb") as f:
            import tomllib
            pyproject = tomllib.load(f)
            if "scripts" in pyproject.get("project", {}):
                return "python-cli"
        return "python"

    # Check for Node.js CLI
    if (cwd / "package.json").exists():
        with open(cwd / "package.json") as f:
            pkg = json.load(f)
            if "bin" in pkg:
                return "node-cli"
        return "node"

    return "generic"
```

### Step 2: Ask About Release Configuration

```
Use AskUserQuestion tool with:
- question: "What type of release are you configuring?"
- header: "Release Type"
- options:
  - label: "CLI Binary (Recommended)"
    description: "Cross-platform binaries with checksums"
  - label: "Library/Package"
    description: "Integrate with npm/PyPI publish workflows"
  - label: "Pre-built Assets"
    description: "Upload existing build artifacts"
- multiSelect: false
```

### Step 3: Configure Platforms

```
Use AskUserQuestion tool with:
- question: "Which platforms should we build for?"
- header: "Platforms"
- options:
  - label: "All platforms (Recommended)"
    description: "linux, macos, windows × amd64, arm64"
  - label: "Linux + macOS"
    description: "Unix-like systems only"
  - label: "Linux only"
    description: "Server/container deployments"
- multiSelect: false
```

## GitHub Actions Workflows

### Go Release (GoReleaser)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true

      - name: Run GoReleaser
        uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GoReleaser Configuration

```yaml
# .goreleaser.yaml
version: 2

project_name: my-cli

before:
  hooks:
    - go mod tidy

builds:
  - env:
      - CGO_ENABLED=0
    goos:
      - linux
      - darwin
      - windows
    goarch:
      - amd64
      - arm64
    ldflags:
      - -s -w
      - -X main.version={{.Version}}
      - -X main.commit={{.Commit}}
      - -X main.date={{.Date}}
    binary: '{{ .ProjectName }}'

archives:
  - format: tar.gz
    name_template: >-
      {{ .ProjectName }}_
      {{- .Version }}_
      {{- .Os }}_
      {{- .Arch }}
    format_overrides:
      - goos: windows
        format: zip
    files:
      - README.md
      - LICENSE

checksum:
  name_template: 'checksums.txt'
  algorithm: sha256

changelog:
  sort: asc
  use: github
  filters:
    exclude:
      - '^docs:'
      - '^test:'
      - '^chore:'
  groups:
    - title: Features
      regexp: '^feat'
      order: 0
    - title: Bug Fixes
      regexp: '^fix'
      order: 1
    - title: Performance
      regexp: '^perf'
      order: 2
    - title: Others
      order: 999

release:
  github:
    owner: '{{ .Env.GITHUB_REPOSITORY_OWNER }}'
    name: '{{ .ProjectName }}'
  draft: false
  prerelease: auto
  mode: replace
  header: |
    ## {{ .ProjectName }} {{ .Version }}

    Welcome to this release!
  footer: |
    ## Checksums

    ```
    {{ .Checksums }}
    ```

    **Full Changelog**: https://github.com/{{ .Env.GITHUB_REPOSITORY }}/compare/{{ .PreviousTag }}...{{ .Tag }}
```

### Rust Release (cargo-dist)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    strategy:
      matrix:
        include:
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
          - target: x86_64-apple-darwin
            os: macos-latest
          - target: aarch64-apple-darwin
            os: macos-latest
          - target: x86_64-pc-windows-msvc
            os: windows-latest

    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Rust
        uses: dtolnay/rust-action@stable
        with:
          targets: ${{ matrix.target }}

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Archive (Unix)
        if: matrix.os != 'windows-latest'
        run: |
          cd target/${{ matrix.target }}/release
          tar czvf ../../../my-cli-${{ matrix.target }}.tar.gz my-cli
          cd ../../..
          sha256sum my-cli-${{ matrix.target }}.tar.gz > my-cli-${{ matrix.target }}.tar.gz.sha256

      - name: Archive (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          cd target/${{ matrix.target }}/release
          7z a ../../../my-cli-${{ matrix.target }}.zip my-cli.exe
          cd ../../..
          certutil -hashfile my-cli-${{ matrix.target }}.zip SHA256 > my-cli-${{ matrix.target }}.zip.sha256

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.target }}
          path: |
            *.tar.gz
            *.zip
            *.sha256

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true

      - name: Generate changelog
        id: changelog
        uses: orhun/git-cliff-action@v3
        with:
          args: --latest --strip header

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          body: ${{ steps.changelog.outputs.content }}
          files: |
            artifacts/*
          draft: false
          prerelease: ${{ contains(github.ref, '-') }}
```

### Node.js CLI (pkg)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: node18-linux-x64
            ext: ''
          - os: ubuntu-latest
            target: node18-linux-arm64
            ext: ''
          - os: macos-latest
            target: node18-macos-x64
            ext: ''
          - os: macos-latest
            target: node18-macos-arm64
            ext: ''
          - os: windows-latest
            target: node18-win-x64
            ext: '.exe'

    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Package binary
        run: npx pkg . --target ${{ matrix.target }} --output my-cli${{ matrix.ext }}

      - name: Archive (Unix)
        if: matrix.os != 'windows-latest'
        run: |
          tar czvf my-cli-${{ matrix.target }}.tar.gz my-cli
          sha256sum my-cli-${{ matrix.target }}.tar.gz > my-cli-${{ matrix.target }}.tar.gz.sha256

      - name: Archive (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          7z a my-cli-${{ matrix.target }}.zip my-cli.exe
          certutil -hashfile my-cli-${{ matrix.target }}.zip SHA256 > my-cli-${{ matrix.target }}.zip.sha256

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.target }}
          path: |
            *.tar.gz
            *.zip
            *.sha256

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true

      - name: Generate release notes
        id: notes
        run: |
          echo "## What's Changed" > notes.md
          git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --pretty=format:"- %s" >> notes.md
          echo "" >> notes.md
          echo "## Checksums" >> notes.md
          echo '```' >> notes.md
          cat artifacts/*.sha256 >> notes.md
          echo '```' >> notes.md

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          body_path: notes.md
          files: |
            artifacts/*
```

### Python CLI (PyInstaller)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact: my-cli-linux-x64
          - os: macos-latest
            artifact: my-cli-macos-x64
          - os: windows-latest
            artifact: my-cli-windows-x64.exe

    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -e .

      - name: Build with PyInstaller
        run: pyinstaller --onefile --name ${{ matrix.artifact }} src/my_cli/__main__.py

      - name: Archive (Unix)
        if: matrix.os != 'windows-latest'
        run: |
          cd dist
          tar czvf ../${{ matrix.artifact }}.tar.gz ${{ matrix.artifact }}
          cd ..
          sha256sum ${{ matrix.artifact }}.tar.gz > ${{ matrix.artifact }}.tar.gz.sha256

      - name: Archive (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          cd dist
          7z a ../${{ matrix.artifact }}.zip ${{ matrix.artifact }}
          cd ..
          certutil -hashfile ${{ matrix.artifact }}.zip SHA256 > ${{ matrix.artifact }}.zip.sha256

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.artifact }}
          path: |
            *.tar.gz
            *.zip
            *.sha256

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            artifacts/*
```

### Generic Release (Pre-built Assets)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      tag:
        description: 'Tag to release'
        required: true
        type: string

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Build artifacts
        run: |
          # Your build commands here
          ./build.sh

      - name: Generate checksums
        run: |
          cd dist
          sha256sum * > checksums.txt

      - name: Generate changelog
        id: changelog
        uses: orhun/git-cliff-action@v3
        with:
          args: --latest --strip header

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ inputs.tag || github.ref_name }}
          body: |
            ${{ steps.changelog.outputs.content }}

            ## Checksums

            ```
            $(cat dist/checksums.txt)
            ```
          files: |
            dist/*
          draft: false
          prerelease: ${{ contains(github.ref, '-') }}
```

## git-cliff Configuration

```toml
# cliff.toml - Changelog generation
[changelog]
header = """
# Changelog\n
All notable changes to this project will be documented in this file.\n
"""
body = """
{% if version %}\
    ## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}\
    ## [unreleased]
{% endif %}\
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | striptags | trim | upper_first }}
    {% for commit in commits %}
        - {% if commit.scope %}*({{ commit.scope }})* {% endif %}\
            {{ commit.message | upper_first }}\
    {% endfor %}
{% endfor %}\n
"""
footer = """
{% for release in releases -%}
    {% if release.version -%}
        {% if release.previous.version -%}
            [{{ release.version | trim_start_matches(pat="v") }}]: \
                https://github.com/{{ remote.github.owner }}/{{ remote.github.repo }}\
                    /compare/{{ release.previous.version }}...{{ release.version }}
        {% endif -%}
    {% else -%}
        [unreleased]: https://github.com/{{ remote.github.owner }}/{{ remote.github.repo }}\
            /compare/{{ release.previous.version }}...HEAD
    {% endif -%}
{% endfor %}
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^doc", group = "Documentation" },
    { message = "^perf", group = "Performance" },
    { message = "^refactor", group = "Refactor" },
    { message = "^style", group = "Styling" },
    { message = "^test", group = "Testing" },
    { message = "^chore\\(release\\)", skip = true },
    { message = "^chore", group = "Miscellaneous Tasks" },
]
filter_commits = false
tag_pattern = "v[0-9]*"
```

## Output Format

```
GitHub Releases Setup
═════════════════════

[1/4] Detecting project type...
      ✓ Detected: Go CLI
      ✓ Binary: my-cli
      ✓ Version: from ldflags

[2/4] Release configuration...
      ✓ Type: CLI Binary
      ✓ Platforms: linux, macos, windows × amd64, arm64
      ✓ Checksums: SHA256

[3/4] Generating workflows...
      ✓ GoReleaser configuration
      ✓ Release workflow (on tag push)
      → .goreleaser.yaml
      → .github/workflows/release.yml

[4/4] Generating changelog config...
      → cliff.toml created (git-cliff)

Files Created:
├── .goreleaser.yaml
├── .github/workflows/release.yml
└── cliff.toml

Release Process:
  1. git tag v1.0.0
  2. git push --tags
  3. GitHub Actions builds and creates release

Artifacts per release:
  - my-cli_1.0.0_linux_amd64.tar.gz
  - my-cli_1.0.0_linux_arm64.tar.gz
  - my-cli_1.0.0_darwin_amd64.tar.gz
  - my-cli_1.0.0_darwin_arm64.tar.gz
  - my-cli_1.0.0_windows_amd64.zip
  - checksums.txt

Would you like to commit these files?
```

## Integration with /popkit:git release

The deploy command works with `/popkit:git release`:

```
# Create release with changelog
/popkit:git release create v1.0.0

# This triggers:
# 1. Creates git tag v1.0.0
# 2. Pushes tag to origin
# 3. GitHub Actions runs release.yml
# 4. Builds artifacts for all platforms
# 5. Creates GitHub Release with changelog
# 6. Uploads artifacts + checksums
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| Workflow syntax | `gh workflow view release.yml` |
| GoReleaser config | `goreleaser check` |
| Test build locally | `goreleaser build --snapshot --clean` |
| Test release dry-run | `goreleaser release --snapshot --clean` |

## Integration

**Command:** `/popkit:deploy setup github-releases`

**Agent:** Uses `devops-automator` for release configuration

**Related:**
- `/popkit:git release` - Create releases
- `/popkit:git release changelog` - Generate changelog

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-npm` | For npm package releases |
| `pop-deploy-pypi` | For PyPI package releases |
