from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

from devtools.lib.fs import gitroot
from devtools.lib.proc import CommandError
from tests.utils import chdir


def test_gitroot(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))

    with chdir(tmp_path):
        assert os.path.samefile(tmp_path, gitroot())
        assert os.path.isdir(f"{gitroot()}/.git")


def test_gitroot_cd(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))
    os.mkdir(f"{tmp_path}/foo")

    _gitroot = gitroot(path=f"{tmp_path}/foo")
    assert os.path.samefile(f"{tmp_path}", _gitroot)
    assert os.path.isdir(f"{_gitroot}/.git")


def test_no_gitroot(tmp_path: pathlib.Path) -> None:
    with pytest.raises(CommandError):
        with chdir(tmp_path):
            gitroot()
