---
name: pop-waitlist-signup
description: "Captures email addresses for the premium features waitlist. Used during pre-launch to collect interested users. Do NOT use directly - invoked when user selects 'Get notified at launch' option."
---

# Waitlist Signup Skill

## Overview

Collects email addresses from users interested in premium features during pre-launch phase. Simple, non-intrusive flow that captures email right in the console.

**Core principle:** Make it incredibly easy to stay updated. No external forms, no browser redirects - just type your email and done.

**Trigger:** Called when user selects "Get notified at launch" from premium feature prompt.

## Arguments

| Argument | Description |
|----------|-------------|
| `feature_name` | The premium feature they're interested in |
| `required_tier` | Tier that will be required (pro, team) |

## Execution

### Step 1: Show Coming Soon Message

```markdown
## 🎉 Coming Soon: {feature_name}

This premium feature is launching soon and will be available in the **{required_tier}** tier.

We'll send you one email when premium features launch - no spam, just a heads up when it's ready.
```

### Step 2: Prompt for Email

Use AskUserQuestion for email input:

```
Use AskUserQuestion tool with:
- question: "Enter your email to get notified at launch:"
- header: "Email"
- options:
  - label: "Enter email address"
    description: "We'll notify you when premium features launch"
  - label: "Skip"
    description: "Continue without signing up"
- multiSelect: false
```

### Step 3: Capture Email

If user enters email (didn't select "Skip"):

**Validate email format:**
```python
import re

email = user_input.strip()
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

if not re.match(email_pattern, email):
    print("⚠️  Invalid email format. Please try again.")
    # Show prompt again
```

**Send to waitlist API:**
```bash
# Use the premium_checker utility
python3 packages/plugin/hooks/utils/premium_checker.py waitlist "{email}" "{feature_name}"
```

### Step 4: Confirm Signup

**If successful:**
```markdown
✅ **Thanks for signing up!**

We'll email you at **{email}** when premium features launch.

You can continue using PopKit's free tier in the meantime.
```

**If failed (network error, etc.):**
```markdown
⚠️ **Couldn't save your email right now.**

Try again later, or email us directly at:
**premium@popkit.dev**

We'll make sure you're on the list!
```

### Step 5: Return to User

After signup (success or failure), return control to user without further prompting.

## Privacy Note

The skill should mention:
- Emails are only used for launch notification
- No spam, marketing, or third-party sharing
- Can unsubscribe anytime
- Stored securely in PopKit Cloud

## Example Flow

**User tries:** `/popkit:project generate` (requires Pro)

**Hook detects:** Pre-launch mode, user is free tier

**Upgrade prompt shows:**
```
🎉 Coming Soon: Custom MCP Server Generation

This premium feature is launching soon. What would you like to do?

[1] Continue with free tier - Basic project analysis available (no custom MCP)
[2] Get notified at launch - Enter your email to stay updated
[3] Cancel - Return without using this feature
```

**User selects:** [2] Get notified at launch

**This skill runs:**
```
Enter your email to get notified at launch:

> user@example.com

✅ Thanks for signing up!

We'll email you at user@example.com when premium features launch.
```

## Related

- `hooks/utils/premium_checker.py` - Waitlist API integration
- `pop-upgrade-prompt` - Full upgrade flow (when billing is live)
- `/popkit:account` - Account management
