"""Jenkins operations: credentials, organization folders, and job management."""

from pathlib import Path
from string import Template
from typing import Optional

from .config import get_config
from .utils import docker_exec_interactive, DevOpsError


def create_credentials(
    cred_id: str,
    username: str,
    password: str,
    description: str = "",
) -> None:
    """
    Create a username/password credential in Jenkins.

    Args:
        cred_id: Credential ID
        username: Username
        password: Password
        description: Optional description

    Raises:
        DevOpsError: If credential creation fails
    """
    config = get_config()

    # Check if credentials already exist
    if credentials_exist(cred_id):
        print(f"Credential '{cred_id}' already exists in Jenkins; skipping creation.")
        return

    template_path = config.get_template_path("jenkins/jenkins-creds.xml")
    with open(template_path) as f:
        template = Template(f.read())

    xml = template.substitute(
        CRED_ID=cred_id,
        CRED_DESC=description,
        CRED_USER=username,
        CRED_PASS=password,
    )

    print(f"Creating Jenkins credential '{cred_id}'...")

    # Pipe XML via stdin to avoid shell escaping issues
    import subprocess
    
    cmd = ["docker", "exec", "-i", "jenkins", "/usr/local/bin/jenkins-cli", 
           "create-credentials-by-xml", "system::system::jenkins", "_"]
    result = subprocess.run(cmd, input=xml.encode(), check=False, capture_output=True)

    if result.returncode != 0:
        stderr = result.stderr.decode() if result.stderr else ""
        raise DevOpsError(f"Failed to create Jenkins credential (exit code {result.returncode}): {stderr}")

    print(f"✅ Created credential '{cred_id}'")


def create_org(
    job_name: str,
    org_name: str,
    credentials: str,
    description: str = "",
) -> None:
    """
    Create an organization folder job in Jenkins for Gitea.

    Args:
        job_name: Jenkins job name
        org_name: Gitea organization name
        credentials: Jenkins credentials ID
        description: Optional job description

    Raises:
        DevOpsError: If job creation fails
    """
    config = get_config()

    # Check if job already exists
    if job_exists(job_name):
        print(f"Job '{job_name}' already exists in Jenkins; skipping creation.")
        return

    if not description:
        description = (
            f"Organization folder job created by script. "
            f"{org_name} @ {config.gitea_internal_url}"
        )

    template_path = config.get_template_path("jenkins/jenkins-org.xml")
    with open(template_path) as f:
        template = Template(f.read())

    xml = template.substitute(
        JOB_ORG_NAME=org_name,
        JOB_ORG_URL=config.gitea_internal_url,
        JOB_ORG_CREDS=credentials,
        JOB_DESC=description,
    )

    print(f"Creating Jenkins job '{job_name}'...")

    # Pipe XML via stdin to avoid shell escaping issues
    from .utils import docker_exec
    import subprocess
    
    cmd = ["docker", "exec", "-i", "jenkins", "/usr/local/bin/jenkins-cli", "create-job", job_name]
    result = subprocess.run(cmd, input=xml.encode(), check=False, capture_output=True)

    if result.returncode != 0:
        stderr = result.stderr.decode() if result.stderr else ""
        raise DevOpsError(f"Failed to create Jenkins job (exit code {result.returncode}): {stderr}")

    print(f"✅ Created job '{job_name}' in Jenkins.")


def job_exists(job_name: str) -> bool:
    """
    Check if a Jenkins job exists.

    Args:
        job_name: Job name to check

    Returns:
        True if job exists, False otherwise
    """
    from .utils import docker_exec

    result = docker_exec(
        "jenkins",
        f"/usr/local/bin/jenkins-cli get-job '{job_name}'",
        capture_output=True,
    )
    return result.returncode == 0


def credentials_exist(cred_id: str) -> bool:
    """
    Check if a Jenkins credential exists.

    Args:
        cred_id: Credential ID to check

    Returns:
        True if credential exists, False otherwise
    """
    return get_credential_name(cred_id) is not None


def get_credential_name(cred_id: str) -> Optional[str]:
    """
    Get the name of a credential by ID.

    Args:
        cred_id: Credential ID

    Returns:
        Credential name or None if not found
    """
    from .utils import docker_exec

    cmd = (
        "/usr/local/bin/jenkins-cli list-credentials system::system::jenkins | "
        f"awk -v id='{cred_id}' '"
        "/^=+/ {next} /^Id[[:space:]]+Name/ {next} /^[[:space:]]*$/ {next} "
        "{ line=$0; sub(/^[[:space:]]+/,\"\",line); sub(/[[:space:]]+$/,\"\",line); "
        "key=$1; sub(\"^\"key\"[[:space:]]+\",\"\",line); "
        "if (key==id) { print line; exit } }'"
    )

    result = docker_exec("jenkins", cmd, capture_output=True)

    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    return None
