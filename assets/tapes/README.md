# VHS Tapes Directory

This directory contains VHS tape definitions for generating animated GIF demonstrations of PopKit features.

## Directory Structure

```
tapes/
├── core-features/          # Essential PopKit features
│   ├── slash-command-discovery/
│   ├── morning-routine/
│   └── before-after/
├── workflows/              # Multi-phase workflows (future)
│   ├── 7-phase-feature-dev/
│   ├── power-mode-collaboration/
│   └── git-workflow/
├── agents/                 # Agent demonstrations (future)
│   ├── bug-whisperer-demo/
│   ├── code-reviewer-demo/
│   └── security-audit-demo/
└── integration/            # Integration demos (future)
    ├── github-integration/
    ├── mcp-server-demo/
    └── cloud-sync-demo/
```

## Tape Directory Format

Each tape directory follows this structure:

```
feature-name/
├── screenshots/           # Source of truth screenshots
│   ├── 01-step-one.png
│   ├── 02-step-two.png
│   └── README.md          # Screenshot capture instructions
├── metadata.json          # Tape configuration and screenshot metadata
└── feature-name.tape      # VHS tape definition
```

## Creating a New Demo

### 1. Create Directory Structure

```bash
mkdir -p packages/plugin/assets/tapes/{category}/{feature-name}/screenshots
```

### 2. Capture Screenshots

Follow the instructions in the `screenshots/README.md` template. Capture each step of the feature workflow.

### 3. Create metadata.json

```json
{
  "name": "Feature Name",
  "description": "Brief description of what this demo shows",
  "category": "core-features",
  "output_file": "feature-name.gif",
  "dimensions": {"width": 900, "height": 600},
  "theme": "Catppuccin Mocha",
  "font_size": 14,
  "padding": 20,
  "screenshots": [
    {
      "filename": "01-step-one.png",
      "description": "What this screenshot shows",
      "timing": "0ms",
      "notes": "Additional context"
    }
  ],
  "key_insights": ["Insight 1", "Insight 2"],
  "readme_sections": ["Where this appears"],
  "tags": ["tag1", "tag2"]
}
```

### 4. Write VHS Tape

Create the `.tape` file following VHS syntax:

```tape
# Feature Name Demo
# Description

Output ../../../images/feature-name.gif

Set FontSize 14
Set Width 900
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20

Type "your commands here"
Sleep 500ms
Enter
```

### 5. Generate GIF

```bash
cd packages/plugin/assets/tapes/{category}/{feature-name}
vhs feature-name.tape
```

The GIF will be generated in `packages/plugin/assets/images/`.

## VHS Tape Guidelines

### What VHS Can Do

✅ Simulate terminal input/output
✅ Control timing precisely
✅ Create reproducible GIFs
✅ Show typing animations
✅ Display terminal output

### What VHS Cannot Do

❌ Show GUI dropdowns/menus
❌ Capture mouse interactions
❌ Display non-terminal UI
❌ Show multiple windows
❌ Interactive elements (buttons, links)

### Workarounds

For features requiring GUI elements (like dropdowns):
1. **Annotated screenshots** - Add arrows and labels to screenshots
2. **ASCII art simulation** - Show concept in terminal using ASCII
3. **Hybrid approach** - Screenshot for UI, VHS for execution

See [RESEARCH-VHS-SCREENSHOT-SYSTEM.md](../../../../RESEARCH-VHS-SCREENSHOT-SYSTEM.md) for detailed guidance.

## Current Demos

### Core Features

| Demo | Status | Output | README Section |
|------|--------|--------|----------------|
| **slash-command-discovery** | 🟡 Awaiting screenshots | `slash-command-discovery.gif` | Quick Start |
| **morning-routine** | ✅ Active | `morning-routine.gif` | Features > Day Routines |
| **before-after** | ✅ Active | `before-after.gif` | Hero Section |

### Planned Demos

- [ ] 7-phase feature development workflow
- [ ] Power Mode multi-agent collaboration
- [ ] Git workflow (commit, pr, release)
- [ ] Bug-whisperer agent in action
- [ ] Security audit demonstration
- [ ] Project initialization and analysis

## Installing VHS

```bash
# macOS
brew install vhs

# Other platforms
# See https://github.com/charmbracelet/vhs
```

## Future: Automated Generation

**Roadmap:** PopKit v2.0 will include `/popkit:vhs` commands for automated tape generation:

```bash
# Analyze screenshots and generate metadata
/popkit:vhs analyze packages/plugin/assets/tapes/core-features/feature-name/

# Generate VHS tape from metadata
/popkit:vhs generate packages/plugin/assets/tapes/core-features/feature-name/

# Regenerate all tapes with changed screenshots
/popkit:vhs regenerate --changed

# Generate from video recording
/popkit:vhs from-video ~/Desktop/demo.mp4 --output feature-name
```

See [RESEARCH-VHS-SCREENSHOT-SYSTEM.md](../../../../RESEARCH-VHS-SCREENSHOT-SYSTEM.md) for the full research proposal.

## Design Guidelines

**Color Palette (Bubblegum):**
- Primary: `#F5A3C7` (soft pink)
- Secondary: `#A78BFA` (purple)
- Accent: `#5EEAD4` (teal)
- Background: Dark terminal theme (Catppuccin Mocha)

**Style:**
- Charmbracelet-inspired playful aesthetic
- Clean terminal recordings
- Minimal text, let visuals demonstrate
- Consistent timing and pacing

**Typography:**
- Font size: 14px (readable at 900x600)
- Monospace font from terminal theme
- Clear contrast for readability

## Questions?

For detailed documentation on the screenshot-driven VHS system:
- See [RESEARCH-VHS-SCREENSHOT-SYSTEM.md](../../../../RESEARCH-VHS-SCREENSHOT-SYSTEM.md)
- Check screenshot capture instructions in each `screenshots/README.md`
- Review existing tapes in `core-features/` for examples

---

**Last updated:** 2025-12-12
