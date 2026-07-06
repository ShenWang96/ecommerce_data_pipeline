#!/usr/bin/env python3
"""从 Pipeline 输出的 JSONL 生成可视化 HTML 报告."""
import json, sys
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

LAYER_COLORS = {
    1: "#ef4444", 2: "#f59e0b", 3: "#3b82f6",
    4: "#8b5cf6", 5: "#10b981", 6: "#6b7280",
}
LAYER_NAMES = {
    1: "需求萌芽 (Pain & Needs)",
    2: "理念形成 (Lifestyle & Concept)",
    3: "内容传播 (Content Amplification)",
    4: "大众关注 (Attention)",
    5: "商业验证 (Commercial)",
    6: "供应扩张 (Supply)",
}
LAYER_EMOJI = {1: "🌱", 2: "💡", 3: "📣", 4: "🔍", 5: "💰", 6: "🏭"}
SIGNAL_TYPE_LABELS = {
    "pain_point": "问题描述", "seeking_help": "求推荐/替代",
    "complaint": "吐槽/后悔", "lifestyle": "新生活方式",
    "concept": "新兴概念", "trending": "上热榜/热搜",
    "viral": "爆款内容",
}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC",sans-serif;background:#f8fafc;color:#1e293b;padding:0}
.header{background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;padding:40px 32px}
.header h1{font-size:28px;margin-bottom:8px}
.header p{color:#94a3b8;font-size:14px}
.stats{display:flex;gap:16px;margin-top:24px;flex-wrap:wrap}
.stat{background:rgba(255,255,255,.08);border-radius:12px;padding:16px 24px;min-width:120px}
.stat .num{font-size:28px;font-weight:800}
.stat .label{color:#94a3b8;font-size:12px;margin-top:4px}
.container{max-width:1200px;margin:0 auto;padding:24px}
.card{background:#fff;border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:24px;overflow:hidden}
.card-header{display:flex;align-items:center;gap:10px;padding:20px 24px;border-bottom:1px solid #f1f5f9}
.card-header .badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;color:#fff}
.card-header h2{font-size:18px}
.card-body{padding:24px}
.bar-wrap{display:flex;align-items:center;gap:12px;margin:8px 0}
.bar-wrap .label{width:200px;text-align:right;font-size:13px;color:#64748b;flex-shrink:0}
.bar-wrap .bar{flex:1;height:24px;border-radius:6px;position:relative;min-width:4px;transition:width .3s}
.bar-wrap .bar span{position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:11px;color:#fff;font-weight:700;text-shadow:0 1px 2px rgba(0,0,0,.3)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;border-bottom:2px solid #e2e8f0;font-size:11px;text-transform:uppercase;color:#64748b;font-weight:600}
td{padding:10px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top}
tr:hover td{background:#f8fafc}
.layer-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.source-tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap}
.src-bilibili{background:#fde9f1;color:#d9467b}.src-zhihu{background:#e0f2fe;color:#0c8ce9}
.src-weibo{background:#fef3c7;color:#d97706}.src-xiaohongshu{background:#fce7f3;color:#db2777}
.type-tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;white-space:nowrap;margin:2px 2px}
.t-pain_point{background:#fee2e2;color:#dc2626}.t-seeking_help{background:#fef3c7;color:#d97706}
.t-complaint{background:#fae8ff;color:#a21caf}.t-lifestyle{background:#d1fae5;color:#059669}
.t-concept{background:#e0e7ff;color:#4f46e5}.t-trending{background:#dbeafe;color:#2563eb}
.domain-tag{font-size:11px;color:#64748b}
.eng-num{font-weight:700;color:#0f172a;white-space:nowrap}
.footer{text-align:center;color:#94a3b8;padding:32px;font-size:12px}
a{color:#3b82f6;text-decoration:none}a:hover{text-decoration:underline}
"""


def build_report(signals: list[dict]) -> str:
    sources = Counter(s["source"] for s in signals)
    layers = Counter(s["layer"] for s in signals)
    stypes = Counter(s["signal_type"] for s in signals)
    domains = Counter(s["domain"] for s in signals if s["domain"] != "其他")

    # Layer groups sorted by engagement
    by_layer = defaultdict(list)
    for s in signals:
        by_layer[s["layer"]].append(s)
    for l in by_layer:
        by_layer[l].sort(key=lambda x: x["engagement"], reverse=True)

    # Top 10 per layer for display
    top_per_layer = {l: ss[:10] for l, ss in by_layer.items()}

    total_engagement = sum(s["engagement"] for s in signals)
    max_eng = max((s["engagement"] for s in signals if s["engagement"] > 0), default=1)

    def bar(width_percent, label, count):
        w = max(width_percent, 1)
        return f'<div class="bar-wrap"><div class="label">{label}</div><div class="bar" style="width:{w}%;background:{LAYER_COLORS.get(l,"#666")}"><span>{count}</span></div></div>'

    parts = []
    parts.append("<!DOCTYPE html><html lang=zh><head><meta charset=utf-8>")
    parts.append("<meta name=viewport content='width=device-width,initial-scale=1'>")
    parts.append("<title>中国大陆电商趋势信号报告</title>")
    parts.append(f"<style>{CSS}</style></head><body>")

    # Header
    ts = signals[0].get("scraped_at", "?")[:19] if signals else "?"
    parts.append(f"""<div class=header>
<h1>中国大陆电商趋势信号报告</h1>
<p>数据采集时间: {ts} &nbsp;|&nbsp; 数据源: B站 · 知乎 · 微博 · 小红书</p>
<div class=stats>
  <div class=stat><div class=num>{len(signals)}</div><div class=label>总信号量</div></div>
  <div class=stat><div class=num>{total_engagement:,}</div><div class=label>总互动量</div></div>
  <div class=stat><div class=num>{len(sources)}</div><div class=label>数据源</div></div>
  <div class=stat><div class=num>{len(domains)}</div><div class=label>消费领域</div></div>
</div></div>""")

    parts.append('<div class=container>')

    # ── Layer Distribution ──
    parts.append('<div class=card><div class=card-header><h2>信号链分层分布</h2></div><div class=card-body>')
    total_sig = len(signals) or 1
    for l in sorted(LAYER_NAMES):
        cnt = layers.get(l, 0)
        pct = cnt / total_sig * 100
        emoji = LAYER_EMOJI.get(l, "")
        parts.append(bar(pct, f"{emoji} Layer {l}: {LAYER_NAMES.get(l,'?')}", cnt))
    parts.append('</div></div>')

    # ── Source Breakdown ──
    parts.append('<div class=card><div class=card-header><h2>数据源分布</h2></div><div class=card-body>')
    for src, cnt in sources.most_common():
        pct = cnt / total_sig * 100
        colors = {"bilibili":"#d9467b","zhihu":"#0c8ce9","weibo":"#d97706","xiaohongshu":"#db2777"}
        parts.append(bar(pct, src, cnt))
        # Break down by layer
        src_layers = Counter(s["layer"] for s in signals if s["source"] == src)
        parts.append('<div style=margin-left:220px;margin-bottom:8px;font-size:11px;color:#94a3b8>')
        for l in sorted(src_layers):
            parts.append(f'L{l}:{src_layers[l]} &nbsp;')
        parts.append('</div>')
    parts.append('</div></div>')

    # ── Domain Top 15 ──
    parts.append('<div class=card><div class=card-header><h2>消费领域 TOP 15</h2></div><div class=card-body>')
    domain_total = sum(domains.values()) or 1
    for domain, cnt in domains.most_common(15):
        pct = cnt / domain_total * 100
        parts.append(bar(pct, domain, cnt))
    parts.append('</div></div>')

    # ── Signal Type Distribution ──
    parts.append('<div class=card><div class=card-header><h2>信号类型分布</h2></div><div class=card-body>')
    type_total = sum(stypes.values()) or 1
    for st, cnt in stypes.most_common():
        label = SIGNAL_TYPE_LABELS.get(st, st)
        pct = cnt / type_total * 100
        parts.append(bar(pct, f"{st} ({label})", cnt))
    parts.append('</div></div>')

    # ── Per Layer Detail ──
    for l in sorted(top_per_layer):
        ss = top_per_layer[l]
        color = LAYER_COLORS.get(l, "#666")
        emoji = LAYER_EMOJI.get(l, "")
        total_in_layer = layers.get(l, 0)
        avg_eng = int(sum(s["engagement"] for s in by_layer[l]) / max(len(by_layer[l]), 1))
        parts.append(f'<div class=card>')
        parts.append(f'<div class=card-header><span class=badge style=background:{color}>{emoji} Layer {l}</span>')
        parts.append(f'<h2>{LAYER_NAMES.get(l,"?")}</h2>')
        parts.append(f'<span style=margin-left:auto;color:#94a3b8;font-size:13px>{total_in_layer} 条信号 | 均互动 {avg_eng:,}</span>')
        parts.append(f'</div><div class=card-body>')
        parts.append('<table>')
        parts.append('<tr><th>#</th><th>源</th><th>类型</th><th>标题</th><th>领域</th><th style=text-align:right>互动量</th></tr>')
        for i, s in enumerate(ss, 1):
            src = s["source"]
            st = s["signal_type"]
            src_cls = f"src-{src}" if src in ("bilibili","zhihu","weibo","xiaohongshu") else ""
            st_cls = f"t-{st}" if st in SIGNAL_TYPE_LABELS else ""
            st_label = SIGNAL_TYPE_LABELS.get(st, st)
            domain = s.get("domain", "")
            title = s.get("title", "")[:80]
            url = s.get("url", "")
            eng = s.get("engagement", 0)
            parts.append(f'<tr>')
            parts.append(f'<td style=color:#94a3b8>{i}</td>')
            parts.append(f'<td><span class="source-tag {src_cls}">{src}</span></td>')
            parts.append(f'<td><span class="type-tag {st_cls}">{st_label}</span></td>')
            parts.append(f'<td><a href="{url}" target=_blank title="{s.get("title","")}">{title}</a></td>')
            parts.append(f'<td><span class=domain-tag>{domain if domain != "其他" else ""}</span></td>')
            parts.append(f'<td style=text-align:right class=eng-num>{eng:,}</td>')
            parts.append(f'</tr>')
        parts.append('</table></div></div>')

    # ── Key Insights ──
    parts.append('<div class=card>')
    parts.append('<div class=card-header><h2>关键洞察</h2></div><div class=card-body>')
    insights = []

    # Top pain point
    pains = [s for s in signals if s["signal_type"] in ("pain_point","seeking_help","complaint")]
    if pains:
        top_pain = sorted(pains, key=lambda x: x["engagement"], reverse=True)[0]
        insights.append(f'<li>🔴 <b>最强需求信号:</b> 知乎问题 <a href="{top_pain["url"]}">「{top_pain["title"][:60]}」</a> 获得 {top_pain["engagement"]:,} 互动</li>')

    # Top trending
    trending = [s for s in signals if s["signal_type"] == "trending"]
    if trending:
        top_tr = sorted(trending, key=lambda x: x["engagement"], reverse=True)[:3]
        titles = "、".join(f'「{s["title"][:30]}」' for s in top_tr)
        insights.append(f'<li>📣 <b>最热内容:</b> {titles} 全网热度最高</li>')

    # Top domains
    for domain, cnt in domains.most_common(3):
        insights.append(f'<li>📊 <b>热门领域 {domain}:</b> {cnt} 条信号，涵盖 {len([s for s in signals if s["domain"]==domain])} 条内容</li>')

    # Source coverage
    for src in ["weibo", "xiaohongshu", "bilibili", "zhihu"]:
        cnt = sources.get(src, 0)
        status = "✅" if cnt > 0 else "❌"
        insights.append(f'<li>{status} <b>{src}:</b> {cnt} 条信号{" (Cookie就绪)" if cnt > 0 else " (未配置)"}</li>')

    parts.append(f'<ul style=line-height:2.2;padding-left:20px>{"".join(insights)}</ul>')
    parts.append('</div></div>')

    parts.append('</div>')  # container

    parts.append(f'<div class=footer>China Ecommerce Trend Signal Pipeline · 信号链: 需求萌芽→理念形成→内容传播→大众关注→商业验证→供应扩张 · {ts}</div>')
    parts.append('</body></html>')

    return "\n".join(parts)


if __name__ == "__main__":
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not jsonl_path:
        # find latest
        data_dir = Path(__file__).parent.parent / "data"
        files = sorted(data_dir.glob("signals_*.jsonl"), reverse=True)
        jsonl_path = files[0] if files else None
    if not jsonl_path:
        print("No signal file found", file=sys.stderr); sys.exit(1)

    signals = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                signals.append(json.loads(line))

    html = build_report(signals)
    out = Path(jsonl_path).with_suffix('.html')
    out.write_text(html)
    print(f"Report: {out} ({len(signals)} signals)")
