import os
import json
import re
import html
import requests
import feedparser
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from source_fetcher import fetch_source, crossref_papers
try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None

RSS_SOURCES = [
    ("国际资讯 - Power Electronics", "https://news.google.com/rss/search?q=power+electronics&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - SST", "https://news.google.com/rss/search?q=%22solid-state+transformer%22&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - SiC", "https://news.google.com/rss/search?q=SiC+power+electronics&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - GaN", "https://news.google.com/rss/search?q=GaN+power+electronics&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - GFM PCS", "https://news.google.com/rss/search?q=%22grid-forming%22+PCS+power&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - 800V AI DC", "https://news.google.com/rss/search?q=800V+AI+data+center+power&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国际资讯 - DAB CLLC LLC", "https://news.google.com/rss/search?q=DAB+CLLC+LLC+power+electronics&hl=en-US&gl=US&ceid=US:en", "国际资讯"),
    ("国内资讯 - 中国电力电子", "https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "国内资讯"),
    ("国内资讯 - 构网型变流器", "https://news.google.com/rss/search?q=%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+GFM+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "国内资讯"),
    ("国内资讯 - SiC GaN", "https://news.google.com/rss/search?q=SiC+GaN+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E5%8A%9F%E7%8E%87%E5%8D%8A%E5%AF%BC%E4%BD%93&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "国内资讯"),
    ("国内资讯 - 800V 数据中心", "https://news.google.com/rss/search?q=800V+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "国内资讯"),
]
KEYWORDS = ["sst", "solid-state transformer", "solid state transformer", "sic", "silicon carbide", "gan", "gallium nitride", "grid-forming", "grid forming", "gfm", "pcs", "800v", "800 v", "ai data center", "ai datacenter", "power electronics", "power semiconductor", "wide-bandgap", "dual active bridge", "dab", "cllc", "llc", "magnetics", "构网型", "变流器", "电力电子", "碳化硅", "氮化镓"]
TOPICS = {"sst": ["sst", "solid-state transformer", "solid state transformer"], "sic": ["sic", "silicon carbide", "碳化硅"], "gan": ["gan", "gallium nitride", "氮化镓"], "gfm": ["grid-forming", "grid forming", "gfm", "构网型"], "pcs": ["pcs", "power conversion system", "变流器", "储能变流器"], "ai_dc": ["ai data center", "ai datacenter", "data center", "datacenter", "数据中心"], "dab": ["dab", "dual active bridge"], "cllc": ["cllc"], "llc": ["llc"], "800v": ["800v", "800 v", "800-volt", "800伏"], "magnetics": ["magnetics", "magnetic integration", "high-frequency magnetics", "磁性元件"]}
SOURCE_PRIORITY = {"ieee": 98, "nature.com": 98, "infineon": 96, "texas instruments": 96, "ti.com": 96, "renesas": 95, "sungrow": 95, "enphase": 95, "tmeic": 95, "电力电子技术": 96, "电力自动化设备": 96, "电力系统自动化": 96, "电工技术学报": 96, "中国电机工程学报": 96, "pv magazine": 90, "electronic design": 82, "hpcwire": 78}
MAX_CANDIDATES = 100
MAX_EVENTS = 50

def clean(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def source_score(source):
    s = source.lower()
    return max((v for k, v in SOURCE_PRIORITY.items() if k in s), default=40)

def topic_list(text):
    t = clean(text).lower()
    return sorted(k for k, vals in TOPICS.items() if any(v.lower() in t for v in vals))

def parse_published(item):
    for key in ("published", "updated", "created"):
        value = item.get(key)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    return ""

def resolve_google(url):
    if not url or "news.google.com" not in url:
        return url
    resolved = url
    if gnewsdecoder is not None:
        try:
            result = gnewsdecoder(url, interval=1)
            if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
                resolved = result["decoded_url"]
        except Exception as exc:
            print("Google News decoder error:", repr(exc))
    try:
        r = requests.get(resolved, timeout=8, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0 PowerElectronicsRadar"})
        if r.url and "news.google.com" not in r.url:
            resolved = r.url
    except Exception:
        pass
    return resolved

def same_event(a, b):
    ta = re.sub(r"[^\w\u4e00-\u9fff ]", "", a["title"].lower())
    tb = re.sub(r"[^\w\u4e00-\u9fff ]", "", b["title"].lower())
    if ta == tb or SequenceMatcher(None, ta, tb).ratio() >= 0.86:
        return True
    sa, sb = set(ta.split()), set(tb.split())
    return len(sa) >= 5 and len(sb) >= 5 and len(sa & sb) / max(1, min(len(sa), len(sb))) >= 0.72

def add_candidate(candidates, seen, item, source_name, source_type):
    title = clean(item.get("title", ""))
    summary = clean(item.get("summary", ""))
    if not title or not any(k.lower() in (title + " " + summary).lower() for k in KEYWORDS):
        return
    link = item.get("link", "") or ""
    resolved = resolve_google(link)
    key = resolved.split("#", 1)[0].rstrip("/") or title.lower()
    if key in seen:
        return
    seen.add(key)
    src = item.get("source")
    source = clean(src.get("title") or src.get("name") or source_name) if isinstance(src, dict) else clean(src or source_name)
    candidates.append({"source": source, "source_type": source_type, "title": title, "summary": summary[:5000], "link": resolved, "published_at": parse_published(item), "score": source_score(source), "paper": False})

def collect_events():
    candidates, seen = [], set()
    for source_name, url, source_type in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            print("RSS error:", source_name, repr(exc))
            continue
        for item in feed.entries[:14]:
            add_candidate(candidates, seen, item, source_name, source_type)
            if len(candidates) >= MAX_CANDIDATES:
                break
        if len(candidates) >= MAX_CANDIDATES:
            break

    # Domestic papers: query the journal itself through Crossref metadata, then fetch the DOI landing page.
    # The final AI input is the fetched publisher page, not Crossref metadata alone.
    paper_journals = ["电力电子技术", "电力自动化设备", "电力系统自动化", "电工技术学报", "中国电机工程学报"]
    paper_keywords = ["构网型", "SiC", "GaN", "电力电子", "变流器", "储能变流器", "DAB", "CLLC", "LLC", "固态变压器"]
    for p in crossref_papers(paper_journals, paper_keywords, since="2026-01-01", rows=20):
        key = (p.get("link") or p["title"]).lower()
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    grounded = []
    for c in candidates:
        source_text = fetch_source(c.get("link", ""), max_chars=9000)
        if len(source_text) < 500:
            print("Skipped without original source content:", c.get("title", ""))
            continue
        c["source_text"] = source_text
        grounded.append(c)

    clusters = []
    for article in sorted(grounded, key=lambda x: (x["score"], x["published_at"]), reverse=True):
        cluster = next((x for x in clusters if same_event(article, x["primary"])), None)
        if cluster:
            cluster["sources"].append({"source": article["source"], "source_type": article["source_type"], "title": article["title"], "link": article["link"], "published_at": article["published_at"]})
            if len(article["source_text"]) > len(cluster["primary"]["source_text"]):
                cluster["primary"].update({"summary": article["summary"], "source_text": article["source_text"], "link": article["link"], "source": article["source"], "source_type": article["source_type"]})
        else:
            clusters.append({"primary": dict(article), "sources": []})

    events = []
    for i, cluster in enumerate(clusters[:MAX_EVENTS], 1):
        p = cluster["primary"]
        events.append({
            "id": datetime.now(timezone.utc).strftime("%y%m%d") + "-" + f"{i:02d}",
            "title": p["title"],
            "category": topic_list(p["title"] + " " + p["summary"] + " " + p["source_text"]),
            "source_type": p["source_type"],
            "primary_source": p["source"],
            "published_at": p["published_at"],
            "link": p["link"],
            "summary_raw": p["summary"],
            "source_text": p["source_text"],
            "sources": cluster["sources"][:10]
        })
    return events

def ask_deepseek(events, report_date):
    key = os.environ["DEEPSEEK_API_KEY"]
    rules = """你是严谨的电力电子技术情报分析员。每条事件中的 SOURCE_TEXT 是唯一允许使用的事实来源。
禁止使用模型预训练知识、常识、标题推断或外部知识补充任何事实、参数、拓扑、应用、性能、成本、产业化状态或技术意义。
只可以把 SOURCE_TEXT 中明确写出的事实重新组织和解释。企业的宣传性判断必须标为“来源声称”，不能改写成客观事实。
plain_summary 写 3-5 句，面向普通读者，回答“发生了什么、为什么值得看”，但第二问只能依据 SOURCE_TEXT 明确表达的内容。
technical_summary 写 5-8 句，面向电力电子工程师，优先覆盖 SOURCE_TEXT 明确出现的器件、拓扑、控制方法、参数、实验平台、测试结果、应用对象和产业化信息。
如果 SOURCE_TEXT 不足以支持 5-8 句，就少写，绝不能为了凑句数引入新知识。plain_summary 与 technical_summary 必须有明显分工，不能只是同义改写。
不要输出“原文未提供”“未知参数”“无法判断”等填充句；没有写到的内容直接省略。
evidence.inferences 和 evidence.unknowns 必须始终为空数组；confirmed_facts 只能列 SOURCE_TEXT 明确事实；source_claims 只列 SOURCE_TEXT 中明确归属于企业/机构/作者的判断。
不要虚构原文链接。保留输入的 id、source_type、primary_source、published_at、link、sources。只输出合法 JSON，不要 Markdown。"""
    schema = {"events": [{"id": "", "title": "", "source_type": "", "primary_source": "", "published_at": "", "link": "", "category": [], "importance": "重点|一般", "plain_summary": "", "technical_summary": "", "technical": {"voltage": "", "power": "", "topology": "", "device": "", "switching_frequency": "", "efficiency": "", "power_density": "", "isolation": "", "control": "", "application": ""}, "industrialization": {"stage": "研究论文|实验室样机|工程样机|产品发布|试点/示范|试产|量产|商业部署|未知", "status": "", "target": ""}, "evidence": {"confirmed_facts": [], "source_claims": [], "inferences": [], "unknowns": []}, "sources": []}], "directions": {}, "observations": [], "quality_notes": ""}
    # Do not send source_text to the public output; it is only the private grounding context for this call.
    prompt_events = []
    for e in events:
        x = dict(e)
        x["SOURCE_TEXT"] = x.pop("source_text", "")
        prompt_events.append(x)
    prompt = rules + "\n报告日期：" + report_date + "\n输出结构：\n" + json.dumps(schema, ensure_ascii=False) + "\n输入事件：\n" + json.dumps(prompt_events, ensure_ascii=False)
    response = requests.post("https://api.deepseek.com/chat/completions", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, json={"model": "deepseek-chat", "messages": [{"role": "system", "content": "只输出合法JSON；任何事实都必须能在对应 SOURCE_TEXT 中找到明确依据。"}, {"role": "user", "content": prompt}], "temperature": 0.02, "max_tokens": 28000, "response_format": {"type": "json_object"}}, timeout=180)
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
    return json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I).strip())

def normalize_ai_event(ai_event, base):
    e = dict(ai_event or {})
    for k in ["id", "title", "source_type", "primary_source", "published_at", "link", "summary_raw"]:
        e[k] = base.get(k, e.get(k, ""))
    e["category"] = e.get("category") or base.get("category", [])
    e["sources"] = e.get("sources") or base.get("sources", [])
    e["plain_summary"] = clean(e.get("plain_summary", ""))
    e["technical_summary"] = clean(e.get("technical_summary", ""))
    technical = dict(e.get("technical") or {})
    for k in ["voltage", "power", "topology", "device", "switching_frequency", "efficiency", "power_density", "isolation", "control", "application"]:
        technical[k] = technical.get(k, "")
    e["technical"] = technical
    ind = dict(e.get("industrialization") or {})
    ind["stage"] = ind.get("stage") or "未知"
    ind["status"] = ind.get("status", "")
    ind["target"] = ind.get("target", "")
    e["industrialization"] = ind
    evidence = dict(e.get("evidence") or {})
    evidence["confirmed_facts"] = evidence.get("confirmed_facts") or []
    evidence["source_claims"] = evidence.get("source_claims") or []
    evidence["inferences"] = []
    evidence["unknowns"] = []
    e["evidence"] = evidence
    return e

def fallback_event(base):
    e = normalize_ai_event({}, base)
    e["plain_summary"] = clean(base.get("summary_raw", ""))
    e["technical_summary"] = ""
    return e

def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(timezone.utc).astimezone(tz)
    report_date = now.strftime("%Y-%m-%d")
    raw_events = collect_events()
    if not raw_events:
        ai = {"events": [], "directions": {}, "observations": [], "quality_notes": "本次没有获得可核验原文内容的强相关事件。"}
        events = []
    else:
        try:
            ai = ask_deepseek(raw_events, report_date)
            by_id = {x["id"]: x for x in raw_events}
            events = [normalize_ai_event(x, by_id[x.get("id")]) for x in ai.get("events", []) if x.get("id") in by_id]
            if not events:
                raise ValueError("AI returned no matching events")
        except Exception as exc:
            print("AI structured output failed:", repr(exc))
            ai = {"events": [], "directions": {}, "observations": [], "quality_notes": "AI分析失败；仅保留已获取的原文摘要，不补充原文之外的事实。"}
            events = [fallback_event(x) for x in raw_events]
    # Never publish the full fetched article body into data.json; keep it only as AI grounding input.
    for e in events:
        e.pop("source_text", None)
    data = {"schema_version": "3.2", "updated": now.isoformat(), "report_date": report_date, "event_count": len(events), "events": events, "directions": ai.get("directions", {}), "observations": ai.get("observations", []), "quality_notes": ai.get("quality_notes", "")}
    with open("data.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    print("Validated", len(events), "strictly grounded events")

if __name__ == "__main__":
    main()
