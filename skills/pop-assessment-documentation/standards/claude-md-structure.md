# CLAUDE.md Structure Standards

Standards for creating effective CLAUDE.md files that guide AI assistants.

## Core Principles

### CM-001: Project Overview

The first section should provide immediate context.

**Required Elements:**
- Project name and one-line description
- Primary purpose and goals
- Target users/developers
- Key technologies used

**Example:**
```markdown
## Project Overview

**PopKit** is an AI-powered development workflow system. This repository
contains the Claude Code plugin that orchestrates AI agents for software
development tasks.
```

### CM-002: Repository Structure

Visual directory tree with explanations.

**Format:**
```markdown
## Repository Structure

\`\`\`
project/
├── src/           # Source code
│   ├── core/      # Core business logic
│   └── utils/     # Utility functions
├── tests/         # Test files
└── docs/          # Documentation
\`\`\`
```

**Guidelines:**
- Use ASCII tree format
- Include meaningful comments
- Show 2-3 levels of depth
- Highlight entry points

### CM-003: Development Notes

Essential information for working with the codebase.

**Required:**
- Build commands
- Test commands
- Prerequisites
- Environment setup

**Format:**
```markdown
## Development Notes

This is a configuration-only project - no build commands.
- Run tests: `npm test`
- Lint: `npm run lint`
```

### CM-004: Key Architectural Patterns

Document design decisions and patterns.

**Include:**
- Main architectural patterns used
- Rationale for decisions
- File locations for implementations
- Cross-references to detailed docs

### CM-005: Key Files Table

Quick reference for important files.

**Format:**
```markdown
| File | Purpose |
|------|---------|
| `src/index.ts` | Application entry point |
| `config.json` | Configuration settings |
```

**Guidelines:**
- Use relative paths
- Keep descriptions under 50 chars
- Include entry points, configs, and core modules

### CM-006: Version History

Current version and changelog reference.

**Format:**
```markdown
## Version History

**Current Version:** 1.0.0

See [CHANGELOG.md](CHANGELOG.md) for full history.
```

### CM-007: Conventions

Coding and documentation standards.

**Include:**
- Commit message format
- Branch naming conventions
- Code style guidelines
- File naming patterns

### CM-008: Auto-Generated Sections

Sections that are programmatically updated.

**Marker Format:**
```markdown
<!-- AUTO-GEN:SECTION_NAME START -->
Auto-generated content here
<!-- AUTO-GEN:SECTION_NAME END -->
```

**Guidelines:**
- Use consistent marker format
- Document regeneration script
- Include last-updated timestamp

### CM-009: Quick Start (Optional)

Fast onboarding for new developers.

**Include:**
1. Installation command
2. First run command
3. Verification step
4. Next steps reference

### CM-010: Troubleshooting (Optional)

Common issues and solutions.

**Format:**
- Problem → Solution pairs
- FAQ style
- Links to detailed docs

## Quality Checklist

| Check | Required | Description |
|-------|----------|-------------|
| Project Overview | Yes | Clear one-paragraph summary |
| Repository Structure | Yes | Visual tree with explanations |
| Development Notes | Yes | Build/test/setup commands |
| Key Patterns | Yes | Architecture documentation |
| Key Files | Yes | Quick reference table |
| Conventions | Yes | Style and commit guidelines |
| Version Info | No | Current version reference |
| Quick Start | No | Fast onboarding guide |
| Troubleshooting | No | FAQ and common issues |

## Anti-Patterns

**Avoid:**
- Outdated information (review regularly)
- Overly long sections (keep focused)
- Missing prerequisites
- Broken links to referenced files
- Duplicating existing documentation
- Including sensitive information

## Maintenance

### Regular Review Schedule

| Frequency | Action |
|-----------|--------|
| Weekly | Verify auto-gen counts |
| Monthly | Review key files table |
| Quarterly | Full content review |
| Per release | Update version info |
