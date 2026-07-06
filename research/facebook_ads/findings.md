# Facebook Ads Library — 数据源调研结论

## 状态：需要官方 API（有免费渠道）

## 测试结果

| 方法 | 结果 | 说明 |
|------|------|------|
| 网页版 Ad Library (无认证) | 403 | Facebook 阻止未认证访问，481字节错误响应 |
| Meta Ad Library API | 未测试 | 需要 Facebook App + Access Token |

## Meta Ad Library API 详情

- **URL**: https://www.facebook.com/ads/library/api/
- **费用**: 免费（有 rate limit）
- **能力**: 
  - 按关键词搜索广告
  - 按 Page ID 搜索广告主的所有广告
  - 获取广告创意、文案、投放时间
  - 按国家/地区过滤
- **限制**:
  - 请求频率限制（具体未公布）
  - 部分数据（花费估算等）仅对政治/社会议题广告开放
  - 需要实名认证的 Facebook 开发者账号
- **申请流程**:
  1. 创建 Facebook App（developers.facebook.com）
  2. 添加 "Ads Library API" 权限
  3. 提交 App Review（需身份验证/手机号）
  4. 获取长期 Access Token

## 竞品广告数据替代源

| 工具 | 类型 | 费用 | 适用场景 |
|------|------|------|---------|
| **Meta Ad Library API** | 官方API | 免费 | Facebook/Instagram 广告分析 |
| **TikTok Ads Library** | 官方 | 免费 | TikTok 广告分析 |
| **Google Ads Transparency** | 官方 | 免费 | Google 广告分析 |
| **BigSpy** | 第三方 | 免费层可用 | 跨平台广告数据库 |
| **AdSpy / PowerAdSpy** | 第三方 | $149/月起 | 专业竞品广告分析 |

## 对 Trend Agent 的价值

- 竞品广告投放频率和强度 → 判断品类热度
- 广告文案和创意 → 了解卖点和营销角度
- 广告投放时长 → 判断产品生命周期阶段
- 多平台广告重叠 → 验证跨平台趋势

## 建议

Meta Ad Library API 是**免费且官方支持**的渠道，最值得优先接入。
需要准备一个 Facebook 开发者账号和 App，建议纳入 Phase 1 前置准备工作。
