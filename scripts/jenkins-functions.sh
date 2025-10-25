#!/usr/bin/env bash
set -euo pipefail

jenkins_create_credentials_usage() {
  cat <<'EOF'
Usage: jenkins_create_credentials -i ID -u USERNAME -p PASSWORD [-d DESCRIPTION]

Creates a username/password credential in Jenkins with the given ID.
EOF
}

jenkins_create_credentials() {
  local CRED_ID="" CRED_DESC="" CRED_USER="" CRED_PASS=""

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) jenkins_create_credentials_usage; return 0;;
      -i|--id) CRED_ID="$2"; shift 2;;
      -d|--description) CRED_DESC="$2"; shift 2;;
      -u|--username) CRED_USER="$2"; shift 2;;
      -p|--password) CRED_PASS="$2"; shift 2;;
      *) echo "Unknown option: $1" >&2; return 2;;
    esac
  done

  if [ -z "$CRED_ID" ] || [ -z "$CRED_USER" ] || [ -z "$CRED_PASS" ]; then
    echo "jenkins_create_credentials: id, username and password are required" >&2
    jenkins_create_credentials_usage
    return 2
  fi

  local template="$TEMPLATE_DIR/jenkins-creds.xml"
  if [ ! -f "$template" ]; then
    echo "jenkins_create_credentials: template not found: $template" >&2
    return 3
  fi

  export CRED_ID CRED_DESC CRED_USER CRED_PASS
  local xml=$(envsubst < "$template")

  # Stream the credentials XML into the create-credentials-by-xml CLI command.
  printf '%s' "$xml" | docker exec -i jenkins /usr/local/bin/jenkins-cli create-credentials-by-xml system::system::jenkins _
}

jenkins_create_maven_pipeline_usage() {
  echo "Usage: jenkins_create_maven_pipeline -n NAME -r GIT_URL [-b BRANCH] [-c CREDENTIALS] [-d DESCRIPTION]"
}

jenkins_create_maven_pipeline() {
  local JOB_NAME="" JOB_GIT_URL="" JOB_GIT_BRANCH="" JOB_GIT_CREDS="" JOB_DESC=""

  # parse positional and flags
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help)
        jenkins_create_maven_pipeline_usage; return 0;;
      -n|--name)
        JOB_NAME="$2"; shift 2;;
      -r|--repo)
        JOB_GIT_URL="$2"; shift 2;;
      -b|--branch)
        JOB_GIT_BRANCH="$2"; shift 2;;
      -c|--credentials)
        JOB_GIT_CREDS="$2"; shift 2;;
      -d|--description)
        JOB_DESC="$2"; shift 2;;
      -*) echo "Unknown option: $1" >&2; return 2;;
      *) shift;;
    esac
  done

  if [ -z "$JOB_NAME" ] || [ -z "$JOB_GIT_URL" ] || [ -z "$JOB_GIT_CREDS" ]; then
    echo "jenkins_create_maven_pipeline: job name, git repo, and credentials are required" >&2
    jenkins_create_maven_pipeline_usage
    return 2
  fi

  if [ -z "$JOB_GIT_BRANCH" ]; then
    JOB_GIT_BRANCH="main"
  fi

  if [ -z "$JOB_DESC" ]; then
    JOB_DESC="Maven pipeline job for repo $JOB_GIT_URL"
  fi

  local template="$TEMPLATE_DIR/jenkins-pipeline-job.xml"
  if [ ! -f "$template" ]; then
    echo "jenkins_create_maven_pipeline: template not found: $template" >&2
    return 3
  fi

  export JOB_GIT_URL JOB_GIT_BRANCH JOB_DESC JOB_GIT_CREDS
  local xml=$(envsubst < "$template")

  # Use a pipe so the full XML is sent on stdin to the CLI inside the container.
  printf '%s' "$xml" | docker exec -i jenkins /usr/local/bin/jenkins-cli create-job "$JOB_NAME"
}
