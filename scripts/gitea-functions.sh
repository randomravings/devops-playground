#!/usr/bin/env bash
set -euo pipefail

gitea_setup_default_webhook() {
  local url="http://localhost:3000/api/v1/admin/hooks"
  local payload='{"type":"gitea","config":{"url":"http://jenkins:8080/gitea-webhook/post","content_type":"json"},"events":["push","pull_request"],"active":true}'
  local hooks_body
  hooks_body=$(curl_get "$url?type=default" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD");
  if printf '%s' "$hooks_body" | grep -q 'http://jenkins:8080/gitea-webhook/post'; then
    echo "Default webhook already present; skipping creation."
    return 0
  else
    echo "Default webhook not found; creating..."
    curl_post "$url" "$payload" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD"
  fi
}

gitea_create_user_usage() {
  cat <<EOF
Usage: gitea_create_user username password org [--admin]

Creates a user in Gitea. If arguments are omitted the function will prompt interactively.
EOF
}

gitea_create_user() {
  local NAME="" PASSWORD="" ORG="" IS_ADMIN=0

  # parse positional and flags
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help)
        gitea_create_user_usage; return 0;;
      --admin)
        IS_ADMIN=1; shift;;
      -n|--name)
        NAME="$2"; shift 2;;
      -p|--password)
        PASSWORD="$2"; shift 2;;
      -o|--org)
        ORG="$2"; shift 2;;
      *)
        if [ -z "$NAME" ]; then NAME="$1";
        elif [ -z "$PASSWORD" ]; then PASSWORD="$1";
        elif [ -z "$ORG" ]; then ORG="$1";
        else
          shift; continue
        fi
        shift;;
    esac
  done

  # prompts for missing
  if [ -z "$NAME" ]; then read -rp "Username: " NAME; fi
  if [ -z "$PASSWORD" ]; then read -rsp "Password: " PASSWORD; echo; fi
  if [ -z "$ORG" ]; then read -rp "Organization (used to build email as ORG.demo): " ORG; fi

  local EMAIL="${NAME}@${ORG}.demo"
  local ADMIN_FLAG=""
  if [ "$IS_ADMIN" -eq 1 ]; then ADMIN_FLAG="--admin"; fi

  echo "Creating user '${NAME}' (email: ${EMAIL}) ${IS_ADMIN:+as admin}..."
  if ! docker exec -i gitea su git -c "gitea admin user create --username '${NAME}' --password '${PASSWORD}' --email '${EMAIL}' ${ADMIN_FLAG} --must-change-password=false"; then
    local rc=$?
    echo "Failed to create user ${NAME} (exit ${rc})." >&2
    return ${rc}
  fi
  echo "User '${NAME}' created (or already exists)."
}


gitea_create_org_usage() {
  cat <<EOF
Usage: gitea_create_org org owner [description]

Creates an organization in Gitea. Prompts for missing arguments.
EOF
}

gitea_create_org() {
  local ORG_NAME="" OWNER="" DESC=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_create_org_usage; return 0;;
      -n|--name) ORG_NAME="$2"; shift 2;;
      -o|--owner) OWNER="$2"; shift 2;;
      -d|--description) DESC="$2"; shift 2;;
      *) if [ -z "$ORG_NAME" ]; then ORG_NAME="$1"; elif [ -z "$OWNER" ]; then OWNER="$1"; fi; shift;;
    esac
  done

  if [ -z "$ORG_NAME" ]; then read -rp "Organization name: " ORG_NAME; fi
  if [ -z "$OWNER" ]; then read -rp "Owner username: " OWNER; fi
  # Do not prompt for description (non-essential). If provided, include it in payload.

  # Prefer REST API to create orgs (admin token or admin user/password)
  local api_base="${GITEA_API_URL:-http://localhost:3000}/api/v1"
  # pass auth args as an array so curl receives them correctly
  local -a auth_args=("--user" "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}")

  # Build payload; omit description if empty
  local payload
  if [ -n "$DESC" ]; then
    payload=$(printf '{"username":"%s","full_name":"%s","description":"%s"}' "$ORG_NAME" "$ORG_NAME" "$DESC")
  else
    payload=$(printf '{"username":"%s","full_name":"%s"}' "$ORG_NAME" "$ORG_NAME")
  fi

  echo "Creating organization '${ORG_NAME}' with owner '${OWNER}' via REST API ${api_base}/orgs..."

  # Capture both response body and HTTP status in a single variable (no temp file)
  local resp_and_code
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" "${auth_args[@]}" -H "Content-Type: application/json" -X POST "${api_base}/orgs" -d "$payload"); then
    echo "curl failed while creating org (network/SSL error)." >&2
    return 3
  fi

  # The last line is the HTTP status code; everything before is the body
  local http_code
  http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  local body
  body=$(printf '%s' "$resp_and_code" | sed '$d')

  if [ "$http_code" = "201" ]; then
    echo "Organization '${ORG_NAME}' created."
    return 0
  elif [ "$http_code" = "409" ] || [ "$http_code" = "422" ]; then
    echo "Organization '${ORG_NAME}' already exists (HTTP ${http_code})."
    return 0
  else
    echo "Failed to create organization: HTTP ${http_code}" >&2
    printf '%s
'"$body" >&2 || true
    return 4
  fi
}

gitea_create_team_usage() {
  cat <<EOF
Usage: gitea_create_team team org [permission] [description]

Creates a team under an organization. Permission: read, write, admin (default: write).
EOF
}

gitea_create_team() {
  local TEAM_NAME="" ORG_NAME="" PERM="write" DESC=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_create_team_usage; return 0;;
      -n|--name) TEAM_NAME="$2"; shift 2;;
      -o|--org) ORG_NAME="$2"; shift 2;;
      -p|--permission) PERM="$2"; shift 2;;
      -d|--description) DESC="$2"; shift 2;;
      *) if [ -z "$TEAM_NAME" ]; then TEAM_NAME="$1"; elif [ -z "$ORG_NAME" ]; then ORG_NAME="$1"; elif [ -z "$PERM" ]; then PERM="$1"; else DESC="$1"; fi; shift;;
    esac
  done

  if [ -z "$TEAM_NAME" ]; then read -rp "Team name: " TEAM_NAME; fi
  if [ -z "$ORG_NAME" ]; then read -rp "Organization name: " ORG_NAME; fi
  if [ -z "$PERM" ]; then PERM="write"; fi
  # Do not prompt for description

  case "$PERM" in read|write|admin) ;; *) echo "Invalid permission: $PERM" >&2; return 2;; esac

  # Create team via REST API: POST /orgs/{org}/teams
  local api_base="http://localhost:3000/api/v1"
  local -a auth_args=("--user" "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}")
  local endpoint="${api_base}/orgs/${ORG_NAME}/teams"

  local payload
  # Build full payload that matches the working Swagger payload
  local UNITS_JSON='["repo.actions","repo.code","repo.issues","repo.ext_issues","repo.wiki","repo.ext_wiki","repo.pulls","repo.releases","repo.projects"]'
  if [ -n "$DESC" ]; then
    payload=$(printf '{"name":"%s","permission":"%s","description":"%s","can_create_org_repo":true,"includes_all_repositories":true,"units":%s}' "$TEAM_NAME" "$PERM" "$DESC" "$UNITS_JSON")
  else
    payload=$(printf '{"name":"%s","permission":"%s","can_create_org_repo":true,"includes_all_repositories":true,"units":%s}' "$TEAM_NAME" "$PERM" "$UNITS_JSON")
  fi

  echo "Creating team '${TEAM_NAME}' in org '${ORG_NAME}' with permission '${PERM}' via REST API..."
  local resp_and_code
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" "${auth_args[@]}" -H "Content-Type: application/json" -X POST "${endpoint}" -d "$payload"); then
    echo "curl failed while creating team (network/SSL error)." >&2
    return 3
  fi
  local http_code
  http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  if [ "$http_code" = "201" ]; then
    echo "Team '${TEAM_NAME}' created."
    return 0
  elif [ "$http_code" = "409" ] || [ "$http_code" = "422" ]; then
    echo "Team '${TEAM_NAME}' already exists (HTTP ${http_code})."
    return 0
  else
    echo "Failed to create team: HTTP ${http_code}" >&2
    printf '%s
'"$(printf '%s' "$resp_and_code" | sed '
$ d')" >&2 || true
    return 4
  fi
}

gitea_add_team_members_usage() {
  cat <<EOF
Usage: gitea_add_team_members team org username [username...]

Adds one or more users to a team. Prompts for missing values.
EOF
}

gitea_add_team_members() {
  local TEAM_NAME="" ORG_NAME="" USER=""

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_add_team_members_usage; return 0;;
      -t|--team) TEAM_NAME="$2"; shift 2;;
      -o|--org) ORG_NAME="$2"; shift 2;;
      -u|--user) USER="$2"; shift 2;;
      -*) echo "Unknown option: $1" >&2; return 2;;
      *) shift;;
    esac
  done

  if [ -z "$TEAM_NAME" ]; then read -rp "Team name: " TEAM_NAME; fi
  if [ -z "$ORG_NAME" ]; then read -rp "Organization name: " ORG_NAME; fi
  if [ -z "$USER" ]; then read -rp "Username to add: " USER; fi

  local api_base="http://localhost:3000/api/v1"
  local creds="${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}"
  local endpoint="${api_base}/orgs/${ORG_NAME}/teams/search"
  local query=$(printf '%s' "$TEAM_NAME" | sed 's/ /%20/g')

  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" --user "${creds}" -H "Accept: application/json" "${endpoint}?q=${query}&page=1&limit=1"); then
    echo "curl failed while creating repository." >&2
    return 3
  fi

  local http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  local body=$(printf '%s' "$resp_and_code" | sed '$d')
  if [ "$http_code" != "200" ]; then
    echo "Team search failed for '${TEAM_NAME}' (HTTP ${http_code})." >&2
    printf '%s\n' "$body" >&2 || true
    return 4
  fi

  # Extract id from JSON body: look for first occurrence within data array
  local team_id=$(printf '%s' "$body" | grep -o '"id"[[:space:]]*:[[:space:]]*[0-9]\+' | head -n1 | grep -o '[0-9]\+')
  if [ -z "$team_id" ]; then
    echo "Failed to parse team id from search response for '${TEAM_NAME}'." >&2
    printf '%s\n' "$body" >&2 || true
    return 4
  fi

  echo "Adding user '${USER}' to team '${TEAM_NAME}' (id ${team_id})..."
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" --user "${creds}" -X PUT "${api_base}/teams/${team_id}/members/${USER}" ); then
    echo "curl failed while adding ${USER}; continuing." >&2
    continue
  fi
  http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  body=$(printf '%s' "$resp_and_code" | sed '$d')
  if [ "$http_code" = "204" ]; then
    echo "Added ${USER}."
  elif [ "$http_code" = "404" ]; then
    echo "User ${USER} or team not found (HTTP 404)." >&2
  else
    echo "Failed to add ${USER}: HTTP ${http_code}." >&2
    printf '%s\n' "$body" >&2 || true
  fi
}

gitea_create_repo_usage() {
  cat <<EOF
Usage: gitea_create_repo -n|--name NAME -o|--org ORG [-d|--description DESC]

Creates a repository using the Gitea REST API. If --org is supplied the repo is
created under that organization (POST /orgs/{org}/repos). Otherwise POST /user/repos
EOF
}

gitea_create_repo() {
  local NAME="" ORG="" TEAM="" DESCRIPTION=""

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_create_repo_usage; return 0;;
      -o|--org) ORG="$2"; shift 2;;
      -n|--name) NAME="$2"; shift 2;;
      -d|--description) DESCRIPTION="$2"; shift 2;;
      *)
    esac
  done

  if [ -z "$NAME" ]; then read -rp "Repository name: " NAME; fi
  if [ -z "$ORG" ]; then read -rp "Organization to create repo under: " ORG; fi

  local url=""
  local payload=""
  local template=""
  
  url="http://localhost:3000/api/v1/repos/${ORG}/${NAME}"

  if curl_exists "$url" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD"; then
    echo "Repository '${NAME}' already exists under org '${ORG}'."
  else
    url="http://localhost:3000/api/v1/orgs/${ORG}/repos"
    
    export NAME DESCRIPTION
    template="$TEMPLATE_DIR/gitea/repo.json"
    payload=$(envsubst < "$template")

    echo "Creating repository '${NAME}' under org '${ORG}'..."
    curl_post "$url" "$payload" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD"
  fi
}

gitea_branch_protection_usage() {
  cat <<EOF
Usage: gitea_branch_protection -n|--name NAME -o|--org ORG [-t|--team TEAM]
Set branch protection rules on the 'main' branch of a repository.
EOF
}

gitea_branch_protection() {
  local NAME="" ORG="" TEAM=""

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_branch_protection_usage; return 0;;
      -n|--name) NAME="$2"; shift 2;;
      -o|--org) ORG="$2"; shift 2;;
      -t|--team) TEAM="$2"; shift 2;;
      *) shift;;
    esac
  done

  if [ -z "$NAME" ]; then read -rp "Repository name: " NAME; fi
  if [ -z "$ORG" ]; then read -rp "Organization name: " ORG; fi
  if [ -z "$TEAM" ]; then read -rp "Team (optional): " TEAM; fi

  local url="http://localhost:3000/api/v1/repos/${ORG}/${NAME}/branch_protections"

  if curl_get "$url" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD" | jq -e '.[] | select(.rule_name == "main")' >/dev/null; then
    echo "Branch proection for '${NAME}' already exists under org '${ORG}'."
  else
    export TEAM GITEA_ADMIN_USER
    local template="$TEMPLATE_DIR/gitea/branch-protection.json"
    local payload
    payload=$(envsubst < "$template")
    echo "Setting branch protection rules on 'main' branch of '${NAME}'..."
    curl_post "$url" "$payload" "$GITEA_ADMIN_USER" "$GITEA_ADMIN_PASSWORD"
  fi
}


gitea_clone_repo_usage() {
  cat <<EOF
Usage: gitea_clone_repo -n|--name NAME -o|--org ORG [-d|--dest DIR] [--protocol http|ssh] [--branch BRANCH] [--depth N]

Clone a repository from the local Gitea server to a path outside the devops environment.
By default protocol is http and destination is ./<repo-name>.
If using http and the repo is private, you can pass --user and --password (or rely on GITEA_ADMIN_USER/GITEA_ADMIN_PASSWORD).
EOF
}

gitea_clone_repo() {
  local NAME="" ORG="" DEST="" USERNAME="" PASSWORD=""

  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help) gitea_clone_repo_usage; return 0;;
      -n|--name) NAME="$2"; shift 2;;
      -o|--org) ORG="$2"; shift 2;;
      -d|--dest) DEST="$2"; shift 2;;
      -u|--user) USERNAME="$2"; shift 2;;
      -p|--password) PASSWORD="$2"; shift 2;;
      *) shift;;
    esac
  done

  if [ -z "$NAME" ]; then read -rp "Repository name: " NAME; fi
  if [ -z "$ORG" ]; then read -rp "Organization name: " ORG; fi
  if [ -z "$DEST" ]; then read -rp "Destination directory: " DEST; fi
  if [ -z "$USERNAME" ]; then read -rp "Username: " USERNAME; fi
  if [ -z "$PASSWORD" ]; then read -rsp "Password: " PASSWORD; echo; fi

  local clone_url="http://${USERNAME}:${PASSWORD}@localhost:3000/${ORG}/${NAME}.git"
  local target_dir="$DEST/$NAME"

  ensure_not_child_of_repo "$target_dir"

  # Do not overwrite an existing repo
  if [ -d "$target_dir/.git" ] || ( [ -d "$target_dir" ] && git -C "$target_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 ); then
    echo "Destination '$target_dir' already looks like a git repository; aborting to avoid overwrite." >&2
  else

    # Verify the user exists in Gitea via REST API and extract email if available.
    # If GITEA_API_URL is set, use it; otherwise default to localhost.
    local api_base="${GITEA_API_URL:-http://localhost:3000}/api/v1"
    echo "Checking user '${USERNAME}' exists via ${api_base}/users/${USERNAME}..."
    local resp_and_code
    if ! resp_and_code=$(curl -sS -w "\n%{http_code}" -H "Accept: application/json" "${api_base}/users/${USERNAME}"); then
      echo "Failed to contact Gitea API while verifying user '${USERNAME}' (network/SSL error)." >&2
      return 1
    fi
    local http_code http_code=$(printf '%s' "$resp_and_code" | tail -n1)
    local body=$(printf '%s' "$resp_and_code" | sed '$d')
    if [ "$http_code" != "200" ]; then
      echo "User '${USERNAME}' not found (HTTP ${http_code}); aborting." >&2
      printf '%s
  ' "$body" >&2 || true
      return 0
    fi

    # Try to extract email from JSON: look for "email":"..."; fall back to username@org.demo
    local email=$(printf '%s' "$body" | grep -o '"email"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed 's/"email"[[:space:]]*:[[:space:]]*"\([^"]*\)"/\1/') || true
    if [ -z "$email" ]; then
      echo "No email found for user: {USERNAME}" >&2
      return 3
    fi

    echo "Cloning ${ORG}/${NAME} -> ${target_dir} (protocol=http)..."
    mkdir -p "$DEST" || true
    git clone "$clone_url" "$target_dir"

    # Configure repo-local git user and credentials so pushes use the provided
    # username instead of global credentials. We store credentials in a
    # repo-local file and set credential.helper to read from it.
    if [ -d "$target_dir/.git" ]; then
      echo "Configuring repo-local git user and credential helper..."
      # Set local user.name and user.email (email built from org)
      git -C "$target_dir" config user.name "$USERNAME"
      git -C "$target_dir" config user.email "$email"

      # Create a repo-scoped credentials file and point credential.helper to it.
      # Format: https://<username>:<password>@host
      local cred_file="$target_dir/.git/credentials"
      # Ensure any existing credential file is removed to avoid leaking other creds
      rm -f "$cred_file"
      printf 'https://%s:%s@localhost:3000\n' "$USERNAME" "$PASSWORD" > "$cred_file"
      chmod 600 "$cred_file"

      # Configure git to use the file-based credential helper for this repo only
      # The helper 'store --file=<path>' was added in newer git versions; use
      # "store --file=<path>" which is supported by Git that includes this feature.
      git -C "$target_dir" config credential.helper "store --file=$cred_file"

      # Sanitize remote to remove embedded password and keep username in URL so
      # origin uses the username, and credential helper supplies the password.
      # e.g. https://username@localhost:3000/org/repo.git
      local remote_url_no_pass="http://${USERNAME}@localhost:3000/${ORG}/${NAME}.git"
      git -C "$target_dir" remote set-url origin "$remote_url_no_pass"
      echo "Repository configured to use username '$USERNAME' locally."
    fi
  fi
}