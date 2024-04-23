from __future__ import annotations

import os

import sentry_sdk


def main() -> None:
    if os.getenv("DEVENV_NO_SENTRY") is None:
        sentry_sdk.init(
            # https://sentry.sentry.io/settings/projects/sentry-dev-env/keys/
            dsn="https://3dc0b17e6467a292dfa9aeaa8e38b6ab@o1.ingest.us.sentry.io/4507182554415104",
            # enable performance monitoring
            enable_tracing=True,
        )

    from devtools.main import main

    raise SystemExit(main())


if __name__ == "__main__":
    main()
