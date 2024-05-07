from __future__ import annotations

import os
import pathlib
import subprocess
import tarfile
import tempfile

import pytest

from devtools.lib import fs
from devtools.lib import proc
from tests.utils import chdir


def test_gitroot(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))

    with chdir(tmp_path):
        assert os.path.samefile(tmp_path, fs.gitroot())
        assert os.path.isdir(f"{fs.gitroot()}/.git")


def test_gitroot_cd(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))
    os.mkdir(f"{tmp_path}/foo")

    _gitroot = fs.gitroot(path=f"{tmp_path}/foo")
    assert os.path.samefile(f"{tmp_path}", _gitroot)
    assert os.path.isdir(f"{_gitroot}/.git")


def test_no_gitroot(tmp_path: pathlib.Path) -> None:
    with pytest.raises(proc.CommandError):
        with chdir(tmp_path):
            fs.gitroot()


def test_idempotent_add(tmp_path: pathlib.Path) -> None:
    fd, file = tempfile.mkstemp(dir=tmp_path)
    with open(fd, "w") as f:
        f.write("")

    # Empty file
    fs.idempotent_add(file, "**/*.pyc\n.idea/\n")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n"

    # Don't add new line which matches
    fs.idempotent_add(file, ".idea/")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n"

    # Add new line which doesn't match
    fs.idempotent_add(file, ".idea")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n.idea\n"

    # Don't add two lines which 100% match
    fs.idempotent_add(file, "**/*.pyc\n.idea/\n")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n.idea\n"

    # Add two lines which do not match existing two lines
    fs.idempotent_add(file, "**/*.pyc\n.idea\n")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n.idea\n**/*.pyc\n.idea\n"

    # Last line
    fs.idempotent_add(file, ".last")
    fs.idempotent_add(file, ".last")
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n.idea\n**/*.pyc\n.idea\n.last\n"

    # Whitespace don't hurt!
    fs.idempotent_add(
        file,
        """
    **/*.pyc    \n   .idea/     \n
    """,
    )
    with open(file, "r") as f:
        assert f.read() == "**/*.pyc\n.idea/\n.idea\n**/*.pyc\n.idea\n.last\n"

    # Whitespace do hurt!
    fs.idempotent_add(
        file,
        """
    **/*.pyc    \n   .idea/     \n
    """,
        trim=False,
    )
    with open(file, "r") as f:
        assert (
            f.read()
            == "**/*.pyc\n.idea/\n.idea\n**/*.pyc\n.idea\n.last\n**/*.pyc    \n   .idea/\n"
        )


def test_retrieve_temp_file() -> None:
    with fs.retrieve_temp_file(
        "https://raw.githubusercontent.com/getsentry/sentry-devtools/main/install-devtools.sh"
    ) as file:
        assert os.path.exists(file)

    assert not os.path.exists(file)


@pytest.fixture
def tar(tmp_path: pathlib.Path) -> pathlib.Path:
    plain = tmp_path.joinpath("plain")
    plain.write_text("hello world\n")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(plain, arcname="hello.txt")

    return tar


def test_unpack_tar(tar: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    fs.unpack(str(tar), str(dest))
    assert dest.joinpath("hello.txt").read_text() == "hello world\n"
