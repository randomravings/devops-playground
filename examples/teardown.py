#!/usr/bin/env python3
"""
Teardown script for devops_tools library.

This script tears down the DevOps environment, removing all
Docker containers, volumes, and local state.
"""

from devops_tools import env

def main():
    """Teardown the DevOps environment."""
    
    print("=" * 60)
    print("DevOps Tools - Teardown")
    print("=" * 60)
    print("\nThis will remove all Docker containers, volumes, and state.")
    
    response = input("\nAre you sure you want to teardown the environment? (yes/no): ")
    
    if response.lower() in ('yes', 'y'):
        print("\nTearing down environment...")
        env.teardown()
        print("\n✅ Teardown complete!")
    else:
        print("\n❌ Teardown cancelled.")


if __name__ == "__main__":
    main()
