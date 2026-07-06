#!/bin/bash
# source this file in your shell to set up the runtime environment
export PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LD_LIBRARY_PATH="$HOME/.local/playwright-libs:$LD_LIBRARY_PATH"
export NODE_PATH="$(npm root -g 2>/dev/null):$NODE_PATH"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
