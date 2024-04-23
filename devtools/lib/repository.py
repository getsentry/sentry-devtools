from __future__ import annotations

import os.path
from configparser import ConfigParser

from devtools import constants
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

    def config(self) -> ConfigParser:
        return get_config(os.path.join(self.config_path, "config.ini"))

    @classmethod
    def from_root_path(cls, root: str) -> Repository:
        name = os.path.basename(root)
        return Repository(DEFAULT_ORG, name, root=root)
