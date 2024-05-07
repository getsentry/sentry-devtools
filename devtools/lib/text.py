from __future__ import annotations

import readline
import textwrap
from collections.abc import Sequence
from typing import List
from typing import NamedTuple

from devtools import constants


class _Color(str):
    def __init__(self, color: str):
        self.color = color

    def __str__(self) -> str:
        return self.color

    def __call__(self, txt: str) -> str:
        return "".join((self.color, txt, colors.reset.color))


class _Colors(NamedTuple):
    reset: _Color
    bold: _Color
    black: _Color
    red: _Color
    green: _Color
    yellow: _Color
    blue: _Color
    magenta: _Color
    cyan: _Color
    white: _Color
    bright_black: _Color
    bright_red: _Color
    bright_green: _Color
    bright_yellow: _Color
    bright_blue: _Color
    bright_magenta: _Color
    bright_cyan: _Color
    bright_white: _Color


_no_color = _Color("")

_ansicolors = _Colors(
    reset=_Color("\x1b[0m"),
    bold=_Color("\x1b[1m"),
    black=_Color("\x1b[0;30m"),
    red=_Color("\x1b[0;31m"),
    green=_Color("\x1b[0;32m"),
    yellow=_Color("\x1b[0;33m"),
    blue=_Color("\x1b[0;34m"),
    magenta=_Color("\x1b[0;35m"),
    cyan=_Color("\x1b[0;36m"),
    white=_Color("\x1b[0;37m"),
    bright_black=_Color("\x1b[0;90m"),
    bright_red=_Color("\x1b[0;91m"),
    bright_green=_Color("\x1b[0;92m"),
    bright_yellow=_Color("\x1b[0;93m"),
    bright_blue=_Color("\x1b[0;94m"),
    bright_magenta=_Color("\x1b[0;95m"),
    bright_cyan=_Color("\x1b[0;96m"),
    bright_white=_Color("\x1b[0;97m"),
)

colors = _ansicolors

# Styles
decoration_sty = colors.bright_magenta
header_sty = colors.bright_cyan
label_sty = colors.bright_green
extra_sty = colors.bright_black
status_sty = colors.blue
warn_sty = colors.bright_yellow
error_sty = colors.bright_red


def _clamp(min: int, max: int, value: int) -> int:
    if value < min:
        return min
    if value > max:
        return max
    return value


def word_wrap(input: str | None) -> str | None:
    if not input:
        return input

    output = " ".join(input.split())
    return "\n".join(
        textwrap.wrap(output, _clamp(20, 80, constants.TERM_WIDTH))
    )


def banner(
    message: str,
    padding: str = "=",
    padding_color: str = colors.cyan,
    message_color: str = header_sty,
) -> str:
    width = _clamp(20, 80, constants.TERM_WIDTH)
    pad_width = int((width - len(message)) / 2 - 1)
    if pad_width < 0:
        return message_color + message + colors.reset

    pad = padding_color + padding[0] * pad_width + colors.reset

    return pad + " " + message_color + message + colors.reset + " " + pad


def single_value(
    prompt: str,
    description: str | None = None,
    default_value: str | None = None,
) -> str | None:
    if not constants.INTERACTIVE:
        return default_value

    if description:
        print(extra_sty, "# ", description, colors.reset)

    try:
        print(label_sty, "   ", prompt, colors.reset, sep="", end="")
        if default_value is not None:
            prompt = (
                f"{decoration_sty('[')}{default_value}{decoration_sty(']')}: "
            )
        else:
            prompt = ": "
        value = input(prompt) or default_value
    except EOFError:
        raise SystemExit()

    return value


class Completer:
    def __init__(self, list: Sequence[str]):
        self.matches = list
        self.terms = list
        self.current_prefix = ""

    def complete(self, prefix: str, index: int) -> str | None:
        if prefix != self.current_prefix:
            self.matches = [w for w in self.terms if w.startswith(prefix)]
            self.current_prefix = prefix
        else:
            pass

        if index < len(self.matches):
            return self.matches[index]
        else:
            return None


def multi_value(
    prompt: str,
    description: str | None = None,
    default_values: Sequence[str] | None = None,
    auto_complete: Sequence[str] | None = None,
) -> Sequence[str] | None:
    if not constants.INTERACTIVE:
        return default_values

    if description:
        print(extra_sty, "# ", description, colors.reset)

    results: List[str] = []

    try:
        if auto_complete:
            readline.set_completer(Completer(auto_complete).complete)

        while True:
            prompt_n = "".join(
                ["   ", label_sty(prompt), f"[{len(results)+1}]: "]
            )
            value = input(prompt_n)
            if not value:
                break
            results.append(value)
    except EOFError:
        raise SystemExit()
    finally:
        readline.set_completer(None)

    return results


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
        print(extra_sty, "# ", description, colors.reset, sep="")

    default = f"{decoration_sty('[')}{default_message}{decoration_sty(']')}: "

    while True:
        print("   ", label_sty(prompt), " ", sep="", end="")
        try:
            response = input(default)
        except EOFError:
            raise SystemExit()

        if response.lower() == "y":
            return True
        if response.lower() == "n":
            return False
        if response == "" and default_value is not None:
            return default_value
        continue
