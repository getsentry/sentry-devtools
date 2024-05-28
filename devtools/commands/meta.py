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
from devtools.lib import jinja
from devtools.lib import proc
from devtools.lib import text
from devtools.lib.context import Context
from devtools.lib.modules import argument
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef
from devtools.lib.modules import require_repo

module_info = ModuleDef(
    module_name=__name__, name="meta", help="devtools devtools commands"
)

logger = logging.getLogger(__name__)


@command("mkcommand", help="Create a new command module")
@argument("-l", "--local", required=False, help="Create a local command")
def mkcommand(context: Context, argv: Sequence[str] | None) -> ExitCode:
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

    env = jinja.get_env(mkcommand)
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
                description=f"Argument for {command} e.g., '-b <bar>' or '[--foo]'; leave blank to end",
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


@command("show", help="Provides details about the top-level command modules")
@argument("-m", var="module", required=False)
def show(context: Context, argv: Sequence[str] | None) -> ExitCode:
    args = context['args']
    loader = context['loader']
    bullet = text.decoration_sty("*")

    modules = loader.modules
    if args.module:
        modules = [module for module in modules if module.module_def.name.startswith(args.module)]

    for m in modules:
        print(text.banner(m.module_def.module_name))
        print(f"{bullet} {text.label_sty('File')} {m.module.__file__}")
        print(f"{bullet} {text.label_sty('Package')} {m.package}")
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


@command("version", help="Display the version and exit")
def version(context: Context, argv: Sequence[str] | None) -> ExitCode:
    print("".join([text.label_sty("Version: "), get_version()]))
    return 0


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


@command(
    "mkpipe", help="Make a venv script for JSON-pipe invocation with devtools"
)
@argument("name")
@argument(
    "-e",
    "--env",
    help="Specific virtual environment if multiple are available",
    required=False,
)
@require_repo
def mkpipe(context: Context, argv: Sequence[str] | None) -> ExitCode:
    args = context["args"]
    repo = context["repo"]

    assert repo is not None
    os.makedirs(repo.script_path(), exist_ok=True)

    script_name = args.name
    if not script_name.endswith(".py"):
        script_name = f"{script_name}.py"

    target = os.path.join(repo.script_path(), script_name)
    if os.path.exists(target):
        if not text.yes(
            "Overwrite?",
            description=f"File exists at {target}",
            default_value=False,
        ):
            return 0

    venvs = repo.find_venvs()
    if not venvs:
        raise SystemExit("No virtual env found")

    if len(venvs) > 2 and not args.env:
        print(f"Multiple virtual environments found: {venvs}")
        raise SystemExit("Target environment needs to be specified with --env")

    if args.env and args.env not in venvs:
        raise SystemExit(
            f"Specified environment {args.env} not known; found: {venvs}"
        )

    venv = args.env if args.env else venvs[0]
    interpreter = os.path.join(repo.get_venv(venv), "bin", "python")

    jenv = jinja.get_env(mkpipe)
    output = []

    template = jenv.get_template("script.jinja")
    output.append(template.render(interpreter=interpreter))

    logger.info("Creating %s using env:%s", target, venv)
    with open(target, "w") as f:
        f.write("".join(output))
    os.chmod(target, 0o755)
    return 0
