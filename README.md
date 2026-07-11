# E-commerce Product Selection Pipeline

> 上次会话: 2026-07-04 | 当前阶段: Stage 1 原始数据落地完成

## ⚡ 快速重拾 (Resume Checklist)

```bash
# 1. 加载环境
source scripts/env.sh

# 2. 验证环境 (3 项都应显示 ✓)
python3 -c "
import sys; sys.path.insert(0,'src')
from ecommerce_data_pipeline.utils.cookies import check_valid
for s in ['zhihu','weibo','xiaohongshu']:
    i=check_valid(s); print(f'  {\"✓\" if i[\"exists\"] else \"✗\"} {s} cookie')
import httpx; print('  ✓ httpx')
from playwright.sync_api import sync_playwright; print('  ✓ playwright')
"

# 3. 如果 Cookie 过期，重新登录 → 见 research/china/README.md
# 4. 运行采集
LD_LIBRARY_PATH="$HOME/.local/playwright-libs" python3 -c "
import sys; sys.path.insert(0,'src')
from ecommerce_data_pipeline.raw_pipeline import RawPipeline
RawPipeline(keywords=['收纳','宠物','家居']).run()
"
```

## 两阶段架构

- **Stage 1 (RawPipeline)**: 原始数据落地 — 完整 HTML/图片 URL/API 响应，零信息损失
- **Stage 2 (SignalPipeline)**: 未来 — 读取原始数据做信号分类、关键词提取、领域识别

## 核心理念

> 预测"哪些新的消费需求、生活方式或行为习惯，未来有可能演变成新的商品机会"，
> 而不是"哪些商品正在卖得好"。

参考：[china_datasource_analysis.md](research/china_datasource_analysis.md) — SOP 六层信号链

```
需求萌芽 → 理念形成 → 内容传播 → 大众关注 → 商业验证 → 供应扩张
  Layer1     Layer2     Layer3     Layer4     Layer5     Layer6
```

## 项目结构

```
ecommerce_data_pipeline/
├── src/ecommerce_data_pipeline/
│   ├── collectors/
│   │   ├── bilibili_raw_collector.py      # B站 — httpx API (无需登录)
│   │   ├── zhihu_raw_collector.py         # 知乎 — httpx /explore + /hot API
│   │   ├── weibo_raw_collector.py         # 微博 — httpx 热搜 API
│   │   └── xiaohongshu_raw_collector.py   # 小红书 — Playwright stealth
│   ├── models/
│   │   ├── raw_record.py                  # RawRecord (原始数据模型)
│   │   └── signal.py                      # TrendSignal (分析后信号模型)
│   ├── utils/
│   │   ├── cookies.py                     # 统一 Cookie 管理
│   │   └── signal_classifier.py           # 信号分类器 (Stage 2 用)
│   ├── raw_pipeline.py                    # Stage 1 原始数据落地管道
│   └── pipeline.py                        # Stage 2 信号提取管道 (开发中)
├── research/
│   ├── china_datasource_analysis.md       # ★ SOP 六层信号链总纲
│   ├── CHINA_FEASIBILITY.md               # 各平台可行性验证结论
│   ├── RESEARCH.md                        # 调研日志
│   └── china/
│       ├── README.md                      # 登录实验说明
│       ├── session.py                     # Cookie 管理 (旧版)
│       ├── weibo_login.js                 # 微博 Playwright stealth 登录
│       ├── zhihu_login.js                 # 知乎 Playwright stealth 登录
│       ├── xhs_login_stealth.js           # 小红书 stealth 登录
│       ├── bilibili/experiment.py         # B站 API 探索脚本
│       └── douyin_experiment.py           # 抖音可行性评估
├── scripts/
│   ├── setup_china_sources.sh             # 统一环境安装
│   ├── env.sh                             # 运行时环境变量
│   ├── generate_report.py                 # HTML 报告生成
│   └── rednote_mcp.sh                     # RedNote-MCP 封装
├── config/pipeline.yaml                   # 配置文件
└── data/                                  # 输出 (gitignored)
    ├── raw/                               # Stage 1: 原始数据
    │   ├── bilibili_*.jsonl
    │   ├── zhihu_*.jsonl
    │   ├── weibo_*.jsonl
    │   ├── xiaohongshu_*.jsonl
    │   └── all_*.jsonl                    # 合并
    └── signals/                           # Stage 2: 分析后信号 (未来)
```

## 数据源状态

| 数据源 | Layer | 接入方式 | Cookie | 状态 |
|--------|-------|---------|--------|------|
| B站 | 1-3 | httpx 公开 API | 无需 | ✅ 220条/video+comment |
| 知乎 | 1 | httpx /explore + /hot API | ✅ 27条 | ✅ 62条/question |
| 微博 | 3 | httpx 热搜 API | ✅ 20条 | ✅ 51条/topic |
| 小红书 | 1-3 | Playwright stealth | ✅ 17条 | ✅ 20条/note |
| 抖音 | 3 | ❌ 自研不可行 | — | 替代: 蝉妈妈/飞瓜 API |
| 百度指数 | 4 | ❌ SPA 空渲染 | — | 待攻克 |
| 淘宝/京东/1688 | 5-6 | ❌ 登录墙+反爬 | — | 待攻克 |

## 运行

```bash
# 环境安装 (首次)
bash scripts/setup_china_sources.sh
source scripts/env.sh

# Stage 1: 原始数据落地
LD_LIBRARY_PATH="$HOME/.local/playwright-libs" python3 -c "
import sys; sys.path.insert(0,'src')
from ecommerce_data_pipeline.raw_pipeline import RawPipeline
RawPipeline(keywords=['收纳','宠物','家居']).run()
"

# 生成 HTML 报告 (读取 Stage 1 的输出)
python3 scripts/generate_report.py data/raw/all_*.jsonl
```

## 当前进度

- [x] SOP 六层信号链定稿 (v1)
- [x] 4 个平台可行性验证 + 反爬攻克
- [x] RawRecord 数据模型 (零信息损失)
- [x] Stage 1 RawPipeline — 4 源原始数据落地
- [x] Stage 2 信号模型 + 分类器 (基础版)
- [ ] Stage 2 SignalPipeline — 信号提取管道 (下一步)
- [ ] Layer 4-6 数据源 (百度指数/淘宝/1688)
- [ ] Cookie 自动刷新机制
- [ ] Agent 评分引擎
- [ ] 闭环验证系统

## 扫码登录 (2026-07-11 新增)

Headless 模式扫码登录脚本，支持 知乎/微博/小红书：

```bash
# 后台启动 + 截图二维码 + 轮询等待登录
LD_LIBRARY_PATH="$HOME/.local/playwright-libs" python3 scripts/qr_login.py zhihu
LD_LIBRARY_PATH="$HOME/.local/playwright-libs" python3 scripts/qr_login.py weibo
LD_LIBRARY_PATH="$HOME/.local/playwright-libs" python3 scripts/qr_login.py xiaohongshu
```

登录成功后 Cookie 自动保存到 `~/.local/china_cookies/{site}.json`，采集器自动加载。

## Stage 1 落地数据样例

最新一版采集数据在 `data/raw/` 目录下，包含四源合并的 JSONL：

```bash
# 加载验证
python3 -c "
import json
for line in open([f for f in __import__('glob').glob('data/raw/all_*.jsonl')][-1]):
    r = json.loads(line)
    print(f'{r[\"source\"]:12s} [{r[\"record_type\"]:8s}] {r[\"title\"][:50]}')
"
```
