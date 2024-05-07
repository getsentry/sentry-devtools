from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from functools import lru_cache
from typing import cast

from devtools.lib import proc
from devtools.lib.context import Context
from devtools.lib.modules import argument
from devtools.lib.modules import argument_fn
from devtools.lib.modules import command
from devtools.lib.modules import ExitCode
from devtools.lib.modules import ModuleDef
from devtools.lib.modules import ParserFn

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_sha(repo: str, ref: str) -> str:
    if len(ref) == 40:
        try:
            int(ref, 16)
        except ValueError:
            pass
        else:
            return ref

    cmd = ("git", "ls-remote", "--exit-code", f"https://github.com/{repo}", ref)
    out = subprocess.check_output(cmd)
    for line in out.decode().splitlines():
        sha, refname = line.split()
        if refname in (f"refs/tags/{ref}", f"refs/heads/{ref}"):
            return sha
    else:
        raise AssertionError(f"unknown ref: {repo}@{ref}")


def extract_repo(action: str) -> str:
    # Some actions can be like `github/codeql-action/init`,
    # where init is just a directory. The ref is for the whole repo.
    # We only want the repo name though.
    parts = action.split("/")
    return f"{parts[0]}/{parts[1]}"


@command("pin-gha", "Pins github actions to SHAs instead of tags")
@argument_fn(
    cast(
        ParserFn,
        lambda p: p.add_argument(
            "files", nargs="+", type=str, help="path to github actions file"
        ),
    )
)
def pin_gha(context: Context, argv: Sequence[str] | None = None) -> int:
    """
    Any supplied Github action files containing references to branches or tags will be modified to
    refer to specific SHAs instead.

    This process rewrites the action YAML files in place.
    """
    args = context["args"]
    files: list[str] = args.files

    ACTION_VERSION_RE = re.compile(
        r"(?<=uses: )(?P<action>.*)@(?P<ref>[^#\s]+)"
    )

    for fp in files:
        with open(fp, "r+") as f:
            newlines: list[str] = []
            for line in f:
                m = ACTION_VERSION_RE.search(line)
                if not m:
                    newlines.append(line)
                    continue
                d = m.groupdict()
                sha = get_sha(extract_repo(d["action"]), ref=d["ref"])
                if sha != d["ref"]:
                    line = ACTION_VERSION_RE.sub(rf"\1@{sha} # \2", line)
                newlines.append(line)
            f.seek(0)
            f.truncate()
            f.writelines(newlines)

    return 0


@command("fetch", "Fetches a repository")
@argument("repo", help="the repository to fetch")
def main(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    args = context["args"]
    workspace = context["workspace"]

    if "/" not in args.repo:
        print("Repository names must be in the form of <owner>/<repo>")
        return 1
    fetch(workspace, args.repo)
    return 0


def fetch(
    workspace: str, repo: str, auth: bool = True, sync: bool = True
) -> None:
    org, slug = repo.split("/")

    codepath = f"{workspace}/{slug}"

    if os.path.exists(codepath):
        print(f"{codepath} already exists")
        return

    print(f"Fetching {repo} into {codepath}")

    additional_args = (
        (f"git@github.com:{repo}",)
        if auth
        else (
            "--depth",
            "1",
            "--single-branch",
            f"--branch={os.environ['SENTRY_BRANCH']}",
            f"https://github.com/{repo}",
        )
    )

    proc.run(
        (
            "git",
            "-C",
            workspace,
            "cloner",
            "--filter=blob:none",
            "--progress",
            *additional_args,
        ),
        stdout=sys.stdout,
    )


module_info = ModuleDef(
    module_name=__name__, name="github", help="Github actions"
)
