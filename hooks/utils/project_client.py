#!/usr/bin/env python3
"""
Project Registration Client

Client for PopKit Cloud project registry API.
Enables cross-project observability and multi-project dashboard.

Part of Issue #93 (Multi-Project Dashboard).
"""

import os
import json
import hashlib
import platform
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import urllib.request
import urllib.error


# =============================================================================
# CONFIGURATION
# =============================================================================

POPKIT_API_URL = os.environ.get(
    "POPKIT_API_URL",
    "https://popkit-cloud-api.joseph-cannon.workers.dev"
)
POPKIT_VERSION = "0.9.10"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProjectInfo:
    """Local project information for registration."""
    project_id: str
    name: str
    path_hint: str
    platform: str = field(default_factory=lambda: platform.system().lower())
    popkit_version: str = POPKIT_VERSION
    health_score: int = 0


@dataclass
class ProjectRegistration:
    """Response from project registration."""
    status: str
    project_id: str
    session_count: int


@dataclass
class ProjectActivity:
    """Activity update for a project."""
    tool_name: Optional[str] = None
    agent_name: Optional[str] = None
    command_name: Optional[str] = None
    health_score: Optional[int] = None
    power_mode_active: bool = False
    power_mode_agents: int = 0


@dataclass
class ProjectSummary:
    """Summary statistics across all projects."""
    total_projects: int
    active_projects_24h: int
    total_tool_calls: int
    total_sessions: int
    avg_health_score: int
    power_mode_active: int


# =============================================================================
# PROJECT CLIENT
# =============================================================================

class ProjectClient:
    """
    Client for PopKit Cloud project registry.

    Features:
    - Project registration on session start
    - Activity tracking for tool calls
    - Cross-project observability
    - Multi-project dashboard support
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = POPKIT_API_URL
    ):
        """
        Initialize project client.

        Args:
            api_key: PopKit API key (defaults to POPKIT_API_KEY env var)
            api_url: PopKit Cloud API URL
        """
        self.api_key = api_key or os.environ.get("POPKIT_API_KEY")
        self.api_url = api_url.rstrip("/")
        self._current_project_id: Optional[str] = None

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def register_project(
        self,
        project_path: Optional[str] = None,
        name: Optional[str] = None,
        health_score: int = 0
    ) -> Optional[ProjectRegistration]:
        """
        Register a project with PopKit Cloud.

        Called at session start to track project usage.

        Args:
            project_path: Path to project root (defaults to cwd)
            name: Project name (defaults to directory name or package.json name)
            health_score: Initial health score from morning routine

        Returns:
            ProjectRegistration or None if registration failed
        """
        if not self.api_key:
            return None

        project_path = project_path or os.getcwd()
        project_info = self._get_project_info(project_path, name, health_score)

        try:
            response = self._post("/v1/projects/register", {
                "project_id": project_info.project_id,
                "name": project_info.name,
                "path_hint": project_info.path_hint,
                "health_score": project_info.health_score,
                "popkit_version": project_info.popkit_version,
                "platform": project_info.platform,
            })

            self._current_project_id = project_info.project_id

            return ProjectRegistration(
                status=response.get("status", "unknown"),
                project_id=response.get("project_id", project_info.project_id),
                session_count=response.get("session_count", 0)
            )

        except Exception:
            return None

    def record_activity(
        self,
        activity: ProjectActivity,
        project_id: Optional[str] = None
    ) -> bool:
        """
        Record activity for a project.

        Called during tool use to track activity.

        Args:
            activity: Activity update
            project_id: Project ID (defaults to current registered project)

        Returns:
            True if activity was recorded
        """
        if not self.api_key:
            return False

        project_id = project_id or self._current_project_id
        if not project_id:
            return False

        body: Dict[str, Any] = {}

        if activity.tool_name:
            body["tool_name"] = activity.tool_name
        if activity.agent_name:
            body["agent_name"] = activity.agent_name
        if activity.command_name:
            body["command_name"] = activity.command_name
        if activity.health_score is not None:
            body["health_score"] = activity.health_score
        if activity.power_mode_active:
            body["power_mode"] = {
                "active": activity.power_mode_active,
                "agent_count": activity.power_mode_agents
            }

        try:
            self._post(f"/v1/projects/{project_id}/activity", body)
            return True
        except Exception:
            return False

    def list_projects(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all registered projects.

        Args:
            active_only: Only return projects active in last 24h

        Returns:
            List of project info dicts
        """
        if not self.api_key:
            return []

        try:
            params = "?active_only=true" if active_only else ""
            response = self._get(f"/v1/projects{params}")
            return response.get("projects", [])
        except Exception:
            return []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific project.

        Args:
            project_id: Project ID

        Returns:
            Project info dict or None
        """
        if not self.api_key:
            return None

        try:
            return self._get(f"/v1/projects/{project_id}")
        except Exception:
            return None

    def get_summary(self) -> Optional[ProjectSummary]:
        """
        Get summary statistics across all projects.

        Returns:
            ProjectSummary or None if unavailable
        """
        if not self.api_key:
            return None

        try:
            response = self._get("/v1/projects/summary")
            return ProjectSummary(
                total_projects=response.get("total_projects", 0),
                active_projects_24h=response.get("active_projects_24h", 0),
                total_tool_calls=response.get("total_tool_calls", 0),
                total_sessions=response.get("total_sessions", 0),
                avg_health_score=response.get("avg_health_score", 0),
                power_mode_active=response.get("power_mode_active", 0),
            )
        except Exception:
            return None

    def unregister_project(self, project_id: str) -> bool:
        """
        Unregister a project.

        Args:
            project_id: Project ID to unregister

        Returns:
            True if unregistered successfully
        """
        if not self.api_key:
            return False

        try:
            self._delete(f"/v1/projects/{project_id}")
            if self._current_project_id == project_id:
                self._current_project_id = None
            return True
        except Exception:
            return False

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @property
    def current_project_id(self) -> Optional[str]:
        """Get the current registered project ID."""
        return self._current_project_id

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _get_project_info(
        self,
        project_path: str,
        name: Optional[str],
        health_score: int
    ) -> ProjectInfo:
        """Extract project information from path."""
        path = Path(project_path).resolve()

        # Generate project ID from absolute path
        project_id = hashlib.sha256(str(path).encode()).hexdigest()[:16]

        # Get project name
        if not name:
            # Try package.json
            package_json = path / "package.json"
            if package_json.exists():
                try:
                    with open(package_json) as f:
                        pkg = json.load(f)
                        name = pkg.get("name", "")
                except Exception:
                    pass

            # Fallback to directory name
            if not name:
                name = path.name

        # Create anonymized path hint (last 2 segments)
        path_parts = path.parts
        if len(path_parts) >= 2:
            path_hint = f".../{'/'.join(path_parts[-2:])}"
        else:
            path_hint = f".../{path.name}"

        return ProjectInfo(
            project_id=project_id,
            name=name,
            path_hint=path_hint,
            health_score=health_score
        )

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to API."""
        return self._request("GET", endpoint)

    def _post(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to API."""
        return self._request("POST", endpoint, body)

    def _delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request to API."""
        return self._request("DELETE", endpoint)

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.api_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-PopKit-Version": POPKIT_VERSION,
        }

        data = json.dumps(body).encode("utf-8") if body else None

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"API error {e.code}: {e.reason}\n{body_text}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_client: Optional[ProjectClient] = None


def get_client() -> ProjectClient:
    """Get or create the singleton project client."""
    global _client
    if _client is None:
        _client = ProjectClient()
    return _client


def register_project(
    project_path: Optional[str] = None,
    name: Optional[str] = None,
    health_score: int = 0
) -> Optional[ProjectRegistration]:
    """Convenience function to register a project."""
    return get_client().register_project(project_path, name, health_score)


def record_activity(activity: ProjectActivity) -> bool:
    """Convenience function to record activity."""
    return get_client().record_activity(activity)


def list_projects(active_only: bool = False) -> List[Dict[str, Any]]:
    """Convenience function to list projects."""
    return get_client().list_projects(active_only)


def get_summary() -> Optional[ProjectSummary]:
    """Convenience function to get summary."""
    return get_client().get_summary()


def is_available() -> bool:
    """Check if project tracking is available."""
    return get_client().is_available


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Project Client Test")
    print("=" * 40)

    client = ProjectClient()

    if not client.is_available:
        print("ERROR: POPKIT_API_KEY not set")
        print("Set: export POPKIT_API_KEY=your-key-here")
        sys.exit(1)

    print(f"API Key: {client.api_key[:8]}...{client.api_key[-4:]}")
    print(f"API URL: {client.api_url}")

    # Test project registration
    print("\nTesting project registration...")
    result = client.register_project()
    if result:
        print(f"Status: {result.status}")
        print(f"Project ID: {result.project_id}")
        print(f"Session Count: {result.session_count}")
    else:
        print("Registration failed")

    # Test activity recording
    print("\nTesting activity recording...")
    success = client.record_activity(ProjectActivity(
        tool_name="Read",
        agent_name="code-reviewer"
    ))
    print(f"Activity recorded: {success}")

    # Test listing projects
    print("\nTesting project listing...")
    projects = client.list_projects()
    print(f"Found {len(projects)} projects")
    for proj in projects[:3]:
        print(f"  - {proj.get('name', 'Unknown')}: {proj.get('last_active', 'never')}")

    # Test summary
    print("\nTesting summary...")
    summary = client.get_summary()
    if summary:
        print(f"Total projects: {summary.total_projects}")
        print(f"Active (24h): {summary.active_projects_24h}")
        print(f"Total tool calls: {summary.total_tool_calls}")
        print(f"Avg health score: {summary.avg_health_score}")
    else:
        print("Summary unavailable")

    print("\nAll tests completed!")
