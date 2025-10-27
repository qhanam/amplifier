"""Unit tests for CLI interface."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ..main import cli
from ..models import SandboxInfo


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_sandbox_info(self, tmp_path: Path) -> SandboxInfo:
        """Create a mock SandboxInfo for testing."""
        from datetime import UTC
        from datetime import datetime

        return SandboxInfo(
            name="test-feature",
            created=datetime.now(UTC),
            project_name="test-project",
            git_url="https://github.com/user/test-project.git",
            branch_name="feature/test-feature",
            sandbox_path=tmp_path / "workspace" / "amplifier-sandbox.test-feature",
            amplifier_commit="abc123def456",
        )

    def test_cli_group(self, runner: CliRunner) -> None:
        """Test CLI group runs without error."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Manage isolated Amplifier sandbox environments" in result.output

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_create_success(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
        mock_sandbox_info: SandboxInfo,
    ) -> None:
        """Test successful sandbox creation."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.create_sandbox.return_value = mock_sandbox_info
        mock_sandbox_manager.return_value = mock_manager

        # Run command with git URL
        result = runner.invoke(
            cli,
            [
                "create",
                "test-feature",
                "https://github.com/user/test-project.git",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "created successfully" in result.output
        assert "test-feature" in result.output
        mock_manager.create_sandbox.assert_called_once()

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_create_empty_git_url(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with empty git URL."""
        # Setup mock to raise error for empty git URL
        mock_manager = MagicMock()
        mock_manager.create_sandbox.side_effect = ValueError("Git URL cannot be empty")
        mock_sandbox_manager.return_value = mock_manager

        # Run command with empty git URL
        result = runner.invoke(
            cli,
            [
                "create",
                "test-feature",
                "",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify error
        assert result.exit_code != 0

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_remove_success(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test successful sandbox removal."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_sandbox_manager.return_value = mock_manager

        # Run command with --force to skip confirmation
        result = runner.invoke(
            cli,
            [
                "remove",
                "test-feature",
                "--force",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "removed successfully" in result.output
        mock_manager.remove_sandbox.assert_called_once_with("test-feature", force=True)

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_remove_with_confirmation(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test removal with user confirmation."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_sandbox_manager.return_value = mock_manager

        # Run command and confirm
        result = runner.invoke(
            cli,
            [
                "remove",
                "test-feature",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
            input="y\n",
        )

        # Verify
        assert result.exit_code == 0
        assert "removed successfully" in result.output
        mock_manager.remove_sandbox.assert_called_once()

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_remove_cancelled(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test removal cancelled by user."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_sandbox_manager.return_value = mock_manager

        # Run command and cancel
        result = runner.invoke(
            cli,
            [
                "remove",
                "test-feature",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
            input="n\n",
        )

        # Verify cancelled
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_manager.remove_sandbox.assert_not_called()

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_info_success(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
        mock_sandbox_info: SandboxInfo,
    ) -> None:
        """Test getting sandbox info."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_sandbox_info.return_value = mock_sandbox_info
        mock_sandbox_manager.return_value = mock_manager

        # Run command
        result = runner.invoke(
            cli,
            [
                "info",
                "test-feature",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "test-feature" in result.output
        assert "test-project" in result.output
        assert "feature/test-feature" in result.output
        mock_manager.get_sandbox_info.assert_called_once_with("test-feature")

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_list_empty(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test listing when no sandboxes exist."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.list_sandboxes.return_value = []
        mock_sandbox_manager.return_value = mock_manager

        # Run command
        result = runner.invoke(
            cli,
            [
                "list",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "No sandboxes found" in result.output

    @patch("sandbox_env.main.SandboxManager")
    @patch("sandbox_env.main.StateManager")
    def test_list_with_sandboxes(
        self,
        mock_state_manager: MagicMock,
        mock_sandbox_manager: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
        mock_sandbox_info: SandboxInfo,
    ) -> None:
        """Test listing multiple sandboxes."""
        from datetime import UTC
        from datetime import datetime

        # Create multiple sandbox infos
        sandbox1 = mock_sandbox_info
        sandbox2 = SandboxInfo(
            name="another-feature",
            created=datetime.now(UTC),
            project_name="another-project",
            git_url="https://github.com/user/another-project.git",
            branch_name="feature/another-feature",
            sandbox_path=tmp_path / "workspace" / "amplifier-sandbox.another-feature",
            amplifier_commit="def456abc789",
        )

        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.list_sandboxes.return_value = [sandbox1, sandbox2]
        mock_sandbox_manager.return_value = mock_manager

        # Run command
        result = runner.invoke(
            cli,
            [
                "list",
                "--workspace",
                str(tmp_path / "workspace"),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "Found 2 sandbox(es)" in result.output
        assert "test-feature" in result.output
        assert "another-feature" in result.output
        assert "test-project" in result.output
        assert "another-project" in result.output

    def test_version(self, runner: CliRunner) -> None:
        """Test version option."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output
