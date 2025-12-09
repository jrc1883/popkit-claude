---
description: "status | consent | export | delete | level [strict|moderate|minimal]"
---

# /popkit:privacy - Privacy Controls

Manage your privacy settings for collective learning, including consent, data sharing preferences, and GDPR data rights.

## Usage

```
/popkit:privacy <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `status` | View current privacy settings (default) |
| `consent` | Give or revoke consent for data sharing |
| `settings` | Update privacy settings |
| `export` | Export all your data (GDPR) |
| `delete` | Delete all your data (GDPR) |

---

## Subcommand: status (default)

View current privacy settings and consent status.

```
/popkit:privacy
/popkit:privacy status
```

### Output

```
Privacy Status
==============
Consent: Given (2024-12-04)
Sharing: Enabled
Level: moderate

Settings:
  Anonymization: moderate
  Auto-delete: 90 days
  Region: us
  Excluded projects: 2
  Excluded patterns: 3

Cloud Stats:
  Insights stored: 15
  Patterns contributed: 3
  Usage this month: 2,450 tokens
```

---

## Subcommand: consent

Give or revoke consent for data sharing.

```
/popkit:privacy consent give       # Give consent
/popkit:privacy consent revoke     # Revoke consent
```

### Giving Consent

When you give consent, you acknowledge:
- Anonymized patterns may be shared with the community
- Your data is processed according to our privacy policy
- You can revoke consent at any time

### Revoking Consent

When you revoke consent:
- Data sharing is immediately disabled
- No new data will be collected
- Existing data remains until you request deletion

---

## Subcommand: settings

Update privacy settings.

```
/popkit:privacy settings level <strict|moderate|minimal>
/popkit:privacy settings exclude project <name>
/popkit:privacy settings exclude pattern <glob>
/popkit:privacy settings region <us|eu>
/popkit:privacy settings auto-delete <days>
```

### Anonymization Levels

| Level | Description |
|-------|-------------|
| `strict` | Abstract patterns only, no code snippets |
| `moderate` | Patterns + generic code (default) |
| `minimal` | More context preserved (for open source) |

### Examples

```bash
# Set strict anonymization
/popkit:privacy settings level strict

# Exclude a project from sharing
/popkit:privacy settings exclude project company-secrets

# Exclude file patterns
/popkit:privacy settings exclude pattern "*.env*"

# Set data region to EU
/popkit:privacy settings region eu

# Set auto-delete to 30 days
/popkit:privacy settings auto-delete 30
```

---

## Subcommand: export

Export all your data from PopKit Cloud (GDPR Right to Data Portability).

```
/popkit:privacy export
/popkit:privacy export --output ./my-data.json
```

### What's Exported

- All stored insights (summaries, not embeddings)
- Contributed patterns
- Usage statistics
- Privacy settings
- Consent history

### Output Format

```json
{
  "exported_at": "2024-12-04T10:30:00Z",
  "user_id": "user_abc123",
  "data": {
    "insights": { "count": 15, "summaries": {...} },
    "patterns": { "count": 3, "items": {...} },
    "usage": {...}
  }
}
```

---

## Subcommand: delete

Permanently delete all your data from PopKit Cloud (GDPR Right to be Forgotten).

```
/popkit:privacy delete
/popkit:privacy delete --confirm
```

### What's Deleted

- All stored insights and embeddings
- All contributed patterns
- Usage statistics
- Privacy settings
- Consent records

### Warning

This action is **permanent and cannot be undone**. You will be asked to confirm before deletion.

---

## Anonymization Details

### What Gets Anonymized

| Data Type | Anonymization |
|-----------|---------------|
| File paths | `project/` prefix |
| API keys | `[API_KEY]` |
| Emails | `[EMAIL]` |
| IPs | `[IP_ADDRESS]` |
| UUIDs | `[UUID]` |
| Database URLs | `[DATABASE_URL]` |

### What Never Leaves Your Machine

- Full file contents
- Credentials or secrets
- Personal identifiable info
- Project names (unless open source)
- Exact file paths

---

## Examples

```bash
# Check privacy status
/popkit:privacy

# Give consent to start sharing
/popkit:privacy consent give

# Set strict anonymization for enterprise
/popkit:privacy settings level strict

# Exclude sensitive project
/popkit:privacy settings exclude project internal-tools

# Export all data
/popkit:privacy export --output ~/popkit-data.json

# Delete all data (requires confirmation)
/popkit:privacy delete --confirm
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Privacy Module | `hooks/utils/privacy.py` |
| Cloud API | `/v1/privacy/*` endpoints |
| Settings Storage | `.claude/popkit/privacy.json` |

## Related Commands

| Command | Purpose |
|---------|---------|
| `/popkit:bug --share` | Share bug pattern (uses privacy settings) |
| `/popkit:power` | Power Mode (uses collective patterns) |
