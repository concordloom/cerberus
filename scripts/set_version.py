#!/usr/bin/env python3
"""Write a version into both manifests. Called by semantic-release.

The version lives in two places, and it is not decoration: a marketplace plugin
is pinned to the string in its entry, so **an existing installation receives an
update only when that string changes**. A release that forgets one of the two
manifests either fails CI or, worse, ships a plugin whose declared version
disagrees with what it says about itself.

    python3 scripts/set_version.py 1.2.3
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "gopnik" / ".claude-plugin" / "plugin.json"

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def write(path: pathlib.Path, setter) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    setter(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit("usage: set_version.py <x.y.z>")
    version = sys.argv[1]
    if not SEMVER.match(version):
        sys.exit(f"not a semver version: {version!r}")

    write(PLUGIN, lambda d: d.__setitem__("version", version))
    write(MARKETPLACE, lambda d: d["plugins"][0].__setitem__("version", version))
    print(f"version set to {version} in both manifests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
