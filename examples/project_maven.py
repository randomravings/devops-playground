#!/usr/bin/env python3
"""Maven project example: Initialize and push a Maven project to Gitea."""

from devops_tools import env, gitea, project


def main():
    """Setup a Maven project in Gitea."""
    print("🚀 Starting Maven project setup...")
    
    # Setup environment
    print("\n1️⃣ Setting up Docker environment...")
    env.setup()
    
    # Create user and org
    print("\n2️⃣ Creating Gitea user and organization...")
    gitea.create_user("alice", "secret", "acme")
    gitea.create_org("acme")
    
    # Create repository
    print("\n3️⃣ Creating repository 'my-maven-app'...")
    gitea.create_repo("acme", "my-maven-app", "alice")
    gitea.setup_branch_protection("acme", "my-maven-app")
    
    # Clone repository
    print("\n4️⃣ Cloning repository...")
    repo_path = gitea.clone_repo("acme", "my-maven-app")
    
    # Initialize Maven project
    print("\n5️⃣ Initializing Maven project...")
    project.init_maven(repo_path, group_id="com.acme", artifact_id="my-maven-app")
    
    # Commit and push
    print("\n6️⃣ Committing and pushing to Gitea...")
    project.init_commit(repo_path, "Initial commit: Maven project structure")
    
    print("\n✅ Maven project setup complete!")
    print(f"\n📂 Project location: {repo_path}")
    print("📍 Repository: http://localhost:3000/acme/my-maven-app")
    print("\n💡 Next steps:")
    print(f"   cd {repo_path}")
    print("   mvn clean package")
    print("   mvn test")
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
