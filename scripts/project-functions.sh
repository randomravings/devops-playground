#!/usr/bin/env bash
set -euo pipefail

init_commit() {
  if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <existing-target-dir> <commit-message>" >&2
    exit 1
  fi

  TARGET_DIR=$1
  COMMIT_MESSAGE=$2

  if [ ! -d "$TARGET_DIR/.git" ]; then
    echo "Directory '$TARGET_DIR' is not a git repository." >&2
    return 1
  fi

  pushd "$TARGET_DIR"
    git add -A
    git commit -m "$COMMIT_MESSAGE"
    git push
  popd
}

init_maven() {
  if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <existing-target-dir>" >&2
    exit 1
  fi

  TARGET_DIR=$1

  JENKINSFILE_PATH="$TARGET_DIR/Jenkinsfile"
  if [ -f "$JENKINSFILE_PATH" ]; then
    echo "Jenkinsfile already exists at '$JENKINSFILE_PATH'; skipping creation." >&2
  else
    # Split TARGET_DIR into parent directory and leaf folder name
    PARENT_DIR=$(dirname -- "$TARGET_DIR")
    LEAF_DIR=$(basename -- "$TARGET_DIR")

    JENKINSFILE_PATH="$TARGET_DIR/Jenkinsfile"
    if [ -f "$JENKINSFILE_PATH" ]; then
      echo "Jenkinsfile already exists at '$JENKINSFILE_PATH'; skipping creation." >&2
    else
      echo "Creating a simple Jenkinsfile at '$JENKINSFILE_PATH'."
      cat "${TEMPLATE_DIR}/Jenkinsfile" > "$JENKINSFILE_PATH"
    fi

    pushd "$PARENT_DIR"
      mvn archetype:generate -DgroupId=acme -DartifactId="${LEAF_DIR}" -DarchetypeArtifactId=maven-archetype-quickstart -DarchetypeVersion=1.5 -DinteractiveMode=false
      pushd "$LEAF_DIR"
        git checkout -b feature-init
        git add -A
        git commit -m "chore: initialize Maven project with Jenkinsfile"
        git push -u origin feature-init
      popd
    popd
  fi
}

init_dbci_tools() {
  if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <existing-target-dir>" >&2
    exit 1
  fi

  TARGET_DIR=$1

  if [ -f "$TARGET_DIR/Jenkinsfile" ]; then
    echo "Jenkins file exists in directory, aborting." >&2
  else
    cp -Rp "${PROJECT_TEMPLATES_DIR}/dbci-tools/." "$TARGET_DIR/"
  fi
}

init_postgres() {
  if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <existing-target-dir>" >&2
    exit 1
  fi

  TARGET_DIR=$1

  if [ -f "$TARGET_DIR/Jenkinsfile" ]; then
    echo "Jenkins file exists in directory, aborting." >&2
  else
    cp -Rp "${PROJECT_TEMPLATES_DIR}/db-postgres-example/." "$TARGET_DIR/"
  fi
}