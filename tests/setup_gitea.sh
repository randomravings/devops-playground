#!/usr/bin/env bash
set -euo pipefail

source "../scripts/.import.sh"

gitea_setup_default_webhook

tmpdir=$(mktemp -d)
gitea_create_repo -n dbci-tools -o acme -d "DB CI Tools repository"
gitea_clone_repo -n dbci-tools -o acme -d "$tmpdir" -u admin -p secret || true
init_dbci_tools "$tmpdir/dbci-tools" || true
init_commit "$tmpdir/dbci-tools" "Initial commit of dbci-tools setup" || true
trap "rm -rf $tmpdir" EXIT

gitea_create_team -n devops -o acme -p admin -d "DevOps Team"
gitea_create_user -n john -p secret -o acme
gitea_create_user -n alice -p secret -o acme
gitea_add_team_members -t devops -o acme -u john
gitea_add_team_members -t devops -o acme -u alice
gitea_create_repo -n demo-repo -o acme -d "Demo repository created via script"
gitea_branch_protection -n demo-repo -o acme -t "devops"