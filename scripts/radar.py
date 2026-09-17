import os
import json
import re
import html
import requests
import feedparser
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse


RSS_SOURCES = [
    {
        "name": "Google News - Power Electronics",
        "url": "https://news.google.com/rss/search?q=power+electronics"
    },
    {
        "name": "Google News - Solid State Transformer",
        "url": "https://news.google.com/rss/search?q=%22solid-state+transformer%22"
    },
    {
        "name": "Google News - SiC Power Electronics",
        "url": "https://news.google.com/rss/search?q=SiC+power+electronics"
    },
    {
        "name": "Google News - GaN Power Electronics",
        "url": "https://news.google.com/rss/search?q=GaN+power+electronics"
    },
    {
        "name": "Google News - Grid Forming",
        "url": "https://news.google.com/rss/search?q=%22grid-forming%22+power"
    },
]

KEYWORDS = [
    "SST", "solid-state transformer", "solid state transformer", "SiC", "GaN",
    "DAB", "CLLC", "LLC", "grid-forming", "GFM", "PCS", "800V",
    "AI data center", "AI datacenter", "high power density", "wide-bandgap",
    "power electronics", "power semiconductor", "silicon carbide", "gallium nitride"
]

# Topics that are useful for engineering radar clustering.
TOPIC_GROUPS = {
    "sst": ["sst", "solid-state transformer", "solid state transformer"],
    "sic": ["sic", "silicon carbide"],
    "gan": ["gan", "gallium nitride"],
    "gfm": ["grid-forming", "grid forming", "gfm"],
    "pcs": ["pcs", "power conversion system"],
    "ai_dc": ["ai data center", "ai datacenter", "data center", "datacenter"],
    "dab": ["dab", "dual active bridge"],
    "cllc": ["cllc"],
    "llc": ["llc"],
    "800v": ["800v", "800 v", "800-volt"],
    "magnetics": ["magnetic integration", "integrated magnetics", "high frequency magnetics", "high-frequency magnetics"],
}

# Companies/entities that frequently appear in the radar. This helps merge syndicated coverage
# of the same product or facility even when headlines are worded differently.
ENTITY_ALIASES = {
    "enphase": ["enphase", "enphase energy"],
    "rir": ["rir power electronics", "rir power"],
    "sungrow": ["sungrow"],
    "tmeic": ["tmeic"],
    "renesas": ["renesas"],
    "delta": ["delta electronics", "delta"],
}

# Prefer technical/primary sources over finance rewrites when choosing a representative source.
SOURCE_PRIORITY = {
    "nature.com": 100,
    "ieee": 98,
    "renesas": 95,
    "sungrow": 95,
    "enphase": 95,
    "tmeic": 95,
    "pv magazine global": 90,
    "pv-magazine-usa.com": 90,
    "electronic design": 82,
    "hpcwire": 78,
    "interesting engineering": 70,
    "machine maker": 68,
    "railwaygazette.com": 65,
    "data center knowledge": 60,
    "pr newswire": 58,
    "business standard": 45,
    "yahoo finance": 30,
    "24/7 wall st.": 25,
    "finance.biggo.com": 20,
    "tradingview": 15,
    "scanx.trade": 10,
}

MAX_CANDIDATES = 80
MAX_EVENTS = 20


def clean_html(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(title):
    title = clean_html(title).lower()
    title = re.sub(r"\([^)]*download[^)]*\)", "", title)
    title = re.sub(r"\s*[-|–—:]\s*[^-]{1,50}$", "", title)
    title = re.sub(r"[^\w\u4e00-\u9fff ]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def source_score(source):
    s = (source or "").lower().strip()
    for key, score in SOURCE_PRIORITY.items():
        if key in s:
            return score
    return 40


def get_source_name(item, fallback):
    source = item.get("source")
    if isinstance(source, dict):
        name = source.get("title") or source.get("name")
        if name:
            return clean_html(name)
    if source:
        return clean_html(str(source))
    return fallback


def topic_set(text):
    t = clean_html(text).lower()
    found = set()
    for group, terms in TOPIC_GROUPS.items():
        if any(term in t for term in terms):
            found.add(group)
    return found


def entity_set(text):
    t = clean_html(text).lower()
    found = set()
    for entity, aliases in ENTITY_ALIASES.items():
        if any(alias in t for alias in aliases):
            found.add(entity)
    return found


def extract_meta_description(url):
    """Try to turn a Google News redirect into a cleaner original URL and description."""
    if not url or "news.google.com" not in url:
        return url, ""
    try:
        r = requests.get(
            url,
            timeout=8,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 PowerElectronicsRadar/1.0"},
        )
        final_url = r.url or url
        page = r.text[:500000]
        candidates = re.findall(
            r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']*)["\']',
            page,
            flags=re.I,
        )
        if not candidates:
            candidates = re.findall(
                r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\'](?:og:description|description)["\']',
                page,
                flags=re.I,
            )
        description = clean_html(candidates[0]) if candidates else ""
        return final_url, description
    except Exception:
        return url, ""


def similar_event(a, b):
    """Conservative event-level deduplication.

    Exact/near-identical titles are merged. Different headlines are merged when they share
    an entity and at least one strong technical topic, or enough distinctive title tokens.
    """
    ta = normalize_title(a["title"])
    tb = normalize_title(b["title"])
    if ta == tb:
        return True
    ratio = SequenceMatcher(None, ta, tb).ratio()
    if ratio >= 0.86:
        return True

    ea, eb = entity_set(a["title"]), entity_set(b["title"])
    topics_a = topic_set(a["title"] + " " + a.get("summary", ""))
    topics_b = topic_set(b["title"] + " " + b.get("summary", ""))

    if ea & eb and topics_a & topics_b:
        # Avoid merging unrelated articles from the same company merely because they mention power electronics.
        strong_topics = {"sst", "sic", "gan", "gfm", "dab", "cllc", "llc", "800v", "magnetics"}
        if (topics_a & topics_b) & strong_topics:
            return True

    # Generic syndicated titles with many words in common.
    words_a = set(ta.split())
    words_b = set(tb.split())
    if len(words_a) >= 5 and len(words_b) >= 5:
        overlap = len(words_a & words_b) / max(1, min(len(words_a), len(words_b)))
        if overlap >= 0.72:
            return True
    return False


def collect_articles():
    candidates = []
    seen_links = set()

    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
        except Exception as exc:
            print(f"RSS error: {source['name']}: {exc}")
            continue

        for item in feed.entries[:20]:
            title = clean_html(item.get("title", ""))
            if not title:
                continue
            raw_summary = clean_html(item.get("summary", ""))
            link = item.get("link", "") or ""
            text = f"{title} {raw_summary}".lower()
            if not any(keyword.lower() in text for keyword in KEYWORDS):
                continue

            link_key = link.split("#", 1)[0].rstrip("/")
            if link_key and link_key in seen_links:
                continue
            if link_key:
                seen_links.add(link_key)

            source_name = get_source_name(item, source["name"])
            candidates.append({
                "source": source_name,
                "title": title,
                "summary": raw_summary,
                "link": link,
                "source_score": source_score(source_name),
            })
            if len(candidates) >= MAX_CANDIDATES:
                break
        if len(candidates) >= MAX_CANDIDATES:
            break

    # Resolve a limited number of links. This improves both readability and AI evidence quality.
    for article in candidates[:MAX_CANDIDATES]:
        resolved, description = extract_meta_description(article["link"])
        if resolved and "news.google.com" not in resolved:
            article["link"] = resolved
        if description and len(description) > len(article["summary"]):
            article["summary"] = description[:1200]

    # Cluster into events. Keep the highest-quality source as the representative article.
    events = []
    for article in sorted(candidates, key=lambda x: x["source_score"], reverse=True):
        matched = None
        for event in events:
            if similar_event(article, event["primary"]):
                matched = event
                break
        if matched:
            matched["sources"].append({
                "source": article["source"],
                "title": article["title"],
                "link": article["link"],
            })
            if article["summary"] and len(article["summary"]) > len(matched["primary"].get("summary", "")):
                matched["primary"]["summary"] = article["summary"]
        else:
            events.append({"primary": dict(article), "sources": []})

    output = []
    for event in events[:MAX_EVENTS]:
        p = event["primary"]
        sources = event["sources"]
        record = {
            "source": p["source"],
            "title": p["title"],
            "summary": p.get("summary", ""),
            "link": p["link"],
        }
        if sources:
            record["related_sources"] = sources[:8]
        output.append(record)
    return output


def ask_deepseek(articles, report_date):
    api_key = os.environ["DEEPSEEK_API_KEY"]

    content = "\n\n".join(
        f"""
事件编号：{i}
主来源：{a['source']}
标题：{a['title']}
摘要：{a['summary'] or '原文摘要未提供'}
主链接：{a['link']}
相关来源：{json.dumps(a.get('related_sources', []), ensure_ascii=False)}
"""
        for i, a in enumerate(articles, 1)
    )

    prompt = f"""
你是一名严谨的电力电子技术情报分析员，为有工程经验的电力电子工程师和考研技术学习服务。

报告日期：{report_date}
必须严格使用这个北京时间日期，禁止根据文章内容猜日期。

输入已经完成“同一事件”聚类。一个事件可能包含多个媒体来源。禁止把同一事件再次拆成多个事件。

重点关注：SST、SiC、GaN、DAB/CLLC/LLC、GFM、储能 PCS、800V DC、AI 数据中心、高功率密度、高频磁件、拓扑、器件、调制、控制、热设计。

【事实边界】
1. 只把输入材料明确支持的内容写成事实。
2. “全球首个/世界首台/首次”等，只能写成“来源声称”，不能自行确认。
3. “production/进入生产”不能自动改写成“量产”；“2028 target”不能写成已经实现。
4. 原文没有参数就写“原文未提供”，严禁凭常识补充电压、功率、效率、频率、功率密度、器件型号、拓扑或控制方法。
5. 不能因为“bidirectional/high frequency/modular”就推断 DAB、CLLC、MMC、ISOP 等具体拓扑。
6. 财经新闻中的股价、融资、营收等不是技术进展，除非同时包含明确技术事实。
7. 论文、实验室样机、工程样机、产品发布、试点、试产、量产、商业部署必须严格区分。
8. 技术推断使用 [模型推断]；发展趋势使用 [趋势判断]；来源自己的宣传或声明使用 [来源声称]；材料不足使用 [信息不足]。
9. 同一事件的多个来源只分析一次，并列出主要来源和相关来源。

【技术参数表要求】
每个重点事件尽量抽取以下字段：
- 电压等级
- 功率等级
- 拓扑
- 功率器件
- 开关频率
- 效率
- 功率密度
- 隔离方式
- 控制/调制
- 应用场景
- 产业化阶段
没有披露的字段统一写“原文未提供”。

【输出】
# 电力电子技术雷达
日期：{report_date}

## 一、今日最值得关注
选择 3～5 个真正有技术价值的独立事件。
每项：
### 标题
- 事件：
- 证据：
- 核心技术：
- 技术参数：
  - 电压等级：
  - 功率等级：
  - 拓扑：
  - 功率器件：
  - 开关频率：
  - 效率：
  - 功率密度：
  - 隔离方式：
  - 控制/调制：
  - 应用场景：
- 产业化阶段：
- 技术意义：
- 需要继续核实：
- 主要来源：

## 二、技术方向
分别讨论 SST、SiC/GaN、DAB/CLLC/LLC、GFM、PCS、800V DC/AI 数据中心、高功率密度/磁件。没有明确进展就写“本批信息未发现明确进展”。

## 三、同一事件合并
列出存在多来源报道的事件，以及相关来源。不要重复分析。

## 四、对工程师有用的技术观察
3～6 条。所有推断/趋势必须带标签。

## 五、阅读建议
分“建议深入阅读”和“快速浏览”，只解释理由，不打总体分数。

## 六、信息质量与缺口
说明论文、企业新闻、媒体报道、产品发布、财经信息等各自的证据性质，并指出缺失的关键参数。

今天的事件数据：
{content}
"""

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是专业电力电子研究人员。事实准确性优先于内容丰富度；不编造任何技术参数。"
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main():
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(timezone.utc).astimezone(beijing_tz)
    report_date = now_beijing.strftime("%Y-%m-%d")

    articles = collect_articles()
    if not articles:
        result = f"# 电力电子技术雷达\n日期：{report_date}\n\n今天没有筛选到符合条件的电力电子信息。"
    else:
        result = ask_deepseek(articles, report_date)

    data = {
        "updated": now_beijing.isoformat(),
        "report_date": report_date,
        "article_count": len(articles),
        "articles": articles,
        "summary": result,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
