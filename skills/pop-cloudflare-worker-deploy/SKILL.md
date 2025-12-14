---
name: cloudflare-worker-deploy
description: "Deploy projects as Cloudflare Workers - generates wrangler.toml, configures secrets, sets up custom domains, and deploys with health verification. Supports TypeScript, JavaScript, and Python Workers."
---

# Cloudflare Worker Deployment

## Overview

Deploy any project as a Cloudflare Worker. Handles wrangler configuration, secret management, custom domain routing, and deployment verification.

**Core principle:** Zero-config for simple cases, full control for complex ones.

**Trigger:** `/popkit:deploy setup cloudflare-worker` command

## Prerequisites

- Cloudflare account with API token
- `CLOUDFLARE_API_TOKEN` environment variable set
- `wrangler` installed (`npm install -g wrangler` or `npx wrangler`)

## Critical Rules

1. **ALWAYS verify token first** - Check API access before any operations
2. **NEVER deploy without health check** - Verify endpoint responds after deploy
3. **Use environment-specific configs** - Dev vs production settings
4. **Set secrets via wrangler** - Never hardcode credentials
5. **Configure custom domains properly** - DNS + route configuration

## Process

### Step 1: Verify Cloudflare Access

```python
import os
import sys

# Check for API token
token = os.environ.get("CLOUDFLARE_API_TOKEN")
if not token:
    print("ERROR: CLOUDFLARE_API_TOKEN not set")
    print("Set via: export CLOUDFLARE_API_TOKEN=your-token")
    sys.exit(1)

# Verify token is valid
# Use hooks/utils/cloudflare_api.py
from hooks.utils.cloudflare_api import CloudflareClient
client = CloudflareClient()
valid, message = client.verify_token()

if not valid:
    print(f"ERROR: Token invalid - {message}")
    sys.exit(1)

print("Cloudflare access verified")
```

### Step 2: Detect Project Type

```python
from pathlib import Path

def detect_worker_type():
    """Detect what kind of Worker to create."""
    cwd = Path.cwd()

    # Check for existing wrangler.toml
    if (cwd / "wrangler.toml").exists():
        return "existing"

    # Check for TypeScript
    if (cwd / "tsconfig.json").exists():
        if (cwd / "package.json").exists():
            import json
            with open(cwd / "package.json") as f:
                pkg = json.load(f)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "hono" in deps:
                return "hono-ts"
            elif "itty-router" in deps:
                return "itty-ts"
            else:
                return "typescript"

    # Check for Python
    if (cwd / "requirements.txt").exists() or (cwd / "pyproject.toml").exists():
        return "python"

    # Default to JavaScript
    return "javascript"
```

### Step 3: User Configuration

Use AskUserQuestion to gather deployment details:

```
Use AskUserQuestion tool with:
- question: "What name should the Worker have?"
- header: "Worker Name"
- options:
  - label: "Use directory name"
    description: "Name based on current folder"
  - label: "Custom name"
    description: "I'll specify a name"
- multiSelect: false
```

```
Use AskUserQuestion tool with:
- question: "Do you want to configure a custom domain?"
- header: "Domain"
- options:
  - label: "Yes, configure domain"
    description: "Set up custom domain routing"
  - label: "No, use workers.dev"
    description: "Access via worker-name.workers.dev"
- multiSelect: false
```

### Step 4: Generate wrangler.toml

#### Basic Template (JavaScript/TypeScript)

```toml
name = "{{worker_name}}"
main = "src/index.ts"
compatibility_date = "2024-12-01"
compatibility_flags = ["nodejs_compat"]

[vars]
ENVIRONMENT = "production"

# Uncomment for custom domain:
# routes = [
#   { pattern = "api.example.com/*", zone_name = "example.com" }
# ]

# KV Namespaces (uncomment if needed):
# [[kv_namespaces]]
# binding = "MY_KV"
# id = "your-kv-namespace-id"

# D1 Database (uncomment if needed):
# [[d1_databases]]
# binding = "DB"
# database_name = "my-database"
# database_id = "your-d1-database-id"

# Durable Objects (uncomment if needed):
# [[durable_objects.bindings]]
# name = "MY_DO"
# class_name = "MyDurableObject"

# R2 Bucket (uncomment if needed):
# [[r2_buckets]]
# binding = "MY_BUCKET"
# bucket_name = "my-bucket"
```

#### Hono Framework Template

```toml
name = "{{worker_name}}"
main = "src/index.ts"
compatibility_date = "2024-12-01"
compatibility_flags = ["nodejs_compat"]

[vars]
ENVIRONMENT = "production"

# For Hono's getConnInfo() helper
# Requires Workers paid plan for certain features
```

#### Python Worker Template

```toml
name = "{{worker_name}}"
main = "src/entry.py"
compatibility_date = "2024-12-01"
compatibility_flags = ["python_workers"]

[vars]
ENVIRONMENT = "production"
```

### Step 5: Create Entry Point (if missing)

#### TypeScript with Hono

```typescript
// src/index.ts
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';

type Bindings = {
  ENVIRONMENT: string;
  // Add your bindings here
};

const app = new Hono<{ Bindings: Bindings }>();

// Middleware
app.use('*', cors());
app.use('*', logger());

// Routes
app.get('/', (c) => {
  return c.json({
    service: '{{worker_name}}',
    version: '1.0.0',
  });
});

app.get('/health', (c) => {
  return c.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
  });
});

// Error handling
app.onError((err, c) => {
  console.error('Request error:', err);
  return c.json({ error: 'Internal server error' }, 500);
});

app.notFound((c) => {
  return c.json({ error: 'Not found' }, 404);
});

export default app;
```

#### JavaScript (Basic)

```javascript
// src/index.js
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return Response.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
      });
    }

    if (url.pathname === '/') {
      return Response.json({
        service: '{{worker_name}}',
        version: '1.0.0',
      });
    }

    return Response.json({ error: 'Not found' }, { status: 404 });
  },
};
```

### Step 6: Configure Custom Domain (if requested)

```python
from hooks.utils.cloudflare_api import CloudflareClient

def setup_custom_domain(domain: str, subdomain: str, worker_name: str):
    """Configure DNS and wrangler for custom domain."""
    client = CloudflareClient()

    # Find zone
    zone = client.get_zone_by_name(domain)
    if not zone:
        raise ValueError(f"Zone not found: {domain}")

    # Check if record exists
    full_domain = f"{subdomain}.{domain}" if subdomain else domain
    records = client.list_dns_records(zone.id, name=full_domain)

    if records:
        # Update existing record
        print(f"Updating existing DNS record for {full_domain}")
        client.update_dns_record(
            zone.id,
            records[0].id,
            content=f"{worker_name}.workers.dev",
            proxied=True,
            comment=f"Worker: {worker_name}"
        )
    else:
        # Create new record
        print(f"Creating DNS record for {full_domain}")
        client.create_dns_record(
            zone.id,
            record_type="CNAME",
            name=subdomain or "@",
            content=f"{worker_name}.workers.dev",
            proxied=True,
            comment=f"Worker: {worker_name}"
        )

    return full_domain, zone.name
```

Update wrangler.toml with route:

```python
import toml

def add_route_to_wrangler(domain: str, zone_name: str):
    """Add custom domain route to wrangler.toml."""
    with open("wrangler.toml") as f:
        config = toml.load(f)

    config["routes"] = [
        {"pattern": f"{domain}/*", "zone_name": zone_name}
    ]

    with open("wrangler.toml", "w") as f:
        toml.dump(config, f)
```

### Step 7: Set Secrets

```
Use AskUserQuestion tool with:
- question: "Do you need to configure secrets for this Worker?"
- header: "Secrets"
- options:
  - label: "Yes, set secrets"
    description: "Configure environment secrets"
  - label: "No secrets needed"
    description: "Skip secret configuration"
- multiSelect: false
```

If yes, guide user through:

```bash
# Set secrets securely (prompts for value)
npx wrangler secret put SECRET_NAME

# Or bulk from .env.local
npx wrangler secret bulk .env.local
```

### Step 8: Deploy

```bash
# Install dependencies if needed
npm install

# Deploy to Cloudflare
npx wrangler deploy
```

### Step 9: Verify Deployment

```python
import urllib.request
import time

def verify_deployment(url: str, max_retries: int = 5):
    """Verify Worker is responding after deployment."""
    health_url = f"{url}/health"

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(health_url, timeout=10) as response:
                if response.status == 200:
                    data = response.read().decode()
                    print(f"Health check passed: {data}")
                    return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(2)

    return False

# Verify
if custom_domain:
    verify_deployment(f"https://{custom_domain}")
else:
    verify_deployment(f"https://{worker_name}.workers.dev")
```

## Output Format

```
Cloudflare Worker Deployment
════════════════════════════

[1/6] Verifying Cloudflare access...
      ✓ API token valid
      ✓ Account: your-account-name

[2/6] Detecting project type...
      ✓ Type: Hono (TypeScript)
      ✓ Entry: src/index.ts

[3/6] Generating wrangler.toml...
      ✓ Worker name: popkit-cloud-api
      ✓ Compatibility: 2024-12-01
      ✓ Node.js compat enabled
      → wrangler.toml created

[4/6] Configuring custom domain...
      ✓ Domain: api.thehouseofdeals.com
      ✓ DNS record created (CNAME → workers.dev)
      ✓ Route added to wrangler.toml

[5/6] Deploying to Cloudflare...
      ✓ Build successful
      ✓ Upload: 309 KiB (gzip)
      ✓ Version: d8efac8e-87c2-4198-a808-6fb9d5b4002d

[6/6] Verifying deployment...
      ✓ Health check passed
      ✓ Response time: 45ms

Deployment Complete!
════════════════════
Worker URL: https://api.thehouseofdeals.com
Workers.dev: https://popkit-cloud-api.workers.dev
Dashboard: https://dash.cloudflare.com/workers/popkit-cloud-api

Quick Commands:
  wrangler tail          # Live logs
  wrangler dev           # Local development
  wrangler deployments   # View deployment history
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Authentication error" | Verify CLOUDFLARE_API_TOKEN is set and valid |
| "Zone not found" | Check domain is in your Cloudflare account |
| "Build failed" | Run `npm run build` locally first |
| "Secret not found" | Set via `wrangler secret put NAME` |
| "Route conflict" | Remove conflicting routes in dashboard |

## Integration

**Command:** `/popkit:deploy setup cloudflare-worker`

**Utility:** Uses `hooks/utils/cloudflare_api.py` for API operations

**Followed by:**
- `/popkit:deploy validate` - Pre-deployment checks
- `/popkit:deploy execute` - Deploy the Worker

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-cloudflare-pages-deploy` | For static sites/SPAs |
| `pop-cloudflare-dns-manage` | DNS-only operations |
| `pop-deploy-init` | Initialize deployment config |
