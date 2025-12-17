#!/usr/bin/env python3
"""
Version Check Utility
Non-blocking update notification system for popkit.

Features:
- 24-hour TTL cache for update checks
- Semantic version comparison
- GitHub API integration with timeout
- Silent failure on network errors
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# Optional import with graceful fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Constants
GITHUB_API_URL = "https://api.github.com/repos/jrc1883/popkit/releases/latest"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 5  # Non-blocking timeout

# Claude Code version requirements
CLAUDE_CODE_REQUIREMENTS = {
    "extended_thinking": "2.0.67",
    "native_async_mode": "2.0.64",
    "plan_mode": "2.0.70",
    "config_toggle": "2.0.71",
    "settings_alias": "2.0.71",
    "mcp_permissions_fix": "2.0.71",
    "bash_glob_safety": "2.0.71",
    "bedrock_support": "2.0.71",
}

POPKIT_MINIMUM_CLAUDE_CODE = "2.0.71"

# Path resolution - works from hooks directory
HOOKS_DIR = Path(__file__).parent.parent
PLUGIN_JSON_PATH = HOOKS_DIR.parent / ".claude-plugin" / "plugin.json"
SETTINGS_PATH = Path.home() / ".claude" / "settings.local.json"


class SemanticVersion:
    """Parse and compare semantic versions."""

    def __init__(self, version_string: str):
        # Strip 'v' prefix if present
        clean = version_string.lstrip('v')

        # Parse major.minor.patch
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', clean)
        if not match:
            raise ValueError(f"Invalid version: {version_string}")

        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.raw = version_string

    def __gt__(self, other: 'SemanticVersion') -> bool:
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch

    def __eq__(self, other: 'SemanticVersion') -> bool:
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def get_current_version() -> Optional[str]:
    """Read current version from plugin.json."""
    try:
        if PLUGIN_JSON_PATH.exists():
            with open(PLUGIN_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version')
    except (json.JSONDecodeError, IOError):
        pass
    return None


def load_cache() -> Dict[str, Any]:
    """Load cache data from settings.local.json."""
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def save_cache(cache_data: Dict[str, Any]) -> bool:
    """Save cache data to settings.local.json."""
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
        return True
    except IOError:
        return False


def is_cache_valid(cache_data: Dict[str, Any]) -> bool:
    """Check if cached update info is still valid (< 24 hours old)."""
    update_cache = cache_data.get('popkit_update_check', {})
    last_check = update_cache.get('last_checked')

    if not last_check:
        return False

    try:
        last_check_time = datetime.fromisoformat(last_check)
        return datetime.now() - last_check_time < timedelta(hours=CACHE_TTL_HOURS)
    except ValueError:
        return False


def fetch_latest_version() -> Optional[Dict[str, Any]]:
    """Fetch latest release info from GitHub API.

    Returns:
        Dict with 'version', 'name', 'url', 'body' on success
        None on failure (network error, timeout, etc.)
    """
    if not HAS_REQUESTS:
        return None

    try:
        response = requests.get(
            GITHUB_API_URL,
            headers={'Accept': 'application/vnd.github.v3+json'},
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            data = response.json()
            return {
                'version': data.get('tag_name', '').lstrip('v'),
                'name': data.get('name', ''),
                'url': data.get('html_url', ''),
                'body': data.get('body', '')[:500]  # Limit body size
            }
    except Exception:
        pass  # Silent failure

    return None


def check_for_updates() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check for popkit updates with caching.

    Returns:
        (update_available: bool, release_info: Optional[Dict])
    """
    # Load cache
    cache_data = load_cache()

    # Check if cache is valid
    if is_cache_valid(cache_data):
        cached_info = cache_data.get('popkit_update_check', {})
        cached_latest = cached_info.get('latest_version')
        current = get_current_version()

        if cached_latest and current:
            try:
                latest_ver = SemanticVersion(cached_latest)
                current_ver = SemanticVersion(current)

                if latest_ver > current_ver:
                    return True, {
                        'version': cached_latest,
                        'name': cached_info.get('release_name', ''),
                        'url': cached_info.get('release_url', '')
                    }
            except ValueError:
                pass

        return False, None

    # Cache expired or missing - fetch from GitHub
    release_info = fetch_latest_version()
    current = get_current_version()

    # Update cache regardless of result
    cache_data['popkit_update_check'] = {
        'last_checked': datetime.now().isoformat(),
        'latest_version': release_info.get('version') if release_info else None,
        'release_name': release_info.get('name') if release_info else None,
        'release_url': release_info.get('url') if release_info else None,
        'current_version': current
    }
    save_cache(cache_data)

    # Compare versions
    if release_info and current:
        try:
            latest_ver = SemanticVersion(release_info['version'])
            current_ver = SemanticVersion(current)

            if latest_ver > current_ver:
                return True, release_info
        except ValueError:
            pass

    return False, None


def is_feature_available(feature_name: str, claude_code_version: Optional[str] = None) -> bool:
    """Check if a PopKit feature is available in the current Claude Code version.

    Args:
        feature_name: Feature key from CLAUDE_CODE_REQUIREMENTS
        claude_code_version: Claude Code version to check (from environment if not provided)

    Returns:
        True if feature is available, False otherwise
    """
    if feature_name not in CLAUDE_CODE_REQUIREMENTS:
        return False

    required_version = CLAUDE_CODE_REQUIREMENTS[feature_name]

    if not claude_code_version:
        claude_code_version = os.environ.get('CLAUDE_CODE_VERSION')

    if not claude_code_version:
        return False

    try:
        current = SemanticVersion(claude_code_version)
        required = SemanticVersion(required_version)
        return current >= required
    except ValueError:
        return False


def meets_minimum_requirements(claude_code_version: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Check if Claude Code version meets PopKit minimum requirements.

    Args:
        claude_code_version: Claude Code version to check (from environment if not provided)

    Returns:
        (meets_requirements: bool, error_message: Optional[str])
    """
    if not claude_code_version:
        claude_code_version = os.environ.get('CLAUDE_CODE_VERSION')

    if not claude_code_version:
        return False, "CLAUDE_CODE_VERSION environment variable not set"

    try:
        current = SemanticVersion(claude_code_version)
        minimum = SemanticVersion(POPKIT_MINIMUM_CLAUDE_CODE)

        if current >= minimum:
            return True, None
        else:
            return False, f"PopKit requires Claude Code {POPKIT_MINIMUM_CLAUDE_CODE}+, found {claude_code_version}"
    except ValueError:
        return False, f"Invalid Claude Code version format: {claude_code_version}"


def format_update_notification(release_info: Dict[str, Any], current_version: str) -> str:
    """Format update notification message for stderr output."""
    latest = release_info.get('version', 'unknown')
    name = release_info.get('name', '')

    lines = [
        "",
        "=" * 60,
        f"  popkit update available: {current_version} -> {latest}",
    ]

    if name and name != f"v{latest}" and name != latest:
        lines.append(f"  Release: {name}")

    lines.extend([
        "",
        "  Update with: /plugin update popkit@popkit-marketplace",
        "=" * 60,
        ""
    ])

    return "\n".join(lines)


# Entry point for direct testing
if __name__ == "__main__":
    print("Testing version check...")
    current = get_current_version()
    print(f"Current version: {current}")
    print(f"Plugin JSON path: {PLUGIN_JSON_PATH}")
    print(f"Settings path: {SETTINGS_PATH}")

    has_update, info = check_for_updates()
    if has_update:
        print(format_update_notification(info, current))
    else:
        print("No update available or check failed")
