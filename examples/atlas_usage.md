# Atlas CLI Usage in Jenkins

Atlas is now available in the Jenkins container for database schema management and comparison.

## Common Atlas Commands

### 1. Schema Diff (Compare two SQL files) - **Recommended for Playground**

Use SQLite in-memory database for dev environment (fastest, no setup required):

```groovy
stage('Schema Diff') {
    steps {
        sh '''
            atlas schema diff \
                --from "file://db/schema/old" \
                --to "file://db/schema/new" \
                --dev-url "sqlite://file?mode=memory"
        '''
    }
}
```

For PostgreSQL-specific syntax, you can also use Docker (requires Docker socket mount):

```groovy
stage('Schema Diff - PostgreSQL') {
    steps {
        sh '''
            atlas schema diff \
                --from "file://db/schema/old" \
                --to "file://db/schema/new" \
                --dev-url "docker://postgres/15/dev?search_path=public"
        '''
    }
}
```

### 2. Schema Inspect (Extract schema from database)

```groovy
stage('Inspect Schema') {
    steps {
        sh '''
            atlas schema inspect \
                --url "postgres://user:pass@host:5432/dbname?sslmode=disable" \
                > current_schema.sql
        '''
    }
}
```

### 3. Schema Apply (Apply migrations)

```groovy
stage('Apply Schema') {
    steps {
        sh '''
            atlas schema apply \
                --url "postgres://user:pass@host:5432/dbname?sslmode=disable" \
                --to "file://db/schema" \
                --dev-url "docker://postgres/15/dev?search_path=public"
        '''
    }
}
```

### 4. Schema Diff with Docker Dev Database

Atlas can spin up a temporary PostgreSQL container for schema comparisons:

```bash
atlas schema diff \
    --from "file://schema1.sql" \
    --to "file://schema2.sql" \
    --dev-url "docker://postgres/15/dev?search_path=public"
```

### 5. Generate Migration Plan

```bash
atlas schema diff \
    --from "file://old" \
    --to "file://new" \
    --dev-url "docker://postgres/15/dev" \
    --format '{{ sql . "  " }}'
```

## Example Jenkinsfile Integration

```groovy
pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Schema Validation') {
            steps {
                script {
                    // Compare current schema against main branch
                    sh '''
                        git fetch origin main
                        git show origin/main:db/schema > /tmp/main-schema.sql
                        
                        atlas schema diff \
                            --from "file:///tmp/main-schema.sql" \
                            --to "file://db/schema" \
                            --dev-url "docker://postgres/15/dev?search_path=public" \
                            > schema_diff.txt
                        
                        cat schema_diff.txt
                    '''
                }
            }
        }
        
        stage('Generate Migration') {
            when {
                branch 'feature/*'
            }
            steps {
                sh '''
                    atlas schema diff \
                        --from "file://db/baseline" \
                        --to "file://db/schema" \
                        --dev-url "docker://postgres/15/dev" \
                        --format '{{ sql . "  " }}' \
                        > migration.sql
                    
                    echo "=== Generated Migration ==="
                    cat migration.sql
                '''
            }
        }
    }
}
```

## Benefits of Atlas

1. **Automatic Diffing**: Compares schemas intelligently, handling column order, constraints, etc.
2. **Docker Integration**: Can spin up temporary databases for validation
3. **Multiple Formats**: Supports PostgreSQL, MySQL, SQLite, and more
4. **Migration Generation**: Automatically generates SQL migration scripts
5. **Declarative**: Define desired state, Atlas figures out how to get there

## Resources

- [Atlas Documentation](https://atlasgo.io/docs)
- [Atlas CLI Reference](https://atlasgo.io/cli-reference)
- [PostgreSQL Guide](https://atlasgo.io/guides/postgres)
