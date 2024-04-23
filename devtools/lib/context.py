from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING
from typing import TypedDict

if TYPE_CHECKING:
    from devtools.lib.repository import Repository
    from devtools.lib.modules import CommandLoader


class Context(TypedDict):
    workspace: str
    repo: "Repository" | None
    args: Namespace
    loader: "CommandLoader"
