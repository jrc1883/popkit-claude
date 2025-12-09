# PopKit Cloud Setup Guide

**Part of Issue #68 - Hosted Redis Service**

This guide explains how to configure PopKit to use the cloud-hosted Redis service instead of local Docker Redis.

## Overview

PopKit Cloud provides a hosted Redis backend for Power Mode, eliminating the need for Docker and local Redis setup. Benefits include:

- **Zero Setup**: No Docker or Redis installation required
- **Always Available**: No need to manage local services
- **Cross-Device**: Same session accessible from multiple machines
- **Collective Learning**: Benefit from anonymized patterns (Pro tier)

## Quick Start

### 1. Get Your API Key

Sign up at [popkit.dev](https://popkit.dev) (coming soon) to get your API key.

### 2. Configure Environment

Set your API key in your environment:

```bash
# Linux/macOS
export POPKIT_API_KEY=pk_live_your_key_here

# Windows PowerShell
$env:POPKIT_API_KEY = "pk_live_your_key_here"

# Windows CMD
set POPKIT_API_KEY=pk_live_your_key_here
```

For persistent configuration, add to your shell profile (`.bashrc`, `.zshrc`, etc.).

### 3. Verify Connection

Test the connection:

```bash
cd /path/to/your/project
python power-mode/cloud_client.py
```

Expected output:
```
PopKit Cloud Client Test
========================================
API Key: pk_live_...your_key
Base URL: https://api.popkit.dev/v1

Connecting...
[OK] Connected!
  User ID: usr_abc123
  Tier: free
```

### 4. Use Power Mode

Power Mode now automatically uses cloud when configured:

```
/popkit:power start
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POPKIT_API_KEY` | (none) | Your PopKit Cloud API key |
| `POPKIT_CLOUD_ENABLED` | `true` | Set to `false` to disable cloud |
| `POPKIT_DEV_MODE` | `false` | Set to `true` for local development |
| `POPKIT_CLOUD_URL` | `https://api.popkit.dev/v1` | Custom API endpoint |

### Disabling Cloud

To temporarily disable cloud and use local Redis:

```bash
export POPKIT_CLOUD_ENABLED=false
```

### Development Mode

For testing against a local API server:

```bash
export POPKIT_DEV_MODE=true
# Uses http://localhost:8787/v1 instead
```

## Fallback Behavior

PopKit uses a priority chain for Redis connections:

1. **Cloud**: If `POPKIT_API_KEY` is set and cloud is enabled
2. **Local Redis**: If Docker Redis is running
3. **File-Based**: JSON file fallback for development

This ensures Power Mode works even without cloud configuration.

## Tier Features

| Feature | Free | Pro ($9/mo) | Team ($29/mo) |
|---------|------|-------------|---------------|
| Cloud Redis | Yes | Yes | Yes (HA) |
| Commands/day | 100 | 1,000 | 10,000 |
| Session persistence | 1 hour | 24 hours | 7 days |
| Collective Learning | Limited | Full | Full + private |
| Team coordination | - | - | Yes |
| Priority support | - | - | Yes |

## Troubleshooting

### Connection Failed

```
[ERROR] Connection failed
  Check API key and network connectivity
```

**Solutions:**
1. Verify API key is correct: `echo $POPKIT_API_KEY`
2. Check network connectivity: `curl https://api.popkit.dev/v1/health`
3. Try disabling cloud temporarily: `export POPKIT_CLOUD_ENABLED=false`

### Rate Limit Exceeded

```
RuntimeError: Rate limit exceeded
```

**Solutions:**
1. Wait a few minutes and retry
2. Upgrade to Pro tier for higher limits
3. Use local Redis for heavy development sessions

### Invalid API Key

```
ValueError: Invalid API key
```

**Solutions:**
1. Verify key starts with `pk_live_` or `pk_test_`
2. Regenerate key at [popkit.dev/settings](https://popkit.dev/settings)

## Security

- API keys are transmitted over HTTPS only
- Keys are never logged or stored in plain text
- Use `pk_test_` keys for development
- Use `pk_live_` keys for production

## API Reference

See [API Documentation](./cloud-api.md) for the complete API reference.

---

**Status:** Plugin-side implementation complete. Waiting for cloud infrastructure (Upstash + API Gateway).
