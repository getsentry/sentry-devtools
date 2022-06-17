from __future__ import annotations

from sentry_devtools.main import main


def test_main():
    assert main(()) == 0
