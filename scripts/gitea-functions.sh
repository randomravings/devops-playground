#!/usr/bin/env bash
set -euo pipefail

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
  if ! docker exec -i gitea su git -c "gitea admin user create --username '${NAME}' --password '${PASSWORD}' --email '${EMAIL}' ${ADMIN_FLAG}"; then
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
  local NAME="" ORG="" DESCRIPTION=""

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


  local api_base="http://localhost:3000/api/v1"
  local creds="${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}"
  local endpoint="${api_base}/orgs/${ORG}/repos"
  echo "Creating repository '${NAME}' under org '${ORG}'..."

  # Build JSON payload; include only provided fields
  local payload
  payload="{"
  payload+="\"name\":\"${NAME}\""
  payload+=""
  payload+=",\"description\":\"${DESCRIPTION}\"";
  payload+=",\"auto_init\":true"
  payload+=",\"private\":false"
  payload+="}"

  local resp_and_code
  if ! resp_and_code=$(curl -sS -w "\n%{http_code}" --user "${creds}" -H "Content-Type: application/json" -X POST "$endpoint" -d "$payload"); then
    echo "curl failed while creating repository." >&2
    return 3
  fi

  local http_code=$(printf '%s' "$resp_and_code" | tail -n1)
  local body
  body=$(printf '%s' "$resp_and_code" | sed '$d')
  if [ "$http_code" = "201" ]; then
    echo "Repository '${NAME}' created."
    return 0
  elif [ "$http_code" = "409" ] || [ "$http_code" = "422" ]; then
    echo "Repository '${NAME}' already exists (HTTP ${http_code})."
    return 0
  else
    echo "Failed to create repository: HTTP ${http_code}" >&2
    printf '%s\n' "$body" >&2 || true
    return 4
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

  # Do not overwrite an existing repo
  if [ -d "$DEST/.git" ] || ( [ -d "$DEST" ] && git -C "$DEST" rev-parse --is-inside-work-tree >/dev/null 2>&1 ); then
    echo "Destination '$DEST' already looks like a git repository; aborting to avoid overwrite." >&2
  else
    echo "Cloning ${ORG}/${NAME} -> ${DEST} (protocol=http)..."
    mkdir -p "$DEST" || true
    git clone "$clone_url" "$DEST"
    git -C "$DEST" remote set-url origin "$clone_url"
  fi
}