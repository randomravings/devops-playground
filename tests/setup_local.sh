#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <existing-empty-local-path-not-inside-repo>" >&2
	exit 2
fi

LOCAL_PATH=$1

source "../scripts/.import.sh"

gitea_clone_repo -n dbci-tools -o acme -d "$LOCAL_PATH" -u john -p secret || true
gitea_clone_repo -n demo-repo -o acme -d "$LOCAL_PATH" -u john -p secret || true
init_postgres "$LOCAL_PATH/demo-repo" || true