# Google Trends — 数据源调研结论

## 状态：可用

## 可用能力

| 功能 | 状态 | 说明 |
|------|------|------|
| interest_over_time | OK | 日/周粒度相对热度（0-100），最多5个关键词对比 |
| related_queries | OK | 提供 top queries（常搜）和 rising queries（飙升），后者是发现新趋势的关键 |
| related_topics | 不OK | pytrends 内部 bug，list index out of range |
| multi-keyword | OK | 最多5个关键词同时对比 |
| interest_by_region | OK | 按地区/城市拆分热度 |
| daily resolution | OK | 时间窗≤3个月可得日粒度，更长变周粒度 |

## 限制

- 数据是归一化的相对值（0-100），不是绝对搜索量
- 单次请求最多5个关键词
- 建议请求间隔≥2秒，过频可能触发临时封禁
- `related_topics` 有已知 bug，暂不可用

## 对 Trend Agent 的价值

- **rising queries**（飙升词）：核心信号，可直接作为新兴产品发现线索
- **multi-keyword comparison**：可设置已知产品作为 benchmark，对比新关键词热度
- **regional interest**：可识别地域性产品机会

## 采集方案建议

- Tech: pytrends + httpx（pytrends 底层用 requests，可桥接到 httpx）
- 频次: 每日采一次即可（Google Trends 数据本身非实时）
- 关键词: 由配置驱动，品类关键词列表可定期更新
