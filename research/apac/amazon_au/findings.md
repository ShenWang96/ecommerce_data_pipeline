# Amazon AU — 调研结论

**状态**: ✅ 可用

## 测试结果

- 搜索页: 48 个商品，19406 字符 HTML
- 提取数据: ASIN, 标题, 价格(AUD), 评分, 评论数
- 无需登录，无 Captcha
- Playwright headless Chromium 可稳定访问

## 数据字段

| 字段 | 示例 |
|------|------|
| ASIN | B0CZRP1KFG |
| 标题 | Xiaomi Sound Outdoor 30 W, Portable Bluetooth Speaker... |
| 价格 | AU$48.16 |
| 评分 | 4.7 out of 5 stars |

## 使用方式

```bash
LD_LIBRARY_PATH="$HOME/.local/playwright-libs:$LD_LIBRARY_PATH" \
  python research/apac/amazon_au/experiment.py
```
