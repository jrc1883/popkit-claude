# Deployment Process Standards

Standards for consistent, safe deployments across all platforms.

## Core Principles

### DP-001: Pre-Deployment Verification

All deployments must pass pre-deployment checks.

**Required Checks:**
1. All tests pass
2. No lint errors
3. Build succeeds
4. No uncommitted changes
5. Version bumped
6. Changelog updated
7. No security vulnerabilities

**Automated:**
```bash
python scripts/pre_deploy_check.py
```

### DP-002: Version Management

Follow semantic versioning strictly.

**Version Format:**
```
MAJOR.MINOR.PATCH[-PRERELEASE]

Examples:
1.0.0        # Initial release
1.0.1        # Patch fix
1.1.0        # New feature
2.0.0        # Breaking change
1.1.0-alpha  # Pre-release
```

**When to Bump:**
| Change Type | Version Bump |
|-------------|--------------|
| Breaking change | MAJOR |
| New feature (backward compatible) | MINOR |
| Bug fix | PATCH |
| Pre-release | -alpha, -beta, -rc |

### DP-003: Changelog Maintenance

Maintain changelog for every release.

**Format:**
```markdown
## [1.0.0] - 2025-01-15

### Added
- New feature description

### Changed
- Modified behavior

### Fixed
- Bug fix description

### Removed
- Deprecated feature
```

### DP-004: Deployment Environments

Use consistent environment progression.

**Standard Environments:**
| Environment | Purpose | When |
|-------------|---------|------|
| Development | Local testing | Continuous |
| Staging | Pre-production testing | Before release |
| Production | Live deployment | After approval |

### DP-005: Rollback Readiness

Every deployment must be rollback-ready.

**Requirements:**
- Previous version artifacts retained
- Rollback procedure documented
- Rollback tested before deploying
- Database migrations reversible

### DP-006: Post-Deployment Verification

Verify deployment success immediately.

**Verification Steps:**
1. Health check passes
2. Correct version deployed
3. Critical paths functional
4. No error spike
5. Monitoring active

## Deployment Workflow

### Standard Flow

```
1. Prepare
   ├── Run pre-deploy checks
   ├── Bump version
   ├── Update changelog
   └── Create release tag

2. Deploy
   ├── Build artifacts
   ├── Push to registry/platform
   └── Update deployment target

3. Verify
   ├── Run post-deploy checks
   ├── Monitor for errors
   └── Notify stakeholders

4. Finalize
   ├── Create GitHub release
   ├── Update documentation
   └── Archive artifacts
```

### Emergency Flow

For hotfixes and urgent patches:

```
1. Create hotfix branch from production
2. Apply minimal fix
3. Run abbreviated tests
4. Deploy to production
5. Backport to main branch
```

## Platform-Specific Guidelines

### NPM

```bash
# Pre-deployment
npm run test
npm run build
npm version patch|minor|major

# Deployment
npm publish

# Post-deployment
npm view package-name version
```

### PyPI

```bash
# Pre-deployment
pytest
python -m build

# Deployment
twine upload dist/*

# Post-deployment
pip index versions package-name
```

### Docker

```bash
# Pre-deployment
docker build --tag app:version .
docker run --rm app:version test

# Deployment
docker push registry/app:version
docker push registry/app:latest

# Post-deployment
docker pull registry/app:version
```

### Vercel/Netlify

```bash
# Pre-deployment
npm run build
npm run test

# Deployment
vercel --prod
# or
netlify deploy --prod

# Post-deployment
curl https://app.vercel.app/health
```

## Security Requirements

### SDP-001: Credential Management

Never store credentials in code.

**Allowed:**
- Environment variables
- Secrets managers (AWS, GCP, Azure)
- CI/CD secret storage

**Forbidden:**
- Hardcoded in source
- Committed to repository
- Logged to console

### SDP-002: Access Control

Limit deployment permissions.

**Principles:**
- Least privilege access
- Separate production credentials
- Audit deployment actions
- Require approval for production

### SDP-003: Audit Trail

Maintain deployment history.

**Record:**
- Who deployed
- What version
- When deployed
- Where deployed
- Deployment outcome

## Quality Metrics

| Metric | Target |
|--------|--------|
| Deployment success rate | >99% |
| Rollback time | <15 minutes |
| Pre-deploy check coverage | 100% |
| Post-deploy verification | 100% |
