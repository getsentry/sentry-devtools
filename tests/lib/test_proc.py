from __future__ import annotations

import os
import sys

import pytest

from devtools.lib import proc


def test_run_with_stdout() -> None:
    cmd = ("echo", "Hello, World!")
    expected_output = "Hello, World!"

    result, out, err = proc.run(cmd)

    assert out == expected_output


def test_run_without_stdout() -> None:
    cmd = ("echo", "Hello, World!")

    result, out, err = proc.run(cmd, stdout=sys.stdout)

    assert out is None


def test_run_with_pathprepend(tmp_path: str) -> None:
    dummy_executable = os.path.join(tmp_path, "dummy_executable")
    with open(dummy_executable, "w") as f:
        f.write("#!/bin/sh\necho Hello, World!")
    os.chmod(dummy_executable, 0o755)

    cmd = ("dummy_executable",)
    pathprepend = tmp_path

    result, out, err = proc.run(cmd, pathprepend=pathprepend)

    assert out == "Hello, World!"


def test_run_command_not_found() -> None:
    cmd = ("invalid_command",)

    with pytest.raises(SystemExit):
        proc.run(cmd)


def test_run_with_custom_env() -> None:
    cmd = ("sh", "-c", "printenv VAR1 && printenv VAR2")
    custom_env = {"VAR1": "value1", "VAR2": "value2"}

    result, out, err = proc.run(cmd, env=custom_env)

    assert out == "value1\nvalue2"


def test_run_with_cwd(tmp_path: str) -> None:
    text = "Hello, World!"
    with open(os.path.join(tmp_path, "test.txt"), "w") as f:
        f.write(text)
    cmd = ("cat", "test.txt")
    cwd = tmp_path

    result, out, err = proc.run(cmd, cwd=cwd)

    assert out == text


def test_run_command_failed() -> None:
    cmd = ("ls", "nonexistent_directory")

    with pytest.raises(proc.CommandError):
        proc.run(cmd)
