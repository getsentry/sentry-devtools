from __future__ import annotations

import os
from unittest import mock

import pytest

from devtools import main
from devtools.lib.config import read_config


def test_init(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devtools/config.ini"
    coderoot = f"{tmp_path}/code"

    with mock.patch("devtools.constants.config", config_path):
        assert not os.path.exists(config_path)
        main.devtools(("config", "init", "-d", f"workspace:{coderoot}"))
        assert os.path.exists(config_path)

        config = read_config(config_path)
        assert config.get("devtools", "workspace") == coderoot


def test_invalid(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devtools/config.ini"
    with mock.patch("devtools.constants.config", config_path):
        assert not os.path.exists(config_path)
        with pytest.raises(SystemExit):
            main.devtools(("config", "init", "-d", "workspace"))
        assert not os.path.exists(config_path)


def test_rm(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devtools/config.ini"
    coderoot = f"{tmp_path}/code"

    with mock.patch("devtools.constants.config", config_path):
        assert not os.path.exists(config_path)
        main.devtools(("config", "init", "-d", f"workspace:{coderoot}"))
        assert os.path.exists(config_path)

        main.devtools(("config", "rm"))
        assert not os.path.exists(config_path)
