""" A set of commands in repo """
from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from devtools.internal import parsehelp
from devtools.lib import jinja
from devtools.lib import text
from devtools.lib.context import Context
from devtools.lib.modules import argument
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef
from devtools.lib.modules import require_repo

logger = logging.getLogger(__name__)

module_info = ModuleDef(
    module_name=__name__, name="repo", help="Repository managements commands"
)


@command("mkscript", help="Generate a new script")
@argument("name")
@argument(
    "-e",
    "--env",
    var="env",
    required=False,
    help="Specific virtual environment if multiple are available",
)
@require_repo
def mkscript(context: Context, argv: Sequence[str] | None) -> ExitCode:
    """mkscript does cool stuff"""
    args = context["args"]
    repo = context["repo"]

    assert repo is not None
    os.makedirs(repo.bin_path(), exist_ok=True)

    target = os.path.join(repo.bin_path(), args.name)
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
    if not os.path.exists(interpreter):
        raise SystemExit(f"Python interpreter not found at {interpreter}")

    interpreter = os.path.relpath(interpreter, repo.bin_path())

    arguments = []
    while True:
        argspec = text.single_value(
            "  Argument",
            description="Argument for script e.g., '-b <bar>' or '[--foo]'; leave blank to end",
        )
        if not argspec:
            break
        try:
            argargs = ", ".join(parsehelp.to_argparse(argspec))
            print(f"    add_argument({argargs}) added")
            arguments.append(argargs)
        except parsehelp.ParseError as pe:
            print(
                text.error_sty,
                "      ".join(("\n" + str(pe).lstrip()).splitlines(True)),
                text.colors.reset,
                sep="",
            )

    jenv = jinja.get_env(mkscript)
    output = []

    template = jenv.get_template("script.jinja")
    output.append(template.render(name=args.name,
                                  interpreter=interpreter,
                                  arguments=arguments))

    logger.info("Creating %s using env:%s", target, venv)
    with open(target, "w") as f:
        f.write("".join(output))
    os.chmod(target, 0o755)

    return "mkscript executed successfully"
