"""The command this project installs. One of its two delivery surfaces."""

import pathlib
import sys

VERSION = (
    (pathlib.Path(__file__).resolve().parent.parent / "VERSION")
    .read_text(encoding="utf-8")
    .strip()
)


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--version"]:
        print(VERSION)
        return 0
    print("usage: cli --version", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
