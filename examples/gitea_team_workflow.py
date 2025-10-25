#!/usr/bin/env python3
"""Team collaboration example: Create organization with teams and members."""

from devops_tools import env, gitea


def main():
    """Setup a team-based Gitea workflow."""
    print("🚀 Starting team workflow setup...")
    
    # Setup environment
    print("\n1️⃣ Setting up Docker environment...")
    env.setup()
    
    # Create users
    print("\n2️⃣ Creating users...")
    users = ["alice", "bob", "charlie", "diana"]
    for user in users:
        print(f"   Creating user '{user}'...")
        gitea.create_user(user, "secret", "acme")
    
    # Create organization
    print("\n3️⃣ Creating organization 'acme'...")
    gitea.create_org("acme")
    
    # Create teams
    print("\n4️⃣ Creating teams...")
    gitea.create_team("acme", "developers", permission="write")
    gitea.create_team("acme", "admins", permission="admin")
    gitea.create_team("acme", "readers", permission="read")
    
    # Add team members
    print("\n5️⃣ Adding team members...")
    gitea.add_team_members("acme", "developers", ["alice", "bob"])
    gitea.add_team_members("acme", "admins", ["alice"])
    gitea.add_team_members("acme", "readers", ["charlie", "diana"])
    
    # Create repositories
    print("\n6️⃣ Creating repositories...")
    repos = [
        ("frontend", "alice"),
        ("backend", "bob"),
        ("docs", "charlie"),
    ]
    for repo_name, owner in repos:
        print(f"   Creating repository '{repo_name}'...")
        gitea.create_repo("acme", repo_name, owner)
        gitea.setup_branch_protection("acme", repo_name)
    
    print("\n✅ Team workflow setup complete!")
    print("\n📍 Access Gitea at: http://localhost:3000")
    print("\n👥 Users (all password: secret):")
    print("   - alice (admin, developer)")
    print("   - bob (developer)")
    print("   - charlie (reader)")
    print("   - diana (reader)")
    print("\n📦 Repositories:")
    print("   - http://localhost:3000/acme/frontend")
    print("   - http://localhost:3000/acme/backend")
    print("   - http://localhost:3000/acme/docs")
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
