#!/bin/sh
# The fast local check named in AGENTS.md. Unit level only: it imports the
# command where it lies and never leaves this directory, so it says nothing
# about the chart that ships beside it.
cd "$(dirname "$0")" || exit 1
python3 - <<'PY' || exit 1
from app.cli import VERSION, main

assert VERSION, "the command has no version"
assert main(["cli", "--version"]) == 0, "--version does not succeed"
assert main(["cli"]) == 2, "a bare invocation does not report usage"
PY
printf stage1-ran > .stage1-ran
