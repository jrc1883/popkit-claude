# PopKit Power Mode - Redis Setup Guide

Get Redis running for multi-agent orchestration in 5 minutes.

## TL;DR

```bash
# 1. Install Docker (if needed)
# macOS/Windows: Download Docker Desktop
# Linux: sudo apt-get install docker.io docker-compose

# 2. Install Python Redis client
pip install redis

# 3. Start Redis
cd power-mode/
python setup-redis.py start

# 4. Verify
python setup-redis.py test
```

Or use PopKit commands:

```
/popkit:power-init start
/popkit:power-mode
```

## Step-by-Step Setup

### Step 1: Install Docker

Power Mode uses Docker to run Redis locally.

**macOS:**
1. Download [Docker Desktop for Mac](https://docs.docker.com/desktop/mac/install/)
2. Install and open Docker Desktop
3. Wait for "Docker Desktop is running" in menu bar

**Windows:**
1. Download [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
2. Install and open Docker Desktop
3. If prompted, enable WSL 2
4. Wait for "Docker Desktop is running" in system tray

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker

# Fedora
sudo dnf install docker docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

**Verify Docker:**
```bash
docker --version
docker ps
```

### Step 2: Install Python Dependencies

Power Mode requires the `redis` Python package:

```bash
# From power-mode directory
cd power-mode/
pip install -r requirements.txt

# Or install directly
pip install redis
```

**Verify:**
```bash
python -c "import redis; print(redis.__version__)"
```

### Step 3: Start Redis

**Option A: Using PopKit command (recommended)**
```
/popkit:power-init start
```

**Option B: Using setup script**
```bash
cd power-mode/
python setup-redis.py start
```

**Option C: Using Docker Compose directly**
```bash
cd power-mode/
docker compose up -d
```

**Expected output:**
```
ℹ Checking Docker availability...
✓ Docker is installed and running
ℹ Starting Redis container...
✓ Redis container started
ℹ Waiting for Redis to be healthy...
✓ Redis is running and accessible

Ready for Power Mode!
```

### Step 4: Verify Setup

**Check status:**
```bash
python setup-redis.py status
```

**Test connectivity:**
```bash
python setup-redis.py test
```

**Expected:**
```
✓ Docker is installed and running
✓ Redis container is running
✓ Redis is accessible on localhost:6379

Ready for Power Mode!

ℹ Testing Redis pub/sub...
ℹ Testing Power Mode channels...
✓ All tests passed!
```

### Step 5: Use Power Mode

**From Claude Code:**
```
/popkit:power-mode "Implement user authentication with JWT tokens"
```

**Check morning status:**
```
/popkit:morning
```

Should show:
```
Services (Power Mode):
  Docker: ✓ Running
  Redis: ✓ Running (localhost:6379)
  Power Mode: ✓ Ready
```

## Common Issues

### Docker not running

**Symptom:**
```
✗ Docker is not available
```

**Fix:**
- macOS/Windows: Open Docker Desktop
- Linux: `sudo systemctl start docker`

### Port 6379 already in use

**Symptom:**
```
Error: bind: address already in use
```

**Fix:**
```bash
# Find what's using the port
# macOS/Linux:
lsof -i :6379

# Windows:
netstat -ano | findstr :6379

# Stop the conflicting service or change PopKit's port
```

### redis module not found

**Symptom:**
```
ModuleNotFoundError: No module named 'redis'
```

**Fix:**
```bash
pip install redis
```

### Permission denied (Linux)

**Symptom:**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**Fix:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Daily Usage

### Morning routine

```bash
# Check if Redis is running
/popkit:morning

# If not, start it
/popkit:power-init start
```

### During development

Power Mode automatically uses Redis when activated:

```
/popkit:power-mode "Refactor auth service for better testability"
```

Agents will:
1. Connect to Redis on startup
2. Publish heartbeats every 5 tool calls
3. Share insights via pub/sub
4. Coordinate through sync barriers

### Debugging

**View Redis activity:**
```bash
python setup-redis.py debug
```

Opens Redis Commander at http://localhost:8081

**View live messages:**
```bash
docker exec -it popkit-redis redis-cli
> PSUBSCRIBE pop:*
```

**Check agent states:**
```bash
docker exec -it popkit-redis redis-cli
> KEYS pop:state:*
> HGETALL pop:state:abc123
```

### Stopping Redis

**When not using Power Mode:**
```bash
/popkit:power-init stop
```

Redis data persists in a Docker volume and will be restored on next start.

**Complete cleanup (loses data):**
```bash
docker compose -f power-mode/docker-compose.yml down -v
```

## Next Steps

After setup:

1. **Try Power Mode**: `/popkit:power-mode "Your task here"`
2. **Explore Redis Commander**: `python setup-redis.py debug`
3. **Check morning status**: `/popkit:morning`
4. **Read the docs**: See `power-mode/README.md`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Agent 1   │  │   Agent 2   │  │   Agent 3   │        │
│  │ (explorer)  │  │ (architect) │  │ (reviewer)  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │ Pub/Sub
                            ▼
                   ┌─────────────────┐
                   │      Redis      │
                   │  (localhost:6379)│
                   │                 │
                   │  Channels:      │
                   │  - broadcast    │
                   │  - heartbeat    │
                   │  - insights     │
                   │  - coordinator  │
                   └─────────────────┘
```

## What Gets Installed

**Docker containers:**
- `popkit-redis`: Redis 7 Alpine (always running)
- `popkit-redis-commander`: Web UI (only with debug flag)

**Docker volumes:**
- `popkit_redis_data`: Persistent storage for Redis data

**Docker networks:**
- `popkit`: Bridge network for containers

**Ports:**
- `6379`: Redis server
- `8081`: Redis Commander (debug mode only)

**Disk usage:**
- Redis image: ~30 MB
- Redis Commander image: ~40 MB (if used)
- Data volume: ~10-50 MB (depends on usage)

**Total: ~100 MB**

## Uninstalling

**Remove containers and keep data:**
```bash
docker compose -f power-mode/docker-compose.yml down
```

**Remove everything including data:**
```bash
docker compose -f power-mode/docker-compose.yml down -v
docker volume rm popkit_redis_data
```

**Remove Docker images:**
```bash
docker rmi redis:7-alpine
docker rmi rediscommander/redis-commander
```

## Configuration

Default configuration works for most cases. If needed, edit `power-mode/config.json`:

```json
{
  "redis": {
    "host": "localhost",  // Change if Redis is remote
    "port": 6379,         // Change if using different port
    "db": 0,              // Redis database number
    "password": null      // Add password if needed
  }
}
```

After changing config, restart Redis:
```bash
/popkit:power-init restart
```

## Security Note

This setup is for **local development only**:
- No authentication
- No encryption
- Binds to localhost
- Not suitable for production

For production deployment, use managed Redis services like:
- AWS ElastiCache
- Redis Cloud
- Azure Cache for Redis
- Google Cloud Memorystore
