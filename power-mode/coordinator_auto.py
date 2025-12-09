#!/usr/bin/env python3
"""
Auto-Detecting Power Mode Coordinator
Automatically uses Redis if available, falls back to file-based storage.

Usage:
    from coordinator_auto import create_coordinator

    coordinator = create_coordinator(objective)
    coordinator.start()
"""

import sys
from pathlib import Path
from typing import Optional

# Try Redis first
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Import file fallback
from file_fallback import FileBasedPowerMode

# Import base coordinator
from coordinator import PowerModeCoordinator, load_config
from protocol import Objective


def redis_is_running() -> bool:
    """Check if Redis is actually running and accessible."""
    if not REDIS_AVAILABLE:
        return False

    try:
        config = load_config()
        redis_config = config.get("redis", {})

        r = redis.Redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            db=redis_config.get("db", 0),
            password=redis_config.get("password"),
            socket_timeout=2,  # Short timeout for quick check
            decode_responses=True
        )
        r.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError):
        return False


class AutoCoordinator(PowerModeCoordinator):
    """
    Coordinator that auto-detects Redis vs file-based storage.

    Inherits from PowerModeCoordinator but overrides the connect() method
    to use file-based fallback if Redis is not available.
    """

    def __init__(self, objective: Optional[Objective] = None, force_file_mode: bool = False):
        """
        Initialize coordinator with auto-detection.

        Args:
            objective: The objective to work toward
            force_file_mode: Force file-based mode even if Redis is available
        """
        super().__init__(objective)
        self.force_file_mode = force_file_mode
        self.is_file_mode = False

    def connect(self) -> bool:
        """Connect to Redis or fallback to file-based storage."""
        # Check if we should use Redis
        use_redis = not self.force_file_mode and REDIS_AVAILABLE and redis_is_running()

        if use_redis:
            # Use Redis
            print("🔌 Using Redis for Power Mode")
            return super().connect()
        else:
            # Use file-based fallback
            if self.force_file_mode:
                reason = "forced file mode"
            elif not REDIS_AVAILABLE:
                reason = "redis module not installed"
            else:
                reason = "redis not running"

            print(f"📁 Using file-based fallback for Power Mode ({reason})")
            print(f"   State file: .claude/popkit/power-mode-state.json")
            print(f"   Limitations: polling (not true pub/sub), single-machine only")
            print()

            self.is_file_mode = True

            # Create file-based client
            try:
                self.redis = FileBasedPowerMode()
                if not self.redis.ping():
                    print("Failed to initialize file-based storage", file=sys.stderr)
                    return False

                # Create pubsub object
                self.pubsub = self.redis.pubsub()
                return True

            except Exception as e:
                print(f"Failed to initialize file-based storage: {e}", file=sys.stderr)
                return False

    def start(self):
        """Start the coordinator with connection info."""
        result = super().start()

        if result and self.is_file_mode:
            print()
            print("⚠️  File-based mode limitations:")
            print("   - Polling-based (100ms intervals), not instant")
            print("   - Best for 2-3 agents, performance degrades with 4+")
            print("   - Single machine only")
            print("   - To use Redis: docker run -d -p 6379:6379 redis")
            print()

        return result


def create_coordinator(objective: Optional[Objective] = None,
                      force_file_mode: bool = False) -> AutoCoordinator:
    """
    Create a coordinator with auto-detection.

    Args:
        objective: The objective to work toward
        force_file_mode: Force file-based mode even if Redis is available

    Returns:
        AutoCoordinator instance
    """
    return AutoCoordinator(objective, force_file_mode)


def get_mode_info() -> dict:
    """
    Get information about which mode would be used.

    Returns:
        {
            "mode": "redis" | "file",
            "redis_available": bool,
            "redis_running": bool,
            "file_path": str (if file mode),
            "recommendation": str
        }
    """
    redis_available = REDIS_AVAILABLE
    redis_running = redis_is_running() if redis_available else False

    mode = "redis" if redis_running else "file"
    file_path = str(Path.cwd() / ".claude" / "popkit" / "power-mode-state.json")

    if not redis_available:
        recommendation = "Install redis: pip install redis"
    elif not redis_running:
        recommendation = "Start Redis: docker run -d -p 6379:6379 redis"
    else:
        recommendation = "Redis is ready!"

    return {
        "mode": mode,
        "redis_available": redis_available,
        "redis_running": redis_running,
        "file_path": file_path if mode == "file" else None,
        "recommendation": recommendation
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    from protocol import create_objective

    parser = argparse.ArgumentParser(description="Auto-detecting Power Mode Coordinator")
    parser.add_argument("command", choices=["start", "info", "cleanup"])
    parser.add_argument("--objective", help="Objective description")
    parser.add_argument("--phases", nargs="+", help="Phase names")
    parser.add_argument("--success-criteria", nargs="+", help="Success criteria")
    parser.add_argument("--force-file", action="store_true", help="Force file-based mode")

    args = parser.parse_args()

    if args.command == "info":
        # Show mode info
        info = get_mode_info()
        print(f"Mode: {info['mode']}")
        print(f"Redis available: {info['redis_available']}")
        print(f"Redis running: {info['redis_running']}")
        if info['file_path']:
            print(f"File path: {info['file_path']}")
        print(f"\n{info['recommendation']}")

    elif args.command == "cleanup":
        # Clean up old messages
        from file_fallback import cleanup_old_messages, get_stats

        state_file = Path.cwd() / ".claude" / "popkit" / "power-mode-state.json"
        if not state_file.exists():
            print("No state file found")
            sys.exit(0)

        print("Before cleanup:")
        stats = get_stats(state_file)
        print(f"  Messages: {stats['total_messages']}")
        print(f"  File size: {stats['file_size_kb']} KB")

        cleanup_old_messages(state_file, max_age_hours=24)

        print("\nAfter cleanup:")
        stats = get_stats(state_file)
        print(f"  Messages: {stats['total_messages']}")
        print(f"  File size: {stats['file_size_kb']} KB")

    elif args.command == "start":
        # Start coordinator
        objective = None
        if args.objective:
            objective = create_objective(
                description=args.objective,
                success_criteria=args.success_criteria or ["Task completed"],
                phases=args.phases or ["explore", "implement", "review"]
            )

        coordinator = create_coordinator(objective, force_file_mode=args.force_file)

        if coordinator.start():
            print("Press Ctrl+C to stop...")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                coordinator.stop()
        else:
            print("Failed to start coordinator")
            sys.exit(1)
