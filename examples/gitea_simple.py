#!/usr/bin/env python3
"""Simple Gitea example: Create a user and repository."""

from devops_tools import env, gitea


def main():
    """Create a simple Gitea setup with one user and repository."""
    print("🚀 Starting simple Gitea setup...")
    
    # Setup environment
    print("\n1️⃣ Setting up Docker environment...")
    env.setup()
    
    # Create a user
    print("\n2️⃣ Creating user 'alice'...")
    gitea.create_user("alice", "secret", "acme")
    
    # Create organization
    print("\n3️⃣ Creating organization 'acme'...")
    gitea.create_org("acme")
    
    # Create repository
    print("\n4️⃣ Creating repository 'my-project'...")
    gitea.create_repo("acme", "my-project", "alice")
    
    # Setup branch protection
    print("\n5️⃣ Setting up branch protection...")
    gitea.setup_branch_protection("acme", "my-project")
    
    print("\n✅ Simple Gitea setup complete!")
    print("\n📍 Access Gitea at: http://localhost:3000")
    print("   Username: alice")
    print("   Password: secret")
    print("\n💡 Repository: http://localhost:3000/acme/my-project")
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
