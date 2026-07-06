#!/bin/bash
# RedNote MCP 启动封装 — 自动设置 playwright 依赖路径
export NODE_PATH="/home/nehswang/.nvm/versions/node/v20.20.2/lib/node_modules"
export LD_LIBRARY_PATH="$HOME/.local/playwright-libs:$LD_LIBRARY_PATH"
exec rednote-mcp --stdio
