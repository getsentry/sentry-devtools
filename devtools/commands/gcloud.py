""" A set of commands in gcloud """
from __future__ import annotations

import csv
import logging
import sys
from collections.abc import Sequence
from typing import cast

from devtools import constants
from devtools.lib import gcptools
from devtools.lib import proc
from devtools.lib import text
from devtools.lib.context import Context
from devtools.lib.modules import argument
from devtools.lib.modules import argument_fn
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import find_resource
from devtools.lib.modules import ModuleDef
from devtools.lib.modules import ParserFn
from devtools.lib.modules import require_repo
from devtools.lib.text import colors

logger = logging.getLogger(__name__)

module_info = ModuleDef(
    module_name=__name__,
    name="gcloud",
    help="GCloud tools ported from tacos gha",
)


@command("whoami", help="Returns the current gcloud identity")
@require_repo
def whoami(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """
    Ported from Tacos-GHA

    This script emulates `gcloud auth print-access-token` except it is helpful
    when given a service account as the argument. The original will instead
    demand a service account key, but that's insecure and unnecessary.
    """
    identity = gcptools.get_identity()

    return str(identity)


@command("sudo", help="Run a command with sudo permissions")
@argument("-u", var="user", required=True, help="Target account for sudo")
def sudo(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """
    Ported from Tacos-GHA

    The username supplied needs to be specified in {repo}/.devtools/config.ini.
    """
    if not argv:
        return "Nothing to run"

    args = context["args"]
    target_alias = args.user
    if "@" not in target_alias:
        repo = context["repo"]
        if repo is None:
            raise SystemExit(
                f"Invalid target identity {colors.red(target_alias)}"
            )
        logger.debug("Assuming %s is an alias", colors.green(target_alias))

        new_token = gcptools.sudo_alias(repo, target_alias)
    else:
        new_token = gcptools.sudo(target_alias)

    proc.run(
        argv,
        env=gcptools.to_env(new_token),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    return "sudo executed successfully"


@command("sudo-env", help="Output environment values for gcp-sudo")
@argument("-u", var="user", required=True, help="Target account for sudo")
@require_repo
def sudo_env(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """
    Outputs an eval'able set of exports for gcp-sudo. E.g., use eval $(detools gcloud sudo-env) to change to a
    sudo account in your current shell. The username supplied needs to be specified in {repo}/.devtools/config.ini.
    """
    repo = context["repo"]
    assert repo is not None

    args = context["args"]
    target_alias = args.user

    env = gcptools.to_env(gcptools.sudo_alias(repo, target_alias))

    if "fish" in constants.shell:
        for k, v in env.items():
            print(f'set -x {k}="{v}"')
    else:
        for k, v in env.items():
            print(f'export {k}="{v}"')
    return 0


@command("create-alias", help="Create a repo-specific sudo alias")
@argument("name", help="name of the alias to create")
@argument(
    "-a",
    "--account",
    var="account",
    help="name of the service account for sudo",
)
@argument_fn(
    cast(
        ParserFn,
        lambda x: x.add_argument(
            "-s", "--scope", nargs="+", help="scopes included", required=False
        ),
    )
)
@require_repo
def create_alias(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """Create a new gcloud sudo alias. You will be prompted for scopes and the target user if they are on the
    command line.

    Example: devtools gcloud create-alias -s email profile -- my-new-alias
    """
    repo = context["repo"]
    assert repo is not None

    args = context["args"]

    section_name = f"gcpsudo.{args.name}"
    config = repo.config()

    if config.has_section(section_name):
        raise SystemExit("Alias already exists")

    config.add_section(section_name)

    scopes = args.scope
    account = args.account

    if not account:
        account = text.single_value(
            "Account name", description="Target gcp service account"
        )
    if not scopes:
        scope_list = find_resource(create_alias, "scopes.csv")
        print(scope_list)
        with open(scope_list, "r") as file:
            all_scopes = [row[0] for row in csv.reader(file)]

        scopes = text.multi_value(
            "Scope",
            description="GCP Scopes to request",
            default_values=["email"],
            auto_complete=all_scopes,
        )

    config.set(section_name, "account", account)
    config.set(section_name, "scopes", "\n".join(scopes))

    config.write(sys.stdout)
    return 0


@command("clear-env", help="Unset GCP account environment variables")
def clear_env(context: Context, argv: Sequence[str] | None) -> ExitCode:
    print(
        """
unset CLOUDSDK_CORE_ACCOUNT
unset GOOGLE_OAUTH_ACCESS_TOKEN
unset CLOUDSDK_AUTH_ACCESS_TOKEN
"""
    )
    return 0
