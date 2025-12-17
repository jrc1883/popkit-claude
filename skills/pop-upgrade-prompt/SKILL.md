---
name: pop-upgrade-prompt
description: "Shows a graceful upgrade prompt when a user attempts to use a premium feature without the required tier. Uses AskUserQuestion for interactive selection. Do NOT use directly - this is invoked by the gating hook when premium features are accessed."
---

# Upgrade Prompt Skill

## Overview

Shows a graceful, interactive upgrade prompt when free tier users attempt to use premium features. Offers upgrade option and free tier fallback when available.

**Core principle:** Be helpful, not hostile. Show users what they're missing without blocking their workflow.

**Trigger:** Called by `pre-tool-use` hook when gating check fails.

## Arguments

| Argument | Description |
|----------|-------------|
| `feature_name` | The premium feature being accessed |
| `feature_description` | What the feature does |
| `required_tier` | Tier required (pro, team) |
| `user_tier` | User's current tier |
| `fallback` | Optional free tier alternative |

## Execution

### Step 1: Build Upgrade Message

```markdown
## ⭐ Premium Feature Required

**{feature_name}**

{feature_description}

| Your Tier | Required Tier |
|-----------|---------------|
| {user_tier} | {required_tier} |
```

### Step 2: Show Interactive Options

Use AskUserQuestion for selection:

```
Use AskUserQuestion tool with:
- question: "This feature requires {required_tier}. What would you like to do?"
- header: "Premium"
- options:
  - label: "Upgrade to {required_tier}"
    description: "Unlock this feature and more (${price}/mo)"
  - label: "Continue with free tier" (if fallback available)
    description: "{fallback}"
  - label: "Cancel"
    description: "Return without using this feature"
- multiSelect: false
```

### Step 3: Handle Selection

**If "Upgrade":**
```
Execute /popkit:upgrade {required_tier}
```

**If "Continue with free tier":**
```markdown
Using free tier alternative: {fallback}

Note: Some capabilities will be limited.
Run `/popkit:upgrade` anytime to unlock full features.
```
Then continue with the limited workflow.

**If "Cancel":**
```markdown
Cancelled. Run `/popkit:upgrade` when you're ready to unlock premium features.
```

## Premium Features Reference

| Feature | Tier | Price | Free Fallback |
|---------|------|-------|---------------|
| Custom MCP servers | Pro | $9/mo | Basic project analysis |
| Custom skills | Pro | $9/mo | View existing skills |
| Custom routines | Pro | $9/mo | Default routines |
| Multi-project dashboard | Pro | $9/mo | Single project |
| Pattern sharing | Pro | $9/mo | Search only |
| Project embeddings | Pro | $9/mo | Basic search |
| Hosted Power Mode | Pro | $9/mo | File-based (2-3 agents) |
| Team coordination | Team | $29/mo | None |
| Team analytics | Team | $29/mo | None |

## Example Flow

**User runs:** `/popkit:project generate`

**Gating hook detects:** User is free tier, feature requires Pro

**This skill shows:**

```
## ⭐ Premium Feature Required

**Custom MCP Server Generation**

Generate project-specific MCP servers with semantic search,
custom health checks, and project-aware tooling.

| Your Tier | Required Tier |
|-----------|---------------|
| Free | Pro |

[AskUserQuestion appears with options]
```

**User selects:** "Continue with free tier"

**Result:**
```
Using free tier alternative: Basic project analysis available (no custom MCP)

Analyzing project structure...
[continues with limited analysis]
```

## Related

- `hooks/utils/premium_checker.py` - Entitlement checking logic
- `/popkit:upgrade` - Upgrade command
- `/popkit:account` - Account management
