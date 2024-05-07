from __future__ import annotations

import configparser
import functools
import logging
import os
import sys
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from devtools import constants
from devtools.constants import MACHINE
from devtools.lib.text import single_value

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigOpt:
    name: str
    prompt: str
    formatter: Callable[[str], str] | None = None
    default: Callable[[], str] = lambda: ""


Config: TypeAlias = "dict[str, str | None]"


def get_value(
    name: str, section: str | None = None, default: str | None = None
) -> str | None:
    if not section:
        section = constants.APP_NAME

    return get_config().get(section, name, fallback=default)


def read_config(path: str) -> configparser.ConfigParser:
    """Reads a configuration file from disk, with no caching"""
    config = configparser.ConfigParser()
    config.read(path)
    return config


@functools.lru_cache(maxsize=None)
def get_config(config_path: str | None = None) -> configparser.ConfigParser:
    """Reads a configuration file from disk, with caching"""
    if not config_path:
        config_path = constants.config

    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def verify_config(
    section: str, opts: Sequence[ConfigOpt], config_path: str | None = None
) -> bool:
    """Checks to ensure that the configuration exists and is complete"""
    config = configparser.ConfigParser()
    config_path = config_path or constants.config

    # Read existing configuration, if present
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        return False

    if not config.has_section(section):
        return False

    for opt in opts:
        current = config.get(section, opt.name, fallback=None)

        if current is None:
            return False
    return True


def update_config(
    section: str,
    opts: Sequence[ConfigOpt],
    overrides: Config | None = None,
    config_path: str | None = None,
) -> None:
    config = configparser.ConfigParser()
    needs_save = False

    if not config_path:
        config_path = constants.config

    # Read existing configuration, if present
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if not config.has_section(section):
        config.add_section(section)

    for opt in opts:
        current = config.get(section, opt.name, fallback=None)
        value = overrides.get(opt.name) if overrides else current

        if value is None and opt.default is not None:
            value = opt.default()

        value = single_value(
            opt.name, description=opt.prompt, default_value=value
        )

        value = (
            opt.formatter(value)
            if opt.formatter and value is not None
            else value
        )

        if value != current:
            needs_save = True
            config.set(section, opt.name, value)
            logger.debug("Setting %s.%s to %s", section, opt.name, value)

    if needs_save:
        save_config(config_path, config)


def save_config(config_path: str, config: configparser.ConfigParser) -> None:
    logger.info("Thank you. Saving answers.")

    with open(config_path, "w") as f:
        config.write(f)

    get_config.cache_clear()


def get_repo(reporoot: str) -> configparser.ConfigParser:
    """Deprecated"""
    from devtools.lib.repository import Repository

    return Repository.from_root_path(reporoot).config()


def get_python(reporoot: str, python_version: str) -> tuple[str, str]:
    cfg = get_repo(reporoot)
    url = cfg[f"python{python_version}"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg[f"python{python_version}"][f"{sys.platform}_{MACHINE}_sha256"]
    return url, sha256


# only used for sentry/getsentry
def get_python_legacy(reporoot: str, python_version: str) -> tuple[str, str]:
    cfg = get_repo(reporoot)
    url = cfg["python"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg["python"][f"{sys.platform}_{MACHINE}_sha256"]
    return url, sha256
