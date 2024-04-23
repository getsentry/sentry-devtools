from __future__ import annotations

import argparse
import importlib
import inspect
import logging
import os
import sys
import textwrap
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from pkgutil import walk_packages
from types import ModuleType
from typing import List
from typing import NotRequired
from typing import Tuple
from typing import TypeAlias
from typing import TypedDict

from devtools import constants
from devtools.lib.context import Context

ExitCode: TypeAlias = "str | int | None"
Action: TypeAlias = "Callable[[Context, Sequence[str] | None], ExitCode]"
ParserFn: TypeAlias = "Callable[[argparse.ArgumentParser], None]"

logger = logging.getLogger(__name__)


def _word_wrap(input: str | None) -> str | None:
    if not input:
        return input

    output = " ".join(input.split())
    return "\n".join(
        textwrap.wrap(output, _clamp(20, 80, constants.TERM_WIDTH))
    )


@dataclass(frozen=True)
class ModuleDef:
    module_name: str
    name: str
    help: str


@dataclass(frozen=True)
class DevModuleInfo:
    module: ModuleType
    module_def: ModuleDef
    commands: Sequence[ModuleAction]


class ModuleAction:
    def __init__(self, action: Action):
        self.name: str
        self.help: str
        self.description: str | None

        self.action = action
        self.argument_parsers: List[ParserFn] = []

    def __call__(
        self, context: Context, args: Sequence[str] | None
    ) -> ExitCode:
        return self.action(context, args)

    def add_argparser(self, fn: ParserFn) -> None:
        self.argument_parsers.append(fn)


def command(name: str, help: str) -> Callable[[Action], Action]:
    """
    Marks a function as being a CLI command.
    @commmand("commandname", "This command makes cookies")
    """

    def wrap(main: Action | ModuleAction) -> Action:
        if isinstance(main, ModuleAction):
            module_action = main
        else:
            module_action = ModuleAction(main)

        module_action.name = name
        module_action.help = help
        module_action.description = _word_wrap(main.__doc__)

        return module_action

    return wrap


class ArgArgs(TypedDict):
    required: NotRequired[bool]
    metavar: NotRequired[str]
    help: NotRequired[str]
    choices: NotRequired[Sequence[str]]
    action: NotRequired[str]
    dest: NotRequired[str]


def _convert_argument_params(
    *names: str,
    help: str | None = None,
    required: bool = True,
    var: str | None = None,
    choices: Sequence[str] | None = None,
) -> Tuple[Tuple[str, ...], ArgArgs]:
    if len(names) == 0:
        print("Argument must have a name")
        raise SystemExit(1)
    if names[0].startswith("-"):
        argtype = "option"
    else:
        argtype = "positional"

    kwargs: ArgArgs = {}

    if argtype == "option":
        kwargs["required"] = required

        if var:
            kwargs["metavar"] = var

            if not [n for n in names if n.startswith("--")]:
                kwargs["dest"] = var

        if choices:
            kwargs["choices"] = choices

        if not (var or choices):
            kwargs["action"] = "store_true"

        if help:
            kwargs["help"] = help
        else:
            if choices:
                kwargs["help"] = f"must be one of {choices}"
    else:
        name = var or names[0]
        kwargs["metavar"] = name

        if choices:
            kwargs["choices"] = choices
        if help:
            kwargs["help"] = help
        else:
            if choices:
                kwargs["help"] = f"{name} must be one of {choices}"
    return names, kwargs


def argument(
    *names: str,
    help: str | None = None,
    required: bool = True,
    var: str | None = None,
    choices: Sequence[str] | None = None,
) -> Callable[[Action], Action]:
    """
    Provides arguments to a command function.

    @command(name, help)
    @argument("-v", help="Verbose")
    """
    ak = _convert_argument_params(
        *names, help=help, required=required, var=var, choices=choices
    )

    def add_args(argparse: argparse.ArgumentParser) -> None:
        argparse.add_argument(*ak[0], **ak[1])

    return argument_fn(add_args)


def argument_fn(fn: ParserFn) -> Callable[[Action], Action]:
    def wrap(main: Action) -> Action:
        if isinstance(main, ModuleAction):
            module_action = main
        else:
            module_action = ModuleAction(main)

        module_action.add_argparser(fn)
        return module_action

    return wrap


def require(var: str, message: str) -> Callable[[Action], Action]:
    """
    Indicates that a Context var is required for this command function

    @require("repo", "You need to be in a repository to use this command")
    """

    def outer(main: Action) -> Action:
        def inner(context: Context, args: Sequence[str] | None) -> ExitCode:
            if context.get(var) is None:
                raise SystemExit(message)
            return main(context, args)

        return inner

    return outer


require_repo = require("repo", "This devtool requires a repository")


def find_resource(command: Action, name: str) -> str:
    if isinstance(command, ModuleAction):
        command = getattr(command, "action", command)

    module = sys.modules[command.__module__]

    assert module.__file__ is not None

    directory = os.path.dirname(module.__file__)
    filepath = os.path.normpath(
        os.path.join(
            directory, "resources", module.__name__.split(".")[-1], name
        )
    )

    return filepath


def get_actions(module: ModuleType) -> Sequence[ModuleAction]:
    return [
        action
        for name, action in inspect.getmembers(
            module, lambda m: isinstance(m, ModuleAction)
        )
    ]


def module_info(module: ModuleType) -> DevModuleInfo:
    info = module.module_info
    return DevModuleInfo(
        module=module, module_def=info, commands=get_actions(module)
    )


def load_modules(path: str, name: str) -> Sequence[ModuleType]:
    if not os.path.exists(path):
        return []

    if name in sys.modules:
        package = sys.modules[name]
    else:
        package = importlib.import_module(name)

    if path not in package.__path__:
        package.__path__.append(path)

    all_modules = []

    for module_finder, module_name, _ in walk_packages(
        (path,), prefix=f"{name}."
    ):
        module_spec = module_finder.find_spec(module_name, None)

        # it "should be" impossible to fail these:
        assert module_spec is not None, module_name
        assert module_spec.loader is not None, module_name

        logger.debug(
            "Loading module %s (%s)", module_spec.name, module_spec.origin
        )
        module = importlib.util.module_from_spec(module_spec)

        if module_name in sys.modules:
            # if already loaded, pull from sys.modules
            all_modules.append(sys.modules[module_name])
        else:
            # else load and add to sys.modules
            sys.modules[module_name] = module
            try:
                module.__loader__.exec_module(module)  # type: ignore
                all_modules.append(module)
            except Exception as e:
                logger.error(f"Failed to load module {module_name}", exc_info=e)

    return all_modules


def _clamp(min: int, max: int, value: int) -> int:
    if value < min:
        return min
    if value > max:
        return max
    return value


def _generate_parser(
    modinfo_list: Sequence[DevModuleInfo],
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v",
        action="count",
        required=False,
        dest="verbosity",
        help="Verbosity -v; multiple invocations increase verbosity",
    )

    subparser = parser.add_subparsers(
        title=argparse.SUPPRESS,
        metavar="command",
        dest="command",
        required=True,
    )
    visited = set()

    for info in modinfo_list:
        # don't show modules with no actions defined
        if not info.commands:
            continue

        module_def = info.module_def

        module_name = module_def.name
        if module_def.name in visited:
            module_name = module_def.module_name
        visited.add(module_name)

        child = subparser.add_parser(
            module_name,
            help=module_def.help,
            description=_word_wrap(info.module.__doc__),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        default_command = [
            command
            for command in info.commands
            if command.name == module_def.name
        ]
        other_commands = [
            command
            for command in info.commands
            if command.name != module_def.name
        ]

        if default_command:
            # command matching name case; i.e., module == command
            for fn in default_command[0].argument_parsers:
                fn(child)

        if not other_commands:
            continue

        subsubparser = child.add_subparsers(
            title="subcommands",
            metavar="subcommand",
            dest="subcommand",
            required=False if default_command else True,
        )

        for command in other_commands:
            grandchild = subsubparser.add_parser(
                command.name,
                help=command.help,
                description=command.description,
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
            for fn in command.argument_parsers:
                fn(grandchild)

    return parser


class CommandLoader:
    def __init__(self) -> None:
        self.modules: List[DevModuleInfo] = []
        self.sources: List[Tuple[str, str]] = []

    def add_source(self, package: str, *paths: str) -> None:
        path = os.path.join(*paths)

        source = path, package
        if source not in self.sources:
            self.sources.append(source)
            self.modules.extend(self._load_modules(path, package))

    def get_argument_parser(self) -> argparse.ArgumentParser:
        return _generate_parser(self.modules)

    def get_module(self, name: str) -> DevModuleInfo:
        if "." in name:
            matching = [
                m for m in self.modules if m.module_def.module_name == name
            ]
        else:
            matching = [m for m in self.modules if m.module_def.name == name]

        return matching[0]

    def _load_modules(self, path: str, package: str) -> List[DevModuleInfo]:
        return [
            module_info(module)
            for module in load_modules(path, package)
            if hasattr(module, "module_info")
        ]
