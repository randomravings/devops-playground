# DevOps Tools - Examples

This folder contains example shell scripts demonstrating how to use the `dt` CLI commands to set up various DevOps environments.

## 🚀 Quick Start Examples

### Main Use Cases

Choose the setup that matches your needs:

**1. Bare Minimum Setup** - Clean slate for custom configuration

```bash
./examples/basic.sh
```

- Docker environment (Gitea + Jenkins)
- Admin users only
- No teams, repos, or additional config
- **Best for**: Starting from scratch with custom requirements

**2. Acme Organization Setup** - Complete working environment

```bash
./examples/acme_org.sh
```

- Acme organization with developers team
- Users: john, jane (team members)
- Repos: demo-app, demo-db, dbci-tools
- Branch protection and webhooks configured
- Jenkins CI/CD integration
- **Best for**: Realistic small-team development environment

### User-Specific Scripts

#### acme_user_local.sh

Creates a local workspace for a user to work with the Acme organization repositories. This script demonstrates how to clone repositories with user-specific credentials, organize them in a local workspace structure, and automatically initialize them with project templates if needed.

**Usage:**
```bash
./examples/acme_user_local.sh USERNAME REPO WORKSPACE_DIR
```

**Parameters:**
- `USERNAME` (required): Gitea username to use for cloning
- `REPO` (required): Repository name to clone (e.g., `demo-app`, `demo-db`)
- `WORKSPACE_DIR` (required): Base directory for local workspace (e.g., `~/Local`)

The script will organize repositories in the structure: `WORKSPACE_DIR/USERNAME/REPO`

**What it does:**
1. Validates that the user exists in the organization
2. Validates that the workspace base directory exists
3. Creates user-specific workspace directory if needed
4. Checks if repository has already been cloned
5. Clones the specified repository with user credentials
6. **Automatically initializes repository with template files if Jenkinsfile is not present:**
   - Checks for Jenkinsfile (marker file) in cloned repository
   - If not found, copies template files from `project_templates/{REPO}/`
   - Creates `feature-init` branch with copied files (ready for you to commit)
   - If found, skips initialization (repository already set up)

**Example:**
```bash
# Clone demo-app for user john to ~/Local
# If demo-app is empty, it will be initialized with template files
./examples/acme_user_local.sh john demo-app ~/Local

# Clone demo-db for user jane to ~/Projects
# If demo-db already has a Jenkinsfile, initialization is skipped
./examples/acme_user_local.sh jane demo-db ~/Projects
```

The repositories will be cloned to:
- `~/Local/john/demo-app`
- `~/Projects/jane/demo-db`

**Prerequisites:**
- Acme organization must be set up (run `acme_org.sh` first)
- The specified user must exist in the organization
- The base workspace directory must exist
- Assumes password is 'secret' for all users
- Project templates should exist in `project_templates/{REPO}/` for initialization

**Teardown** - Clean up everything

```bash
./examples/teardown.sh
```

## 📚 What These Scripts Demonstrate

The shell scripts show real-world usage patterns of the `dt` CLI:

### basic.sh

```bash
dt env up                                    # Start Docker with admin only
```

### acme_org.sh

```bash
dt env up                                    # Start Docker
dt git org acme --owner admin                # Create organization
dt git user john --password secret --org acme  # Create user
dt git team developers --org acme            # Create team
dt git add-member john --team developers --org acme  # Add to team
dt git repo demo-app --org acme              # Create repository
dt git protect demo-app --org acme --team developers  # Branch protection
dt git webhook                               # Setup webhook
dt ci creds gitea-credentials --username admin  # Jenkins credentials
dt ci org acme-folder --org acme --credentials gitea-credentials  # Jenkins org
```

### acme_user_local.sh

```bash
dt git clone demo-app --org acme --dest ~/Local/john  # Clone existing repo
# If Jenkinsfile not found, automatically initializes with template
# Copies from project_templates/demo-app/ to feature-init branch
# Files are staged and ready for you to review, commit, and push
```

### teardown.sh

```bash
dt env down                                  # Stop and remove all containers
```

## 🎯 Typical Workflow

```bash
# 1. Setup your environment
./examples/acme_org.sh

# 2. Clone repo for local work (automatically initializes if needed)
./examples/acme_user_local.sh john demo-app ~/Local

# 3. Review and commit template files (if initialized)
cd ~/Local/john/demo-app
git checkout feature-init  # Only if template was copied
git status                  # Review what was added
git add .
git commit -m "Initialize with template"
git push -u origin feature-init

# 4. Start developing!
# Make your changes...

# 5. Cleanup when done
./examples/teardown.sh
```

## 🔧 Creating Custom Setup Scripts

Start with the bare minimum and add your commands:

```bash
#!/usr/bin/env bash
set -e

source .venv/bin/activate

# Start with bare minimum
dt env up

# Add your custom configuration
dt git user myuser --password secret --org myorg
dt git org myorg --owner myuser
dt git repo myrepo --org myorg
dt ci creds my-creds --username myuser --password secret
dt ci org myorg-folder --org myorg --credentials my-creds

echo "✅ Custom setup complete!"
```

## 📝 Notes

- All scripts are idempotent - safe to run multiple times
- Docker must be running before executing scripts
- Scripts activate the virtual environment automatically
- Use `dt --help` to explore all available commands
- Check [CLI_SHORTCUTS.md](../CLI_SHORTCUTS.md) for quick reference

## 🆘 Troubleshooting

**Virtual environment not found:**

```bash
./env_setup.sh
```

**Containers already running:**

```bash
./examples/teardown.sh
./examples/acme_org.sh
```

**Permission denied:**

```bash
chmod +x examples/*.sh
```

## 📚 Further Reading

- [README.md](../README.md) - Main project documentation
- [CLI_SHORTCUTS.md](../CLI_SHORTCUTS.md) - CLI quick reference
- [QUICKSTART.md](../QUICKSTART.md) - Getting started guide
- [USAGE.md](../USAGE.md) - Detailed usage patterns
