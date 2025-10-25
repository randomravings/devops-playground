#!/usr/bin/env bash
set -euo pipefail

source "../scripts/.import.sh"

env_setup

gitea_create_team -n devops -o acme -p admin -d "DevOps Team"
gitea_create_user -n john -p secret -o acme
gitea_add_team_members -t devops -o acme -u john
gitea_create_repo -n demo-repo -o acme -d "Demo repository created via script"
gitea_clone_repo -n demo-repo -o acme -d ./repos/demo-repo -u john -p secret

jenkins_create_credentials -i gitea-credentials -u john -p secret -d "Gitea user credentials"
jenkins_create_maven_pipeline -n demo-pipeline -r http://gitea:3000/acme/demo-repo.git -b main -c gitea-credentials 