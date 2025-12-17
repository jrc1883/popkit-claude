---
name: deploy-rollback
description: "Use when a deployment needs to be reverted - rolls back to a previous version with health verification. Premium feature (Pro+). Supports Docker, Vercel, and npm targets. Shows deployment history and confirms rollback before execution."
---

# Deployment Rollback

## Overview

Safely revert deployments to a previous version with verification. Premium feature requiring Pro or Team subscription.

**Core principle:** Rollback should be safer than deploying forward - verify before and after.

**Trigger:** `/popkit:deploy rollback` command

## Critical Rules

1. **ALWAYS check tier before rollback** - Free tier shows upgrade prompt
2. **ALWAYS show history first** - Let user see what they're rolling back to
3. **ALWAYS verify after rollback** - Health checks are mandatory
4. **NEVER rollback npm without warning** - Package unpublish has 24h limit
5. **NEVER rollback GitHub Releases** - They are immutable

## Premium Gating

```python
import os

def check_rollback_access():
    """Check if user has Pro+ tier for rollback."""
    api_key = os.environ.get("POPKIT_API_KEY")

    if not api_key:
        return {
            "allowed": False,
            "reason": "no_key",
            "message": "Rollback requires Pro subscription. Run /popkit:upgrade to get started."
        }

    # Check tier via cloud API
    # For now, any API key = Pro access
    return {"allowed": True, "tier": "pro"}
```

If not allowed, use AskUserQuestion:

```
Use AskUserQuestion tool with:
- question: "Rollback is a Pro feature. Would you like to upgrade?"
- header: "Upgrade"
- options:
  - label: "View upgrade options"
    description: "See Pro benefits and pricing ($9/mo)"
  - label: "Not now"
    description: "Continue without rollback capability"
- multiSelect: false
```

## Process

### Step 1: Load Deployment History

```python
import json
from pathlib import Path
from datetime import datetime

def load_deployment_history(target: str = None):
    """Load deployment history from deploy.json."""
    deploy_path = Path(".claude/popkit/deploy.json")

    if not deploy_path.exists():
        return {"error": "No deployment configuration found. Run /popkit:deploy init first."}

    with open(deploy_path) as f:
        config = json.load(f)

    history = config.get("history", [])

    if target:
        history = [h for h in history if target in h.get("targets", [])]

    # Filter to entries with rollback_available
    rollback_points = [h for h in history if h.get("rollback_available", False)]

    return {
        "current": config.get("last_deployment"),
        "history": rollback_points,
        "target_configs": config.get("target_configs", {})
    }
```

### Step 2: Display History

If called with `--list` flag, show history and exit:

```markdown
## Deployment History

| Version | Target | Deployed | Status | Duration | Rollback |
|---------|--------|----------|--------|----------|----------|
| **1.2.0** | docker | 30m ago | success | 1m 23s | Current |
| 1.1.0 | docker | 2h ago | success | 1m 15s | Available |
| 1.0.5 | docker | 3d ago | success | 1m 08s | Available |
| 1.0.4 | docker, vercel | 5d ago | success | 2m 45s | Available |

**Current deployment:** v1.2.0 (docker)
**Rollback points available:** 3

To rollback: `/popkit:deploy rollback --to 1.1.0`
```

### Step 3: Present Rollback Options

```
Use AskUserQuestion tool with:
- question: "Which version would you like to rollback to?"
- header: "Rollback"
- options:
  - label: "v1.1.0 (2 hours ago)"
    description: "Last stable version before current deployment"
  - label: "v1.0.5 (3 days ago)"
    description: "Stable for 72+ hours before v1.1.0"
  - label: "Cancel"
    description: "Don't rollback, keep current version"
- multiSelect: false
```

### Step 4: Confirm Rollback

```
Use AskUserQuestion tool with:
- question: "Confirm rollback from v1.2.0 to v1.1.0? This will affect: docker"
- header: "Confirm"
- options:
  - label: "Yes, rollback now"
    description: "Revert to v1.1.0 and run health checks"
  - label: "No, cancel"
    description: "Keep current v1.2.0 deployment"
- multiSelect: false
```

### Step 5: Execute Rollback Per Target

#### Docker Rollback

```bash
# Re-tag previous image as latest
docker pull ghcr.io/owner/repo:1.1.0
docker tag ghcr.io/owner/repo:1.1.0 ghcr.io/owner/repo:latest
docker push ghcr.io/owner/repo:latest

# If using Kubernetes
kubectl set image deployment/app app=ghcr.io/owner/repo:1.1.0
kubectl rollout status deployment/app
```

#### Vercel Rollback

```bash
# Get previous deployment ID
vercel rollback --yes

# Or specific deployment
vercel rollback <deployment-id> --yes
```

#### npm Rollback (Warning Required)

**IMPORTANT:** npm has strict unpublish rules:
- Within 24 hours: Can unpublish entirely
- After 24 hours: Can only deprecate

```
Use AskUserQuestion tool with:
- question: "npm package unpublish has restrictions. How would you like to proceed?"
- header: "npm Rollback"
- options:
  - label: "Deprecate v1.2.0 (Recommended)"
    description: "Mark as deprecated, users see warning but can still install"
  - label: "Unpublish v1.2.0"
    description: "Remove entirely (only if published <24h ago)"
  - label: "Cancel"
    description: "Keep current version published"
- multiSelect: false
```

```bash
# Deprecate (always available)
npm deprecate my-package@1.2.0 "Please use v1.1.0 - rollback due to issues"

# Unpublish (24h limit)
npm unpublish my-package@1.2.0
```

### Step 6: Verify Rollback

```python
def verify_rollback(target: str, version: str):
    """Run post-rollback health checks."""
    checks = {
        "docker": verify_docker_rollback,
        "vercel": verify_vercel_rollback,
        "npm": verify_npm_rollback
    }

    if target in checks:
        return checks[target](version)
    return {"status": "skipped", "reason": f"No verification for {target}"}

def verify_docker_rollback(version: str):
    """Verify Docker rollback succeeded."""
    import subprocess

    # Check running container version
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Config.Image}}", "app"],
        capture_output=True, text=True
    )

    if version in result.stdout:
        return {"status": "success", "message": f"Container running {version}"}
    return {"status": "warning", "message": "Container version mismatch"}

def verify_vercel_rollback(version: str):
    """Verify Vercel rollback via health check."""
    import requests

    # Get deployment URL from vercel.json or config
    url = "https://your-app.vercel.app/api/health"

    try:
        response = requests.get(url, timeout=10)
        if response.ok:
            return {"status": "success", "message": "Health check passed"}
        return {"status": "warning", "message": f"Health returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Step 7: Update History

```python
def record_rollback(target: str, from_version: str, to_version: str, status: str):
    """Record rollback in deployment history."""
    deploy_path = Path(".claude/popkit/deploy.json")

    with open(deploy_path) as f:
        config = json.load(f)

    rollback_entry = {
        "type": "rollback",
        "from_version": from_version,
        "to_version": to_version,
        "targets": [target],
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "initiated_by": "popkit-deploy"
    }

    config.setdefault("rollback_history", []).append(rollback_entry)
    config["last_deployment"] = {
        "version": to_version,
        "timestamp": datetime.now().isoformat(),
        "status": "rollback",
        "from_version": from_version
    }

    with open(deploy_path, "w") as f:
        json.dump(config, f, indent=2)
```

## Output Format

### Successful Rollback

```
Rollback Deployment
═══════════════════

[1/4] Checking access...
      ✓ Pro tier verified

[2/4] Loading history...
      ✓ Current: v1.2.0 (docker)
      ✓ Available: 3 rollback points

[3/4] Executing rollback...
      Target: docker
      From: v1.2.0
      To: v1.1.0

      → Re-tagging image...
      ✓ ghcr.io/owner/repo:1.1.0 → latest
      → Updating deployment...
      ✓ Pods rolling (3/3 ready)

[4/4] Verifying...
      ✓ Health check passed
      ✓ All endpoints responding

Rollback Complete!
══════════════════

Rolled back: v1.2.0 → v1.1.0
Target: docker
Duration: 45s
Status: Success

Note: v1.2.0 is still available in registry.
      Redeploy with: /popkit:deploy execute docker --version 1.2.0
```

### Failed Rollback

```
Rollback Deployment
═══════════════════

[1/4] Checking access...
      ✓ Pro tier verified

[2/4] Loading history...
      ✓ Current: v1.2.0 (docker)

[3/4] Executing rollback...
      → Re-tagging image...
      ✓ Image tagged
      → Updating deployment...
      ✗ Deployment failed: ImagePullBackOff

Rollback Failed
═══════════════

Error: Could not pull image ghcr.io/owner/repo:1.1.0
Reason: Image may have been deleted from registry

Recovery options:
  1. Check registry for available tags
  2. Rollback to an older version: /popkit:deploy rollback --to 1.0.5
  3. Deploy a new fix: /popkit:deploy execute docker
```

### No History Available

```
Rollback Deployment
═══════════════════

[1/4] Checking access...
      ✓ Pro tier verified

[2/4] Loading history...
      ⚠️ No deployment history found

No rollback points available.

This can happen if:
  - This is the first deployment
  - History was cleared
  - deploy.json was reset

Next steps:
  1. Deploy a new version: /popkit:deploy execute
  2. Check git history for previous releases
```

## Rollback Per Target

| Target | Method | Reversible | Notes |
|--------|--------|------------|-------|
| Docker | Re-tag image, restart | Yes | Image stays in registry |
| Vercel | `vercel rollback` | Yes | All deployments preserved |
| Netlify | Redeploy from git | Yes | Can publish any commit |
| npm | Deprecate or unpublish | Partial | 24h unpublish limit |
| PyPI | Cannot rollback | No | Only deprecation possible |
| GitHub Releases | Cannot rollback | No | Releases are immutable |

## History Limits

| Tier | Local History | Cloud History |
|------|---------------|---------------|
| Free | 3 entries | None |
| Pro | Unlimited | 7 days |
| Team | Unlimited | 90 days |

## Error Handling

| Error | Response |
|-------|----------|
| No deploy.json | "Run /popkit:deploy init first" |
| No history | "No rollback points. Deploy first." |
| Free tier | Show upgrade prompt |
| Image not found | "Image may have been deleted. Try older version." |
| Verification failed | "Rollback may have issues. Check logs." |

## Integration

**Command:** `/popkit:deploy rollback`

**Agent:** Uses `rollback-specialist` for complex rollbacks

**Related Skills:**
| Skill | Relationship |
|-------|--------------|
| `pop-deploy-docker` | Docker-specific deployment |
| `pop-deploy-vercel` | Vercel-specific deployment |
| `pop-deploy-npm` | npm-specific deployment |

**Related Commands:**
| Command | Purpose |
|---------|---------|
| `/popkit:deploy execute` | Forward deployment |
| `/popkit:deploy validate` | Pre-deployment checks |
| `/popkit:deploy --list` | View deployment history |
