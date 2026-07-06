#!/bin/bash
# Sets up Playwright library dependencies (no sudo required) and runs the given command.
# Usage: ./scripts/run_with_playwright.sh [command...]
# e.g.:  ./scripts/run_with_playwright.sh python research/amazon/experiment.py

PLAYWRIGHT_LIBS="/home/nehswang/.local/playwright-libs"
export LD_LIBRARY_PATH="${PLAYWRIGHT_LIBS}:${LD_LIBRARY_PATH}"
exec "$@"
