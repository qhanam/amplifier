# Sandboxed Feature Development Guide

**Develop multiple features concurrently with complete isolation and security.**

Amplifier's sandbox system creates isolated development environments where you can work on different features simultaneously without context poisoning or security risks. Each sandbox is a complete Amplifier workspace with your project as a submodule, running in a Docker container for security.

## Why Use Sandboxes?

- **Concurrent Development**: Work on multiple features at the same time (e.g., adding tags + improving styling)
- **Context Isolation**: Each Claude session is completely independent—no context poisoning
- **Security Protection**: Docker container protects your host machine from prompt injection attacks
- **Clean History**: Each feature gets its own branch and commits
- **Risk-Free Experimentation**: Test ideas without affecting your main workspace

## Quick Start

```bash
# 1. Start Docker environment (one-time setup)
docker-compose up -d
docker exec -it amplifier-dev bash

# 2. Create isolated sandboxes for different features
make sandbox-create /mnt/projects/my-website add-tags
make sandbox-create /mnt/projects/my-website improve-styling

# 3. Work on feature A (isolated Claude session)
cd /workspace/amplifier-sandbox.add-tags
claude  # Complete context isolation

# 4. Switch to feature B (different isolated session)
cd /workspace/amplifier-sandbox.improve-styling
claude  # No knowledge of feature A—clean context!
```

## Complete Workflow

### Prerequisites

- Docker and docker-compose installed
- Your project repository accessible from the Docker container
- Git configured with your credentials

### 1. Initial Docker Setup (One-Time)

Start the Amplifier development container:

```bash
# From your amplifier directory on the host
docker-compose up -d

# Verify container is running
docker ps | grep amplifier-dev

# Enter the container
docker exec -it amplifier-dev bash
```

**What this does:**
- Starts a Docker container with resource limits (4 CPU, 8GB RAM, 50GB disk)
- Mounts your projects directory at `/mnt/projects`
- Creates persistent workspace at `/workspace`
- Provides filesystem isolation from your host machine

### 2. Create a Sandbox

From inside the container:

```bash
make sandbox-create PROJECT_PATH FEATURE_NAME
```

**Example:**
```bash
make sandbox-create /mnt/projects/my-website add-tags
```

**What this creates:**
- `/workspace/amplifier-sandbox.add-tags/` - Full Amplifier workspace clone
- `/workspace/amplifier-sandbox.add-tags/my-website/` - Your project as a submodule
- Feature branch: `feature/add-tags` in your project
- Metadata file: `/workspace/amplifier-sandbox.add-tags/SANDBOX.md`

**The command:**
1. Clones a fresh Amplifier workspace into `/workspace/amplifier-sandbox.{feature-name}/`
2. Adds your project as a git submodule
3. Creates and checks out a new feature branch
4. Initializes the workspace with `make install`
5. Records sandbox metadata for tracking

### 3. Work in the Sandbox

Navigate to your sandbox and start developing:

```bash
cd /workspace/amplifier-sandbox.add-tags
source .venv/bin/activate
claude
```

**Inside Claude:**
- You have a completely fresh context—no knowledge of other sandboxes
- Your project is at `my-website/` within this workspace
- Changes are isolated to this feature branch
- Use Amplifier's full toolkit (agents, slash commands, etc.)

### 4. Develop Your Feature

Work normally with Claude Code:

```bash
# Example workflow inside Claude session
cd my-website/
# Make your changes with Claude
# Test your changes
# Commit your work
```

**Best practices:**
- Commit frequently within the sandbox
- Test thoroughly before merging
- Use descriptive commit messages
- Keep feature scope focused

### 5. Exit and Finalize

When your feature is complete:

```bash
# Exit Claude (Ctrl+D or /exit)
cd /workspace/amplifier-sandbox.add-tags/my-website

# Review your changes
git log
git diff origin/main

# Push your feature branch to origin
git push -u origin feature/add-tags

# Create a pull request (if needed)
gh pr create --title "Add tags feature" --body "Description..."
```

### 6. Clean Up (Optional)

List active sandboxes:

```bash
make sandbox-list
```

Remove a sandbox when done:

```bash
make sandbox-rm add-tags
```

**Warning:** This permanently deletes the sandbox workspace. Make sure you've pushed all changes to your remote repository first.

## Working with Multiple Sandboxes

The power of sandboxes is concurrent development. Here's a typical workflow:

```bash
# Create two sandboxes for different features
make sandbox-create /mnt/projects/my-website add-tags
make sandbox-create /mnt/projects/my-website improve-styling

# Morning: Work on tags feature
cd /workspace/amplifier-sandbox.add-tags
claude
# ... develop tags feature ...
# Exit Claude when done

# Afternoon: Work on styling feature
cd /workspace/amplifier-sandbox.improve-styling
claude
# ... develop styling improvements ...
# Exit Claude when done
```

**Key insight:** Each Claude session is completely independent. The styling session has no knowledge of the tags work, preventing context contamination and allowing you to focus on one feature at a time.

## Security Features

### Level 1 Security (Current)

The sandbox system provides basic protection through Docker containerization:

**Resource Limits:**
- 4 CPU cores maximum
- 8GB RAM maximum
- 50GB disk space maximum

**Filesystem Isolation:**
- Container has limited access to host filesystem
- Projects mounted read-only at `/mnt/projects`
- Workspace is container-specific at `/workspace`
- Protects against accidental host modifications

**What this protects against:**
- Runaway processes consuming all resources
- Accidental file operations on host system
- Some basic prompt injection attacks that try to access host

**What this does NOT protect against:**
- Sophisticated prompt injection attacks
- Intentional malicious code execution
- Network-based attacks
- Privilege escalation attempts

### Security Best Practices

1. **Review generated code** before committing
2. **Use separate API keys** for sandbox environments
3. **Monitor resource usage** via `docker stats amplifier-dev`
4. **Keep secrets out of repos** - use environment variables
5. **Regular updates** - keep Docker images and dependencies current

### Future Security Enhancements

Potential improvements for higher security needs:

- **Level 2**: User namespacing, network policies, seccomp profiles
- **Level 3**: gVisor or Kata Containers for VM-level isolation
- **Advanced**: Separate containers per sandbox, ephemeral environments

See `ai_working/ddd/plan.md` for detailed security architecture.

## Docker Environment Management

### Starting and Stopping

```bash
# Start container (from host)
docker-compose up -d

# Stop container
docker-compose stop

# Stop and remove container (preserves workspace volume)
docker-compose down

# Completely remove everything including workspace
docker-compose down -v  # ⚠️  DESTROYS ALL SANDBOXES
```

### Accessing the Container

```bash
# Primary method
docker exec -it amplifier-dev bash

# Alternative: attach to running container
docker attach amplifier-dev  # Ctrl+P, Ctrl+Q to detach
```

### Checking Container Status

```bash
# View container status
docker ps -a | grep amplifier-dev

# View resource usage
docker stats amplifier-dev

# View logs
docker logs amplifier-dev
```

### Persistence

**What persists across container restarts:**
- All sandboxes in `/workspace`
- Installed dependencies in `.venv`
- Git configurations
- Claude Code history (if stored in workspace)

**What does NOT persist:**
- Running processes
- Shell session state
- Temporary files in `/tmp`

## Troubleshooting

### Sandbox Creation Fails

**Problem:** `make sandbox-create` fails with git errors

**Solutions:**
1. Verify git credentials are configured in container:
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your@email.com"
   ```
2. Check SSH keys are available:
   ```bash
   ssh-add -l
   ```
3. Verify project path is accessible:
   ```bash
   ls -la /mnt/projects/my-website
   ```

### Container Won't Start

**Problem:** `docker-compose up -d` fails

**Solutions:**
1. Check Docker daemon is running:
   ```bash
   docker ps
   ```
2. Review error logs:
   ```bash
   docker-compose logs
   ```
3. Rebuild container:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Out of Space in Container

**Problem:** Container reports disk space errors

**Solutions:**
1. Check disk usage:
   ```bash
   df -h /workspace
   ```
2. Remove unused sandboxes:
   ```bash
   make sandbox-list
   make sandbox-rm old-feature
   ```
3. Clean up Docker:
   ```bash
   # From host
   docker system prune -a
   ```

### Claude Session Issues

**Problem:** Claude Code doesn't start in sandbox

**Solutions:**
1. Verify virtual environment is activated:
   ```bash
   which claude
   # Should show: /workspace/amplifier-sandbox.feature/.venv/bin/claude
   ```
2. Reinstall dependencies:
   ```bash
   cd /workspace/amplifier-sandbox.feature
   make install
   ```
3. Check Claude Code installation:
   ```bash
   claude --version
   ```

### Git Submodule Issues

**Problem:** Project submodule shows errors or uncommitted changes

**Solutions:**
1. Update submodule:
   ```bash
   cd /workspace/amplifier-sandbox.feature
   git submodule update --remote my-website
   ```
2. Check submodule status:
   ```bash
   git submodule status
   ```
3. Reset submodule if needed:
   ```bash
   git submodule deinit my-website
   git submodule update --init my-website
   ```

## Advanced Usage

### Custom Makefile Targets

Add project-specific setup to sandboxes by customizing the Makefile:

```makefile
# Example: Add database setup
sandbox-create-with-db: sandbox-create
	cd $(SANDBOX_DIR)/my-website && ./setup-db.sh
```

### Sharing Sandboxes

To work on the same feature from different machines:

```bash
# Machine 1: Create and push
make sandbox-create /mnt/projects/my-website feature-x
cd /workspace/amplifier-sandbox.feature-x/my-website
git push -u origin feature/feature-x

# Machine 2: Create and pull
make sandbox-create /mnt/projects/my-website feature-x
cd /workspace/amplifier-sandbox.feature-x/my-website
git pull origin feature/feature-x
```

**Note:** Each machine has its own Claude session, so context isn't shared.

### Environment Variables

Pass environment variables to sandboxes via docker-compose:

```yaml
# docker-compose.yml
services:
  amplifier-dev:
    environment:
      - API_KEY=${API_KEY}
      - DEBUG=true
```

### Volume Mounting

Mount additional directories for data or tools:

```yaml
# docker-compose.yml
services:
  amplifier-dev:
    volumes:
      - ./projects:/mnt/projects:ro
      - ./data:/mnt/data:rw
      - workspace:/workspace
```

### Multiple Isolated Containers

**Use case**: Separate sensitive/private projects from untrusted/third-party repositories for enhanced security.

All sandboxes within a single Docker container share resources and filesystem access. For projects with different trust levels, create completely isolated containers.

#### Why Multiple Containers?

**Single container isolation** (default):
- Sandboxes share CPU, memory, disk within one container
- Context isolation only (separate Claude sessions)
- Sandboxes could access each other's files
- Protects host, but not sandboxes from each other

**Multiple container isolation** (advanced):
- Complete filesystem separation between containers
- Independent resource limits per container
- Separate network namespaces
- Different security configurations per trust level

#### Setup Example

Separate containers for private vs untrusted projects:

```bash
# Directory structure
~/amplifier/              # Private/sensitive projects
~/amplifier-untrusted/    # Third-party/untrusted projects
```

**Step 1: Create separate Amplifier directories**

```bash
# Keep existing setup for private work
cd ~/amplifier

# Clone for untrusted work
cp -r ~/amplifier ~/amplifier-untrusted
cd ~/amplifier-untrusted
```

**Step 2: Customize docker-compose.yml**

Edit `~/amplifier-untrusted/docker-compose.yml`:

```yaml
services:
  amplifier-dev-untrusted:  # Different container name
    build:
      context: .
      dockerfile: Dockerfile
    container_name: amplifier-dev-untrusted

    volumes:
      # Different projects directory
      - ./projects-untrusted:/mnt/projects:ro

      # Different workspace volume
      - workspace-untrusted:/workspace

      # NO sensitive credentials
      # (no SSH keys, limited API keys, etc.)

    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_SANDBOX}

    # Optionally: Reduced resources for untrusted work
    deploy:
      resources:
        limits:
          cpus: '2'      # Half resources
          memory: 4G

volumes:
  workspace-untrusted:  # Unique volume name
    driver: local
```

**Step 3: Run both containers**

```bash
# Terminal 1: Private projects
cd ~/amplifier
docker-compose up -d
docker exec -it amplifier-dev bash

# Terminal 2: Untrusted projects
cd ~/amplifier-untrusted
docker-compose up -d
docker exec -it amplifier-dev-untrusted bash
```

**Step 4: Work in isolated environments**

```bash
# In amplifier-dev (private - full access)
make sandbox-create /mnt/projects/my-private-app add-auth
cd /workspace/amplifier-sandbox.add-auth
claude

# In amplifier-dev-untrusted (restricted)
make sandbox-create /mnt/projects/third-party-lib test-feature
cd /workspace/amplifier-sandbox.test-feature
claude
```

#### Security Best Practices

Configure containers with different security profiles:

**Private container** (full trust):
```yaml
volumes:
  - ~/.ssh:/root/.ssh:ro              # SSH keys available
  - ~/.gitconfig:/root/.gitconfig:ro  # Git config
environment:
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}  # Production key
```

**Untrusted container** (restricted):
```yaml
volumes:
  # NO SSH keys
  # NO git config
  - ./projects-untrusted:/mnt/projects:ro
environment:
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_LIMITED}  # Separate/limited key
```

#### Resource Planning

Each container reserves configured resources:

**Example on 16GB RAM machine**:
- Private container: 8GB RAM limit
- Untrusted container: 4GB RAM limit
- Total reserved: 12GB (4GB remains for host)

Containers only use resources when active, but limits are enforced.

#### Convention over Configuration

This approach follows **convention over configuration**:
- Standard directory structure (`~/amplifier/`, `~/amplifier-untrusted/`)
- Predictable container names (`amplifier-dev`, `amplifier-dev-untrusted`)
- Consistent volume naming (`workspace`, `workspace-untrusted`)
- Same commands work in all containers (`make sandbox-create`)

No special configuration needed - just copy the directory and customize the container name.

## Comparison with Other Patterns

### Sandboxes vs Worktrees

**Worktrees** (docs/WORKTREE_GUIDE.md):
- Multiple branches in the same repo
- Shared git history and configuration
- Same Claude session context
- Fast branch switching
- Best for: Quick experiments, comparing implementations

**Sandboxes** (this guide):
- Complete workspace isolation
- Independent Claude sessions
- Separate git configurations
- Full feature development environments
- Best for: Concurrent features, context isolation, security

### Sandboxes vs Workspace Pattern

**Workspace Pattern** (docs/WORKSPACE_PATTERN.md):
- Project as submodule in Amplifier
- Persistent context via AGENTS.md
- Single development environment
- Best for: Long-term projects, team collaboration

**Sandboxes**:
- Temporary feature-specific workspaces
- Fresh context per feature
- Multiple concurrent environments
- Best for: Feature development, experimentation

## Best Practices

### When to Use Sandboxes

✅ **Use sandboxes for:**
- Developing multiple features concurrently
- Risky or experimental changes
- Working with untrusted prompts or code
- Learning new patterns without affecting main workspace
- Testing breaking changes
- Collaborating on features with different contexts

❌ **Don't use sandboxes for:**
- Quick bug fixes (use worktrees instead)
- Simple documentation updates
- Single-file changes
- When you need shared context across features

### Feature Scope

Keep features focused:
- ✅ "Add user authentication"
- ✅ "Improve homepage styling"
- ✅ "Implement caching layer"
- ❌ "Rewrite entire application" (too broad)
- ❌ "Fix typo" (too small, use worktree)

### Naming Conventions

Use descriptive, kebab-case feature names:
- ✅ `add-user-auth`
- ✅ `improve-homepage-styling`
- ✅ `fix-login-bug`
- ❌ `feature1` (not descriptive)
- ❌ `new_feature` (use kebab-case)

### Cleanup Strategy

Regularly clean up completed sandboxes:

```bash
# Weekly cleanup routine
make sandbox-list
# Review list and remove merged features
make sandbox-rm feature-name-1
make sandbox-rm feature-name-2
```

### Resource Management

Monitor and manage Docker resources:

```bash
# Check container resource usage
docker stats amplifier-dev

# Check disk usage
docker exec -it amplifier-dev df -h /workspace

# Prune unused Docker resources
docker system prune -a
```

## Related Documentation

- [Workspace Pattern Guide](WORKSPACE_PATTERN.md) - Long-term project setup
- [Worktree Guide](WORKTREE_GUIDE.md) - Quick parallel development
- [Document-Driven Development](document_driven_development/) - DDD methodology
- [The Amplifier Way](THIS_IS_THE_WAY.md) - Best practices and tips

## Developer Documentation

For implementation details and contribution guidelines, see:
- [tools/sandbox_env/README.md](../tools/sandbox_env/README.md) - Developer documentation
- [ai_working/ddd/plan.md](../ai_working/ddd/plan.md) - Complete implementation plan
