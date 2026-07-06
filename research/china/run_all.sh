#!/bin/bash
# 运行所有需要登录的中国数据源实验
# 如 Cookie 文件不存在，会交互式引导输入
#
# 首次使用：
#   1. 在 Windows 浏览器登录对应网站
#   2. F12 → Console → 执行以下代码：
#      JSON.stringify(document.cookie.split("; ").reduce((a,c)=>{const[p,...v]=c.split("=");a[p]=v.join("=");return a},{}))
#   3. 复制输出的 JSON 字符串
#   4. 运行本脚本，按提示粘贴

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

export LD_LIBRARY_PATH="$HOME/.local/playwright-libs:${LD_LIBRARY_PATH}"

echo "============================================"
echo "  中国大陆数据源 — 登录后测试"
echo "  按 Ctrl+C 跳过当前测试"
echo "============================================"
echo

sources=(
    "知乎:zhihu_experiment.py"
    "淘宝:taobao_experiment.py"
    "小红书:xiaohongshu_experiment.py"
    "百度指数:baidu_index_experiment.py"
    "1688:1688_experiment.py"
    "京东:jd_experiment.py"
    "拼多多:pdd_experiment.py"
    "微博:weibo_experiment.py"
)

for pair in "${sources[@]}"; do
    name="${pair%%:*}"
    script="${pair##*:}"
    if [ ! -f "$SCRIPT_DIR/$script" ]; then
        echo "[跳过] $name — $script 不存在"
        continue
    fi
    echo
    echo ">>> 运行: $name <<<"
    set +e
    python3 "$SCRIPT_DIR/$script"
    rc=$?
    set -e
    if [ $rc -ne 0 ]; then
        echo "  [$name] 退出码=$rc"
    fi
    echo "---"
    sleep 1
done

echo
echo "所有实验完成。结果文件位于 $SCRIPT_DIR/"
