# DevOps Tools - Usage Guide

## Getting Started

### 1. Setup

```bash
cd devops_tools
./env_setup.sh
```

This will:
- Create a Python virtual environment in `devops_tools/venv/`
- Install all dependencies
- Install the `devops-tools` CLI command

### 2. Run the Example

The easiest way to get started is to run the example script:

```bash
python example.py
```

This will:
- Start Docker containers (Jenkins, Gitea)
- Create admin users
- Create additional users (john, jane)
- Create a development team
- Create demo repositories
- Setup branch protection
- Configure Jenkins

**Access the services:**
- Gitea: http://localhost:3000 (admin/secret)
- Jenkins: http://localhost:8080 (admin/secret)

### 3. Teardown When Done

```bash
python teardown.py
```

This will remove all Docker containers, volumes, and state.

## Usage Patterns

### Pattern 1: Direct Execution

Activate the virtual environment once, then run multiple scripts:

```bash
source .venv/bin/activate
python examples/full_setup.py       # Full setup
python examples/gitea_simple.py     # Simple Gitea setup
python examples/teardown.py         # Clean teardown
devops-tools --help                 # CLI help
deactivate                          # Exit venv
```

### Pattern 2: Using the CLI

```bash
# Activate virtual environment
source .venv/bin/activate

# Use the devops-tools command
devops-tools environment setup
devops-tools git create-user bob --password secret --org acme
devops-tools environment teardown

# Deactivate when done
deactivate
```

### Pattern 3: As a Python Library

```python
#!/usr/bin/env python3
from devops_tools import env, gitea, jenkins

# Setup environment
env.setup()

# Create resources
gitea.create_user("bob", "secret", "acme", admin=False)
gitea.create_repo("my-app", "acme")

jenkins.create_credentials("git-creds", "bob", "secret")
jenkins.create_org("my-org", "acme", "git-creds")

# Teardown (when ready)
# env.teardown()
```

Save as a script and run with:
```bash
python my_script.py
```

## Common Workflows

### Complete Setup Workflow

```bash
# 1. Setup environment
python example.py

# 2. Clone a repository to work on
source venv/bin/activate
devops-tools git clone demo-app --org acme --dest ~/projects --username john

# 3. Initialize a project in the cloned repo
devops-tools projects init-postgres ~/projects/demo-app

# 4. Work on your project...

# 5. Teardown when done
python teardown.py
```

### Quick Test Workflow

```bash
# Setup
devops-tools environment setup

# Create a test repo
devops-tools git create-repo test-repo --org acme

# Teardown
devops-tools environment teardown
```

## Troubleshooting

### Virtual Environment Issues

If you have issues with the virtual environment:

```bash
# Remove it and start fresh
rm -rf venv
./env_setup.sh
```

### Docker Issues

If containers don't start properly:

```bash
# Check Docker is running
docker ps

# Force cleanup
python teardown.py
python example.py
```

### Import Errors

If you get import errors:

```bash
# Reinstall the package
source venv/bin/activate
pip install -e .
```

## File Structure

```
devops_tools/
├── env_setup.sh              # Initial setup script
├── env_cleanup.sh            # Cleanup script
├── .venv/                    # Virtual environment
├── examples/                 # Example scripts
│   ├── full_setup.py        # Complete setup example
│   ├── teardown.py          # Teardown example
│   └── ...                  # Other examples
├── devops_tools/            # Python package
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── utils.py             # Utilities
│   ├── env.py               # Environment lifecycle
│   ├── gitea.py             # Gitea operations
│   ├── jenkins.py           # Jenkins operations
│   ├── project.py           # Project initialization
│   └── cli.py               # CLI interface
└── pyproject.toml           # Package configuration
```

## Next Steps

- See [README.md](README.md) for detailed API documentation
- See [QUICKSTART.md](QUICKSTART.md) for CLI command reference
- Check out the [example.py](example.py) script for usage patterns
