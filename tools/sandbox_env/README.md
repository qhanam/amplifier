# Sandbox Environment Tool

A CLI tool for managing isolated Amplifier sandbox environments for concurrent feature development.

## What It Does

Creates isolated Amplifier workspaces where each sandbox is a complete Amplifier clone with your project as a git submodule. This enables:

- **Concurrent feature development** - Work on multiple features simultaneously
- **Complete context isolation** - Each sandbox is independent
- **Clean workflows** - Feature branches automatically created
- **Easy cleanup** - Remove entire sandbox with one command

## Quick Start

### Installation

```bash
cd tools/sandbox_env
make install
```

### Basic Usage

```bash
# From anywhere in the amplifier repository:
./tools/sandbox-env create my-feature git@github.com:user/my-project.git
./tools/sandbox-env list
./tools/sandbox-env info my-feature
./tools/sandbox-env remove my-feature

# Or from within tools/sandbox_env/ directory:
uv run python -m sandbox_env create my-feature git@github.com:user/my-project.git
uv run python -m sandbox_env list
```

## Commands

### create

Create a new sandbox environment.

```bash
python -m sandbox_env create NAME GIT_URL [OPTIONS]
```

**Arguments:**
- `NAME` - Sandbox name (alphanumeric, hyphens, underscores only)
- `GIT_URL` - Git URL of your project repository (e.g., git@github.com:user/repo.git)

**Options:**
- `--workspace PATH` - Custom workspace root (default: /workspace)
- `--repo-url URL` - Custom Amplifier repo URL

**Example:**
```bash
python -m sandbox_env create add-tags git@github.com:user/my-website.git
```

**What happens:**
1. Clones Amplifier to `/workspace/amplifier-sandbox.add-tags`
2. Adds your project as a git submodule using the git URL
3. Creates feature branch `feature/add-tags` in your project
4. Runs `make install` to set up the environment
5. Creates `SANDBOX.md` with metadata

### list

List all sandbox environments.

```bash
python -m sandbox_env list [OPTIONS]
```

**Options:**
- `--workspace PATH` - Custom workspace root (default: /workspace)

**Example output:**
```
Found 2 sandbox(es):

  add-tags
    Project: my-website
    Branch: feature/add-tags
    Created: 2025-01-24 10:30

  refactor-api
    Project: backend-service
    Branch: feature/refactor-api
    Created: 2025-01-24 14:15
```

### info

Show detailed information about a sandbox.

```bash
python -m sandbox_env info NAME [OPTIONS]
```

**Arguments:**
- `NAME` - Sandbox name

**Options:**
- `--workspace PATH` - Custom workspace root (default: /workspace)

**Example output:**
```
Sandbox: add-tags
  Created: 2025-01-24T10:30:00+00:00
  Project: my-website
  Git URL: git@github.com:user/my-website.git
  Branch: feature/add-tags
  Sandbox path: /workspace/amplifier-sandbox.add-tags
  Amplifier commit: abc123de
```

### remove

Remove a sandbox environment.

```bash
python -m sandbox_env remove NAME [OPTIONS]
```

**Arguments:**
- `NAME` - Sandbox name to remove

**Options:**
- `--force` - Skip confirmation prompt
- `--workspace PATH` - Custom workspace root (default: /workspace)

**Example:**
```bash
# With confirmation
python -m sandbox_env remove add-tags

# Without confirmation
python -m sandbox_env remove add-tags --force
```

## Architecture

### File Structure

```
tools/sandbox_env/
├── __init__.py              # Package marker
├── __main__.py              # Entry point (python -m sandbox_env)
├── main.py                  # CLI implementation with Click
├── config.py                # Configuration constants
├── exceptions.py            # Custom exception hierarchy
├── models.py                # Data models (SandboxConfig, SandboxInfo, SandboxState)
├── state_manager.py         # State persistence with file locking
├── sandbox_manager.py       # Core sandbox lifecycle operations
├── Makefile                 # Build targets
└── tests/
    ├── test_models.py       # Model tests (11 tests)
    ├── test_state_manager.py # State management tests (15 tests)
    ├── test_sandbox_manager.py # Sandbox lifecycle tests (17 tests)
    ├── test_main.py         # CLI tests (10 tests)
    └── test_integration.py  # Integration tests (2 tests)
```

### State Management

Sandboxes are tracked in `.sandbox-state.json` at the workspace root:

```json
{
  "version": "1.0",
  "sandboxes": {
    "add-tags": {
      "name": "add-tags",
      "created": "2025-01-24T10:30:00+00:00",
      "project_name": "my-website",
      "git_url": "git@github.com:user/my-website.git",
      "branch_name": "feature/add-tags",
      "sandbox_path": "/workspace/amplifier-sandbox.add-tags",
      "amplifier_commit": "abc123def456"
    }
  }
}
```

**Features:**
- Thread-safe with file locking (fcntl)
- Atomic writes (write to temp file, then rename)
- JSON format for human readability

### Data Models

**SandboxConfig** - Configuration for creating a sandbox:
- Validates sandbox name (alphanumeric, hyphens, underscores)
- Validates git URL is not empty
- Extracts project name from git URL
- Derives branch name: `feature/{name}`
- Derives sandbox path: `{workspace}/amplifier-sandbox.{name}`

**SandboxInfo** - Information about an existing sandbox:
- All configuration details
- Creation timestamp (UTC timezone)
- Amplifier commit hash
- Serialization to/from JSON

**SandboxState** - Complete state of all sandboxes:
- Version for future migrations
- Dictionary of sandbox name → SandboxInfo
- Empty state factory method

### Sandbox Manager

Core operations:

**create_sandbox():**
1. Validate configuration
2. Check for duplicate names
3. Clone Amplifier repository
4. Add project as git submodule
5. Create and checkout feature branch
6. Run `make install` in sandbox
7. Create `SANDBOX.md` metadata
8. Update state file
9. Return SandboxInfo

**remove_sandbox():**
1. Get sandbox info from state
2. Remove sandbox directory (if exists)
3. Update state file

**list_sandboxes():**
- Returns all sandboxes sorted by creation date (oldest first)

**get_sandbox_info():**
- Returns details for a specific sandbox

### Error Handling

Custom exceptions for clear error messages:

- `SandboxError` - Base exception
- `SandboxExistsError` - Duplicate sandbox name
- `SandboxNotFoundError` - Sandbox not found
- `InvalidProjectPathError` - Invalid project path
- `GitOperationError` - Git operation failed
- `StateFileError` - State file corruption or I/O error

All errors include helpful messages and exit with non-zero status codes.

## Testing

### Run All Tests

```bash
make test
```

### Run Unit Tests Only

```bash
make test-unit
```

### Run Integration Tests

```bash
make test-integration
```

**Note:** Integration tests require:
- Git installed
- Network access to clone Amplifier repo
- Sufficient disk space

Integration tests are automatically skipped if git is unavailable.

### Test Coverage

- **53 unit tests** - All passing
- **Test coverage** - 100% of modules
- **Mocked operations** - Git commands mocked for fast unit tests
- **Real git operations** - Integration tests use real git

## Development

### Requirements

- Python 3.11+
- uv (package manager)
- Git
- Click library

### Design Philosophy

Follows Amplifier's **ruthless simplicity** philosophy:

- **Flat structure** - No deep directory hierarchies
- **Minimal abstractions** - Direct, focused code
- **Standard library** - Uses Python logging, not custom amplifier logger
- **Thread-safe** - File locking for concurrent access
- **Atomic operations** - State writes are atomic
- **Clear errors** - Descriptive error messages
- **Well-tested** - Comprehensive test coverage

### Key Decisions

**Full clone per sandbox** (not shared Amplifier):
- Complete isolation
- Independent dependencies
- Simpler mental model
- Easy cleanup

**JSON state file** (not database):
- Simple, human-readable
- No external dependencies
- Easy to inspect/debug
- Sufficient for ~10-20 sandboxes

**Git submodules** (not worktrees):
- Standard git workflow
- Compatible with all git tools
- Well-understood by developers

### Adding Features

When extending this tool:

1. **Add tests first** - TDD approach
2. **Keep it simple** - Resist over-engineering
3. **Update docs** - Keep README in sync
4. **Follow patterns** - Match existing code style
5. **Run linting** - `make check` from project root

## Troubleshooting

### "Sandbox already exists"

A sandbox with that name is already registered. Use a different name or remove the existing sandbox:

```bash
python -m sandbox_env list
python -m sandbox_env remove old-sandbox-name
```

### "Git URL cannot be empty"

The git URL argument is required and must be a valid git URL:

```bash
# Bad
python -m sandbox_env create feat ""

# Good
python -m sandbox_env create feat git@github.com:user/repo.git
python -m sandbox_env create feat https://github.com/user/repo.git
```

### "Failed to clone Amplifier"

Check:
- Network connectivity
- Git is installed (`which git`)
- Repository URL is correct
- Sufficient disk space

### "Failed to add project as submodule"

This usually means the git URL is invalid or inaccessible. Verify:
- The git URL is correct
- You have access to the repository (SSH keys configured for git@ URLs)
- The repository exists
- Network connectivity

### State file corruption

If `.sandbox-state.json` becomes corrupted:

1. Back up the file
2. Manually fix the JSON
3. Or delete it (loses sandbox tracking, but sandboxes remain on disk)

### Sandbox directory exists but not in state

Manually add to state or remove the directory:

```bash
# Remove orphaned directory
rm -rf /workspace/amplifier-sandbox.orphaned-name
```

## Related Documentation

- [Workspace Pattern](../../docs/WORKSPACE_PATTERN.md) - Architecture context
- [Sandbox Guide](../../docs/SANDBOX_GUIDE.md) - User guide for sandboxes
- [Implementation Philosophy](../../ai_context/IMPLEMENTATION_PHILOSOPHY.md) - Design principles

## Version

Current version: 1.0.0

## License

Same as Amplifier project.
