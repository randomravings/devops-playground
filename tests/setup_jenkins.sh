#!/usr/bin/env bash
set -euo pipefail

source "../scripts/.import.sh"

jenkins_create_org -n acme-org -o acme -c gitea-credentials