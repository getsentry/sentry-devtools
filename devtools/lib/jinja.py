from __future__ import annotations

import os
from collections.abc import Callable
from os.path import getmtime
from typing import Optional
from typing import Tuple

from jinja2 import BaseLoader
from jinja2 import Environment
from jinja2 import select_autoescape
from jinja2 import TemplateNotFound

from devtools.lib.modules import Action
from devtools.lib.modules import find_resource
from devtools.lib.modules import ModuleAction


class ResourceLoader(BaseLoader):  # type: ignore
    def __init__(self, action: Action) -> None:
        if isinstance(action, ModuleAction):
            self.action = action.action
        else:
            self.action = action

    def get_source(self, environment: Environment, path: str) -> Tuple[str, Optional[str], Optional[Callable[[], bool]]]:  # type: ignore
        template = find_resource(self.action, path)
        if not os.path.exists(template):
            raise TemplateNotFound(template)
        mtime = getmtime(template)
        with open(template) as f:
            source = f.read()
        return source, path, lambda: mtime == getmtime(template)


def get_env(action: Action) -> Environment:  # type: ignore
    return Environment(
        loader=ResourceLoader(action), autoescape=select_autoescape()
    )
