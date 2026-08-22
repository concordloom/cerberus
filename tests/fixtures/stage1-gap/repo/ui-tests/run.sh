#!/bin/sh
# The browser-facing suite for the operator dashboard. Nothing else in this
# project invokes it: check.sh runs the unit checks only, and no workflow
# mentions it.
cd "$(dirname "$0")/.." || exit 1
python3 ui-tests/dashboard_check.py || exit 1
printf ui-tests-ran > .ui-tests-ran
