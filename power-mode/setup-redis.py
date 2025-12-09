#!/usr/bin/env python3
"""
PopKit Power Mode - Redis Setup Script
Cross-platform script to initialize Redis for multi-agent orchestration.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def print_status(message, status="info"):
    """Print colored status message (Windows-compatible ASCII)."""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "reset": "\033[0m"
    }

    # ASCII-only icons for Windows compatibility
    icons = {
        "info": "[i]",
        "success": "[+]",
        "warning": "[!]",
        "error": "[x]"
    }

    color = colors.get(status, colors["info"])
    icon = icons.get(status, "[*]")
    print(f"{color}{icon} {message}{colors['reset']}")


def check_docker():
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_docker_compose():
    """Check if Docker Compose is available."""
    # Try docker compose (V2)
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "docker compose"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Try docker-compose (V1)
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "docker-compose"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def check_redis_running():
    """Check if Redis container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=popkit-redis", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "popkit-redis" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_redis_accessible():
    """Check if Redis is accessible on localhost:16379."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=16379, db=0, socket_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


def start_redis(compose_cmd, compose_file):
    """Start Redis container."""
    print_status("Starting Redis container...", "info")

    try:
        # Build command based on compose version
        if compose_cmd == "docker compose":
            cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
        else:
            cmd = ["docker-compose", "-f", str(compose_file), "up", "-d"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print_status(f"Failed to start Redis: {result.stderr}", "error")
            return False

        # Wait for health check
        print_status("Waiting for Redis to be healthy...", "info")
        for i in range(15):
            if check_redis_accessible():
                print_status("Redis is running and accessible", "success")
                return True
            time.sleep(1)

        print_status("Redis started but not responding", "warning")
        return False

    except subprocess.TimeoutExpired:
        print_status("Timeout while starting Redis", "error")
        return False
    except Exception as e:
        print_status(f"Error starting Redis: {e}", "error")
        return False


def stop_redis(compose_cmd, compose_file):
    """Stop Redis container."""
    print_status("Stopping Redis container...", "info")

    try:
        if compose_cmd == "docker compose":
            cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        else:
            cmd = ["docker-compose", "-f", str(compose_file), "down"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print_status("Redis stopped", "success")
            return True
        else:
            print_status(f"Failed to stop Redis: {result.stderr}", "error")
            return False

    except Exception as e:
        print_status(f"Error stopping Redis: {e}", "error")
        return False


def start_redis_commander(compose_cmd, compose_file):
    """Start Redis Commander for debugging."""
    print_status("Starting Redis Commander...", "info")

    try:
        if compose_cmd == "docker compose":
            cmd = ["docker", "compose", "-f", str(compose_file), "--profile", "debug", "up", "-d"]
        else:
            cmd = ["docker-compose", "-f", str(compose_file), "--profile", "debug", "up", "-d"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print_status("Redis Commander started at http://localhost:8081", "success")
            return True
        else:
            print_status(f"Failed to start Redis Commander: {result.stderr}", "error")
            return False

    except Exception as e:
        print_status(f"Error starting Redis Commander: {e}", "error")
        return False


def get_status():
    """Get current Redis status."""
    docker_available = check_docker()
    redis_running = check_redis_running()
    redis_accessible = check_redis_accessible()

    status = {
        "docker_available": docker_available,
        "redis_running": redis_running,
        "redis_accessible": redis_accessible,
        "ready_for_power_mode": docker_available and redis_running and redis_accessible
    }

    return status


def print_status_report(status):
    """Print formatted status report."""
    print("\n" + "=" * 60)
    print("PopKit Power Mode - Redis Status")
    print("=" * 60)

    if status["docker_available"]:
        print_status("Docker is installed and running", "success")
    else:
        print_status("Docker is not available", "error")
        print_status("Install Docker: https://docs.docker.com/get-docker/", "info")

    if status["redis_running"]:
        print_status("Redis container is running", "success")
    else:
        print_status("Redis container is not running", "warning")

    if status["redis_accessible"]:
        print_status("Redis is accessible on localhost:16379", "success")
    else:
        print_status("Redis is not accessible", "warning")

    print("\n" + "-" * 60)

    if status["ready_for_power_mode"]:
        print_status("Ready for Power Mode!", "success")
    else:
        print_status("Power Mode not ready", "warning")
        print_status("Run: python setup-redis.py start", "info")

    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    compose_file = script_dir / "docker-compose.yml"

    if not compose_file.exists():
        print_status(f"docker-compose.yml not found at {compose_file}", "error")
        sys.exit(1)

    # Parse command
    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "status":
        status = get_status()
        print_status_report(status)
        sys.exit(0 if status["ready_for_power_mode"] else 1)

    # Check Docker availability
    if not check_docker():
        print_status("Docker is not available", "error")
        print_status("Install Docker: https://docs.docker.com/get-docker/", "info")
        sys.exit(1)

    compose_cmd = check_docker_compose()
    if not compose_cmd:
        print_status("Docker Compose is not available", "error")
        print_status("Install Docker Compose or update Docker Desktop", "info")
        sys.exit(1)

    # Execute command
    if command == "start":
        if check_redis_running():
            print_status("Redis is already running", "info")
            if check_redis_accessible():
                print_status("Redis is accessible at localhost:16379", "success")
                sys.exit(0)
            else:
                print_status("Redis is running but not accessible", "warning")
                print_status("Restarting...", "info")
                stop_redis(compose_cmd, compose_file)
                time.sleep(2)

        success = start_redis(compose_cmd, compose_file)
        sys.exit(0 if success else 1)

    elif command == "stop":
        success = stop_redis(compose_cmd, compose_file)
        sys.exit(0 if success else 1)

    elif command == "restart":
        stop_redis(compose_cmd, compose_file)
        time.sleep(2)
        success = start_redis(compose_cmd, compose_file)
        sys.exit(0 if success else 1)

    elif command == "debug":
        if not check_redis_running():
            print_status("Starting Redis first...", "info")
            if not start_redis(compose_cmd, compose_file):
                sys.exit(1)
            time.sleep(2)

        success = start_redis_commander(compose_cmd, compose_file)
        sys.exit(0 if success else 1)

    elif command == "test":
        if not check_redis_accessible():
            print_status("Redis is not accessible", "error")
            sys.exit(1)

        try:
            import redis
            r = redis.Redis(host='localhost', port=16379, db=0, decode_responses=True)

            # Test pub/sub
            print_status("Testing Redis pub/sub...", "info")
            r.publish("pop:test", json.dumps({"message": "test"}))

            # Test channels
            print_status("Testing Power Mode channels...", "info")
            channels = [
                "pop:broadcast",
                "pop:heartbeat",
                "pop:results",
                "pop:insights",
                "pop:coordinator",
                "pop:human"
            ]

            for channel in channels:
                r.publish(channel, json.dumps({"test": True}))

            print_status("All tests passed!", "success")
            sys.exit(0)

        except Exception as e:
            print_status(f"Test failed: {e}", "error")
            sys.exit(1)

    else:
        print_status(f"Unknown command: {command}", "error")
        print("\nUsage:")
        print("  python setup-redis.py status      Check Redis status")
        print("  python setup-redis.py start       Start Redis")
        print("  python setup-redis.py stop        Stop Redis")
        print("  python setup-redis.py restart     Restart Redis")
        print("  python setup-redis.py debug       Start with Redis Commander")
        print("  python setup-redis.py test        Test Redis connectivity")
        sys.exit(1)


if __name__ == "__main__":
    main()
