"""Manages persistent state of all sandboxes."""

import fcntl
import json
from pathlib import Path

from .config import STATE_FILE_NAME
from .config import get_workspace_root
from .exceptions import SandboxExistsError
from .exceptions import SandboxNotFoundError
from .exceptions import StateFileError
from .models import SandboxInfo
from .models import SandboxState


class StateManager:
    """Manages persistent state of all sandboxes.

    State is stored in a JSON file at workspace root with file locking
    to ensure thread safety.
    """

    def __init__(self: "StateManager", workspace_root: Path | None = None) -> None:
        """Initialize with workspace root.

        Args:
            workspace_root: Path to workspace root (defaults to auto-detected)
        """
        self.workspace_root = workspace_root or get_workspace_root()
        self.state_file = self.workspace_root / STATE_FILE_NAME

    def load(self: "StateManager") -> SandboxState:
        """Load state from file, return empty if missing.

        Returns:
            SandboxState loaded from file or empty state

        Raises:
            StateFileError: If state file is corrupt or unreadable
        """
        if not self.state_file.exists():
            return SandboxState.empty()

        try:
            with open(self.state_file) as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    self._validate_state(data)
                    return SandboxState.from_dict(data)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except json.JSONDecodeError as e:
            raise StateFileError(f"State file is corrupt: {e}") from e
        except OSError as e:
            raise StateFileError(f"Failed to read state file: {e}") from e

    def save(self: "StateManager", state: SandboxState) -> None:
        """Save state to file with file locking.

        Args:
            state: SandboxState to persist

        Raises:
            StateFileError: If state cannot be written
        """
        try:
            # Ensure workspace root exists
            self.workspace_root.mkdir(parents=True, exist_ok=True)

            # Convert to dict
            data = state.to_dict()

            # Atomic write with exclusive lock
            self._atomic_write(data)
        except OSError as e:
            raise StateFileError(f"Failed to write state file: {e}") from e

    def add_sandbox(self: "StateManager", info: SandboxInfo) -> None:
        """Add sandbox to state.

        Args:
            info: SandboxInfo to add

        Raises:
            SandboxExistsError: If sandbox name already exists
            StateFileError: If state cannot be saved
        """
        state = self.load()

        if info.name in state.sandboxes:
            raise SandboxExistsError(f"Sandbox '{info.name}' already exists")

        state.sandboxes[info.name] = info
        self.save(state)

    def remove_sandbox(self: "StateManager", name: str) -> None:
        """Remove sandbox from state.

        Args:
            name: Sandbox name to remove

        Raises:
            SandboxNotFoundError: If sandbox doesn't exist
            StateFileError: If state cannot be saved
        """
        state = self.load()

        if name not in state.sandboxes:
            raise SandboxNotFoundError(f"Sandbox '{name}' not found")

        del state.sandboxes[name]
        self.save(state)

    def get_sandbox(self: "StateManager", name: str) -> SandboxInfo | None:
        """Get sandbox info by name.

        Args:
            name: Sandbox name

        Returns:
            SandboxInfo if found, None otherwise
        """
        state = self.load()
        return state.sandboxes.get(name)

    def list_sandboxes(self: "StateManager") -> list[SandboxInfo]:
        """Get all sandboxes, sorted by creation date.

        Returns:
            List of SandboxInfo sorted by creation date (oldest first)
        """
        state = self.load()
        sandboxes = list(state.sandboxes.values())
        return sorted(sandboxes, key=lambda s: s.created)

    def sandbox_exists(self: "StateManager", name: str) -> bool:
        """Check if sandbox exists in state.

        Args:
            name: Sandbox name

        Returns:
            True if sandbox exists, False otherwise
        """
        state = self.load()
        return name in state.sandboxes

    def _validate_state(self: "StateManager", state_dict: dict) -> None:
        """Validate state file format.

        Args:
            state_dict: Dictionary to validate

        Raises:
            StateFileError: If state format is invalid
        """
        if not isinstance(state_dict, dict):
            raise StateFileError("State file must be a JSON object")

        if "version" not in state_dict:
            raise StateFileError("State file missing 'version' field")

        if "sandboxes" not in state_dict:
            raise StateFileError("State file missing 'sandboxes' field")

        if not isinstance(state_dict["sandboxes"], dict):
            raise StateFileError("'sandboxes' field must be an object")

    def _atomic_write(self: "StateManager", data: dict) -> None:
        """Write state file atomically with locking.

        Args:
            data: Dictionary to write as JSON

        Raises:
            StateFileError: If write fails
        """
        # Write to temporary file first
        temp_file = self.state_file.with_suffix(".tmp")

        try:
            with open(temp_file, "w") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename (replaces existing file)
            temp_file.replace(self.state_file)
        except OSError as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise StateFileError(f"Failed to write state atomically: {e}") from e
