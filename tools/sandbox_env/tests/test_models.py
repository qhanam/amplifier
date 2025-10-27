"""Unit tests for data models."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from ..models import SandboxConfig
from ..models import SandboxInfo
from ..models import SandboxState


class TestSandboxConfig:
    """Tests for SandboxConfig model."""

    def test_sandbox_config_properties(self, tmp_path: Path) -> None:
        """Test derived properties like branch_name, project_name, sandbox_path."""
        config = SandboxConfig(
            name="add-tags",
            git_url="git@github.com:user/my-website.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        # Test project_name property (extracted from git URL)
        assert config.project_name == "my-website"

        # Test branch_name property
        assert config.branch_name == "feature/add-tags"

        # Test sandbox_path property
        expected_path = tmp_path / "workspace" / "amplifier-sandbox.add-tags"
        assert config.sandbox_path == expected_path

    def test_sandbox_config_validation_valid(self, tmp_path: Path) -> None:
        """Test SandboxConfig validates valid inputs."""
        config = SandboxConfig(
            name="valid-name-123",
            git_url="https://github.com/user/test-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        # Should not raise
        config.validate()

    def test_sandbox_config_validation_empty_name(self, tmp_path: Path) -> None:
        """Test validation fails with empty name."""
        config = SandboxConfig(
            name="",
            git_url="https://github.com/user/test-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        with pytest.raises(ValueError, match="Sandbox name cannot be empty"):
            config.validate()

    def test_sandbox_config_validation_invalid_characters(self, tmp_path: Path) -> None:
        """Test validation fails with invalid characters in name."""
        config = SandboxConfig(
            name="invalid/name!",
            git_url="https://github.com/user/test-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        with pytest.raises(ValueError, match="alphanumeric characters"):
            config.validate()

    def test_sandbox_config_validation_empty_git_url(self, tmp_path: Path) -> None:
        """Test validation fails when git URL is empty."""
        config = SandboxConfig(
            name="test-feature",
            git_url="",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        with pytest.raises(ValueError, match="Git URL cannot be empty"):
            config.validate()

    def test_sandbox_config_project_name_from_https_url(self, tmp_path: Path) -> None:
        """Test project_name extraction from HTTPS URL."""
        config = SandboxConfig(
            name="test-feature",
            git_url="https://github.com/user/my-project.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        assert config.project_name == "my-project"

    def test_sandbox_config_project_name_from_ssh_url(self, tmp_path: Path) -> None:
        """Test project_name extraction from SSH URL."""
        config = SandboxConfig(
            name="test-feature",
            git_url="git@github.com:user/another-repo.git",
            amplifier_repo_url="https://github.com/qhanam/amplifier.git",
            workspace_root=tmp_path / "workspace",
        )

        assert config.project_name == "another-repo"


class TestSandboxInfo:
    """Tests for SandboxInfo model."""

    def test_sandbox_info_serialization_roundtrip(self, tmp_path: Path) -> None:
        """Test to_dict/from_dict roundtrip maintains all data."""
        created_time = datetime.now()
        info = SandboxInfo(
            name="add-tags",
            created=created_time,
            project_name="my-website",
            git_url="git@github.com:user/my-website.git",
            branch_name="feature/add-tags",
            sandbox_path=tmp_path / "workspace" / "amplifier-sandbox.add-tags",
            amplifier_commit="abc123def456",
        )

        # Serialize to dict
        data = info.to_dict()

        # Verify dict structure
        assert data["name"] == "add-tags"
        assert data["created"] == created_time.isoformat()
        assert data["project_name"] == "my-website"
        assert data["git_url"] == "git@github.com:user/my-website.git"
        assert data["branch_name"] == "feature/add-tags"
        assert data["amplifier_commit"] == "abc123def456"
        assert isinstance(data["sandbox_path"], str)

        # Deserialize back
        restored = SandboxInfo.from_dict(data)

        # Verify all fields match
        assert restored.name == info.name
        assert restored.created == info.created
        assert restored.project_name == info.project_name
        assert restored.git_url == info.git_url
        assert restored.branch_name == info.branch_name
        assert restored.sandbox_path == info.sandbox_path
        assert restored.amplifier_commit == info.amplifier_commit


class TestSandboxState:
    """Tests for SandboxState model."""

    def test_sandbox_state_empty(self) -> None:
        """Test creating empty initial state."""
        state = SandboxState.empty()

        assert state.version == "1.0"
        assert state.sandboxes == {}

    def test_sandbox_state_serialization_roundtrip(self, tmp_path: Path) -> None:
        """Test to_dict/from_dict roundtrip with multiple sandboxes."""
        # Create state with two sandboxes
        info1 = SandboxInfo(
            name="feature-1",
            created=datetime(2025, 1, 24, 10, 0, 0, tzinfo=UTC),
            project_name="project-a",
            git_url="git@github.com:user/project-a.git",
            branch_name="feature/feature-1",
            sandbox_path=tmp_path / "workspace" / "amplifier-sandbox.feature-1",
            amplifier_commit="commit1",
        )

        info2 = SandboxInfo(
            name="feature-2",
            created=datetime(2025, 1, 24, 11, 0, 0, tzinfo=UTC),
            project_name="project-b",
            git_url="https://github.com/user/project-b.git",
            branch_name="feature/feature-2",
            sandbox_path=tmp_path / "workspace" / "amplifier-sandbox.feature-2",
            amplifier_commit="commit2",
        )

        state = SandboxState(
            version="1.0",
            sandboxes={"feature-1": info1, "feature-2": info2},
        )

        # Serialize
        data = state.to_dict()

        # Verify structure
        assert data["version"] == "1.0"
        assert len(data["sandboxes"]) == 2
        assert "feature-1" in data["sandboxes"]
        assert "feature-2" in data["sandboxes"]

        # Deserialize
        restored = SandboxState.from_dict(data)

        # Verify all fields match
        assert restored.version == state.version
        assert len(restored.sandboxes) == 2
        assert "feature-1" in restored.sandboxes
        assert "feature-2" in restored.sandboxes

        # Verify individual sandbox info
        restored_info1 = restored.sandboxes["feature-1"]
        assert restored_info1.name == info1.name
        assert restored_info1.created == info1.created
        assert restored_info1.project_name == info1.project_name
        assert restored_info1.amplifier_commit == info1.amplifier_commit

    def test_sandbox_state_from_dict_empty_sandboxes(self) -> None:
        """Test deserializing state with no sandboxes."""
        data = {"version": "1.0", "sandboxes": {}}

        state = SandboxState.from_dict(data)

        assert state.version == "1.0"
        assert state.sandboxes == {}

    def test_sandbox_state_from_dict_missing_sandboxes_key(self) -> None:
        """Test deserializing state without sandboxes key defaults to empty."""
        data = {"version": "1.0"}

        state = SandboxState.from_dict(data)

        assert state.version == "1.0"
        assert state.sandboxes == {}
