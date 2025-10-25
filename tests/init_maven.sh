
#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <existing-target-dir>" >&2
	exit 1
fi

TARGET_DIR=$1

if [ ! -d "$TARGET_DIR" ]; then
	echo "Target directory '$TARGET_DIR' does not exist. Please provide an existing directory." >&2
	exit 2
fi

if [ -f "$TARGET_DIR/pom.xml" ]; then
	echo "Target directory '$TARGET_DIR' exists already has a pom.xml — aborting." >&2
	exit 3
fi

# Split TARGET_DIR into parent directory and leaf folder name
PARENT_DIR=$(dirname -- "$TARGET_DIR")
LEAF_DIR=$(basename -- "$TARGET_DIR")

GITIGNORE_PATH="$TARGET_DIR/.gitignore"
if [ ! -f "$GITIGNORE_PATH" ]; then
    echo "Creating $GITIGNORE_PATH and adding .mvn/"
    printf '%s\n' '.mvn/' > "$GITIGNORE_PATH"
else
    if ! grep -qxF '.mvn/' "$GITIGNORE_PATH" >/dev/null 2>&1; then
    echo "Adding .mvn/ to $GITIGNORE_PATH"
    printf '\n%s\n' '.mvn/' >> "$GITIGNORE_PATH"
    fi
fi

pushd "$PARENT_DIR"
	mvn archetype:generate -DgroupId=acme -DartifactId="${LEAF_DIR}" -DarchetypeArtifactId=maven-archetype-quickstart -DarchetypeVersion=1.5 -DinteractiveMode=false
popd

