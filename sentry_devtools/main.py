from __future__ import annotations

import argparse
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)
    print(f"hello {args}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
