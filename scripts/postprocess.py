import json
import re
from datetime import date, datetime
from pathlib import Path

PATH = Path("data.json")
FOCUS = {
    "SST": ["sst", "solid-state transformer", "固态变压器"],
    "SiC/GaN": ["sic", "silicon carbide", "gan", "gallium nitride", "碳化硅", "氮化镓"],
    "GFM/PCS": ["gfm", "grid-forming", "grid forming", "pcs", "构网型", "储能变流器"],
    "DAB/CLLC/LLC": ["dab", "dual active bridge", "cllc", "llc", "双有源桥"],
    "800V/AI DC": ["800v", "800 v", "800-volt", "ai data center", "ai datacenter", "数据中心电源"],
    "Magnetics": ["magnetics", "magnetic integration", "high-frequency magnetics", "高频磁件", "磁集成"],
}
DOMESTIC_PAPER = ["电力电子技术", "电工技术学报", "电力自动化设备", "电力系统自动化", "中国电机工程学报", "cnki", "知网", "dldzqk", "epae.cn", "aeps-info", "dgjsxb", "cjepe"]
PAPER_HINTS = ["doi.org", "ieeexplore", "ieee", "springer", "sciencedirect", "nature.com", "journal", "论文", "期刊", "transactions"]


def text(e):
    return " ".join(str(e.get(k, "")) for k in ["title", "primary_source", "summary_raw", "plain_summary", "technical_summary", "link"]).lower()


def source_type(e):
    current = e.get("source_type")
    if current in {"国内资讯", "国内论文", "国际资讯", "国际论文"}:
        if current == "国际资讯" and any(x in text(e) for x in PAPER_HINTS):
            return "国际论文"
        return current
    t = text(e)
    if any(x.lower() in t for x in DOMESTIC_PAPER):
        return "国内论文"
    if any(x in t for x in PAPER_HINTS):
        return "国际论文"
    if re.search(r"[\u4e00-\u9fff]", e.get("title", "")):
        return "国内资讯"
    return "国际资讯"


def relevance(e):
    t = text(e)
    matched = {name for name, keys in FOCUS.items() if any(k in t for k in keys)}
    core = min(100, 35 + 13 * len(matched))
    density = min(100, 35 + 8 * sum(1 for k in ["voltage", "power", "topology", "device", "switching_frequency", "efficiency", "power_density", "control"] if (e.get("technical") or {}).get(k)))
    engineering = 80 if e.get("technical_summary") else 50
    score = round(0.55 * core + 0.25 * density + 0.20 * engineering)
    return score, {"focus_match": round(core, 1), "technical_density": round(density, 1), "engineering_usability": engineering, "matched_topics": sorted(matched)}


def heat(e, report_date):
    try:
        d = datetime.strptime(str(e.get("report_date") or report_date)[:10], "%Y-%m-%d").date()
    except Exception:
        d = date.today()
    age = max(0, (date.today() - d).days)
    freshness = max(35, 100 - 12 * age)
    nsrc = max(1, len(e.get("sources") or []))
    multi = min(100, 45 + 18 * min(3, nsrc - 1))
    source = str(e.get("primary_source", "")).lower()
    authority = 92 if any(x in source for x in ["ieee", "电工技术学报", "电力电子技术", "电力自动化设备", "电力系统自动化", "中国电机工程学报"]) else 75 if any(x in source for x in ["infineon", "ti", "renesas", "sungrow", "huawei", "阳光电源", "华为"]) else 58
    score = round(0.45 * freshness + 0.25 * multi + 0.30 * authority)
    return score, {"freshness": round(freshness, 1), "multi_source": round(multi, 1), "source_authority": authority}


data = json.loads(PATH.read_text(encoding="utf-8"))
report_date = str(data.get("report_date") or date.today())[:10]
events = data.get("events") or []

for e in events:
    e["source_type"] = source_type(e)
    r, rf = relevance(e)
    h, hf = heat(e, report_date)
    tech = e.get("technical") or {}
    depth = min(100, 35 + 9 * sum(bool(v and str(v) not in {"原文未提供", "未知"}) for v in tech.values()))
    authority = hf["source_authority"]
    radar = round(0.50 * r + 0.25 * h + 0.15 * depth + 0.10 * authority)
    e["relevance_score"] = r
    e["relevance_factors"] = rf
    e["heat_score"] = h
    e["heat_factors"] = hf
    e["technical_depth_score"] = depth
    e["radar_score"] = radar

# Rank without pretending that the score is an external popularity metric.
events.sort(key=lambda x: (x.get("radar_score", 0), x.get("relevance_score", 0)), reverse=True)
for i, e in enumerate(events, 1):
    e["radar_rank"] = i

counts = {}
for e in events:
    counts[e["source_type"]] = counts.get(e["source_type"], 0) + 1
focus_counts = {}
for e in events:
    for k in (e.get("relevance_factors") or {}).get("matched_topics", []):
        focus_counts[k] = focus_counts.get(k, 0) + 1

highlights = []
for e in events[:5]:
    highlights.append({
        "rank": e["radar_rank"],
        "title": e.get("title", ""),
        "source_type": e.get("source_type", ""),
        "source": e.get("primary_source", ""),
        "radar_score": e.get("radar_score", 0),
        "relevance_score": e.get("relevance_score", 0),
        "heat_score": e.get("heat_score", 0),
        "link": e.get("link", ""),
    })

summary_parts = [f"今日收录 {len(events)} 条技术事件。"]
if counts:
    summary_parts.append("来源结构：" + "、".join(f"{k} {v} 条" for k, v in sorted(counts.items())) + "。")
if focus_counts:
    top_focus = sorted(focus_counts.items(), key=lambda x: x[1], reverse=True)[:4]
    summary_parts.append("今日关注度最高的技术方向按收录量计为：" + "、".join(f"{k}（{v}）" for k, v in top_focus) + "。")

data["events"] = events
data["event_count"] = len(events)
data["daily_summary"] = "".join(summary_parts)
data["daily_highlights"] = highlights
data["daily_focus"] = [{"topic": k, "count": v} for k, v in sorted(focus_counts.items(), key=lambda x: x[1], reverse=True)]
data["daily_stats"] = {"event_count": len(events), "source_types": counts, "scored_events": len(events)}
data["scoring_note"] = "热度为可解释的站内信号分数（新鲜度、多源出现、来源权威度）；相关度为与预设电力电子技术重点方向及技术信息密度的匹配分数，不代表外部平台热搜排名。"

PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Postprocessed {len(events)} events; daily brief and scores ready.")
