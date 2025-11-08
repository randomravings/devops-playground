"""Configuration management for DevOps Tools."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration class for managing environment variables and paths."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_file: Optional path to .env file (for advanced use cases only).
        """
        # Determine base directories (repo root is now two levels up from this file)
        self.devops_dir = Path(__file__).parent.parent.resolve()
        self.script_dir = self.devops_dir / "scripts"
        self.docker_dir = self.devops_dir / "docker"
        self.volumes_dir = self.docker_dir / ".volumes"
        self.template_dir = self.devops_dir / "templates"
        self.projects_dir = self.devops_dir / "projects"

        # Load environment variables only if explicitly provided
        if env_file:
            load_dotenv(env_file)

    @property
    def docker_env_name(self) -> str:
        """Docker environment name."""
        return os.getenv("DOCKER_ENV_NAME", "devops-env")

    @property
    def gitea_port(self) -> int:
        """Gitea port."""
        return int(os.getenv("GITEA_PORT", "3000"))

    @property
    def gitea_default_org(self) -> str:
        """Default Gitea organization."""
        return os.getenv("GITEA_DEFAULT_ORG", "acme")

    @property
    def gitea_admin_user(self) -> str:
        """Gitea admin username."""
        return os.getenv("GITEA_ADMIN_USER", "admin")

    @property
    def gitea_admin_password(self) -> str:
        """Gitea admin password."""
        return os.getenv("GITEA_ADMIN_PASSWORD", "secret")

    @property
    def gitea_internal_url(self) -> str:
        """Gitea internal URL (from inside Docker network)."""
        return os.getenv("GITEA_INTERNAL_URL", f"http://gitea:{self.gitea_port}")

    @property
    def gitea_advertised_url(self) -> str:
        """Gitea advertised URL (from host)."""
        return os.getenv("GITEA_ADVERTISED_URL", f"http://localhost:{self.gitea_port}")

    @property
    def gitea_api_url(self) -> str:
        """Gitea API base URL."""
        return os.getenv("GITEA_API_URL", f"http://localhost:{self.gitea_port}")

    @property
    def jenkins_admin_user(self) -> str:
        """Jenkins admin username."""
        return os.getenv("JENKINS_ADMIN_USER", "admin")

    @property
    def jenkins_admin_password(self) -> str:
        """Jenkins admin password."""
        return os.getenv("JENKINS_ADMIN_PASSWORD", "secret")

    @property
    def jenkins_port(self) -> int:
        """Jenkins port."""
        return int(os.getenv("JENKINS_PORT", "8080"))

    @property
    def jenkins_url(self) -> str:
        """Jenkins URL."""
        return os.getenv("JENKINS_URL", f"http://localhost:{self.jenkins_port}")

    def get_template_path(self, template_name: str) -> Path:
        """
        Get path to a template file.

        Args:
            template_name: Template name relative to templates directory
                          (e.g., "jenkins/jenkins-org.xml")

        Returns:
            Path to template file

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path

    def get_project_template_path(self, template_name: str) -> Path:
        """
        Get path to a project template directory.

        Args:
            template_name: Project template name (e.g., "maven-project")

        Returns:
            Path to project template directory

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.projects_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Project template not found: {template_path}")
        return template_path


# Global config instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get or create the global configuration instance.

    Args:
        env_file: Optional path to .env file

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None
