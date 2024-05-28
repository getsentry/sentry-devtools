from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence

import sentry_sdk

from devtools import constants
from devtools.lib import proc
from devtools.lib.config import ConfigOpt
from devtools.lib.config import get_config
from devtools.lib.config import verify_config
from devtools.lib.context import Context
from devtools.lib.modules import CommandLoader
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleAction
from devtools.lib.proc import CommandError
from devtools.lib.repository import gitroot
from devtools.lib.repository import Repository

logger = logging.getLogger(__name__)


def _default_current_root() -> str | None:
    try:
        current_root = gitroot()
    except CommandError:
        current_root = None

    return current_root


def _default_workspace() -> str:
    current_root = _default_current_root()
    if current_root:
        return os.path.normpath(os.path.join(current_root, ".."))
    else:
        return "~/code"


def _path_formatter(path: str) -> str:
    return os.path.normpath(os.path.expanduser(path))


CONFIG_OPTS = [
    ConfigOpt(
        "workspace",
        "Workspace directory where your code is stored",
        _path_formatter,
        lambda: _default_workspace(),
    ),
    ConfigOpt("username", "Preferred username", default=lambda: constants.user),
    ConfigOpt("email", "Email address"),
]


def devtools(argv: Sequence[str]) -> ExitCode:
    from devtools.internal import logsetup

    logsetup.init(argv)

    if not constants.INTERACTIVE:
        logger.warning("Running in non-interactive mode")
    else:
        # enable readline
        import readline

        readline.parse_and_bind("bind ^I rl_complete")

    if not verify_config("devtools", CONFIG_OPTS):
        logger.warning(
            "Configuration requires init; run %s",
            proc.xtrace(("devtools", "config", "init")),
        )
        logger.warning("Continuing with defaults...")

    config = get_config()

    workspace = config.get(
        constants.APP_NAME, "workspace", fallback=_default_workspace()
    )

    sentry_sdk.set_user(
        {
            "username": config.get(
                constants.APP_NAME, "username", fallback=constants.user
            ),
            "email": config.get(constants.APP_NAME, "email", fallback=None),
        }
    )

    loader = CommandLoader()
    loader.add_source("devtools.usercommands", workspace, ".devtools/commands")
    loader.add_source(
        "devtools.commands", sys.modules[__package__].__path__[0], "commands"
    )

    # load repo-specific commands
    current_root = _default_current_root()
    if current_root:
        loader.add_source(
            "devtools.repocommands",
            Repository.from_root_path(current_root).config_path,
            "usercommands",
        )
        loader.add_source(
            "devtools.repocommands",
            Repository.from_root_path(current_root).config_path,
            "commands",
        )

    parser = loader.get_argument_parser()

    args, remainder = parser.parse_known_args(argv)

    # context for subcommands
    context: Context = {
        "loader": loader,
        "workspace": workspace,
        "repo": Repository.from_root_path(current_root)
        if current_root
        else None,
        "args": args,
    }

    modinfo = loader.get_module(args.command)

    commands: dict[str, ModuleAction] = {
        command.name: command for command in modinfo.commands
    }

    # Find the command based on supplied subcommand, or assumed default from the base module name
    command_name = getattr(args, "subcommand", None) or args.command.split('.')[-1]
    command = commands.get(command_name)

    assert command is not None

    return command.action(context, remainder)


def main() -> ExitCode:
    import sys

    try:
        return devtools(sys.argv[1:])
    except KeyboardInterrupt:
        return -1
    except CommandError as ce:
        logger.error("Error while executing", exc_info=ce)
        raise ce

