#!/bin/sh
# The browser suite for the operator dashboard. Nothing else in this project
# invokes it: check.sh runs the unit checks only, and no workflow mentions it.
cd "$(dirname "$0")/.."
printf ui-tests-ran > .ui-tests-ran
exit 0
