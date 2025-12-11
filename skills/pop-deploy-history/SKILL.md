---
name: deploy-history
description: "Use to record and display deployment history - tracks versions, targets, timestamps, and rollback availability. Called automatically after deployments and on rollback --list. Free tier limited to 3 entries, Pro+ has unlimited local and cloud sync."
---

# Deployment History Tracking

## Overview

Records deployment events and provides history display for rollback capability. Integrates with cloud for Pro+ users to enable cross-device history and longer retention.

**Core principle:** Every deployment should be recoverable - track everything needed for rollback.

**Trigger:**
- Automatically after `/popkit:deploy execute`
- Manually via `/popkit:deploy rollback --list`

## Critical Rules

1. **ALWAYS record after successful deployment** - No silent deployments
2. **ALWAYS include commit hash** - Links deployment to code
3. **ALWAYS check tier for limits** - Free tier gets 3 entries max
4. **Sync to cloud for Pro+** - Enable cross-device visibility

## History Schema

### Local History (deploy.json)

```json
{
  "history": [
    {
      "id": "deploy_abc123",
      "version": "1.2.0",
      "targets": ["docker", "vercel"],
      "timestamp": "2025-12-10T15:00:00Z",
      "status": "success",
      "duration_seconds": 154,
      "commit": "abc123def456",
      "commit_message": "feat: add user authentication",
      "branch": "main",
      "rollback_available": true,
      "artifacts": {
        "docker": {
          "image": "ghcr.io/owner/repo:1.2.0",
          "digest": "sha256:abc..."
        },
        "vercel": {
          "deployment_id": "dpl_xxx",
          "url": "https://app-abc123.vercel.app"
        }
      }
    }
  ],
  "rollback_history": [
    {
      "id": "rollback_xyz789",
      "type": "rollback",
      "from_version": "1.2.0",
      "to_version": "1.1.0",
      "targets": ["docker"],
      "timestamp": "2025-12-10T16:00:00Z",
      "status": "success",
      "reason": "Performance regression detected",
      "initiated_by": "user"
    }
  ]
}
```

## Process

### Recording a Deployment

```python
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import os

def record_deployment(
    version: str,
    targets: List[str],
    status: str,
    duration_seconds: int,
    artifacts: Dict[str, Any] = None
) -> Dict:
    """Record a deployment to history."""
    deploy_path = Path(".claude/popkit/deploy.json")

    if not deploy_path.exists():
        return {"error": "No deploy.json. Run /popkit:deploy init first."}

    with open(deploy_path) as f:
        config = json.load(f)

    # Get git info
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True
    ).stdout.strip()[:12]

    commit_msg = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        capture_output=True, text=True
    ).stdout.strip()

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True
    ).stdout.strip()

    # Create history entry
    entry = {
        "id": f"deploy_{commit}_{int(datetime.now().timestamp())}",
        "version": version,
        "targets": targets,
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "duration_seconds": duration_seconds,
        "commit": commit,
        "commit_message": commit_msg,
        "branch": branch,
        "rollback_available": status == "success",
        "artifacts": artifacts or {}
    }

    # Apply tier limits
    tier = get_user_tier()
    max_entries = 3 if tier == "free" else None  # Pro+ unlimited

    history = config.setdefault("history", [])
    history.insert(0, entry)  # Newest first

    if max_entries and len(history) > max_entries:
        # Remove oldest entries for free tier
        removed = history[max_entries:]
        history = history[:max_entries]
        config["history"] = history
        print(f"Note: Free tier limited to {max_entries} entries. Removed {len(removed)} old entries.")

    # Update last_deployment
    config["last_deployment"] = {
        "version": version,
        "timestamp": entry["timestamp"],
        "status": status
    }

    with open(deploy_path, "w") as f:
        json.dump(config, f, indent=2)

    # Sync to cloud for Pro+
    if tier in ["pro", "team"]:
        sync_to_cloud(entry, tier)

    return entry

def get_user_tier() -> str:
    """Get user's subscription tier."""
    api_key = os.environ.get("POPKIT_API_KEY")
    if not api_key:
        return "free"
    # In production, verify with cloud API
    return "pro"  # Assume Pro if key exists
```

### Displaying History

```python
def display_history(target: str = None, limit: int = 10) -> str:
    """Format deployment history for display."""
    deploy_path = Path(".claude/popkit/deploy.json")

    if not deploy_path.exists():
        return "No deployment history. Run /popkit:deploy init first."

    with open(deploy_path) as f:
        config = json.load(f)

    history = config.get("history", [])

    if not history:
        return "No deployments recorded yet."

    if target:
        history = [h for h in history if target in h.get("targets", [])]

    history = history[:limit]

    # Build table
    lines = [
        "## Deployment History",
        "",
        "| Version | Target | Deployed | Status | Duration | Commit |",
        "|---------|--------|----------|--------|----------|--------|"
    ]

    from datetime import datetime as dt

    for i, entry in enumerate(history):
        ts = dt.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
        ago = format_time_ago(ts)
        targets = ", ".join(entry.get("targets", []))
        duration = format_duration(entry.get("duration_seconds", 0))
        commit = entry.get("commit", "")[:7]
        status = "✓" if entry["status"] == "success" else "✗"

        current = " (current)" if i == 0 else ""

        lines.append(
            f"| **{entry['version']}**{current} | {targets} | {ago} | {status} | {duration} | {commit} |"
        )

    # Add rollback info
    current = history[0] if history else None
    available = sum(1 for h in history[1:] if h.get("rollback_available"))

    lines.extend([
        "",
        f"**Current:** v{current['version']} ({', '.join(current['targets'])})" if current else "",
        f"**Rollback points:** {available}",
        "",
        "To rollback: `/popkit:deploy rollback --to <version>`"
    ])

    return "\n".join(lines)

def format_time_ago(ts) -> str:
    """Format timestamp as relative time."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    delta = now - ts

    if delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600}h ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60}m ago"
    else:
        return "just now"

def format_duration(seconds: int) -> str:
    """Format duration for display."""
    if seconds > 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"
```

### Cloud Sync (Pro+)

```python
import requests

def sync_to_cloud(entry: Dict, tier: str):
    """Sync deployment history to PopKit Cloud."""
    api_key = os.environ.get("POPKIT_API_KEY")
    if not api_key:
        return

    retention_days = 7 if tier == "pro" else 90  # Team gets 90 days

    try:
        response = requests.post(
            "https://popkit-cloud-api.joseph-cannon.workers.dev/v1/deployments",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "entry": entry,
                "retention_days": retention_days
            },
            timeout=10
        )

        if response.ok:
            print("✓ Synced to PopKit Cloud")
        else:
            print(f"⚠️ Cloud sync failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Cloud sync unavailable: {e}")

def fetch_cloud_history(limit: int = 20) -> List[Dict]:
    """Fetch deployment history from cloud."""
    api_key = os.environ.get("POPKIT_API_KEY")
    if not api_key:
        return []

    try:
        response = requests.get(
            "https://popkit-cloud-api.joseph-cannon.workers.dev/v1/deployments",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": limit},
            timeout=10
        )

        if response.ok:
            return response.json().get("deployments", [])
    except Exception:
        pass

    return []
```

## Output Format

### Full History Display

```
## Deployment History

| Version | Target | Deployed | Status | Duration | Commit |
|---------|--------|----------|--------|----------|--------|
| **1.2.0** (current) | docker | 30m ago | ✓ | 1m 23s | abc123 |
| **1.1.0** | docker | 2h ago | ✓ | 1m 15s | def456 |
| **1.0.5** | docker, vercel | 3d ago | ✓ | 2m 45s | ghi789 |
| **1.0.4** | docker, vercel | 5d ago | ✓ | 2m 30s | jkl012 |
| **1.0.3** | vercel | 7d ago | ✓ | 45s | mno345 |

**Current:** v1.2.0 (docker)
**Rollback points:** 4

To rollback: `/popkit:deploy rollback --to <version>`
```

### After Recording

```
Deployment Recorded
═══════════════════

Version: 1.2.0
Targets: docker, vercel
Status: success
Duration: 1m 23s
Commit: abc123 (feat: add user authentication)

✓ History updated (5 entries)
✓ Synced to PopKit Cloud (Pro)
✓ Rollback point saved

View history: /popkit:deploy rollback --list
```

### Free Tier Limit Warning

```
Deployment Recorded
═══════════════════

Version: 1.2.0
Targets: docker
Status: success

⚠️ Free tier history limit (3 entries)
   Removed 1 old entry to make room.

Upgrade to Pro ($9/mo) for:
  - Unlimited local history
  - 7-day cloud history
  - Cross-device sync

Run /popkit:upgrade to unlock.
```

## Tier Limits

| Feature | Free | Pro ($9/mo) | Team ($29/mo) |
|---------|------|-------------|---------------|
| Local entries | 3 | Unlimited | Unlimited |
| Cloud sync | No | Yes | Yes |
| Cloud retention | - | 7 days | 90 days |
| Cross-device | No | Yes | Yes |
| Export history | No | Yes | Yes |

## Integration

**Automatically called by:**
- `pop-deploy-docker` after Docker deployment
- `pop-deploy-vercel` after Vercel deployment
- `pop-deploy-npm` after npm publish
- `pop-deploy-github-releases` after release creation

**Used by:**
- `pop-deploy-rollback` to find rollback points
- `/popkit:routine morning` to show deployment age

**Related Skills:**
| Skill | Relationship |
|-------|--------------|
| `pop-deploy-rollback` | Uses history for version selection |
| `pop-deploy-init` | Creates initial deploy.json structure |

## Error Handling

| Error | Response |
|-------|----------|
| No deploy.json | "Run /popkit:deploy init first" |
| Write failed | "Could not update history. Check permissions." |
| Cloud sync failed | "Local history saved. Cloud sync will retry." |
| Tier limit hit | "Free tier limit reached. Oldest entry removed." |
