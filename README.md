# DevOps Playground

Local sandbox for practicing Git workflows and CI/CD pipelines.

Wraps a lot of REST and Command Line calls in an opinionated Python project to simplify environment setup and configuration.

## Requirements

- Python 3.8+
- Docker & Docker Compose
- Git
- rsync (for template copying)

## Quick Start

Setup and activate:

```bash
./env_setup.sh                      # Builds the virtual environment for this project.
source .venv/bin/activate           # Activates the virtual environmnet to enable commands.
```

Example setup commands:

```bash
dt env up                                                   # Sets up up the Docker environment.

dt git org new acme                                         # Creates an 'acme' organization in Gitea.
dt ci org new acme                                          # Creates the corresponding org (folder) in Jenkins (names must match).

dt git team new devs -o acme -m write                       # Creates a team 'devs' with write permissions to 'acme' repos.
dt git user new john -o acme                                # Creates a user 'john' (default password 'secret') in 'acme' org.
dt git member new john -o acme -t devs                      # Adds John to the 'devs' team.

dt git repo new demo-app -o acme                            # Creates a repo 'demo-app' in 'acme' org.
dt git repo init -o acme -d ./projects/demo-app demo-app    # Initializes 'demo-app' repo by pushing diectory content (-d) to master.
dt git clone demo-app -o acme -d ~/Local -u john -p secret  # Clones the 'demo-app' repo to a local folder with the user credentials.

dt env down                                                 # Tears down the Docker environment.
```

Use `dt --help` for more commands.

The docker environment Gitea and Jenkins are available at:

- Gitea: [http://localhost:3000](http://localhost:3000)
- Jenkins: [http://localhost:8080](http://localhost:8080)

Both services have admin login as: `admin` / `secret`

Deactivate and cleanup:

```bash
deactivate                          # Deactivates the virutal environment.
./env_cleanup.sh                    # Removes Python generated directories.
```

## Examples

See how commands compose together:

```bash
./examples/acme_org.sh                          # Set up acme org in Gitea and Jenkins.
./examples/acme_user_local.sh john ~/Local      # Clone to local workspace for 'john'.
./examples/acme_user_test.sh john ~/Local       # Run all builds locally for 'john'.
./examples/teardown.sh                          # Cleanup Docker, local workspace must be cleaned up manually.
```

The examples in this case presuppose and existing folder 'Local' in home directory. There are two users in the Acme org 'john' and 'jane'.
There are four projects in the current setup:

- **dbci-tools**: a custom build CLI tool based on Python, SQLFluff, and Atlas for doing Postgres database checks.
- **etl-franework**: a minimalistic ETL framework that can build Star schemas from metadata that describes sources and target model.
- **demo-dw**: a small Star schema in Postgres syntax, inlcuding selected SQLFluff config file for linting.
- **demo-etl**: an ETL pipeline based on Dagster that uses the ETL Framework and a metadata file to describe the source and target model.

> Note: The `dbci-tool` and `etl-franework` are general purpose tools and already initialized on `origin/main` already, but the demo projects `demo-db` and `demo-etl` are "actual" projects and checked out locally to a `feature-init` branch. The idea is now to experiment with commit, pull requests, and merge to master to demo a Data as Code way of working.

To learn more about dbci-tools checkout the [dbci-tools/README.md](./projects/dbci-tools/README.md).

To learn more about the etl-framework checkout the [etl-framework/README.md](./projects/etl-framework/README.md).

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
- sqlfluff >= 3.0.0 (SQL linter)
- Atlas CLI (database schema management and diffing)
- Docker CLI (for Atlas ephemeral dev databases)

**For local DBCI development:**

- Python 3.9+
- Atlas CLI: `curl -sSf https://atlasgo.sh | sh`
- SQLFluff: `pip install "sqlfluff>=3.0.0"`
- Docker (for Atlas dev database - uses `docker://postgres/15/dev`)

Set `ATLAS_DEV_URL` environment variable to override the default dev database URL.
