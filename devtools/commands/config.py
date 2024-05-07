from __future__ import annotations

import configparser
import logging
import os
import sys
from collections.abc import Sequence
from typing import cast

from devtools import constants
from devtools.lib.config import update_config
from devtools.lib.context import Context
from devtools.lib.modules import argument
from devtools.lib.modules import argument_fn
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef
from devtools.lib.modules import ParserFn
from devtools.main import CONFIG_OPTS

logger = logging.getLogger(__name__)


@command("init", "Display configuration")
@argument_fn(
    cast(
        ParserFn,
        lambda x: x.add_argument(
            "-d",
            "--default-config",
            metavar="config:value",
            required=False,
            action="append",
            help="Provide a default config value. e.g., -d workspace:path/to/root",
        ),
    )
)
@argument(
    "-m",
    var="module",
    help="init configuration for a specific module",
    required=False,
)
def init(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    args = context["args"]

    defaults = args.default_config or []
    for conf in defaults:
        if len(conf.split(":", 1)) != 2:
            raise SystemExit(
                f"Invalid config option; '{conf}' should be in the form of 'key:value'"
            )

    overrides = {k: v for k, v in (conf.split(":", 1) for conf in defaults)}

    if not args.module:
        update_config("devtools", CONFIG_OPTS, overrides=overrides)
    return 0


@command("show", "Display configuration")
def show_config(
    context: Context, argv: Sequence[str] | None = None
) -> ExitCode:
    config_path = constants.config

    if not os.path.exists(config_path):
        print(f"No config at {config_path}")

    logger.info("Reading config file from %s", config_path)

    parser = configparser.ConfigParser()
    parser.read(config_path)
    parser.write(sys.stdout)
    return 0


@command("rm", "Remove configuration")
def rm_config(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    if os.path.exists(constants.config):
        os.remove(constants.config)
    return 0


module_info = ModuleDef(
    module_name=__name__,
    name="config",
    help="View or update your devtools configuration",
)
