# DevOps Playground

Local sandbox for practicing Git workflows and CI/CD pipelines.

## Requirements

- Python 3.8+
- Docker & Docker Compose
- Git
- rsync (for template copying)

## Quick Start

Setup and activate:

```bash
./env_setup.sh
source .venv/bin/activate
```

Access at [http://localhost:3000](http://localhost:3000) (Gitea) and [http://localhost:8080](http://localhost:8080) (Jenkins)
Login: `admin` / `secret`

Run commands:

```bash
dt env up
dt git org acme
dt git user john --org acme
dt git repo myapp --org acme
dt ci org acme-folder --org acme --credentials gitea-creds
dt env down
```

Use `dt --help` for more commands.

Deactivate and cleanup:

```bash
deactivate
./env_cleanup.sh
```

## Examples

See how commands compose together:

```bash
./examples/acme_org.sh                              # Full org setup
./examples/acme_user_local.sh john db-demo ~/Local  # Clone to local workspace
./examples/teardown.sh                              # Cleanup
```

The user example clones a repo to your local filesystem (`~/Local/john/db-demo`) and initializes it with project templates if needed.

## Dependencies

**Python packages:**

- click >= 8.1
- requests >= 2.28
- docker >= 6.0
- python-dotenv >= 1.0

**Docker images:**

- gitea: docker.gitea.com/gitea:latest
- jenkins: jenkins/jenkins:latest-jdk21

**Jenkins tools:**

- Maven (for Java builds)
- Python 3 + venv
- pgformatter (PostgreSQL formatter)
- sqlfluff >= 3.0.0 (SQL linter)
