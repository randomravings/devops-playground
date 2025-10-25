#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
DEVOPS_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="${DEVOPS_DIR}/docker"
VOLUMES_DIR="${DOCKER_DIR}/.volumes"
TEMPLATE_DIR="${SCRIPT_DIR}/templates"

export DEVOPS_DIR
export SCRIPT_DIR
export DOCKER_DIR
export VOLUMES_DIR
export TEMPLATE_DIR

source "$SCRIPT_DIR/.env-vars"
export JENKINS_ADMIN_USER="${JENKINS_ADMIN_USER:-admin}"
export JENKINS_ADMIN_PASSWORD="${JENKINS_ADMIN_PASSWORD:-admin}"
export GITEA_ADMIN_USER="${GITEA_ADMIN_USER:-admin}"
export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-secret}"
export GITEA_DEFAULT_ORG="${GITEA_DEFAULT_ORG:-acme}"

source "$SCRIPT_DIR/env-functions.sh"
source "$SCRIPT_DIR/gitea-functions.sh"
source "$SCRIPT_DIR/jenkins-functions.sh"

wait_for_http() {
  # $1: URL
  # $2: timeout in seconds (default 60)
  local url="$1"
  local timeout="${2:-60}"
  local interval=2
  local elapsed=0

  while true; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -E "200|302" >/dev/null; then
      return 0
    fi
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "Timeout waiting for $url after ${timeout}s" >&2
      return 1
    fi
    sleep $interval
    elapsed=$((elapsed + interval))
  done
}