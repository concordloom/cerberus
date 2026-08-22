#!/bin/sh
# The browser-facing suite for the operator dashboard. It arrived after Stage 1
# was first recorded, and nothing recorded reaches it.
cd "$(dirname "$0")/.." || exit 1
python3 ui-tests/dashboard_check.py || exit 1
printf ui-tests-ran > .ui-tests-ran
