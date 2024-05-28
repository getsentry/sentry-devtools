from __future__ import annotations

import os.path
from collections.abc import Sequence
from configparser import ConfigParser
from functools import lru_cache

from devtools import constants
from devtools.lib import proc
from devtools.lib.config import get_config
from devtools.lib.fs import ensure_binroot


DEFAULT_ORG = "getsentry"


class Repository:
    def __init__(self, org: str, name: str, root: str = "") -> None:
        self.name = os.path.basename(root)
        self.org = org

        if root:
            self.path = root
        else:
            workspace = get_config().get(constants.APP_NAME, "workspace")
            self.path = os.path.join(workspace, name)

        self.config_path = os.path.join(self.path, constants.APP_DIR)

    def __repr__(self) -> str:
        return f"Repository: {self.name}"

    def ensure_binroot(self) -> None:
        ensure_binroot(self.path)

    def dot_path(self) -> str:
        return os.path.join(self.path, constants.APP_DOT_DIR)

    def script_path(self) -> str:
        return os.path.join(self.dot_path(), "scripts")

    def bin_path(self) -> str:
        return os.path.join(self.path, "bin")

    def config(self) -> ConfigParser:
        return get_config(os.path.join(self.config_path, "config.ini"))

    def get_venv(self, name: str) -> str:
        """Get a specific venv by name"""
        return os.path.join(self.path, f".venv-{name}")

    def find_venvs(self) -> Sequence[str]:
        result = []
        for f in os.scandir(self.path):
            if not f.name.startswith(".venv-"):
                continue
            if not os.path.isdir(f):
                continue
            result.append(f.name.split("-", 1)[1])
        return result

    @classmethod
    def from_root_path(cls, root: str) -> Repository:
        name = os.path.basename(root)
        return Repository(DEFAULT_ORG, name, root=root)


@lru_cache
def _gitroot(path: str) -> str:
    code, stdout, stderr = proc.run(
        ("git", "-C", path, "rev-parse", "--show-cdup")
    )
    return os.path.normpath(os.path.join(path, stdout))


def gitroot(path: str = "") -> str:
    return _gitroot(path or os.getcwd())
