---
description: "init | setup | validate | execute | rollback [--target, --all, --dry-run]"
argument-hint: "<subcommand> [target] [options]"
---

# /popkit:deploy - Universal Deployment Orchestration

Deploy to any target: Docker, npm/PyPI, Vercel/Netlify, or GitHub Releases. Adapts to project state from no CI/CD to full production pipelines.

## Usage

```
/popkit:deploy <subcommand> [options]
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `init` | Analyze project state and configure deployment (default) |
| `setup` | Generate CI/CD pipeline and target configuration |
| `validate` | Run pre-deployment checks |
| `execute` | Deploy to target(s) |
| `rollback` | Undo a deployment |

---

## Subcommand: init (default)

Analyze project state, identify deployment targets, and configure `.claude/popkit/deploy.json`.

```
/popkit:deploy                          # Auto-runs init if unconfigured
/popkit:deploy init                     # Explicit init
/popkit:deploy init --force             # Re-analyze even if configured
```

### Process

1. **Check PopKit Initialization**
   - Verify `.claude/popkit/` exists
   - Verify CLAUDE.md has PopKit markers
   - Offer to fix gaps if found

2. **Front-load User Intent** (using AskUserQuestion with multiple questions)

   ```
   Use AskUserQuestion tool with:
   - questions:
     [1] "What type of project are you deploying?" [header: "Project"]
         Options:
         - Web application (frontend/fullstack/SSR)
         - Backend API/service
         - CLI tool or library

     [2] "Where do you want to deploy?" [header: "Targets", multiSelect: true]
         Options:
         - Docker (universal - any server/cloud)
         - Vercel/Netlify (frontend hosting)
         - npm/PyPI registry (package publishing)
         - GitHub Releases (binary artifacts)

     [3] "What's your current deployment setup?" [header: "State"]
         Options:
         - Starting fresh (no GitHub, no CI/CD)
         - Have GitHub, need CI/CD
         - Have CI/CD, need target config
         - Everything exists (just orchestrate)
   ```

3. **Store Configuration**
   ```json
   // .claude/popkit/deploy.json
   {
     "version": "1.0",
     "project_type": "web-app",
     "targets": ["docker", "vercel"],
     "state": "needs-cicd",
     "initialized_at": "2025-12-10T...",
     "initialized_by": "popkit-1.2.0",
     "github": {
       "repo": "owner/repo",
       "default_branch": "main",
       "has_actions": true
     },
     "history": []
   }
   ```

### Gap Handling

If PopKit initialization is incomplete, show:

```
PopKit deployment readiness check:

⚠️ Missing: .claude/popkit/ directory
⚠️ Missing: CLAUDE.md PopKit markers
⚠️ Missing: PopKit fields in settings.json

These are required for deployment features to work properly.
```

Then use AskUserQuestion:
```
Use AskUserQuestion tool with:
- question: "Would you like to fix these PopKit initialization gaps?"
- header: "Fix Gaps"
- options:
  - label: "Yes, fix and continue (Recommended)"
    description: "Run project init to create missing directories and config"
  - label: "Skip, continue anyway"
    description: "May cause issues with some features"
- multiSelect: false
```

### Output

```
PopKit Deployment Initialization
═════════════════════════════════

[1/3] Checking PopKit prerequisites...
      ✓ .claude/popkit/ exists
      ✓ CLAUDE.md has PopKit markers
      ✓ settings.json has PopKit fields

[2/3] Detecting current state...
      ✓ GitHub repository: owner/repo
      ✓ GitHub Actions: detected
      ⚠️ Docker: not configured
      ⚠️ Vercel: not configured

[3/3] Saving configuration...
      ✓ .claude/popkit/deploy.json created

Configuration:
  Project Type: web-app
  Targets: docker, vercel
  State: has-github-needs-cicd

Next Steps:
  Run /popkit:deploy setup docker    → Generate Dockerfile & CI
  Run /popkit:deploy setup vercel    → Configure Vercel deployment
```

### Options

| Flag | Description |
|------|-------------|
| `--force` | Re-run analysis even if config exists |
| `--skip-github` | Don't offer GitHub setup |
| `--json` | Output config as JSON |

---

## Subcommand: setup

Configure CI/CD pipeline and deployment target(s). Generates configuration files specific to each target.

```
/popkit:deploy setup                    # Interactive setup for all targets
/popkit:deploy setup docker             # Setup Docker specifically
/popkit:deploy setup vercel             # Setup Vercel specifically
/popkit:deploy setup netlify            # Setup Netlify specifically
/popkit:deploy setup npm                # Setup npm publishing
/popkit:deploy setup pypi               # Setup PyPI publishing
/popkit:deploy setup github-releases    # Setup GitHub Releases
/popkit:deploy setup --all              # Setup all configured targets
```

### Files Generated Per Target

| Target | Files Generated |
|--------|-----------------|
| Docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/docker-publish.yml` |
| Vercel | `vercel.json`, `.github/workflows/preview-deploy.yml` |
| Netlify | `netlify.toml`, `.github/workflows/netlify-deploy.yml` |
| npm | Validates `package.json`, `.github/workflows/npm-publish.yml`, `.npmrc` template |
| PyPI | Validates `pyproject.toml`, `.github/workflows/pypi-publish.yml` |
| GitHub Releases | `.github/workflows/release.yml`, asset configuration |

### Process

Invokes **devops-automator** agent:

1. **Load Configuration**
   - Read `deploy.json` for targets and project type
   - Verify GitHub connection

2. **Generate Files**
   - Create Dockerfile (multi-stage, optimized for project type)
   - Create CI/CD workflow for target
   - Configure environment variables

3. **Optionally Commit**
   ```
   Use AskUserQuestion tool with:
   - question: "Generated files ready. Would you like to commit them?"
   - header: "Commit"
   - options:
     - label: "Yes, commit changes"
       description: "Create a commit with the generated files"
     - label: "No, review first"
       description: "I'll review and commit manually"
   - multiSelect: false
   ```

### Output

```
/popkit:deploy setup docker

Setting up Docker deployment...

[1/4] Analyzing project for Dockerfile generation...
      ✓ Detected: Node.js 20 with Next.js 14
      ✓ Build command: npm run build
      ✓ Start command: npm start
      ✓ Port: 3000

[2/4] Generating Dockerfile...
      ✓ Multi-stage build (builder + runner)
      ✓ Optimized layer caching
      ✓ Non-root user for security
      → Dockerfile created

[3/4] Generating docker-compose.yml...
      ✓ Dev environment config
      ✓ Volume mounts for hot reload
      → docker-compose.yml created

[4/4] Generating CI/CD workflow...
      ✓ Build on push to main
      ✓ Push to ghcr.io
      → .github/workflows/docker-publish.yml created

Files created:
  - Dockerfile (multi-stage, 3 stages)
  - docker-compose.yml (dev environment)
  - .dockerignore
  - .github/workflows/docker-publish.yml

Would you like to commit these files?
```

### Template Levels

| Template | Included |
|----------|----------|
| `minimal` | Basic Dockerfile, no CI |
| `standard` | Dockerfile + CI/CD workflow |
| `production` | Standard + caching, security scanning, multi-registry |

### Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be generated without creating files |
| `--no-commit` | Generate files but don't offer to commit |
| `--template <level>` | Use template: `minimal`, `standard`, `production` |
| `--all` | Setup all configured targets |

---

## Subcommand: validate

Run pre-deployment checks to ensure everything is ready.

```
/popkit:deploy validate                 # Run all checks
/popkit:deploy validate --target docker # Validate for Docker specifically
/popkit:deploy validate --quick         # Fast checks only
/popkit:deploy validate --fix           # Auto-fix what's possible
```

### Checks Performed

| Check | Description | Auto-fix? |
|-------|-------------|-----------|
| Build | Project builds successfully | No |
| Tests | Test suite passes | No |
| Lint | No lint errors | Yes |
| TypeCheck | No type errors | No |
| Security | No critical vulnerabilities | Partial |
| Secrets | No exposed credentials | No |
| Config | Deployment config valid | Yes |
| Dependencies | All deps available | Yes |

### Process

Invokes **deployment-validator** agent:

1. **Run Quality Gates**
   - TypeScript check (if applicable)
   - Lint check
   - Test suite (unless `--quick`)

2. **Security Scan**
   - Check for exposed secrets in code
   - Check for vulnerable dependencies
   - Validate environment variable handling

3. **Config Validation**
   - Verify Dockerfile syntax (if Docker target)
   - Verify vercel.json/netlify.toml (if applicable)
   - Check CI/CD workflow syntax

### Output

```
/popkit:deploy validate

Validation Report
═════════════════

Pre-flight checks for: docker, vercel

├─ Build:      ✅ Pass (12s)
├─ Tests:      ✅ 47/47 passing (45s)
├─ Lint:       ⚠️ 2 warnings (auto-fixed)
├─ TypeCheck:  ✅ No errors
├─ Security:   ✅ No vulnerabilities
├─ Secrets:    ✅ No exposure detected
├─ Config:     ✅ Valid for docker, vercel
└─ Deps:       ✅ All available

───────────────────────────────
Ready to deploy: Yes

Warnings (2):
  - src/utils.ts:45 - Unused variable 'temp' (auto-fixed)
  - src/api.ts:12 - Missing return type (auto-fixed)

Run /popkit:deploy execute to proceed.
```

### Options

| Flag | Description |
|------|-------------|
| `--target <name>` | Validate for specific target |
| `--quick` | Skip slow checks (full test suite) |
| `--fix` | Auto-fix fixable issues |
| `--strict` | Fail on warnings too |

---

## Subcommand: execute

Deploy to configured target(s).

```
/popkit:deploy execute                  # Deploy to default target
/popkit:deploy execute docker           # Deploy Docker image
/popkit:deploy execute vercel           # Deploy to Vercel
/popkit:deploy execute npm              # Publish to npm
/popkit:deploy execute --all            # Deploy to all targets
/popkit:deploy execute --dry-run        # Show what would happen
```

### Process

1. **Pre-flight** (automatic validate)
   - Run validation checks
   - Block if critical issues found

2. **Confirm** (unless `--yes`)
   ```
   Use AskUserQuestion tool with:
   - question: "Ready to deploy v1.2.0 to docker, vercel. Proceed?"
   - header: "Deploy"
   - options:
     - label: "Yes, deploy now"
       description: "Start deployment to all targets"
     - label: "No, cancel"
       description: "Cancel deployment"
   - multiSelect: false
   ```

3. **Execute** per target
   - Docker: Build and push image
   - Vercel: Trigger deployment via CLI/CI
   - npm: Publish to registry

4. **Post-deploy Validation**
   - Health checks
   - Smoke tests (if configured)

5. **Record History**
   - Add to `deploy.json` history
   - Enable rollback capability

### Output

```
/popkit:deploy execute docker

Deploying to Docker...

[1/4] Running pre-flight checks...
      ✓ All validation checks passed

[2/4] Building Docker image...
      → Building ghcr.io/owner/repo:1.2.0
      → Stage 1/3: deps (cached)
      → Stage 2/3: builder (47s)
      → Stage 3/3: runner (3s)
      ✓ Build complete (52s)

[3/4] Pushing to registry...
      → Pushing to ghcr.io/owner/repo
      ✓ 1.2.0 pushed
      ✓ latest tag updated

[4/4] Recording deployment...
      ✓ History updated
      ✓ Rollback point saved

Deployment Complete!
═══════════════════

Target: docker
Image: ghcr.io/owner/repo:1.2.0
Duration: 1m 23s
Status: Success

Rollback available: /popkit:deploy rollback docker --to 1.1.0
```

### Options

| Flag | Description |
|------|-------------|
| `--target <name>` | Deploy to specific target |
| `--all` | Deploy to all configured targets |
| `--dry-run` | Show what would happen without deploying |
| `--yes` | Skip confirmation |
| `--version <ver>` | Override version |
| `--skip-validate` | Skip pre-flight checks (dangerous) |
| `--watch` | Watch deployment progress |

---

## Subcommand: rollback

Undo a deployment and restore previous version.

```
/popkit:deploy rollback                 # Rollback last deployment
/popkit:deploy rollback docker          # Rollback Docker specifically
/popkit:deploy rollback --to v1.1.0     # Rollback to specific version
/popkit:deploy rollback --list          # Show rollback history
```

### Process

Invokes **rollback-specialist** agent:

1. **Load History**
   - Read deployment history from `deploy.json`
   - Identify available rollback points

2. **Present Options**
   ```
   Use AskUserQuestion tool with:
   - question: "Which version would you like to rollback to?"
   - header: "Rollback"
   - options:
     - label: "v1.1.0 (previous)"
       description: "Deployed 2 hours ago, all tests passed"
     - label: "v1.0.5"
       description: "Deployed 3 days ago, stable for 72h"
     - label: "Cancel"
       description: "Don't rollback"
   - multiSelect: false
   ```

3. **Execute Rollback**
   - Docker: Re-tag previous image
   - Vercel: Revert to previous deployment
   - npm: Deprecate current, unpublish if within 24h

4. **Verify**
   - Run health checks on rolled-back version
   - Confirm functionality restored

### Output

```
/popkit:deploy rollback docker

Rollback Docker Deployment
══════════════════════════

Current version: 1.2.0 (deployed 30m ago)

Available rollback points:
  1. v1.1.0 - Deployed 2 hours ago (success)
  2. v1.0.5 - Deployed 3 days ago (success)
  3. v1.0.4 - Deployed 5 days ago (success)

Which version would you like to rollback to?

[User selects v1.1.0]

Rolling back to v1.1.0...

[1/3] Re-tagging image...
      ✓ ghcr.io/owner/repo:1.1.0 → latest

[2/3] Updating deployment...
      ✓ Kubernetes deployment updated
      ✓ Pods rolling update started

[3/3] Verifying rollback...
      ✓ Health check passed
      ✓ Smoke tests passed

Rollback Complete!
══════════════════

Rolled back: 1.2.0 → 1.1.0
Duration: 45s
Status: Success

Note: v1.2.0 is still available in registry for future deployment.
```

### Options

| Flag | Description |
|------|-------------|
| `--to <version>` | Rollback to specific version |
| `--target <name>` | Rollback specific target only |
| `--list` | Show rollback history |
| `--yes` | Skip confirmation |

---

## Deployment Targets

### Docker (Universal)

Any server/cloud that runs containers. Most flexible option.

**Generated:**
- `Dockerfile` (multi-stage, optimized)
- `docker-compose.yml` (dev environment)
- `.dockerignore`
- `.github/workflows/docker-publish.yml`

**Execution:**
- Build image locally or trigger CI
- Push to registry (Docker Hub, GHCR, ECR)
- Optionally deploy to cloud

### Vercel/Netlify (Frontend)

Static sites, SSR apps, serverless functions.

**Generated:**
- `vercel.json` or `netlify.toml`
- Environment variable templates
- `.github/workflows/preview-deploy.yml`

**Execution:**
- Trigger deployment via CLI
- Handle preview deployments for PRs
- Production deploy on main branch

### npm/PyPI (Packages)

Library/package publishing.

**Generated:**
- Validates `package.json` / `pyproject.toml`
- `.github/workflows/npm-publish.yml` or `pypi-publish.yml`
- Auth config templates

**Execution:**
- Version bump assistance
- Changelog generation
- Registry publish

### GitHub Releases (Binaries)

CLI tools, compiled artifacts.

**Generated:**
- `.github/workflows/release.yml`
- Release asset configuration
- Changelog automation

**Execution:**
- Create GitHub release
- Upload compiled assets
- Generate release notes

---

## Premium Features

| Feature | Free | Pro | Team |
|---------|------|-----|------|
| `deploy init` | ✅ | ✅ | ✅ |
| `deploy validate` | ✅ | ✅ | ✅ |
| `deploy setup` (basic) | ✅ | ✅ | ✅ |
| `deploy setup` (custom) | ❌ | ✅ | ✅ |
| `deploy execute` (local) | ✅ | ✅ | ✅ |
| `deploy execute` (cloud) | ❌ | ✅ | ✅ |
| `deploy rollback` | ❌ | ✅ | ✅ |
| Multi-target deploy | ❌ | ✅ | ✅ |
| Deploy history (cloud) | ❌ | 7-day | 90-day |

---

## Examples

```bash
# Initialize deployment configuration
/popkit:deploy
/popkit:deploy init

# Setup Docker deployment
/popkit:deploy setup docker
/popkit:deploy setup docker --template production

# Validate before deploying
/popkit:deploy validate
/popkit:deploy validate --quick

# Deploy to Docker
/popkit:deploy execute docker
/popkit:deploy execute docker --dry-run

# Deploy to multiple targets
/popkit:deploy execute --all

# Rollback if something goes wrong
/popkit:deploy rollback docker --to v1.1.0
```

---

## Workflow Integration

```
/popkit:project init       → PopKit configuration
         ↓
/popkit:deploy init        → Deployment targets
         ↓
/popkit:deploy setup       → Generate configs
         ↓
/popkit:deploy validate    → Pre-flight checks
         ↓
/popkit:deploy execute     → Ship it!
         ↓
/popkit:deploy rollback    → Undo if needed
```

**Related Commands:**
- `/popkit:git pr` → Code workflow
- `/popkit:git release` → Version tagging
- `/popkit:routine morning` → Check deployment health

---

## Agent Integration

| Agent | Role |
|-------|------|
| `devops-automator` | Generate CI/CD configs, Dockerfiles |
| `deployment-validator` | Pre/post deployment checks |
| `rollback-specialist` | Recovery procedures |
| `security-auditor` | Secrets scanning |

---

## Configuration

### deploy.json Schema

Located at `.claude/popkit/deploy.json`:

```json
{
  "version": "1.0",
  "project_type": "web-app",
  "targets": ["docker", "vercel"],
  "state": "configured",
  "initialized_at": "2025-12-10T10:00:00Z",
  "initialized_by": "popkit-1.2.0",

  "github": {
    "repo": "owner/repo",
    "default_branch": "main",
    "has_actions": true
  },

  "target_configs": {
    "docker": {
      "registry": "ghcr.io",
      "image_name": "owner/repo",
      "dockerfile": "Dockerfile"
    },
    "vercel": {
      "project_id": "prj_xxx",
      "team_id": null
    }
  },

  "history": [
    {
      "version": "1.2.0",
      "targets": ["docker"],
      "timestamp": "2025-12-10T15:00:00Z",
      "status": "success",
      "duration_seconds": 154,
      "commit": "abc123",
      "rollback_available": true
    }
  ],

  "last_deployment": {
    "version": "1.2.0",
    "timestamp": "2025-12-10T15:00:00Z",
    "status": "success"
  }
}
```

---

## Architecture Integration

| Component | Integration |
|-----------|-------------|
| Deploy Init Skill | `skills/pop-deploy-init/SKILL.md` |
| Deploy Config | `.claude/popkit/deploy.json` |
| DevOps Agent | `agents/tier-2-on-demand/devops-automator/` |
| Validator Agent | `agents/tier-2-on-demand/deployment-validator/` |
| Rollback Agent | `agents/tier-2-on-demand/rollback-specialist/` |
| Premium Gating | `hooks/utils/premium_checker.py` |
