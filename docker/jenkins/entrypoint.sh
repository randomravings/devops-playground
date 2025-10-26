#!/bin/bash
set -e

# Fix Docker socket permissions
# The docker group GID might not match between host and container
if [ -S /var/run/docker.sock ]; then
    DOCKER_SOCKET_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock)
    
    echo "Docker socket GID: $DOCKER_SOCKET_GID"
    
    # If socket is owned by root (GID 0), just make it accessible to jenkins
    if [ "$DOCKER_SOCKET_GID" = "0" ]; then
        echo "Docker socket owned by root - setting permissions to 666"
        chmod 666 /var/run/docker.sock || true
    else
        # Otherwise, adjust the docker group to match
        CURRENT_GID=$(getent group docker | cut -d: -f3)
        if [ "$DOCKER_SOCKET_GID" != "$CURRENT_GID" ]; then
            echo "Fixing docker group GID: $CURRENT_GID -> $DOCKER_SOCKET_GID"
            groupmod -g "$DOCKER_SOCKET_GID" docker
            usermod -aG docker jenkins
        fi
    fi
fi

# Execute the original Jenkins entrypoint
exec /usr/local/bin/jenkins.sh "$@"
