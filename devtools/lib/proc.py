from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import run as subprocess_run
from typing import TextIO
from typing import Tuple

from devtools import constants
from devtools.constants import home
from devtools.constants import homebrew_bin
from devtools.constants import root
from devtools.constants import shell_path
from devtools.constants import user_environ
from devtools.lib import text

base_path = f"{root}/bin:{homebrew_bin}:{user_environ['PATH']}"
base_env = {"PATH": base_path, "HOME": home, "SHELL": shell_path}

logger = logging.getLogger(__name__)


def quote(cmd: Sequence[str]) -> str:
    """convert a command to bash-compatible form"""
    from pipes import quote

    return " ".join(quote(arg) for arg in cmd)


def xtrace(cmd: Sequence[str]) -> str:
    """Print a commandline, similar to how xtrace does."""
    return "".join(
        (text.decoration_sty("$"), " ", text.colors.bold(quote(cmd)))
    )


class CommandError(SystemExit):
    def __init__(
        self, message: str, code: int, out: str | None, err: str | None
    ):
        super().__init__(message)
        self.code = code
        self.stdout = out
        self.stderr = err


def run(
    cmd: Sequence[str],
    *,
    pathprepend: str = "",
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    input: str | None = None,
) -> Tuple[int, str, str]:
    """Wraps command invocation with a small amount of logging"""
    if env is None:
        env = {}
    env = {**constants.user_environ, **base_env, **env}

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    logger.debug(xtrace(cmd))
    try:
        proc = subprocess_run(
            cmd,
            check=True,
            cwd=cwd,
            env=env,
            stdout=stdout if stdout else PIPE,
            stderr=stderr if stderr else PIPE,
            input=input.encode("utf-8") if input else None,
        )
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        raise SystemExit(f"{e}") from e

    except CalledProcessError as e:
        out = e.stdout.decode().strip() if e.stdout else None
        err = e.stderr.decode().strip() if e.stderr else None

        detail = f"Command `{quote(e.cmd)}` failed! (code {e.returncode})"
        raise CommandError(detail, e.returncode, out, err) from e
    else:
        out = proc.stdout.decode().strip() if proc.stdout else None
        err = proc.stderr.decode().strip() if proc.stderr else None
        return proc.returncode, out, err


def invoke_pipe(script: Sequence[str], data: str) -> str:
    """Executes a script with parameters passed via a strings"""
    ret, out, _ = run(script, stderr=sys.stderr, input=data)
    if ret != 0:
        raise SystemExit("Pipe command returned non-zero status")
    return out
