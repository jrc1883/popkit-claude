---
name: deploy-docker
description: "Use when setting up Docker deployment - generates production-ready Dockerfile, docker-compose.yml for dev, and GitHub Actions workflow. Handles Node.js, Python, Go, and Rust projects with multi-stage builds and security best practices."
---

# Docker Deployment Setup

## Overview

Generate Docker deployment configuration for any project type. Creates production-optimized Dockerfiles, development docker-compose, and CI/CD workflows.

**Core principle:** Don't just containerize - optimize. Multi-stage builds, layer caching, non-root users, health checks.

**Trigger:** `/popkit:deploy setup docker` command

## Critical Rules

1. **ALWAYS use multi-stage builds** - Minimize final image size
2. **NEVER run as root** - Create non-root user in final stage
3. **ALWAYS include .dockerignore** - Exclude node_modules, .git, etc.
4. **Use specific base image tags** - No `latest` in production
5. **Order layers for cache efficiency** - Dependencies before source code

## Process

### Step 1: Detect Project Type

```python
import os
from pathlib import Path

def detect_project_type():
    """Detect project type from files."""
    cwd = Path.cwd()

    # Check for package.json
    if (cwd / "package.json").exists():
        import json
        with open(cwd / "package.json") as f:
            pkg = json.load(f)

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        if "next" in deps:
            return "nextjs"
        elif "react" in deps and "vite" in deps:
            return "vite-react"
        elif "express" in deps or "fastify" in deps or "hono" in deps:
            return "node-api"
        else:
            return "node"

    # Check for Python
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists():
        if (cwd / "manage.py").exists():
            return "django"
        elif (cwd / "app.py").exists() or (cwd / "main.py").exists():
            return "python-api"
        return "python"

    # Check for Go
    if (cwd / "go.mod").exists():
        return "go"

    # Check for Rust
    if (cwd / "Cargo.toml").exists():
        return "rust"

    return "unknown"
```

### Step 2: Generate Dockerfile

Use AskUserQuestion to confirm template:

```
Use AskUserQuestion tool with:
- question: "Which Docker template level do you want?"
- header: "Template"
- options:
  - label: "Standard (Recommended)"
    description: "Multi-stage build, docker-compose, CI workflow"
  - label: "Minimal"
    description: "Basic Dockerfile only, no CI"
  - label: "Production"
    description: "All above + health checks, security scanning, multi-registry"
- multiSelect: false
```

### Step 3: Write Files

Generate files based on project type and template level.

## Dockerfile Templates

### Node.js (Express/API)

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser

# Copy production dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Set ownership
RUN chown -R appuser:nodejs /app

USER appuser

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

### Next.js (Standalone)

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package*.json ./
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Copy standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
```

### Python (FastAPI/Flask)

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runner
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash appuser

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application
COPY --chown=appuser:appgroup . .

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Go

```dockerfile
# Stage 1: Builder
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install git for go mod
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build with optimizations
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server .

# Stage 2: Runner (distroless for minimal attack surface)
FROM gcr.io/distroless/static-debian12 AS runner

WORKDIR /app

# Copy binary
COPY --from=builder /app/server .

# Non-root user (distroless uses nonroot by default)
USER nonroot:nonroot

ENV PORT=8080

EXPOSE 8080

# Note: distroless doesn't support shell, so no HEALTHCHECK
# Use container orchestrator health checks instead

ENTRYPOINT ["/app/server"]
```

### Rust

```dockerfile
# Stage 1: Builder
FROM rust:1.75-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache musl-dev

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy src to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Copy real source
COPY src ./src

# Build release
RUN touch src/main.rs && cargo build --release

# Stage 2: Runner (scratch for minimal size)
FROM scratch AS runner

# Copy binary
COPY --from=builder /app/target/release/app /app

# Non-root (UID 1001)
USER 1001

ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["/app"]
```

## Docker Compose Template

```yaml
# docker-compose.yml - Development environment
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder  # Use builder stage for dev
    ports:
      - "${PORT:-3000}:3000"
    volumes:
      - .:/app
      - /app/node_modules  # Persist node_modules
    environment:
      - NODE_ENV=development
      - DATABASE_URL=${DATABASE_URL:-}
    command: npm run dev
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Optional: Database for development
  # db:
  #   image: postgres:16-alpine
  #   environment:
  #     POSTGRES_USER: dev
  #     POSTGRES_PASSWORD: dev
  #     POSTGRES_DB: app
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

# volumes:
#   postgres_data:
```

## .dockerignore Template

```
# Dependencies
node_modules/
.pnp/
.pnp.js

# Testing
coverage/

# Build output
.next/
out/
dist/
build/

# Git
.git/
.gitignore

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Logs
logs/
*.log
npm-debug.log*

# Docker
Dockerfile*
docker-compose*.yml
.docker/

# Documentation
docs/
*.md
!README.md

# Claude Code
.claude/

# OS
.DS_Store
Thumbs.db
```

## GitHub Actions Workflow

```yaml
# .github/workflows/docker-publish.yml
name: Docker Build & Publish

on:
  push:
    branches: [main, master]
    tags: ['v*']
  pull_request:
    branches: [main, master]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Optional: Security scanning
      # - name: Run Trivy vulnerability scanner
      #   uses: aquasecurity/trivy-action@master
      #   with:
      #     image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
      #     format: 'sarif'
      #     output: 'trivy-results.sarif'
```

## Output Format

```
Docker Deployment Setup
═══════════════════════

[1/4] Detecting project type...
      ✓ Detected: Next.js 14 (Node.js)
      ✓ Build command: npm run build
      ✓ Start command: npm start
      ✓ Port: 3000

[2/4] Generating Dockerfile...
      ✓ Template: Standard (3-stage build)
      ✓ Base image: node:20-alpine
      ✓ Security: Non-root user configured
      ✓ Health check: /api/health endpoint
      → Dockerfile created

[3/4] Generating docker-compose.yml...
      ✓ Development environment
      ✓ Hot reload via volume mounts
      ✓ Port mapping: 3000:3000
      → docker-compose.yml created

[4/4] Generating CI/CD workflow...
      ✓ Registry: ghcr.io
      ✓ Build cache: GitHub Actions cache
      ✓ Tags: semver + sha
      → .github/workflows/docker-publish.yml created

Files Created:
├── Dockerfile (3 stages, ~150MB final)
├── docker-compose.yml (dev environment)
├── .dockerignore (25 patterns)
└── .github/workflows/docker-publish.yml

Quick Commands:
  docker compose up -d    # Start dev environment
  docker build -t app .   # Build production image
  docker run -p 3000:3000 app  # Run container

Would you like to commit these files?
```

## Verification Checklist

After generation, verify:

| Check | Command |
|-------|---------|
| Dockerfile syntax | `docker build --check .` |
| Compose syntax | `docker compose config` |
| Build works | `docker build -t test .` |
| Container runs | `docker run --rm -p 3000:3000 test` |
| Health check | `curl localhost:3000/health` |

## Integration

**Command:** `/popkit:deploy setup docker`

**Agent:** Uses `devops-automator` for intelligent template selection

**Followed by:**
- `/popkit:deploy validate` - Pre-deployment checks
- `/popkit:deploy execute docker` - Build and push

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `pop-deploy-init` | Run first to configure targets |
| `pop-deploy-validate` | Verify Docker config before deploy |
