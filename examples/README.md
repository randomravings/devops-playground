# DevOps Tools - Examples

This folder contains example scripts demonstrating various use cases for the DevOps Tools library.

## 🚀 Quick Start

Activate the virtual environment and run examples:

```bash
cd /path/to/devops-playground
source .venv/bin/activate
python examples/full_setup.py
python examples/teardown.py
```

## 📚 Available Examples

### Core Examples

- **[full_setup.py](full_setup.py)** - Complete environment setup
  - Sets up Docker environment (Gitea, Jenkins)
  - Creates users, organizations, teams
  - Initializes multiple project types
  - Sets up webhooks and CI/CD integration
  - **Best for**: First-time users, complete demonstration

- **[teardown.py](teardown.py)** - Clean environment teardown
  - Stops and removes all Docker containers
  - Cleans up volumes and networks
  - **Best for**: Cleanup after testing

### Gitea Examples

- **[gitea_simple.py](gitea_simple.py)** - Simple Gitea setup
  - Create a single user and repository
  - **Best for**: Quick repository creation

- **[gitea_team_workflow.py](gitea_team_workflow.py)** - Team collaboration setup
  - Create organization with multiple teams
  - Assign team members and permissions
  - Create team-owned repositories
  - **Best for**: Multi-team organizations

### Jenkins Examples

- **[jenkins_simple.py](jenkins_simple.py)** - Simple Jenkins setup
  - Create credentials and a basic organization
  - **Best for**: Basic CI/CD setup

### Project Examples

- **[project_maven.py](project_maven.py)** - Maven project initialization
  - Initialize a Maven Java project
  - Commit and push to Gitea
  - **Best for**: Java development

- **[project_postgres.py](project_postgres.py)** - PostgreSQL project initialization
  - Initialize a database project with schema files
  - **Best for**: Database development

- **[library_usage.py](library_usage.py)** - Library API demonstration
  - Shows how to import and use the library programmatically
  - **Best for**: Integrating into your own scripts

## 🎯 Usage Patterns

```bash
source .venv/bin/activate           # Activate venv
python examples/full_setup.py       # Run example
python examples/teardown.py         # Cleanup
deactivate                          # Exit venv
```

## 🔧 Creating Your Own Examples

Copy an existing example and modify it:

```python
#!/usr/bin/env python3
"""My custom example."""

from devops_tools import env, gitea, jenkins, project

def main():
    """Main function."""
    print("🚀 Starting my custom setup...")
    
    # Setup environment
    env.setup()
    
    # Your custom logic here
    gitea.create_user("myuser", "secret", "myorg")
    
    print("✅ Setup complete!")

if __name__ == "__main__":
    main()
```

## 📝 Notes

- All examples assume Docker is running
- Examples are independent - run them in any order
- Remember to run `teardown.py` to clean up after testing
- Check the main [README.md](../README.md) for installation instructions

## 🆘 Troubleshooting

### Problem: Import errors

**Solution:**

```bash
cd /path/to/devops-playground
./env_setup.sh
source .venv/bin/activate
```

### Problem: Docker containers already running

**Solution:**

```bash
source .venv/bin/activate
python examples/teardown.py
python examples/full_setup.py
```

### Problem: Permission denied

**Solution:**

```bash
chmod +x examples/*.py
```

## 📚 Further Reading

- [README.md](../README.md) - Main project documentation
- [QUICKSTART.md](../QUICKSTART.md) - CLI command reference
- [USAGE.md](../USAGE.md) - Detailed usage patterns
- [MIGRATION_SUMMARY.md](../MIGRATION_SUMMARY.md) - Migration guide
