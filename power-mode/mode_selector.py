#!/usr/bin/env python3
"""
Power Mode Selector

Auto-selects the best Power Mode based on environment:
1. Native Async (Claude Code 2.0.64+) - Zero config, uses background agents
2. Redis Mode - Full power, requires Docker/Redis setup
3. File Mode - Fallback, works everywhere but limited

Priority order can be configured in config.json.
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Tuple
from enum import Enum


class PowerMode(Enum):
    """Available Power Mode implementations."""
    NATIVE = "native"      # Claude Code native async (2.0.64+)
    UPSTASH = "upstash"    # Upstash cloud Redis (no Docker, Issue #191)
    REDIS = "redis"        # Local Redis pub/sub (Docker required)
    FILE = "file"          # File-based coordination (fallback)
    DISABLED = "disabled"  # Power Mode not available


class ModeSelector:
    """
    Selects the best available Power Mode based on environment.

    Checks:
    1. Claude Code version (for native async support)
    2. Premium tier status (for agent limits)
    3. Redis availability (for Redis mode)
    4. Configuration preferences
    """

    # Minimum Claude Code version for native async
    MIN_NATIVE_VERSION = "2.0.64"

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the mode selector."""
        self.config = config or self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def select_mode(self) -> Tuple[PowerMode, str]:
        """
        Select the best available Power Mode.

        Returns:
            Tuple of (PowerMode, reason_string)
        """
        # Check configured priority order
        # Issue #191: Added upstash to priority (between native and redis)
        priority = self.config.get("mode_priority", ["native", "upstash", "redis", "file"])

        for mode_name in priority:
            if mode_name == "native":
                available, reason = self._check_native_available()
                if available:
                    return PowerMode.NATIVE, reason

            elif mode_name == "upstash":
                available, reason = self._check_upstash_available()
                if available:
                    return PowerMode.UPSTASH, reason

            elif mode_name == "redis":
                available, reason = self._check_redis_available()
                if available:
                    return PowerMode.REDIS, reason

            elif mode_name == "file":
                # File mode is always available
                return PowerMode.FILE, "File-based mode (always available)"

        # Fallback
        return PowerMode.FILE, "Fallback to file-based mode"

    def _check_native_available(self) -> Tuple[bool, str]:
        """
        Check if native async mode is available.

        Requires Claude Code 2.0.64+ with background agent support.
        """
        # Check if native mode is enabled in config
        native_config = self.config.get("native", {})
        if not native_config.get("enabled", True):
            return False, "Native mode disabled in config"

        # Try to detect Claude Code version
        version = self._get_claude_code_version()
        if version is None:
            # Can't detect version - assume available if in Claude Code context
            if os.environ.get("CLAUDE_CODE_VERSION"):
                return True, "Claude Code detected (version unknown)"
            return False, "Claude Code not detected"

        # Compare versions
        if self._version_compare(version, self.MIN_NATIVE_VERSION) >= 0:
            return True, f"Claude Code {version} supports native async"

        return False, f"Claude Code {version} < {self.MIN_NATIVE_VERSION} (native async requires 2.0.64+)"

    def _check_upstash_available(self) -> Tuple[bool, str]:
        """
        Check if Upstash cloud Redis is available.

        Issue #191: Upstash provides cloud Redis without Docker requirement.
        Requires UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN env vars.
        """
        # Check for Upstash env vars
        upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL")
        upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

        if upstash_url and upstash_token:
            # Try to verify connection
            try:
                from .upstash_adapter import UpstashRedisClient
                client = UpstashRedisClient(url=upstash_url, token=upstash_token)
                if client.ping():
                    return True, f"Upstash cloud Redis: {upstash_url[:40]}..."
                return False, "Upstash configured but ping failed"
            except Exception as e:
                return False, f"Upstash configured but connection failed: {e}"

        return False, "Upstash not configured (set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN)"

    def _check_redis_available(self) -> Tuple[bool, str]:
        """
        Check if Redis mode is available.

        Requires:
        1. Docker installed and running
        2. Redis container available or cloud URL configured
        """
        # Check for cloud Redis URL first
        cloud_url = os.environ.get("POPKIT_REDIS_URL")
        if cloud_url:
            return True, f"Cloud Redis configured: {cloud_url[:30]}..."

        # Check for local Redis via Docker
        if self._docker_available():
            # Check if Redis container is running
            if self._redis_container_running():
                return True, "Local Redis container running"
            else:
                return False, "Docker available but Redis container not running"

        return False, "Docker not available for Redis mode"

    def _get_claude_code_version(self) -> Optional[str]:
        """
        Try to detect Claude Code version.

        Returns version string or None if undetectable.
        """
        # Check environment variable
        version = os.environ.get("CLAUDE_CODE_VERSION")
        if version:
            return version

        # Try to parse from claude --version
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from output like "Claude Code v2.0.64"
                match = re.search(r'v?(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return None

    def _docker_available(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _redis_container_running(self) -> bool:
        """Check if popkit-redis container is running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=popkit-redis", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "popkit-redis" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _version_compare(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        def normalize(v):
            return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.')]

        parts1 = normalize(v1)
        parts2 = normalize(v2)

        # Pad shorter version
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)

        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            if p1 > p2:
                return 1
        return 0

    def get_tier_limits(self, tier: str = "free") -> Dict:
        """
        Get agent limits for a tier.

        Args:
            tier: "free", "premium", or "pro"
        """
        tier_config = self.config.get("tier_limits", {})
        return tier_config.get(tier, {
            "mode": "file",
            "max_agents": 2
        })

    def format_status(self) -> str:
        """Format mode selection status for display."""
        mode, reason = self.select_mode()

        status_lines = [
            f"Power Mode: {mode.value.upper()}",
            f"Reason: {reason}",
            ""
        ]

        # Add mode-specific info
        if mode == PowerMode.NATIVE:
            native_config = self.config.get("native", {})
            status_lines.extend([
                f"Max Agents: {native_config.get('max_parallel_agents', 5)}",
                "Setup: Zero config required"
            ])
        elif mode == PowerMode.UPSTASH:
            upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL", "")
            status_lines.extend([
                f"Upstash: {upstash_url[:40]}..." if upstash_url else "Upstash: configured",
                "Setup: Set env vars (no Docker required)",
                "Max Agents: 6+ (parallel)"
            ])
        elif mode == PowerMode.REDIS:
            redis_config = self.config.get("redis", {})
            status_lines.extend([
                f"Redis: {redis_config.get('host', 'localhost')}:{redis_config.get('port', 16379)}",
                "Setup: Docker + Redis container"
            ])
        elif mode == PowerMode.FILE:
            status_lines.extend([
                "Max Agents: 2-3 (sequential)",
                "Setup: None required"
            ])

        return "\n".join(status_lines)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def auto_select_mode() -> PowerMode:
    """Convenience function to auto-select mode."""
    selector = ModeSelector()
    mode, _ = selector.select_mode()
    return mode


def get_mode_for_tier(tier: str) -> PowerMode:
    """Get the recommended mode for a user tier."""
    selector = ModeSelector()
    limits = selector.get_tier_limits(tier)
    mode_name = limits.get("mode", "file")

    return PowerMode(mode_name)


def print_mode_status():
    """Print mode selection status to stdout."""
    selector = ModeSelector()
    print(selector.format_status())


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Power Mode Selector")
    parser.add_argument("--select", action="store_true", help="Auto-select best mode")
    parser.add_argument("--status", action="store_true", help="Show full status")
    parser.add_argument("--check", type=str, choices=["native", "upstash", "redis", "file"], help="Check specific mode")
    parser.add_argument("--tier", type=str, default="free", help="User tier (free, premium, pro)")

    args = parser.parse_args()

    selector = ModeSelector()

    if args.select:
        mode, reason = selector.select_mode()
        print(f"{mode.value}")

    elif args.status:
        print(selector.format_status())

    elif args.check:
        if args.check == "native":
            available, reason = selector._check_native_available()
            print(f"Native: {'Yes' if available else 'No'} - {reason}")
        elif args.check == "upstash":
            available, reason = selector._check_upstash_available()
            print(f"Upstash: {'Yes' if available else 'No'} - {reason}")
        elif args.check == "redis":
            available, reason = selector._check_redis_available()
            print(f"Redis: {'Yes' if available else 'No'} - {reason}")
        elif args.check == "file":
            print("File: Yes - Always available")

    elif args.tier:
        limits = selector.get_tier_limits(args.tier)
        print(f"Tier: {args.tier}")
        print(f"Mode: {limits.get('mode', 'file')}")
        print(f"Max Agents: {limits.get('max_agents', 2)}")

    else:
        # Default: show status
        print(selector.format_status())
