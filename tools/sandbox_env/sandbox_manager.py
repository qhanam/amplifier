"""Core sandbox lifecycle operations."""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .exceptions import GitOperationError
from .exceptions import SandboxExistsError
from .exceptions import SandboxNotFoundError
from .models import SandboxConfig
from .models import SandboxInfo
from .state_manager import StateManager

logger = logging.getLogger(__name__)

# Find required executables at module import time
_GIT_EXECUTABLE = shutil.which("git")
if _GIT_EXECUTABLE is None:
    raise RuntimeError("git executable not found in PATH. Please install git.")

_MAKE_EXECUTABLE = shutil.which("make")
if _MAKE_EXECUTABLE is None:
    raise RuntimeError("make executable not found in PATH. Please install make.")


class SandboxManager:
    """Manages sandbox lifecycle operations.

    Creates and manages isolated Amplifier workspaces for concurrent
    feature development with complete context isolation.
    """

    def __init__(
        self: "SandboxManager",
        state_manager: StateManager | None = None,
    ) -> None:
        """Initialize with state manager.

        Args:
            state_manager: StateManager instance (defaults to new instance)
        """
        self.state = state_manager or StateManager()

    def create_sandbox(
        self: "SandboxManager",
        config: SandboxConfig,
    ) -> SandboxInfo:
        """Create a new sandbox environment.

        Steps:
        1. Validate configuration
        2. Check sandbox doesn't exist
        3. Clone Amplifier
        4. Add project as submodule
        5. Create feature branch
        6. Run make install
        7. Create SANDBOX.md
        8. Update state
        9. Return SandboxInfo

        Args:
            config: SandboxConfig with creation parameters

        Returns:
            SandboxInfo for the created sandbox

        Raises:
            SandboxExistsError: If name already used
            InvalidProjectPathError: If project path invalid
            GitOperationError: If git operations fail
        """
        logger.info(f"Creating sandbox: {config.name}")

        # Step 1: Validate configuration
        config.validate()

        # Step 2: Check sandbox doesn't already exist
        if self.state.sandbox_exists(config.name):
            raise SandboxExistsError(
                f"Sandbox '{config.name}' already exists. Use a different name or remove the existing sandbox first."
            )

        # Record creation time
        created_time = datetime.now()

        try:
            # Step 3: Clone Amplifier repository
            logger.info(f"Cloning Amplifier to {config.sandbox_path}")
            commit_hash = self._clone_amplifier(
                target_dir=config.sandbox_path,
                repo_url=config.amplifier_repo_url,
            )

            # Step 4: Add project as git submodule
            logger.info(f"Adding {config.project_name} as submodule")
            self._add_project_submodule(
                sandbox_dir=config.sandbox_path,
                git_url=config.git_url,
                project_name=config.project_name,
            )

            # Step 5: Create and checkout feature branch
            logger.info(f"Creating feature branch: {config.branch_name}")
            project_dir = config.sandbox_path / config.project_name
            self._create_feature_branch(
                project_dir=project_dir,
                branch_name=config.branch_name,
            )

            # Step 6: Run make install
            logger.info("Running make install in sandbox")
            self._run_make_install(sandbox_dir=config.sandbox_path)

            # Step 7: Create SANDBOX.md metadata file
            logger.info("Creating sandbox metadata file")
            self._create_sandbox_metadata(
                sandbox_dir=config.sandbox_path,
                config=config,
                commit_hash=commit_hash,
                created_time=created_time,
            )

            # Step 8: Create SandboxInfo
            info = SandboxInfo(
                name=config.name,
                created=created_time,
                project_name=config.project_name,
                git_url=config.git_url,
                branch_name=config.branch_name,
                sandbox_path=config.sandbox_path,
                amplifier_commit=commit_hash,
            )

            # Step 9: Update state
            self.state.add_sandbox(info)

            logger.info(f"Sandbox '{config.name}' created successfully")
            return info

        except Exception as e:
            # Clean up on failure
            logger.error(f"Sandbox creation failed: {e}")
            if config.sandbox_path.exists():
                logger.info("Cleaning up failed sandbox directory")
                shutil.rmtree(config.sandbox_path)
            raise

    def remove_sandbox(
        self: "SandboxManager",
        name: str,
        force: bool = False,
    ) -> None:
        """Remove sandbox and clean up.

        Args:
            name: Sandbox name
            force: Skip confirmation if True (reserved for future use)

        Raises:
            SandboxNotFoundError: If sandbox doesn't exist
        """
        logger.info(f"Removing sandbox: {name}")

        # Get sandbox info
        info = self.state.get_sandbox(name)
        if info is None:
            raise SandboxNotFoundError(f"Sandbox '{name}' not found. Use 'list' command to see available sandboxes.")

        # Remove directory
        if info.sandbox_path.exists():
            logger.info(f"Deleting sandbox directory: {info.sandbox_path}")
            shutil.rmtree(info.sandbox_path)
        else:
            logger.warning(f"Sandbox directory not found: {info.sandbox_path}")

        # Remove from state
        self.state.remove_sandbox(name)

        logger.info(f"Sandbox '{name}' removed successfully")

    def get_sandbox_info(self: "SandboxManager", name: str) -> SandboxInfo:
        """Get information about a sandbox.

        Args:
            name: Sandbox name

        Returns:
            SandboxInfo for the sandbox

        Raises:
            SandboxNotFoundError: If sandbox doesn't exist
        """
        info = self.state.get_sandbox(name)
        if info is None:
            raise SandboxNotFoundError(f"Sandbox '{name}' not found")
        return info

    def list_sandboxes(self: "SandboxManager") -> list[SandboxInfo]:
        """List all sandboxes.

        Returns:
            List of SandboxInfo sorted by creation date
        """
        return self.state.list_sandboxes()

    def _clone_amplifier(
        self: "SandboxManager",
        target_dir: Path,
        repo_url: str,
    ) -> str:
        """Clone Amplifier repo, return commit hash.

        Args:
            target_dir: Directory to clone into
            repo_url: Git repository URL

        Returns:
            Git commit hash of the cloned repository

        Raises:
            GitOperationError: If clone fails
        """
        # Ensure target directory doesn't exist
        if target_dir.exists():
            raise GitOperationError(f"Target directory already exists: {target_dir}")

        # Ensure parent directory exists
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # Clone repository
        self._run_command(
            cmd=["git", "clone", repo_url, str(target_dir)],
            cwd=target_dir.parent,
            error_msg=f"Failed to clone Amplifier from {repo_url}",
        )

        # Get commit hash
        commit_hash = self._run_command(
            cmd=["git", "rev-parse", "HEAD"],
            cwd=target_dir,
            error_msg="Failed to get commit hash",
        ).strip()

        return commit_hash

    def _add_project_submodule(
        self: "SandboxManager",
        sandbox_dir: Path,
        git_url: str,
        project_name: str,
    ) -> None:
        """Add project as git submodule using its git URL.

        Args:
            sandbox_dir: Sandbox directory
            git_url: Git URL of project repository
            project_name: Name for submodule directory

        Raises:
            GitOperationError: If submodule add fails
        """
        # Add as submodule using git URL
        self._run_command(
            cmd=["git", "submodule", "add", git_url, project_name],
            cwd=sandbox_dir,
            error_msg=f"Failed to add {project_name} as submodule",
        )

        # Initialize and update submodule
        self._run_command(
            cmd=["git", "submodule", "update", "--init", "--recursive"],
            cwd=sandbox_dir,
            error_msg="Failed to initialize submodule",
        )

    def _create_feature_branch(
        self: "SandboxManager",
        project_dir: Path,
        branch_name: str,
    ) -> None:
        """Create and checkout feature branch.

        Args:
            project_dir: Project directory inside sandbox
            branch_name: Feature branch name

        Raises:
            GitOperationError: If branch creation fails
        """
        # Create and checkout branch
        self._run_command(
            cmd=["git", "checkout", "-b", branch_name],
            cwd=project_dir,
            error_msg=f"Failed to create branch {branch_name}",
        )

    def _run_make_install(self: "SandboxManager", sandbox_dir: Path) -> None:
        """Run make install in sandbox.

        Args:
            sandbox_dir: Sandbox directory

        Raises:
            GitOperationError: If make install fails
        """
        self._run_command(
            cmd=["make", "install"],
            cwd=sandbox_dir,
            error_msg="Failed to run 'make install'",
        )

    def _create_sandbox_metadata(
        self: "SandboxManager",
        sandbox_dir: Path,
        config: SandboxConfig,
        commit_hash: str,
        created_time: datetime,
    ) -> None:
        """Create SANDBOX.md from template.

        Args:
            sandbox_dir: Sandbox directory
            config: Sandbox configuration
            commit_hash: Git commit hash
            created_time: Creation timestamp

        Raises:
            IOError: If template not found or metadata cannot be written
        """
        # Find template
        template_path = Path(__file__).parent / "SANDBOX.md.template"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Read template
        template_content = template_path.read_text()

        # Replace placeholders
        metadata_content = template_content.format(
            feature_name=config.name,
            git_url=config.git_url,
            branch_name=config.branch_name,
            created_at=created_time.isoformat(),
            sandbox_dir=str(sandbox_dir),
            project_name=config.project_name,
            status="Active",
        )

        # Write metadata file
        metadata_file = sandbox_dir / "SANDBOX.md"
        metadata_file.write_text(metadata_content)

    def _run_command(
        self: "SandboxManager",
        cmd: list[str],
        cwd: Path,
        error_msg: str,
    ) -> str:
        """Run shell command with error handling.

        Args:
            cmd: Command and arguments as list
            cwd: Working directory
            error_msg: Error message prefix

        Returns:
            Command stdout output

        Raises:
            GitOperationError: If command fails
        """
        # Replace commands with absolute paths if needed
        if cmd[0] == "git":
            assert _GIT_EXECUTABLE is not None  # Already checked at module import
            cmd = [_GIT_EXECUTABLE] + cmd[1:]
        elif cmd[0] == "make":
            assert _MAKE_EXECUTABLE is not None  # Already checked at module import
            cmd = [_MAKE_EXECUTABLE] + cmd[1:]

        logger.debug(f"Running command: {' '.join(cmd)} in {cwd}")
        logger.debug(f"_GIT_EXECUTABLE={_GIT_EXECUTABLE}, _MAKE_EXECUTABLE={_MAKE_EXECUTABLE}")

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_detail = f"{error_msg}\nCommand: {' '.join(cmd)}\nError: {e.stderr}"
            logger.error(error_detail)
            raise GitOperationError(error_detail) from e
        except FileNotFoundError as e:
            error_detail = (
                f"{error_msg}\nCommand not found: {cmd[0]}\nOriginal error: {e}\nCommand was: {cmd}\nCWD: {cwd}"
            )
            logger.error(error_detail)
            raise GitOperationError(error_detail) from e
