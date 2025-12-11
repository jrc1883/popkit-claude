---
name: deploy-netlify
description: "Use when deploying to Netlify - generates netlify.toml, preview deployment workflows, and environment variable templates. Handles Next.js, Nuxt, Astro, and static sites with automatic framework detection and Netlify Functions support."
---

# Netlify Deployment Setup

## Overview

Configure Netlify deployment for frontend applications. Generates production-ready `netlify.toml`, preview deployment workflows, and environment management.

**Core principle:** Convention over configuration, with escape hatches when needed.

**Trigger:** `/popkit:deploy setup netlify` command

## Critical Rules

1. **ALWAYS detect framework first** - Netlify has framework-specific build plugins
2. **Use deploy previews for PRs** - Automatic with Netlify, but we add custom workflows
3. **Separate contexts** - Production, deploy-preview, branch-deploy
4. **Use Netlify Functions** - For serverless API routes
5. **Edge Functions for performance** - When latency matters

## Process

### Step 1: Detect Framework

```python
import os
import json
from pathlib import Path

def detect_framework():
    """Detect frontend framework for Netlify optimization."""
    cwd = Path.cwd()

    # Check package.json
    if (cwd / "package.json").exists():
        with open(cwd / "package.json") as f:
            pkg = json.load(f)

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Framework detection
        if "next" in deps:
            return "nextjs"
        elif "nuxt" in deps:
            return "nuxt"
        elif "@sveltejs/kit" in deps:
            return "sveltekit"
        elif "astro" in deps:
            return "astro"
        elif "gatsby" in deps:
            return "gatsby"
        elif "remix" in deps:
            return "remix"
        elif "vite" in deps:
            return "vite"
        elif "react-scripts" in deps:
            return "create-react-app"
        elif "@angular/core" in deps:
            return "angular"
        elif "vue" in deps and "vite" not in deps:
            return "vue-cli"

    # Static site generators
    if (cwd / "hugo.toml").exists() or (cwd / "config.toml").exists():
        return "hugo"
    if (cwd / "_config.yml").exists():
        return "jekyll"
    if (cwd / "mkdocs.yml").exists():
        return "mkdocs"
    if (cwd / "docusaurus.config.js").exists():
        return "docusaurus"

    return "static"
```

### Step 2: Generate netlify.toml

Use AskUserQuestion to confirm settings:

```
Use AskUserQuestion tool with:
- question: "Detected [framework]. Configure Netlify settings?"
- header: "Netlify Config"
- options:
  - label: "Default settings (Recommended)"
    description: "Use Netlify's automatic detection with sensible defaults"
  - label: "With Netlify Functions"
    description: "Include serverless function support"
  - label: "With Edge Functions"
    description: "Include edge function support for low latency"
- multiSelect: false
```

### Step 3: Write Configuration Files

Generate files based on framework and user preferences.

## netlify.toml Templates

### Next.js

```toml
# netlify.toml - Next.js configuration

[build]
  command = "npm run build"
  publish = ".next"

# Next.js requires the Netlify Next.js Runtime
[[plugins]]
  package = "@netlify/plugin-nextjs"

# Production context
[context.production]
  environment = { NODE_ENV = "production" }

# Deploy preview context
[context.deploy-preview]
  environment = { NODE_ENV = "preview" }

# Headers for security and caching
[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    Referrer-Policy = "strict-origin-when-cross-origin"

[[headers]]
  for = "/_next/static/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

# Redirects for SPA fallback (if needed)
# [[redirects]]
#   from = "/*"
#   to = "/index.html"
#   status = 200
```

### Vite (React/Vue/Svelte)

```toml
# netlify.toml - Vite SPA configuration

[build]
  command = "npm run build"
  publish = "dist"

[context.production]
  environment = { NODE_ENV = "production" }

[context.deploy-preview]
  environment = { NODE_ENV = "preview" }

# SPA fallback - serve index.html for all routes
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

# Headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

### Astro

```toml
# netlify.toml - Astro configuration

[build]
  command = "npm run build"
  publish = "dist"

# Astro SSR adapter (if using SSR)
# [[plugins]]
#   package = "@astrojs/netlify"

[context.production]
  environment = { NODE_ENV = "production" }

[[headers]]
  for = "/_astro/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
```

### Static Site (Hugo/Jekyll)

```toml
# netlify.toml - Static site configuration

[build]
  command = "hugo --minify"  # or "jekyll build"
  publish = "public"         # or "_site" for Jekyll

[context.production]
  environment = { HUGO_ENV = "production" }

[context.deploy-preview]
  command = "hugo --buildDrafts --buildFuture"

# Pretty URLs
[[redirects]]
  from = "/posts/:year/:month/:slug"
  to = "/blog/:year/:month/:slug"
  status = 301

# Headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    Cache-Control = "public, max-age=3600"

[[headers]]
  for = "/css/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/js/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

### With Netlify Functions

```toml
# netlify.toml - With serverless functions

[build]
  command = "npm run build"
  publish = "dist"
  functions = "netlify/functions"

[functions]
  node_bundler = "esbuild"
  included_files = ["./config/**"]

[context.production]
  environment = { NODE_ENV = "production" }

# API routes to functions
[[redirects]]
  from = "/api/*"
  to = "/.netlify/functions/:splat"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
```

### With Edge Functions

```toml
# netlify.toml - With edge functions

[build]
  command = "npm run build"
  publish = "dist"

[[edge_functions]]
  path = "/api/*"
  function = "api-handler"

[[edge_functions]]
  path = "/*"
  function = "middleware"

[context.production]
  environment = { NODE_ENV = "production" }

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
```

## GitHub Actions Workflow

### Deploy Preview (PR)

```yaml
# .github/workflows/netlify-preview.yml
name: Netlify Preview Deployment

on:
  pull_request:
    branches: [main, master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          NODE_ENV: preview

      - name: Deploy to Netlify
        id: deploy
        uses: nwtgck/actions-netlify@v3
        with:
          publish-dir: './dist'
          production-deploy: false
          github-token: ${{ secrets.GITHUB_TOKEN }}
          deploy-message: "Deploy from GitHub Actions - PR #${{ github.event.number }}"
          enable-pull-request-comment: true
          enable-commit-comment: false
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

### Production Deployment

```yaml
# .github/workflows/netlify-production.yml
name: Netlify Production Deployment

on:
  push:
    branches: [main, master]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          NODE_ENV: production

      - name: Deploy to Netlify
        uses: nwtgck/actions-netlify@v3
        with:
          publish-dir: './dist'
          production-deploy: true
          github-token: ${{ secrets.GITHUB_TOKEN }}
          deploy-message: "Production deploy from GitHub Actions"
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

## Netlify Functions Example

```typescript
// netlify/functions/hello.ts
import type { Handler } from "@netlify/functions";

export const handler: Handler = async (event, context) => {
  const name = event.queryStringParameters?.name || "World";

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: `Hello, ${name}!`,
      timestamp: new Date().toISOString(),
    }),
  };
};
```

## Edge Functions Example

```typescript
// netlify/edge-functions/middleware.ts
import type { Context } from "@netlify/edge-functions";

export default async (request: Request, context: Context) => {
  // Add custom header
  const response = await context.next();
  response.headers.set("X-Custom-Header", "PopKit");

  return response;
};

export const config = {
  path: "/*",
};
```

## Environment Variables Template

```markdown
# Netlify Environment Variables Setup

Required secrets in GitHub Actions:

| Secret | Description | How to Get |
|--------|-------------|------------|
| `NETLIFY_AUTH_TOKEN` | Personal access token | netlify.com/user/applications |
| `NETLIFY_SITE_ID` | Site ID | Netlify Dashboard → Site Settings → General |

## Getting Netlify Site ID

1. Go to Netlify Dashboard
2. Select your site
3. Site Settings → General → Site ID

## Environment Variables in Netlify Dashboard

Add these in Netlify Dashboard → Site → Site Settings → Environment Variables:

| Variable | Contexts | Value |
|----------|----------|-------|
| `DATABASE_URL` | Production | Your production database |
| `DATABASE_URL` | Deploy previews | Your staging database |
| `API_SECRET` | All | Your API secret |

## Scopes and Contexts

Netlify supports different contexts:
- **production**: Main branch deployments
- **deploy-preview**: PR preview deployments
- **branch-deploy**: Other branch deployments
- **dev**: Local development (netlify dev)
```

## Output Format

```
Netlify Deployment Setup
════════════════════════

[1/4] Detecting framework...
      ✓ Detected: Vite + React
      ✓ Build command: npm run build
      ✓ Output: dist

[2/4] Generating netlify.toml...
      ✓ Build configuration set
      ✓ SPA fallback redirect added
      ✓ Security headers configured
      ✓ Asset caching headers added
      → netlify.toml created

[3/4] Generating workflows...
      ✓ Preview deployment for PRs
      ✓ Production deployment on main
      → .github/workflows/netlify-preview.yml
      → .github/workflows/netlify-production.yml

[4/4] Generating env template...
      → docs/NETLIFY_SETUP.md created

Files Created:
├── netlify.toml
├── .github/workflows/netlify-preview.yml
├── .github/workflows/netlify-production.yml
└── docs/NETLIFY_SETUP.md

Required Secrets:
  NETLIFY_AUTH_TOKEN  - Personal access token from netlify.com
  NETLIFY_SITE_ID     - From Netlify Dashboard → Site Settings

Quick Commands:
  netlify link        # Connect to Netlify site
  netlify dev         # Run local development
  netlify deploy      # Manual deploy (preview)
  netlify deploy --prod  # Manual production deploy

Would you like to commit these files?
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| TOML valid | `netlify build --dry` |
| CLI linked | `netlify status` |
| Local dev works | `netlify dev` |
| Build succeeds | `netlify build` |
| Deploy works | `netlify deploy` |

## Integration

**Command:** `/popkit:deploy setup netlify`

**Agent:** Uses `devops-automator` for intelligent template selection

**Followed by:**
- `/popkit:deploy validate` - Pre-deployment checks
- `/popkit:deploy execute netlify` - Trigger deployment

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-vercel` | Alternative frontend hosting |
| `pop-deploy-docker` | For containerized deployments |
