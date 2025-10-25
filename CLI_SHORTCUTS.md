# CLI Shortcuts

Quick reference for short command aliases.

## Command Shortcuts

### Main Command

- `devops-tools` → `dt`

### Environment Commands

| Long Form | Short Form | Description |
|-----------|------------|-------------|
| `dt environment setup` | `dt env up` | Setup environment |
| `dt environment teardown` | `dt env down` | Teardown environment |

### Git/Gitea Commands

| Long Form | Short Form | Description |
|-----------|------------|-------------|
| `dt git create-user` | `dt git user` | Create user |
| `dt git create-org` | `dt git org` | Create organization |
| `dt git create-team` | `dt git team` | Create team |
| `dt git add-team-member` | `dt git add-member` | Add member to team |
| `dt git create-repo` | `dt git repo` | Create repository |
| `dt git branch-protection` | `dt git protect` | Setup branch protection |
| `dt git setup-webhook` | `dt git webhook` | Setup webhook |
| `dt git clone` | `dt git clone` | Clone repository |

Alternative: `dt gitea` works the same as `dt git`

### CI/Jenkins Commands

| Long Form | Short Form | Description |
|-----------|------------|-------------|
| `dt ci create-credentials` | `dt ci creds` | Create credentials |
| `dt ci create-org` | `dt ci org` | Create org folder job |
| `dt ci job-exists` | `dt ci check` | Check if job exists |

Alternatives: `dt jenkins` or `dt j` work the same as `dt ci`

### Project Commands

| Long Form | Short Form | Description |
|-----------|------------|-------------|
| `dt projects init-maven` | `dt proj maven` | Init Maven project |
| `dt projects init-postgres` | `dt proj pg` | Init PostgreSQL project |
| `dt projects init-dbci-tools` | `dt proj dbci` | Init dbci-tools project |
| `dt projects commit` | `dt proj commit` | Commit and push |

Alternative: `dt p` works the same as `dt projects` or `dt proj`

## Examples

### Quick setup/teardown

```bash
dt env up      # Instead of: devops-tools environment setup
dt env down    # Instead of: devops-tools environment teardown
```

### Quick Git operations

```bash
dt git user john --org acme         # Create user
dt git org myorg --owner admin      # Create org
dt git team dev --org myorg         # Create team
dt git repo myapp --org myorg       # Create repo
dt git protect myapp --org myorg    # Branch protection
```

### Quick Jenkins operations

```bash
dt ci creds my-creds --username admin     # Create credentials
dt ci org acme-folder --org acme --credentials my-creds
dt ci check my-job                        # Check job exists
```

### Quick project init

```bash
dt proj maven /path/to/project      # Init Maven
dt proj pg /path/to/db              # Init PostgreSQL
dt proj dbci /path/to/tools         # Init dbci-tools
```

## Super Short Examples

```bash
dt env up                           # Setup
dt git user john --org acme         # User
dt git repo app --org acme          # Repo
dt ci org acme --org acme --creds gitea-creds  # Jenkins org
dt p maven ./myapp                  # Maven project
dt env down                         # Teardown
```
