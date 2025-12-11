---
name: deploy-vercel
description: "Use when deploying to Vercel - generates vercel.json, preview deployment workflows, and environment variable templates. Handles Next.js, Nuxt, SvelteKit, Astro, and static sites with automatic framework detection."
---

# Vercel Deployment Setup

## Overview

Configure Vercel deployment for frontend applications. Generates production-ready `vercel.json`, preview deployment workflows, and environment management.

**Core principle:** Zero-config where possible, explicit config where needed.

**Trigger:** `/popkit:deploy setup vercel` command

## Critical Rules

1. **ALWAYS detect framework first** - Vercel has framework-specific optimizations
2. **Use preview deployments for PRs** - Every PR gets a unique URL
3. **Separate staging and production** - Different environment variables
4. **Never commit secrets** - Use Vercel environment variables
5. **Prefer Vercel CLI** - More control than git push deploys

## Process

### Step 1: Detect Framework

```python
import os
import json
from pathlib import Path

def detect_framework():
    """Detect frontend framework for Vercel optimization."""
    cwd = Path.cwd()

    # Check package.json
    if (cwd / "package.json").exists():
        with open(cwd / "package.json") as f:
            pkg = json.load(f)

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Framework detection order matters
        if "next" in deps:
            # Check for App Router vs Pages Router
            if (cwd / "app").exists() or (cwd / "src" / "app").exists():
                return "nextjs-app"
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
            if "react" in deps:
                return "vite-react"
            elif "vue" in deps:
                return "vite-vue"
            elif "svelte" in deps:
                return "vite-svelte"
            return "vite"
        elif "react-scripts" in deps:
            return "create-react-app"

    # Check for static site generators
    if (cwd / "hugo.toml").exists() or (cwd / "config.toml").exists():
        return "hugo"
    if (cwd / "_config.yml").exists():
        return "jekyll"

    # Default to static
    return "static"
```

### Step 2: Generate vercel.json

Use AskUserQuestion to confirm settings:

```
Use AskUserQuestion tool with:
- question: "Detected [framework]. Configure Vercel settings?"
- header: "Vercel Config"
- options:
  - label: "Default settings (Recommended)"
    description: "Use Vercel's automatic detection"
  - label: "Custom configuration"
    description: "Specify build commands and output directory"
- multiSelect: false
```

### Step 3: Write Configuration Files

Generate files based on framework and user preferences.

## vercel.json Templates

### Next.js (App Router)

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "regions": ["iad1"],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "/api/:path*"
    }
  ]
}
```

### Vite (React/Vue/Svelte)

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### Astro

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "astro",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "headers": [
    {
      "source": "/_astro/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### SvelteKit

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "sveltekit",
  "regions": ["iad1"]
}
```

### Static Site

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "outputDirectory": "public",
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

## GitHub Actions Workflow

### Preview Deployment (PR)

```yaml
# .github/workflows/vercel-preview.yml
name: Vercel Preview Deployment

on:
  pull_request:
    branches: [main, master]

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

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

      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Pull Vercel Environment
        run: vercel pull --yes --environment=preview --token=${{ secrets.VERCEL_TOKEN }}

      - name: Build Project
        run: vercel build --token=${{ secrets.VERCEL_TOKEN }}

      - name: Deploy to Vercel
        id: deploy
        run: |
          url=$(vercel deploy --prebuilt --token=${{ secrets.VERCEL_TOKEN }})
          echo "url=$url" >> $GITHUB_OUTPUT

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🚀 Preview Deployment Ready\n\n**URL:** ${{ steps.deploy.outputs.url }}\n\n*Deployed via Vercel*`
            })
```

### Production Deployment

```yaml
# .github/workflows/vercel-production.yml
name: Vercel Production Deployment

on:
  push:
    branches: [main, master]

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

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

      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Pull Vercel Environment
        run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}

      - name: Build Project
        run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}

      - name: Deploy to Vercel
        run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
```

## Environment Variables Template

```markdown
# Vercel Environment Variables Setup

Required secrets in GitHub Actions:

| Secret | Description | How to Get |
|--------|-------------|------------|
| `VERCEL_TOKEN` | Vercel API token | vercel.com/account/tokens |
| `VERCEL_ORG_ID` | Organization ID | vercel.com/teams → Settings |
| `VERCEL_PROJECT_ID` | Project ID | vercel.com/project → Settings |

## Getting Vercel Project IDs

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel link`
3. Check `.vercel/project.json` for orgId and projectId

## Environment Variables in Vercel Dashboard

Add these in Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Environments | Value |
|----------|--------------|-------|
| `DATABASE_URL` | Production, Preview | Your database URL |
| `NEXT_PUBLIC_API_URL` | Production | https://api.yoursite.com |
| `NEXT_PUBLIC_API_URL` | Preview | https://staging-api.yoursite.com |
```

## Output Format

```
Vercel Deployment Setup
═══════════════════════

[1/4] Detecting framework...
      ✓ Detected: Next.js 14 (App Router)
      ✓ Build command: next build
      ✓ Output: .next

[2/4] Generating vercel.json...
      ✓ Framework preset applied
      ✓ Security headers added
      ✓ Region: iad1 (US East)
      → vercel.json created

[3/4] Generating workflows...
      ✓ Preview deployment for PRs
      ✓ Production deployment on main
      → .github/workflows/vercel-preview.yml
      → .github/workflows/vercel-production.yml

[4/4] Generating env template...
      → docs/VERCEL_SETUP.md created

Files Created:
├── vercel.json
├── .github/workflows/vercel-preview.yml
├── .github/workflows/vercel-production.yml
└── docs/VERCEL_SETUP.md

Required Secrets:
  VERCEL_TOKEN       - API token from vercel.com/account/tokens
  VERCEL_ORG_ID      - From vercel link or dashboard
  VERCEL_PROJECT_ID  - From vercel link or dashboard

Quick Commands:
  vercel link         # Connect to Vercel project
  vercel dev          # Run local development
  vercel deploy       # Manual deploy

Would you like to commit these files?
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| JSON valid | `cat vercel.json | jq .` |
| CLI linked | `vercel whoami` |
| Local dev works | `vercel dev` |
| Build succeeds | `vercel build` |
| Deploy works | `vercel deploy` |

## Integration

**Command:** `/popkit:deploy setup vercel`

**Agent:** Uses `devops-automator` for intelligent template selection

**Followed by:**
- `/popkit:deploy validate` - Pre-deployment checks
- `/popkit:deploy execute vercel` - Trigger deployment

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-netlify` | Alternative frontend hosting |
| `pop-deploy-docker` | For containerized deployments |
