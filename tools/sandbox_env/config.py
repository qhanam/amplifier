"""Configuration constants and path definitions for sandbox tool."""

from pathlib import Path

# Path constants
WORKSPACE_ROOT = Path("/workspace")
STATE_FILE_NAME = ".sandbox-state.json"
SANDBOX_PREFIX = "amplifier-sandbox."

# Git constants
AMPLIFIER_REPO_URL = "https://github.com/qhanam/amplifier.git"
BRANCH_PREFIX = "feature/"


def in_docker() -> bool:
    """Detect if running inside Docker container.

    Returns:
        True if running in Docker, False otherwise
    """
    # Check for .dockerenv file
    if Path("/.dockerenv").exists():
        return True

    # Check for docker in cgroup
    try:
        with open("/proc/1/cgroup") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def get_workspace_root() -> Path:
    """Get workspace root, handling both Docker and local dev.

    Returns:
        Path to workspace root

    Notes:
        - In Docker: /workspace
        - Local dev: ./workspace (relative to current directory)
    """
    if in_docker():
        return WORKSPACE_ROOT

    # Local development: use ./workspace relative to current dir
    return Path.cwd() / "workspace"
