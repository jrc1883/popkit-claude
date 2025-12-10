#!/usr/bin/env python3
"""
Premium Feature Checker

Part of Epic #126 (Premium Feature Gating)
Parent: Epic #125 (User Signup & Billing)

Checks if features require premium tier and validates user entitlement.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_API_URL = os.environ.get(
    "POPKIT_API_URL",
    "https://popkit-cloud-api.joseph-cannon.workers.dev"
)

# Cache entitlement for 5 minutes to reduce API calls
ENTITLEMENT_CACHE_TTL = 300


# =============================================================================
# TYPES
# =============================================================================

class Tier(Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


@dataclass
class PremiumFeature:
    """Definition of a premium feature."""
    name: str
    description: str
    required_tier: Tier
    free_tier_fallback: Optional[str] = None  # What to show/do for free users


@dataclass
class EntitlementResult:
    """Result of an entitlement check."""
    allowed: bool
    user_tier: Tier
    required_tier: Tier
    feature_name: str
    upgrade_message: Optional[str] = None
    fallback_available: bool = False


# =============================================================================
# PREMIUM FEATURE REGISTRY
# =============================================================================

# Registry of all premium features and their requirements
PREMIUM_FEATURES: Dict[str, PremiumFeature] = {
    # Project Generation Features (Pro+)
    "pop-mcp-generator": PremiumFeature(
        name="Custom MCP Server Generation",
        description="Generate project-specific MCP servers with semantic search",
        required_tier=Tier.PRO,
        free_tier_fallback="Basic project analysis available (no custom MCP)"
    ),
    "pop-skill-generator": PremiumFeature(
        name="Custom Skill Generation",
        description="Generate project-specific skills based on codebase patterns",
        required_tier=Tier.PRO,
        free_tier_fallback="View existing skills only"
    ),
    "pop-morning-generator": PremiumFeature(
        name="Custom Morning Routine",
        description="Generate project-tailored morning health checks",
        required_tier=Tier.PRO,
        free_tier_fallback="Default morning routine available"
    ),
    "pop-nightly-generator": PremiumFeature(
        name="Custom Nightly Routine",
        description="Generate project-tailored nightly cleanup routines",
        required_tier=Tier.PRO,
        free_tier_fallback="Default nightly routine available"
    ),

    # Multi-Project Features (Pro+)
    "pop-dashboard": PremiumFeature(
        name="Multi-Project Dashboard",
        description="Manage multiple projects from a single view",
        required_tier=Tier.PRO,
        free_tier_fallback="Single project mode only"
    ),

    # Pattern Sharing Features (Pro+)
    "pop-pattern-share": PremiumFeature(
        name="Pattern Sharing",
        description="Share learned patterns with team or community",
        required_tier=Tier.PRO,
        free_tier_fallback="Search patterns only (no submit)"
    ),

    # Embeddings Features (Pro+)
    "pop-embed-project": PremiumFeature(
        name="Project Embeddings",
        description="Embed project items for semantic search",
        required_tier=Tier.PRO,
        free_tier_fallback="Basic search without embeddings"
    ),
    "pop-embed-content": PremiumFeature(
        name="Content Embeddings",
        description="Manage project embeddings",
        required_tier=Tier.PRO,
        free_tier_fallback=None
    ),

    # Power Mode Features
    "pop-power-mode:redis": PremiumFeature(
        name="Power Mode (Hosted Redis)",
        description="Multi-agent orchestration with 6+ agents via cloud Redis",
        required_tier=Tier.PRO,
        free_tier_fallback="File-based Power Mode (2-3 agents)"
    ),

    # Team Features (Team tier only)
    "team-coordination": PremiumFeature(
        name="Team Coordination",
        description="Coordinate work across team members",
        required_tier=Tier.TEAM,
        free_tier_fallback=None
    ),
    "team-analytics": PremiumFeature(
        name="Team Analytics",
        description="View team-wide efficiency metrics",
        required_tier=Tier.TEAM,
        free_tier_fallback=None
    ),
}

# Commands that trigger premium features
COMMAND_TO_FEATURE: Dict[str, str] = {
    "/popkit:project mcp": "pop-mcp-generator",
    "/popkit:project generate": "pop-mcp-generator",
    "/popkit:project skills": "pop-skill-generator",
    "/popkit:routine generate": "pop-morning-generator",
    "/popkit:dashboard": "pop-dashboard",
    "/popkit:power init redis": "pop-power-mode:redis",
}

# Skills that are premium
PREMIUM_SKILLS = set(PREMIUM_FEATURES.keys())


# =============================================================================
# ENTITLEMENT CACHE
# =============================================================================

_entitlement_cache: Dict[str, Tuple[Tier, float]] = {}


def _get_cached_tier(api_key: str) -> Optional[Tier]:
    """Get cached tier if still valid."""
    import time

    if api_key in _entitlement_cache:
        tier, cached_at = _entitlement_cache[api_key]
        if time.time() - cached_at < ENTITLEMENT_CACHE_TTL:
            return tier
    return None


def _cache_tier(api_key: str, tier: Tier) -> None:
    """Cache tier for future lookups."""
    import time
    _entitlement_cache[api_key] = (tier, time.time())


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_user_tier(api_key: Optional[str] = None) -> Tier:
    """
    Get the user's current tier.

    Args:
        api_key: PopKit API key (or from POPKIT_API_KEY env)

    Returns:
        User's tier (defaults to FREE if no key or error)
    """
    key = api_key or os.environ.get("POPKIT_API_KEY")

    if not key:
        return Tier.FREE

    # Check cache first
    cached = _get_cached_tier(key)
    if cached:
        return cached

    # Query API
    try:
        url = f"{POPKIT_API_URL}/v1/auth/me"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode())
            tier_str = data.get("user", {}).get("tier", "free")
            tier = Tier(tier_str)
            _cache_tier(key, tier)
            return tier

    except Exception:
        return Tier.FREE


def is_premium_feature(feature_name: str) -> bool:
    """
    Check if a feature is premium.

    Args:
        feature_name: Name of the skill/feature

    Returns:
        True if feature requires premium
    """
    return feature_name in PREMIUM_FEATURES


def get_feature_info(feature_name: str) -> Optional[PremiumFeature]:
    """
    Get information about a premium feature.

    Args:
        feature_name: Name of the skill/feature

    Returns:
        PremiumFeature info or None
    """
    return PREMIUM_FEATURES.get(feature_name)


def check_entitlement(
    feature_name: str,
    api_key: Optional[str] = None
) -> EntitlementResult:
    """
    Check if user is entitled to use a feature.

    Args:
        feature_name: Name of the skill/feature
        api_key: PopKit API key (or from POPKIT_API_KEY env)

    Returns:
        EntitlementResult with allowed status and upgrade info
    """
    user_tier = get_user_tier(api_key)
    feature = PREMIUM_FEATURES.get(feature_name)

    # If feature isn't in registry, it's free
    if not feature:
        return EntitlementResult(
            allowed=True,
            user_tier=user_tier,
            required_tier=Tier.FREE,
            feature_name=feature_name
        )

    # Check tier hierarchy: FREE < PRO < TEAM
    tier_order = {Tier.FREE: 0, Tier.PRO: 1, Tier.TEAM: 2}
    allowed = tier_order[user_tier] >= tier_order[feature.required_tier]

    return EntitlementResult(
        allowed=allowed,
        user_tier=user_tier,
        required_tier=feature.required_tier,
        feature_name=feature.name,
        upgrade_message=None if allowed else _get_upgrade_message(feature, user_tier),
        fallback_available=feature.free_tier_fallback is not None
    )


def _get_upgrade_message(feature: PremiumFeature, user_tier: Tier) -> str:
    """Generate upgrade message for a feature."""
    tier_name = feature.required_tier.value.title()
    price = "$9/mo" if feature.required_tier == Tier.PRO else "$29/mo"

    msg = f"""
⭐ Premium Feature: {feature.name}

{feature.description}

Required tier: {tier_name} ({price})
Your tier: {user_tier.value.title()}
"""

    if feature.free_tier_fallback:
        msg += f"\nFree tier alternative: {feature.free_tier_fallback}"

    msg += "\n\nRun `/popkit:upgrade` to unlock premium features."

    return msg.strip()


def get_upgrade_prompt_options(feature_name: str) -> Dict[str, Any]:
    """
    Get AskUserQuestion options for an upgrade prompt.

    Args:
        feature_name: Name of the feature being gated

    Returns:
        Dict with question, header, options for AskUserQuestion
    """
    feature = PREMIUM_FEATURES.get(feature_name)

    if not feature:
        return {}

    options = [
        {
            "label": "Upgrade to Premium",
            "description": f"Unlock {feature.name} and all premium features"
        }
    ]

    if feature.free_tier_fallback:
        options.append({
            "label": "Continue with free tier",
            "description": feature.free_tier_fallback
        })
    else:
        options.append({
            "label": "Cancel",
            "description": "Return without using this feature"
        })

    return {
        "question": f"This feature requires PopKit Premium. What would you like to do?",
        "header": "Premium",
        "options": options,
        "multiSelect": False
    }


def list_premium_features(tier: Optional[Tier] = None) -> List[PremiumFeature]:
    """
    List all premium features, optionally filtered by tier.

    Args:
        tier: Filter to features requiring this tier

    Returns:
        List of premium features
    """
    features = list(PREMIUM_FEATURES.values())

    if tier:
        features = [f for f in features if f.required_tier == tier]

    return features


# =============================================================================
# RATE LIMITS (Issue #139)
# =============================================================================

# Rate limits per tier per feature (daily, monthly)
# -1 = unlimited
RATE_LIMITS: Dict[str, Dict[str, Dict[str, int]]] = {
    "free": {
        "default": {"daily": 100, "monthly": 3000},
        "pop-embed-project": {"daily": 10, "monthly": 100},
        "pop-embed-content": {"daily": 10, "monthly": 100},
        "pop-pattern-share": {"daily": 20, "monthly": 500},
        "pop-power-mode:redis": {"daily": 5, "monthly": 50},
    },
    "pro": {
        "default": {"daily": -1, "monthly": -1},
        "pop-embed-project": {"daily": 1000, "monthly": 10000},
        "pop-embed-content": {"daily": 1000, "monthly": 10000},
    },
    "team": {
        "default": {"daily": -1, "monthly": -1},
    },
}


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    current: int
    limit: int
    remaining: int
    reset_at: str
    feature: str
    tier: str


def get_rate_limit_for_feature(tier: str, feature: str) -> Dict[str, int]:
    """Get rate limits for a feature based on tier."""
    tier_limits = RATE_LIMITS.get(tier, RATE_LIMITS["free"])
    return tier_limits.get(feature, tier_limits.get("default", {"daily": 100, "monthly": 3000}))


def format_rate_limit_message(result: RateLimitResult) -> str:
    """Generate a user-friendly rate limit message."""
    if result.allowed:
        if result.limit == -1:
            return f"✅ {result.feature}: Unlimited usage ({result.tier} tier)"
        return f"✅ {result.feature}: {result.remaining} remaining today"

    # Rate limited
    msg = f"""
⚠️ Rate Limit Reached: {result.feature}

You've used {result.current} of {result.limit} allowed today.
Resets at: {result.reset_at}

Your tier: {result.tier}
"""

    if result.tier == "free":
        msg += """
💡 Upgrade to Pro for unlimited access!
Run `/popkit:upgrade` to unlock.
"""

    return msg.strip()


# =============================================================================
# USAGE TRACKING (Issue #138)
# =============================================================================

@dataclass
class UsageEvent:
    """A tracked usage event for a premium feature."""
    feature: str
    tier: str
    timestamp: str
    project_id: str
    success: bool
    user_id: Optional[str] = None


def _get_project_id() -> str:
    """Generate a privacy-respecting project identifier (hash of path)."""
    import hashlib
    cwd = os.getcwd()
    return hashlib.sha256(cwd.encode()).hexdigest()[:16]


def track_feature_usage(
    feature_name: str,
    success: bool = True,
    api_key: Optional[str] = None
) -> bool:
    """
    Track usage of a premium feature.

    Args:
        feature_name: Name of the feature used
        success: Whether the feature executed successfully
        api_key: PopKit API key (or from POPKIT_API_KEY env)

    Returns:
        True if tracking was successful
    """
    from datetime import datetime

    key = api_key or os.environ.get("POPKIT_API_KEY")
    if not key:
        return False  # Can't track without API key

    user_tier = get_user_tier(key)

    event = UsageEvent(
        feature=feature_name,
        tier=user_tier.value,
        timestamp=datetime.utcnow().isoformat() + "Z",
        project_id=_get_project_id(),
        success=success
    )

    try:
        url = f"{POPKIT_API_URL}/v1/usage/track"
        data = json.dumps({
            "feature": event.feature,
            "tier": event.tier,
            "timestamp": event.timestamp,
            "project_id": event.project_id,
            "success": event.success
        }).encode()

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200

    except Exception:
        return False  # Don't fail if tracking fails


def get_usage_summary(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get usage summary for the current user.

    Args:
        api_key: PopKit API key (or from POPKIT_API_KEY env)

    Returns:
        Dict with usage statistics
    """
    key = api_key or os.environ.get("POPKIT_API_KEY")
    if not key:
        return {"error": "No API key"}

    try:
        url = f"{POPKIT_API_URL}/v1/usage/summary"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode())

    except Exception as e:
        return {"error": str(e)}


def check_rate_limit(
    feature_name: str,
    api_key: Optional[str] = None
) -> RateLimitResult:
    """
    Check if user has exceeded rate limit for a feature.

    Args:
        feature_name: Name of the feature to check
        api_key: PopKit API key (or from POPKIT_API_KEY env)

    Returns:
        RateLimitResult with allowed status and limit info
    """
    from datetime import datetime, timedelta

    key = api_key or os.environ.get("POPKIT_API_KEY")
    tier = get_user_tier(key).value if key else "free"

    # Calculate reset time (end of day UTC)
    now = datetime.utcnow()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    reset_at = end_of_day.isoformat() + "Z"

    if not key:
        # Free tier defaults - use local limits
        limits = get_rate_limit_for_feature("free", feature_name)
        return RateLimitResult(
            allowed=True,  # Allow locally, actual enforcement on server
            current=0,
            limit=limits["daily"],
            remaining=limits["daily"],
            reset_at=reset_at,
            feature=feature_name,
            tier="free"
        )

    try:
        url = f"{POPKIT_API_URL}/v1/usage/limits?feature={feature_name}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode())
            return RateLimitResult(
                allowed=data.get("allowed", True),
                current=data.get("current", {}).get("daily", 0),
                limit=data.get("limit", {}).get("daily", -1),
                remaining=data.get("remaining", {}).get("daily", -1),
                reset_at=data.get("reset_at", {}).get("daily", reset_at),
                feature=feature_name,
                tier=data.get("tier", tier)
            )

    except Exception:
        # Allow on error - don't block users due to API issues
        limits = get_rate_limit_for_feature(tier, feature_name)
        return RateLimitResult(
            allowed=True,
            current=0,
            limit=limits["daily"],
            remaining=limits["daily"],
            reset_at=reset_at,
            feature=feature_name,
            tier=tier
        )


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: premium_checker.py <command> [args]")
        print("Commands: check <feature>, list, tier, usage, track <feature>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        feature = sys.argv[2] if len(sys.argv) > 2 else "pop-mcp-generator"
        result = check_entitlement(feature)
        print(f"Feature: {result.feature_name}")
        print(f"Allowed: {result.allowed}")
        print(f"User tier: {result.user_tier.value}")
        print(f"Required: {result.required_tier.value}")
        if result.upgrade_message:
            print(f"\n{result.upgrade_message}")

    elif command == "list":
        print("Premium Features:")
        for feature in list_premium_features():
            print(f"  [{feature.required_tier.value}] {feature.name}")

    elif command == "tier":
        tier = get_user_tier()
        print(f"Your tier: {tier.value}")

    elif command == "usage":
        summary = get_usage_summary()
        if "error" in summary:
            print(f"Error: {summary['error']}")
        else:
            print("Usage Summary:")
            print(json.dumps(summary, indent=2))

    elif command == "track":
        feature = sys.argv[2] if len(sys.argv) > 2 else "pop-mcp-generator"
        success = track_feature_usage(feature)
        print(f"Tracked {feature}: {'success' if success else 'failed'}")

    elif command == "limit":
        feature = sys.argv[2] if len(sys.argv) > 2 else "pop-mcp-generator"
        result = check_rate_limit(feature)
        print(format_rate_limit_message(result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
