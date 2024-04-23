from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from devtools.internal.colors import colors

logger = logging.getLogger("devtools")
logger.setLevel(logging.WARNING)


class CustomFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"{colors.bright_black}%(levelname)s{colors.reset}: %(message)s",
        logging.INFO: f"{colors.blue}%(levelname)s{colors.reset}: %(message)s",
        logging.WARNING: f"{colors.yellow}%(levelname)s{colors.reset}: %(message)s",
        logging.ERROR: f"{colors.red}%(levelname)s{colors.reset}: %(message)s",
        logging.CRITICAL: f"{colors.bright_red}%(levelname)s{colors.reset}: %(message)s",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def init(argv: Sequence[str]) -> None:
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setStream(sys.stderr)
    ch.setLevel(logging.DEBUG)

    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-v",
        action="count",
        required=False,
        dest="verbosity",
        help="Verbosity -v; multiple invocations increase verbosity",
    )

    args, _ = parser.parse_known_args(argv)

    v = getattr(args, "verbosity", 0) or 0

    if v == 1:
        logger.setLevel(logging.INFO)
    elif v > 1:
        logger.setLevel(logging.DEBUG)
