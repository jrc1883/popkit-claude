---
name: readme-builder
description: "Generate compelling, well-structured README files following awesome-readme patterns. Analyzes project structure, extracts key information, and creates READMEs with progressive disclosure, visual elements, and beginner-friendly narratives. Use when creating a new project README, overhauling an existing one, or when a README feels stale or overwhelming."
inputs:
  - from: any
    field: project_path
    required: false
outputs:
  - field: readme_path
    type: file_path
  - field: assets_needed
    type: list
next_skills:
  - pop-doc-sync
---

# README Builder

## Overview

Generate professional, compelling README files that follow awesome-readme best practices. Creates READMEs with:
- Hero sections with visual elements
- Progressive disclosure (beginners first, depth for advanced)
- Clear installation and quick start
- Auto-generated sections where appropriate

**Announce at start:** "I'm using the README builder skill to create/update your project's README."

## The Process

### Step 1: Project Analysis

Gather project context:

```bash
# Check package.json or similar
cat package.json 2>/dev/null | head -30
cat pyproject.toml 2>/dev/null | head -30
cat Cargo.toml 2>/dev/null | head -20

# Check existing README
cat README.md 2>/dev/null | head -50

# Check project structure
ls -la
ls src/ 2>/dev/null || ls lib/ 2>/dev/null
```

Extract:
- Project name and description
- Language/framework
- Key dependencies
- Existing documentation style
- Installation method (npm, pip, cargo, etc.)

### Step 2: User Input via AskUserQuestion

**Project Type:**
```
Use AskUserQuestion tool with:
- question: "What type of project is this?"
- header: "Type"
- options:
  - label: "CLI Tool"
    description: "Command-line application"
  - label: "Library/SDK"
    description: "Reusable package for developers"
  - label: "Web App"
    description: "Website or web application"
  - label: "Plugin"
    description: "Extension for another platform"
- multiSelect: false
```

**Target Audience:**
```
Use AskUserQuestion tool with:
- question: "Who is the primary audience?"
- header: "Audience"
- options:
  - label: "Beginners"
    description: "New developers, needs hand-holding"
  - label: "Intermediate"
    description: "Knows basics, needs clear docs"
  - label: "Advanced"
    description: "Experts, wants concise reference"
  - label: "Mixed"
    description: "All skill levels"
- multiSelect: false
```

**Visual Style:**
```
Use AskUserQuestion tool with:
- question: "What visual style do you prefer?"
- header: "Style"
- options:
  - label: "Minimal (Recommended)"
    description: "Badges, clean formatting, no heavy graphics"
  - label: "Visual-rich"
    description: "Banner, GIFs, diagrams"
  - label: "Text-only"
    description: "Pure markdown, no images"
- multiSelect: false
```

### Step 3: Structure Selection

Based on project type, select appropriate structure:

**CLI Tool Template:**
```
1. Hero (name + badges + tagline)
2. Demo GIF/screenshot
3. Quick Install (one-liner)
4. Usage Examples (3 common commands)
5. All Commands (collapsible)
6. Configuration
7. FAQ (collapsible)
8. Contributing + License
```

**Library Template:**
```
1. Hero (name + badges + tagline)
2. Why This Library (value prop)
3. Install
4. Quick Start (code example)
5. API Reference (brief + link)
6. Examples (collapsible)
7. Contributing + License
```

**Web App Template:**
```
1. Hero (name + badges)
2. Screenshot/Demo
3. Features (bullet points)
4. Getting Started (local dev)
5. Deployment
6. Tech Stack
7. Contributing + License
```

**Plugin Template:**
```
1. Hero (platform badge + name)
2. What It Does (one paragraph)
3. Install (platform-specific)
4. Quick Start (3 commands)
5. Features/Commands
6. Configuration
7. FAQ
8. Contributing + License
```

### Step 4: Generate Content

For each section, follow these principles:

**Hero Section:**
- Center-aligned logo (if available) or text-based banner
- Badges: version, license, platform, downloads (if applicable)
- One-line tagline (action-oriented)

```markdown
<p align="center">
  <img src="assets/logo.png" alt="Project Name" width="200">
</p>

<h1 align="center">Project Name</h1>

<p align="center">
  <strong>One-line tagline that explains the value</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-X.Y.Z-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>
```

**Installation:**
- Show the simplest path first
- Platform-specific tabs if needed
- Note any prerequisites

**Quick Start:**
- 3 commands maximum
- Show output where helpful
- Link to full docs for more

**Progressive Disclosure:**
- Use `<details>` for advanced content
- Keep main README scannable
- Link to separate docs for deep dives

```markdown
<details>
<summary><strong>Advanced Configuration</strong></summary>

[Detailed content here]

</details>
```

### Step 5: Visual Assets Checklist

After generating README, list needed assets:

| Asset | Purpose | Suggested Tool |
|-------|---------|----------------|
| Logo | Brand identity | Figma, Canva, or text-based |
| Banner | Hero section | Same as logo |
| Demo GIF | Show functionality | asciinema, ScreenToGif, VHS |
| Architecture diagram | System overview | Mermaid, Excalidraw |

Output:
```
Assets Needed:
- [ ] Logo (optional): assets/logo.png
- [ ] Demo GIF (recommended): assets/demo.gif
- [ ] Badges: Auto-generated via shields.io

You can create the README now and add visuals later.
```

### Step 6: Write and Validate

Write README:
```bash
# Backup existing if present
cp README.md README.md.backup 2>/dev/null

# Write new README (use Write tool)
```

Validate:
- All links work (no broken references)
- Code examples are syntactically correct
- Installation commands are accurate
- No placeholder text remaining

### Step 7: Completion

Offer next steps via AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "README created. What's next?"
- header: "Next Step"
- options:
  - label: "Commit it"
    description: "Save to git with commit message"
  - label: "Create assets"
    description: "Help me create the visual assets"
  - label: "Review first"
    description: "I'll review and get back to you"
  - label: "Done"
    description: "That's all for now"
- multiSelect: false
```

## Best Practices

### DO:
- Start with "what problem does this solve?"
- Show, don't tell (demos > descriptions)
- Keep main README under 500 lines
- Use consistent formatting
- Include "quick win" examples
- Link to detailed docs

### DON'T:
- List every feature exhaustively
- Use jargon without explanation
- Include outdated screenshots
- Leave placeholder text
- Over-promise capabilities
- Forget to update version badges

## Auto-Generated Sections

For projects with predictable structure, use AUTO-GEN markers:

```markdown
<!-- AUTO-GEN:COMMANDS START -->
| Command | Description |
|---------|-------------|
...
<!-- AUTO-GEN:COMMANDS END -->
```

These can be updated by CI or doc-sync tools.

## Examples of Excellence

Study these for inspiration:
- **Aider** - Screencast SVG, testimonials, icon+paragraph features
- **Claude Code** - Strategic minimalism, demo GIF, 4 install methods
- **Fiber** - Philosophy section, benchmarks, progressive examples
- **Continue** - Multiple use-case GIFs, quick install

## Output Format

The skill produces:
1. `README.md` - The main README file
2. `assets_needed.md` (optional) - List of visual assets to create
3. Git commit (if requested)
