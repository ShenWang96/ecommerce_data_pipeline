# 中国大陆数据源可行性验证

> 测试日期：2026-07-04
> 环境：WSL (Ubuntu 24.04) / 中国境外 IP（美国）

## 一、逐层测试结果

按 `china_datasource_analysis.md` 定义的 6 层信号链，逐源验证。

### Layer 1 — 需求萌芽（知乎 / 小红书 / B站评论）

| 数据源 | 接入方式 | 状态 | 实测数据 |
|--------|---------|------|---------|
| **B站评论 API** | `api.bilibili.com/x/v2/reply` | ✅ | 评论全文 + 点赞数，无需登录 |
| **知乎 /explore** | Playwright | ⚠️ | 热点问题标题+浏览量+回答数，需登录才看全文 |
| **知乎 /hot** | Playwright | ❌ | 登录墙 |
| **小红书** | Playwright | ❌ | 登录墙（仅1462字符登录引导） |

### Layer 2 — 理念形成（小红书创作者 / B站UP主 / 公众号）

| 数据源 | 接入方式 | 状态 | 实测数据 |
|--------|---------|------|---------|
| **B站视频详情 API** | `api.bilibili.com/x/web-interface/view` | ✅ | 标题、描述、标签、播放/点赞/投币/收藏/转发 |
| **B站UP主视频列表** | `api.bilibili.com/x/space/arc/search` | ✅ | UP主全部视频（待单独验证） |
| **小红书创作者** | Playwright | ❌ | 登录墙 |
| **微信公众号** | — | ❌ | 无公开 API，仅搜狗微信搜索可试 |

### Layer 3 — 内容传播（抖音 / 小红书热榜 / 微博 / B站排行榜）

| 数据源 | 接入方式 | 状态 | 实测数据 |
|--------|---------|------|---------|
| **B站热门 API** | `api.bilibili.com/x/web-interface/popular` | ✅ | 10条热门视频，播放/弹幕/评论/收藏 |
| **B站排行榜 API** | `api.bilibili.com/x/web-interface/ranking/v2` | ✅ | 100条排行视频，按分类筛选 |
| **微博热搜 mobile** | `m.weibo.cn/api/container/getIndex` | ⚠️ | 首次可用，后续 302 重定向（IP频率限制） |
| **微博热搜 web** | `weibo.com/ajax/side/hotSearch` | ❌ | 403 |
| **抖音** | Playwright | ❌ | 超时，完全拦截 |
| **B站搜索 API** | `api.bilibili.com/x/web-interface/search` | ❌ | 412 Precondition Failed（需 cookie） |

### Layer 4 — 大众关注（百度指数 / 微信指数）

| 数据源 | 接入方式 | 状态 | 实测数据 |
|--------|---------|------|---------|
| **百度指数** | Playwright | ❌ | 空 SPA，0 字符，完全不可用 |
| **百度指数** | httpx | ⚠️ | 200 返回 2KB HTML，无数据 |
| **微信指数** | — | ❌ | 仅微信小程序内可用，无公开 API |

### Layer 5 — 商业验证（淘宝 / 京东 / 拼多多 / 抖音商城）

| 数据源 | 接入方式 | 状态 | 备注 |
|--------|---------|------|------|
| **淘宝** | Playwright | ❌ | 之前测试：强制登录 + "加载中..." |
| **淘宝移动 API** | httpx | ❌ | RGV587_ERROR: mtop 签名拦截 |
| **京东** | Playwright | ❌ | 搜索跳转登录页 |
| **拼多多** | Playwright | ❌ | 搜索跳转登录页 "登录" |
| **抖音商城** | — | ❌ | 与抖音主站相同拦截 |

### Layer 6 — 供应扩张（1688 / 义乌指数）

| 数据源 | 接入方式 | 状态 | 实测数据 |
|--------|---------|------|---------|
| **1688** | Playwright | ❌ | 之前测试：登录墙 + Captcha |
| **义乌指数** | Playwright | ⚠️ | 3340 字符可见，但有 Captcha 标记 |
| **1688 API** | httpx | ❌ | "FAIL_SYS_API_NOT_FOUNDED" |

---

## 二、可行性汇总

```
Layer 1 (需求萌芽)     Layer 2 (理念形成)     Layer 3 (内容传播)
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │ B站 ✅    │          │ B站 ✅    │          │ B站 ✅    │
  │ 知乎 ⚠️   │          │ 公众号 ❌  │          │ 微博 ⚠️   │
  │ 小红书 ❌  │          │ 小红书 ❌  │          │ 抖音 ❌   │
  └──────────┘          └──────────┘          └──────────┘

Layer 4 (大众关注)    Layer 5 (商业验证)     Layer 6 (供应扩张)
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │ 百度 ❌   │          │ 淘宝 ❌   │          │ 1688 ❌   │
  │ 微信 ❌   │          │ 京东 ❌   │          │ 义乌 ⚠️   │
  └──────────┘          │ 拼多多 ❌  │          └──────────┘
                        └──────────┘
```

**核心发现：B站是唯一在 Layer 1-3 全线可用的中国数据源。**

---

## 三、B站 API 能力清单（已确认可用）

以下端点全部无需登录，境外 IP 可直接访问：

| 端点 | 用途 | 返回数据 |
|------|------|---------|
| `/x/web-interface/popular` | 热门内容 | 视频标题 + 播放/弹幕/评论/收藏/分享/投币 |
| `/x/web-interface/ranking/v2` | 全站排行榜 | 100 条排名视频，支持按分区筛选 |
| `/x/web-interface/view?bvid=` | 视频详情 | 标题、描述、分区标签、UP主信息、全量统计 |
| `/x/v2/reply?type=1&oid=` | 视频评论 | 评论文本 + 点赞数 + 回复数 |
| `/x/space/arc/search?mid=` | UP主视频列表 | 某UP主的历史视频（待验证但大概率可用） |
| `/x/web-interface/card?mid=` | UP主信息 | 粉丝数、关注数（待验证） |

### 数据提取示例

```python
# 热门视频
GET https://api.bilibili.com/x/web-interface/popular?pn=1&ps=50
→ { "data": { "list": [
    { "title": "华为Mate 80 Pro性能分析", 
      "stat": {"view": 1410080, "reply": 3500, "favorite": 8500, "like": 22000},
      "owner": {"name": "某科技UP"},
      "tname": "科技" }
]}}

# 视频评论 (需求信号)
GET https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn=1&ps=20&sort=2
→ { "data": { "replies": [
    { "content": {"message": "有没有更方便的收纳方式"}, "like": 342 },
    { "content": {"message": "这东西太贵了，有没有平替"}, "like": 128 }
]}}
```

---

## 四、结论：可行的信号链

实际可行的中国信号链只有 **前半段**（早期信号）：

```
需求萌芽 ──────→ 理念形成 ──────→ 内容传播 ──→ [断层] ──→ [断层] ──→ [断层]
   B站评论         B站视频详情       B站热门/排行      
   知乎 ⚠️                                         
                                                商业验证层   供应扩张层
                                                (全部不可用)  (全部不可用)
```

但这恰好符合项目的设计目标——**预测早期趋势，而非跟踪已有销量**。Layer 1-3 的早期信号比 Layer 5-6 的销售数据更有预测价值。

---

## 五、推荐行动方案

### 立即可做（代码量小，数据质量高）

| 优先级 | Collector | 数据 | 对应 Layer |
|--------|----------|------|-----------|
| P0 | **B站热门 Collector** | 50条热门视频 + 统计 | Layer 3 |
| P0 | **B站排行榜 Collector** | 100条排行 + 按分区 | Layer 3 |
| P1 | **B站评论 Collector** | 视频评论文本 | Layer 1 |
| P1 | **B站视频详情 Collector** | 标题/描述/标签/统计 | Layer 2 |
| P2 | **知乎 explore Collector** | 热点问题+浏览量 | Layer 1 |

### 需要额外投入（账号/代理/付费）

| 数据源 | 需要什么 | Layer |
|--------|---------|------|
| 微博 | 控制请求频率，可能需 cookie | Layer 3 |
| 义乌指数 | 研究数据提取方式，回避 captcha | Layer 6 |
| 小红书 | 需登录态 + 反自动化检测 | Layer 1-3 |
| 百度指数 | 需百度账号登录 | Layer 4 |
| 淘宝/京东 | 需开放平台 API 或登录 | Layer 5 |
| 1688 | 需登录 + 反爬 | Layer 6 |

### 近期不做

- 抖音（拦截强度最高，投入产出比低）
- 拼多多（与淘宝同类，重复投入）
- 微信指数（仅小程序，无抓取途径）

### 长线：补充商业验证层

Layer 5-6 是当前最大盲区。建议从以下路径突破：

1. **淘宝开放平台 (TOP)** — 申请开发者资质，获取官方 API
2. **京东开放平台** — 同上
3. **1688 分销 API** — 部分接口对合作伙伴开放
4. **义乌指数官网** — 研究其数据接口（网站有结构化数据但需规避 captcha）

---

## 六、实际落地产出（阶段成果）

> 更新日期：2026-07-04 (同日完成)

### 六.1 两阶段 Pipeline 架构

```
Stage 1 (已落地): RawPipeline
  4 个 RawCollector → data/raw/{source}_*.jsonl (原始数据，零信息损失)
  
Stage 2 (框架就绪): SignalPipeline  
  读取 data/raw/ → 信号分类+关键词+领域 → data/signals/*.jsonl
```

### 六.2 各平台攻克方案

| 数据源 | 攻克方案 | 关键参数 |
|--------|---------|---------|
| **B站** | httpx 公开 API，无需登录 | 220 条/session |
| **知乎** | Playwright stealth → 扫码登录 → Cookie 持久化 | `launchPersistentContext` + `--disable-blink-features` + JS 注入隐藏 webdriver |
| **微博** | 同上 | 同上 |
| **小红书** | 同上 + 中文字体安装 + 4 个关键 Cookie (a1/web_session/websectiga/acw_tc) | `launchPersistentContext` + userDataDir 持久化 |
| **抖音** | 不可自研，推荐第三方: 蝉妈妈/飞瓜数据 | $500-2000/月 |

### 六.3 依赖与迁移

- 系统库: `~/.local/playwright-libs/` (libnspr4, libnss3 等，无 sudo 安装)
- Cookie: `~/.local/china_cookies/{site}.json` (Playwright 格式)
- Chromium: `~/.cache/ms-playwright/`
- 字体: `~/.local/share/fonts/wqy-microhei.ttc`
- 环境变量: 见 `scripts/env.sh`
- 安装脚本: `bash scripts/setup_china_sources.sh`

## 七、下一步（当前最新）

- [x] B站 Collector — 已完成 (RawCollector)
- [x] 知乎 Collector — 已完成 (RawCollector, /explore + /hot API)
- [x] 微博 Collector — 已完成 (RawCollector, 热搜 JSON API)
- [x] 小红书 Collector — 已完成 (RawCollector, Playwright stealth)
- [ ] Stage 2 SignalPipeline — 从 raw 数据提取趋势信号（框架已就绪）
- [ ] Layer 4-6 数据源 (百度指数/淘宝/1688)
- [ ] Cookie 自动刷新机制
