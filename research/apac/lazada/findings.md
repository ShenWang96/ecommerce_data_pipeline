# Lazada — 调研结论

**状态**: ❌ 不可用

## 测试结果

| 市场 | 网址 | 结果 |
|------|------|------|
| Singapore | lazada.sg | Captcha 拦截 (仅返回 ~1.7KB) |
| Indonesia | lazada.co.id | 同上 |
| Malaysia | lazada.com.my | 同上 |
| Philippines | lazada.com.ph | 同上 |
| Thailand | lazada.co.th | 同上 |

## 原因

- Lazada 使用 Akamai/CDN 级别的反爬，HTTP 请求直接返回 JS Challenge 页面
- Playwright 同样触发 Captcha（页面标题 "Captcha Interception"）
- 与母公司 Alibaba 的技术栈一致，反爬策略也类似

## 可能方案

1. **Lazada Open Platform** — 官方卖家 API（需要 Lazada 卖家账号）
2. **代理 IP + 更强的反检测** — 住宅代理 + playwright-stealth
3. **移动端 API** — 但同样需要签名算法
