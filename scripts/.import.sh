#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
DEVOPS_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="${DEVOPS_DIR}/docker"
VOLUMES_DIR="${DOCKER_DIR}/.volumes"
TEMPLATE_DIR="${SCRIPT_DIR}/templates"
PROJECT_TEMPLATES_DIR="${DEVOPS_DIR}/project_templates"

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
source "$SCRIPT_DIR/project-functions.sh"

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

ensure_not_child_of_repo() {
  local path="$1"
  if [ -z "$path" ]; then
    echo "ensure_not_child_of_repo: path is required" >&2
    return 2
  fi

  local repo_root
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
  if [ -n "$repo_root" ]; then
    case "$(realpath "$path")" in
      "$repo_root"/*)
        echo "Path '$path' must not be inside the repository ($repo_root)." >&2
        return 3
        ;;
    esac
  fi
}

curl_get() {
  local url="$1"
  local user="$2"
  local pass="$3"

  local resp_and_code
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" -X GET -u "${user}:${pass}" -H "Content-Type: application/json" "${url}"); then
    echo "curl failed while checking for repository." >&2
    return 1
  fi

  local http_code
  http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  if [ "$http_code" = "200" ]; then
    printf '%s\n' "$(printf '%s' "$resp_and_code" | sed '$ d')" || true
    return 0
  elif [ "$http_code" = "404" ]; then
    return 4
  else
    echo "ERROR: HTTP ${http_code}" >&2
    printf '%s\n' "$(printf '%s' "$resp_and_code" | sed '$ d')" >&2 || true
    return 2
  fi
}

# curl_exists: lightweight wrapper that returns a small, easy-to-check exit
# contract and emits short diagnostics. Intended for callers that only need to
# know whether a resource exists (HTTP 200) or not (HTTP 404), while treating
# other HTTP responses as errors. Exit codes:
#   0 -> exists (HTTP 200)
#   1 -> not found (HTTP 404)
#   2 -> other HTTP error or curl/network failure
curl_exists() {
  local url="$1"
  local user="$2"
  local pass="$3"

  curl -X GET "$url" -H "Accept: application/json" -u "${user}:${pass}" -o /dev/null -s -w "%{http_code}\n" | grep -q '^200$' && {
    return 0
  }
  return 1
}

curl_post() {
  local url="$1"
  local data="$2"
  local user="$3"
  local pass="$4"

  local resp_and_code
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" -X POST -u "${user}:${pass}" -H "Content-Type: application/json" -d "${data}" "${url}"); then
    echo "curl failed while creating repository." >&2
    return 1
  fi

  local http_code
  http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  if [ "$http_code" = "201" ]; then
    echo "SUCCESS."
    return 0
  else
    echo "ERROR: HTTP ${http_code}" >&2
    printf '%s\n' "$(printf '%s' "$resp_and_code" | sed '$ d')" >&2 || true
    return 2
  fi
}
