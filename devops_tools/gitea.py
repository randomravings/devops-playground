"""Gitea operations: users, organizations, teams, repositories, and cloning."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from .config import get_config
from .utils import (
    curl_exists,
    curl_get,
    curl_post,
    curl_put,
    ensure_not_child_of_repo,
    run_command,
    DevOpsError,
    HTTPError,
)


def user_exists(username: str) -> bool:
    """
    Check if a user exists in Gitea.
    
    Args:
        username: Username to check
        
    Returns:
        True if user exists, False otherwise
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    try:
        response = requests.get(
            f"{api_base}/users/{username}",
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
        )
        return response.status_code == 200
    except Exception:
        return False


def create_user(
    username: str,
    password: str,
    org: str,
    admin: bool = False,
) -> None:
    """
    Create a user in Gitea (idempotent).

    Args:
        username: Username to create
        password: Password for the user
        org: Organization (used for email as username@org.demo)
        admin: Whether to make the user an admin

    Raises:
        DevOpsError: If user creation fails
    """
    config = get_config()
    email = f"{username}@{org}.demo"
    
    # Check if user already exists
    if user_exists(username):
        print(f"User '{username}' already exists; skipping creation.")
        return

    print(f"Creating user '{username}' (email: {email}){' as admin' if admin else ''}...")

    admin_flag = "--admin" if admin else ""
    cmd = (
        f"gitea admin user create --username '{username}' "
        f"--password '{password}' --email '{email}' {admin_flag} "
        f"--must-change-password=false"
    )

    from .utils import docker_exec_interactive

    result = docker_exec_interactive("gitea", f"su git -c \"{cmd}\"")

    if result != 0:
        print(f"Warning: Failed to create user {username} (may already exist)")
    else:
        print(f"User '{username}' created successfully")


def delete_user(username: str) -> None:
    """
    Delete a user from Gitea.

    Args:
        username: Username to delete

    Raises:
        HTTPError: If user deletion fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    # Check if user exists
    if not user_exists(username):
        print(f"User '{username}' does not exist; skipping deletion.")
        return

    print(f"Deleting user '{username}'...")

    try:
        response = requests.delete(
            f"{api_base}/admin/users/{username}",
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            timeout=30,
        )

        if response.status_code == 204:
            print(f"✅ User '{username}' deleted successfully")
        elif response.status_code == 404:
            print(f"User '{username}' not found (already deleted?)")
        else:
            raise HTTPError(f"Failed to delete user: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to delete user: {e}") from e


def repo_file_exists(repo_name: str, org_name: str, file_path: str, branch: str = "main") -> bool:
    """
    Check if a file exists in a Gitea repository.
    
    Args:
        repo_name: Repository name
        org_name: Organization name
        file_path: Path to file within repository (e.g., "pyproject.toml")
        branch: Branch name (default: "main")
        
    Returns:
        True if file exists, False otherwise
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    # Use the Gitea API to check file contents
    # GET /repos/{owner}/{repo}/contents/{filepath}
    url = f"{api_base}/repos/{org_name}/{repo_name}/contents/{file_path}"
    
    try:
        response = requests.get(
            url,
            params={"ref": branch},
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            timeout=30,
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def org_exists(org_name: str) -> bool:
    """
    Check if an organization exists in Gitea.
    
    Args:
        org_name: Organization name to check
        
    Returns:
        True if organization exists, False otherwise
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    try:
        response = requests.get(
            f"{api_base}/orgs/{org_name}",
            timeout=30,
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    try:
        response = requests.get(
            f"{api_base}/orgs/{org_name}",
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
        )
        return response.status_code == 200
    except Exception:
        return False


def create_org(org_name: str, owner: str, description: str = "") -> None:
    """
    Create an organization in Gitea (idempotent).

    Args:
        org_name: Organization name
        owner: Owner username
        description: Optional description

    Raises:
        HTTPError: If organization creation fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    # Check if organization already exists
    if org_exists(org_name):
        print(f"Organization '{org_name}' already exists; skipping creation.")
        return

    # Build payload
    payload = {
        "username": org_name,
        "full_name": org_name,
    }
    if description:
        payload["description"] = description

    print(f"Creating organization '{org_name}' with owner '{owner}' via REST API...")

    try:
        response = requests.post(
            f"{api_base}/orgs",
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code == 201:
            print(f"Organization '{org_name}' created.")
        elif response.status_code in (409, 422):
            print(f"Organization '{org_name}' already exists (HTTP {response.status_code}).")
        else:
            raise HTTPError(f"Failed to create organization: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to create organization: {e}") from e


def delete_org(org_name: str) -> None:
    """
    Delete an organization from Gitea.

    Args:
        org_name: Organization name to delete

    Raises:
        HTTPError: If organization deletion fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    
    # Check if organization exists
    if not org_exists(org_name):
        print(f"Organization '{org_name}' does not exist; skipping deletion.")
        return

    print(f"Deleting organization '{org_name}'...")

    try:
        response = requests.delete(
            f"{api_base}/orgs/{org_name}",
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            timeout=30,
        )

        if response.status_code == 204:
            print(f"✅ Organization '{org_name}' deleted successfully")
        elif response.status_code == 404:
            print(f"Organization '{org_name}' not found (already deleted?)")
        else:
            raise HTTPError(f"Failed to delete organization: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to delete organization: {e}") from e


def create_team(
    team_name: str,
    org_name: str,
    permission: str = "write",
    description: str = "",
) -> None:
    """
    Create a team in an organization.

    Args:
        team_name: Team name
        org_name: Organization name
        permission: Team permission (read, write, admin)
        description: Optional description

    Raises:
        HTTPError: If team creation fails
    """
    config = get_config()

    if permission not in ("read", "write", "admin"):
        raise ValueError(f"Invalid permission: {permission}")

    api_base = f"{config.gitea_api_url}/api/v1"
    endpoint = f"{api_base}/orgs/{org_name}/teams"

    # Build payload matching Swagger specification
    units = [
        "repo.actions",
        "repo.code",
        "repo.issues",
        "repo.ext_issues",
        "repo.wiki",
        "repo.ext_wiki",
        "repo.pulls",
        "repo.releases",
        "repo.projects",
    ]

    payload = {
        "name": team_name,
        "permission": permission,
        "can_create_org_repo": True,
        "includes_all_repositories": True,
        "units": units,
    }

    if description:
        payload["description"] = description

    print(f"Creating team '{team_name}' in org '{org_name}' with permission '{permission}'...")

    try:
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code == 201:
            print(f"Team '{team_name}' created.")
        elif response.status_code in (409, 422):
            print(f"Team '{team_name}' already exists (HTTP {response.status_code}).")
        else:
            raise HTTPError(f"Failed to create team: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to create team: {e}") from e


def delete_team(team_name: str, org_name: str) -> None:
    """
    Delete a team from an organization.

    Args:
        team_name: Team name
        org_name: Organization name

    Raises:
        HTTPError: If team deletion fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    creds = (config.gitea_admin_user, config.gitea_admin_password)

    # Search for team ID
    search_endpoint = f"{api_base}/orgs/{org_name}/teams/search"
    try:
        response = requests.get(
            search_endpoint,
            auth=HTTPBasicAuth(*creds),
            params={"q": team_name, "page": 1, "limit": 1},
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPError(f"Team search failed: HTTP {response.status_code}\n{response.text}")

        data = response.json()
        if not data.get("data"):
            print(f"Team '{team_name}' not found in org '{org_name}'; skipping deletion.")
            return

        team_id = data["data"][0]["id"]

        print(f"Deleting team '{team_name}' (id {team_id}) from org '{org_name}'...")

        # Delete team
        delete_response = requests.delete(
            f"{api_base}/teams/{team_id}",
            auth=HTTPBasicAuth(*creds),
            timeout=30,
        )

        if delete_response.status_code == 204:
            print(f"✅ Team '{team_name}' deleted successfully")
        elif delete_response.status_code == 404:
            print(f"Team not found (already deleted?)")
        else:
            raise HTTPError(f"Failed to delete team: HTTP {delete_response.status_code}\n{delete_response.text}")

    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to delete team: {e}") from e


def add_team_members(team_name: str, org_name: str, username: str) -> None:
    """
    Add a user to a team.

    Args:
        team_name: Team name
        org_name: Organization name
        username: Username to add

    Raises:
        HTTPError: If operation fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    creds = (config.gitea_admin_user, config.gitea_admin_password)


    # Search for team ID
    search_endpoint = f"{api_base}/orgs/{org_name}/teams/search"
    try:
        response = requests.get(
            search_endpoint,
            auth=HTTPBasicAuth(*creds),
            params={"q": team_name, "page": 1, "limit": 1},
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPError(f"Team search failed: HTTP {response.status_code}\n{response.text}")

        data = response.json()
        if not data.get("data"):
            raise HTTPError(f"Team '{team_name}' not found")

        team_id = data["data"][0]["id"]



        # Check if user is already a member (handle all status codes and fallback to explicit member list)
        member_check = requests.get(
            f"{api_base}/teams/{team_id}/members/{username}",
            auth=HTTPBasicAuth(*creds),
            timeout=30,
        )
        # Only print membership check status if not 404 (404 is expected for new members)
        if member_check.status_code != 404:
            print(f"Membership check status for user '{username}' in team '{team_name}': {member_check.status_code}")
        if member_check.status_code == 204:
            print(f"User '{username}' is already a member of team '{team_name}'. Skipping.")
            return
        elif member_check.status_code == 200:
            # Some Gitea versions return 200 with user info if member
            print(f"User '{username}' is already a member of team '{team_name}'. Skipping.")
            return
        elif member_check.status_code == 404:
            # Not a member, proceed silently
            pass
        else:
            # Fallback: check explicit member list
            members_resp = requests.get(
                f"{api_base}/teams/{team_id}/members",
                auth=HTTPBasicAuth(*creds),
                timeout=30,
            )
            if members_resp.status_code == 200:
                members = [m.get("username") for m in members_resp.json()]
                if username in members:
                    print(f"User '{username}' is already a member of team '{team_name}'. Skipping.")
                    return

        print(f"Adding user '{username}' to team '{team_name}' (id {team_id})...")

        # Add user to team
        add_response = requests.put(
            f"{api_base}/teams/{team_id}/members/{username}",
            auth=HTTPBasicAuth(*creds),
            timeout=30,
        )

        if add_response.status_code == 204:
            print(f"Added {username}.")
        elif add_response.status_code == 404:
            print(f"User {username} or team not found (HTTP 404).")
        else:
            raise HTTPError(f"Failed to add {username}: HTTP {add_response.status_code}\n{add_response.text}")

    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to add team member: {e}") from e


def create_repo(name: str, org: str, description: str = "") -> None:
    """
    Create a repository in an organization.

    Args:
        name: Repository name
        org: Organization name
        description: Optional repository description

    Raises:
        HTTPError: If repository creation fails
    """
    config = get_config()
    url = f"{config.gitea_api_url}/api/v1/repos/{org}/{name}"

    # Check if repository already exists
    if curl_exists(url, config.gitea_admin_user, config.gitea_admin_password):
        print(f"Repository '{name}' already exists under org '{org}'.")
        return

    # Create repository
    create_url = f"{config.gitea_api_url}/api/v1/orgs/{org}/repos"


    # Load post-repo payload template
    template_path = config.get_template_path("gitea/post-repo.json")
    with open(template_path) as f:
        template = Template(f.read())
        payload = json.loads(template.substitute(NAME=name, DESCRIPTION=description))
        payload_str = json.dumps(payload)

    print(f"Creating repository '{name}' under org '{org}'...")

    status_code, response = curl_post(
        create_url,
        payload_str,
        config.gitea_admin_user,
        config.gitea_admin_password,
    )


    if status_code == 201:
        print("Repository created successfully.")
        # Patch repo to enable auto-delete branch after merge
        patch_template_path = config.get_template_path("gitea/patch-repo.json")
        with open(patch_template_path) as f:
            patch_payload = json.load(f)
        patch_repo(name, org, patch_payload)
    else:
        raise HTTPError(f"Failed to create repository: HTTP {status_code}\n{response}")


def delete_repo(name: str, org: str) -> None:
    """
    Delete a repository from an organization.

    Args:
        name: Repository name
        org: Organization name

    Raises:
        HTTPError: If repository deletion fails
    """
    config = get_config()
    api_base = f"{config.gitea_api_url}/api/v1"
    url = f"{api_base}/repos/{org}/{name}"

    # Check if repository exists
    if not curl_exists(url, config.gitea_admin_user, config.gitea_admin_password):
        print(f"Repository '{name}' does not exist under org '{org}'; skipping deletion.")
        return

    print(f"Deleting repository '{name}' from org '{org}'...")

    try:
        response = requests.delete(
            url,
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            timeout=30,
        )

        if response.status_code == 204:
            print(f"✅ Repository '{name}' deleted successfully")
        elif response.status_code == 404:
            print(f"Repository '{name}' not found (already deleted?)")
        else:
            raise HTTPError(f"Failed to delete repository: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to delete repository: {e}") from e



def patch_repo(name: str, org: str, payload: dict) -> None:
    """
    Patch repository settings (e.g., default_delete_branch_after_merge).

    Args:
        name: Repository name
        org: Organization name
        payload: Dictionary of patch settings

    Raises:
        HTTPError: If operation fails
    """
    config = get_config()
    url = f"{config.gitea_api_url}/api/v1/repos/{org}/{name}"

    print(f"Patching repo '{name}' with: {payload}")

    try:
        response = requests.patch(
            url,
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            print(f"Repo '{name}' patched successfully.")
        else:
            print(f"Response: {response.text}")
            raise HTTPError(f"Failed to patch repository: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to patch repository: {e}") from e


def setup_branch_protection(
    name: str,
    org: str,
    teams: list,
    branch: str = "main",
    jenkins_folder: str = "",
    enable_status_check: bool = False,
) -> None:
    """
    Set branch protection rules on the 'main' branch of a repository.

    Args:
        name: Repository name
        org: Organization name
        teams: List of team names for protection rules (required)
        jenkins_folder: Jenkins folder name (e.g., 'acme-folder'). If not provided, defaults to '{org}-folder'
        enable_status_check: Enable Jenkins status check requirement (will construct context as '{jenkins_folder}/{name}/pipeline/head')

    Raises:
        HTTPError: If operation fails
    """
    config = get_config()
    url = f"{config.gitea_api_url}/api/v1/repos/{org}/{name}/branch_protections"

    # Check if protection already exists
    status_code, response = curl_get(url, config.gitea_admin_user, config.gitea_admin_password)

    if status_code == 200:
        try:
            protections = json.loads(response)
            for protection in protections:
                if protection.get("rule_name") == branch:
                    print(f"Branch protection for '{branch}' already exists under repo '{name}' in org '{org}'.")
                    return
        except json.JSONDecodeError:
            pass

    # Create protection
    template_path = config.get_template_path("gitea/branch-protection.json")
    with open(template_path) as f:
        content = f.read()

    # Load as JSON to manipulate status_check_contexts
    protection_data = json.loads(content)

    # Verify teams exist under org
    api_base = f"{config.gitea_api_url}/api/v1"
    creds = (config.gitea_admin_user, config.gitea_admin_password)
    valid_teams = []
    for team in teams:
        search_endpoint = f"{api_base}/orgs/{org}/teams/search"
        response = requests.get(
            search_endpoint,
            auth=HTTPBasicAuth(*creds),
            params={"q": team, "page": 1, "limit": 1},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and any(t["name"] == team for t in data["data"]):
                valid_teams.append(team)
            else:
                print(f"Warning: Team '{team}' not found in org '{org}', skipping.")
        else:
            print(f"Warning: Could not verify team '{team}' (HTTP {response.status_code}), skipping.")

    if not valid_teams:
        raise HTTPError(f"No valid teams found in org '{org}'. Aborting branch protection setup.")

    # Replace all relevant arrays in payload
    for arr in [
        "approvals_whitelist_teams",
        "merge_whitelist_teams",
        "push_whitelist_teams",
        "whitelist_teams"
    ]:
        if arr in protection_data:
            protection_data[arr] = valid_teams

    protection_str = json.dumps(protection_data)
    template = Template(protection_str)
    payload_str = template.substitute(GITEA_ADMIN_USER=config.gitea_admin_user)

    # Parse and update status check contexts if enabled
    payload_data = json.loads(payload_str)
    if enable_status_check:
        folder = jenkins_folder if jenkins_folder else f"{org}-folder"
        status_check_context = f"{folder}/{name}/pipeline/head"
        payload_data["status_check_contexts"] = [status_check_context]

    print(f"Setting branch protection rules on '{branch}' branch of '{name}'...")
    if enable_status_check:
        folder = jenkins_folder if jenkins_folder else f"{org}-folder"
        print(f"  - Requiring status check: {folder}/{name}/pipeline/head")

    # Update the rule_name in the payload to match the branch
    payload_data["rule_name"] = branch
    # Ensure repo name is included in the payload for correct association
    payload_data["repo_name"] = name
    payload_str = json.dumps(payload_data)

    status_code, response = curl_post(
        url,
        payload_str,
        config.gitea_admin_user,
        config.gitea_admin_password,
    )

    if status_code == 201:
        print("Branch protection created successfully.")
    else:
        raise HTTPError(f"Failed to create branch protection: HTTP {status_code}\n{response}")


def clone_repo(
    name: str,
    org: str,
    dest: str,
    username: str,
    password: str,
) -> None:
    """
    Clone a repository from Gitea.

    Args:
        name: Repository name
        org: Organization name
        dest: Destination directory (parent, repo will be created inside)
        username: Username for authentication
        password: Password for authentication

    Raises:
        DevOpsError: If clone fails
    """
    config = get_config()
    clone_url = f"http://{username}:{password}@localhost:{config.gitea_port}/{org}/{name}.git"
    target_dir = Path(dest)  # Clone directly to the specified directory

    # Ensure target is not in a repo
    ensure_not_child_of_repo(str(target_dir))

    # Check if target already exists
    if target_dir.exists() and (target_dir / ".git").exists():
        print(f"Destination '{target_dir}' already looks like a git repository; aborting.")
        return

    # Verify user exists and get email
    api_base = f"{config.gitea_api_url}/api/v1"
    print(f"Checking user '{username}' exists via {api_base}/users/{username}...")

    try:
        response = requests.get(
            f"{api_base}/users/{username}",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if response.status_code != 200:
            raise DevOpsError(f"User '{username}' not found (HTTP {response.status_code})")

        user_data = response.json()
        email = user_data.get("email")
        if not email:
            raise DevOpsError(f"No email found for user: {username}")

    except requests.exceptions.RequestException as e:
        raise DevOpsError(f"Failed to verify user: {e}") from e

    # Clone repository
    print(f"Cloning {org}/{name} -> {target_dir}...")
    target_dir.parent.mkdir(parents=True, exist_ok=True)  # Create parent directory if it doesn't exist

    try:
        run_command(["git", "clone", clone_url, str(target_dir)])
    except subprocess.CalledProcessError as e:
        raise DevOpsError(f"Git clone failed: {e.stderr}") from e

    # Configure repo-local git settings
    if (target_dir / ".git").exists():
        print("Configuring repo-local git user and credential helper...")

        # Set local user
        run_command(["git", "-C", str(target_dir), "config", "user.name", username])
        run_command(["git", "-C", str(target_dir), "config", "user.email", email])

        # Create credentials file
        cred_file = target_dir / ".git" / "credentials"
        cred_file.write_text(f"https://{username}:{password}@localhost:{config.gitea_port}\n")
        cred_file.chmod(0o600)

        # Configure credential helper
        run_command([
            "git",
            "-C",
            str(target_dir),
            "config",
            "credential.helper",
            f"store --file={cred_file}",
        ])

        # Update remote URL (without password)
        remote_url = f"http://{username}@localhost:{config.gitea_port}/{org}/{name}.git"
        run_command(["git", "-C", str(target_dir), "remote", "set-url", "origin", remote_url])

        # Set up remote branch tracking for current branch
        try:
            # Get current branch name
            result = subprocess.run(
                ["git", "-C", str(target_dir), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()
            
            if current_branch:
                # Set upstream tracking for current branch
                run_command([
                    "git",
                    "-C",
                    str(target_dir),
                    "branch",
                    "--set-upstream-to",
                    f"origin/{current_branch}",
                    current_branch,
                ])
                print(f"Set upstream tracking for branch '{current_branch}' to 'origin/{current_branch}'.")
        except subprocess.CalledProcessError:
            # If we can't set upstream, just skip it (might be detached HEAD or other edge case)
            pass

        print(f"Repository configured to use username '{username}' locally.")


def setup_dt_git_webhook() -> None:
    """
    Setup dt git webhook for integration (global admin scope).

    Raises:
        HTTPError: If operation fails
    """
    config = get_config()
    url = f"{config.gitea_api_url}/api/v1/admin/hooks?type=default"

    payload = {
        "type": "gitea",
        "config": {
            "url": "http://jenkins:8080/gitea-webhook/post",
            "content_type": "json",
        },
        "events": ["delete", "release", "repository", "status", "create", "pull_request", "pull_request_sync", "push"],
        "active": True,
    }

    # Get all global webhooks
    status_code, response = curl_get(
        url,
        config.gitea_admin_user,
        config.gitea_admin_password,
    )

    if status_code == 200:
        try:
            hooks = json.loads(response)
            for hook in hooks:
                if hook.get("config", {}).get("url") == "http://jenkins:8080/gitea-webhook/post":
                    print("dt git webhook already present; skipping creation.")
                    return
        except Exception:
            pass

    print("dt git webhook not found; creating...")
    status_code, response = curl_post(
        url,
        json.dumps(payload),
        config.gitea_admin_user,
        config.gitea_admin_password,
    )

    if status_code == 201:
        print("dt git webhook created successfully.")
    else:
        raise HTTPError(f"Failed to create dt git webhook: HTTP {status_code}\n{response}")

def remove_dt_git_webhook() -> None:
    """
    Remove dt git webhook for integration (global admin scope).

    Raises:
        HTTPError: If operation fails
    """
    config = get_config()
    url = f"{config.gitea_api_url}/api/v1/admin/hooks?type=default"

    # Get all global webhooks
    status_code, response = curl_get(
        url,
        config.gitea_admin_user,
        config.gitea_admin_password,
    )

    if status_code != 200:
        raise HTTPError(f"Failed to fetch webhooks: HTTP {status_code}\n{response}")

    try:
        hooks = json.loads(response)
    except Exception:
        raise HTTPError("Failed to parse webhook list response.")

    # Print all webhook URLs for debugging
    print("Existing global webhooks:")
    for hook in hooks:
        url_val = hook.get("config", {}).get("url")
        print(f"- id={hook.get('id')} url={url_val}")

    # Find dt git webhook by URL
    hook_id = None
    for hook in hooks:
        if hook.get("config", {}).get("url") == "http://jenkins:8080/gitea-webhook/post":
            hook_id = hook.get("id")
            break

    if not hook_id:
        print("dt git webhook already removed (not found).")
        return

    # Delete webhook using requests.delete (no ?type=default)
    delete_url = f"{config.gitea_api_url}/api/v1/admin/hooks/{hook_id}"
    try:
        response = requests.delete(
            delete_url,
            auth=HTTPBasicAuth(config.gitea_admin_user, config.gitea_admin_password),
            timeout=30,
        )
        if response.status_code == 204:
            print("dt git webhook removed successfully.")
        elif response.status_code == 404:
            print("dt git webhook not found (already deleted?)")
        else:
            raise HTTPError(f"Failed to remove dt git webhook: HTTP {response.status_code}\n{response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"Failed to remove dt git webhook: {e}") from e
