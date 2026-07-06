# 中国大陆数据源实验

## 当前状态 (2026-07-04)

| 平台 | 登录方式 | Cookie 文件 | 状态 |
|------|---------|------------|------|
| B站 | 公开 API，无需登录 | — | ✅ |
| 知乎 | `node zhihu_login.js` | `~/.local/china_cookies/zhihu.json` | ✅ 27条 |
| 微博 | `node weibo_login.js` | `~/.local/china_cookies/weibo.json` | ✅ 20条 |
| 小红书 | `node xhs_login_stealth.js` | `~/.local/china_cookies/xiaohongshu.json` | ✅ 17条 |
| 抖音 | ❌ 不可行 | — | 替代: 蝉妈妈/飞瓜 |

## 登录方式 (Cookie 过期后重新获取)

每个平台运行对应的 Playwright stealth 登录脚本，浏览器会弹出，扫码/输入验证码登录后自动保存 Cookie：

```bash
# 设置环境变量
NODE_PATH="$(npm root -g)"
LD_LIBRARY_PATH="$HOME/.local/playwright-libs"

# 登录知乎
node research/china/zhihu_login.js

# 登录微博  
node research/china/weibo_login.js

# 登录小红书
node research/china/xhs_login_stealth.js
```

> 注意：需要 node 环境 + npm install -g playwright

## 文件说明

| 文件 | 用途 |
|------|------|
| `zhihu_login.js` | 知乎 Playwright stealth 登录 → Cookie 保存 |
| `weibo_login.js` | 微博 Playwright stealth 登录 → Cookie 保存 |
| `xhs_login_stealth.js` | 小红书 stealth 登录 → Cookie 保存 |
| `session.py` | Cookie 管理工具 (旧版，已被 `utils/cookies.py` 替代) |
| `weibo_v2_experiment.py` | 微博多策略攻克实验 |
| `zhihu_v2_experiment.py` | 知乎多策略实验 |
| `douyin_experiment.py` | 抖音可行性评估 |
| `bilibili/experiment.py` | B站 API 验证 |
| `run_all.sh` | 旧版一键运行实验 (已过时) |

## 架构

原始落地阶段使用 `src/ecommerce_data_pipeline/` 下的 RawCollector + RawPipeline，不再需要手动运行这些实验脚本。

这些实验脚本仅用于：
1. 初次登录获取 Cookie
2. Cookie 过期后重新登录
3. 调试和探索新的数据提取方式
