#!/bin/sh
# Stage 2 for the command surface: take it out of the source tree and run it the
# way somebody who installed it would, from a directory that is not this
# repository. It can go red: break what the command reports and the comparison
# below fails. It cannot catch a stale copy of VERSION, because both sides read
# the same file — that would need a version the command carries independently.
set -e
cd "$(dirname "$0")/.." || exit 1
root=$(pwd)
scratch=$(mktemp -d /tmp/gate-surface.XXXXXX)
trap 'rm -rf "$scratch"' EXIT
cp -r app VERSION "$scratch/"
cd "$scratch"
got=$(python3 -m app.cli --version)
want=$(cat "$root/VERSION")
if [ "$got" != "$want" ]; then
  echo "the installed command reports $got, the project is $want" >&2
  exit 1
fi
