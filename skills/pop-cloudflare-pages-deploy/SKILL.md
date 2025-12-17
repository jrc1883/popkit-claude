---
name: cloudflare-pages-deploy
description: "Deploy static sites and SPAs to Cloudflare Pages - auto-detects framework (Next.js, Vite, Astro, etc.), configures build settings, sets up custom domains, and deploys with preview URLs."
---

# Cloudflare Pages Deployment

## Overview

Deploy any frontend application to Cloudflare Pages. Handles framework detection, build configuration, custom domains, and preview deployments.

**Core principle:** Framework-aware deployment with zero config for standard setups.

**Trigger:** `/popkit:deploy setup cloudflare-pages` command

## Prerequisites

- Cloudflare account with API token
- `CLOUDFLARE_API_TOKEN` environment variable set
- Git repository (recommended for automatic deployments)

## Critical Rules

1. **Auto-detect framework** - Configure build settings based on detected framework
2. **Optimize for edge** - Enable edge caching and compression
3. **Configure preview URLs** - Enable PR preview deployments
4. **Set environment variables properly** - Build-time vs runtime
5. **Use custom domains with SSL** - Automatic HTTPS configuration

## Supported Frameworks

| Framework | Build Command | Output Directory |
|-----------|--------------|------------------|
| Next.js | `npm run build` | `.next` or `out` |
| Vite | `npm run build` | `dist` |
| Astro | `npm run build` | `dist` |
| Remix | `npm run build` | `build` |
| SvelteKit | `npm run build` | `build` |
| Nuxt | `npm run build` | `.output/public` |
| Create React App | `npm run build` | `build` |
| Vue CLI | `npm run build` | `dist` |
| Docusaurus | `npm run build` | `build` |
| Hugo | `hugo` | `public` |
| 11ty | `npx @11ty/eleventy` | `_site` |

## Process

### Step 1: Detect Framework

```python
from pathlib import Path
import json

def detect_frontend_framework():
    """Detect frontend framework from project files."""
    cwd = Path.cwd()

    # Check package.json
    pkg_path = cwd / "package.json"
    if pkg_path.exists():
        with open(pkg_path) as f:
            pkg = json.load(f)

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Framework detection order matters
        if "next" in deps:
            # Check for static export
            next_config = cwd / "next.config.js"
            if next_config.exists():
                content = next_config.read_text()
                if "output: 'export'" in content or "output: \"export\"" in content:
                    return {
                        "name": "Next.js (Static)",
                        "build_command": "npm run build",
                        "output_directory": "out"
                    }
            return {
                "name": "Next.js",
                "build_command": "npm run build",
                "output_directory": ".next"
            }

        if "astro" in deps:
            return {
                "name": "Astro",
                "build_command": "npm run build",
                "output_directory": "dist"
            }

        if "@remix-run/react" in deps:
            return {
                "name": "Remix",
                "build_command": "npm run build",
                "output_directory": "build"
            }

        if "@sveltejs/kit" in deps:
            return {
                "name": "SvelteKit",
                "build_command": "npm run build",
                "output_directory": "build"
            }

        if "nuxt" in deps:
            return {
                "name": "Nuxt",
                "build_command": "npm run build",
                "output_directory": ".output/public"
            }

        if "vite" in deps:
            return {
                "name": "Vite",
                "build_command": "npm run build",
                "output_directory": "dist"
            }

        if "react-scripts" in deps:
            return {
                "name": "Create React App",
                "build_command": "npm run build",
                "output_directory": "build"
            }

        if "@vue/cli-service" in deps:
            return {
                "name": "Vue CLI",
                "build_command": "npm run build",
                "output_directory": "dist"
            }

        if "@docusaurus/core" in deps:
            return {
                "name": "Docusaurus",
                "build_command": "npm run build",
                "output_directory": "build"
            }

    # Hugo
    if (cwd / "hugo.toml").exists() or (cwd / "config.toml").exists():
        return {
            "name": "Hugo",
            "build_command": "hugo",
            "output_directory": "public"
        }

    # 11ty
    if (cwd / ".eleventy.js").exists() or (cwd / "eleventy.config.js").exists():
        return {
            "name": "Eleventy",
            "build_command": "npx @11ty/eleventy",
            "output_directory": "_site"
        }

    # Static HTML
    if (cwd / "index.html").exists():
        return {
            "name": "Static HTML",
            "build_command": "",
            "output_directory": "."
        }

    return None
```

### Step 2: User Configuration

```
Use AskUserQuestion tool with:
- question: "What name should the Pages project have?"
- header: "Project Name"
- options:
  - label: "Use directory name"
    description: "Name based on current folder"
  - label: "Custom name"
    description: "I'll specify a name"
- multiSelect: false
```

```
Use AskUserQuestion tool with:
- question: "How do you want to deploy?"
- header: "Deploy Method"
- options:
  - label: "Direct upload (Recommended)"
    description: "Deploy built files directly"
  - label: "Git integration"
    description: "Auto-deploy on push to GitHub/GitLab"
- multiSelect: false
```

### Step 3: Deploy via Wrangler

#### Direct Upload (Recommended for testing)

```bash
# Build the project first
npm run build

# Deploy to Cloudflare Pages
npx wrangler pages deploy dist --project-name=my-project
```

#### Git Integration (Recommended for production)

Use Cloudflare Dashboard or API to connect Git repository:

```python
# This requires going to Cloudflare Dashboard
# https://dash.cloudflare.com/pages/new

print("""
To set up Git integration:

1. Go to https://dash.cloudflare.com/pages/new
2. Connect your GitHub/GitLab account
3. Select repository
4. Configure build settings:
   - Framework preset: {framework}
   - Build command: {build_command}
   - Build output directory: {output_directory}
5. Deploy!

Or use wrangler for direct deploy:
  npx wrangler pages deploy {output_directory}
""")
```

### Step 4: Configure Custom Domain

```python
from hooks.utils.cloudflare_api import CloudflareClient

def setup_pages_domain(project_name: str, domain: str):
    """Configure custom domain for Pages project."""
    client = CloudflareClient()

    # Find zone
    root_domain = ".".join(domain.split(".")[-2:])
    zone = client.get_zone_by_name(root_domain)

    if not zone:
        raise ValueError(f"Zone not found: {root_domain}")

    # Subdomain or root
    subdomain = domain.replace(f".{root_domain}", "") if domain != root_domain else "@"

    # Create CNAME record pointing to Pages
    existing = client.list_dns_records(zone.id, name=domain)

    if existing:
        client.update_dns_record(
            zone.id,
            existing[0].id,
            content=f"{project_name}.pages.dev",
            proxied=True
        )
    else:
        client.create_dns_record(
            zone.id,
            record_type="CNAME",
            name=subdomain,
            content=f"{project_name}.pages.dev",
            proxied=True,
            comment=f"Pages project: {project_name}"
        )

    print(f"DNS configured: {domain} -> {project_name}.pages.dev")
```

### Step 5: Set Environment Variables (if needed)

```bash
# For build-time variables (available during build)
npx wrangler pages secret put API_KEY --project-name=my-project

# For runtime variables (in _headers or _redirects)
# Or via Dashboard: Pages > Project > Settings > Environment variables
```

### Step 6: Verify Deployment

```python
import urllib.request
import time

def verify_pages_deployment(url: str, max_retries: int = 5):
    """Verify Pages site is responding."""
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                if response.status == 200:
                    print(f"Site is live: {url}")
                    return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(3)

    return False
```

## Output Format

```
Cloudflare Pages Deployment
═══════════════════════════

[1/5] Detecting framework...
      ✓ Framework: Vite (React)
      ✓ Build command: npm run build
      ✓ Output directory: dist

[2/5] Building project...
      ✓ Dependencies installed
      ✓ Build completed
      ✓ Output size: 245 KiB

[3/5] Deploying to Pages...
      ✓ Project: my-frontend
      ✓ Upload: 12 files
      ✓ Deploy ID: abc123def456

[4/5] Configuring domain...
      ✓ Domain: app.example.com
      ✓ DNS record created
      ✓ SSL auto-configured

[5/5] Verifying deployment...
      ✓ Site is live
      ✓ HTTPS enabled
      ✓ Edge caching active

Deployment Complete!
════════════════════
Production URL: https://app.example.com
Pages URL: https://my-frontend.pages.dev
Preview URL: https://abc123.my-frontend.pages.dev
Dashboard: https://dash.cloudflare.com/pages/my-frontend

Features Enabled:
  ✓ Automatic HTTPS
  ✓ Edge caching
  ✓ Brotli compression
  ✓ Preview deployments
```

## Files Generated

### _headers (Optional)

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

### _redirects (Optional)

```
# SPA fallback
/*  /index.html  200

# Redirect www to apex
https://www.example.com/*  https://example.com/:splat  301
```

## Integration

**Command:** `/popkit:deploy setup cloudflare-pages`

**Utility:** Uses `hooks/utils/cloudflare_api.py` for DNS operations

**Followed by:**
- `/popkit:deploy validate` - Pre-deployment checks
- `/popkit:deploy execute` - Deploy the site

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-cloudflare-worker-deploy` | For API/backend Workers |
| `pop-cloudflare-dns-manage` | DNS-only operations |
| `pop-deploy-vercel` | Alternative: Vercel deployment |
| `pop-deploy-netlify` | Alternative: Netlify deployment |
