"""Utility functions for HTTP requests, Docker operations, and common helpers."""

import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth


class DevOpsError(Exception):
    """Base exception for DevOps Tools errors."""
    pass


class HTTPError(DevOpsError):
    """Exception raised for HTTP errors."""
    pass


class DockerError(DevOpsError):
    """Exception raised for Docker operations errors."""
    pass


def wait_for_http(url: str, timeout: int = 60, interval: int = 2) -> bool:
    """
    Wait for an HTTP endpoint to become available.

    Args:
        url: The URL to check
        timeout: Maximum time to wait in seconds (default: 60)
        interval: Time between checks in seconds (default: 2)

    Returns:
        True if endpoint becomes available, False if timeout

    Raises:
        HTTPError: If there's a network error
    """
    elapsed = 0
    while elapsed < timeout:
        try:
            response = requests.get(url, timeout=5, allow_redirects=True)
            if response.status_code in (200, 302):
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(interval)
        elapsed += interval

    return False


def curl_get(url: str, username: str, password: str) -> Tuple[int, str]:
    """
    Perform HTTP GET request with basic auth.

    Args:
        url: The URL to request
        username: Username for basic auth
        password: Password for basic auth

    Returns:
        Tuple of (status_code, response_body)

    Raises:
        HTTPError: If request fails
    """
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"GET request failed: {e}") from e


def curl_post(url: str, data: str, username: str, password: str) -> Tuple[int, str]:
    """
    Perform HTTP POST request with basic auth.

    Args:
        url: The URL to request
        data: JSON data to post
        username: Username for basic auth
        password: Password for basic auth

    Returns:
        Tuple of (status_code, response_body)

    Raises:
        HTTPError: If request fails
    """
    try:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            data=data,
            timeout=30,
        )
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"POST request failed: {e}") from e


def curl_put(url: str, username: str, password: str, data: Optional[str] = None) -> Tuple[int, str]:
    """
    Perform HTTP PUT request with basic auth.

    Args:
        url: The URL to request
        username: Username for basic auth
        password: Password for basic auth
        data: Optional JSON data to put

    Returns:
        Tuple of (status_code, response_body)

    Raises:
        HTTPError: If request fails
    """
    try:
        response = requests.put(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            data=data,
            timeout=30,
        )
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        raise HTTPError(f"PUT request failed: {e}") from e


def curl_exists(url: str, username: str, password: str) -> bool:
    """
    Check if a resource exists via HTTP HEAD/GET.

    Args:
        url: The URL to check
        username: Username for basic auth
        password: Password for basic auth

    Returns:
        True if resource exists (HTTP 200), False otherwise
    """
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def docker_exec(
    container: str, command: str, user: Optional[str] = None, capture_output: bool = True
) -> subprocess.CompletedProcess:
    """
    Execute a command inside a Docker container.

    Args:
        container: Container name or ID
        command: Command to execute
        user: Optional user to run as (e.g., "0" for root)
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess instance

    Raises:
        DockerError: If command fails
    """
    cmd = ["docker", "exec"]
    if user:
        cmd.extend(["-u", user])
    cmd.append(container)
    cmd.extend(["sh", "-c", command])

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        return result
    except subprocess.SubprocessError as e:
        raise DockerError(f"Docker exec failed: {e}") from e


def docker_exec_interactive(container: str, command: str, user: Optional[str] = None) -> int:
    """
    Execute a command inside a Docker container interactively.

    Args:
        container: Container name or ID
        command: Command to execute
        user: Optional user to run as

    Returns:
        Exit code

    Raises:
        DockerError: If command fails
    """
    cmd = ["docker", "exec", "-i"]
    if user:
        cmd.extend(["-u", user])
    cmd.append(container)
    cmd.extend(["sh", "-c", command])

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except subprocess.SubprocessError as e:
        raise DockerError(f"Docker exec failed: {e}") from e


def docker_cp(source: str, dest: str) -> None:
    """
    Copy files to/from a Docker container.

    Args:
        source: Source path (container:path or local path)
        dest: Destination path (container:path or local path)

    Raises:
        DockerError: If copy fails
    """
    cmd = ["docker", "cp", source, dest]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise DockerError(f"Docker cp failed: {e.stderr}") from e


def ensure_not_child_of_repo(path: str) -> None:
    """
    Ensure a path is not inside a git repository.

    Args:
        path: Path to check

    Raises:
        DevOpsError: If path is inside a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            repo_root = Path(result.stdout.strip()).resolve()
            target_path = Path(path).resolve()
            if repo_root in target_path.parents or repo_root == target_path:
                raise DevOpsError(f"Path '{path}' must not be inside the repository ({repo_root})")
    except FileNotFoundError:
        # git not available, skip check
        pass


def run_command(
    command: list[str], cwd: Optional[str] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a shell command.

    Args:
        command: Command and arguments as list
        cwd: Working directory
        check: Whether to raise exception on non-zero exit

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=check)
