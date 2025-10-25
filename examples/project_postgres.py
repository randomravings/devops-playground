#!/usr/bin/env python3
"""PostgreSQL project example: Initialize a database project."""

from devops_tools import env, gitea, project


def main():
    """Setup a PostgreSQL database project in Gitea."""
    print("🚀 Starting PostgreSQL project setup...")
    
    # Setup environment
    print("\n1️⃣ Setting up Docker environment...")
    env.setup()
    
    # Create user and org
    print("\n2️⃣ Creating Gitea user and organization...")
    gitea.create_user("alice", "secret", "acme")
    gitea.create_org("acme")
    
    # Create repository
    print("\n3️⃣ Creating repository 'my-database'...")
    gitea.create_repo("acme", "my-database", "alice")
    gitea.setup_branch_protection("acme", "my-database")
    
    # Clone repository
    print("\n4️⃣ Cloning repository...")
    repo_path = gitea.clone_repo("acme", "my-database")
    
    # Initialize PostgreSQL project
    print("\n5️⃣ Initializing PostgreSQL project...")
    project.init_postgres(repo_path)
    
    # Commit and push
    print("\n6️⃣ Committing and pushing to Gitea...")
    project.init_commit(repo_path, "Initial commit: PostgreSQL schema structure")
    
    print("\n✅ PostgreSQL project setup complete!")
    print(f"\n📂 Project location: {repo_path}")
    print("📍 Repository: http://localhost:3000/acme/my-database")
    print("\n💡 Project structure:")
    print("   db/")
    print("   └── schema/")
    print("       ├── 001_tenants.sql")
    print("       └── 010_users.sql")
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
