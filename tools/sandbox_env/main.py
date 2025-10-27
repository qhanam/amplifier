"""CLI interface for sandbox environment management."""

import logging
import sys
from pathlib import Path

import click

from .config import AMPLIFIER_REPO_URL
from .config import get_workspace_root
from .exceptions import SandboxError
from .models import SandboxConfig
from .sandbox_manager import SandboxManager
from .state_manager import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0", prog_name="sandbox-env")
def cli() -> None:
    """Manage isolated Amplifier sandbox environments."""
    pass


@cli.command()
@click.argument("name")
@click.argument("git_url")
@click.option(
    "--path",
    type=click.Path(file_okay=False, path_type=Path),
    help="Custom sandbox directory path (overrides --workspace)",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    help="Workspace root directory (default: /workspace)",
)
@click.option(
    "--repo-url",
    default=AMPLIFIER_REPO_URL,
    help="Amplifier repository URL",
)
def create(name: str, git_url: str, path: Path | None, workspace: Path | None, repo_url: str) -> None:
    """Create a new sandbox environment.

    NAME: Sandbox name (alphanumeric, hyphens, underscores)
    GIT_URL: Git URL of your project repository (e.g., git@github.com:user/repo.git)
    """
    try:
        # Set workspace root or use custom path
        if path:
            # Custom path specified - use it directly
            workspace_root = path.parent
            custom_sandbox_path = path
        else:
            # Use workspace root (default or specified)
            workspace_root = workspace or get_workspace_root()
            custom_sandbox_path = None

        # Create config
        config = SandboxConfig(
            name=name,
            git_url=git_url,
            amplifier_repo_url=repo_url,
            workspace_root=workspace_root,
            custom_sandbox_path=custom_sandbox_path,
        )

        # Create sandbox
        state_manager = StateManager(workspace_root=workspace_root)
        manager = SandboxManager(state_manager=state_manager)
        info = manager.create_sandbox(config)

        # Success message
        click.echo(f"✓ Sandbox '{name}' created successfully!")
        click.echo(f"  Location: {info.sandbox_path}")
        click.echo(f"  Project: {info.project_name}")
        click.echo(f"  Branch: {info.branch_name}")
        click.echo(f"  Amplifier commit: {info.amplifier_commit[:8]}")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"  1. cd {info.sandbox_path}")
        click.echo("  2. Start working on your feature!")

    except SandboxError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    help="Workspace root directory (default: /workspace)",
)
def remove(name: str, force: bool, workspace: Path | None) -> None:
    """Remove a sandbox environment.

    NAME: Sandbox name to remove
    """
    try:
        # Set workspace root
        workspace_root = workspace or get_workspace_root()

        # Confirm unless force
        if not force and not click.confirm(f"Remove sandbox '{name}'?"):
            click.echo("Cancelled.")
            return

        # Remove sandbox
        state_manager = StateManager(workspace_root=workspace_root)
        manager = SandboxManager(state_manager=state_manager)
        manager.remove_sandbox(name, force=force)

        click.echo(f"✓ Sandbox '{name}' removed successfully!")

    except SandboxError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    help="Workspace root directory (default: /workspace)",
)
def info(name: str, workspace: Path | None) -> None:
    """Show information about a sandbox.

    NAME: Sandbox name
    """
    try:
        # Set workspace root
        workspace_root = workspace or get_workspace_root()

        # Get sandbox info
        state_manager = StateManager(workspace_root=workspace_root)
        manager = SandboxManager(state_manager=state_manager)
        sandbox_info = manager.get_sandbox_info(name)

        # Display info
        click.echo(f"Sandbox: {sandbox_info.name}")
        click.echo(f"  Created: {sandbox_info.created.isoformat()}")
        click.echo(f"  Project: {sandbox_info.project_name}")
        click.echo(f"  Git URL: {sandbox_info.git_url}")
        click.echo(f"  Branch: {sandbox_info.branch_name}")
        click.echo(f"  Sandbox path: {sandbox_info.sandbox_path}")
        click.echo(f"  Amplifier commit: {sandbox_info.amplifier_commit[:8]}")

    except SandboxError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command(name="list")
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    help="Workspace root directory (default: /workspace)",
)
def list_sandboxes(workspace: Path | None) -> None:
    """List all sandbox environments."""
    try:
        # Set workspace root
        workspace_root = workspace or get_workspace_root()

        # List sandboxes
        state_manager = StateManager(workspace_root=workspace_root)
        manager = SandboxManager(state_manager=state_manager)
        sandboxes = manager.list_sandboxes()

        if not sandboxes:
            click.echo("No sandboxes found.")
            return

        # Display table
        click.echo(f"Found {len(sandboxes)} sandbox(es):\n")
        for sandbox_info in sandboxes:
            click.echo(f"  {sandbox_info.name}")
            click.echo(f"    Project: {sandbox_info.project_name}")
            click.echo(f"    Branch: {sandbox_info.branch_name}")
            click.echo(f"    Created: {sandbox_info.created.strftime('%Y-%m-%d %H:%M')}")
            click.echo()

    except SandboxError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
