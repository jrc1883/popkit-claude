# Monorepo Conversion Implementation Plan

> **For Claude:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** Convert PopKit from separate repos to a monorepo with packages structure.

**Architecture:** Create a packages/ directory containing plugin/ (current PopKit content) and cloud/ (from popkit-cloud repo). Root-level files (CLAUDE.md, README.md) stay at root. Use npm workspaces for package management.

**Tech Stack:** npm workspaces, git subtree (for importing cloud repo history)

**GitHub Issue:** #98

---

## Pre-Flight Checks

Before starting, verify:
- [ ] All current changes committed
- [ ] popkit-cloud repo is at `../popkit-cloud/`
- [ ] No uncommitted changes in popkit-cloud

---

### Task 1: Create packages directory structure

**Files:**
- Create: `packages/` directory
- Create: `packages/plugin/` directory

**Step 1: Verify clean git state**

Run: `git status`
Expected: "nothing to commit, working tree clean"

**Step 2: Create packages directory**

```bash
mkdir -p packages/plugin
```

**Step 3: Commit structure**

```bash
git add packages/
git commit -m "chore: create packages/ directory structure for monorepo"
```

---

### Task 2: Move plugin content to packages/plugin/

**Files:**
- Move: All current directories and files to `packages/plugin/`
- Keep at root: `.git/`, `packages/`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `.gitignore`

**Step 1: Move plugin directories**

```bash
# Move all plugin content
git mv .claude-plugin packages/plugin/
git mv .mcp.json packages/plugin/
git mv agents packages/plugin/
git mv commands packages/plugin/
git mv hooks packages/plugin/
git mv output-styles packages/plugin/
git mv power-mode packages/plugin/
git mv skills packages/plugin/
git mv templates packages/plugin/
git mv tests packages/plugin/
git mv docs packages/plugin/
git mv CONTRIBUTING.md packages/plugin/
```

**Step 2: Move remaining plugin files**

```bash
# Move test files and other plugin-specific files
git mv test_cloud_e2e.py packages/plugin/
git mv test_insight_embedder.py packages/plugin/
git mv nul packages/plugin/ 2>/dev/null || true
```

**Step 3: Handle .github directory**

```bash
# Keep .github at root (for repo-level workflows)
# But move issue templates if they're plugin-specific
# For now, keep at root
```

**Step 4: Commit the move**

```bash
git add -A
git commit -m "refactor: move plugin content to packages/plugin/"
```

---

### Task 3: Import popkit-cloud as packages/cloud/

**Files:**
- Create: `packages/cloud/` with content from `../popkit-cloud/`

**Step 1: Copy cloud content (without .git)**

```bash
# Copy cloud-api content
cp -r ../popkit-cloud/cloud-api packages/cloud

# Copy other relevant directories
cp -r ../popkit-cloud/billing packages/cloud-billing 2>/dev/null || true
cp -r ../popkit-cloud/team packages/cloud-team 2>/dev/null || true
cp -r ../popkit-cloud/scripts packages/cloud-scripts 2>/dev/null || true
cp -r ../popkit-cloud/docs packages/cloud-docs 2>/dev/null || true
```

Note: We're copying (not git subtree) to keep things simple. The cloud repo can be archived after verification.

**Step 2: Add cloud to git**

```bash
git add packages/cloud packages/cloud-*
git commit -m "feat: import cloud-api into packages/cloud"
```

---

### Task 4: Create root package.json with workspaces

**Files:**
- Create: `package.json` (root)

**Step 1: Create root package.json**

Create file `package.json`:

```json
{
  "name": "popkit-monorepo",
  "version": "0.9.9",
  "private": true,
  "description": "PopKit - AI-powered development workflows",
  "workspaces": [
    "packages/*"
  ],
  "scripts": {
    "test:plugin": "cd packages/plugin && npm test",
    "deploy:cloud": "cd packages/cloud && npm run deploy",
    "lint": "npm run lint --workspaces --if-present"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/jrc1883/popkit.git"
  },
  "author": "Joseph Cannon",
  "license": "MIT"
}
```

**Step 2: Commit package.json**

```bash
git add package.json
git commit -m "chore: add root package.json with workspaces"
```

---

### Task 5: Update CLAUDE.md paths

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update repository structure section**

Update the Repository Structure section to reflect new paths:

```markdown
## Repository Structure

<!-- AUTO-GEN:REPO-STRUCTURE START -->
```
packages/
  plugin/              # Claude Code plugin (main product)
    .claude-plugin/    Plugin manifest (plugin.json, marketplace.json)
    .mcp.json          MCP server configuration
    agents/            30 agent definitions with tiered activation
    skills/            36 reusable skills
    commands/          15 slash commands
    hooks/             22 Python hooks
    ...
  cloud/               # PopKit Cloud API (Cloudflare Workers)
    src/               API source code
    wrangler.toml      Cloudflare config
package.json           Workspace root
CLAUDE.md              This file
CHANGELOG.md           Version history
```
<!-- AUTO-GEN:REPO-STRUCTURE END -->
```

**Step 2: Update key files section paths**

Update paths in Key Files table to include `packages/plugin/` prefix for plugin files.

**Step 3: Commit CLAUDE.md updates**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md paths for monorepo structure"
```

---

### Task 6: Update README.md for monorepo

**Files:**
- Modify: `README.md`

**Step 1: Update README structure section**

Add monorepo structure to README:

```markdown
## Repository Structure

This is a monorepo containing:

| Package | Description |
|---------|-------------|
| `packages/plugin` | Claude Code plugin - agents, skills, commands, hooks |
| `packages/cloud` | PopKit Cloud API - Cloudflare Workers backend |

## Development

```bash
# Install all dependencies
npm install

# Run plugin tests
npm run test:plugin

# Deploy cloud API
npm run deploy:cloud
```
```

**Step 2: Commit README updates**

```bash
git add README.md
git commit -m "docs: update README for monorepo structure"
```

---

### Task 7: Update .gitignore for monorepo

**Files:**
- Modify: `.gitignore`

**Step 1: Update .gitignore**

Add monorepo-specific ignores:

```
# Monorepo
node_modules/
packages/*/node_modules/

# Cloud API
packages/cloud/.wrangler/
packages/cloud/.dev.vars

# Existing ignores...
```

**Step 2: Commit .gitignore**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for monorepo"
```

---

### Task 8: Verify and test

**Step 1: Verify structure**

```bash
ls -la packages/
ls -la packages/plugin/
ls -la packages/cloud/
```

Expected: Both directories contain their respective content.

**Step 2: Run plugin tests**

```bash
cd packages/plugin
python -c "import json; json.load(open('.claude-plugin/plugin.json'))" && echo "PASS: plugin.json valid"
```

**Step 3: Verify git history preserved**

```bash
git log --oneline -10
```

Expected: All previous commits visible, plus new monorepo commits.

---

### Task 9: Push and update issue

**Step 1: Push changes**

```bash
git push
```

**Step 2: Close issue #98**

```bash
gh issue close 98 --comment "Monorepo conversion complete. Structure:
- packages/plugin/ - Claude Code plugin
- packages/cloud/ - PopKit Cloud API

All git history preserved. Ready for unified development."
```

---

## Post-Migration Tasks (Manual)

After completing this plan:

1. **Archive popkit-cloud repo** - Mark as archived on GitHub since content is now in monorepo
2. **Update any CI/CD** - If there are GitHub Actions, update paths
3. **Test plugin installation** - Verify `/plugin update` still works with new structure
4. **Update Epic #67** - Mark as consolidated into monorepo

---

## Rollback Plan

If something goes wrong:

```bash
# Reset to before monorepo changes
git log --oneline  # Find commit before "create packages/ directory"
git reset --hard <commit-hash>
git push --force  # Only if already pushed
```

The original popkit-cloud repo remains untouched as backup.
