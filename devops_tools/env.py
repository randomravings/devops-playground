"""Environment lifecycle management for DevOps environments."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template
from typing import Optional

from . import gitea
from .config import get_config
from .utils import docker_cp, docker_exec, wait_for_http, DevOpsError


def setup() -> None:
    """
    Setup the DevOps environment (Jenkins, Gitea, Docker).

    This function:
    1. Creates necessary directories
    2. Configures Jenkins init scripts
    3. Starts Docker containers
    4. Waits for services to be ready
    5. Creates admin user
    6. Sets up Jenkins CLI

    Raises:
        DevOpsError: If setup fails
    """
    config = get_config()

    # Validate required directories
    if not config.docker_dir.exists():
        raise DevOpsError(f"Docker directory not found: {config.docker_dir}")
    if not config.template_dir.exists():
        raise DevOpsError(f"Template directory not found: {config.template_dir}")

    # Create volumes directory structure
    jenkins_dir = config.volumes_dir / "jenkins"
    jenkins_init_dir = jenkins_dir / "init.groovy.d"
    jenkins_dir.mkdir(parents=True, exist_ok=True)
    jenkins_init_dir.mkdir(parents=True, exist_ok=True)

    # Create Jenkins basic security init script from template
    basic_security_template = config.get_template_path("jenkins/basic-security.groovy")
    jenkins_init_script = jenkins_init_dir / "basic-security.groovy"

    with open(basic_security_template) as f:
        template = Template(f.read())

    init_content = template.substitute(
        user=config.jenkins_admin_user,
        password=config.jenkins_admin_password,
    )

    with open(jenkins_init_script, "w") as f:
        f.write(init_content)

    jenkins_init_script.chmod(0o644)
    print(f"Wrote {jenkins_init_script} (admin={config.jenkins_admin_user})")

    # Copy Jenkins configuration
    jenkins_yaml_template = config.get_template_path("jenkins/jenkins.yaml")
    jenkins_yaml = jenkins_dir / "jenkins.yaml"
    shutil.copy(jenkins_yaml_template, jenkins_yaml)

    print(f"Starting devops environment from {config.docker_dir}/docker-compose.yml")

    # Check if Jenkins container is already running
    compose_file = config.docker_dir / "docker-compose.yml"
    check_cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "-p",
        config.docker_env_name,
        "ps",
        "--status=running",
        "-q",
        "jenkins",
    ]

    result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
    jenkins_running = bool(result.stdout.strip())

    # Start containers
    up_cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "-p",
        config.docker_env_name,
        "up",
        "-d",
    ]

    if not jenkins_running:
        up_cmd.append("--build")

    subprocess.run(up_cmd, check=True)

    # Wait for Gitea to be ready
    print(f"Waiting for Gitea to become ready at {config.gitea_advertised_url} ...")
    if not wait_for_http(config.gitea_advertised_url, timeout=120, interval=2):
        raise DevOpsError("Timeout waiting for Gitea")

    # Create Gitea admin user
    print(f"Creating admin user '{config.gitea_admin_user}' ...")
    try:
        gitea.create_user(
            config.gitea_admin_user,
            config.gitea_admin_password,
            "system",  # Using "system" as org for admin email
            admin=True,
        )
    except Exception as e:
        print(f"gitea_create_user returned error (user may already exist): {e}")

    # Setup Jenkins CLI
    _setup_jenkins_cli(config)

    # Setup dt git webhook for Jenkins integration
    try:
        gitea.setup_dt_git_webhook()
    except Exception as e:
        print(f"Warning: dt git webhook setup failed: {e}")

    print("✅ DevOps environment setup complete!")


def _setup_jenkins_cli(config) -> None:
    """
    Setup Jenkins CLI inside the container.
    
    Downloads jenkins-cli.jar from the running Jenkins instance and
    creates the auth file for authentication.

    Args:
        config: Config instance
    """
    # Check if jenkins-cli.jar already exists
    check_result = docker_exec("jenkins", "[ -f /usr/local/bin/jenkins-cli.jar ]", capture_output=True)
    if check_result.returncode == 0:
        print("jenkins-cli.jar already present in container; skipping download.")
    else:
        jenkins_cli_url = f"{config.jenkins_url}/jnlpJars/jenkins-cli.jar"
        
        # Wait for Jenkins CLI endpoint to be ready
        if not wait_for_http(jenkins_cli_url, timeout=60, interval=2):
            print("Warning: jenkins-cli endpoint did not become available within timeout")
            return
        
        print("jenkins-cli available; attempting download...")
        download_cmd = (
            f"curl -fsSL '{jenkins_cli_url}' -o /usr/local/bin/jenkins-cli.jar && "
            f"chmod 755 /usr/local/bin/jenkins-cli.jar"
        )
        
        result = docker_exec("jenkins", download_cmd, user="0", capture_output=True)
        if result.returncode != 0:
            print(f"Warning: failed to download jenkins-cli.jar: {result.stderr}")
            return
    
    # Check if auth file exists
    check_result = docker_exec("jenkins", "[ -f /usr/local/bin/jenkins-cli.auth ]", capture_output=True)
    if check_result.returncode == 0:
        print("Skipping creation of jenkins-cli auth file because one already exists.")
    else:
        print("Creating jenkins-cli auth file inside container...")
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_auth:
            tmp_auth.write(f"{config.jenkins_admin_user}:{config.jenkins_admin_password}")
            tmp_auth_path = tmp_auth.name

        try:
            docker_cp(tmp_auth_path, "jenkins:/tmp/jenkins-cli.auth")
            move_cmd = (
                "mv /tmp/jenkins-cli.auth /usr/local/bin/jenkins-cli.auth && "
                "chown jenkins:jenkins /usr/local/bin/jenkins-cli.auth && "
                "chmod 600 /usr/local/bin/jenkins-cli.auth"
            )
            docker_exec("jenkins", move_cmd, user="0")
        finally:
            Path(tmp_auth_path).unlink(missing_ok=True)


def teardown() -> None:
    """
    Teardown the DevOps environment.

    This removes all containers, volumes, and local state.

    Raises:
        DevOpsError: If teardown fails
    """
    config = get_config()

    print("Tearing down devops environment (compose down -v)")

    compose_file = config.docker_dir / "docker-compose.yml"
    down_cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "-p",
        config.docker_env_name,
        "down",
        "-v",
    ]

    try:
        subprocess.run(down_cmd, check=False)
    except Exception as e:
        print(f"Warning: docker compose down failed: {e}")

    # Remove volumes directory
    if config.volumes_dir.exists():
        try:
            shutil.rmtree(config.volumes_dir)
            print(f"Removed {config.volumes_dir}")
        except Exception as e:
            print(f"Warning: failed to remove volumes directory: {e}")

    print("✅ DevOps environment teardown complete!")
