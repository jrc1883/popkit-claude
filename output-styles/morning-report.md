---
name: morning-report
description: Daily morning health check and status summary
---

# Morning Report Style

## Format

```
┌─────────────────────────────────────────────────────────────┐
│ 🌅 Morning Report - [Project Name]                          │
│ [Date] [Time]                                               │
├─────────────────────────────────────────────────────────────┤
│ Ready to Code Score: [XX/100]                               │
├─────────────────────────────────────────────────────────────┤
│ Services                                                     │
│ ✓ Dev Server: Running on :3000                              │
│ ✓ Database: Connected on :5432                              │
│ ✗ Redis: Not running                                        │
├─────────────────────────────────────────────────────────────┤
│ Git Status                                                   │
│ Branch: feature/auth                                        │
│ Last commit: abc123 - feat: add login (2 hours ago)         │
│ Uncommitted: 3 files                                        │
│ Behind remote: 2 commits                                    │
├─────────────────────────────────────────────────────────────┤
│ Code Quality                                                 │
│ TypeScript: 0 errors                                        │
│ Lint: 2 warnings                                            │
│ Tests: 47/47 passing                                        │
├─────────────────────────────────────────────────────────────┤
│ Issues                                                       │
│ ⚠ Redis not running - run `docker-compose up -d redis`      │
│ ⚠ 2 lint warnings - run `npm run lint:fix`                  │
├─────────────────────────────────────────────────────────────┤
│ Recommendations                                              │
│ 1. Start Redis before proceeding                            │
│ 2. Pull latest from remote                                  │
│ 3. Fix lint warnings                                        │
└─────────────────────────────────────────────────────────────┘
```

## Ready to Code Score

| Score | Status | Meaning |
|-------|--------|---------|
| 90-100 | 🟢 Ready | All systems go |
| 70-89 | 🟡 Mostly Ready | Minor issues |
| 50-69 | 🟠 Issues | Several problems |
| 0-49 | 🔴 Blocked | Major issues |

## Checks Performed

### Services
- Dev server (Next.js, Vite, etc.)
- Database (PostgreSQL, MongoDB, etc.)
- Cache (Redis, Memcached)
- Other project-specific services

### Git
- Current branch
- Last commit (hash, message, time)
- Uncommitted changes
- Remote sync status

### Code Quality
- TypeScript errors
- Lint errors/warnings
- Test results
- Build status

## Issues and Recommendations

- Issues are problems found
- Recommendations are suggested actions
- Ordered by priority
- Include commands to fix

## Compact Format

For quick status:

```
Morning Report: 85/100 🟢
✓ Services (3/3) | ✓ Git (clean) | ⚠ Lint (2 warnings)
Branch: feature/auth | Last: feat: add login (2h ago)
```
