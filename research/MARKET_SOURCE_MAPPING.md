# 商品市场 → 信息源 映射

> 目标：梳理每个目标区域市场的可选数据源，为后续深耕选型提供决策依据
> 更新时间：2026-07-04

---

## 一、市场与数据源总览矩阵

| 市场 Region | Amazon | 本土电商 | 批发/供应链 | 趋势 | 评论 |
|------------|--------|---------|------------|------|------|
| 🌏 全球 | US/JP/AU/SG/IN | — | Alibaba ⚠️ | Google Trends ✅ | Trustpilot ✅ |
| 🇯🇵 日本 | ✅ amazon.co.jp | ✅ Rakuten | — | Google Trends JP ✅ | — |
| 🇦🇺 澳洲 | ✅ amazon.com.au | ❌ eBay/Catch/Kogan | — | Google Trends AU ✅ | — |
| 🇸🇬 东南亚 | ✅ amazon.sg | ❌ Shopee/Lazada | — | Google Trends ✅ | — |
| 🇮🇳 印度 | ✅ amazon.in | ❓ Flipkart | — | Google Trends ✅ | — |
| 🇨🇳 中国 | — | ❌ Taobao/JD/1688 | ❌ 1688 | — | — |
| 🇺🇸 美国 | ✅ amazon.com | — | — | Google Trends ✅ | Trustpilot ✅ |

## 二、逐市场详析

### 🇯🇵 日本 — **深耕首选** ⭐⭐⭐

| 数据源 | 状态 | 每页商品 | 提取字段 | 备注 |
|--------|------|---------|---------|------|
| **Amazon JP** | ✅ | 48 | ASIN, 日文标题, JPY价格, 评分 | 与 US 同一套 selector，代码复用 |
| **Rakuten JP** | ✅ | 45 (65k+件) | 日文标题, JPY价格, 评分+评论数, 商 | 日本最大本土平台；数据颗粒度更细 |
| Yahoo 购物 | ❓ | — | — | 未测试 |
| Mercari | ❓ | — | — | C2C 二手，选品参考价值有限 |

**选择理由**：
- 两个高质量数据源都可用，数据互补（Amazon = 国际化品牌，Rakuten = 本土品牌）
- 同一套 Playwright 基础设施，零额外成本
- 日本是全球第三大电商市场，选品出口价值高
- 两个源代码已实现（`AmazonCollector(market='jp')` + `RakutenCollector`）

---

### 🇦🇺 澳洲 — **可行** ⭐⭐

| 数据源 | 状态 | 每页商品 | 提取字段 | 备注 |
|--------|------|---------|---------|------|
| **Amazon AU** | ✅ | 48 | ASIN, 标题, AUD价格, 评分 | 代码已有 |
| eBay AU | ❌ 403 | — | — | TLS fingerprinting 拦截 |
| Catch | ❌ 403 | — | — | 反爬严格 |
| Kogan | ❌ SPA | — | — | JS 渲染后无内容 |

**选择理由**：
- 仅 Amazon AU 可用，但已足够覆盖澳洲主流电商 SKU
- 澳洲市场体量较小但利润率高
- eBay 可考虑通过官方 API 接入（免费注册）

---

### 🇸🇬 东南亚 — **受限** ⭐

| 数据源 | 状态 | 每页商品 | 备注 |
|--------|------|---------|------|
| **Amazon SG** | ✅ | 48 | SG 市场有限，但可抓到部分 SEA 商品 |
| Shopee (6国) | ❌ | — | API 签名验证 error 90399 |
| Lazada (5国) | ❌ | — | Akamai CDN 级别 Captcha |
| Tokopedia | ❌ | — | HTTP2 协议拦截 |
| Zalora | ⚠️ | — | 31 个元素但内容量少 |

**选择理由**：
- 东南亚本土平台反爬最为严格（Shopee/Lazada 都是阿里系/Akamai）
- Amazon SG 是唯一可用入口，但覆盖范围有限
- **要深耕 SEA 需投入 Shopee/Lazada API 申请 或 付费第三方**

---

### 🇮🇳 印度 — **可行** ⭐⭐

| 数据源 | 状态 | 每页商品 | 备注 |
|--------|------|---------|------|
| **Amazon IN** | ✅ | 16 | 商品数少于其他站点 |
| Flipkart | ❓ | — | 需测试 |
| Snapdeal | ❓ | — | 需测试 |

**选择理由**：
- Amazon IN 可用但商品数较少（16 vs 48）
- 印度是快速增长市场，但选品出口以 IT/纺织品为主

---

### 🇨🇳 中国 — **不可用** ❌

| 数据源 | 状态 | 原因 |
|--------|------|------|
| Taobao/Tmall | ❌ | 强制登录 + mtop 签名 |
| JD.com | ❌ | 跳转登录页 |
| 1688.com | ❌ | 登录墙 + Captcha |
| Xiaohongshu | ❌ | SPA JS 渲染但数据不可见 |
| Pinduoduo | ❓ | 未测试（大概率同样拦截） |

**选择理由**：
- 中国平台反爬是最高级别的，短时间无法攻克
- 替代方案：Amazon US/JP 上的中国品牌卖家数据 + AliExpress（待测试）
- 长期方案：找中国卖家 API 供应商 或 使用住宅代理

---

### 🌏 全球/跨市场

| 数据源 | 状态 | 覆盖 | 备注 |
|--------|------|------|------|
| **Google Trends** | ✅ | 全球/按国家筛选 | pytrends，趋势+关联查询+地区分布 |
| **Trustpilot** | ✅ | 全球 | Playwright 可获取评论全文 |
| Alibaba.com | ⚠️ | 全球 B2B | httpx 部分可用，Playwright 被 Captcha |
| TikTok | ❌ | 全球 | Captcha + 需 ms_token |
| Facebook Ads | ❌ | 全球 | 需开发者账号审批 |

---

## 三、按 Agent 需求 → 数据源推荐

| Agent | 需求 | 首选源 | 备选 |
|-------|------|--------|------|
| **Competition** (竞品分析) | 价格、排名、评分、评论数 | Amazon (5站点) + Rakuten JP | Alibaba (待解决) |
| **Trend** (趋势发现) | 搜索热度、上升品类 | Google Trends | TikTok (待解决) |
| **Demand** (需求验证) | 用户痛点、评论区信号 | Trustpilot | Amazon 评论 (详情页待开发) |
| **Supply** (供应链) | 批发价、MOQ、供应商 | Alibaba.com ⚠️ | Amazon BSR 替代信号 |

---

## 四、深耕优先级建议

```
第1优先级 (立即投入) ─────────────────────
  Amazon US + JP + AU + SG + IN   ← 5站复用同一套 Collector
  Rakuten JP                      ← 日本本土差异化数据
  Google Trends                   ← 趋势信号，跨市场通用

第2优先级 (短期) ─────────────────────────
  Trustpilot                      ← 评论数据，验证需求
  Amazon 详情页 + BSR             ← 补充商品详情数据
  1688/Alibaba API 方案           ← Supply Agent 关键

第3优先级 (中期) ─────────────────────────
  Shopee/Lazada API 申请          ← 覆盖东南亚本土
  Facebook Ads Library API        ← 广告趋势信号
  eBay Developer API              ← 澳洲替代源

第4优先级 (长期/探索) ────────────────────
  TikTok API (ms_token)           ← 社媒趋势
  Taobao/Tmall (代理方案)          ← 中国市场
  Flipkart (印度)                  ← 印度本土补充
```

## 五、投入产出评估

| 投入方向 | 开发成本 | 数据质量 | 覆盖市场 | ROI |
|---------|---------|---------|---------|-----|
| Amazon Collector (5站) | 低 (已完成80%) | ⭐⭐⭐⭐ | US+JP+AU+SG+IN | 🔥🔥🔥🔥🔥 |
| Rakuten Collector | 低 (已完成) | ⭐⭐⭐⭐ | JP | 🔥🔥🔥🔥 |
| Google Trends | 低 (已完成) | ⭐⭐⭐ | 全球 | 🔥🔥🔥🔥 |
| Trustpilot | 低 (验证完成) | ⭐⭐⭐ | 全球 | 🔥🔥🔥 |
| 1688 API/代理 | 高 | ⭐⭐ | CN | 🔥🔥 |
| Shopee/Lazada API | 中 (需申请) | ⭐⭐⭐⭐ | SEA (6/5国) | 🔥🔥🔥🔥 |
| TikTok | 高 | ⭐⭐⭐ | 全球 | 🔥🔥 |
