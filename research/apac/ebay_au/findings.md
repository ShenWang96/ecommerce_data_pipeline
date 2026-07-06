# eBay AU — 调研结论

**状态**: ❌ 不可用（HTTP 403）

## 测试结果

- httpx: HTTP 403
- Playwright: eBay 返回错误页 "SORRY - Something went wrong on our end"

## 原因

eBay 的反爬策略已升级到 TLS fingerprinting 级别，Playwright 的 Chromium 被识别为自动化工具。

## 可能方案

1. **eBay Developer API** — 官方 API（免费，需注册开发者账号）
2. **替代** → Amazon AU 已可用，覆盖澳洲市场
