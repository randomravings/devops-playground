# Quick Start Guide

## Installation

### Quick Setup

```bash
./env_setup.sh
```

This creates a virtual environment and installs all dependencies.

### Activate Virtual Environment

```bash
source .venv/bin/activate
```

Now you can run examples or use the CLI.

## CLI Usage

### Environment Management

```bash
# Setup the environment (starts Docker containers, creates admin users, etc.)
devops-tools environment setup

# Teardown the environment (removes containers and volumes)
devops-tools environment teardown
```

### Gitea Operations

```bash
# Create a user
devops-tools git create-user john --password secret --org acme

# Create an organization
devops-tools git create-org myorg --owner admin

# Create a team
devops-tools git create-team developers --org acme --permission write

# Add user to team
devops-tools git add-team-member developers --org acme --username john

# Create a repository
devops-tools git create-repo my-project --org acme --description "My project"

# Setup branch protection
devops-tools git branch-protection my-project --org acme

# Clone a repository
devops-tools git clone my-project --org acme --dest ~/projects --username john

# Setup Jenkins webhook
devops-tools git setup-webhook
```

### Jenkins Operations

```bash
# Create credentials
devops-tools ci create-credentials gitea-creds --username admin

# Create organization folder
devops-tools ci create-org acme-org --org acme --credentials gitea-creds

# Check if job exists
devops-tools ci job-exists acme-org
```

### Project Initialization

```bash
# Initialize Maven project
devops-tools projects init-maven ~/projects/my-maven-app

# Initialize PostgreSQL project
devops-tools projects init-postgres ~/projects/my-db

# Initialize dbci-tools project
devops-tools projects init-dbci-tools ~/projects/my-dbci

# Commit and push changes
devops-tools projects commit ~/projects/my-project -m "Initial commit"
```

## Library Usage

```python
from devops_tools import env, gitea, jenkins

# Setup environment
env.setup()

# Create Gitea resources
gitea.create_user("john", "secret", "acme", admin=False)
gitea.create_org("myorg", "admin")
gitea.create_repo("my-repo", "myorg")

# Create Jenkins resources
jenkins.create_credentials("gitea-creds", "admin", "secret")
jenkins.create_org("myorg-folder", "myorg", "gitea-creds")

# Teardown
env.teardown()
```

## Running the Example

```bash
source .venv/bin/activate
python examples/full_setup.py
```

This will set up a complete environment with users, teams, repositories, and Jenkins integration.

## Teardown

```bash
python examples/teardown.py
```

## Configuration

The library uses environment variables or a `.env` file. Default values:

```bash
DOCKER_ENV_NAME=devops-env
GITEA_PORT=3000
GITEA_DEFAULT_ORG=acme
GITEA_ADMIN_USER=admin
GITEA_ADMIN_PASSWORD=secret
JENKINS_ADMIN_USER=admin
JENKINS_ADMIN_PASSWORD=secret
```

You can override these by:
1. Setting environment variables
2. Creating a `.env` file
3. Using `--env-file` with the CLI

## Comparison with Shell Scripts

| Shell Script Function | Python Function |
|-----------------------|-----------------|
| `env_setup` | `env.setup()` |
| `env_teardown` | `env.teardown()` |
| `gitea_create_user` | `gitea.create_user()` |
| `gitea_create_org` | `gitea.create_org()` |
| `gitea_create_team` | `gitea.create_team()` |
| `gitea_add_team_members` | `gitea.add_team_members()` |
| `gitea_create_repo` | `gitea.create_repo()` |
| `gitea_branch_protection` | `gitea.setup_branch_protection()` |
| `gitea_clone_repo` | `gitea.clone_repo()` |
| `gitea_setup_default_webhook` | `gitea.setup_default_webhook()` |
| `jenkins_create_credentials` | `jenkins.create_credentials()` |
| `jenkins_create_org` | `jenkins.create_org()` |
| `jenkins_job_exists` | `jenkins.job_exists()` |
| `init_maven` | `project.init_maven()` |
| `init_postgres` | `project.init_postgres()` |
| `init_dbci_tools` | `project.init_dbci_tools()` |
| `init_commit` | `project.init_commit()` |
