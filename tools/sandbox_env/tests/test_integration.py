"""Integration tests for sandbox environment tool."""

import subprocess
from pathlib import Path

import pytest

from ..state_manager import StateManager


@pytest.mark.integration
class TestSandboxIntegration:
    """Integration tests using real git operations."""

    @pytest.fixture
    def test_workspace(self, tmp_path: Path) -> Path:
        """Create a temporary workspace for testing."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    @pytest.fixture
    def test_git_url(self) -> str:
        """Return a test git URL for integration testing."""
        return "https://github.com/user/test-project.git"

    @pytest.mark.skipif(
        subprocess.run(["which", "git"], capture_output=True).returncode != 0,
        reason="Git not available",
    )
    def test_full_lifecycle(
        self,
        test_workspace: Path,
        test_git_url: str,
    ) -> None:
        """Test complete sandbox lifecycle with real git operations.

        This test requires:
        1. Git to be installed
        2. Network access to clone Amplifier repo
        3. Sufficient disk space

        Skip this test in CI/CD environments or when resources are unavailable.
        """
        from ..models import SandboxConfig
        from ..sandbox_manager import SandboxManager

        # Create sandbox using git URL directly
        config = SandboxConfig(
            name="integration-test",
            git_url=test_git_url,
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=test_workspace,
        )

        state_manager = StateManager(workspace_root=test_workspace)
        manager = SandboxManager(state_manager=state_manager)

        # Create sandbox (this will clone the real Amplifier repo)
        info = manager.create_sandbox(config)

        # Verify sandbox was created
        assert info.name == "integration-test"
        assert info.project_name == "test-project"
        assert info.branch_name == "feature/integration-test"
        assert info.sandbox_path.exists()
        assert (info.sandbox_path / "test-project").exists()
        assert (info.sandbox_path / "SANDBOX.md").exists()

        # Verify state was updated
        assert state_manager.sandbox_exists("integration-test")
        retrieved_info = state_manager.get_sandbox("integration-test")
        assert retrieved_info is not None
        assert retrieved_info.name == info.name

        # Verify git submodule was added
        gitmodules = info.sandbox_path / ".gitmodules"
        assert gitmodules.exists()
        gitmodules_content = gitmodules.read_text()
        assert "test-project" in gitmodules_content

        # Verify feature branch was created
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=info.sandbox_path / "test-project",
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/integration-test"

        # List sandboxes
        sandboxes = manager.list_sandboxes()
        assert len(sandboxes) == 1
        assert sandboxes[0].name == "integration-test"

        # Get sandbox info
        retrieved = manager.get_sandbox_info("integration-test")
        assert retrieved.name == info.name
        assert retrieved.amplifier_commit == info.amplifier_commit

        # Remove sandbox
        manager.remove_sandbox("integration-test")

        # Verify sandbox was removed
        assert not state_manager.sandbox_exists("integration-test")
        assert not info.sandbox_path.exists()

    def test_cli_integration(
        self,
        test_workspace: Path,
    ) -> None:
        """Test CLI commands with mocked operations.

        This is a lighter integration test that verifies CLI commands
        work together without requiring network access.
        """
        from click.testing import CliRunner

        from ..main import cli

        runner = CliRunner()

        # Note: This test uses mocked operations, not real git
        # For full integration with real git, use test_full_lifecycle above
        with runner.isolated_filesystem():
            # The CLI test is covered in test_main.py with proper mocks
            # This integration test verifies the overall structure works
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            assert "create" in result.output
            assert "remove" in result.output
            assert "info" in result.output
            assert "list" in result.output
