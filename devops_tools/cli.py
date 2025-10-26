"""Command-line interface for DevOps Tools."""

import sys
from pathlib import Path

import click

from . import config, env, gitea, jenkins, project
from .utils import DevOpsError


class AliasedGroup(click.Group):
    """A Click Group that supports command aliases."""
    
    def __init__(self, *args, **kwargs):
        self.aliases = kwargs.pop('aliases', [])
        super().__init__(*args, **kwargs)
    
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        # Check if cmd_name is an alias for any command
        for name, cmd in self.commands.items():
            if hasattr(cmd, 'aliases') and cmd_name in cmd.aliases:
                return cmd
        return None
    
    def format_commands(self, ctx, formatter):
        """Extra format methods for multi methods that adds all the commands."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            
            cmd_name = subcommand
            if hasattr(cmd, 'aliases') and cmd.aliases:
                cmd_name = f"{subcommand} ({', '.join(cmd.aliases)})"
            
            commands.append((cmd_name, cmd))

        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                with formatter.section("Commands"):
                    formatter.write_dl(rows)


@click.group(cls=AliasedGroup)
@click.option("--env-file", type=click.Path(exists=True), help="Path to .env file")
@click.pass_context
def cli(ctx, env_file):
    """DevOps Tools - Manage Jenkins, Gitea, and Docker environments."""
    ctx.ensure_object(dict)
    if env_file:
        config.get_config(env_file)
    else:
        config.get_config()


# Environment commands
@cli.group(name="environment", cls=AliasedGroup)
def environment():
    """Environment lifecycle management."""
    pass

environment.aliases = ["env"]


@environment.command("setup")
def env_setup():
    """Setup the DevOps environment. (Alias: up)"""
    try:
        env.setup(create_default_org=True)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

env_setup.aliases = ["up"]


@environment.command("teardown")
def env_teardown():
    """Teardown the DevOps environment. (Alias: down)"""
    try:
        env.teardown()
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

env_teardown.aliases = ["down"]


# Gitea commands
@cli.group(name="git", cls=AliasedGroup)
def git():
    """Gitea operations."""
    pass

git.aliases = ["gitea"]


@git.command("create-user")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, help="User password")
@click.option("--org", required=True, help="Organization (for email)")
@click.option("--admin", is_flag=True, help="Make user an admin")
def gitea_create_user(username, password, org, admin):
    """Create a user in Gitea. (Alias: user)"""
    try:
        gitea.create_user(username, password, org, admin)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_create_user.aliases = ["user"]


@git.command("user-exists")
@click.argument("username")
def gitea_user_exists(username):
    """Check if a user exists in Gitea. (Alias: check-user)"""
    exists = gitea.user_exists(username)
    if exists:
        click.echo(f"✅ User '{username}' exists")
    else:
        click.echo(f"❌ User '{username}' does not exist")
        sys.exit(1)

gitea_user_exists.aliases = ["check-user"]


@git.command("create-org")
@click.argument("org_name")
@click.option("--owner", required=True, help="Owner username")
@click.option("--description", default="", help="Organization description")
def gitea_create_org(org_name, owner, description):
    """Create an organization in Gitea. (Alias: org)"""
    try:
        gitea.create_org(org_name, owner, description)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_create_org.aliases = ["org"]


@git.command("create-team")
@click.argument("team_name")
@click.option("--org", required=True, help="Organization name")
@click.option("--permission", default="write", type=click.Choice(["read", "write", "admin"]), help="Team permission")
@click.option("--description", default="", help="Team description")
def gitea_create_team(team_name, org, permission, description):
    """Create a team in an organization. (Alias: team)"""
    try:
        gitea.create_team(team_name, org, permission, description)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_create_team.aliases = ["team"]


@git.command("add-team-member")
@click.argument("team_name")
@click.option("--org", required=True, help="Organization name")
@click.option("--username", required=True, help="Username to add")
def gitea_add_team_member(team_name, org, username):
    """Add a user to a team. (Alias: add-member)"""
    try:
        gitea.add_team_members(team_name, org, username)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_add_team_member.aliases = ["add-member"]


@git.command("create-repo")
@click.argument("name")
@click.option("--org", required=True, help="Organization name")
@click.option("--description", default="", help="Repository description")
def gitea_create_repo(name, org, description):
    """Create a repository in an organization. (Alias: repo)"""
    try:
        gitea.create_repo(name, org, description)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_create_repo.aliases = ["repo"]


@git.command("branch-protection")
@click.argument("name")
@click.option("--org", required=True, help="Organization name")
@click.option("--team", default="", help="Team name for protection")
@click.option("--jenkins-folder", default="", help="Jenkins folder name (defaults to '{org}-folder')")
@click.option("--enable-status-check", is_flag=True, help="Require Jenkins pipeline status check to pass")
def gitea_branch_protection(name, org, team, jenkins_folder, enable_status_check):
    """Setup branch protection on main branch. (Alias: protect)"""
    try:
        gitea.setup_branch_protection(name, org, team, jenkins_folder, enable_status_check)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_branch_protection.aliases = ["protect"]


@git.command("auto-delete-branch")
@click.argument("name")
@click.option("--org", required=True, help="Organization name")
def gitea_auto_delete_branch(name, org):
    """Enable auto-delete of branch after PR merge."""
    try:
        gitea.enable_auto_delete_branch(name, org)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@git.command("clone")
@click.argument("name")
@click.option("--org", required=True, help="Organization name")
@click.option("--dest", required=True, type=click.Path(), help="Destination directory")
@click.option("--username", required=True, help="Username for authentication")
@click.option("--password", prompt=True, hide_input=True, help="Password for authentication")
def gitea_clone(name, org, dest, username, password):
    """Clone a repository from Gitea."""
    try:
        gitea.clone_repo(name, org, dest, username, password)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@git.command("setup-webhook")
def gitea_setup_webhook():
    """Setup default webhook for Jenkins. (Alias: webhook)"""
    try:
        gitea.setup_default_webhook()
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

gitea_setup_webhook.aliases = ["webhook"]


# Jenkins commands
@cli.group(name="ci", cls=AliasedGroup)
def ci():
    """Jenkins operations."""
    pass

ci.aliases = ["jenkins", "j"]


@ci.command("create-credentials")
@click.argument("cred_id")
@click.option("--username", required=True, help="Username")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.option("--description", default="", help="Credential description")
def jenkins_create_creds(cred_id, username, password, description):
    """Create Jenkins credentials. (Alias: creds)"""
    try:
        jenkins.create_credentials(cred_id, username, password, description)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

jenkins_create_creds.aliases = ["creds"]


@ci.command("create-org")
@click.argument("job_name")
@click.option("--org", required=True, help="Gitea organization name")
@click.option("--credentials", required=True, help="Jenkins credentials ID")
@click.option("--description", default="", help="Job description")
def jenkins_create_org(job_name, org, credentials, description):
    """Create an organization folder job in Jenkins. (Alias: org)"""
    try:
        jenkins.create_org(job_name, org, credentials, description)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

jenkins_create_org.aliases = ["org"]


@ci.command("job-exists")
@click.argument("job_name")
def jenkins_job_exists(job_name):
    """Check if a Jenkins job exists. (Alias: check)"""
    exists = jenkins.job_exists(job_name)
    if exists:
        click.echo(f"✅ Job '{job_name}' exists")
    else:
        click.echo(f"❌ Job '{job_name}' does not exist")
        sys.exit(1)

jenkins_job_exists.aliases = ["check"]


# Project commands
@cli.group(name="projects", cls=AliasedGroup)
def projects():
    """Project initialization."""
    pass

projects.aliases = ["proj", "p"]


@projects.command("init-maven")
@click.argument("target_dir", type=click.Path())
def project_init_maven(target_dir):
    """Initialize a Maven project. (Alias: maven)"""
    try:
        project.init_maven(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

project_init_maven.aliases = ["maven"]


@projects.command("init-postgres")
@click.argument("target_dir", type=click.Path())
def project_init_postgres(target_dir):
    """Initialize a PostgreSQL database project. (Aliases: postgres, pg)"""
    try:
        project.init_postgres(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

project_init_postgres.aliases = ["postgres", "pg"]


@projects.command("init-dbci-tools")
@click.argument("target_dir", type=click.Path())
def project_init_dbci(target_dir):
    """Initialize a dbci-tools project. (Alias: dbci)"""
    try:
        project.init_dbci_tools(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

project_init_dbci.aliases = ["dbci"]


@projects.command("commit")
@click.argument("target_dir", type=click.Path(exists=True))
@click.option("--message", "-m", required=True, help="Commit message")
def project_commit(target_dir, message):
    """Add, commit, and push changes."""
    try:
        project.init_commit(target_dir, message)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
