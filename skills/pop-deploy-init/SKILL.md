---
name: deploy-init
description: "Analyze project deployment readiness and initialize deployment configuration. Use when user runs /popkit:deploy or /popkit:deploy init. Detects project state (GitHub, CI/CD, targets), collects user intent through AskUserQuestion, and creates .claude/popkit/deploy.json configuration file. Do NOT use if deploy.json already exists - use deploy-validate instead."
---

# Deploy Initialization

## Overview

Establish deployment infrastructure for any project state - from no GitHub to production-ready CI/CD. Uses progressive disclosure to adapt the experience based on detected project capabilities.

**Core principle:** Front-load user intent before analyzing gaps, then fill gaps systematically.

**Trigger:** `/popkit:deploy` or `/popkit:deploy init` command

## Critical Rules

1. **NEVER overwrite existing deploy.json** - If exists, error and suggest `/popkit:deploy init --force`
2. **ALWAYS front-load user intent** - Ask questions BEFORE running analysis
3. **ALWAYS use AskUserQuestion tool** for all user decisions (enforced by hooks)
4. **Verify `.claude/popkit/` exists** - Run `/popkit:project init` if missing
5. **Progressive disclosure** - Only show relevant options based on project state
6. **Store configuration in deploy.json** - Required for all deploy subcommands

## Required Decision Points

This skill has **3 mandatory user decision points** that MUST use the AskUserQuestion tool:

| Step | When | Decision ID |
|------|------|-------------|
| Step 1 | Always (front-load intent) | `deployment_intent` |
| Step 5 | After analysis complete | `github_setup` (conditional) |
| Step 7 | After config created | `next_action` |

**WARNING:** Skipping these prompts violates the PopKit UX standard. The hook system tracks these decisions.

## Initialization Process

### Step 0: Pre-flight Checks

Check that PopKit is initialized:

```bash
# Verify .claude/popkit/ directory exists
if [ ! -d ".claude/popkit" ]; then
  echo "❌ PopKit not initialized"
  echo "Run: /popkit:project init"
  exit 1
fi

# Check if deploy.json already exists
if [ -f ".claude/popkit/deploy.json" ] && [ "$FORCE" != "true" ]; then
  echo "❌ Deployment already configured"
  echo "To re-initialize: /popkit:deploy init --force"
  exit 1
fi
```

### Step 1: Front-Load User Intent (MANDATORY AskUserQuestion)

**CRITICAL:** Ask ALL intent questions in a SINGLE AskUserQuestion call with multiple questions.

Use AskUserQuestion tool with:

**Question 1:**
```
question: "What type of project are you deploying?"
header: "Project"
options:
  - label: "Web application"
    description: "Frontend, fullstack, or SSR application (React, Next.js, Vue, etc.)"
  - label: "Backend API/service"
    description: "REST API, GraphQL server, microservice, etc."
  - label: "CLI tool or library"
    description: "Command-line tool or reusable package/library"
  - label: "Other"
    description: "Describe your project type"
multiSelect: false
```

**Question 2:**
```
question: "Where do you want to deploy? (Select all that apply)"
header: "Targets"
options:
  - label: "Docker"
    description: "Universal - works on any server or cloud platform"
  - label: "Vercel/Netlify"
    description: "Frontend hosting with automatic previews"
  - label: "npm/PyPI registry"
    description: "Package publishing for libraries and tools"
  - label: "GitHub Releases"
    description: "Binary artifacts and release notes"
multiSelect: true
```

**Question 3:**
```
question: "What's your current deployment setup?"
header: "State"
options:
  - label: "Starting fresh"
    description: "No GitHub repo, no CI/CD - build from scratch"
  - label: "Have GitHub, need CI/CD"
    description: "Repo exists but no automated pipelines"
  - label: "Have CI/CD, need targets"
    description: "Workflows exist but need deployment configs"
  - label: "Everything exists"
    description: "Just need orchestration shortcuts"
multiSelect: false
```

Store responses for later use.

### Step 2: Detect Project Type

Automatically detect project language and framework:

```bash
# Detect from package files
if [ -f "package.json" ]; then
  lang="javascript"

  # Check for frameworks
  if grep -q '"next"' package.json; then
    framework="nextjs"
  elif grep -q '"vite"' package.json; then
    framework="vite"
  elif grep -q '"react"' package.json; then
    framework="react"
  else
    framework="node"
  fi

elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  lang="python"

  # Check for frameworks
  if [ -f "manage.py" ]; then
    framework="django"
  elif grep -q "flask" requirements.txt 2>/dev/null; then
    framework="flask"
  elif grep -q "fastapi" requirements.txt 2>/dev/null; then
    framework="fastapi"
  else
    framework="python"
  fi

elif [ -f "Cargo.toml" ]; then
  lang="rust"
  framework="cargo"

elif [ -f "go.mod" ]; then
  lang="go"
  framework="go"

else
  lang="unknown"
  framework="generic"
fi
```

### Step 3: Detect GitHub State

Check GitHub configuration:

```bash
# Check if git repo exists
if [ ! -d ".git" ]; then
  git_initialized=false
  has_remote=false
  has_github_actions=false
else
  git_initialized=true

  # Check for remote
  if git remote -v | grep -q "github.com"; then
    has_remote=true

    # Extract repo from remote
    repo=$(git remote get-url origin | sed -E 's/.*github\.com[:/](.+)\.git/\1/')

    # Get default branch
    default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
    [ -z "$default_branch" ] && default_branch="main"
  else
    has_remote=false
  fi

  # Check for GitHub Actions
  if [ -d ".github/workflows" ]; then
    has_github_actions=true
  else
    has_github_actions=false
  fi
fi
```

### Step 4: Detect CI/CD State

Check for existing CI/CD configurations:

```bash
# Initialize detection results
cicd_detected=false
cicd_platform=""

# Check for GitHub Actions
if [ -d ".github/workflows" ]; then
  cicd_detected=true
  cicd_platform="github-actions"

  # Count workflow files
  workflow_count=$(ls -1 .github/workflows/*.yml 2>/dev/null | wc -l)
fi

# Check for other CI platforms
if [ -f ".gitlab-ci.yml" ]; then
  cicd_detected=true
  cicd_platform="gitlab-ci"
fi

if [ -f ".circleci/config.yml" ]; then
  cicd_detected=true
  cicd_platform="circleci"
fi

if [ -f "azure-pipelines.yml" ]; then
  cicd_detected=true
  cicd_platform="azure-pipelines"
fi
```

### Step 5: GitHub Setup Decision (Conditional AskUserQuestion)

**ONLY if** user selected "Starting fresh" AND no GitHub repo exists:

Use AskUserQuestion tool with:
```
question: "Would you like to set up GitHub now?"
header: "GitHub"
options:
  - label: "Yes, create repo"
    description: "I'll help create a GitHub repo and push your code"
  - label: "Skip for now"
    description: "I'll configure deployment locally, you can add GitHub later"
multiSelect: false
```

If user selects "Yes, create repo":
1. Run `gh repo create` (if gh CLI available)
2. Initialize git if needed
3. Create initial commit
4. Push to GitHub

### Step 6: Create Configuration File

Build the deploy.json configuration:

```json
{
  "version": "1.0",
  "project_type": "<from user question 1>",
  "language": "<detected in step 2>",
  "framework": "<detected in step 2>",
  "targets": ["<from user question 2>"],
  "state": "<from user question 3>",
  "initialized_at": "<ISO timestamp>",
  "initialized_by": "popkit-<version>",
  "github": {
    "initialized": <boolean>,
    "repo": "<owner/repo or null>",
    "default_branch": "<branch or null>",
    "has_actions": <boolean>
  },
  "cicd": {
    "detected": <boolean>,
    "platform": "<platform or null>",
    "workflow_count": <number>
  },
  "gaps": {
    "needs_github": <boolean>,
    "needs_cicd": <boolean>,
    "needs_target_configs": <boolean>
  },
  "history": [
    {
      "action": "init",
      "timestamp": "<ISO timestamp>",
      "user": "<git user.name>",
      "version": "popkit-<version>"
    }
  ]
}
```

Write to `.claude/popkit/deploy.json`:

```bash
cat > .claude/popkit/deploy.json <<'EOF'
{json content here}
EOF
```

### Step 7: Summary and Next Action (MANDATORY AskUserQuestion)

Display summary of what was detected and configured:

```
Deployment Configuration Created:

📦 Project Type: <type>
🎯 Targets: <comma-separated list>
📊 State: <state>

Detected:
├─ Language: <language>
├─ Framework: <framework>
├─ GitHub: <✅ or ❌>
├─ CI/CD: <✅ or ❌>
└─ Config: .claude/popkit/deploy.json

Gaps Identified:
<list of gaps if any>
```

Then use AskUserQuestion tool with:
```
question: "Configuration complete. What would you like to do next?"
header: "Next Step"
options:
  - label: "Setup targets"
    description: "Run /popkit:deploy setup to generate CI/CD and target configs"
  - label: "Validate readiness"
    description: "Run /popkit:deploy validate to check if ready to deploy"
  - label: "Done for now"
    description: "I'll continue manually"
multiSelect: false
```

If user selects "Setup targets", invoke `/popkit:deploy setup`.
If user selects "Validate readiness", invoke `/popkit:deploy validate`.

## Configuration Schema

The deploy.json file schema:

```typescript
interface DeployConfig {
  version: string;              // Config schema version (currently "1.0")
  project_type: string;         // "web-app" | "backend-api" | "cli-tool" | "library" | "other"
  language: string;             // Detected language: "javascript" | "python" | "rust" | "go" | etc.
  framework: string;            // Detected framework: "nextjs" | "react" | "django" | "fastapi" | etc.
  targets: string[];            // Selected deployment targets
  state: string;                // User-selected initial state
  initialized_at: string;       // ISO timestamp
  initialized_by: string;       // PopKit version

  github: {
    initialized: boolean;       // Is git initialized?
    repo: string | null;        // "owner/repo" or null
    default_branch: string | null;
    has_actions: boolean;       // .github/workflows/ exists?
  };

  cicd: {
    detected: boolean;          // Any CI/CD found?
    platform: string | null;    // "github-actions" | "gitlab-ci" | etc.
    workflow_count: number;     // Number of workflow files
  };

  gaps: {
    needs_github: boolean;      // True if no GitHub setup
    needs_cicd: boolean;        // True if no CI/CD pipelines
    needs_target_configs: boolean; // True if targets not configured
  };

  history: Array<{
    action: string;             // "init" | "setup" | "deploy" | etc.
    timestamp: string;          // ISO timestamp
    user: string;               // Git user.name
    version: string;            // PopKit version
  }>;
}
```

## Flags

| Flag | Description |
|------|-------------|
| `--force` | Re-run init even if deploy.json exists (overwrites) |
| `--skip-github` | Don't offer GitHub setup (useful for local-only projects) |
| `--json` | Output configuration as JSON instead of summary |
| `--dry-run` | Show what would be created without writing files |

## Error Handling

### PopKit Not Initialized

```
❌ PopKit not initialized in this project

Run /popkit:project init to set up PopKit first.
Then run /popkit:deploy init again.
```

### Already Configured

```
❌ Deployment already configured

Config exists at: .claude/popkit/deploy.json

To re-initialize: /popkit:deploy init --force
To update config: /popkit:deploy setup
```

### Git Not Initialized

If user wants GitHub but git not initialized:

```
⚠️ Git repository not initialized

Would you like me to:
1. Initialize git repo
2. Create .gitignore
3. Make initial commit
```

### No GitHub CLI

If user wants to create GitHub repo but `gh` CLI not available:

```
⚠️ GitHub CLI (gh) not found

Install it to create repos automatically:
  brew install gh        (macOS)
  winget install GitHub.cli  (Windows)

Or create repo manually at: https://github.com/new
Then run: git remote add origin <repo-url>
```

## Integration Points

### Commands
- `/popkit:deploy` - Runs this skill by default if no config exists
- `/popkit:deploy init` - Explicit invocation
- `/popkit:deploy setup` - Next step after init

### Skills
- `pop-project-init` - Must run before this skill
- `pop-deploy-setup` - Next skill in deployment workflow
- `pop-deploy-validate` - Validation skill

### Agents
- `devops-automator` - For GitHub setup and CI/CD generation (used in setup phase)
- `deployment-validator` - For readiness checks (used in validate phase)

### Hooks
- `pre-tool-use.py` - Tracks skill invocation
- `post-tool-use.py` - Verifies AskUserQuestion completion decisions were used

## Testing

Validate the skill works correctly:

```bash
# Test basic init
/popkit:deploy init

# Test force re-init
/popkit:deploy init --force

# Test with flags
/popkit:deploy init --skip-github --json
```

Verify created files:
```bash
# Check config file
cat .claude/popkit/deploy.json | jq .

# Verify schema
jq '.version, .project_type, .targets, .gaps' .claude/popkit/deploy.json
```

## Success Criteria

✅ User intent collected via AskUserQuestion (all 3 questions)
✅ Project type auto-detected correctly
✅ GitHub state detected correctly
✅ CI/CD state detected correctly
✅ deploy.json created with valid schema
✅ Gaps identified correctly
✅ Next action offered via AskUserQuestion
✅ All mandatory decision points enforced

## Notes

- This skill implements Phase 1 of the deploy command design
- Progressive disclosure: Only show GitHub setup if user needs it
- Front-loading: Ask ALL questions upfront before analysis
- Configuration file: Central source of truth for deploy command
- History tracking: Every action logged for audit trail
