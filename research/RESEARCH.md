# 数据源调研 — 综合结论

> 调研日期：2026-07-04
> 最新状态：聚焦中国大陆趋势信号，已完成 4/5 个 Layer 1-3 数据源的采集落地
> 架构：Stage 1 (RawPipeline 原始落地) → Stage 2 (SignalPipeline 信息挖掘)
> 环境：WSL (Ubuntu 24.04) / Python 3.12 / Node.js 20 / 无 sudo
> Playwright: 已解决（手动提取 deb 依赖到 ~/.local/playwright-libs）

## 一、中国大陆数据源 — 最终结论

| 数据源 | Layer | 接入方式 | 登录方式 | 状态 | 采集量 |
|--------|-------|---------|---------|------|--------|
| **B站** | 1-3 | httpx → 公开 API | 无需登录 | ✅ | 220条 (热门+排行+评论) |
| **知乎** | 1 | httpx → /explore + /hot API | Playwright stealth 扫码 | ✅ | 62条 (热点问题) |
| **微博** | 3 | httpx → 热搜 JSON API | Playwright stealth 扫码 | ✅ | 51条 (热搜话题) |
| **小红书** | 1-3 | Playwright stealth | Playwright stealth 扫码 | ✅ | 20条 (推荐+搜索) |
| **抖音** | 3 | — | — | ❌ | 推荐替代方案 |
| **百度指数** | 4 | Playwright | ❌ SPA 空渲染 | ❌ | 待攻克 |
| **淘宝/京东** | 5 | Playwright | ❌ 登录墙 | ❌ | 待攻克 |
| **1688** | 6 | Playwright | ❌ 登录墙+Captcha | ❌ | 待攻克 |

## 二、技术突破记录

### B站 — 最简单的
- 5 个公开 JSON API 端点，境外 IP 直接访问
- `/x/web-interface/popular` / `ranking/v2` / `view` (热门/排行/详情)
- `/x/v2/reply` (评论) / `/x/web-interface/card` (UP主信息)
- 搜索 API (`/x/web-interface/search`) 返回 412 — 需 Cookie

### 知乎 — 无登录也能拿到数据
- `/explore` 发现页返回 181KB HTML，含问题标题+回答数+链接
- `/hot` 热榜需要 Cookie，但 `/api/v3/feed/topstory/hot-lists/total` JSON API 更好用
- 登录方案：Playwright stealth 打开 signin 页 → 扫码 → 等待跳转 → 保存 Cookie

### 微博 — 最顺利
- `weibo.com/ajax/side/hotSearch` JSON API 配合 Cookie 返回完整热搜
- 移动端 API (`m.weibo.cn`) 被 Sina Visitor System 拦截
- 登录方案：Playwright stealth 打开登录页 → 扫码 → 检测跳转 → 保存 Cookie

### 小红书 — 最难攻克
- 网页版反爬 T0 级别：shield 算法、xsec_token、频率限制、automation 检测
- 解决方案：**Playwright stealth + persistent context**
  - `launchPersistentContext` + userDataDir (模拟真实浏览器)
  - `--disable-blink-features=AutomationControlled`
  - JS 注入隐藏 `navigator.webdriver` / 伪造 `chrome.runtime` / 伪造 `plugins`
  - 中文字体安装 (文泉驿微米黑，无 sudo)
- 额外方案：RedNote-MCP (Node.js MCP Server，可直接被 AI 工具调用)

### 抖音 — 自研不可行
- 网页版加载 UI 壳但无实际内容数据
- 推荐第三方付费 API：蝉妈妈/飞瓜数据 ($500-2000/月)
- 早期信号替代：知乎/小红书/B站 已覆盖 80% 话题重叠

## 三、架构演进

```
v1 (废弃): 单 Collector 内嵌分类逻辑
    Collector → mark_signal(layer, type, domain, keywords)

v2 (当前): 两阶段分离
    Stage 1: RawCollector → data/raw/*.jsonl    (零信息损失)
    Stage 2: SignalExtractor → data/signals/*.jsonl (分类/理解)
```

## 四、迁移指南

从本机迁移到远程 agent 机器需复制：
```bash
~/.local/playwright-libs/    # 系统依赖库
~/.local/china_cookies/      # 登录 Cookie
~/.cache/ms-playwright/      # Chromium 浏览器
~/.mcp/rednote/              # RedNote-MCP Cookie (Node.js)
```

运行 `bash scripts/setup_china_sources.sh` 自动安装依赖。

## 五、下一步

1. Stage 2 SignalPipeline — 从 `data/raw/` 提取趋势信号
2. Layer 4-6 数据源攻克 (百度指数/淘宝/1688)
3. Cookie 过期自动刷新机制
