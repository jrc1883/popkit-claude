---
name: upgrade
description: "upgrade | pro | team [--open] - Upgrade to PopKit Premium"
---

# /popkit:upgrade

Upgrade to PopKit Premium for advanced features.

## Subcommands

| Subcommand | Description |
|------------|-------------|
| (default) | Open PopKit signup/pricing page |
| `pro` | Direct link to Pro tier checkout ($9/mo) |
| `team` | Direct link to Team tier checkout ($29/mo) |

## Flags

| Flag | Description |
|------|-------------|
| `--open` | Force open in browser (default behavior) |
| `--url` | Just print the URL without opening |

## Examples

```bash
/popkit:upgrade           # Open pricing page
/popkit:upgrade pro       # Go directly to Pro checkout
/popkit:upgrade team      # Go directly to Team checkout
/popkit:upgrade --url     # Print URL without opening
```

## Execution

### Step 1: Determine Target URL

```python
import sys

subcommand = "$ARGUMENTS".strip().lower() if "$ARGUMENTS" else ""
flags = subcommand.split()

# Parse flags
url_only = "--url" in flags
plan = None
for arg in flags:
    if arg in ["pro", "team"]:
        plan = arg
        break

# Build URL
base_url = "https://popkit.dev"
if plan == "pro":
    url = f"{base_url}/checkout?plan=pro"
elif plan == "team":
    url = f"{base_url}/checkout?plan=team"
else:
    url = f"{base_url}/pricing"
```

### Step 2: Open URL or Print

If `--url` flag is present, just output the URL.

Otherwise, use AskUserQuestion to confirm and open:

```
Use AskUserQuestion tool with:
- question: "Open PopKit upgrade page in your browser?"
- header: "Upgrade"
- options:
  - label: "Yes, open in browser"
    description: "Opens {url}"
  - label: "Just show the URL"
    description: "Copy the URL manually"
- multiSelect: false
```

### Step 3: Open Browser

If user confirms, open the URL:

```bash
# Cross-platform browser open
# macOS
open "{url}"

# Windows
start "{url}"

# Linux
xdg-open "{url}"
```

### Step 4: Show Next Steps

After opening, display:

```markdown
## Next Steps

1. Complete signup at popkit.dev
2. Choose your plan and complete checkout
3. Copy your API key from the dashboard
4. Set it in your environment:

   **macOS/Linux:**
   ```bash
   export POPKIT_API_KEY=pk_live_your_key_here
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:POPKIT_API_KEY = "pk_live_your_key_here"
   ```

5. Restart Claude Code to activate premium features

Need help? Run `/popkit:account status` to check your tier.
```

## Premium Features Unlocked

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0/mo | Core workflows, file-based Power Mode |
| **Pro** | $9/mo | + Custom MCP/skills, hosted Redis, pattern sharing |
| **Team** | $29/mo | + Team coordination, analytics, priority support |

## Related

- `/popkit:account` - Manage your PopKit account
- `/popkit:account status` - Check current tier
- `/popkit:account billing` - Open billing portal
