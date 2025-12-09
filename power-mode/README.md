# PopKit Power Mode - Redis Setup

Multi-agent orchestration requires Redis for pub/sub messaging between agents. This directory contains everything needed to set up and run Redis locally.

## Quick Start

```bash
# Check status
python setup-redis.py status

# Start Redis
python setup-redis.py start

# Verify it's working
python setup-redis.py test
```

Or use the PopKit command:

```
/popkit:power-init start
```

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Redis container configuration |
| `setup-redis.py` | Cross-platform setup script |
| `config.json` | Power Mode configuration |
| `coordinator.py` | Mesh brain for agent orchestration |
| `protocol.py` | Message types and serialization |
| `checkin-hook.py` | PostToolUse hook for periodic check-ins |
| `README.md` | This file |

## Prerequisites

1. **Docker** - Install from https://docs.docker.com/get-docker/
   - macOS: Docker Desktop
   - Windows: Docker Desktop
   - Linux: Docker Engine

2. **Python 3.8+** - Already required for PopKit hooks

3. **redis-py** - Python Redis client
   ```bash
   pip install redis
   ```

## Setup Script Commands

### Status Check
```bash
python setup-redis.py status
```

Shows:
- Docker availability
- Redis container status
- Redis accessibility
- Overall readiness for Power Mode

### Start Redis
```bash
python setup-redis.py start
```

1. Checks Docker is running
2. Starts Redis container (pulls image if needed)
3. Waits for health check
4. Verifies connectivity

### Stop Redis
```bash
python setup-redis.py stop
```

Gracefully stops and removes the container (data persists in volume).

### Restart Redis
```bash
python setup-redis.py restart
```

Stops and starts Redis (useful for config changes).

### Debug Mode
```bash
python setup-redis.py debug
```

Starts Redis Commander at http://localhost:8081 for visual inspection of:
- Active channels and subscriptions
- Agent states
- Message queues
- Insight pool
- Learned patterns

### Test Connectivity
```bash
python setup-redis.py test
```

Verifies:
- Basic connectivity
- Pub/sub functionality
- All Power Mode channels work

## Docker Compose Configuration

### Services

**redis** (always running):
- Image: `redis:7-alpine`
- Port: 6379
- Volume: `redis_data` (persistent)
- Memory: 256MB max
- Eviction: LRU (least recently used)

**redis-commander** (debug only):
- Image: `rediscommander/redis-commander`
- Port: 8081
- Only starts with `--profile debug`

### Starting Without Script

```bash
# Start Redis only
docker compose up -d

# Start with Redis Commander
docker compose --profile debug up -d

# Stop all
docker compose down

# View logs
docker compose logs -f redis
```

## Redis Channels

Power Mode uses 6 pub/sub channels:

| Channel | Publisher | Subscribers | Purpose |
|---------|-----------|-------------|---------|
| `pop:broadcast` | Coordinator | All agents | Broadcast messages |
| `pop:heartbeat` | Agents | Coordinator | Health checks |
| `pop:results` | Agents | Coordinator | Task completions |
| `pop:insights` | Agents | Coordinator + Agents | Shared discoveries |
| `pop:coordinator` | External | Coordinator | Control commands |
| `pop:human` | Agents | Coordinator | Human approval requests |

## Configuration

From `config.json`:

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": null,
    "socket_timeout": 5,
    "retry_on_timeout": true,
    "health_check_interval": 30
  },
  "channels": {
    "prefix": "pop",
    "broadcast": "pop:broadcast",
    "heartbeat": "pop:heartbeat",
    "results": "pop:results",
    "insights": "pop:insights",
    "coordinator": "pop:coordinator",
    "human": "pop:human"
  }
}
```

## Integration Points

### 1. Power Mode Command (`/popkit:power-mode`)
Auto-checks Redis status and offers to start if not running.

### 2. Morning Health Check (`/popkit:morning`)
Includes Redis status in daily report:
```
Services:
  Redis: ✓ Running (localhost:6379)
  Power Mode: ✓ Ready
```

### 3. Coordinator (`coordinator.py`)
Connects to Redis on startup:
```python
coordinator = PowerModeCoordinator(objective)
if coordinator.connect():
    coordinator.start()
```

### 4. Check-In Hook (`checkin-hook.py`)
Agents publish to channels every N tool calls.

### 5. Agent Output
Agents subscribe to their channel (`pop:agent:{agent_id}`) for messages.

## Data Stored in Redis

### Keys

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `pop:objective` | String | Session | Current objective definition |
| `pop:state:{agent_id}` | Hash | Session | Agent state snapshots |
| `pop:completed:{session_id}` | String | 24h | Completed session results |
| `pop:tasks:orphaned` | List | Session | Tasks from failed agents |
| `pop:coordinator:status` | String | Live | Coordinator health |
| `pop:patterns:{pattern_id}` | Hash | 24h | Learned patterns |

### Values

All values are JSON-encoded for consistency.

## Monitoring

### Check Active Agents
```bash
docker exec -it popkit-redis redis-cli
> KEYS pop:state:*
> HGETALL pop:state:abc123
```

### Monitor Pub/Sub
```bash
docker exec -it popkit-redis redis-cli
> PSUBSCRIBE pop:*
```

### View Insights
```bash
docker exec -it popkit-redis redis-cli
> LRANGE pop:insights 0 -1
```

## Troubleshooting

### Container Won't Start

**Check Docker:**
```bash
docker ps
docker info
```

**Check logs:**
```bash
docker logs popkit-redis
```

**Remove and retry:**
```bash
docker rm -f popkit-redis
docker volume rm popkit_redis_data
python setup-redis.py start
```

### Connection Refused

**Check port binding:**
```bash
docker port popkit-redis
# Should show: 6379/tcp -> 0.0.0.0:6379
```

**Check firewall:**
- macOS: System Preferences > Security > Firewall
- Windows: Windows Defender Firewall
- Linux: `sudo ufw status`

**Test from host:**
```bash
# Via Docker (recommended - no local redis-cli needed)
docker exec popkit-redis redis-cli ping
# Should return: PONG

# Or via Python
python -c "import redis; print(redis.Redis(port=16379).ping())"
# Should return: True
```

### Port Already in Use

**Find process using port 6379:**
```bash
# macOS/Linux
lsof -i :6379

# Windows
netstat -ano | findstr :6379
```

**Options:**
1. Stop the conflicting service
2. Change PopKit's port in `config.json`

### Memory Issues

**Check memory usage:**
```bash
docker stats popkit-redis
```

**Increase limit in `docker-compose.yml`:**
```yaml
command: redis-server --maxmemory 512mb
```

**Clear old data:**
```bash
docker exec -it popkit-redis redis-cli
> FLUSHDB
```

### Permission Errors (Linux)

**Add user to docker group:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Python Module Not Found

**Install redis-py:**
```bash
pip install redis
```

**Or install all requirements:**
```bash
cd power-mode/
pip install -r requirements.txt
```

## Performance Notes

### For Development

Current settings are optimized for local development:
- 256MB memory (sufficient for ~5-10 agents)
- LRU eviction (keeps recent data)
- Persistence enabled (survives restarts)
- No password (localhost only)

### For Production

Would need:
- Managed Redis service (AWS ElastiCache, Redis Cloud)
- Authentication and TLS
- Higher memory (1GB+)
- Replication for HA
- Network security groups

## Cleanup

### Stop and Remove Everything
```bash
docker compose down -v
```

This removes:
- Redis container
- Redis Commander container
- Network
- **Volume** (all data lost)

### Keep Data, Remove Containers
```bash
docker compose down
```

Data persists in volume and will be restored on next start.

### Remove Only Containers
```bash
docker rm -f popkit-redis popkit-redis-commander
```

Network and volume remain.

## Advanced Usage

### Custom Configuration

Edit `docker-compose.yml`:

```yaml
services:
  redis:
    command: |
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --loglevel warning
```

### Persistent Sessions

By default, sessions are ephemeral (cleared on restart). To persist:

```python
# In coordinator.py
CONFIG["intervals"]["insight_ttl_seconds"] = 86400  # 24 hours
```

### Multiple Instances

To run multiple PopKit instances:

```yaml
# In docker-compose.yml
ports:
  - "6380:6379"  # Different host port

# In config.json
"redis": {
  "port": 6380
}
```

## Resources

- Redis Documentation: https://redis.io/docs/
- Redis Pub/Sub Guide: https://redis.io/docs/manual/pubsub/
- Docker Compose Reference: https://docs.docker.com/compose/
- redis-py Documentation: https://redis-py.readthedocs.io/

## Support

For issues with:
- **PopKit setup**: Check `/popkit:power-init` command
- **Docker issues**: Check Docker Desktop logs
- **Redis issues**: Check `docker logs popkit-redis`
- **Power Mode**: Check coordinator logs via `/popkit:power-mode status`
