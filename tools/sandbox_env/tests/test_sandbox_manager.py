"""Unit tests for sandbox operations (with mocked git)."""

import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ..exceptions import GitOperationError
from ..exceptions import SandboxExistsError
from ..exceptions import SandboxNotFoundError
from ..models import SandboxConfig
from ..sandbox_manager import _GIT_EXECUTABLE
from ..sandbox_manager import _MAKE_EXECUTABLE
from ..sandbox_manager import SandboxManager
from ..state_manager import StateManager


class TestSandboxManager:
    """Tests for SandboxManager class."""

    @pytest.fixture
    def sandbox_config(self, tmp_path: Path) -> SandboxConfig:
        """Create a test sandbox configuration."""
        return SandboxConfig(
            name="test-feature",
            git_url="https://github.com/user/test-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

    @pytest.fixture
    def state_manager(self, tmp_path: Path) -> StateManager:
        """Create a test state manager."""
        return StateManager(workspace_root=tmp_path / "workspace")

    @pytest.fixture
    def manager(self, state_manager: StateManager) -> SandboxManager:
        """Create a test sandbox manager."""
        return SandboxManager(state_manager=state_manager)

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_create_sandbox_success(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
        tmp_path: Path,
    ) -> None:
        """Test successful sandbox creation."""
        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                # Simulate git clone creating the directory
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123def456\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        # Create sandbox
        info = manager.create_sandbox(sandbox_config)

        # Verify info
        assert info.name == "test-feature"
        assert info.project_name == "test-project"
        assert info.branch_name == "feature/test-feature"
        assert info.amplifier_commit == "abc123def456"

        # Verify it was added to state
        assert manager.state.sandbox_exists("test-feature")

        # Verify git commands were called
        assert mock_run.call_count >= 4  # clone, rev-parse, submodule add, submodule update, checkout, make

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_create_sandbox_duplicate_error(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
    ) -> None:
        """Test error when sandbox name exists."""
        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        # Create first sandbox
        manager.create_sandbox(sandbox_config)

        # Try to create duplicate
        with pytest.raises(SandboxExistsError, match="already exists"):
            manager.create_sandbox(sandbox_config)

    def test_create_sandbox_empty_git_url(
        self,
        manager: SandboxManager,
        tmp_path: Path,
    ) -> None:
        """Test error when git URL is empty."""
        config = SandboxConfig(
            name="test-feature",
            git_url="",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        with pytest.raises(ValueError, match="Git URL cannot be empty"):
            manager.create_sandbox(config)

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    @patch("sandbox_env.sandbox_manager.shutil.rmtree")
    def test_create_sandbox_git_failure_cleanup(
        self,
        mock_rmtree: MagicMock,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
    ) -> None:
        """Test cleanup when git clone fails."""
        # Mock git clone to fail
        mock_run.side_effect = GitOperationError("Clone failed")

        # Attempt to create sandbox
        with pytest.raises(GitOperationError, match="Clone failed"):
            manager.create_sandbox(sandbox_config)

        # Verify sandbox was not added to state
        assert not manager.state.sandbox_exists("test-feature")

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_remove_sandbox_success(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
    ) -> None:
        """Test successful removal."""

        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        # Create sandbox
        info = manager.create_sandbox(sandbox_config)

        # Create the sandbox directory to test cleanup
        info.sandbox_path.mkdir(parents=True, exist_ok=True)

        # Remove it
        manager.remove_sandbox("test-feature")

        # Verify it's gone from state
        assert not manager.state.sandbox_exists("test-feature")

        # Verify directory was deleted
        assert not info.sandbox_path.exists()

    def test_remove_sandbox_not_found(self, manager: SandboxManager) -> None:
        """Test error when sandbox doesn't exist."""
        with pytest.raises(SandboxNotFoundError, match="not found"):
            manager.remove_sandbox("nonexistent")

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_remove_sandbox_missing_directory(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
    ) -> None:
        """Test removal when directory already deleted."""

        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        manager.create_sandbox(sandbox_config)

        # Don't create the directory (simulate it being manually deleted)

        # Remove should succeed even if directory missing
        manager.remove_sandbox("test-feature")

        # Verify it's gone from state
        assert not manager.state.sandbox_exists("test-feature")

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_get_sandbox_info(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
    ) -> None:
        """Test getting sandbox info."""

        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        # Create sandbox
        created_info = manager.create_sandbox(sandbox_config)

        # Get info
        retrieved_info = manager.get_sandbox_info("test-feature")

        # Verify info matches
        assert retrieved_info.name == created_info.name
        assert retrieved_info.project_name == created_info.project_name
        assert retrieved_info.amplifier_commit == created_info.amplifier_commit

    def test_get_sandbox_info_not_found(self, manager: SandboxManager) -> None:
        """Test error when getting info for nonexistent sandbox."""
        with pytest.raises(SandboxNotFoundError, match="not found"):
            manager.get_sandbox_info("nonexistent")

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_list_sandboxes(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        sandbox_config: SandboxConfig,
        tmp_path: Path,
    ) -> None:
        """Test listing sandboxes."""
        # Mock subprocess to create directory on git clone
        def mock_subprocess(cmd, *args, **kwargs):
            if _GIT_EXECUTABLE in cmd and "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(stdout="abc123\n", stderr="", returncode=0)

        mock_run.side_effect = mock_subprocess

        # Create multiple sandboxes
        config1 = sandbox_config
        manager.create_sandbox(config1)

        config2 = SandboxConfig(
            name="another-feature",
            git_url="https://github.com/user/another-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )
        manager.create_sandbox(config2)

        # List sandboxes
        sandboxes = manager.list_sandboxes()

        # Verify both are listed
        assert len(sandboxes) == 2
        names = {s.name for s in sandboxes}
        assert "test-feature" in names
        assert "another-feature" in names

    def test_list_sandboxes_empty(self, manager: SandboxManager) -> None:
        """Test listing when no sandboxes exist."""
        sandboxes = manager.list_sandboxes()
        assert sandboxes == []

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_clone_amplifier(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        tmp_path: Path,
    ) -> None:
        """Test cloning Amplifier repository."""
        # Mock git clone and rev-parse
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # clone
            MagicMock(stdout="abc123def456\n", stderr="", returncode=0),  # rev-parse
        ]

        target_dir = tmp_path / "test-sandbox"
        commit_hash = manager._clone_amplifier(
            target_dir=target_dir,
            repo_url="https://github.com/qhanam/amplifier.git",
        )

        # Verify commit hash
        assert commit_hash == "abc123def456"

        # Verify git commands were called
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][0][:2] == [_GIT_EXECUTABLE, "clone"]
        assert mock_run.call_args_list[1][0][0] == [_GIT_EXECUTABLE, "rev-parse", "HEAD"]

    @patch("sandbox_env.sandbox_manager.subprocess.run")
    def test_add_project_submodule(
        self,
        mock_run: MagicMock,
        manager: SandboxManager,
        tmp_path: Path,
    ) -> None:
        """Test adding project as submodule using git URL."""
        sandbox_dir = tmp_path / "sandbox"
        sandbox_dir.mkdir()

        # Initialize git repo in sandbox
        subprocess.run([_GIT_EXECUTABLE, "init"], cwd=sandbox_dir, check=True, capture_output=True)

        # Call the method
        manager._add_project_submodule(
            sandbox_dir=sandbox_dir,
            git_url="https://github.com/user/test-project.git",
            project_name="test-project",
        )

        # Verify git submodule commands were called
        assert mock_run.call_count >= 2
        # Check submodule add was called with git URL
        submodule_add_called = any(
            "submodule" in str(call) and "add" in str(call) and "test-project" in str(call)
            for call in mock_run.call_args_list
        )
        assert submodule_add_called
