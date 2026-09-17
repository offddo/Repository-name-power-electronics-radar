import os
import json
import re
import html
import requests
import feedparser
from datetime import datetime, timezone, timedelta


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
    "SST",
    "solid-state transformer",
    "SiC",
    "GaN",
    "DAB",
    "CLLC",
    "LLC",
    "grid-forming",
    "GFM",
    "PCS",
    "800V",
    "AI data center",
    "AI datacenter",
    "high power density",
    "wide-bandgap",
    "power electronics",
]

MAX_ARTICLES = 20


def clean_html(text):
    """Remove HTML tags/entities from RSS summaries."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(title):
    """Normalize a title for duplicate detection."""
    title = html.unescape(title or "").lower()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[^\w\u4e00-\u9fff ]", "", title)
    return title.strip()


def get_source_name(item, fallback):
    """Prefer the publisher supplied by the RSS item when available."""
    source = item.get("source")
    if isinstance(source, dict):
        name = source.get("title") or source.get("name")
        if name:
            return clean_html(name)
    if source:
        return clean_html(str(source))
    return fallback


def collect_articles():
    """Collect, filter, clean and deduplicate RSS articles."""
    articles = []
    seen_titles = set()
    seen_links = set()

    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
        except Exception as exc:
            print(f"RSS error: {source['name']}: {exc}")
            continue

        for item in feed.entries[:15]:
            title = clean_html(item.get("title", ""))
            summary = clean_html(item.get("summary", ""))
            link = item.get("link", "") or ""

            if not title:
                continue

            text = f"{title} {summary}".lower()
            if not any(keyword.lower() in text for keyword in KEYWORDS):
                continue

            title_key = normalize_title(title)
            link_key = link.split("#", 1)[0].rstrip("/")

            if title_key in seen_titles or (link_key and link_key in seen_links):
                continue

            seen_titles.add(title_key)
            if link_key:
                seen_links.add(link_key)

            articles.append({
                "source": get_source_name(item, source["name"]),
                "title": title,
                "summary": summary,
                "link": link,
            })

            if len(articles) >= MAX_ARTICLES:
                return articles

    return articles


def ask_deepseek(articles, report_date):
    api_key = os.environ["DEEPSEEK_API_KEY"]

    content = "\n\n".join(
        f"""
编号：{i}
标题：{a['title']}
来源：{a['source']}
摘要：{a['summary']}
链接：{a['link']}
"""
        for i, a in enumerate(articles, 1)
    )

    prompt = f"""
你是一名严谨的电力电子技术情报分析员，为工程师和考研期间的技术学习提供信息雷达。

报告日期：{report_date}
注意：报告日期必须严格使用“{report_date}”，禁止根据新闻标题、摘要或模型知识自行推测日期。

下面是今天通过 RSS 收集的候选信息。请先判断哪些是真正有技术价值的内容，再进行归并分析。

重点关注：
1. SST / Solid-State Transformer
2. SiC / GaN / 宽禁带器件
3. DAB / CLLC / LLC 等隔离型 DC-DC
4. Grid-Forming / GFM
5. 储能 PCS
6. 800V DC
7. AI 数据中心供电
8. 高功率密度
9. 高频磁件与磁集成
10. 拓扑、器件、调制、控制和热设计

【最重要的事实性要求】
- 不要把新闻标题中的宣传性表述直接当成已经验证的事实。
- “全球首个”“世界首台”“首次”“行业第一”等表述，只有当来源明确如此表述时才能写，并必须标注“[来源声称]”。不要自行升级为事实。
- 不要编造额定功率、电压、电流、效率、频率、功率密度、器件型号、拓扑、控制方法、量产时间等参数。
- 原文没有给出的参数必须写“原文未提供相关信息”。
- 不要根据常识猜测具体拓扑。例如不能仅因为双向、高频或模块化就断言“采用 DAB/CLLC/ISOP/MMC”。如果确实需要提出可能性，必须标记为“[模型推断]”，并说明依据；没有必要时不要推断。
- 严格区分：论文/理论研究、实验室样机、工程样机、产品发布、试点部署、试产、量产、商业部署。原文没有说明时写“产业化阶段未披露”。
- 不要把股票价格、融资、市场宣传等财经信息当成技术进展，除非它直接包含有价值的技术事实。
- 不要把预测写成事实。对于未来判断统一标记为“[趋势判断]”。
- 对有明显重复的新闻必须合并，只保留一个事件，不要因为不同媒体转载而重复分析。
- 对证据不足的信息，明确写“[信息不足]”。

【证据标签】
使用以下标签帮助读者快速判断可信度：
[已证实]：来源直接给出了明确事实、参数或论文/产品信息。
[来源声称]：这是新闻稿、媒体或企业自己的表述，尚未由当前材料独立验证。
[模型推断]：根据材料进行的合理技术推断，不是原文事实。
[趋势判断]：对技术发展方向的分析，不是已经发生的事实。
[信息不足]：当前材料不足以支持更具体的结论。

【输出格式】
# 电力电子技术雷达
日期：{report_date}

## 一、今日最值得关注
选择 3～5 个真正有技术价值的独立事件。不要按新闻数量排序，也不要给事件打分。
每项包括：
- 事件
- 证据标签
- 核心技术
- 关键参数（仅填写原文明确给出的）
- 技术意义
- 产业化阶段
- 值得继续阅读的原因

## 二、技术方向
分别总结 SST、SiC/GaN、DAB/CLLC/LLC、GFM、PCS、800V DC/AI 数据中心、高功率密度/磁件等方向。没有有效信息的方向直接写“本批信息未发现明确进展”。

## 三、同一事件合并
明确指出哪些新闻实际上属于同一个事件，并说明采用哪个来源作为主要依据。不要重复分析。

## 四、对工程师有用的技术观察
只基于本批材料，提炼 3～6 条技术观察。涉及推断必须标记 [模型推断] 或 [趋势判断]。

## 五、阅读优先级建议
分成“建议深入阅读”和“快速浏览”两组，只说明理由，不进行总体排名或评分。

## 六、信息质量说明
指出本批信息中哪些内容属于企业新闻稿、媒体报道、论文、产品信息等，并说明当前材料有哪些明显缺口。

请保持技术严谨、简洁，不要为了让报告看起来丰富而补充未经来源支持的内容。

今天收集的信息：

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
                    "content": "你是专业的电力电子技术研究人员，优先保证事实准确性，不编造技术细节。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main():
    # Use Beijing time for the report date so the radar is aligned with the user's daily schedule.
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(timezone.utc).astimezone(beijing_tz)
    report_date = now_beijing.strftime("%Y-%m-%d")

    articles = collect_articles()

    if not articles:
        result = f"# 电力电子技术雷达\n日期：{report_date}\n\n今天没有筛选到符合条件的电力电子信息。"
    else:
        result = ask_deepseek(articles, report_date)

    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "report_date": report_date,
        "article_count": len(articles),
        "articles": articles,
        "summary": result
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
