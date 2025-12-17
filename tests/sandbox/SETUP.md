# Sandbox Testing Setup Guide

This guide walks you through setting up the PopKit Sandbox Testing Platform and its optional cloud integrations.

## Quick Start (Local Only)

The local test runner works **without any setup**. Just run:

```bash
cd packages/plugin/tests/sandbox
python local_runner.py --help
```

This is sufficient for most testing needs. The optional integrations below provide additional capabilities.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PopKit Sandbox Testing                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐         ┌──────────────┐                │
│   │ Local Runner │         │  E2B Runner  │  ← Optional    │
│   │  (Default)   │         │   (Cloud)    │                │
│   └──────┬───────┘         └──────┬───────┘                │
│          │                        │                         │
│          ▼                        ▼                         │
│   ┌──────────────────────────────────────┐                 │
│   │         Test Telemetry Layer         │                 │
│   │  (Tool traces, decisions, events)    │                 │
│   └──────────────────┬───────────────────┘                 │
│                      │                                      │
│          ┌───────────┴───────────┐                         │
│          ▼                       ▼                          │
│   ┌─────────────┐        ┌─────────────┐                   │
│   │ Local JSONL │        │   Upstash   │  ← Optional       │
│   │   Storage   │        │   Streams   │                   │
│   └─────────────┘        └─────────────┘                   │
│                                                             │
│                      ▼                                      │
│            ┌─────────────────┐                              │
│            │    Analytics    │                              │
│            │   & Reporting   │                              │
│            └─────────────────┘                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Setup

### 1. Local Runner (No Setup Required)

The local runner creates temporary directories, initializes git, and runs tests in isolation.

**Verify it works:**
```bash
cd packages/plugin/tests/sandbox
python local_runner.py --help
```

**Run a simple test:**
```bash
python -c "
from local_runner import LocalTestRunner, TestConfig
runner = LocalTestRunner()
result = runner.run_skill_test('pop-brainstorming', {'topic': 'test'})
print(f'Success: {result.success}')
"
```

---

### 2. E2B Cloud Runner (Optional)

E2B provides fully isolated cloud sandboxes for testing. Useful for:
- Running tests that might affect local system
- Parallel test execution
- Clean environment guarantees

#### Step 1: Create E2B Account

1. Go to [e2b.dev](https://e2b.dev)
2. Sign up for an account (free tier available)
3. Navigate to Dashboard → API Keys
4. Create a new API key

#### Step 2: Install E2B SDK

```bash
pip install e2b
```

#### Step 3: Configure API Key

**Option A: Environment Variable (Recommended)**
```bash
# Linux/macOS
export E2B_API_KEY="your-api-key-here"

# Windows PowerShell
$env:E2B_API_KEY = "your-api-key-here"

# Windows CMD
set E2B_API_KEY=your-api-key-here
```

**Option B: .env File**
Create `.env` in your project root:
```
E2B_API_KEY=your-api-key-here
```

#### Step 4: Verify Setup

```bash
cd packages/plugin/tests/sandbox
python e2b_runner.py --status
```

Expected output:
```
E2B Test Runner Status
========================================
E2B SDK installed: True
E2B API key: Configured
E2B available: True
Telemetry available: True
Upstash available: False  (or True if configured)
```

#### E2B Pricing Notes

- Free tier: Limited sandbox minutes per month
- Sandboxes timeout after configurable duration (default: 300s)
- Each sandbox costs compute time while running
- Use `--timeout` to limit execution time

---

### 3. Upstash Redis (Optional)

Upstash provides serverless Redis for cloud telemetry storage. Useful for:
- Persisting test results across sessions
- Sharing results between machines
- CI/CD integration
- Real-time streaming during E2B tests

#### Step 1: Create Upstash Account

1. Go to [upstash.com](https://upstash.com)
2. Sign up (free tier: 10K commands/day)
3. Create a new Redis database
4. Choose region closest to you

#### Step 2: Get Credentials

From your Upstash dashboard:
1. Select your database
2. Copy the REST URL and Token

#### Step 3: Configure Credentials

**Option A: Environment Variables (Recommended)**
```bash
# Linux/macOS
export UPSTASH_REDIS_REST_URL="https://your-db.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="your-token-here"

# Windows PowerShell
$env:UPSTASH_REDIS_REST_URL = "https://your-db.upstash.io"
$env:UPSTASH_REDIS_REST_TOKEN = "your-token-here"
```

**Option B: .env File**
```
UPSTASH_REDIS_REST_URL=https://your-db.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token-here
```

#### Step 4: Verify Setup

```bash
cd packages/plugin/hooks/utils
python upstash_telemetry.py --status
```

Expected output:
```
Upstash Telemetry Status
========================================
Upstash configured: True
Connection test: Success
Rate limit: 100 req/10s
```

#### Upstash Pricing Notes

- Free tier: 10,000 commands/day, 256MB storage
- Telemetry uses Redis Streams (XADD, XREAD)
- Rate limiting built-in to stay within free tier
- Data auto-expires after 7 days (configurable)

---

### 4. Voyage AI Embeddings (Optional)

Voyage AI provides embeddings for semantic tool discovery. Useful for:
- Intelligent agent routing
- Semantic search in test results
- Pattern matching across sessions

#### Step 1: Get API Key

1. Go to [voyageai.com](https://www.voyageai.com)
2. Sign up for an account
3. Navigate to API Keys
4. Create a new key

#### Step 2: Configure

```bash
# Linux/macOS
export VOYAGE_API_KEY="your-api-key-here"

# Windows PowerShell
$env:VOYAGE_API_KEY = "your-api-key-here"
```

---

## Environment Variables Summary

| Variable | Required | Purpose |
|----------|----------|---------|
| `POPKIT_TEST_MODE` | Auto-set | Enables telemetry capture during tests |
| `POPKIT_TEST_SESSION_ID` | Auto-set | Unique session identifier |
| `E2B_API_KEY` | For E2B | Cloud sandbox authentication |
| `UPSTASH_REDIS_REST_URL` | For Upstash | Redis REST endpoint |
| `UPSTASH_REDIS_REST_TOKEN` | For Upstash | Redis authentication |
| `VOYAGE_API_KEY` | For embeddings | Semantic search (optional) |

---

## Configuration Files

### .env (Project Root)

Create a `.env` file for local development:

```bash
# Sandbox Testing Configuration
# Copy this to .env and fill in your values

# E2B Cloud Sandboxes (optional)
# Get key from: https://e2b.dev/dashboard
E2B_API_KEY=

# Upstash Redis (optional)
# Get from: https://console.upstash.com
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# Voyage AI Embeddings (optional)
# Get from: https://www.voyageai.com
VOYAGE_API_KEY=
```

### Loading .env

The test runners automatically load `.env` if present. You can also use:

```bash
# Install python-dotenv
pip install python-dotenv

# Or load manually in Python
from dotenv import load_dotenv
load_dotenv()
```

---

## Verification Checklist

Run these commands to verify your setup:

```bash
# 1. Check local runner (always works)
cd packages/plugin/tests/sandbox
python local_runner.py --help
echo "✓ Local runner ready"

# 2. Check test matrix
python matrix_loader.py --stats
echo "✓ Test matrix loaded"

# 3. Check analytics
python analytics.py --help
echo "✓ Analytics ready"

# 4. Check E2B (optional)
python e2b_runner.py --status

# 5. Check Upstash (optional)
cd ../hooks/utils
python upstash_telemetry.py --status
```

---

## Running Tests

### Quick Smoke Test (Local)

```bash
cd packages/plugin/tests/sandbox
python matrix_loader.py --suite smoke --json | python -c "
import json, sys
tests = json.load(sys.stdin)
print(f'Smoke suite: {len(tests)} tests')
for t in tests[:3]:
    print(f'  - {t[\"id\"]}: {t[\"name\"]}')
"
```

### Full Test Run

```bash
# Via command (when in Claude Code)
/popkit:plugin test sandbox

# Or directly
python -c "
from local_runner import LocalTestRunner, TestConfig
from matrix_loader import TestMatrix

matrix = TestMatrix()
runner = LocalTestRunner()

for test in matrix.get_suite('smoke')[:3]:
    print(f'Testing {test.id}...')
    # Tests would be executed here
"
```

### With Telemetry

```bash
# Enable test mode
export POPKIT_TEST_MODE=1
export POPKIT_TEST_SESSION_ID=manual-test-$(date +%s)

# Run test
python local_runner.py  # with your test

# View results
python analytics.py --session $POPKIT_TEST_SESSION_ID
```

---

## Troubleshooting

### "E2B SDK not installed"

```bash
pip install e2b
```

### "E2B API key not configured"

1. Check environment variable is set:
   ```bash
   echo $E2B_API_KEY  # Linux/macOS
   echo %E2B_API_KEY%  # Windows CMD
   $env:E2B_API_KEY  # Windows PowerShell
   ```

2. If using .env, ensure it's in the right directory

### "Upstash connection failed"

1. Verify URL format: `https://xxx.upstash.io`
2. Check token is correct (no extra whitespace)
3. Ensure database is active in Upstash console

### "No sessions found" in analytics

This is normal if you haven't run any tests yet. Run a test first:

```bash
export POPKIT_TEST_MODE=1
export POPKIT_TEST_SESSION_ID=test-$(date +%s)
# Run your test
python analytics.py --recent 5
```

### Rate limiting errors

The Upstash client has built-in rate limiting. If you see rate limit errors:
1. Wait a few seconds and retry
2. Reduce test parallelism
3. Upgrade Upstash plan if needed

---

## Next Steps

1. **Run smoke tests**: `/popkit:plugin test sandbox`
2. **Explore test matrix**: `python matrix_loader.py --stats`
3. **View analytics**: `python analytics.py --recent 10`
4. **Compare runs**: `python analytics.py --compare session1 session2`

For more details, see:
- `pop-sandbox-test` skill documentation
- `/popkit:plugin test` command documentation
- Issue #225-231 for implementation details
