#!/usr/bin/env python3
"""
Test creating a repository as a regular user (not admin).

This verifies that a user can:
1. Create/use an empty repository in their org
2. Clone it to a local directory outside devops-playground
3. Initialize it with a project template
4. Commit and push changes
"""

import tempfile
from pathlib import Path
from datetime import datetime

from devops_tools import config, gitea, project


def main():
    """Test user workflow for creating and pushing a project."""
    
    cfg = config.get_config()
    
    # Test user details (should exist from full_setup.py)
    username = "john"
    password = "secret"
    org_name = cfg.gitea_default_org  # typically "acme"
    # Use timestamp to ensure unique repo name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    repo_name = f"test-maven-{timestamp}"
    
    print("=" * 60)
    print("Testing User Workflow: Create & Push Maven Project")
    print("=" * 60)
    print(f"User: {username}")
    print(f"Org:  {org_name}")
    print(f"Repo: {repo_name}")
    print()
    
    # Step 1: Create repository in Gitea (as user john)
    print("Step 1: Creating repository in Gitea...")
    try:
        gitea.create_repo(repo_name, org_name, description="My Maven application")
        print(f"✅ Repository '{repo_name}' created\n")
    except Exception as e:
        print(f"❌ Failed to create repository: {e}\n")
        return 1
    
    # Step 2: Clone repository to ~/Local
    print("Step 2: Cloning repository...")
    workspace_path = Path.home() / "Local"
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"   Using workspace: {workspace_path}")
    
    try:
        gitea.clone_repo(
            repo_name,
            org_name,
            str(workspace_path),
            username,
            password,
        )
        print(f"✅ Repository cloned to {workspace_path / repo_name}\n")
    except Exception as e:
        print(f"❌ Failed to clone repository: {e}\n")
        return 1
    
    repo_path = workspace_path / repo_name
    
    # Step 3: Initialize with Maven template
    print("Step 3: Initializing with Maven template...")
    try:
        project.init_maven(str(repo_path))
        print(f"✅ Maven project initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize project: {e}\n")
        return 1
    
    # Step 4: Verify file exists in Gitea (on feature-init branch)
    print("Step 4: Verifying file exists in Gitea...")
    if gitea.repo_file_exists(repo_name, org_name, "pom.xml", branch="feature-init"):
        print(f"✅ pom.xml found in Gitea repository (feature-init branch)\n")
    else:
        print(f"❌ pom.xml not found in Gitea - push may have failed\n")
        return 1
    
    print("=" * 60)
    print("✅ User workflow test completed successfully!")
    print("=" * 60)
    print()
    print(f"You can view the repository at:")
    print(f"{cfg.gitea_advertised_url}/{org_name}/{repo_name}")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())
