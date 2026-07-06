# TikTok — 数据源调研结论

## 状态：需要浏览器+账号（纯 HTTP 不可行）

## 测试结果

| 方法 | 结果 | 说明 |
|------|------|------|
| httpx 搜索页 | 200 但无数据 | 350KB HTML 是 SPA 空壳，`__UNIVERSAL_DATA_FOR_REHYDRATION__` 仅含AB配置，无视频/话题内容 |
| httpx trending 页 | 200 但含 captcha | 361KB，检测到验证码 |
| httpx hashtag 页 | 200 但无数据 | 355KB，同样是 SPA 空壳 |
| TikTokApi 库 | 未安装 | 需 Playwright 获取 ms_token |

## 反爬机制

- TikTok 是纯 SPA，所有内容通过 XHR/fetch 动态加载
- 页面有 captcha 检测
- API 调用需要设备指纹（ms_token）签名

## 对 Trend Agent 的价值

- 热门视频/话题标签 → 新兴产品趋势信号
- 视频互动量（点赞/分享/评论）→ 话题热度指示器
- 带货视频 → 直接发现热卖产品

## 可选方案

| 方案 | 成本 | 可行性 |
|------|------|------|
| TikTokApi + Playwright | 低（开发） | 中（依赖 ms_token，可能频繁失效） |
| TikTok 官方 API (TikTok for Developers) | 低（免费） | 低（权限审批严格，功能有限） |
| RapidAPI 第三方 TikTok API | 中（$30-100/月） | 中（封装好的接口） |
| TikTok Ads Library | 低（免费） | 中（只显示广告数据，非全量内容） |

## 建议

作为趋势发现的重要来源，TikTok 不可或缺。
建议优先评估 TikTok Ads Library（广告库）和 BigSpy 等工具作为替代方案，
或者直接在云端服务器上运行 Playwright + TikTokApi。
