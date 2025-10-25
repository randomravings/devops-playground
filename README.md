# DevOps Tools - Python Library

A Python library for managing local DevOps environments with Docker, Gitea, and Jenkins. This replaces the shell scripts in `scripts/` with a modern, type-safe, and testable Python package.

## 🚀 Quick Start

### 1. Setup (One-time)

```bash
./env_setup.sh
```

This creates a virtual environment and installs all dependencies.

### 2. Run Example

```bash
source .venv/bin/activate
python examples/full_setup.py
```

This sets up a complete environment with:

- Gitea server (port 3000) with users, organizations, and repositories
- Jenkins server (port 8080) with credentials and organization folder
- Example projects (Maven, PostgreSQL, dbci-tools)

### 3. Access Services

- **Gitea**: <http://localhost:3000> (admin/secret)
- **Jenkins**: <http://localhost:8080> (admin/secret)

### 4. Teardown

```bash
python examples/teardown.py
```

## 📦 What's Included

### Core Python Package (`devops_tools/`)

- **config.py** - Configuration management with environment variables
- **utils.py** - HTTP, Docker, and Git utilities
- **env.py** - Environment lifecycle (setup/teardown Docker services)
- **gitea.py** - Gitea operations (users, orgs, teams, repos, webhooks)
- **jenkins.py** - Jenkins operations (credentials, organizations, jobs)
- **project.py** - Project initialization (Maven, PostgreSQL, dbci-tools)
- **cli.py** - Command-line interface with Click

### Scripts

- **env_setup.sh** - Create virtual environment and install package
- **env_cleanup.sh** - Remove virtual environment and build artifacts
- **examples/** - Example scripts demonstrating various use cases

### Documentation

- **QUICKSTART.md** - CLI command reference
- **USAGE.md** - Detailed usage patterns and workflows
- **MIGRATION_SUMMARY.md** - Migration guide from shell scripts

### Infrastructure

- **docker/** - Docker Compose and Jenkins configuration
- **templates/** - Configuration templates for Gitea and Jenkins
- **project_templates/** - Example projects (Maven, PostgreSQL, dbci-tools)
- **examples/** - Example scripts showing different use cases
- **scripts/** - Original shell scripts (deprecated - use Python library instead)
- **tests/** - Test scripts

## 💡 Usage Patterns

### Pattern 1: Direct Execution

Activate virtual environment once, run multiple scripts:

```bash
source .venv/bin/activate           # Activate venv
python examples/full_setup.py       # Full setup
python examples/teardown.py         # Clean teardown
devops-tools --help                 # Use CLI
deactivate                          # Exit venv
```

### Pattern 2: As a Library

```bash
source venv/bin/activate
devops-tools environment setup
devops-tools git create-user alice --password secret --org acme
devops-tools ci create-credentials alice-creds --username alice --password secret
devops-tools environment teardown
```

### Pattern 4: Python Library

```python
from devops_tools import env, gitea, jenkins, project

# Setup environment
env.setup()

# Create Gitea resources
gitea.create_user("alice", "secret", "acme")
gitea.create_org("acme")
gitea.create_repo("acme", "my-project", "alice")

# Create Jenkins credentials
jenkins.create_credentials("alice-creds", "alice", "secret")
jenkins.create_org("acme", "alice-creds")

# Initialize a project
repo_path = gitea.clone_repo("acme", "my-project")
project.init_maven(repo_path)
project.init_commit(repo_path, "Initial commit")

# Teardown
env.teardown()
```

## 📚 API Reference

### Environment (`devops_tools.env`)

```python
env.setup()                  # Start Docker services (Gitea, Jenkins)
env.teardown()               # Stop and remove all services
```

### Gitea (`devops_tools.gitea`)

```python
gitea.create_user(username, password, org)
gitea.create_org(org)
gitea.create_team(org, team, permission="write")
gitea.add_team_members(org, team, usernames)
gitea.create_repo(org, repo, owner)
gitea.setup_branch_protection(org, repo, branch="main")
gitea.clone_repo(org, repo, destination=None)
gitea.setup_default_webhook(org, repo)
```

### Jenkins (`devops_tools.jenkins`)

```python
jenkins.create_credentials(cred_id, username, password)
jenkins.create_org(org, cred_id)
jenkins.job_exists(job_name)
jenkins.get_credential_name(username)
```

### Project (`devops_tools.project`)

```python
project.init_maven(repo_path, group_id="acme", artifact_id="app")
project.init_postgres(repo_path)
project.init_dbci_tools(repo_path)
project.init_commit(repo_path, message)
```

### Configuration (`devops_tools.config`)

```python
from devops_tools.config import get_config

config = get_config()
print(config.gitea_url)      # http://localhost:3000
print(config.jenkins_url)    # http://localhost:8080
print(config.docker_compose) # Path to docker-compose.yml
```

## ⚙️ Configuration

All configuration uses sensible defaults - no setup required!

**Default settings:**

```bash
# Environment
DOCKER_ENV_NAME=devops-env

# Gitea
GITEA_PORT=3000
GITEA_DEFAULT_ORG=acme
GITEA_ADMIN_USER=admin
GITEA_ADMIN_PASSWORD=secret
GITEA_INTERNAL_URL=http://gitea:3000
GITEA_ADVERTISED_URL=http://localhost:3000

# Jenkins
JENKINS_ADMIN_USER=admin
JENKINS_ADMIN_PASSWORD=secret
```

To customize settings, set environment variables before running:

```bash
export GITEA_PORT=3001
export GITEA_DEFAULT_ORG=mycompany
source .venv/bin/activate
python examples/full_setup.py
```

## 🛠️ Requirements

- Python 3.8+
- Docker and Docker Compose
- Git

### Python Dependencies

All automatically installed by `env_setup.sh`:

- click >= 8.0.0
- requests >= 2.28.0
- docker >= 6.0.0
- python-dotenv >= 1.0.0

## 📖 CLI Commands

### Environment

```bash
devops-tools environment setup     # Setup Docker environment
devops-tools environment teardown  # Teardown environment
```

### Git (Gitea)

```bash
devops-tools git create-user <username>
devops-tools git create-org <org>
devops-tools git create-team <org> <team>
devops-tools git add-team-member <org> <team> <username>
devops-tools git create-repo <org> <repo>
devops-tools git branch-protection <org> <repo>
devops-tools git clone <org> <repo>
devops-tools git setup-webhook <org> <repo>
```

### CI (Jenkins)

```bash
devops-tools ci create-credentials <cred-id>
devops-tools ci create-org <org>
devops-tools ci job-exists <job-name>
```

### Projects

```bash
devops-tools projects init-maven <path>
devops-tools projects init-postgres <path>
devops-tools projects init-dbci-tools <path>
devops-tools projects commit <path>
```

## 🎓 Examples

The `examples/` folder contains various example scripts:

- **[full_setup.py](examples/full_setup.py)** - Complete environment setup
- **[teardown.py](examples/teardown.py)** - Clean teardown
- **[gitea_simple.py](examples/gitea_simple.py)** - Simple Gitea setup
- **[gitea_team_workflow.py](examples/gitea_team_workflow.py)** - Team collaboration
- **[jenkins_simple.py](examples/jenkins_simple.py)** - Simple Jenkins setup
- **[project_maven.py](examples/project_maven.py)** - Maven project initialization
- **[project_postgres.py](examples/project_postgres.py)** - PostgreSQL project
- **[library_usage.py](examples/library_usage.py)** - Library API demonstration

See [examples/README.md](examples/README.md) for detailed descriptions.

Run any example with:

```bash
source .venv/bin/activate
python examples/<example_name>.py
```

## 🔧 Development

### Install in Editable Mode

```bash
./env_setup.sh
source venv/bin/activate
```

### Run Tests

```bash
pytest  # (when tests are added)
```

### Format Code

```bash
black devops_tools/
```

## 📝 Migration from Shell Scripts

This Python library replaces the shell scripts in `scripts/`:

| Shell Script | Python Module |
|--------------|---------------|
| `env-functions.sh` | `devops_tools.env` |
| `gitea-functions.sh` | `devops_tools.gitea` |
| `jenkins-functions.sh` | `devops_tools.jenkins` |
| `project-functions.sh` | `devops_tools.project` |

See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) for complete details.

## 🎉 Benefits Over Shell Scripts

1. **Type Safety** - Catch errors before running
2. **Better Error Handling** - Clear exceptions with context
3. **IDE Support** - Autocomplete and inline documentation
4. **Reusable** - Import in other Python projects
5. **Testable** - Unit tests with pytest
6. **Cross-platform** - Works on Windows/Mac/Linux
7. **CLI** - User-friendly command-line interface
8. **Documentation** - Comprehensive docs and examples

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please open an issue or pull request.

---

**Quick Links:**

- [QUICKSTART.md](QUICKSTART.md) - CLI command reference
- [USAGE.md](USAGE.md) - Detailed usage patterns
- [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) - Migration guide
