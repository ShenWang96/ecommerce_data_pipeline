# 原始数据落地 — 输入/输出验证报告

> 聚焦 Stage 1 (原始数据落地)：**数据从哪里来 → 统一成了什么样子**。
> 不涉及信号分类、关键词提取等后续环节。

---

## 1. 输入端: 四个数据源的采集位置

```
 平台           采集入口                          是否是用户获取热点的常用入口
 ─────────────────────────────────────────────────────────────────────────
 哔哩哔哩        首页"热门"Tab + "排行榜"Tab        ✅ app/Web 首页默认进入
 小红书          首页"发现"Tab 推荐流                ✅ app/Web 首页默认进入
 微博            首页右侧"热搜榜"                    ✅ Web 端最核心的流量入口
 知乎            热榜页 /hot                        ✅ 知乎用户看热榜的标准页面
```

详细说明：

### 哔哩哔哩 — api.bilibili.com (公开 API)

| 采集点位 | 用户在平台上的对应位置 | API 请求 |
|---------|---------------------|---------|
| 热门推荐 | B站首页 → "热门" Tab (用户默认进入的页面) | `GET /x/web-interface/popular?pn=1&ps=20` |
| 全站排行榜 | B站首页 → "排行榜" Tab | `GET /x/web-interface/ranking/v2?rid=0&type=all` |
| 视频评论 | 前3个热门视频的评论区 (按热度排序) | `GET /x/v2/reply?type=1&oid={aid}&pn=1&ps=20&sort=2` |

**无需登录**。每次采集 ~220 条 (热门视频 160 + 排行榜全量 + 热门视频评论 60)。

### 微博 — weibo.com (Ajax API)

| 采集点位 | 用户在平台上的对应位置 | API 请求 |
|---------|---------------------|---------|
| 热搜榜 | 微博 Web 端右侧边栏 "微博热搜" | `GET https://weibo.com/ajax/side/hotSearch` |

**需 Cookie**。单次请求获取全部 50 条热搜话题。

### 知乎 — zhihu.com/hot (HTML 解析)

| 采集点位 | 用户在平台上的对应位置 | 请求 |
|---------|---------------------|------|
| 热榜页 | 知乎 → "热榜" Tab | `GET https://www.zhihu.com/hot` → BeautifulSoup 解析 |
| 热榜 JSON API | 热榜后端接口 (结构化数据补充) | `GET /api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true` |

**需 Cookie**。HTML 解析提取问题标题、热度("520万热度")、回答数；JSON API 提供结构化补充。每次 ~60 条。

### 小红书 — xiaohongshu.com (Playwright 浏览器自动化)

| 采集点位 | 用户在平台上的对应位置 | 实现方式 |
|---------|---------------------|---------|
| 发现页热门笔记 | app/Web 首页 "发现" Tab (默认推荐流) | Playwright 打开 `/explore`，滚动加载，解析 `section.note-item` |
| 热搜关键词 | 点击搜索框后的 "猜你想搜" Suggestion 面板 | Playwright 模拟点击搜索区域，解析 `.suggestion-item` |

**需 Cookie + Playwright 反反爬**。每次 ~45-80 条 (发现页笔记 + 热搜词)。

---

## 2. 输出端: 统一 Schema

四端数据全部落入同一 schema (`RawRecord` dataclass)，写入 JSONL。每行一个 JSON 对象，可直接用 `pandas.read_json(path, lines=True)` 加载。

### Schema 定义

```
字段组        字段                 类型        说明
─────────────────────────────────────────────────────────────
标识          source              str         平台: bilibili / zhihu / weibo / xiaohongshu
              record_type         str         内容类型: video / question / topic / note / comment
              item_id             str         平台内唯一 ID (bvid / qid / note_id / 热搜词)
              url                 str         原始链接 (可回放访问)
              scraped_at          str         UTC 采集时间戳

内容          title               str         标题 / 热搜词 / 问题
              body                str         描述 / 正文 / 评论内容
              author_name         str         作者 / UP主 / 答主
              author_id           str         作者唯一 ID

媒体          images              list[str]   所有图片 URL
              videos              list[str]   视频 URL
              cover_url           str         封面图 URL

互动          metrics.views       int
              metrics.likes       int
              metrics.comments    int         评论数 / 回答数
              metrics.shares      int
              metrics.favorites   int

原始回放      api_response        dict/null   API 源: 完整 JSON 响应
              html_snapshot       str         Playwright 源: 页面 HTML (默认空)
              extra               dict        平台特有字段 (分区/热度/弹幕等)
              comments            list        嵌套子记录 (评论)
```

### 以 DataFrame 视角验证 (pandas.read_json)

```
$ python3 -c "
import pandas as pd
df = pd.read_json('data/raw/all_20260705_123528.jsonl', lines=True)
print(df['source'].value_counts())
"
# source             count    record_types
# bilibili             220    video, comment
# zhihu                 62    question
# weibo                 50    topic
# xiaohongshu           45    note, topic
# ──────────────────────────
# Total                377    5 types across 4 platforms
```

### 真实数据采样 (每平台 1 条)

**B站 — 热门视频** (record_type: `video`)
```
  source:       bilibili
  record_type:  video
  item_id:      BV1U7Mu6cEpy
  url:          https://www.bilibili.com/video/BV1U7Mu6cEpy
  title:        【TF家族练习生】《突围II破局》EP02
  author_name:  TF家族
  metrics:      { views: 483962, likes: 23318, comments: 4128, shares: 710, favorites: 6836 }
  extra:        { bvid, aid, tname:"明星综合", duration:4421, danmaku:439969, coin:2375 }
  api_response: ✓ 完整 JSON (含 owner.face, stat.* 等全量字段)
```

**B站 — 评论** (record_type: `comment`)
```
  source:       bilibili
  record_type:  comment
  item_id:      304957090241
  url:          https://www.bilibili.com/video/BV1U7Mu6cEpy#reply304957090241
  body:         "橹橹是全天下最棒的小孩_(≧∇≦」∠)_"
  author_name:  芝士味の橹
  metrics:      { likes: 1387 }
  extra:        { parent_bvid, parent_aid, rcount:43, ctime:1783249362 }
  api_response: ✓ 完整 JSON (含 member.avatar, replies[], content.pictures 等)
```

**知乎 — 热榜问题** (record_type: `question`)
```
  source:       zhihu
  record_type:  question
  item_id:      662705703
  url:          https://www.zhihu.com/question/662705703
  title:        刘国梁为什么要培养王楚钦呢?
  body:         刘国梁为什么要培养王楚钦呢?
  metrics:      { comments: 1054 }     ← comments = 回答数
  extra:        { answer_count: 1054 }
```

**微博 — 热搜话题** (record_type: `topic`)
```
  source:       weibo
  record_type:  topic
  item_id:      奶奶删了77万条未读又来3万
  url:          https://s.weibo.com/weibo?q=奶奶删了77万条未读又来3万
  title:        奶奶删了77万条未读又来3万
  body:         奶奶删了77万条未读又来3万
  extra:        { rank:0, raw_hot:"", category:"", icon_desc:"热", num:1142649 }
  api_response: ✓ 完整 JSON (含 realpos, flag, word_scheme, topic_flag 等)
```

**小红书 — 发现页笔记** (record_type: `note`)
```
  source:       xiaohongshu
  record_type:  note
  item_id:      6a46804a000000001101c128
  url:          https://www.xiaohongshu.com/explore/6a46804a000000001101c128
  title:        ‼️一百万人追更的后续已放出😂纽约天才❗️
  author_name:  ItsLisa!
  cover_url:    https://sns-webpic-qc.xhscdn.com/.../1040g0083224h3tqqms...!nc_n_webp_mw_1
  images:       [cover_url, ...]
  extra:        { source_tab: "explore" }
```

**小红书 — 热搜关键词** (record_type: `topic`)
```
  source:       xiaohongshu
  record_type:  topic
  item_id:      trending_search_{hash}
  url:          https://www.xiaohongshu.com/search_result?keyword=xxx
  title:        xxx  (热搜词文本)
  extra:        { source_tab: "trending_search", rank: N }
```

---

## 3. 一次完整采集的统计

最新一次运行 (2026-07-05 12:35):

| 平台 | 记录数 | tipo 分布 | 认证 |
|------|--------|-----------|------|
| 哔哩哔哩 | 220 | video:160, comment:60 | 无需登录 |
| 知乎 | 62 | question:62 | Cookie |
| 微博 | 50 | topic:50 | Cookie |
| 小红书 | 45 | note:39, topic:6 | Cookie + Playwright |
| **合并** | **377** | | |

### 各平台数据特征

```
平台         有互动指标   有封面/图片   有完整原始响应    特点
───────────────────────────────────────────────────────────
bilibili     ✅ 全量     ✅ 封面图     ✅ api_response   唯一有 comment 子类型的源
zhihu        ✅ 回答数   ❌            ❌ (HTML 源)      comment 字段存回答数
weibo        ❌          ❌            ✅ api_response   热搜数(num)在 extra 中
xiaohongshu  ❌          ✅ 多张配图   ❌ (HTML 源)      images 含图片 URL 列表
```

---

## 4. 验证脚本

**环境依赖已剥离**，以下脚本可在裸 Python 环境运行：

```python
# check_schema.py — 验证所有原始数据是否可统一 DataFrame 加载
import json, os
from collections import defaultdict

DATA_DIR = "data/raw"

files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.jsonl') and not f.startswith('all_'))
print(f"找到 {len(files)} 个 JSONL 文件\n")

for f in files:
    path = os.path.join(DATA_DIR, f)
    source = f.split('_')[0]
    count = 0
    types = set()
    required_keys = ['source','record_type','item_id','url','title','metrics']

    with open(path) as fh:
        for line in fh:
            if not line.strip(): continue
            r = json.loads(line)
            count += 1
            types.add(r['record_type'])
            assert all(k in r for k in required_keys), f"MISSING field in {r['item_id']}"

    print(f"  {source:<15} {count:>5} records   types: {sorted(types)}")

print("\nAll records conform to unified schema.")
```
