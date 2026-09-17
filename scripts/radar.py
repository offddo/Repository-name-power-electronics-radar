import os
import json
import requests
import feedparser
from datetime import datetime, timezone


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
    "high power density",
    "wide-bandgap",
    "power electronics",
]


def collect_articles():

    articles = []

    for source in RSS_SOURCES:

        feed = feedparser.parse(source["url"])

        for item in feed.entries[:10]:

            title = item.get("title", "")
            summary = item.get("summary", "")
            link = item.get("link", "")

            text = f"{title} {summary}".lower()

            if any(keyword.lower() in text for keyword in KEYWORDS):

                articles.append({
                    "source": source["name"],
                    "title": title,
                    "summary": summary,
                    "link": link
                })

    return articles[:20]


def ask_deepseek(articles):

    api_key = os.environ["DEEPSEEK_API_KEY"]

    content = "\n\n".join(
        f"""
标题：{a['title']}
来源：{a['source']}
摘要：{a['summary']}
链接：{a['link']}
"""
        for a in articles
    )

    prompt = f"""
你是一名电力电子技术情报分析员。

请分析下面今天收集到的电力电子信息。

重点关注：

1. SST / Solid-State Transformer
2. SiC
3. GaN
4. DAB / CLLC / LLC
5. Grid-Forming
6. 储能 PCS
7. 800V DC
8. AI 数据中心供电
9. 高功率密度
10. 高频磁件
11. 宽禁带半导体

请不要简单翻译新闻。

对于每条重要信息，尽量回答：

- 一句话结论
- 技术方向
- 核心技术
- 解决什么问题
- 相比传统方案有什么变化
- 拓扑 / 器件 / 控制方法
- 实验或产品参数（如果有）
- 当前产业化情况
- 为什么值得关注
- 是否值得进一步阅读

如果信息不足，请明确写：

“原文未提供相关信息”。

不要编造参数。

今天的信息：

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
                    "content": "你是专业的电力电子技术研究人员。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def main():

    articles = collect_articles()

    if not articles:

        result = "今天没有筛选到符合条件的电力电子信息。"

    else:

        result = ask_deepseek(articles)

    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
        "summary": result
    }

    with open("data.json", "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    main()
