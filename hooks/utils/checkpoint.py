#!/usr/bin/env python3
"""
Checkpoint/Restore Utility

Part of Issue #94 (Long Horizon Agent Patterns Integration)

Saves and restores session state for long-running sessions.
Enables recovery from crashes and continuation across sessions.

Based on patterns from Anthropic's Long Horizon Coding Agent Demo.
"""

import os
import json
import subprocess
import shutil
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

CHECKPOINT_DIR = Path.home() / ".claude" / "popkit" / "checkpoints"
MAX_CHECKPOINTS_PER_SESSION = 10  # Keep last N checkpoints


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint."""
    checkpoint_id: str
    session_id: str
    created_at: str
    description: str
    tool_calls: int
    files_modified: List[str]
    git_ref: Optional[str] = None  # Git commit/stash reference
    is_auto: bool = False  # Auto-created vs manual


@dataclass
class CheckpointData:
    """Complete checkpoint data."""
    metadata: CheckpointMetadata
    session_state: Dict[str, Any]
    file_snapshots: Dict[str, str]  # file_path -> content hash
    context: Dict[str, Any]  # Agent context/memory


@dataclass
class RestoreResult:
    """Result of restoring a checkpoint."""
    success: bool
    checkpoint_id: str
    restored_files: List[str]
    warnings: List[str]
    error: Optional[str] = None


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """
    Manages checkpoints for long-running sessions.

    Features:
    - Manual and automatic checkpoints
    - Git-based file snapshots
    - Session state persistence
    - Rollback support
    """

    def __init__(self, session_id: str, project_path: Optional[str] = None):
        """
        Initialize checkpoint manager.

        Args:
            session_id: Session identifier
            project_path: Project root path (for git operations)
        """
        self.session_id = session_id
        self.project_path = project_path or os.getcwd()
        self.checkpoint_dir = CHECKPOINT_DIR / session_id
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        description: str,
        session_state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        is_auto: bool = False
    ) -> CheckpointMetadata:
        """
        Create a new checkpoint.

        Args:
            description: Human-readable checkpoint description
            session_state: Session state to save
            context: Agent context/memory
            is_auto: Whether this is an automatic checkpoint

        Returns:
            CheckpointMetadata for the created checkpoint
        """
        checkpoint_id = self._generate_checkpoint_id()

        # Get modified files from git
        files_modified = self._get_modified_files()

        # Create git stash for file backup
        git_ref = self._create_git_snapshot(description) if files_modified else None

        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            session_id=self.session_id,
            created_at=datetime.now().isoformat(),
            description=description,
            tool_calls=session_state.get("tool_calls", 0) if session_state else 0,
            files_modified=files_modified,
            git_ref=git_ref,
            is_auto=is_auto
        )

        # Build complete checkpoint
        checkpoint = CheckpointData(
            metadata=metadata,
            session_state=session_state or {},
            file_snapshots=self._snapshot_files(files_modified),
            context=context or {}
        )

        # Save to disk
        self._save_checkpoint(checkpoint)

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints()

        return metadata

    def _generate_checkpoint_id(self) -> str:
        """Generate unique checkpoint ID."""
        existing = self.list_checkpoints()
        next_num = len(existing) + 1
        timestamp = datetime.now().strftime("%H%M%S")
        return f"checkpoint-{next_num:03d}-{timestamp}"

    def _get_modified_files(self) -> List[str]:
        """Get list of modified files from git."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        # Format: XY filename
                        file_path = line[3:].strip()
                        # Handle renamed files
                        if " -> " in file_path:
                            file_path = file_path.split(" -> ")[1]
                        files.append(file_path)
                return files
        except Exception:
            pass
        return []

    def _create_git_snapshot(self, description: str) -> Optional[str]:
        """Create git stash for backup."""
        try:
            # Create stash with message
            result = subprocess.run(
                ["git", "stash", "push", "-m", f"[PopKit Checkpoint] {description}"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and "No local changes" not in result.stdout:
                # Get stash reference
                list_result = subprocess.run(
                    ["git", "stash", "list", "-1"],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if list_result.returncode == 0 and list_result.stdout.strip():
                    stash_ref = list_result.stdout.strip().split(":")[0]

                    # Immediately restore the changes (we just want the stash as backup)
                    subprocess.run(
                        ["git", "stash", "pop"],
                        cwd=self.project_path,
                        capture_output=True,
                        timeout=30
                    )

                    return stash_ref

        except Exception:
            pass
        return None

    def _snapshot_files(self, files: List[str]) -> Dict[str, str]:
        """Create content hashes for files."""
        import hashlib
        snapshots = {}

        for file_path in files:
            full_path = Path(self.project_path) / file_path
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_bytes()
                    snapshots[file_path] = hashlib.sha256(content).hexdigest()[:12]
                except Exception:
                    pass

        return snapshots

    def _save_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Save checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.metadata.checkpoint_id}.json"

        with open(checkpoint_file, "w") as f:
            json.dump({
                "metadata": asdict(checkpoint.metadata),
                "session_state": checkpoint.session_state,
                "file_snapshots": checkpoint.file_snapshots,
                "context": checkpoint.context
            }, f, indent=2)

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints beyond limit."""
        checkpoints = self.list_checkpoints()

        if len(checkpoints) > MAX_CHECKPOINTS_PER_SESSION:
            # Keep only recent checkpoints
            to_remove = checkpoints[MAX_CHECKPOINTS_PER_SESSION:]
            for cp in to_remove:
                checkpoint_file = self.checkpoint_dir / f"{cp.checkpoint_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()

    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """
        List all checkpoints for this session.

        Returns:
            List of CheckpointMetadata, newest first
        """
        checkpoints = []

        for file_path in self.checkpoint_dir.glob("checkpoint-*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    checkpoints.append(CheckpointMetadata(**data["metadata"]))
            except Exception:
                pass

        # Sort by creation time, newest first
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)

        return checkpoints

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """
        Get a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to retrieve

        Returns:
            CheckpointData or None if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)
                return CheckpointData(
                    metadata=CheckpointMetadata(**data["metadata"]),
                    session_state=data["session_state"],
                    file_snapshots=data["file_snapshots"],
                    context=data["context"]
                )
        except Exception:
            return None

    def restore(self, checkpoint_id: str) -> RestoreResult:
        """
        Restore to a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to restore

        Returns:
            RestoreResult with details
        """
        checkpoint = self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            return RestoreResult(
                success=False,
                checkpoint_id=checkpoint_id,
                restored_files=[],
                warnings=[],
                error=f"Checkpoint not found: {checkpoint_id}"
            )

        warnings = []
        restored_files = []

        # Check if we have uncommitted changes
        current_modified = self._get_modified_files()
        if current_modified:
            warnings.append(f"Current uncommitted changes in {len(current_modified)} files")

        # Try to restore from git stash if available
        if checkpoint.metadata.git_ref:
            try:
                # First, stash current changes
                if current_modified:
                    subprocess.run(
                        ["git", "stash", "push", "-m", "[PopKit] Pre-restore backup"],
                        cwd=self.project_path,
                        capture_output=True,
                        timeout=30
                    )

                # Apply the checkpoint stash
                result = subprocess.run(
                    ["git", "stash", "apply", checkpoint.metadata.git_ref],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    restored_files = checkpoint.metadata.files_modified
                else:
                    warnings.append(f"Could not restore from git stash: {result.stderr}")

            except Exception as e:
                warnings.append(f"Git restore failed: {e}")

        return RestoreResult(
            success=True,
            checkpoint_id=checkpoint_id,
            restored_files=restored_files,
            warnings=warnings
        )

    def get_latest(self) -> Optional[CheckpointData]:
        """Get the most recent checkpoint."""
        checkpoints = self.list_checkpoints()
        if checkpoints:
            return self.get_checkpoint(checkpoints[0].checkpoint_id)
        return None

    def auto_checkpoint(
        self,
        trigger: str,
        session_state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[CheckpointMetadata]:
        """
        Create automatic checkpoint based on trigger.

        Triggers:
        - "build_failure": After build command fails
        - "test_failure": After tests fail
        - "stuck_detected": When stuck detection fires
        - "phase_complete": After completing a phase
        - "many_changes": After many file changes

        Args:
            trigger: Trigger type
            session_state: Session state
            context: Agent context

        Returns:
            CheckpointMetadata or None if skipped
        """
        description_map = {
            "build_failure": "Auto-checkpoint after build failure",
            "test_failure": "Auto-checkpoint after test failure",
            "stuck_detected": "Auto-checkpoint on stuck detection",
            "phase_complete": "Auto-checkpoint after phase completion",
            "many_changes": "Auto-checkpoint after significant changes"
        }

        description = description_map.get(trigger, f"Auto-checkpoint: {trigger}")

        return self.create(
            description=description,
            session_state=session_state,
            context=context,
            is_auto=True
        )


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_current_manager: Optional[CheckpointManager] = None


def get_manager(session_id: Optional[str] = None) -> CheckpointManager:
    """Get or create checkpoint manager."""
    global _current_manager
    if _current_manager is None or (session_id and _current_manager.session_id != session_id):
        from heartbeat import get_monitor
        session_id = session_id or get_monitor().session_id
        _current_manager = CheckpointManager(session_id)
    return _current_manager


def create_checkpoint(description: str, **kwargs) -> CheckpointMetadata:
    """Convenience function to create checkpoint."""
    return get_manager().create(description, **kwargs)


def restore_checkpoint(checkpoint_id: str) -> RestoreResult:
    """Convenience function to restore checkpoint."""
    return get_manager().restore(checkpoint_id)


def list_checkpoints() -> List[CheckpointMetadata]:
    """Convenience function to list checkpoints."""
    return get_manager().list_checkpoints()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Checkpoint manager")
    parser.add_argument("command", choices=["create", "list", "restore", "show"], default="list", nargs="?")
    parser.add_argument("--session", "-s", help="Session ID")
    parser.add_argument("--checkpoint", "-c", help="Checkpoint ID (for restore/show)")
    parser.add_argument("--description", "-d", help="Checkpoint description")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")

    args = parser.parse_args()

    # Get or create session
    session_id = args.session
    if not session_id:
        from heartbeat import get_monitor
        session_id = get_monitor().session_id

    manager = CheckpointManager(session_id)

    if args.command == "list":
        checkpoints = manager.list_checkpoints()
        if args.json:
            print(json.dumps([asdict(c) for c in checkpoints], indent=2))
        else:
            print(f"Checkpoints for session {session_id}:")
            for cp in checkpoints:
                auto = " [auto]" if cp.is_auto else ""
                print(f"  {cp.checkpoint_id}{auto}")
                print(f"    {cp.description}")
                print(f"    Created: {cp.created_at}")
                print(f"    Files: {len(cp.files_modified)}")
                print()

    elif args.command == "create":
        description = args.description or "Manual checkpoint"
        metadata = manager.create(description)
        print(f"Created checkpoint: {metadata.checkpoint_id}")
        print(f"  Files: {len(metadata.files_modified)}")
        if metadata.git_ref:
            print(f"  Git ref: {metadata.git_ref}")

    elif args.command == "restore":
        if not args.checkpoint:
            print("Error: --checkpoint required for restore")
            exit(1)
        result = manager.restore(args.checkpoint)
        if result.success:
            print(f"Restored checkpoint: {result.checkpoint_id}")
            print(f"  Files restored: {len(result.restored_files)}")
            if result.warnings:
                print("  Warnings:")
                for w in result.warnings:
                    print(f"    - {w}")
        else:
            print(f"Restore failed: {result.error}")

    elif args.command == "show":
        if not args.checkpoint:
            # Show latest
            checkpoint = manager.get_latest()
        else:
            checkpoint = manager.get_checkpoint(args.checkpoint)

        if checkpoint:
            if args.json:
                print(json.dumps({
                    "metadata": asdict(checkpoint.metadata),
                    "session_state": checkpoint.session_state,
                    "file_snapshots": checkpoint.file_snapshots
                }, indent=2))
            else:
                print(f"Checkpoint: {checkpoint.metadata.checkpoint_id}")
                print(f"  Description: {checkpoint.metadata.description}")
                print(f"  Created: {checkpoint.metadata.created_at}")
                print(f"  Tool calls: {checkpoint.metadata.tool_calls}")
                print(f"  Files modified: {checkpoint.metadata.files_modified}")
                if checkpoint.metadata.git_ref:
                    print(f"  Git ref: {checkpoint.metadata.git_ref}")
        else:
            print("Checkpoint not found")
