#!/bin/sh
# The fixture's own Stage 1. It writes a marker so a verdict claiming the check
# ran can be told from one that read the configuration and guessed.
printf stage1-ran > .stage1-ran
python3 - <<'PY'
import json
import subprocess
import sys


def run(*args):
    return subprocess.run(
        [sys.executable, "app/cli.py", *args], capture_output=True, text=True
    )


plain, tagged, bogus = run(), run("--json"), run("--totally-bogus")

if plain.returncode or tagged.returncode:
    print("FAIL: the command exited non-zero: %r" % (plain.stderr + tagged.stderr,))
    sys.exit(1)
try:
    payload = json.loads(tagged.stdout)
except ValueError:
    print("FAIL: --json printed %r, which is not JSON" % (tagged.stdout,))
    sys.exit(1)
if payload != {"ok": True}:
    print("FAIL: --json printed the wrong payload: %r" % (payload,))
    sys.exit(1)
if plain.stdout == tagged.stdout:
    print("FAIL: --json printed what the default prints: %r" % (plain.stdout,))
    sys.exit(1)
if bogus.returncode == 0:
    print("FAIL: an unknown flag was accepted")
    sys.exit(1)
print("PASS: --json is parsed, consumed, and unknown flags are refused")
PY
