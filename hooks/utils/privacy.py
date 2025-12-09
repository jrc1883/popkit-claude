#!/usr/bin/env python3
"""
Privacy & Data Anonymization Pipeline

Part of Issue #77 (Privacy & Data Anonymization Pipeline)

Provides robust anonymization for collective learning while ensuring
user privacy. Supports multiple anonymization levels and user controls.
"""

import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# =============================================================================
# ANONYMIZATION LEVELS
# =============================================================================

class AnonymizationLevel(Enum):
    """Anonymization levels for pattern sharing."""
    STRICT = "strict"      # Abstract patterns only, no code
    MODERATE = "moderate"  # Patterns + generic code (default)
    MINIMAL = "minimal"    # More context preserved (open source)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class PrivacySettings:
    """User privacy settings for collective learning."""
    # Sharing controls
    sharing_enabled: bool = True
    anonymization_level: str = "moderate"

    # Consent tracking
    consent_given: bool = False
    consent_timestamp: Optional[str] = None
    consent_version: str = "1.0"

    # Exclusions
    excluded_projects: List[str] = field(default_factory=list)
    excluded_patterns: List[str] = field(default_factory=list)

    # Data retention
    auto_delete_days: int = 90  # Delete shared data after N days

    # Region (for GDPR)
    data_region: str = "us"  # "us" or "eu"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PrivacySettings':
        """Create from dictionary."""
        return cls(
            sharing_enabled=data.get("sharing_enabled", True),
            anonymization_level=data.get("anonymization_level", "moderate"),
            consent_given=data.get("consent_given", False),
            consent_timestamp=data.get("consent_timestamp"),
            consent_version=data.get("consent_version", "1.0"),
            excluded_projects=data.get("excluded_projects", []),
            excluded_patterns=data.get("excluded_patterns", []),
            auto_delete_days=data.get("auto_delete_days", 90),
            data_region=data.get("data_region", "us")
        )


# =============================================================================
# SENSITIVE PATTERN DETECTION
# =============================================================================

# Patterns that indicate sensitive data
SENSITIVE_PATTERNS = {
    # API Keys and tokens
    "api_key": [
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_-]{16,})["\']?',
        r'(?i)(secret|token|password|auth)\s*[:=]\s*["\']?([A-Za-z0-9_-]{8,})["\']?',
        r'pk_[a-z]+_[A-Za-z0-9]{20,}',  # Stripe-style keys
        r'sk_[a-z]+_[A-Za-z0-9]{20,}',
        r'Bearer\s+[A-Za-z0-9_.-]+',
    ],

    # Personal info
    "email": [
        r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    ],
    "phone": [
        r'\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
    ],

    # File paths
    "paths": [
        r'/Users/[^/\s]+/',
        r'/home/[^/\s]+/',
        r'C:\\Users\\[^\\]+\\',
        r'C:/Users/[^/]+/',
    ],

    # Network
    "ip_address": [
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    ],
    "url_with_auth": [
        r'https?://[^:]+:[^@]+@',
    ],

    # Identifiers
    "uuid": [
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    ],
    "database_connection": [
        r'(?i)(mongodb|postgres|mysql|redis)://[^\s]+',
    ],
}

# Replacement tokens by category
REPLACEMENT_TOKENS = {
    "api_key": "[API_KEY]",
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "paths": "project/",
    "ip_address": "[IP_ADDRESS]",
    "url_with_auth": "https://[AUTH_URL]/",
    "uuid": "[UUID]",
    "database_connection": "[DATABASE_URL]",
}


# =============================================================================
# ANONYMIZATION FUNCTIONS
# =============================================================================

def detect_sensitive_data(content: str) -> List[Dict[str, Any]]:
    """
    Detect sensitive data patterns in content.

    Returns list of detected patterns with category and match info.
    """
    detections = []

    for category, patterns in SENSITIVE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                detections.append({
                    "category": category,
                    "pattern": pattern,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })

    return detections


def anonymize_content(
    content: str,
    level: AnonymizationLevel = AnonymizationLevel.MODERATE
) -> Tuple[str, List[str]]:
    """
    Anonymize content based on level.

    Args:
        content: Content to anonymize
        level: Anonymization level

    Returns:
        Tuple of (anonymized_content, list of removed categories)
    """
    result = content
    removed_categories = []

    # Always remove these (all levels)
    always_remove = ["api_key", "email", "database_connection", "url_with_auth"]

    # Level-specific removals
    if level == AnonymizationLevel.STRICT:
        # Remove everything sensitive
        categories = list(SENSITIVE_PATTERNS.keys())
    elif level == AnonymizationLevel.MODERATE:
        # Remove most, keep some context
        categories = always_remove + ["paths", "uuid"]
    else:  # MINIMAL
        # Only remove obviously sensitive
        categories = always_remove

    for category in categories:
        if category not in SENSITIVE_PATTERNS:
            continue

        for pattern in SENSITIVE_PATTERNS[category]:
            replacement = REPLACEMENT_TOKENS.get(category, f"[{category.upper()}]")
            if re.search(pattern, result, re.IGNORECASE):
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                if category not in removed_categories:
                    removed_categories.append(category)

    # Additional processing for STRICT level
    if level == AnonymizationLevel.STRICT:
        # Abstract function/variable names
        result = abstract_code_identifiers(result)

    return result, removed_categories


def abstract_code_identifiers(content: str) -> str:
    """
    Abstract code identifiers (function names, variables) for strict mode.
    """
    # Replace camelCase function names with generic terms
    result = content

    # Common patterns to abstract
    abstractions = [
        (r'(?<=[^a-zA-Z])handle[A-Z][a-zA-Z]*\b', '[HANDLER]'),
        (r'(?<=[^a-zA-Z])get[A-Z][a-zA-Z]*\b', '[GETTER]'),
        (r'(?<=[^a-zA-Z])set[A-Z][a-zA-Z]*\b', '[SETTER]'),
        (r'(?<=[^a-zA-Z])fetch[A-Z][a-zA-Z]*\b', '[FETCHER]'),
        (r'(?<=[^a-zA-Z])update[A-Z][a-zA-Z]*\b', '[UPDATER]'),
        (r'(?<=[^a-zA-Z])create[A-Z][a-zA-Z]*\b', '[CREATOR]'),
        (r'(?<=[^a-zA-Z])delete[A-Z][a-zA-Z]*\b', '[DELETER]'),
        (r'(?<=[^a-zA-Z])validate[A-Z][a-zA-Z]*\b', '[VALIDATOR]'),
        (r'(?<=[^a-zA-Z])process[A-Z][a-zA-Z]*\b', '[PROCESSOR]'),
    ]

    for pattern, replacement in abstractions:
        result = re.sub(pattern, replacement, result)

    return result


def abstract_error_message(error: str) -> str:
    """
    Abstract error message while preserving error type.
    """
    result = error

    # Remove line numbers
    result = re.sub(r':\d+:\d+', '', result)
    result = re.sub(r'at line \d+', '', result)
    result = re.sub(r'line \d+', '', result)

    # Remove specific property names
    result = re.sub(r"property '([^']+)'", "property '[PROP]'", result)
    result = re.sub(r'property "([^"]+)"', 'property "[PROP]"', result)

    # Remove file paths from stack traces
    result = re.sub(r'\s+at\s+[^\s]+\.(ts|js|tsx|jsx|py):\d+', '', result)

    # Remove function names in stack traces
    result = re.sub(r'at ([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', 'at [FUNCTION](', result)

    return result.strip()


def generate_content_hash(content: str) -> str:
    """
    Generate hash for content deduplication.
    Normalizes content before hashing.
    """
    # Normalize whitespace
    normalized = " ".join(content.lower().split())

    # Hash
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# =============================================================================
# SETTINGS MANAGEMENT
# =============================================================================

class PrivacyManager:
    """
    Manages user privacy settings and consent.
    """

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.settings_dir = self.project_dir / ".claude" / "popkit"
        self.settings_file = self.settings_dir / "privacy.json"
        self._settings: Optional[PrivacySettings] = None

    @property
    def settings(self) -> PrivacySettings:
        """Get current settings, loading if needed."""
        if self._settings is None:
            self._settings = self.load_settings()
        return self._settings

    def load_settings(self) -> PrivacySettings:
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                data = json.loads(self.settings_file.read_text())
                return PrivacySettings.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return PrivacySettings()

    def save_settings(self, settings: Optional[PrivacySettings] = None) -> None:
        """Save settings to file."""
        if settings:
            self._settings = settings

        if self._settings:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
            self.settings_file.write_text(
                json.dumps(self._settings.to_dict(), indent=2)
            )

    def give_consent(self) -> None:
        """Record user consent for data sharing."""
        self.settings.consent_given = True
        self.settings.consent_timestamp = datetime.now().isoformat()
        self.save_settings()

    def revoke_consent(self) -> None:
        """Revoke user consent and disable sharing."""
        self.settings.consent_given = False
        self.settings.sharing_enabled = False
        self.save_settings()

    def set_anonymization_level(self, level: str) -> None:
        """Set anonymization level."""
        if level in [l.value for l in AnonymizationLevel]:
            self.settings.anonymization_level = level
            self.save_settings()

    def add_excluded_project(self, project_name: str) -> None:
        """Add project to exclusion list."""
        if project_name not in self.settings.excluded_projects:
            self.settings.excluded_projects.append(project_name)
            self.save_settings()

    def remove_excluded_project(self, project_name: str) -> None:
        """Remove project from exclusion list."""
        if project_name in self.settings.excluded_projects:
            self.settings.excluded_projects.remove(project_name)
            self.save_settings()

    def add_excluded_pattern(self, pattern: str) -> None:
        """Add file pattern to exclusion list."""
        if pattern not in self.settings.excluded_patterns:
            self.settings.excluded_patterns.append(pattern)
            self.save_settings()

    def can_share(self) -> Tuple[bool, str]:
        """
        Check if sharing is allowed.

        Returns:
            Tuple of (can_share, reason)
        """
        if not self.settings.consent_given:
            return False, "User consent not given"

        if not self.settings.sharing_enabled:
            return False, "Sharing disabled in settings"

        # Check if current project is excluded
        project_name = self.project_dir.name
        if project_name in self.settings.excluded_projects:
            return False, f"Project '{project_name}' is excluded"

        return True, "OK"

    def should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from sharing."""
        import fnmatch

        for pattern in self.settings.excluded_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True

        # Always exclude these
        always_exclude = [
            "*.env*",
            "*secret*",
            "*credential*",
            "*.pem",
            "*.key",
            "*password*",
        ]

        for pattern in always_exclude:
            if fnmatch.fnmatch(file_path.lower(), pattern):
                return True

        return False

    def anonymize(
        self,
        content: str,
        file_path: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Anonymize content according to settings.

        Returns:
            Tuple of (anonymized_content, metadata)
        """
        # Check if file should be excluded
        if file_path and self.should_exclude_file(file_path):
            return "", {"excluded": True, "reason": "file_pattern_excluded"}

        # Get level
        level = AnonymizationLevel(self.settings.anonymization_level)

        # Anonymize
        anonymized, removed = anonymize_content(content, level)

        # Generate hash for dedup
        content_hash = generate_content_hash(anonymized)

        return anonymized, {
            "level": level.value,
            "removed_categories": removed,
            "content_hash": content_hash,
            "original_length": len(content),
            "anonymized_length": len(anonymized),
        }


# =============================================================================
# DATA DELETION (GDPR Right to be Forgotten)
# =============================================================================

def request_data_deletion(api_key: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Request deletion of all user data from PopKit Cloud.

    This is the GDPR "Right to be Forgotten" implementation.
    """
    import urllib.request
    import urllib.error

    base_url = base_url or "https://popkit-cloud-api.joseph-cannon.workers.dev/v1"
    url = f"{base_url}/privacy/delete-all"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    request = urllib.request.Request(
        url,
        data=json.dumps({"confirm": True}).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {"error": f"API error {e.code}: {error_body}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}


def export_user_data(api_key: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Export all user data from PopKit Cloud.

    This is the GDPR "Right to Data Portability" implementation.
    """
    import urllib.request
    import urllib.error

    base_url = base_url or "https://popkit-cloud-api.joseph-cannon.workers.dev/v1"
    url = f"{base_url}/privacy/export"

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {"error": f"API error {e.code}: {error_body}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing privacy module."""
    print("Privacy Module Test")
    print("=" * 50)

    # Test sensitive data detection
    print("\n[TEST] Sensitive data detection...")
    test_content = """
    const apiKey = "sk_live_abc123def456";
    const email = "user@example.com";
    const path = "/Users/john/projects/myapp/src/auth.ts";
    const db = "postgres://user:pass@localhost:5432/db";
    """

    detections = detect_sensitive_data(test_content)
    print(f"  Found {len(detections)} sensitive patterns:")
    for d in detections:
        print(f"    - {d['category']}: {d['match'][:30]}...")

    # Test anonymization
    print("\n[TEST] Anonymization levels...")

    for level in AnonymizationLevel:
        anonymized, removed = anonymize_content(test_content, level)
        print(f"\n  {level.value.upper()}:")
        print(f"    Removed: {removed}")
        print(f"    Result preview: {anonymized[:100]}...")

    # Test settings
    print("\n[TEST] Privacy settings...")
    manager = PrivacyManager()
    print(f"  Sharing enabled: {manager.settings.sharing_enabled}")
    print(f"  Consent given: {manager.settings.consent_given}")
    print(f"  Level: {manager.settings.anonymization_level}")

    can_share, reason = manager.can_share()
    print(f"  Can share: {can_share} ({reason})")

    # Test error abstraction
    print("\n[TEST] Error message abstraction...")
    error = "TypeError: Cannot read property 'token' of undefined at handleAuth (auth.ts:45:12)"
    abstracted = abstract_error_message(error)
    print(f"  Original: {error}")
    print(f"  Abstracted: {abstracted}")

    print("\n" + "=" * 50)
    print("[OK] Privacy module test completed!")


if __name__ == "__main__":
    main()
