import json
import re
from datetime import date, datetime, timezone, timedelta
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

def event_date(e, report_date):
    raw = str(e.get("published_at") or e.get("report_date") or report_date)
    try:
        # All UI daily buckets use Beijing time (UTC+8), regardless of the
        # source timestamp's original timezone.
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(timedelta(hours=8))).date().isoformat()
        datetime.strptime(raw[:10], "%Y-%m-%d")
        return raw[:10]
    except Exception:
        return report_date

def heat(e, report_date):
    try:
        d = datetime.strptime(event_date(e, report_date), "%Y-%m-%d").date()
    except Exception:
        d = date.today()
    age = max(0, (date.today() - d).days)
    freshness = max(20, 100 - 15 * age)
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
    e["published_date"] = event_date(e, report_date)
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

events.sort(key=lambda x: (x.get("published_date", ""), x.get("radar_score", 0)), reverse=True)
for i, e in enumerate(events, 1):
    e["radar_rank"] = i

counts = {}
for e in events:
    counts[e["source_type"]] = counts.get(e["source_type"], 0) + 1
focus_counts = {}
for e in events:
    for k in (e.get("relevance_factors") or {}).get("matched_topics", []):
        focus_counts[k] = focus_counts.get(k, 0) + 1

dates = {}
for e in events:
    dates[e["published_date"]] = dates.get(e["published_date"], 0) + 1

highlights = []
for e in sorted(events, key=lambda x: (x.get("radar_score", 0), x.get("published_date", "")), reverse=True)[:8]:
    highlights.append({"rank": e["radar_rank"], "title": e.get("title", ""), "source_type": e.get("source_type", ""), "source": e.get("primary_source", ""), "published_date": e.get("published_date", ""), "radar_score": e.get("radar_score", 0), "relevance_score": e.get("relevance_score", 0), "heat_score": e.get("heat_score", 0), "link": e.get("link", "")})

# A more useful daily brief: explain what changed today, not just count records.
today_events = [e for e in events if e.get("published_date") == report_date]
today_events.sort(key=lambda x: x.get("radar_score", 0), reverse=True)
today_counts = {}
for e in today_events:
    t = e.get("source_type", "其他")
    today_counts[t] = today_counts.get(t, 0) + 1
summary_parts = [f"{report_date} 收录 {len(today_events)} 条当天发布/更新的电力电子技术事件。"]
if today_events:
    top = today_events[:3]
    summary_parts.append("今日值得先读：" + "；".join(e.get("title", "") for e in top) + "。")
    topic_today = {}
    for e in today_events:
        for k in (e.get("relevance_factors") or {}).get("matched_topics", []): topic_today[k] = topic_today.get(k, 0) + 1
    if topic_today:
        summary_parts.append("今日主题分布以 " + "、".join(k for k, _ in sorted(topic_today.items(), key=lambda x:x[1], reverse=True)[:5]) + " 为主。")
else:
    summary_parts.append("当前 RSS/论文源没有足够的当天条目，因此保留最近条目供回溯，并在页面提供日期筛选。")
summary_parts.append("历史数据按发布时间保留，可按今天、昨天、近7天和全部切换；热度只表示站内新鲜度、多源出现和来源权威度等信号。")

data["events"] = events
data["event_count"] = len(events)
data["daily_summary"] = "".join(summary_parts)
data["daily_highlights"] = highlights
data["daily_focus"] = [{"topic": k, "count": v} for k, v in sorted(focus_counts.items(), key=lambda x: x[1], reverse=True)]
data["daily_stats"] = {"event_count": len(events), "today_count": len(today_events), "today_source_types": today_counts, "source_types": counts, "dates": dates, "scored_events": len(events)}
data["scoring_note"] = "热度为可解释的站内信号分数（发布时间新鲜度、多源出现、来源权威度）；相关度为与预设电力电子技术重点方向及技术信息密度的匹配分数，不代表外部平台热搜排名。"
PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Postprocessed {len(events)} events; date index, daily brief and scores ready.")
