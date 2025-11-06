# Configuration Templates

This folder contains configuration templates used by the DevOps Tools library for setting up Gitea and Jenkins.

## 📁 Structure

```bash
templates/
├── gitea/              # Gitea configuration templates
│   ├── branch-protection.json
│   └── repo.json
└── jenkins/            # Jenkins configuration templates
    ├── basic-security.groovy
    ├── jenkins-creds.xml
    ├── jenkins-org.xml
    └── jenkins.yaml
```

## 🦊 Gitea Templates

### branch-protection.json

Template for setting up branch protection rules on repositories.

**Used by:** `devops_tools.gitea.setup_branch_protection()`

**Variables:**

- None (static configuration)

**Purpose:** Protects the main branch from direct pushes, requires pull requests.

### repo.json

Template for creating new repositories via Gitea API.

**Used by:** `devops_tools.gitea.create_repo()`

**Variables:**

- `$name` - Repository name
- `$description` - Repository description
- `$private` - Whether repository is private (true/false)

## 🔧 Jenkins Templates

### basic-security.groovy

Groovy script for configuring Jenkins basic security settings.

**Used by:** `devops_tools.env.setup()`

**Variables:**

- `$JENKINS_ADMIN_USER` - Admin username
- `$JENKINS_ADMIN_PASSWORD` - Admin password

**Purpose:** Sets up basic authentication and security realm.

### jenkins-creds.xml

XML template for creating Jenkins credentials.

**Used by:** `devops_tools.jenkins.create_credentials()`

**Variables:**

- `$CRED_ID` - Credential ID
- `$USERNAME` - Username for the credential
- `$PASSWORD` - Password for the credential

### jenkins-org.xml

XML template for creating Jenkins organization folders.

**Used by:** `devops_tools.jenkins.create_org()`

**Variables:**

- `$ORG_NAME` - Organization name
- `$GITEA_ADVERTISED_URL` - Gitea server URL
- `$CRED_ID` - Credentials to use for accessing Gitea

**Purpose:** Creates an organization folder that scans Gitea for repositories with Jenkinsfiles.

### jenkins.yaml

Jenkins Configuration as Code (JCasC) template.

**Used by:** `devops_tools.env.setup()`

**Variables:**

- `$JENKINS_ADMIN_USER` - Admin username
- `$JENKINS_ADMIN_PASSWORD` - Admin password

**Purpose:** Configures Jenkins using JCasC for reproducible setup.

## 🔄 Template Processing

Templates are processed using Python's `string.Template` class, which replaces variables in the format `$VARIABLE_NAME` or `${VARIABLE_NAME}`.

### Example Usage in Code

```python
from string import Template
from devops_tools.config import get_config

config = get_config()
template_path = config.get_template_path("jenkins/jenkins-creds.xml")

with open(template_path) as f:
    template = Template(f.read())
    
xml_content = template.substitute(
    CRED_ID="my-creds",
    USERNAME="alice",
    PASSWORD="secret"
)
```

## 📝 Adding New Templates

1. Create your template file in the appropriate subdirectory
2. Use `$VARIABLE_NAME` syntax for placeholders
3. Document the template in this README
4. Update the appropriate Python module to use the template

## 🧪 Testing Templates

You can test template substitution manually:

```python
from string import Template
from pathlib import Path

template_path = Path("templates/jenkins/jenkins-creds.xml")
with open(template_path) as f:
    template = Template(f.read())

result = template.substitute(
    CRED_ID="test-creds",
    USERNAME="testuser",
    PASSWORD="testpass"
)
print(result)
```

## 🔗 Related Files

- **devops_tools/config.py** - Manages template paths
- **devops_tools/env.py** - Uses Jenkins templates for setup
- **devops_tools/gitea.py** - Uses Gitea templates
- **devops_tools/jenkins.py** - Uses Jenkins templates

## 📚 Further Reading

- [Python string.Template](https://docs.python.org/3/library/string.html#template-strings)
- [Jenkins Configuration as Code](https://www.jenkins.io/projects/jcasc/)
- [Gitea API Documentation](https://docs.gitea.io/en-us/api-usage/)
