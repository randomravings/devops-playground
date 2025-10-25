#!/usr/bin/env python3
"""Simple Jenkins example: Create credentials and organization."""

from devops_tools import env, gitea, jenkins


def main():
    """Setup a simple Jenkins configuration."""
    print("🚀 Starting simple Jenkins setup...")
    
    # Setup environment
    print("\n1️⃣ Setting up Docker environment...")
    env.setup()
    
    # Create Gitea user (Jenkins needs to access Gitea)
    print("\n2️⃣ Creating Gitea user 'jenkins-bot'...")
    gitea.create_user("jenkins-bot", "secret", "acme")
    
    # Create organization
    print("\n3️⃣ Creating Gitea organization 'acme'...")
    gitea.create_org("acme")
    
    # Create Jenkins credentials
    print("\n4️⃣ Creating Jenkins credentials...")
    jenkins.create_credentials("jenkins-bot-creds", "jenkins-bot", "secret")
    
    # Create Jenkins organization
    print("\n5️⃣ Creating Jenkins organization folder...")
    jenkins.create_org("acme", "jenkins-bot-creds")
    
    print("\n✅ Simple Jenkins setup complete!")
    print("\n📍 Access Jenkins at: http://localhost:8080")
    print("   Username: admin")
    print("   Password: secret")
    print("\n💡 Jenkins will automatically scan 'acme' organization in Gitea")
    print("   Any repository with a Jenkinsfile will be built automatically")
    print("\n🧹 Run 'python examples/teardown.py' to clean up")


if __name__ == "__main__":
    main()
