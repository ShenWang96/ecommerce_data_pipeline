# 1688 / Alibaba — 数据源调研结论

## 状态：Alibaba.com 部分可用（需浏览器），1688.com 不可用（需登录）

## 测试结果

| 平台 | 方法 | 结果 |
|------|------|------|
| **1688.com** | httpx 搜索页 | 被登录墙拦截，5KB空壳页面 |
| **1688.com** | API 端点 | 返回 "API不存在"，需要签名/令牌 |
| **Alibaba.com** | httpx + HTML 解析 | 间歇可用 — 不同CDN节点返回不同内容（服务端渲染 vs 客户端渲染） |
| **Alibaba.com** | JSON 内嵌数据 | 不可靠 — 仅在部分CDN节点出现 |

## Alibaba.com 可提取数据（当HTML可解析时）

| 字段 | 说明 |
|------|------|
| 商品标题 (title) | h2 > a text |
| 价格区间 (price) | CN¥ xxx - xxx，含折扣信息 |
| 最小起订量 (MOQ) | Min. order: N pieces |
| 供应商 (supplier) | 公司名 + 年限 + 评分 + 评价数 |
| 销量 (sold) | N pieces sold / N sold |
| 商品链接 | /product-detail/xxx.html |
| 分页 | 需确认（有 rel="next" 链接） |

## 反爬机制

- 1688.com：强登录墙，未登录直接跳转/空白
- Alibaba.com：CDN层面的差异化内容分发，部分节点返回 JS 渲染的 SPA
- 两者都属于阿里巴巴集团，有强大的反爬团队

## 可选方案

| 方案 | 成本 | 可行性 |
|------|------|--------|
| Playwright + Alibaba.com | 低（开发） | 高（浏览器正常渲染SPA） |
| 第三方API (如阿里官方开放平台) | 低 | 中（需企业认证，API有调用限制） |
| 1688 维持登录态 + Playwright | 低 | 中（维护cookie/登录态） |

## 对 Supply Agent 的价值

- 价格区间：计算毛利空间（零售价 vs 批发价）
- MOQ：评估采购门槛
- 供应商信用：年限 + 评分 + 评价数 → 供应商可靠性评分
- 销量趋势：连续采集观察月销量变化 → 市场需求信号

## 建议

与 Amazon 类似 — 必须先解决 Playwright 系统依赖问题，或在云端服务器上运行浏览器。
在本地环境受限的情况下，Alibaba.com HTML 可能间歇可用但不可作为可靠方案。
