"""Unit tests for state persistence."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from ..exceptions import SandboxExistsError
from ..exceptions import SandboxNotFoundError
from ..exceptions import StateFileError
from ..models import SandboxInfo
from ..models import SandboxState
from ..state_manager import StateManager


class TestStateManager:
    """Tests for StateManager class."""

    def test_load_empty_state(self, tmp_path: Path) -> None:
        """Test loading when no state file exists."""
        manager = StateManager(workspace_root=tmp_path)
        state = manager.load()

        assert state.version == "1.0"
        assert state.sandboxes == {}

    def test_load_existing_state(self, tmp_path: Path) -> None:
        """Test loading valid state file."""
        # Create a state file
        state_file = tmp_path / ".sandbox-state.json"
        state_data = {
            "version": "1.0",
            "sandboxes": {
                "test-feature": {
                    "name": "test-feature",
                    "created": "2025-01-24T10:00:00",
                    "project_name": "my-project",
                    "git_url": "https://github.com/user/my-project.git",
                    "branch_name": "feature/test-feature",
                    "sandbox_path": "/workspace/amplifier-sandbox.test-feature",
                    "amplifier_commit": "abc123",
                }
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Load state
        manager = StateManager(workspace_root=tmp_path)
        state = manager.load()

        assert state.version == "1.0"
        assert len(state.sandboxes) == 1
        assert "test-feature" in state.sandboxes

        info = state.sandboxes["test-feature"]
        assert info.name == "test-feature"
        assert info.project_name == "my-project"
        assert info.amplifier_commit == "abc123"

    def test_load_corrupt_state(self, tmp_path: Path) -> None:
        """Test handling of corrupt state file."""
        state_file = tmp_path / ".sandbox-state.json"
        state_file.write_text("not valid json {")

        manager = StateManager(workspace_root=tmp_path)

        with pytest.raises(StateFileError, match="corrupt"):
            manager.load()

    def test_load_invalid_format_missing_version(self, tmp_path: Path) -> None:
        """Test validation fails when version field is missing."""
        state_file = tmp_path / ".sandbox-state.json"
        state_data = {"sandboxes": {}}

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        manager = StateManager(workspace_root=tmp_path)

        with pytest.raises(StateFileError, match="missing 'version'"):
            manager.load()

    def test_load_invalid_format_missing_sandboxes(self, tmp_path: Path) -> None:
        """Test validation fails when sandboxes field is missing."""
        state_file = tmp_path / ".sandbox-state.json"
        state_data = {"version": "1.0"}

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        manager = StateManager(workspace_root=tmp_path)

        with pytest.raises(StateFileError, match="missing 'sandboxes'"):
            manager.load()

    def test_save_state(self, tmp_path: Path) -> None:
        """Test saving state to file."""
        manager = StateManager(workspace_root=tmp_path)

        # Create state with one sandbox
        info = SandboxInfo(
            name="test-feature",
            created=datetime(2025, 1, 24, 10, 0, 0, tzinfo=UTC),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/test-feature",
            sandbox_path=Path("/workspace/amplifier-sandbox.test-feature"),
            amplifier_commit="abc123",
        )

        state = SandboxState(version="1.0", sandboxes={"test-feature": info})

        # Save state
        manager.save(state)

        # Verify file exists
        state_file = tmp_path / ".sandbox-state.json"
        assert state_file.exists()

        # Verify content
        with open(state_file) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "test-feature" in data["sandboxes"]

    def test_add_sandbox(self, tmp_path: Path) -> None:
        """Test adding sandbox to state."""
        manager = StateManager(workspace_root=tmp_path)

        info = SandboxInfo(
            name="new-feature",
            created=datetime.now(),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/new-feature",
            sandbox_path=Path("/workspace/amplifier-sandbox.new-feature"),
            amplifier_commit="abc123",
        )

        # Add sandbox
        manager.add_sandbox(info)

        # Verify it was saved
        state = manager.load()
        assert "new-feature" in state.sandboxes
        assert state.sandboxes["new-feature"].name == "new-feature"

    def test_add_sandbox_duplicate_error(self, tmp_path: Path) -> None:
        """Test error when sandbox name exists."""
        manager = StateManager(workspace_root=tmp_path)

        info = SandboxInfo(
            name="duplicate",
            created=datetime.now(),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/duplicate",
            sandbox_path=Path("/workspace/amplifier-sandbox.duplicate"),
            amplifier_commit="abc123",
        )

        # Add first time
        manager.add_sandbox(info)

        # Try to add again
        with pytest.raises(SandboxExistsError, match="already exists"):
            manager.add_sandbox(info)

    def test_remove_sandbox(self, tmp_path: Path) -> None:
        """Test removing sandbox from state."""
        manager = StateManager(workspace_root=tmp_path)

        # Add sandbox
        info = SandboxInfo(
            name="to-remove",
            created=datetime.now(),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/to-remove",
            sandbox_path=Path("/workspace/amplifier-sandbox.to-remove"),
            amplifier_commit="abc123",
        )
        manager.add_sandbox(info)

        # Verify it exists
        assert manager.sandbox_exists("to-remove")

        # Remove it
        manager.remove_sandbox("to-remove")

        # Verify it's gone
        assert not manager.sandbox_exists("to-remove")

    def test_remove_sandbox_not_found(self, tmp_path: Path) -> None:
        """Test error when removing non-existent sandbox."""
        manager = StateManager(workspace_root=tmp_path)

        with pytest.raises(SandboxNotFoundError, match="not found"):
            manager.remove_sandbox("nonexistent")

    def test_get_sandbox(self, tmp_path: Path) -> None:
        """Test getting sandbox by name."""
        manager = StateManager(workspace_root=tmp_path)

        # Add sandbox
        info = SandboxInfo(
            name="get-test",
            created=datetime.now(),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/get-test",
            sandbox_path=Path("/workspace/amplifier-sandbox.get-test"),
            amplifier_commit="abc123",
        )
        manager.add_sandbox(info)

        # Get it
        retrieved = manager.get_sandbox("get-test")

        assert retrieved is not None
        assert retrieved.name == "get-test"
        assert retrieved.project_name == "my-project"

    def test_get_sandbox_not_found(self, tmp_path: Path) -> None:
        """Test getting non-existent sandbox returns None."""
        manager = StateManager(workspace_root=tmp_path)

        result = manager.get_sandbox("nonexistent")

        assert result is None

    def test_list_sandboxes(self, tmp_path: Path) -> None:
        """Test listing all sandboxes."""
        manager = StateManager(workspace_root=tmp_path)

        # Add multiple sandboxes with different creation times
        info1 = SandboxInfo(
            name="feature-1",
            created=datetime(2025, 1, 24, 10, 0, 0, tzinfo=UTC),
            project_name="project-a",
            git_url="https://github.com/user/project-a.git",
            branch_name="feature/feature-1",
            sandbox_path=Path("/workspace/amplifier-sandbox.feature-1"),
            amplifier_commit="commit1",
        )

        info2 = SandboxInfo(
            name="feature-2",
            created=datetime(2025, 1, 24, 11, 0, 0, tzinfo=UTC),
            project_name="project-b",
            git_url="https://github.com/user/project-b.git",
            branch_name="feature/feature-2",
            sandbox_path=Path("/workspace/amplifier-sandbox.feature-2"),
            amplifier_commit="commit2",
        )

        info3 = SandboxInfo(
            name="feature-3",
            created=datetime(2025, 1, 24, 9, 0, 0, tzinfo=UTC),
            project_name="project-c",
            git_url="https://github.com/user/project-c.git",
            branch_name="feature/feature-3",
            sandbox_path=Path("/workspace/amplifier-sandbox.feature-3"),
            amplifier_commit="commit3",
        )

        manager.add_sandbox(info1)
        manager.add_sandbox(info2)
        manager.add_sandbox(info3)

        # List sandboxes
        sandboxes = manager.list_sandboxes()

        # Should be sorted by creation date (oldest first)
        assert len(sandboxes) == 3
        assert sandboxes[0].name == "feature-3"  # 9:00
        assert sandboxes[1].name == "feature-1"  # 10:00
        assert sandboxes[2].name == "feature-2"  # 11:00

    def test_sandbox_exists(self, tmp_path: Path) -> None:
        """Test checking if sandbox exists."""
        manager = StateManager(workspace_root=tmp_path)

        # Should not exist initially
        assert not manager.sandbox_exists("test-feature")

        # Add sandbox
        info = SandboxInfo(
            name="test-feature",
            created=datetime.now(),
            project_name="my-project",
            git_url="https://github.com/user/my-project.git",
            branch_name="feature/test-feature",
            sandbox_path=Path("/workspace/amplifier-sandbox.test-feature"),
            amplifier_commit="abc123",
        )
        manager.add_sandbox(info)

        # Should exist now
        assert manager.sandbox_exists("test-feature")

    def test_atomic_write_creates_workspace(self, tmp_path: Path) -> None:
        """Test that save creates workspace directory if it doesn't exist."""
        workspace = tmp_path / "nonexistent" / "workspace"
        manager = StateManager(workspace_root=workspace)

        state = SandboxState.empty()
        manager.save(state)

        # Verify workspace was created
        assert workspace.exists()
        assert (workspace / ".sandbox-state.json").exists()
