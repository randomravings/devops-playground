#!/usr/bin/env bash
set -euo pipefail


# Environment lifecycle helpers (inline implementation)
env_setup() {


  # --- environment validation and defaults ---
  # Required top-level directories/variables: VOLUMES_DIR, SCRIPT_DIR, DOCKER_DIR, DOCKER_ENV_NAME
  : "${VOLUMES_DIR:?VOLUMES_DIR must be set and non-empty}"
  : "${SCRIPT_DIR:?SCRIPT_DIR must be set and non-empty}"
  : "${DOCKER_DIR:?DOCKER_DIR must be set and non-empty}"
  : "${DOCKER_ENV_NAME:?DOCKER_ENV_NAME must be set and non-empty}"

  # Export and default admin credentials (safe quoted expansions)

  # Local copies / derived paths
  local jenkins_dir="${VOLUMES_DIR}/jenkins"
  local jenkins_init_dir="${jenkins_dir}/init.groovy.d"
  local jenkins_init="${jenkins_init_dir}/basic-security.groovy"
  local basic_security_template="${SCRIPT_DIR}/templates/basic-security.groovy"

  mkdir -p "${VOLUMES_DIR}" "$jenkins_dir" "$jenkins_init_dir"

  # Create the basic-security.groovy init script from template if it doesn't already exist
  # Preconfigure admin user and disable the setup wizard
	sed -e "s/<user>/${JENKINS_ADMIN_USER}/g" -e "s/<pass>/${JENKINS_ADMIN_PASSWORD}/g" "$basic_security_template" > "$jenkins_init"
  chmod 644 "$jenkins_init"
  echo "Wrote $jenkins_init (admin=${JENKINS_ADMIN_USER})"

  echo "Starting devops environment from ${DOCKER_DIR}/docker-compose.yml"

  # If the jenkins container is already running, do a simple 'up -d' to avoid downtime.
  # Otherwise do a full 'up -d --build' to build missing images and start
  if [ -n "$(docker compose -f "${DOCKER_DIR}/docker-compose.yml" -p "${DOCKER_ENV_NAME}" ps --status=running -q jenkins)" ]; then
    docker compose -f "${DOCKER_DIR}/docker-compose.yml" -p ${DOCKER_ENV_NAME} up -d
  else
    docker compose -f "${DOCKER_DIR}/docker-compose.yml" -p ${DOCKER_ENV_NAME} up -d --build
  fi

  # Wait for Gitea to be ready
  echo "Waiting for Gitea to become ready at http://localhost:3000 ..."
  # wait_for_http accepts either host:port or full URL depending on implementation; try both forms
  if ! wait_for_http "http://localhost:3000" 120 2; then
    echo "Timeout waiting for Gitea" >&2
    return 3
  fi

  # Create admin user if not exists using the inlined gitea_create_user function.
  echo "Creating admin user '${GITEA_ADMIN_USER}' ..."
  # Call gitea_create_user; it will prompt if password/org are empty
  if ! gitea_create_user "${GITEA_ADMIN_USER}" "${GITEA_ADMIN_PASSWORD}" "${GITEA_DEFAULT_ORG}" --admin; then
    echo "gitea_create_user returned non-zero (user may already exist)." >&2
  fi

  echo "Creating organization '${GITEA_DEFAULT_ORG}' with owner '${GITEA_ADMIN_USER}'..."
  if ! gitea_create_org "${GITEA_DEFAULT_ORG}" "${GITEA_ADMIN_USER}"; then
    echo "gitea_create_org returned non-zero (org may already exist)." >&2
  fi

  if docker exec jenkins sh -c '[ -f /usr/local/bin/jenkins-cli.jar ]' >/dev/null 2>&1; then
    echo "jenkins-cli.jar already present in container; skipping download."
  else
    local jenkins_cli_url="http://localhost:8080/jnlpJars/jenkins-cli.jar"
    # Wait for the CLI endpoint to be ready using the existing helper (timeout = 60s)
    if ! wait_for_http "${jenkins_cli_url}" 60 2; then
      echo "Warning: jenkins-cli endpoint did not become available within timeout; the container will remain up but CLI will be unavailable." >&2
      return 4
    fi

    echo "jenkins-cli available; attempting single download..."
    # Download once as root and set executable bit
    if ! docker exec -u 0 jenkins sh -c "curl -fsSL '${jenkins_cli_url}' -o /usr/local/bin/jenkins-cli.jar && chmod 755 /usr/local/bin/jenkins-cli.jar"; then
      echo "Warning: failed to download jenkins-cli.jar; the container will remain up but CLI will be unavailable." >&2
      return 4
    fi
  fi

  if docker exec jenkins sh -c '[ -f /usr/local/bin/jenkins-cli.auth ]' >/dev/null 2>&1; then
    echo "Skipping creation of jenkins-cli auth file because one already exists inside the container."
  else
    echo "Creating jenkins-cli auth file inside container..."
    local tmp_auth=$(mktemp)
    printf '%s:%s' "${JENKINS_ADMIN_USER}" "${JENKINS_ADMIN_PASSWORD}" > "$tmp_auth"
    docker cp "$tmp_auth" jenkins:/tmp/jenkins-cli.auth
    # Set ownership to the 'jenkins' user inside the container so the CLI process can read it
    docker exec -u 0 jenkins sh -c 'mv /tmp/jenkins-cli.auth /usr/local/bin/jenkins-cli.auth && chown jenkins:jenkins /usr/local/bin/jenkins-cli.auth && chmod 600 /usr/local/bin/jenkins-cli.auth'
    rm -f "$tmp_auth"
  fi
}

env_teardown() {

  : "${VOLUMES_DIR:?VOLUMES_DIR must be set and non-empty}"
  : "${DOCKER_DIR:?DOCKER_DIR must be set and non-empty}"

  echo "Tearing down devops environment (compose down -v)"
  docker compose -f "${DOCKER_DIR}/docker-compose.yml" -p devops-env down -v || true
  rm -rf "${VOLUMES_DIR}" || true
}
