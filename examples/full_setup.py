#!/usr/bin/env python3
"""
Example usage of devops_tools library.

This script demonstrates how to use the devops_tools library
to set up a complete DevOps environment.
"""

from devops_tools import config, env, gitea, jenkins, project

def main():
    """Main example workflow."""
    
    # Get configuration
    cfg = config.get_config()
    
    print("=" * 60)
    print("DevOps Tools - Example Usage")
    print("=" * 60)
    
    # 1. Setup environment
    print("\n1. Setting up environment...")
    env.setup()
    
    # 2. Create additional users
    print("\n2. Creating users...")
    gitea.create_user("john", "secret", cfg.gitea_default_org, admin=False)
    gitea.create_user("jane", "secret", cfg.gitea_default_org, admin=False)
    
    # 3. Create a team
    print("\n3. Creating team...")
    gitea.create_team("developers", cfg.gitea_default_org, permission="write")
    gitea.add_team_members("developers", cfg.gitea_default_org, "john")
    gitea.add_team_members("developers", cfg.gitea_default_org, "jane")
    
    # 4. Create repositories
    print("\n4. Creating repositories...")
    gitea.create_repo("demo-app", cfg.gitea_default_org, description="Demo application")
    gitea.create_repo("demo-db", cfg.gitea_default_org, description="Demo database")
    gitea.create_repo("dbci-tools", cfg.gitea_default_org, description="Database CI tools")
    
    # 5. Setup branch protection
    print("\n5. Setting up branch protection...")
    gitea.setup_branch_protection("demo-app", cfg.gitea_default_org, team="developers")
    
    # 6. Setup Jenkins webhook
    print("\n6. Setting up Jenkins webhook...")
    gitea.setup_default_webhook()
    
    # 7. Create Jenkins credentials
    print("\n7. Creating Jenkins credentials...")
    jenkins.create_credentials(
        "gitea-credentials",
        cfg.gitea_admin_user,
        cfg.gitea_admin_password,
        "Gitea user credentials",
    )
    
    # 8. Create Jenkins organization folder for Gitea org
    print(f"\n8. Creating Jenkins organization folder for '{cfg.gitea_default_org}'...")
    jenkins.create_org(
        f"{cfg.gitea_default_org}-folder",
        cfg.gitea_default_org,
        "gitea-credentials",
        f"Gitea organization folder for {cfg.gitea_default_org}",
    )
    
    # 9. Initialize dbci-tools repository with template content
    print("\n9. Initializing dbci-tools repository...")
    
    # Check if repository already has content (pyproject.toml exists)
    if gitea.repo_file_exists("dbci-tools", cfg.gitea_default_org, "pyproject.toml"):
        print("   dbci-tools repository already initialized; skipping.")
    else:
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_dest = Path(tmpdir)
            
            # Clone the repo
            print("   Cloning dbci-tools repository...")
            gitea.clone_repo(
                "dbci-tools",
                cfg.gitea_default_org,
                str(clone_dest),
                cfg.gitea_admin_user,
                cfg.gitea_admin_password,
            )
            
            repo_path = clone_dest / "dbci-tools"
            
            # Initialize with template
            print("   Copying dbci-tools template content...")
            project.init_dbci_tools(str(repo_path))
            
            # Commit and push
            print("   Committing and pushing initial content...")
            project.init_commit(str(repo_path), "Initial commit: Add dbci-tools template")
            
            print("   ✅ dbci-tools repository initialized")
    
    print("\n" + "=" * 60)
    print("✅ Environment setup complete!")
    print("=" * 60)
    print(f"\nGitea:   {cfg.gitea_advertised_url}")
    print(f"Jenkins: {cfg.jenkins_url}")
    print(f"\nGitea Admin:   {cfg.gitea_admin_user} / {cfg.gitea_admin_password}")
    print(f"Jenkins Admin: {cfg.jenkins_admin_user} / {cfg.jenkins_admin_password}")
    print("\nYou can now:")
    print("  - Clone repositories with: devops-tools git clone <repo> --org acme --dest /path")
    print("  - Initialize projects with: devops-tools projects init-maven /path/to/repo")
    print("  - Teardown with: devops-tools environment teardown")
    print()


if __name__ == "__main__":
    main()
