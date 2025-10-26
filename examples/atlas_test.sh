#!/usr/bin/env bash
#
# Test Atlas CLI in Jenkins
#

set -e

echo "=== Testing Atlas CLI in Jenkins ==="

# Create test schemas
docker exec jenkins sh -c 'cat > /tmp/schema_v1.sql << EOF
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT,
    content TEXT
);
EOF'

docker exec jenkins sh -c 'cat > /tmp/schema_v2.sql << EOF
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT,
    published BOOLEAN DEFAULT FALSE
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
EOF'

echo ""
echo "=== Schema Diff: v1 -> v2 ==="
docker exec jenkins atlas schema diff \
    --from "file:///tmp/schema_v1.sql" \
    --to "file:///tmp/schema_v2.sql" \
    --dev-url "sqlite://file?mode=memory"

echo ""
echo "✅ Atlas is working correctly!"
