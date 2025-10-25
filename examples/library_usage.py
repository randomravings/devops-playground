#!/usr/bin/env python3
"""Library usage example: Demonstrates programmatic API usage."""

from devops_tools import env, gitea, jenkins, project
from devops_tools.config import get_config


def main():
    """Demonstrate how to use the library programmatically."""
    print("📚 DevOps Tools Library API Demonstration\n")
    
    # Get configuration
    config = get_config()
    print("⚙️  Configuration:")
    print(f"   Gitea URL: {config.gitea_url}")
    print(f"   Jenkins URL: {config.jenkins_url}")
    print(f"   Docker Compose: {config.docker_compose}")
    print(f"   Project Templates: {config.project_templates_dir}")
    
    # Setup environment
    print("\n🐳 Setting up Docker environment...")
    env.setup()
    
    # Gitea operations
    print("\n🦊 Gitea Operations:")
    print("   Creating users...")
    gitea.create_user("dev1", "secret", "mycompany")
    gitea.create_user("dev2", "secret", "mycompany")
    
    print("   Creating organization...")
    gitea.create_org("mycompany")
    
    print("   Creating team...")
    gitea.create_team("mycompany", "backend-team", permission="write")
    
    print("   Adding team members...")
    gitea.add_team_members("mycompany", "backend-team", ["dev1", "dev2"])
    
    print("   Creating repository...")
    gitea.create_repo("mycompany", "api-service", "dev1")
    gitea.setup_branch_protection("mycompany", "api-service")
    
    # Jenkins operations
    print("\n🔧 Jenkins Operations:")
    print("   Creating credentials...")
    jenkins.create_credentials("dev1-creds", "dev1", "secret")
    
    print("   Creating organization folder...")
    jenkins.create_org("mycompany", "dev1-creds")
    
    # Project initialization
    print("\n📦 Project Initialization:")
    print("   Cloning repository...")
    repo_path = gitea.clone_repo("mycompany", "api-service")
    
    print("   Initializing Maven project...")
    project.init_maven(
        repo_path,
        group_id="com.mycompany",
        artifact_id="api-service"
    )
    
    print("   Committing changes...")
    project.init_commit(repo_path, "Initial commit: API service skeleton")
    
    # Setup webhook
    print("\n🔗 Setting up webhook...")
    gitea.setup_default_webhook("mycompany", "api-service")
    
    print("\n✅ Demonstration complete!")
    print("\n📊 Summary:")
    print("   ✓ Environment setup with Docker")
    print("   ✓ 2 users created (dev1, dev2)")
    print("   ✓ 1 organization created (mycompany)")
    print("   ✓ 1 team created (backend-team)")
    print("   ✓ 1 repository created (api-service)")
    print("   ✓ Maven project initialized")
    print("   ✓ Jenkins credentials and organization configured")
    print("   ✓ Webhook configured")
    
    print("\n🌐 Access URLs:")
    print(f"   Gitea: {config.gitea_url}")
    print(f"   Jenkins: {config.jenkins_url}")
    
    print("\n📝 Try these commands:")
    print("   # Check if job exists")
    print("   jenkins.job_exists('mycompany/api-service')")
    print()
    print("   # Get credential name")
    print("   jenkins.get_credential_name('dev1')")
    
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
