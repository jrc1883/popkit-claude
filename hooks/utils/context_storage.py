#!/usr/bin/env python3
"""
Context Storage Backend Abstraction

Provides unified interface for storing skill context with multiple backends:
- File-based (default, free mode): JSON files in .popkit/context/
- Redis/Upstash (Power Mode): Real-time shared state

Part of Issue #188: Implement skill-to-skill context handoff system

Usage:
    storage = get_context_storage()  # Auto-detects backend
    storage.save_context("workflow_123", {"skill": "brainstorming", ...})
    ctx = storage.load_context("workflow_123")
"""

import json
import os
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


# =============================================================================
# Storage Interface
# =============================================================================

class ContextStorage(ABC):
    """Abstract base class for context storage backends."""

    @abstractmethod
    def save_context(self, workflow_id: str, context: Dict[str, Any]) -> bool:
        """Save context for a workflow. Returns success status."""
        pass

    @abstractmethod
    def load_context(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load context for a workflow. Returns None if not found."""
        pass

    @abstractmethod
    def delete_context(self, workflow_id: str) -> bool:
        """Delete context for a workflow. Returns success status."""
        pass

    @abstractmethod
    def list_workflows(self) -> List[str]:
        """List all active workflow IDs."""
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        pass

    # Activity Ledger (optional - for real-time awareness)
    def publish_activity(
        self,
        skill_name: str,
        event_type: str,
        data: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> Optional[str]:
        """Publish skill activity to activity ledger."""
        return None  # Default: no-op for backends that don't support it

    def get_recent_activity(
        self,
        count: int = 20,
        skill_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent activity from ledger."""
        return []  # Default: empty for backends that don't support it

    def get_active_skills(self) -> List[str]:
        """Get list of currently active skills."""
        return []  # Default: empty


# =============================================================================
# File-Based Storage (Free Mode)
# =============================================================================

class FileContextStorage(ContextStorage):
    """File-based storage using JSON files in .popkit/context/

    Default backend that works without any infrastructure.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or self._find_popkit_dir()

    def _find_popkit_dir(self) -> Path:
        """Find or create .popkit/context directory."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "package.json").exists():
                context_dir = parent / ".popkit" / "context"
                context_dir.mkdir(parents=True, exist_ok=True)
                return context_dir
        # Fallback
        context_dir = current / ".popkit" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        return context_dir

    def _workflow_file(self, workflow_id: str) -> Path:
        """Get file path for a workflow."""
        # Sanitize workflow_id for filesystem
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in workflow_id)
        return self.base_dir / f"{safe_id}.json"

    def save_context(self, workflow_id: str, context: Dict[str, Any]) -> bool:
        try:
            context["_updated_at"] = datetime.now().isoformat()
            context["_workflow_id"] = workflow_id
            with open(self._workflow_file(workflow_id), 'w') as f:
                json.dump(context, f, indent=2, default=str)
            return True
        except (IOError, TypeError) as e:
            return False

    def load_context(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._workflow_file(workflow_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def delete_context(self, workflow_id: str) -> bool:
        file_path = self._workflow_file(workflow_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_workflows(self) -> List[str]:
        workflows = []
        for f in self.base_dir.glob("*.json"):
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                    if wf_id := data.get("_workflow_id"):
                        workflows.append(wf_id)
            except (json.JSONDecodeError, IOError):
                continue
        return workflows

    def get_backend_name(self) -> str:
        return "file"

    # File-based activity tracking (limited but works without infrastructure)
    def _get_activity_file(self) -> Path:
        """Get activity log file path."""
        return self.base_dir / "activity.jsonl"

    def publish_activity(
        self,
        skill_name: str,
        event_type: str,
        data: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> Optional[str]:
        """Append activity to JSONL file."""
        activity_file = self._get_activity_file()
        entry_id = f"{int(datetime.now().timestamp() * 1000)}-0"

        entry = {
            "id": entry_id,
            "skill": skill_name,
            "event": event_type,
            "workflow": workflow_id or "none",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        try:
            with open(activity_file, 'a') as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return entry_id
        except IOError:
            return None

    def get_recent_activity(
        self,
        count: int = 20,
        skill_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Read recent activity from JSONL file."""
        activity_file = self._get_activity_file()

        if not activity_file.exists():
            return []

        try:
            with open(activity_file, 'r') as f:
                lines = f.readlines()

            # Get last N lines (newest)
            activities = []
            for line in reversed(lines[-100:]):  # Cap at 100 for performance
                try:
                    entry = json.loads(line.strip())
                    if skill_filter and entry.get("skill") != skill_filter:
                        continue
                    activities.append(entry)
                    if len(activities) >= count:
                        break
                except json.JSONDecodeError:
                    continue

            return activities
        except IOError:
            return []

    def get_active_skills(self) -> List[str]:
        """Get active skills from activity file."""
        activities = self.get_recent_activity(count=50)

        skill_states: Dict[str, str] = {}
        for activity in reversed(activities):
            skill = activity.get("skill", "unknown")
            event = activity.get("event", "unknown")
            skill_states[skill] = event

        return [
            skill for skill, event in skill_states.items()
            if event in ("start", "progress")
        ]


# =============================================================================
# Upstash Redis Storage (Power Mode / Premium)
# =============================================================================

class UpstashContextStorage(ContextStorage):
    """Upstash Redis storage for Power Mode and premium features.

    Uses Upstash REST API - no local Redis required.
    Requires UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN env vars.

    Implements:
    - Hash storage for workflow state (fast key-value)
    - Redis Streams for activity ledger (real-time log of skill executions)
    """

    KEY_PREFIX = "popkit:workflow:"
    STREAM_KEY = "popkit:activity"  # Central activity ledger
    TTL_SECONDS = 86400 * 7  # 7 days

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = url or os.environ.get("UPSTASH_REDIS_REST_URL")
        self.token = token or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

        if not self.url or not self.token:
            raise ValueError(
                "Upstash credentials required. Set UPSTASH_REDIS_REST_URL and "
                "UPSTASH_REDIS_REST_TOKEN environment variables."
            )

    def _make_key(self, workflow_id: str) -> str:
        """Generate Redis key for workflow."""
        return f"{self.KEY_PREFIX}{workflow_id}"

    def _redis_command(self, command: List[str]) -> Any:
        """Execute Redis command via Upstash REST API."""
        url = f"{self.url}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        request = Request(url, method="POST")
        for key, value in headers.items():
            request.add_header(key, value)

        body = json.dumps(command).encode('utf-8')
        try:
            with urlopen(request, body, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("result")
        except URLError as e:
            return None

    def save_context(self, workflow_id: str, context: Dict[str, Any]) -> bool:
        context["_updated_at"] = datetime.now().isoformat()
        context["_workflow_id"] = workflow_id

        key = self._make_key(workflow_id)
        value = json.dumps(context, default=str)

        # SET with TTL
        result = self._redis_command(["SET", key, value, "EX", str(self.TTL_SECONDS)])
        return result == "OK"

    def load_context(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(workflow_id)
        result = self._redis_command(["GET", key])

        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return None
        return None

    def delete_context(self, workflow_id: str) -> bool:
        key = self._make_key(workflow_id)
        result = self._redis_command(["DEL", key])
        return result == 1

    def list_workflows(self) -> List[str]:
        """List workflow IDs using SCAN."""
        workflows = []
        cursor = "0"
        pattern = f"{self.KEY_PREFIX}*"

        while True:
            result = self._redis_command(["SCAN", cursor, "MATCH", pattern, "COUNT", "100"])
            if not result or not isinstance(result, list) or len(result) < 2:
                break

            cursor = result[0]
            keys = result[1]

            for key in keys:
                wf_id = key.replace(self.KEY_PREFIX, "")
                workflows.append(wf_id)

            if cursor == "0":
                break

        return workflows

    def get_backend_name(self) -> str:
        return "upstash"

    # =========================================================================
    # Redis Streams - Activity Ledger (Issue #188, #189)
    # =========================================================================

    def publish_activity(
        self,
        skill_name: str,
        event_type: str,
        data: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> Optional[str]:
        """Publish skill activity to the central activity stream.

        Uses XADD to append to the activity ledger. All skills write here,
        creating a unified view of what's happening across the system.

        Args:
            skill_name: Name of the skill publishing
            event_type: "start", "progress", "complete", "error"
            data: Event-specific data
            workflow_id: Optional workflow context

        Returns:
            Stream entry ID if successful, None otherwise
        """
        entry = {
            "skill": skill_name,
            "event": event_type,
            "workflow": workflow_id or "none",
            "timestamp": datetime.now().isoformat(),
            "data": json.dumps(data, default=str)
        }

        # XADD with auto-generated ID (*)
        result = self._redis_command([
            "XADD", self.STREAM_KEY, "*",
            "skill", entry["skill"],
            "event", entry["event"],
            "workflow", entry["workflow"],
            "timestamp", entry["timestamp"],
            "data", entry["data"]
        ])

        return result if isinstance(result, str) else None

    def get_recent_activity(
        self,
        count: int = 20,
        skill_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent activity from the stream.

        Uses XREVRANGE to get latest entries (newest first).

        Args:
            count: Number of entries to retrieve
            skill_filter: Optional skill name to filter by

        Returns:
            List of activity entries
        """
        # XREVRANGE stream + - COUNT n (newest first)
        result = self._redis_command([
            "XREVRANGE", self.STREAM_KEY, "+", "-", "COUNT", str(count)
        ])

        if not result or not isinstance(result, list):
            return []

        activities = []
        for entry in result:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            entry_id = entry[0]
            fields = entry[1]

            # Convert flat list to dict
            activity = {"id": entry_id}
            for i in range(0, len(fields), 2):
                key = fields[i]
                value = fields[i + 1]
                if key == "data":
                    try:
                        activity[key] = json.loads(value)
                    except json.JSONDecodeError:
                        activity[key] = value
                else:
                    activity[key] = value

            # Apply filter if specified
            if skill_filter and activity.get("skill") != skill_filter:
                continue

            activities.append(activity)

        return activities

    def get_active_skills(self) -> List[str]:
        """Get list of skills that have been active recently.

        Returns skills with "start" but no "complete"/"error" in recent activity.
        """
        activities = self.get_recent_activity(count=50)

        # Track skill states
        skill_states: Dict[str, str] = {}  # skill -> latest event

        # Process oldest to newest (reverse since we got newest first)
        for activity in reversed(activities):
            skill = activity.get("skill", "unknown")
            event = activity.get("event", "unknown")
            skill_states[skill] = event

        # Return skills still in "start" or "progress" state
        return [
            skill for skill, event in skill_states.items()
            if event in ("start", "progress")
        ]

    def trim_activity_stream(self, max_entries: int = 1000) -> int:
        """Trim the activity stream to prevent unbounded growth.

        Uses XTRIM with MAXLEN.

        Returns:
            Number of entries removed
        """
        result = self._redis_command([
            "XTRIM", self.STREAM_KEY, "MAXLEN", "~", str(max_entries)
        ])
        return result if isinstance(result, int) else 0


# =============================================================================
# PopKit Cloud API Storage (Future)
# =============================================================================

class CloudAPIContextStorage(ContextStorage):
    """PopKit Cloud API storage via our Workers endpoint.

    Uses the authenticated PopKit Cloud API for team-shared workflows.
    Requires POPKIT_API_KEY env var.
    """

    API_BASE = "https://api.popkit.dev/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("POPKIT_API_KEY")

        if not self.api_key:
            raise ValueError("POPKIT_API_KEY environment variable required.")

    def _api_request(self, method: str, path: str, body: Optional[Dict] = None) -> Any:
        """Make authenticated API request."""
        url = f"{self.API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        request = Request(url, method=method)
        for key, value in headers.items():
            request.add_header(key, value)

        data = json.dumps(body).encode('utf-8') if body else None
        try:
            with urlopen(request, data, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except URLError:
            return None

    def save_context(self, workflow_id: str, context: Dict[str, Any]) -> bool:
        result = self._api_request("PUT", f"/workflows/{workflow_id}", context)
        return result is not None and result.get("success", False)

    def load_context(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        result = self._api_request("GET", f"/workflows/{workflow_id}")
        return result.get("data") if result else None

    def delete_context(self, workflow_id: str) -> bool:
        result = self._api_request("DELETE", f"/workflows/{workflow_id}")
        return result is not None and result.get("success", False)

    def list_workflows(self) -> List[str]:
        result = self._api_request("GET", "/workflows")
        return result.get("workflows", []) if result else []

    def get_backend_name(self) -> str:
        return "cloud"


# =============================================================================
# Backend Selection
# =============================================================================

def get_context_storage(prefer: Optional[str] = None) -> ContextStorage:
    """Get appropriate context storage backend.

    Auto-detection order:
    1. If prefer is specified, try that backend
    2. If POPKIT_API_KEY is set, use Cloud API
    3. If Upstash env vars are set, use Upstash
    4. Fall back to file-based storage

    Args:
        prefer: Optional preferred backend ("file", "upstash", "cloud")

    Returns:
        Appropriate ContextStorage implementation
    """
    # Explicit preference
    if prefer == "file":
        return FileContextStorage()
    elif prefer == "upstash":
        try:
            return UpstashContextStorage()
        except ValueError:
            pass
    elif prefer == "cloud":
        try:
            return CloudAPIContextStorage()
        except ValueError:
            pass

    # Auto-detect
    # 1. Check for PopKit Cloud API
    if os.environ.get("POPKIT_API_KEY"):
        try:
            return CloudAPIContextStorage()
        except ValueError:
            pass

    # 2. Check for Upstash (Power Mode)
    if os.environ.get("UPSTASH_REDIS_REST_URL") and os.environ.get("UPSTASH_REDIS_REST_TOKEN"):
        try:
            return UpstashContextStorage()
        except ValueError:
            pass

    # 3. Default to file-based
    return FileContextStorage()


def is_power_mode_available() -> bool:
    """Check if Power Mode (Upstash) storage is available."""
    return bool(
        os.environ.get("UPSTASH_REDIS_REST_URL") and
        os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    )


def is_cloud_available() -> bool:
    """Check if PopKit Cloud storage is available."""
    return bool(os.environ.get("POPKIT_API_KEY"))


def get_storage_status() -> Dict[str, Any]:
    """Get status of all storage backends."""
    return {
        "current": get_context_storage().get_backend_name(),
        "file": True,  # Always available
        "upstash": is_power_mode_available(),
        "cloud": is_cloud_available()
    }


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("Testing context_storage.py...")

    # Test file storage
    storage = FileContextStorage()
    print(f"Backend: {storage.get_backend_name()}")

    workflow_id = "test_workflow_123"

    # Save
    success = storage.save_context(workflow_id, {
        "skill": "pop-brainstorming",
        "output": {"topic": "auth"},
        "artifacts": ["design.md"]
    })
    assert success, "Save failed"
    print("Save: OK")

    # Load
    ctx = storage.load_context(workflow_id)
    assert ctx is not None
    assert ctx["skill"] == "pop-brainstorming"
    print(f"Load: OK - {ctx['skill']}")

    # List
    workflows = storage.list_workflows()
    assert workflow_id in workflows
    print(f"List: OK - found {len(workflows)} workflows")

    # Delete
    success = storage.delete_context(workflow_id)
    assert success
    assert storage.load_context(workflow_id) is None
    print("Delete: OK")

    # Test auto-detection
    auto_storage = get_context_storage()
    print(f"\nAuto-detected backend: {auto_storage.get_backend_name()}")

    # Status
    status = get_storage_status()
    print(f"Storage status: {status}")

    print("\nAll tests passed!")
