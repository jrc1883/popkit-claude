---
name: deploy-init
description: "Analyze project deployment readiness and initialize deployment configuration. Use when user runs /popkit:deploy or /popkit:deploy init. Detects project state (GitHub, CI/CD, targets), collects user intent through AskUserQuestion, and creates .claude/popkit/deploy.json configuration file. Do NOT use if deploy.json already exists - use deploy-validate instead."
---

# Deploy Initialization

## Overview

Establish deployment infrastructure for any project state - from no GitHub to production-ready CI/CD.

**Core principle:** Front-load user intent before analyzing gaps, then fill gaps systematically using programmatic scripts.

**Trigger:** `/popkit:deploy` or `/popkit:deploy init` command

## Workflow

### 1. Pre-flight Checks

```bash
# Verify PopKit initialized
test -d .claude/popkit || {
  echo "❌ PopKit not initialized"
  echo "Run: /popkit:project init"
  exit 1
}

# Check if already configured (unless --force)
test -f .claude/popkit/deploy.json && [ "$FORCE" != "true" ] && {
  echo "❌ Deployment already configured"
  echo "To re-initialize: /popkit:deploy init --force"
  exit 1
}
```

### 2. Run Detection Script

Execute programmatic detection:

```bash
# Run detection and save results
python scripts/detect_project.py --dir . --json > /tmp/detection.json

# Parse detection results
LANGUAGE=$(jq -r '.language' /tmp/detection.json)
FRAMEWORK=$(jq -r '.framework' /tmp/detection.json)
DETECTED_STATE=$(jq -r '.detected_state' /tmp/detection.json)
```

**Script:** `scripts/detect_project.py`
- Detects language (JavaScript, Python, Rust, Go, etc.)
- Detects framework (Next.js, FastAPI, React, Django, etc.)
- Analyzes GitHub state (initialized, repo, branch, actions)
- Analyzes CI/CD state (detected, platform, workflow count)
- Computes gaps (needs GitHub, CI/CD, target configs)

### 3. Front-Load User Intent (MANDATORY AskUserQuestion)

**CRITICAL:** Ask ALL intent questions in a SINGLE AskUserQuestion call with multiple questions.

Use AskUserQuestion tool with 3 questions:

**Question 1 - Project Type:**
```
question: "What type of project are you deploying?"
header: "Project"
options:
  - label: "Web application"
    description: "Frontend, fullstack, or SSR (React, Next.js, Vue)"
  - label: "Backend API/service"
    description: "REST API, GraphQL server, microservice"
  - label: "CLI tool or library"
    description: "Command-line tool or reusable package"
  - label: "Other"
    description: "Describe your project type"
multiSelect: false
```

**Question 2 - Deployment Targets:**
```
question: "Where do you want to deploy? (Select all that apply)"
header: "Targets"
options:
  - label: "Docker"
    description: "Universal - any server or cloud platform"
  - label: "Vercel/Netlify"
    description: "Frontend hosting with automatic previews"
  - label: "npm/PyPI registry"
    description: "Package publishing for libraries"
  - label: "GitHub Releases"
    description: "Binary artifacts and release notes"
multiSelect: true
```

**Question 3 - Current State:**
```
question: "What's your current deployment setup?"
header: "State"
options:
  - label: "Starting fresh"
    description: "No GitHub repo, no CI/CD"
  - label: "Have GitHub, need CI/CD"
    description: "Repo exists but no pipelines"
  - label: "Have CI/CD, need targets"
    description: "Workflows exist, need deployment configs"
  - label: "Everything exists"
    description: "Just need orchestration"
multiSelect: false
```

Store responses for config generation.

### 4. (Optional) GitHub Setup Decision

**ONLY if** user selected "Starting fresh" AND detection shows no GitHub repo:

Use AskUserQuestion tool with:
```
question: "Would you like to set up GitHub now?"
header: "GitHub"
options:
  - label: "Yes, create repo"
    description: "I'll help create a GitHub repo and push code"
  - label: "Skip for now"
    description: "Configure locally, add GitHub later"
multiSelect: false
```

If "Yes, create repo":
```bash
# Initialize git if needed
[ -d .git ] || git init

# Create GitHub repo (if gh CLI available)
gh repo create --source=. --public

# Push to GitHub
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 5. Create Configuration

Execute config generation script:

```bash
# Build targets argument
TARGETS=$(echo "$USER_TARGETS" | jq -R 'split(",") | map(gsub(" "; ""))')

# Create configuration
python scripts/create_config.py \
  --project-type "$USER_PROJECT_TYPE" \
  --targets "$TARGETS" \
  --state "$USER_STATE" \
  --detection /tmp/detection.json \
  --output .claude/popkit/deploy.json
```

**Script:** `scripts/create_config.py`
- Loads detection results
- Merges with user-selected options
- Generates deploy.json from template
- Adds history entry with timestamp, user, version

**Output:** `.claude/popkit/deploy.json` with full schema

### 6. Validate Configuration

Run validation script:

```bash
# Validate schema
python scripts/validate_config.py --config .claude/popkit/deploy.json

# Check validation passed
if [ $? -ne 0 ]; then
  echo "⚠️  Configuration created but validation failed"
  echo "Check: python scripts/validate_config.py"
fi
```

**Script:** `scripts/validate_config.py`
- Validates all required fields present
- Checks version compatibility
- Validates GitHub repo format
- Validates CI/CD configuration
- Checks history has init entry
- Validates timestamp formats

### 7. Run Checklist

Execute automated checklist:

```bash
# Run automated checks
python -c "
import json
import subprocess

checklist = json.load(open('checklists/init-checklist.json'))
for category in checklist['categories']:
    for check in category['checks']:
        if check.get('automated') and check.get('script'):
            result = subprocess.run(check['script'], shell=True, capture_output=True)
            status = '✅' if 'PASS' in result.stdout.decode() else '❌'
            print(f\"{status} {check['name']}\")
"
```

**Checklist:** `checklists/init-checklist.json`
- Pre-flight checks
- Project detection
- User intent collection
- Configuration creation
- Schema validation
- Gap analysis
- User experience

### 8. Display Summary

```bash
# Load config
CONFIG=$(cat .claude/popkit/deploy.json)

# Display summary
cat <<EOF

Deployment Configuration Created:

📦 Project Type: $(echo "$CONFIG" | jq -r '.project_type')
🎯 Targets: $(echo "$CONFIG" | jq -r '.targets | join(", ")')
📊 State: $(echo "$CONFIG" | jq -r '.state')

Detected:
├─ Language: $(echo "$CONFIG" | jq -r '.language')
├─ Framework: $(echo "$CONFIG" | jq -r '.framework')
├─ GitHub: $(echo "$CONFIG" | jq -r 'if .github.initialized then "✅" else "❌" end')
├─ CI/CD: $(echo "$CONFIG" | jq -r 'if .cicd.detected then "✅" else "❌" end')
└─ Config: .claude/popkit/deploy.json

Gaps Identified:
$(echo "$CONFIG" | jq -r '.gaps | to_entries | map("  - \(.key): \(if .value then "❌ needed" else "✅ ready" end)") | .[]')

EOF
```

### 9. Next Action (MANDATORY AskUserQuestion)

Use AskUserQuestion tool with:
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

## Required Decision Points

This skill has **3-4 mandatory user decision points** that MUST use the AskUserQuestion tool:

| Step | When | Decision ID | Required |
|------|------|-------------|----------|
| Step 3 | Always | `deployment_intent` | Yes (3 questions) |
| Step 4 | Conditional | `github_setup` | Only if fresh + no GitHub |
| Step 9 | Always | `next_action` | Yes |

**WARNING:** Skipping these prompts violates the PopKit UX standard. The hook system tracks these decisions.

## Scripts Reference

### scripts/detect_project.py

**Purpose:** Detect project deployment state

**Usage:**
```bash
python scripts/detect_project.py [--dir DIR] [--json]
```

**Output:** JSON with language, framework, GitHub state, CI/CD state, gaps

**Example:**
```bash
python scripts/detect_project.py --dir . --json > /tmp/detection.json
```

### scripts/create_config.py

**Purpose:** Generate deploy.json configuration

**Usage:**
```bash
python scripts/create_config.py \
  --project-type TYPE \
  --targets TARGET1,TARGET2 \
  --state STATE \
  [--detection FILE] \
  [--output PATH] \
  [--dry-run]
```

**Example:**
```bash
python scripts/create_config.py \
  --project-type web-app \
  --targets docker,vercel \
  --state fresh \
  --detection /tmp/detection.json \
  --output .claude/popkit/deploy.json
```

### scripts/validate_config.py

**Purpose:** Validate deploy.json schema

**Usage:**
```bash
python scripts/validate_config.py [--config PATH] [--strict] [--json]
```

**Example:**
```bash
python scripts/validate_config.py --config .claude/popkit/deploy.json
```

## Templates Reference

### templates/deploy.json.template

**Purpose:** Base template for config generation

**Placeholders:**
- `{{VERSION}}` - Schema version (1.0)
- `{{PROJECT_TYPE}}` - User-selected type
- `{{LANGUAGE}}` - Detected language
- `{{FRAMEWORK}}` - Detected framework
- `{{TARGETS}}` - JSON array of targets
- `{{STATE}}` - User-selected state
- `{{TIMESTAMP}}` - ISO 8601 timestamp
- `{{POPKIT_VERSION}}` - PopKit version
- `{{GITHUB_*}}` - GitHub state fields
- `{{CICD_*}}` - CI/CD state fields
- `{{NEEDS_*}}` - Gap analysis fields
- `{{GIT_USER}}` - Git user.name

## Checklists Reference

### checklists/init-checklist.json

**Purpose:** Automated verification of initialization

**Categories:**
1. Pre-flight Checks (2 checks)
2. Project Detection (4 checks)
3. User Intent Collection (3 checks)
4. Configuration Creation (10 checks)
5. Schema Validation (2 checks)
6. Gap Analysis (2 checks)
7. User Experience (3 checks)

**Total:** 26 checks (19 automated, 7 manual)

## Flags

| Flag | Description |
|------|-------------|
| `--force` | Re-run init even if deploy.json exists (overwrites) |
| `--skip-github` | Don't offer GitHub setup |
| `--json` | Output config as JSON instead of summary |
| `--dry-run` | Show what would be created without writing |

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

### Detection Failed

```
⚠️ Could not auto-detect project type

Please select your project type manually.
```

### Validation Failed

```
⚠️ Configuration created but validation failed

Run: python scripts/validate_config.py
Fix issues and re-run /popkit:deploy init --force
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
- `devops-automator` - For GitHub setup and CI/CD generation (Phase 2+)
- `deployment-validator` - For readiness checks (Phase 3)
- `rollback-specialist` - For emergency rollback (Phase 7)

### Hooks
- `pre-tool-use.py` - Tracks skill invocation
- `post-tool-use.py` - Verifies AskUserQuestion completion decisions

## Testing

Test the skill programmatically:

```bash
# Test detection script
python scripts/detect_project.py --dir . --json

# Test config creation (dry run)
python scripts/create_config.py \
  --project-type web-app \
  --targets docker \
  --state fresh \
  --dry-run

# Test validation
python scripts/validate_config.py --config .claude/popkit/deploy.json

# Run automated checklist
python -c "
import json
checklist = json.load(open('checklists/init-checklist.json'))
for script in checklist['scripts'].values():
    print(f'Running: {script}')
"
```

## Success Criteria

✅ User intent collected via AskUserQuestion (3-4 questions)
✅ Detection script executed successfully
✅ Project type, language, framework auto-detected
✅ GitHub state detected correctly
✅ CI/CD state detected correctly
✅ deploy.json created with valid schema
✅ Validation script passes
✅ Automated checklist passes
✅ Gaps identified correctly
✅ Next action offered via AskUserQuestion

## Notes

- **Programmatic first:** All logic in Python scripts, not embedded bash
- **Front-loading:** Ask ALL questions upfront before analysis
- **Progressive disclosure:** Only show GitHub setup if needed
- **Validation:** Always validate config after creation
- **Checklists:** Automated verification of all steps
- **Templates:** Config generated from template with placeholders
- **History tracking:** Every action logged for audit trail
