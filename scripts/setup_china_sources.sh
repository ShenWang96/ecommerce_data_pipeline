#!/bin/bash
# ============================================================================
# 中国大陆数据源 — 统一环境安装脚本
# 
# 安装内容:
#   1. Playwright Chromium 浏览器 (Python + Node.js 共用)
#   2. 系统依赖库 (libnspr4 等，无 sudo)
#   3. 中文字体 (文泉驿微米黑)
#   4. Node.js RedNote-MCP (小红书 MCP Server)
#   5. Cookie 存储目录
#   6. 环境验证
#
# 使用: bash scripts/setup_china_sources.sh
# 迁移: 复制 ~/.local/playwright-libs ~/.local/china_cookies ~/.cache/ms-playwright
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOCAL_DIR="$HOME/.local"
COOKIE_DIR="$LOCAL_DIR/china_cookies"
FONT_DIR="$LOCAL_DIR/share/fonts"
PLAYWRIGHT_LIBS="$LOCAL_DIR/playwright-libs"

echo "=========================================="
echo "  中国大陆数据源 — 环境安装"
echo "=========================================="
echo ""

# ─── 1. 系统依赖库 (无 sudo) ───
echo "[1/6] 检查 Playwright 系统依赖..."
if [ ! -f "$PLAYWRIGHT_LIBS/libnspr4.so" ]; then
    echo "  下载 libnspr4/libnss3 等..."
    mkdir -p "$PLAYWRIGHT_LIBS" /tmp/playwright-debs
    cd /tmp/playwright-debs
    for pkg in libnspr4 libnss3 libasound2t64; do
        if ! apt download "$pkg" 2>/dev/null; then
            apt download "${pkg}-dev" 2>/dev/null || true
        fi
    done
    for deb in *.deb; do
        dpkg -x "$deb" /tmp/playwright-extract 2>/dev/null || true
    done
    find /tmp/playwright-extract -name "*.so*" -exec cp {} "$PLAYWRIGHT_LIBS/" \; 2>/dev/null || true
    rm -rf /tmp/playwright-debs /tmp/playwright-extract
    echo "  依赖库安装完成: $(ls $PLAYWRIGHT_LIBS/*.so* 2>/dev/null | wc -l) 个文件"
else
    echo "  依赖库已安装 ✓"
fi

# ─── 2. 中文字体 ───
echo ""
echo "[2/6] 检查中文字体..."
if [ -z "$(fc-list :lang=zh 2>/dev/null)" ]; then
    echo "  下载文泉驿微米黑..."
    cd /tmp
    apt download fonts-wqy-microhei 2>/dev/null || true
    if [ -f fonts-wqy-microhei*.deb ]; then
        mkdir -p /tmp/fonts-wqy "$FONT_DIR"
        dpkg -x fonts-wqy-microhei*.deb /tmp/fonts-wqy 2>/dev/null || true
        cp /tmp/fonts-wqy/usr/share/fonts/truetype/wqy/*.ttc "$FONT_DIR/" 2>/dev/null || true
        fc-cache -f "$FONT_DIR" 2>/dev/null || true
        rm -rf /tmp/fonts-wqy /tmp/fonts-wqy-microhei*.deb
    fi
    echo "  字体安装完成"
else
    echo "  中文字体已安装 ✓"
fi

# ─── 3. Playwright Chromium ───
echo ""
echo "[3/6] 检查 Playwright 浏览器..."
CHROMIUM_DIR="$HOME/.cache/ms-playwright"
if [ -z "$(find "$CHROMIUM_DIR" -name chrome -type f 2>/dev/null)" ]; then
    echo "  安装 Playwright Chromium (Python)..."
    python3 -m playwright install chromium 2>&1 | tail -1 || true
    echo "  安装 Playwright Chromium (Node.js)..."
    npx playwright install chromium 2>&1 | tail -1 || true
else
    echo "  Chromium 已安装 ✓"
fi

# ─── 4. Node.js RedNote-MCP ───
echo ""
echo "[4/6] 检查 RedNote-MCP..."
if ! command -v rednote-mcp &>/dev/null; then
    echo "  安装 rednote-mcp..."
    npm install -g rednote-mcp 2>&1 | tail -1
else
    echo "  RedNote-MCP 已安装 ✓ ($(rednote-mcp --version 2>/dev/null || echo 'ok'))"
fi

# ─── 5. Cookie 存储目录 ───
echo ""
echo "[5/6] 创建 Cookie 存储目录..."
mkdir -p "$COOKIE_DIR"
echo "  存储路径: $COOKIE_DIR"

# ─── 6. 环境变量 ───
echo ""
echo "[6/6] 环境变量配置..."
PROFILE_FILE="$HOME/.bashrc"
MARKER="# china_datasource_env"

if ! grep -q "$MARKER" "$PROFILE_FILE" 2>/dev/null; then
    cat >> "$PROFILE_FILE" << EOF
$MARKER
export LD_LIBRARY_PATH="$PLAYWRIGHT_LIBS:\$LD_LIBRARY_PATH"
export NODE_PATH="\$(npm root -g 2>/dev/null):\$NODE_PATH"
EOF
    echo "  已添加到 ~/.bashrc"
else
    echo "  环境变量已配置 ✓"
fi

# ─── 验证 ───
echo ""
echo "=========================================="
echo "  验证"
echo "=========================================="
echo ""

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  ✓ $name"
    else
        echo "  ✗ $name (可能需要 Cookie)"
    fi
}

echo "  Python Collector:"
check "  BilibiliCollector" python3 -c "import sys;sys.path.insert(0,'$PROJECT_DIR/src');from ecommerce_data_pipeline.collectors.bilibili_collector import BilibiliCollector;BilibiliCollector().collect_popular(count=3);print('ok')"
check "  ZhihuCollector" python3 -c "import sys;sys.path.insert(0,'$PROJECT_DIR/src');from ecommerce_data_pipeline.collectors.zhihu_collector import ZhihuCollector;c=ZhihuCollector();s=c.collect_explore();print(f'{len(s)} signals')"

echo ""
echo "  Cookie 状态:"
for site in xiaohongshu zhihu weibo; do
    python3 -c "
import sys; sys.path.insert(0,'$PROJECT_DIR/src')
from ecommerce_data_pipeline.utils.cookies import check_valid
info = check_valid('$site')
status = '✓' if info['exists'] else '✗ 未配置'
keys = ','.join(info.get('key_cookies',[]))
print(f'  {status} $site ({keys})')
" 2>/dev/null || echo "  ? $site"
done

echo ""
echo "=========================================="
echo "  安装完成!"
echo ""
echo "  下一步:"
echo "    1. 在 Windows 浏览器登录 知乎/微博"
echo "    2. F12 Console 执行以下代码导出 Cookie:"
echo '       JSON.stringify(document.cookie.split("; ").reduce((a,c)=>{const[p,...v]=c.split("=");a[p]=v.join("=");return a},{}))'
echo "    3. 运行对应的 collector 或 experiment 脚本"
echo ""
echo "  迁移到其他机器:"
echo "    需要复制的目录:"
echo "      ~/.local/playwright-libs/    (系统依赖库)"
echo "      ~/.local/china_cookies/      (登录 Cookie)"
echo "      ~/.cache/ms-playwright/      (Chromium 浏览器)"
echo "    并在新机器上添加环境变量到 ~/.bashrc"
echo "=========================================="
