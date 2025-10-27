"""Data models for sandbox configuration and state."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import Self

from .config import BRANCH_PREFIX
from .config import SANDBOX_PREFIX
from .exceptions import InvalidProjectPathError


@dataclass
class SandboxConfig:
    """Configuration for creating a new sandbox.

    Attributes:
        name: Feature name (e.g., "add-tags")
        git_url: Git URL of project repository (e.g., git@github.com:user/repo.git)
        amplifier_repo_url: Git URL for Amplifier
        workspace_root: Where to create sandbox (used for default path)
        custom_sandbox_path: Optional custom full path for sandbox (overrides default)
    """

    name: str
    git_url: str
    amplifier_repo_url: str
    workspace_root: Path
    custom_sandbox_path: Path | None = None

    @property
    def project_name(self) -> str:
        """Extract project name from git URL.

        Returns:
            Project directory name (extracted from git URL)
        """
        # Extract repository name from git URL
        # Examples:
        #   git@github.com:user/repo.git -> repo
        #   https://github.com/user/repo.git -> repo
        #   https://github.com/user/repo -> repo
        url = self.git_url.rstrip("/")

        # Handle .git suffix
        if url.endswith(".git"):
            url = url[:-4]

        # Extract last part after / or :
        if "/" in url:
            return url.split("/")[-1]
        elif ":" in url:
            # Handle git@host:user/repo format
            parts = url.split(":")
            if len(parts) >= 2 and "/" in parts[-1]:
                return parts[-1].split("/")[-1]

        # Fallback: just use the whole URL if we can't parse it
        return url

    @property
    def branch_name(self) -> str:
        """Generate branch name (feature/{name}).

        Returns:
            Feature branch name
        """
        return f"{BRANCH_PREFIX}{self.name}"

    @property
    def sandbox_path(self) -> Path:
        """Full path to sandbox directory.

        Returns:
            Path where sandbox will be created
        """
        if self.custom_sandbox_path:
            return self.custom_sandbox_path
        return self.workspace_root / f"{SANDBOX_PREFIX}{self.name}"

    def validate(self) -> None:
        """Validate configuration, raise if invalid.

        Raises:
            ValueError: If name or git_url is invalid
        """
        # Validate name
        if not self.name:
            raise ValueError("Sandbox name cannot be empty")

        if not self.name.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Sandbox name must contain only alphanumeric characters, hyphens, and underscores")

        # Validate git URL is not empty
        if not self.git_url:
            raise ValueError("Git URL cannot be empty")


@dataclass
class SandboxInfo:
    """Information about an existing sandbox.

    Attributes:
        name: Sandbox/feature name
        created: Creation timestamp
        project_name: Name of the project
        git_url: Git URL of the project repository
        branch_name: Feature branch name
        sandbox_path: Path to sandbox directory
        amplifier_commit: Git commit hash of Amplifier clone
    """

    name: str
    created: datetime
    project_name: str
    git_url: str
    branch_name: str
    sandbox_path: Path
    amplifier_commit: str

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "created": self.created.isoformat(),
            "project_name": self.project_name,
            "git_url": self.git_url,
            "branch_name": self.branch_name,
            "sandbox_path": str(self.sandbox_path),
            "amplifier_commit": self.amplifier_commit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Deserialize from dict.

        Args:
            data: Dictionary with sandbox info

        Returns:
            SandboxInfo instance

        Note:
            Supports backward compatibility with old state files that use
            'project_path' instead of 'git_url'.
        """
        # Handle backward compatibility: old state files have 'project_path',
        # new ones have 'git_url'
        git_url = data.get("git_url")
        if git_url is None:
            # Fall back to old project_path field for backward compatibility
            project_path = data.get("project_path")
            if project_path is None:
                raise ValueError("State file missing both 'git_url' and 'project_path' fields")
            # Use the old project_path value (will be a file path, not a git URL,
            # but that's ok for existing sandboxes)
            git_url = str(project_path)

        return cls(
            name=data["name"],
            created=datetime.fromisoformat(data["created"]),
            project_name=data["project_name"],
            git_url=git_url,
            branch_name=data["branch_name"],
            sandbox_path=Path(data["sandbox_path"]),
            amplifier_commit=data["amplifier_commit"],
        )


@dataclass
class SandboxState:
    """Complete state of all sandboxes.

    Attributes:
        version: State file format version
        sandboxes: Dictionary of sandbox name to SandboxInfo
    """

    version: str
    sandboxes: dict[str, SandboxInfo] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize for JSON storage.

        Returns:
            Dictionary representation
        """
        return {
            "version": self.version,
            "sandboxes": {name: info.to_dict() for name, info in self.sandboxes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Deserialize from JSON.

        Args:
            data: Dictionary with state data

        Returns:
            SandboxState instance
        """
        sandboxes = {name: SandboxInfo.from_dict(info_dict) for name, info_dict in data.get("sandboxes", {}).items()}
        return cls(
            version=data.get("version", "1.0"),
            sandboxes=sandboxes,
        )

    @classmethod
    def empty(cls) -> Self:
        """Create empty initial state.

        Returns:
            Empty SandboxState with current version
        """
        return cls(version="1.0", sandboxes={})
