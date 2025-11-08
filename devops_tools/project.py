"""Project initialization functions for Maven, PostgreSQL, and CI tools."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .config import get_config  # Ensure this import is present
from .utils import run_command, DevOpsError


def init_commit(target_dir: str, commit_message: str) -> None:
    """
    Add, commit, and push all changes in a git repository.

    Args:
        target_dir: Path to git repository
        commit_message: Commit message

    Raises:
        DevOpsError: If git operations fail
    """
    target_path = Path(target_dir)

    if not (target_path / ".git").exists():
        raise DevOpsError(f"Directory '{target_dir}' is not a git repository.")

    print(f"Committing and pushing changes in {target_dir}...")

    try:
        run_command(["git", "-C", str(target_path), "add", "-A"])
        # Check for staged changes before committing
        status = run_command(["git", "-C", str(target_path), "status", "--porcelain"], check=False)
        if status.stdout.strip():
            run_command(["git", "-C", str(target_path), "commit", "-m", commit_message])
        else:
            print("No changes to commit; skipping git commit.")
        run_command(["git", "-C", str(target_path), "push"])
        print("✅ Changes committed and pushed successfully")
    except subprocess.CalledProcessError as e:
        raise DevOpsError(f"Git operation failed: {e.stderr}") from e


def init_maven(target_dir: str) -> None:
    """
    Initialize a Maven project with archetype and Jenkinsfile.

    Args:
        target_dir: Path where Maven project should be created

    Raises:
        DevOpsError: If initialization fails
    """
    config = get_config()
    target_path = Path(target_dir)

    jenkinsfile_path = target_path / "Jenkinsfile"
    if jenkinsfile_path.exists():
        print(f"Jenkinsfile already exists at '{jenkinsfile_path}'; skipping creation.")
        return

    parent_dir = target_path.parent
    leaf_dir = target_path.name

    # Check for Jenkinsfile template in projects/maven-project
    template_dir = config.projects_dir / "maven-project"
    template_path = template_dir / "Jenkinsfile"
    if not template_path.exists():
        raise DevOpsError(f"Jenkinsfile template not found: {template_path}")

    print(f"Creating Maven project in {target_dir}...")

    try:
        # Generate Maven project
        run_command(
            [
                "mvn",
                "archetype:generate",
                "-DgroupId=acme",
                f"-DartifactId={leaf_dir}",
                "-DarchetypeArtifactId=maven-archetype-quickstart",
                "-DarchetypeVersion=1.5",
                "-DinteractiveMode=false",
            ],
            cwd=str(parent_dir),
        )

        # Copy Jenkinsfile
        shutil.copy(template_path, jenkinsfile_path)

        # Create feature branch and commit
        run_command(["git", "-C", str(target_path), "checkout", "-b", "feature-init"])
        run_command(["git", "-C", str(target_path), "add", "-A"])
        run_command(
            ["git", "-C", str(target_path), "commit", "-m", "chore: initialize Maven project with Jenkinsfile"]
        )
        run_command(["git", "-C", str(target_path), "push", "-u", "origin", "feature-init"])

        print("✅ Maven project initialized successfully")

    except subprocess.CalledProcessError as e:
        raise DevOpsError(f"Maven initialization failed: {e.stderr}") from e


def init_dbci_tools(target_dir: str) -> None:
    """
    Initialize a dbci-tools project by copying template.

    Args:
        target_dir: Path where dbci-tools project should be created

    Raises:
        DevOpsError: If initialization fails
    """
    config = get_config()
    target_path = Path(target_dir)

    if (target_path / "pyproject.toml").exists():
        print("dbci-tools project already initialized in directory, aborting.")
        return

    template_path = config.get_project_template_path("dbci-tools")

    print(f"Copying dbci-tools template to {target_dir}...")

    try:
        # Copy all files from template
        for item in template_path.iterdir():
            if item.is_file():
                shutil.copy2(item, target_path / item.name)
            elif item.is_dir():
                shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)

        print("✅ dbci-tools project initialized successfully")

    except (OSError, shutil.Error) as e:
        raise DevOpsError(f"Failed to copy dbci-tools template: {e}") from e


def init_postgres(target_dir: str) -> None:
    """
    Initialize a PostgreSQL database project by copying template.

    Args:
        target_dir: Path where postgres project should be created

    Raises:
        DevOpsError: If initialization fails
    """
    config = get_config()
    target_path = Path(target_dir)

    if (target_path / "Jenkinsfile").exists():
        print("Jenkins file exists in directory, aborting.")
        return

    template_path = config.get_project_template_path("db-postgres-example")

    print(f"Copying db-postgres-example template to {target_dir}...")

    try:
        # Copy all files from template
        for item in template_path.iterdir():
            if item.is_file():
                shutil.copy2(item, target_path / item.name)
            elif item.is_dir():
                shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)

        print("✅ PostgreSQL project initialized successfully")

    except (OSError, shutil.Error) as e:
        raise DevOpsError(f"Failed to copy db-postgres-example template: {e}") from e


def init_and_push_repo(repo_name: str, org_name: str, source_dir: str) -> None:
    """
    Initialize a repository in Gitea by cloning, adding files from a source directory, and pushing.

    Args:
        repo_name: Name of the repository to initialize
        org_name: Name of the Gitea organization
        source_dir: Path to the source directory to copy files from

    Raises:
        DevOpsError: If initialization fails
    """
    from . import gitea

    config = get_config()
    source_path = Path(source_dir)
    if not source_path.exists() or not source_path.is_dir():
        raise DevOpsError(f"Source directory does not exist: {source_dir}")


    with tempfile.TemporaryDirectory() as tmpdir:
        admin_user = config.gitea_admin_user
        clone_dest = Path(tmpdir) / org_name / admin_user / repo_name
        clone_dest.parent.mkdir(parents=True, exist_ok=True)

        print(f"   Cloning {repo_name} to {clone_dest}...")
        gitea.clone_repo(repo_name, org_name, str(clone_dest), admin_user, config.gitea_admin_password)

        print(f"   Copying files from '{source_dir}' to '{clone_dest}'...")
        try:
            for item in source_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, clone_dest / item.name)
                elif item.is_dir():
                    shutil.copytree(item, clone_dest / item.name, dirs_exist_ok=True)
        except (OSError, shutil.Error) as e:
            raise DevOpsError(f"Failed to copy files from '{source_dir}': {e}") from e

        print("   Committing and pushing...")
        init_commit(str(clone_dest), f"Initial commit: Add files from {source_dir}")

        # Now main branch should exist, enable auto-delete branch
        import requests
        from requests.auth import HTTPBasicAuth
        repo_api_url = f"{config.gitea_api_url}/api/v1/repos/{org_name}/{repo_name}/branches/main/protection"
        auto_delete_payload = {"enable_auto_delete": True}
        try:
            auto_delete_resp = requests.patch(
                repo_api_url,
                auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
                headers={"Content-Type": "application/json"},
                json=auto_delete_payload,
                timeout=30
            )
            if auto_delete_resp.status_code == 200:
                print(f"Auto-delete branch enabled for '{repo_name}'.")
            # If still 404, silently skip (branch may be named differently or not pushed yet)
        except Exception as e:
            print(f"Error enabling auto-delete branch for '{repo_name}': {e}")

        print(f"   ✅ {repo_name} initialized")
