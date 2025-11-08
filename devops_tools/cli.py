"""Command-line interface for DevOps Tools."""

import sys
from pathlib import Path

import click

from . import config, env, gitea, jenkins, project
from .utils import DevOpsError

import os
import pathlib


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
@cli.group(name="env", cls=AliasedGroup)
def environment():
    """Environment lifecycle management."""
    pass


@environment.command("up")
def env_setup():
    """Setup the DevOps environment."""
    env.setup()


@environment.command("down")
def env_teardown():
    """Teardown the DevOps environment."""
    try:
        env.teardown()
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# Gitea commands

@cli.group(name="git", cls=AliasedGroup)
def git():
        """
        Gitea operations.

        Subgroups:
            repo      Manage repositories (create, init, remove)
            team      Manage teams
            user      Manage users
            member    Manage team membership
            protect   Manage branch protection
            org       Manage organizations

        Common commands:
            dt git repo new <name> -o <org>
            dt git repo init <repo_name> -o <org> -d <dir>
            dt git team new <name> -o <org> -m <perm>
            dt git user new <name> -o <org>
            dt git member new <user> -o <org> -t <team>
            dt git org new <name>
            dt git clone <repo> -o <org> -d <dest> -u <user> -p <password>
        """
        pass

# Clone command must be defined immediately after git group
@git.command("clone")
@click.argument("repo")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--dir", "-d", required=True, type=click.Path(file_okay=False), help="Destination directory")
@click.option("--user", "-u", required=True, help="Username")
@click.option("--password", "-p", required=True, help="Password")
def git_clone(repo, org, dir, user, password):
    """Clone a Gitea repository to a local directory."""
    from devops_tools import gitea
    import os
    import pathlib
    # Ensure destination directory exists
    dest_dir = os.path.expanduser(dir)
    # Compose the full path: <dest>/<org>/<user>/<repo>
    full_path = os.path.join(dest_dir, org, user, repo)
    pathlib.Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    gitea.clone_repo(repo, org, full_path, user, password)

# Organization subcommands
@git.group()
def org():
    """Organization operations."""
    pass

@org.command("new")
@click.argument("name")
@click.option("--description", "-d", default="", help="Organization description")
@click.option("--owner", "-o", required=False, help="Owner username (optional)")
def org_new(name, description, owner):
    """Create a new organization."""
    from devops_tools import gitea
    # Use admin user as owner if not specified
    if not owner:
        from devops_tools.config import get_config
        owner = get_config().gitea_admin_user
    gitea.create_org(name, owner, description)

@org.command("rem")
@click.argument("name")
def org_rem(name):
    """Remove an organization."""
    from devops_tools import gitea
    gitea.delete_org(name)



# member subcommands (after webhook, before Jenkins)
@git.group()
def member():
    """Team membership operations."""




@member.command("new")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--team", "-t", required=True, help="Team name")
@click.argument("user")
def member_new(org, team, user):
    """Add a user to a team."""
    gitea.add_team_members(team, org, user)





@member.command("rem")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--team", "-t", required=True, help="Team name")
@click.argument("user")
def member_rem(org, team, user):
    """Remove a user from a team."""
    gitea.remove_team_member(team, org, user)


# repo subcommands
@git.group()
def repo():
    """Repository operations."""

@repo.command("new")
@click.argument("name")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--description", "-d", default="", help="Repository description")
def repo_new(name, org, description):
    """Create a new repository."""
    gitea.create_repo(name, org, description)

@repo.command("init")
@click.argument("repo_name")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--dir", "-d", required=True, type=click.Path(exists=True, file_okay=False), help="Source folder to initialize repo from")
def repo_init(repo_name, org, dir):
    """Initialize a repository from a source folder."""
    project.init_and_push_repo(repo_name, org, dir)


@repo.command("rem")
@click.argument("name")
@click.option("--org", "-o", required=True, help="Organization name")
def repo_rem(name, org):
    """Remove a repository."""
    gitea.delete_repo(name, org)

# protect subcommands
@repo.group()
def protect():
    """Branch protection management."""


@protect.command("new")
@click.option("--org", "-o", required=True, help="Organization name")
@click.argument("repo")
@click.option("--team", "-t", required=True, help="Comma-separated team names (e.g. devs,qa)")
@click.option("--branch", "-b", default="main", show_default=True, help="Branch name")
@click.option("--status-check", "-s", is_flag=True, help="Enable status checks on branch protection")
def protect_add(org, repo, team, branch, status_check):
    """Add branch protection."""
    team_list = [t.strip() for t in team.split(",") if t.strip()]
    gitea.setup_branch_protection(repo, org, team_list, branch, status_check)


    # ...existing code...


# user subcommands
@git.group()
def user():
    """User operations."""

@user.command("get")
@click.argument("name")
def user_get(name):
    """Get user info: prints username if exists."""
    if gitea.user_exists(name):
        print(name)
        sys.exit(0)
    else:
        sys.exit(1)

@user.command("new")
@click.argument("name")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--password", "-p", default="secret", help="User password")
@click.option("--admin", "-a", is_flag=True, help="Make user an admin")
def user_new(name, org, password, admin):
    """Create a new user."""
    gitea.create_user(name, password, org, admin)

@user.command("rem")
@click.argument("name")
def user_rem(name):
    """Remove a user."""
    gitea.delete_user(name)

# team subcommands
@git.group()
def team():
    """Team operations."""


@team.command("new")
@click.argument("name")
@click.option("--org", "-o", required=True, help="Organization name")
@click.option("--permission", "-m", type=click.Choice(["read", "write", "admin"]), default="write", help="Team permission")
def team_new(name, org, permission):
    """Create a new team."""
    gitea.create_team(name, org, permission)

@team.command("rem")
@click.argument("name")
@click.option("--org", "-o", required=True, help="Organization name")
def team_rem(name, org):
    """Remove a team."""
    gitea.delete_team(name, org)



# Jenkins commands
@cli.group(name="ci", cls=AliasedGroup)
def ci():
    """Jenkins operations."""
    pass

# creds subcommands
@ci.group()
def creds():
    """Jenkins credentials management."""
    pass

@creds.command("new")
@click.argument("name")
@click.option("--user", "-u", required=True, help="Jenkins username")
@click.option("--token", "-t", required=True, help="Jenkins API token")
def creds_new(name, user, token):
    """Create new Jenkins credentials."""
    try:
        jenkins.create_credentials(name, user, token)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@creds.command("rem")
@click.argument("name")
def creds_rem(name):
    """Remove Jenkins credentials."""
    try:
        jenkins.delete_credentials(name)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

# org subcommands
@ci.group()
def org():
    """Jenkins folder/org management."""
    pass

@org.command("new")
@click.argument("org")
def org_new(org):
    """Create new Jenkins folder/org (name must match Gitea org)."""
    try:
        jenkins.create_org(f"{org}-folder", org, "gitea")
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@org.command("rem")
@click.argument("org")
def org_rem(org):
    """Remove Jenkins folder/org (name must match Gitea org)."""
    try:
        jenkins.delete_job(f"{org}-folder")
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

# job subcommands
@ci.group()
def job():
    """Jenkins job operations."""
    pass

@job.command("exists")
@click.argument("name")
def job_exists(name):
    """Check if a Jenkins job exists."""
    exists = jenkins.job_exists(name)
    if exists:
        click.echo(f"✅ Job '{name}' exists")
    else:
        click.echo(f"❌ Job '{name}' does not exist")
        sys.exit(1)


# Project commands
@cli.group(name="src", cls=AliasedGroup)
def src():
    """Project source initialization."""
    pass


@src.command("maven")
@click.argument("target_dir", type=click.Path())
def project_init_maven(target_dir):
    """Initialize a Maven project."""
    try:
        project.init_maven(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@src.command("postgres")
@click.argument("target_dir", type=click.Path())
def project_init_postgres(target_dir):
    """Initialize a PostgreSQL database project."""
    try:
        project.init_postgres(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@src.command("dbci")
@click.argument("target_dir", type=click.Path())
def project_init_dbci(target_dir):
    """Initialize a dbci-tools project."""
    try:
        project.init_dbci_tools(target_dir)
    except DevOpsError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@src.command("commit")
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
