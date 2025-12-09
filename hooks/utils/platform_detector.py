#!/usr/bin/env python3
"""
Platform Detector for PopKit Command Learning

Part of Issue #89 - Platform-Aware Command Learning

Detects the operating system, shell type, and available capabilities
to enable intelligent command translation and cross-platform support.
"""

import os
import sys
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum


class OSType(Enum):
    """Operating system types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class ShellType(Enum):
    """Shell types"""
    CMD = "cmd"
    POWERSHELL = "powershell"
    POWERSHELL_CORE = "pwsh"
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    SH = "sh"
    GIT_BASH = "git-bash"
    WSL = "wsl"
    UNKNOWN = "unknown"


@dataclass
class ShellCapabilities:
    """Capabilities of the detected shell"""
    unix_commands: bool = False  # Can run cp, rm, ls, etc.
    powershell_commands: bool = False  # Can run Copy-Item, Remove-Item, etc.
    cmd_commands: bool = False  # Can run xcopy, del, dir, etc.
    pipe_support: bool = True
    redirection_support: bool = True
    glob_support: bool = False
    environment_vars: bool = True
    heredoc_support: bool = False
    background_jobs: bool = False


@dataclass
class PlatformInfo:
    """Complete platform information"""
    os_type: OSType
    os_version: str
    shell_type: ShellType
    shell_path: str
    shell_version: str
    capabilities: ShellCapabilities
    available_commands: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "os_type": self.os_type.value,
            "os_version": self.os_version,
            "shell_type": self.shell_type.value,
            "shell_path": self.shell_path,
            "shell_version": self.shell_version,
            "capabilities": {
                "unix_commands": self.capabilities.unix_commands,
                "powershell_commands": self.capabilities.powershell_commands,
                "cmd_commands": self.capabilities.cmd_commands,
                "pipe_support": self.capabilities.pipe_support,
                "redirection_support": self.capabilities.redirection_support,
                "glob_support": self.capabilities.glob_support,
                "environment_vars": self.capabilities.environment_vars,
                "heredoc_support": self.capabilities.heredoc_support,
                "background_jobs": self.capabilities.background_jobs,
            },
            "available_commands": self.available_commands,
        }


class PlatformDetector:
    """Detects platform, shell, and capabilities"""

    # Cache the detection result
    _cached_info: Optional[PlatformInfo] = None

    @classmethod
    def detect(cls, force_refresh: bool = False) -> PlatformInfo:
        """
        Detect the current platform and shell.

        Args:
            force_refresh: If True, re-detect even if cached

        Returns:
            PlatformInfo with all detected information
        """
        if cls._cached_info is not None and not force_refresh:
            return cls._cached_info

        os_type = cls._detect_os()
        os_version = cls._detect_os_version()
        shell_type, shell_path = cls._detect_shell()
        shell_version = cls._detect_shell_version(shell_type, shell_path)
        capabilities = cls._detect_capabilities(os_type, shell_type)
        available_commands = cls._detect_available_commands(capabilities)

        cls._cached_info = PlatformInfo(
            os_type=os_type,
            os_version=os_version,
            shell_type=shell_type,
            shell_path=shell_path,
            shell_version=shell_version,
            capabilities=capabilities,
            available_commands=available_commands,
        )

        return cls._cached_info

    @classmethod
    def _detect_os(cls) -> OSType:
        """Detect the operating system"""
        platform = sys.platform.lower()

        if platform == "win32" or platform == "cygwin":
            return OSType.WINDOWS
        elif platform == "darwin":
            return OSType.MACOS
        elif platform.startswith("linux"):
            return OSType.LINUX
        else:
            return OSType.UNKNOWN

    @classmethod
    def _detect_os_version(cls) -> str:
        """Detect OS version string"""
        import platform
        return platform.platform()

    @classmethod
    def _detect_shell(cls) -> Tuple[ShellType, str]:
        """Detect the current shell type and path"""
        os_type = cls._detect_os()

        # Check environment variables first
        shell_env = os.environ.get("SHELL", "")
        comspec = os.environ.get("COMSPEC", "")

        # Check for Git Bash on Windows
        if os_type == OSType.WINDOWS:
            # Check if running in Git Bash
            if "MSYSTEM" in os.environ:
                msystem = os.environ.get("MSYSTEM", "")
                if msystem in ("MINGW64", "MINGW32", "MSYS"):
                    bash_path = shutil.which("bash")
                    return ShellType.GIT_BASH, bash_path or "/usr/bin/bash"

            # Check for WSL
            if "WSL_DISTRO_NAME" in os.environ:
                return ShellType.WSL, shell_env or "/bin/bash"

            # Check for PowerShell
            ps_version = os.environ.get("PSVersionTable", "")
            if "powershell" in comspec.lower() or ps_version:
                # Check if PowerShell Core (pwsh) or Windows PowerShell
                pwsh_path = shutil.which("pwsh")
                if pwsh_path:
                    return ShellType.POWERSHELL_CORE, pwsh_path

                ps_path = shutil.which("powershell")
                if ps_path:
                    return ShellType.POWERSHELL, ps_path

            # Default to cmd on Windows
            return ShellType.CMD, comspec or "C:\\Windows\\System32\\cmd.exe"

        # Unix-like systems
        if shell_env:
            shell_name = Path(shell_env).name.lower()

            if shell_name == "bash":
                return ShellType.BASH, shell_env
            elif shell_name == "zsh":
                return ShellType.ZSH, shell_env
            elif shell_name == "fish":
                return ShellType.FISH, shell_env
            elif shell_name == "sh":
                return ShellType.SH, shell_env

        # Try to detect from running process
        bash_path = shutil.which("bash")
        if bash_path:
            return ShellType.BASH, bash_path

        return ShellType.UNKNOWN, ""

    @classmethod
    def _detect_shell_version(cls, shell_type: ShellType, shell_path: str) -> str:
        """Detect the shell version"""
        try:
            if shell_type in (ShellType.BASH, ShellType.GIT_BASH, ShellType.ZSH):
                result = subprocess.run(
                    [shell_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.split("\n")[0].strip()

            elif shell_type in (ShellType.POWERSHELL, ShellType.POWERSHELL_CORE):
                result = subprocess.run(
                    [shell_path, "-Command", "$PSVersionTable.PSVersion.ToString()"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return f"PowerShell {result.stdout.strip()}"

            elif shell_type == ShellType.CMD:
                # CMD doesn't have a simple version command
                result = subprocess.run(
                    ["cmd", "/c", "ver"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass

        return "unknown"

    @classmethod
    def _detect_capabilities(cls, os_type: OSType, shell_type: ShellType) -> ShellCapabilities:
        """Detect shell capabilities based on OS and shell type"""
        caps = ShellCapabilities()

        # Unix-like shells (including Git Bash)
        if shell_type in (ShellType.BASH, ShellType.ZSH, ShellType.FISH,
                          ShellType.SH, ShellType.GIT_BASH, ShellType.WSL):
            caps.unix_commands = True
            caps.glob_support = True
            caps.heredoc_support = True
            caps.background_jobs = True

        # PowerShell
        elif shell_type in (ShellType.POWERSHELL, ShellType.POWERSHELL_CORE):
            caps.powershell_commands = True
            caps.glob_support = True  # PowerShell supports globbing
            caps.heredoc_support = True  # Here-strings
            caps.background_jobs = True

        # CMD
        elif shell_type == ShellType.CMD:
            caps.cmd_commands = True
            caps.glob_support = False  # CMD has limited globbing
            caps.heredoc_support = False
            caps.background_jobs = False  # START is not quite the same

        return caps

    @classmethod
    def _detect_available_commands(cls, capabilities: ShellCapabilities) -> Dict[str, str]:
        """Detect which commands are available in the current environment"""
        commands_to_check = []

        if capabilities.unix_commands:
            commands_to_check.extend([
                "cp", "mv", "rm", "ls", "cat", "grep", "find", "mkdir", "touch"
            ])

        if capabilities.cmd_commands:
            commands_to_check.extend([
                "xcopy", "copy", "move", "del", "dir", "type", "find", "mkdir"
            ])

        if capabilities.powershell_commands:
            commands_to_check.extend([
                "Copy-Item", "Move-Item", "Remove-Item", "Get-ChildItem",
                "Get-Content", "New-Item", "Test-Path"
            ])

        available = {}
        for cmd in commands_to_check:
            path = shutil.which(cmd)
            if path:
                available[cmd] = path
            else:
                # For PowerShell cmdlets, check differently
                if capabilities.powershell_commands and "-" in cmd:
                    # PowerShell cmdlets are always available
                    available[cmd] = "builtin"

        return available

    @classmethod
    def get_recommended_shell_for_command(cls, command: str) -> ShellType:
        """
        Get the recommended shell type for a given command.

        Args:
            command: The command to check (e.g., "cp", "xcopy")

        Returns:
            Recommended shell type
        """
        info = cls.detect()

        # Unix commands
        unix_commands = {"cp", "mv", "rm", "ls", "cat", "grep", "find", "mkdir",
                        "touch", "chmod", "chown", "tar", "gzip", "sed", "awk"}

        # Windows CMD commands
        cmd_commands = {"xcopy", "copy", "move", "del", "dir", "type", "md",
                       "rd", "ren", "attrib", "robocopy"}

        # PowerShell cmdlets
        ps_commands = {"Copy-Item", "Move-Item", "Remove-Item", "Get-ChildItem",
                      "Get-Content", "Set-Content", "New-Item", "Test-Path"}

        base_command = command.split()[0].lower()

        if base_command in unix_commands:
            if info.capabilities.unix_commands:
                return info.shell_type
            elif info.os_type == OSType.WINDOWS:
                # Prefer Git Bash if available
                if shutil.which("bash"):
                    return ShellType.GIT_BASH
                return ShellType.POWERSHELL

        elif base_command in cmd_commands:
            return ShellType.CMD

        elif any(base_command.lower() == ps.lower() for ps in ps_commands):
            if info.capabilities.powershell_commands:
                return ShellType.POWERSHELL

        return info.shell_type

    @classmethod
    def is_command_available(cls, command: str) -> bool:
        """
        Check if a command is available in the current environment.

        Args:
            command: The command to check

        Returns:
            True if available, False otherwise
        """
        info = cls.detect()
        base_command = command.split()[0]
        return base_command in info.available_commands or shutil.which(base_command) is not None


def get_platform_info() -> PlatformInfo:
    """Convenience function to get platform info"""
    return PlatformDetector.detect()


def get_platform_summary() -> str:
    """Get a human-readable platform summary"""
    info = get_platform_info()

    caps = []
    if info.capabilities.unix_commands:
        caps.append("Unix")
    if info.capabilities.cmd_commands:
        caps.append("CMD")
    if info.capabilities.powershell_commands:
        caps.append("PowerShell")

    return (
        f"OS: {info.os_type.value} ({info.os_version})\n"
        f"Shell: {info.shell_type.value} ({info.shell_version})\n"
        f"Capabilities: {', '.join(caps) if caps else 'Unknown'}"
    )


if __name__ == "__main__":
    # Test the detector
    info = get_platform_info()
    print("Platform Detection Results:")
    print("=" * 50)
    print(get_platform_summary())
    print("\nAvailable Commands:")
    for cmd, path in sorted(info.available_commands.items()):
        print(f"  {cmd}: {path}")
