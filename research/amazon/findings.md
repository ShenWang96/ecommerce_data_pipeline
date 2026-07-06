# Amazon — 数据源调研结论

## 状态：需要浏览器自动化（当前环境受限）

## 测试结果

| 方法 | 结果 | 说明 |
|------|------|------|
| httpx (纯 HTTP) | 被拦截 | 返回 JS 验证页面（`bm-verify` 机制），状态码200但内容是空壳 |
| httpx + Referer 头 | 被拦截 | 同上，加 Referer 无改善 |
| Playwright Chromium | 未完成 | 需要系统库 libnspr4/libnss3/libasound2，WSL 环境缺 sudo 权限 |
| Playwright Firefox | 未完成 | 同样需要系统依赖 |

## 反爬机制

- Amazon 使用 `bm-verify` (Bot Management) + JS 验证
- 无 JS 引擎的请求直接返回空壳页面
- 检测粒度：User-Agent + 浏览器指纹 + IP 信誉

## 可选方案

| 方案 | 成本 | 可行性 |
|------|------|--------|
| Playwright/Chromium（解决系统依赖后） | 低（开发成本） | 中等（需 root 装系统库） |
| Amazon Product Advertising API | 低（免费，但需 affiliate 账户） | 高（官方支持，数据有限） |
| 第三方 API (Rainforest/ScrapingBee) | 中（月费 ~$50-200） | 高（稳定，但按请求计费） |
| 在云端服务器上运行 Playwright | 低 | 高（服务器已有浏览器环境） |

## 对 Competition Agent 的价值

- 搜索排名/BSR：评估竞品市场地位
- 价格区间：了解市场价格带
- 评论数+评分：用户反馈量级和质量
- 商品详情页：产品规格、差异化卖点

## 建议

1. 短期：先搞定系统依赖让 Playwright 能在本地跑起来，或直接改用云端服务器测试
2. 中期：评估第三方 API 成本 vs 自行维护爬虫的维护成本
3. 长期：考虑 Anti-detect browser (如 undetected_chromedriver) 提高稳定性
