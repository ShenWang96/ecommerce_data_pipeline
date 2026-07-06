# Reviews 聚合 — 数据源调研结论

## 状态：需要浏览器或第三方 API（纯 HTTP 不可行）

## 测试结果

| 平台 | 方法 | 结果 |
|------|------|------|
| **Amazon Reviews** | httpx 产品评论页 | 128KB 但全为空壳（`a-no-js` 页面），无评论内容 |
| **Trustpilot** | httpx 商家评论页 | 403 Forbidden — 已封禁 |
| **Google Shopping** | httpx | 重度 JS 依赖，纯 HTTP 不可行 |

## 评论数据获取方案

| 方案 | 覆盖平台 | 费用 | 数据质量 |
|------|---------|------|---------|
| **Amazon Product Advertising API** | Amazon | 免费（需Affiliate） | 仅有评分摘要（星级+数量），无评论全文 |
| **Rainforest API** | Amazon | $49/mo起 | 完整评论全文+评分+图片 |
| **Trustpilot API** | Trustpilot（第三方商家评分） | 免费层可用 | 用户评论+商家回复 |
| **Playwright 自爬** | 多平台 | 低（开发成本） | 可控，但维护高 |
| **ReviewMeta API** | Amazon | 免费 | 评论真实性分析，非原始数据 |

## 对 Demand Agent 的价值

- 用户评论中的**痛点描述** → 发现未被满足的需求
- 评论中的**使用场景** → 验证产品定位
- 评分分布 → 产品质量口碑
- 高频关键词 → 用户关注的维度（音质、续航、做工等）

## 建议

1. **最优先**：Amazon Product Advertising API — 免费、官方、稳定，虽无评论文本但评分+评论数量信号已很有价值
2. **中期**：Trustpilot API + Playwright 自爬 Amazon 评论
3. **长期**：如果数据量需求大，评估 Rainforest API 成本效益
