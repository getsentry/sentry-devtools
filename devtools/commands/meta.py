""" This set of commands is fun """
from __future__ import annotations

import logging
import os.path
import sys
import tomllib
from collections.abc import Sequence

from devtools.internal.parsehelp import ParseError
from devtools.internal.parsehelp import to_decorator
from devtools.lib import fs
from devtools.lib import proc
from devtools.lib import text
from devtools.lib.context import Context
from devtools.lib.jinja import get_env
from devtools.lib.modules import argument
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef

module_info = ModuleDef(
    module_name=__name__, name="meta", help="devtools devtools commands"
)

logger = logging.getLogger(__name__)


@command("create", help="Create a new command")
@argument("-l", "--local", required=False, help="Create a local command")
def create(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """Create a new devtools command from templates"""
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

    module_name = text.single_value("Module name")
    if not (module_name and module_name.isidentifier()):
        raise SystemExit(
            f"Module name '{module_name}' must be a valid identifier"
        )

    write_path = os.path.join(path, f"{module_name}.py")
    if os.path.exists(write_path):
        if not text.yes(
            "Overwrite?",
            description=f"{write_path} exists.",
            default_value=False,
        ):
            raise SystemExit("Not overwriting")

    module_help = text.single_value("Module help")

    env = get_env(create)
    output = []

    template = env.get_template("module.jinja")
    output.append(template.render(module=module_name, help=module_help))

    template = env.get_template("command.jinja")
    print("Enter commands ")
    while True:
        command = text.single_value(
            "Command name",
            description="The name of the command and command function; leave blank to end command entry",
        )

        if not command:
            break

        command = command.lower()
        if not command.isidentifier():
            print(f"Command name '{command}' must be a valid identifier")
            continue

        details = {"command": command, "help": text.single_value("  Help text")}
        arguments = []
        while True:
            argspec = text.single_value(
                "  Argument",
                description=f"Argument for {command} e.g., '-b <bar>'; leave blank to end",
            )
            if not argspec:
                break
            try:
                argargs = to_decorator(argspec)
                print(f"    {argargs} added")
                arguments.append(argargs)
            except ParseError as pe:
                print(
                    text.error_sty,
                    "      ".join(("\n" + str(pe).lstrip()).splitlines(True)),
                    text.colors.reset,
                    sep="",
                )

        output.append(template.render(**details, arguments=arguments))

    os.makedirs(path, exist_ok=True)

    f = open(write_path, "w")
    f.write("\n".join(output))
    f.close()
    return 0


@command("show")
def show(context: Context, argv: Sequence[str] | None) -> ExitCode:
    loader = context["loader"]
    bullet = text.decoration_sty("*")
    for m in loader.modules:
        print(text.banner(m.module_def.module_name))
        print(f"{bullet} {text.label_sty('File')} {m.module.__file__}")
        print(f"{bullet} {text.label_sty('Name')} {m.module_def.name}")
        print(f"{bullet} {text.label_sty('Help')} {m.module_def.help}")
        print()
        print(text.header_sty("Commands:"))
        for action in m.commands:
            description = action.description or action.help or "no description"
            print("\t", text.label_sty(action.name), description)

        print()
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


@command("mkaliases", help="Create aliases for repo-specific user commands")
def mkaliases(context: Context, argv: Sequence[str] | None) -> ExitCode:
    loader = context["loader"]
    for module in loader.modules:
        if "devtools.usercommands" in module.module_def.module_name:
            print(
                f"alias {module.module_def.name}='devtools {module.module_def.name}'"
            )
    return 0


def get_version() -> str:
    """
    Get the current running version of devtools -- which is not necessarily the installed version
    of devtools but it's close enough
    """
    import devtools.constants

    path = os.path.normpath(
        os.path.join(
            os.path.dirname(devtools.constants.__file__), "..", "pyproject.toml"
        )
    )

    with open(path, "rb") as config:
        toml = tomllib.load(config)
    my_version = str(toml.get("project", {}).get("version", ""))

    return my_version


@command("update", help="Update devtools")
def update(context: Context, argv: Sequence[str] | None) -> ExitCode:
    get_version()

    with fs.retrieve_temp_file(
        "https://raw.githubusercontent.com/getsentry/sentry-devtools/main/pyproject.toml"
    ) as project:
        with open(project, "rb") as config:
            toml = tomllib.load(config)
            published_version = toml.get("project", {}).get("version", "")

    if not published_version:
        raise SystemExit("Could not locate published version")

    installed_version = get_version()

    if installed_version == published_version:
        return f"Current version is up to date ({installed_version})"

    print(
        f"New version found {published_version} (currently {installed_version})"
    )

    with fs.retrieve_temp_file(
        "https://raw.githubusercontent.com/getsentry/sentry-devtools/main/install-devtools.sh"
    ) as script:
        _, output, err = proc.run(
            ("bash", script), env={"SNTY_DRY_RUN": "PARCHED"}
        )
        logger.debug("Dry run output: %s", output)

        var = {
            k.strip("\t\n \"'"): v.strip("\t\n \"'")
            for k, v in [
                line.split("=")
                for line in output.split("\n")
                if line and not line.startswith("#")
            ]
        }
        if "SNTY_DEVTOOLS_HOME" not in var:
            raise SystemExit(
                f"Couldn't locate devtools home in shell response \n{output}"
            )

        devtools_home = var["SNTY_DEVTOOLS_HOME"]

        print(f"Installing devtools {published_version} into {devtools_home}]")

        proc.run(("bash", script), stderr=sys.stderr, stdout=sys.stdout)

        print(text.status_sty("Done"))

        return 0
