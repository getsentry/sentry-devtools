from __future__ import annotations

from devtools import constants
from devtools.internal.colors import colors


def single_value(
    prompt: str,
    description: str | None = None,
    default_value: str | None = None,
) -> str | None:
    if not constants.INTERACTIVE:
        return default_value

    if description:
        print(colors.bright_black, "# ", description, colors.reset)

    try:
        print(colors.bright_green, "   ", prompt, colors.reset, sep="", end="")
        if default_value is not None:
            prompt = f"{colors.cyan}[{colors.reset}{default_value}{colors.cyan}]{colors.reset}: "
        else:
            prompt = ": "
        value = input(prompt) or default_value
    except EOFError:
        raise SystemExit()

    return value


def yes(
    prompt: str,
    description: str | None = None,
    default_value: bool | None = None,
) -> bool | None:
    if not constants.INTERACTIVE:
        if default_value:
            return default_value
        raise SystemExit("No default response provided")

    default_message = "y/n"
    if default_value is False:
        default_message = "y/N"
    elif default_value:
        default_message = "Y/n"

    if description:
        print(colors.bright_black, "# ", description, colors.reset, sep="")

    print(colors.bright_green, "   ", prompt, colors.reset, sep="", end="")
    prompt = f"{colors.cyan}[{colors.reset}{default_message}{colors.cyan}]{colors.reset}: "

    while True:
        try:
            response = input(prompt)
        except EOFError:
            raise SystemExit()

        if response.lower() == "y":
            return True
        if response.lower() == "n":
            return False
        if response == "" and default_value is not None:
            return default_value
        continue
