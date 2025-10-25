#!/usr/bin/env bash
set -euo pipefail

AUTH_FILE=/usr/local/bin/jenkins-cli.auth
if [ -f "$AUTH_FILE" ]; then
	java -jar /usr/local/bin/jenkins-cli.jar -s http://host.docker.internal:8080 -auth @${AUTH_FILE} "$@"
else
	java -jar /usr/local/bin/jenkins-cli.jar -s http://host.docker.internal:8080 "$@"
fi