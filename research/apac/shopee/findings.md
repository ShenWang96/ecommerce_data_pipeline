# Shopee — 调研结论

**状态**: ❌ 不可用

## 测试结果

| 市场 | 网址 | 结果 |
|------|------|------|
| Singapore | shopee.sg | 首页可加载，搜索 API 返回 error 90309999 |
| Indonesia | shopee.co.id | 同上 |
| Malaysia | shopee.com.my | 同上 |
| Philippines | shopee.ph | 同上 |
| Thailand | shopee.co.th | 同上 |
| Vietnam | shopee.vn | 同上 |

## 原因

- 搜索页面为 SPA，httpx 返回空壳
- Playwright 可渲染首页，但搜索 API (`/api/v4/search/search_items`) 需要特殊的 CSRF token + cookie 签名验证
- 即使获取了首页 cookies (104个)，API 仍然返回 90309999 错误

## 可能方案

1. **Shopee Open Platform API** — 官方卖家 API，需要 Shopee 卖家账号
2. **第三方数据服务** — SimilarWeb、Jungle Scout 等有 Shopee 数据
3. **移动端抓包** — 逆向 App 的 API 签名（维护成本高）
