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

  local template="$TEMPLATE_DIR/jenkins/jenkins-creds.xml"
  if [ ! -f "$template" ]; then
    echo "jenkins_create_credentials: template not found: $template" >&2
    return 3
  fi

  export CRED_ID CRED_DESC CRED_USER CRED_PASS
  local xml=$(envsubst < "$template")

  # Stream the credentials XML into the create-credentials-by-xml CLI command.
  printf '%s' "$xml" | docker exec -i jenkins /usr/local/bin/jenkins-cli create-credentials-by-xml system::system::jenkins _
}

jenkins_create_org_usage() {
  echo "Usage: jenkins_create_org -n NAME -o ORG -r REPO -c CREDENTIALS [-d DESCRIPTION]"
}

jenkins_create_org() {
  local JOB_NAME="" JOB_ORG_NAME="" JOB_ORG_CREDS="" JOB_DESC=""

  # parse positional and flags
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help)
        jenkins_create_org_usage; return 0;;
      -n|--name)
        JOB_NAME="$2"; shift 2;;
      -o|--org)
        JOB_ORG_NAME="$2"; shift 2;;
      -c|--credentials)
        JOB_ORG_CREDS="$2"; shift 2;;
      -d|--description)
        JOB_DESC="$2"; shift 2;;
      -*) echo "Unknown option: $1" >&2; return 2;;
      *) shift;;
    esac
  done

  if [ -z "$JOB_NAME" ] || [ -z "$JOB_ORG_NAME" ] || [ -z "$JOB_ORG_CREDS" ]; then
    echo "jenkins_create_org: job name, git org, and credentials are required" >&2
    jenkins_create_org_usage
    return 2
  fi

  if jenkins_job_exists "$JOB_NAME"; then
    echo "Job '$JOB_NAME' already exists in Jenkins; skipping creation."
    return 0
  fi

  JOB_ORG_URL="${GITEA_INTERNAL_URL}"

  if [ -z "$JOB_DESC" ]; then
    JOB_DESC="Organization folder job created by script. $JOB_ORG_NAME @ $JOB_ORG_URL"
  fi

  local template="$TEMPLATE_DIR/jenkins/jenkins-org.xml"
  if [ ! -f "$template" ]; then
    echo "jenkins_create_maven_pipeline: template not found: $template" >&2
    return 3
  fi

  local tmp_xml=$(mktemp)
  export JOB_ORG_NAME JOB_ORG_URL JOB_ORG_CREDS JOB_DESC
  local xml=$(envsubst < "$template")

  # Use a pipe so the full XML is sent on stdin to the CLI inside the container.
  echo "$xml" | docker exec -i jenkins /usr/local/bin/jenkins-cli create-job "$JOB_NAME"
  echo "✅ Created job '$JOB_NAME' in Jenkins."
}

jenkins_get_credential_name() {
  local CRED_ID="$1"
  docker exec jenkins /usr/local/bin/jenkins-cli list-credentials system::system::jenkins \
  | awk -v id="$CRED_ID" '
    /^=+/ {next} /^Id[[:space:]]+Name/ {next} /^[[:space:]]*$/ {next}
    { line=$0; sub(/^[[:space:]]+/,"",line); sub(/[[:space:]]+$/,"",line);
      key=$1; sub("^"key"[[:space:]]+","",line);
      if (key==id) { print line; exit }
    }'
}

jenkins_job_exists() {
  local JOB_NAME="$1"
  if docker exec jenkins /usr/local/bin/jenkins-cli get-job "$JOB_NAME" >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}