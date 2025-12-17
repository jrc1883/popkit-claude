# Rollback Procedures Standards

Standards for safe, fast rollback of failed deployments.

## Core Principles

### RB-001: Rollback Decision

Know when to rollback.

**Automatic Rollback Triggers:**
| Condition | Threshold | Action |
|-----------|-----------|--------|
| Health check failing | >2 minutes | Auto-rollback |
| Error rate elevated | >10% for 5 min | Auto-rollback |
| Response time degraded | >5s for 2 min | Alert + manual decision |

**Manual Rollback Triggers:**
- Critical functionality broken
- Security vulnerability discovered
- Data corruption detected
- Customer-impacting bugs

### RB-002: Rollback Speed

Rollback must be fast.

**Targets:**
| Metric | Target |
|--------|--------|
| Decision to rollback | <5 minutes |
| Rollback execution | <10 minutes |
| Verification complete | <5 minutes |
| Total recovery time | <20 minutes |

### RB-003: Rollback Safety

Rollback should not cause additional harm.

**Requirements:**
- Rollback tested before deployment
- Previous artifacts retained
- Database state compatible
- No data loss

## Rollback Procedures by Platform

### NPM Package Rollback

```bash
# Option 1: Deprecate bad version
npm deprecate package-name@bad-version "Critical bug, use previous version"

# Option 2: Publish new patch
# (Cannot truly remove from npm, must publish fixed version)
npm version patch
npm publish
```

### PyPI Package Rollback

```bash
# Option 1: Yank the release (removes from install, keeps in history)
pip index remove-version package-name bad-version

# Option 2: Publish new patch
python -m build
twine upload dist/*
```

### Docker Rollback

```bash
# Rollback to previous version
docker pull registry/app:previous-version
docker stop app-container
docker run -d --name app-container registry/app:previous-version

# Or using tags
docker tag registry/app:previous-version registry/app:latest
docker push registry/app:latest
```

### Kubernetes Rollback

```bash
# View deployment history
kubectl rollout history deployment/app

# Rollback to previous revision
kubectl rollout undo deployment/app

# Rollback to specific revision
kubectl rollout undo deployment/app --to-revision=2

# Verify rollback
kubectl rollout status deployment/app
```

### Vercel Rollback

```bash
# List deployments
vercel ls

# Promote previous deployment to production
vercel promote <deployment-url>

# Or via dashboard
# Go to Deployments → Select previous → Promote to Production
```

### Netlify Rollback

```bash
# Via CLI
netlify rollback

# Via dashboard
# Go to Deploys → Select previous → Publish deploy
```

### GitHub Releases Rollback

```bash
# Cannot delete releases, but can:
# 1. Mark as pre-release
gh release edit v1.0.0 --prerelease

# 2. Create new release pointing to previous tag
gh release create v1.0.1 --notes "Rollback to v0.9.9 functionality"
```

## Database Rollback Considerations

### Schema Migrations

**Forward-Compatible Migrations:**
```
1. Add new column (nullable)
2. Deploy code that writes to both
3. Backfill data
4. Deploy code that reads from new
5. Remove old column (later)
```

**Rollback-Safe Migrations:**
- Always write backward-compatible migrations
- Keep old column during transition
- Use feature flags for new behavior
- Never delete data in migration

### Data Rollback

**If data corruption occurred:**
```
1. Stop all writes to affected tables
2. Identify scope of corruption
3. Restore from backup if needed
4. Verify data integrity
5. Resume operations
```

## Post-Rollback Actions

### Immediate (within 1 hour)

1. **Verify rollback success**
   - Health checks passing
   - Error rate normalized
   - Critical paths functional

2. **Notify stakeholders**
   - Team notification
   - Status page update
   - Customer communication (if needed)

3. **Preserve evidence**
   - Capture logs
   - Document timeline
   - Save error reports

### Short-term (within 24 hours)

1. **Root cause analysis**
   - What went wrong?
   - Why wasn't it caught?
   - How to prevent recurrence?

2. **Fix preparation**
   - Write failing test for bug
   - Implement fix
   - Review fix thoroughly

3. **Process improvement**
   - Update checklists
   - Add automated checks
   - Improve monitoring

## Rollback Checklist

```
[ ] Confirm rollback is necessary
[ ] Notify team of rollback decision
[ ] Execute rollback procedure
[ ] Verify health checks pass
[ ] Verify correct version deployed
[ ] Test critical functionality
[ ] Check error rates
[ ] Update status page
[ ] Document incident
[ ] Schedule post-mortem
```

## Quality Metrics

| Metric | Target |
|--------|--------|
| Rollback success rate | 100% |
| Time to decision | <5 minutes |
| Rollback duration | <10 minutes |
| Data loss incidents | 0 |
