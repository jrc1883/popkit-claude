---
name: account
description: "status | keys | billing | logout - Manage your PopKit account"
argument-hint: "<subcommand>"
---

# /popkit:account

View and manage your PopKit account.

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Show current tier, usage, and subscription status |
| `usage` | Detailed feature usage and rate limits (Issue #138) |
| `keys` | List and manage your API keys |
| `billing` | Open Stripe billing portal |
| `logout` | Clear local session/cache |

## Examples

```bash
/popkit:account           # Show account status
/popkit:account status    # Same as above
/popkit:account usage     # Detailed usage stats
/popkit:account keys      # List your API keys
/popkit:account billing   # Open billing management
/popkit:account logout    # Clear cached session
```

## Execution

### Subcommand: status (default)

Check if `POPKIT_API_KEY` is set and query the cloud API for account info.

#### Step 1: Check API Key

```python
import os

api_key = os.environ.get("POPKIT_API_KEY")
if not api_key:
    print("No POPKIT_API_KEY found. Run /popkit:upgrade to get started.")
    return
```

#### Step 2: Query Account Status

```bash
curl -s -H "Authorization: Bearer $POPKIT_API_KEY" \
  https://popkit-cloud-api.joseph-cannon.workers.dev/v1/auth/me
```

#### Step 3: Query Subscription Status

```bash
curl -s -H "Authorization: Bearer $POPKIT_API_KEY" \
  https://popkit-cloud-api.joseph-cannon.workers.dev/v1/billing/subscription
```

#### Step 4: Display Status

```markdown
## PopKit Account

**Email:** user@example.com
**Tier:** Pro ⭐
**Member since:** December 2025

### Subscription
- **Status:** Active
- **Renews:** January 9, 2026
- **Plan:** Pro ($9/month)

### Usage This Month
- API calls: 1,234 / unlimited
- Embeddings: 45 / 1,000
- Power Mode sessions: 12

### API Keys
- `pk_live_...abc` (Default Key) - Last used: 2 hours ago

Run `/popkit:account billing` to manage your subscription.
```

If no subscription or free tier:

```markdown
## PopKit Account

**Email:** user@example.com
**Tier:** Free

### Free Tier Limits
- Core workflows: ✅ Unlimited
- Power Mode: File-based only (2 agents)
- Custom MCP/skills: ❌ Premium only
- Pattern sharing: ❌ Premium only

**Upgrade to Pro** for $9/month to unlock all features.
Run `/popkit:upgrade pro` to get started.
```

---

### Subcommand: usage (Issue #138)

Show detailed feature usage and rate limits.

#### Step 1: Query Usage Summary

```bash
curl -s -H "Authorization: Bearer $POPKIT_API_KEY" \
  https://popkit-cloud-api.joseph-cannon.workers.dev/v1/usage/summary
```

#### Step 2: Display Usage

**Pro tier example:**

```markdown
## Feature Usage

**Tier:** Pro ⭐
**Period:** December 2025

### Today's Usage

| Feature | Used | Limit | Status |
|---------|------|-------|--------|
| MCP Generator | 3 | ∞ | ✅ |
| Project Embeddings | 45 | 1,000/day | ✅ |
| Pattern Sharing | 12 | ∞ | ✅ |
| Power Mode (Redis) | 5 | ∞ | ✅ |

### Monthly Totals

| Feature | This Month | Limit |
|---------|------------|-------|
| API Calls | 1,234 | ∞ |
| Project Embeddings | 456 | 10,000 |
| Total Features Used | 89 | ∞ |

### Rate Limit Status

All features within limits. ✅

Pro tier has unlimited access to most features.
```

**Free tier example:**

```markdown
## Feature Usage

**Tier:** Free
**Period:** December 2025

### Today's Usage

| Feature | Used | Limit | Status |
|---------|------|-------|--------|
| API Calls | 45 | 100/day | ✅ |
| Project Embeddings | 8 | 10/day | ⚠️ Near limit |
| Pattern Search | 15 | 20/day | ✅ |

### Upgrade Benefits

With **Pro tier** ($9/mo) you get:
- ∞ API calls
- 1,000 embeddings/day
- ∞ pattern sharing
- Hosted Power Mode (6+ agents)

Run `/popkit:upgrade` to unlock.
```

---

### Subcommand: keys

List and manage API keys.

#### Step 1: Query Keys

```bash
curl -s -H "Authorization: Bearer $POPKIT_API_KEY" \
  https://popkit-cloud-api.joseph-cannon.workers.dev/v1/account/keys
```

#### Step 2: Display Keys

```markdown
## Your API Keys

| Name | Key | Tier | Last Used |
|------|-----|------|-----------|
| Default Key | pk_live_...abc123 | Pro | 2 hours ago |
| CI Pipeline | pk_live_...def456 | Pro | 1 day ago |

### Actions
```

Then use AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "What would you like to do with your API keys?"
- header: "Keys"
- options:
  - label: "Create new key"
    description: "Generate a new API key"
  - label: "Revoke a key"
    description: "Deactivate an existing key"
  - label: "Done"
    description: "Return to main menu"
- multiSelect: false
```

---

### Subcommand: billing

Open Stripe Customer Portal for subscription management.

#### Step 1: Get Portal URL

```bash
curl -s -H "Authorization: Bearer $POPKIT_API_KEY" \
  https://popkit-cloud-api.joseph-cannon.workers.dev/v1/billing/portal
```

#### Step 2: Confirm and Open

```
Use AskUserQuestion tool with:
- question: "Open billing portal in your browser?"
- header: "Billing"
- options:
  - label: "Yes, open portal"
    description: "Manage subscription, update payment method"
  - label: "Just show URL"
    description: "Copy the URL manually"
- multiSelect: false
```

#### Step 3: Open Browser

```bash
# Cross-platform
open "{portal_url}"  # macOS
start "{portal_url}" # Windows
xdg-open "{portal_url}" # Linux
```

---

### Subcommand: logout

Clear any cached authentication.

```markdown
## Logged Out

Cleared local PopKit session cache.

Note: Your `POPKIT_API_KEY` environment variable is still set.
To fully logout, unset it:

**macOS/Linux:**
```bash
unset POPKIT_API_KEY
```

**Windows (PowerShell):**
```powershell
Remove-Item Env:POPKIT_API_KEY
```
```

## Error Handling

| Error | Response |
|-------|----------|
| No API key | "Run /popkit:upgrade to get an API key" |
| Invalid API key | "API key invalid. Get a new one at popkit.dev" |
| Network error | "Couldn't reach PopKit Cloud. Check your connection." |
| No subscription | Show free tier status with upgrade prompt |

## Related

- `/popkit:upgrade` - Upgrade to premium
- `/popkit:privacy` - Privacy and data settings
