import os
import json
import re
import html
import requests
import feedparser
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta

RSS_SOURCES = [
    ("Google News - Power Electronics", "https://news.google.com/rss/search?q=power+electronics"),
    ("Google News - Solid State Transformer", "https://news.google.com/rss/search?q=%22solid-state+transformer%22"),
    ("Google News - SiC Power Electronics", "https://news.google.com/rss/search?q=SiC+power+electronics"),
    ("Google News - GaN Power Electronics", "https://news.google.com/rss/search?q=GaN+power+electronics"),
    ("Google News - Grid Forming", "https://news.google.com/rss/search?q=%22grid-forming%22+power"),
]

KEYWORDS = [
    "sst", "solid-state transformer", "solid state transformer", "sic", "silicon carbide",
    "gan", "gallium nitride", "grid-forming", "grid forming", "gfm", "pcs",
    "800v", "800 v", "ai data center", "ai datacenter", "power electronics",
    "power semiconductor", "wide-bandgap", "high power density", "dual active bridge",
    "dab", "cllc", "llc", "magnetics"
]

TOPICS = {
    "sst": ["sst", "solid-state transformer", "solid state transformer"],
    "sic": ["sic", "silicon carbide"],
    "gan": ["gan", "gallium nitride"],
    "gfm": ["grid-forming", "grid forming", "gfm"],
    "pcs": ["pcs", "power conversion system"],
    "ai_dc": ["ai data center", "ai datacenter", "data center", "datacenter"],
    "dab": ["dab", "dual active bridge"],
    "cllc": ["cllc"], "llc": ["llc"], "800v": ["800v", "800 v", "800-volt"],
    "magnetics": ["magnetics", "magnetic integration", "high-frequency magnetics"]
}

ENTITIES = {
    "enphase": ["enphase", "enphase energy"], "sungrow": ["sungrow"],
    "renesas": ["renesas"], "tmeic": ["tmeic"], "rir": ["rir power"],
    "delta": ["delta electronics"], "infineon": ["infineon"],
    "wolfspeed": ["wolfspeed"], "onsemi": ["onsemi"], "ti": ["texas instruments"]
}

SOURCE_PRIORITY = {
    "nature.com": 100, "ieee": 98, "renesas": 95, "sungrow": 95, "enphase": 95,
    "tmeic": 95, "pv magazine": 90, "pv-magazine": 90, "electronic design": 82,
    "hpcwire": 78, "interesting engineering": 70, "railwaygazette": 65,
    "data center knowledge": 60, "pr newswire": 58, "yahoo finance": 30,
    "24/7 wall st": 25, "finance.biggo": 20, "tradingview": 15
}

MAX_CANDIDATES = 80
MAX_EVENTS = 15


def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title):
    s = clean(title).lower()
    s = re.sub(r"\([^)]*download[^)]*\)", "", s)
    s = re.sub(r"\s*[-|–—:]\s*[^-]{1,50}$", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def score(source):
    s = source.lower()
    return max((v for k, v in SOURCE_PRIORITY.items() if k in s), default=40)


def topics(text):
    t = clean(text).lower()
    return {k for k, vals in TOPICS.items() if any(v in t for v in vals)}


def entities(text):
    t = clean(text).lower()
    return {k for k, vals in ENTITIES.items() if any(v in t for v in vals)}


def resolve_google(url):
    if not url or "news.google.com" not in url:
        return url, ""
    try:
        r = requests.get(url, timeout=8, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 PowerElectronicsRadar/2.0"})
        final = r.url or url
        page = r.text[:500000]
        desc = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']*)', page, re.I)
        if not desc:
            desc = re.findall(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\'](?:og:description|description)["\']', page, re.I)
        return final, clean(desc[0]) if desc else ""
    except Exception:
        return url, ""


def same_event(a, b):
    ta, tb = normalize_title(a["title"]), normalize_title(b["title"])
    if ta == tb or SequenceMatcher(None, ta, tb).ratio() >= 0.86:
        return True
    ea, eb = entities(a["title"]), entities(b["title"])
    common_topics = topics(a["title"] + " " + a.get("summary", "")) & topics(b["title"] + " " + b.get("summary", ""))
    strong = {"sst", "sic", "gan", "gfm", "dab", "cllc", "llc", "800v", "magnetics"}
    if ea & eb and common_topics & strong:
        return True
    wa, wb = set(ta.split()), set(tb.split())
    return len(wa) >= 5 and len(wb) >= 5 and len(wa & wb) / max(1, min(len(wa), len(wb))) >= 0.72


def collect_events():
    candidates, seen = [], set()
    for fallback, url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print("RSS error:", fallback, e)
            continue
        for item in feed.entries[:25]:
            title = clean(item.get("title", ""))
            summary = clean(item.get("summary", ""))
            link = item.get("link", "") or ""
            text = (title + " " + summary).lower()
            if not title or not any(k in text for k in KEYWORDS):
                continue
            key = link.split("#", 1)[0].rstrip("/")
            if key and key in seen:
                continue
            if key: seen.add(key)
            source = item.get("source")
            if isinstance(source, dict): source = source.get("title") or source.get("name")
            source = clean(source or fallback)
            resolved, desc = resolve_google(link)
            if "news.google.com" not in resolved: link = resolved
            if len(desc) > len(summary): summary = desc[:1600]
            candidates.append({"source": source, "title": title, "summary": summary, "link": link, "score": score(source)})
            if len(candidates) >= MAX_CANDIDATES: break
        if len(candidates) >= MAX_CANDIDATES: break

    clusters = []
    for article in sorted(candidates, key=lambda x: x["score"], reverse=True):
        cluster = next((c for c in clusters if same_event(article, c["primary"])), None)
        if cluster:
            cluster["sources"].append({"source": article["source"], "title": article["title"], "link": article["link"]})
            if len(article["summary"]) > len(cluster["primary"].get("summary", "")):
                cluster["primary"]["summary"] = article["summary"]
        else:
            clusters.append({"primary": dict(article), "sources": []})

    events = []
    for i, c in enumerate(clusters[:MAX_EVENTS], 1):
        p = c["primary"]
        events.append({
            "id": f"{datetime.now(timezone.utc).strftime('%y%m%d')}-{i:02d}",
            "title": p["title"], "category": sorted(topics(p["title"] + " " + p["summary"])),
            "primary_source": p["source"], "link": p["link"], "summary_raw": p["summary"],
            "sources": c["sources"][:10]
        })
    return events


def ask_deepseek(events, date):
    key = os.environ["DEEPSEEK_API_KEY"]
    prompt = f'''你是严谨的电力电子技术情报分析员。报告日期：{date}。输入已经按“同一事件”聚类，禁止再次拆分。

目标：把输入事件转换为严格 JSON，不要 Markdown，不要代码围栏，不要额外文字。

事实规则：
- 只使用输入明确支持的信息；没有参数必须写“原文未提供”。
- 全球首个/首次/世界第一只能标为“来源声称”。
- production 不等于量产；target/预计不等于已实现。
- 禁止根据常识补充电压、功率、拓扑、频率、效率、功率密度、器件型号、控制方式。
- 不得因为 bidirectional/high-frequency/modular 推断 DAB/CLLC/MMC 等拓扑。
- 财经新闻只作为技术事件的辅助来源，不作为独立技术事件。
- 标签只能使用：[已证实]、[来源声称]、[模型推断]、[趋势判断]、[信息不足]。
- 产业化阶段只能从：研究论文、实验室样机、工程样机、产品发布、试点/示范、试产、量产、商业部署、未知 中选择。

输出结构：
{{"events":[{{"id":原id,"title":"","category":[""],"importance":"重点|一般","evidence_level":"论文/企业官方/专业媒体/普通媒体/财经媒体/多源交叉/信息不足","summary":"带标签的事实摘要","technical":{{"voltage":"","power":"","topology":"","device":"","switching_frequency":"","efficiency":"","power_density":"","isolation":"","control":"","application":""}},"industrialization":{{"stage":"","status":"","target":""}},"evidence":{{"confirmed_facts":[""],"source_claims":[""],"inferences":[""],"unknowns":[""]}},"sources":[{{"source":"","title":"","link":""}}]}}],"directions":{{"SST":"","SiC_GaN":"","GFM_PCS":"","800V_AI_DC":"","topology_magnetics":""}},"observations":[""],"quality_notes":""}}

输入事件：
{json.dumps(events, ensure_ascii=False)}'''
    r = requests.post("https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model":"deepseek-chat","messages":[
            {"role":"system","content":"只输出合法 JSON。事实准确性优先，不编造参数。"},
            {"role":"user","content":prompt}], "temperature":0.1}, timeout=150)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I).strip()
    return json.loads(text)


def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(timezone.utc).astimezone(tz)
    date = now.strftime("%Y-%m-%d")
    raw_events = collect_events()
    if raw_events:
        try:
            ai = ask_deepseek(raw_events, date)
            by_id = {e.get("id"): e for e in raw_events}
            events = []
            for e in ai.get("events", []):
                base = by_id.get(e.get("id"), {})
                if base:
                    e.setdefault("sources", base.get("sources", []))
                    e.setdefault("link", base.get("link", ""))
                    e.setdefault("primary_source", base.get("primary_source", ""))
                events.append(e)
            if not events: raise ValueError("AI returned no events")
            result = ai
        except Exception as e:
            print("AI structured output failed:", e)
            events = raw_events
            result = {"events": events, "directions": {}, "observations": [], "quality_notes": "AI结构化分析失败，本次保留原始事件数据。"}
    else:
        events, result = [], {"events": [], "directions": {}, "observations": [], "quality_notes": "本次未筛选到事件。"}

    data = {
        "schema_version": "2.0",
        "updated": now.isoformat(),
        "report_date": date,
        "event_count": len(events),
        "events": events,
        "directions": result.get("directions", {}),
        "observations": result.get("observations", []),
        "quality_notes": result.get("quality_notes", ""),
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
