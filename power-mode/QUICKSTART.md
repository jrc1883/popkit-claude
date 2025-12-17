# Power Mode Quick Start

Get Power Mode running in **30 seconds** - no Docker, no Redis required.

## The TL;DR

```python
from coordinator_auto import create_coordinator
from protocol import create_objective

# Define what you want to do
objective = create_objective(
    description="Build user authentication",
    success_criteria=["Login works", "Tests pass"],
    phases=["explore", "implement", "test"]
)

# Create coordinator (auto-detects Redis or uses file-based)
coordinator = create_coordinator(objective)
coordinator.start()
```

**That's it.** Power Mode will:
- Auto-detect if Redis is available
- Fall back to file-based mode if not
- Work the same either way

## File-Based Mode (Zero Setup)

No installation needed. Just works.

**How it works:**
- Uses `.claude/popkit/power-mode-state.json` for storage
- Polls file for new messages (100ms interval)
- File locking prevents race conditions
- Cross-platform (Windows, macOS, Linux)

**When to use:**
- Development and testing
- 2-3 agents
- Single machine
- Learning Power Mode
- No Docker/Redis available

**Example output:**
```
[OK] Using file-based fallback for Power Mode (redis not running)
   State file: .claude/popkit/power-mode-state.json
   Limitations: polling (not true pub/sub), single-machine only
```

## Redis Mode (Production)

Better performance, more scalable.

**Installation:**
```bash
# Install Python module
pip install redis

# Start Redis (Docker)
docker run -d -p 6379:6379 redis
```

**When to use:**
- 4+ agents
- Production workflows
- Network distribution
- Long-running sessions

**Example output:**
```
[OK] Using Redis for Power Mode
[OK] Coordinator started. Session: abc123
```

## Check Which Mode You'll Use

```bash
python power-mode/coordinator_auto.py info
```

Output:
```
Mode: file
Redis available: False
Redis running: False
File path: /path/to/.claude/popkit/power-mode-state.json

Install redis: pip install redis
```

## Run Examples

```bash
# Run all examples
python power-mode/example_usage.py

# Run specific example
python power-mode/example_usage.py 3  # Pub/sub demo
```

## Switching Modes

**No code changes needed!** The coordinator auto-detects:

```python
# This works with both Redis and file-based
coordinator = create_coordinator(objective)
coordinator.start()
```

If you start Redis later, it will automatically use it next time.

## Force File Mode

Even if Redis is available, force file-based:

```python
coordinator = create_coordinator(objective, force_file_mode=True)
```

Useful for:
- Testing the fallback
- Debugging (inspect JSON file)
- Environments where Redis is not allowed

## State File Format

```json
{
  "messages": {
    "pop:broadcast": [{"data": "...", "timestamp": "..."}]
  },
  "keys": {
    "pop:objective": "..."
  },
  "hashes": {
    "pop:state:agent-1": {"progress": "0.5"}
  },
  "lists": {
    "pop:tasks:pending": ["task-1", "task-2"]
  },
  "subscriptions": {
    "client-123": ["pop:broadcast"]
  },
  "read_positions": {
    "client-123": {"pop:broadcast": 5}
  }
}
```

You can **open this file while Power Mode is running** to see what's happening!

## Cleanup

File-based mode auto-trims messages, but you can manually cleanup:

```bash
python power-mode/coordinator_auto.py cleanup
```

Removes messages older than 24 hours.

## Performance Comparison

| Operation | Redis | File-Based |
|-----------|-------|------------|
| Publish message | <1ms | ~10ms |
| Receive message | <1ms | ~100ms |
| Throughput | 10,000/sec | ~100/sec |

File-based is **100x slower** but still fast enough for 2-3 agents.

## Common Issues

### "Could not acquire lock"

**Problem:** Too many agents or orphaned lock file

**Solution:**
```bash
rm .claude/popkit/power-mode-state.lock
```

### Messages not appearing

**Problem:** Polling lag or read position issue

**Solution:**
```python
# Check state file manually
cat .claude/popkit/power-mode-state.json

# Look for your client_id in subscriptions
```

### File growing too large

**Problem:** Too many messages

**Solution:**
```bash
python power-mode/coordinator_auto.py cleanup
```

## Migration Path

1. **Start**: Use file-based mode for prototyping
2. **Test**: Validate workflow with 2-3 agents
3. **Scale**: Switch to Redis for production (no code changes!)

## What's Next?

- Read [FALLBACK.md](./FALLBACK.md) for detailed comparison
- Run [example_usage.py](./example_usage.py) for hands-on examples
- See [coordinator_auto.py](./coordinator_auto.py) for implementation details

## Bottom Line

**File-based mode gets you started immediately.**

**Redis mode scales when you need it.**

**Both use the same code.**
