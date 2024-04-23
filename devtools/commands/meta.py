""" This set of commands is fun """
from __future__ import annotations

import os.path
import sys
from collections.abc import Sequence

from devtools.lib import ask
from devtools.lib.context import Context
from devtools.lib.jinja import get_env
from devtools.lib.modules import argument
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef


module_info = ModuleDef(
    module_name=__name__, name="meta", help="devtools devtools commands"
)


@command("create", help="Create a new command")
@argument(
    "-l", "--local", required=False, var="user", help="Create a local command"
)
def create(context: Context, argv: Sequence[str] | None) -> ExitCode:
    args = context["args"]

    if args.local:
        path = os.path.join(context["workspace"], ".devtools/commands")
    else:
        repository = context["repo"]
        if not repository:
            raise SystemExit(
                "Not currently in a repository -- did you want to do --local?"
            )

        path = os.path.join(repository.config_path, "usercommands")

    module_name = ask.single_value("Module name")

    write_path = os.path.join(path, f"{module_name}.py")
    if os.path.exists(write_path):
        if not ask.yes(
            "Overwrite?",
            description=f"{write_path} exists.",
            default_value=False,
        ):
            raise SystemExit("Not overwriting")

    module_help = ask.single_value("Module help")

    env = get_env(create)
    output = []

    template = env.get_template("module.jinja")
    output.append(template.render(module=module_name, help=module_help))

    template = env.get_template("command.jinja")
    while True:
        command = ask.single_value("Module name")
        if not command:
            break

        details = {"command": command, "help": ask.single_value("Help test")}
        output.append(template.render(**details))

    os.makedirs(path, exist_ok=True)

    f = open(write_path, "w")
    f.write("\n".join(output))
    f.close()
    return 0


@command("which", help="Find the location of a command")
@argument("name")
def which(context: Context, argv: Sequence[str] | None) -> ExitCode:
    loader = context["loader"]
    args = context["args"]

    for module in loader.modules:
        if module.module_def.name == args.name:
            break
    else:
        print(f"Could not locate module {args.name}")
        return 1

    module_name = module.module_def.module_name

    print(sys.modules[module_name].__file__)

    return 0
