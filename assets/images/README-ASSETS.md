# PopKit Visual Assets

This directory contains visual assets for the README and documentation.

## Current Assets

| Asset | Status | Description |
|-------|--------|-------------|
| `popkit-banner.png` | Placeholder | Main banner with bubblegum aesthetic |
| `before-after.gif` | Pending | Hero GIF showing workflow transformation |
| `morning-routine.gif` | Pending | Demo of morning routine |
| `power-mode.gif` | Pending | Demo of multi-agent collaboration |
| `dev-workflow.gif` | Pending | Demo of development workflow |

## Generating GIFs

GIFs are generated from VHS tape files in `../tapes/`:

```bash
# Install VHS
brew install vhs  # macOS
# or see https://github.com/charmbracelet/vhs

# Generate a GIF
cd packages/plugin/assets/tapes
vhs morning-routine.tape
```

## Design Guidelines

**Color Palette (Bubblegum):**
- Primary: `#F5A3C7` (soft pink)
- Secondary: `#A78BFA` (purple)
- Accent: `#5EEAD4` (teal)
- Background: Dark terminal theme

**Style:**
- Charmbracelet-inspired playful aesthetic
- Clean terminal recordings
- Minimal text, let visuals demonstrate
