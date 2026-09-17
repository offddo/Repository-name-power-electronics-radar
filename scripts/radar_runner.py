from pathlib import Path

# Run radar.py after applying persistent runtime configuration without duplicating its core logic.
path = Path(__file__).with_name("radar.py")
text = path.read_text(encoding="utf-8")

# Fix the prompt template and enforce separate plain/technical summaries.
text = text.replace("    prompt = f'''", "    prompt = '''", 1)
text = text.replace("报告日期：{date}", "报告日期：DATE_PLACEHOLDER", 1)
text = text.replace("{json.dumps(events, ensure_ascii=False)}'''", "EVENTS_PLACEHOLDER'''", 1)
text = text.replace(
    "EVENTS_PLACEHOLDER'''\n\n    r = requests.post",
    "EVENTS_PLACEHOLDER'''\n    prompt = prompt.replace(\"DATE_PLACEHOLDER\", date).replace(\"EVENTS_PLACEHOLDER\", json.dumps(events, ensure_ascii=False))\n\n    r = requests.post",
    1,
)
text = text.replace(
    "7. summary 必须短而具体，并在句首使用一个标签：[已证实]、[来源声称]、[模型推断]、[趋势判断]、[信息不足]。",
    "7. 必须分别输出 plain_summary 和 technical_summary；plain_summary 面向普通读者，用1～2句话解释发生了什么及其意义；technical_summary 面向电力电子工程师，用1～3句话说明具体技术、器件、拓扑和关键参数；两者不得复制。",
    1,
)
text = text.replace('"summary":"",', '"plain_summary":"","technical_summary":"",', 1)
text = text.replace('"technical":{"voltage":"原文未提供","power":"原文未提供","topology":"原文未提供","device":"原文未提供","switching_frequency":"原文未提供","efficiency":"原文未提供","power_density":"原文未提供","isolation":"原文未提供","control":"原文未提供","application":"原文未提供"}', '"technical":{}', 1)
text = text.replace('"industrialization":{"stage":"未知","status":"","target":""}', '"industrialization":{}', 1)
text = text.replace('"evidence":{"confirmed_facts":[],"source_claims":[],"inferences":[],"unknowns":[]}', '"evidence":{"confirmed_facts":[],"source_claims":[],"inferences":[]}', 1)

# Add domestic industry/news and domestic academic sources.
marker = '    ("Google News - Grid Forming", "https://news.google.com/rss/search?q=%22grid-forming%22+power&hl=en-US&gl=US&ceid=US:en"),\n]'
extra = '''    ("国内资讯 - 中国电力电子", "https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 构网型变流器", "https://news.google.com/rss/search?q=%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+GFM+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - SiC GaN", "https://news.google.com/rss/search?q=SiC+GaN+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E5%8A%9F%E7%8E%87%E5%8D%8A%E5%AF%BC%E4%BD%93&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 800V 数据中心电源", "https://news.google.com/rss/search?q=800V+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 阳光电源", "https://news.google.com/rss/search?q=%E9%98%B3%E5%85%89%E7%94%B5%E6%BA%90+%E5%8F%98%E6%B5%81%E5%99%A8+SiC+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 华为数字能源", "https://news.google.com/rss/search?q=%E5%8D%8E%E4%B8%BA+%E6%95%B0%E5%AD%97%E8%83%BD%E6%BA%90+800V+%E7%94%B5%E6%BA%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 中车时代电气", "https://news.google.com/rss/search?q=%E4%B8%AD%E8%BD%A6%E6%97%B6%E4%BB%A3%E7%94%B5%E6%B0%94+SiC+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 上能电气", "https://news.google.com/rss/search?q=%E4%B8%8A%E8%83%BD%E7%94%B5%E6%B0%94+PCS+%E5%82%A8%E8%83%BD+%E5%8F%98%E6%B5%81%E5%99%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 科华数据", "https://news.google.com/rss/search?q=%E7%A7%91%E5%8D%8E%E6%95%B0%E6%8D%AE+UPS+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力电子技术", "https://news.google.com/rss/search?q=site%3Adldzqk.com+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90%E6%8A%80%E6%9C%AF+SiC+GaN+DAB+CLLC+GFM&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力自动化设备", "https://news.google.com/rss/search?q=site%3Aepae.cn+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力系统自动化", "https://news.google.com/rss/search?q=site%3Aaeps-info.com+%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电工技术学报", "https://news.google.com/rss/search?q=site%3Adgjsxb.ces-transaction.com+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+%E5%8F%98%E6%B5%81%E5%99%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 中国电机工程学报", "https://news.google.com/rss/search?q=site%3Acjepe.com.cn+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E6%9E%84%E7%BD%91+SiC+GaN&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - CNKI 电力电子", "https://news.google.com/rss/search?q=site%3Acnki.net+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+GFM+DAB+CLLC&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]'''
if marker not in text:
    raise SystemExit("RSS insertion marker not found")
text = text.replace(marker, marker[:-1] + extra + "\n]", 1)

text = text.replace("MAX_CANDIDATES = 80\nMAX_EVENTS = 15", "MAX_CANDIDATES = 240\nMAX_EVENTS = 40")
text = text.replace("for item in feed.entries[:25]:", "for item in feed.entries[:40]:")

old_priority = '    "data center knowledge": 60, "pr newswire": 58, "yahoo finance": 30,'
new_priority = '''    "dldzqk": 100, "电力电子技术": 100, "epae.cn": 99, "电力自动化设备": 99,
    "aeps-info": 98, "电力系统自动化": 98, "dgjsxb": 98, "电工技术学报": 98,
    "cjepe": 98, "中国电机工程学报": 98, "cnki": 94,
    "data center knowledge": 60, "pr newswire": 58, "yahoo finance": 30,'''
if old_priority not in text:
    raise SystemExit("Priority marker not found")
text = text.replace(old_priority, new_priority, 1)

old_append = '            candidates.append({"source": source, "title": title, "summary": summary, "link": link, "score": score(source)})'
new_append = '''            if fallback.startswith("国内论文"):
                source_type = "国内论文"
            elif fallback.startswith("国内资讯"):
                source_type = "国内资讯"
            elif any(x in (source.lower() + " " + link.lower()) for x in ["dldzqk", "epae.cn", "aeps-info", "dgjsxb", "cjepe", "cnki"]):
                source_type = "国内论文"
            else:
                source_type = "国际资讯"
            candidates.append({"source": source, "title": title, "summary": summary, "link": link, "score": score(source), "source_type": source_type})'''
if old_append not in text:
    raise SystemExit("Candidate marker not found")
text = text.replace(old_append, new_append, 1)

old_event = '            "sources": c["sources"][:10]\n        })'
new_event = '            "source_type": p.get("source_type", "国际资讯"),\n            "sources": c["sources"][:10]\n        })'
if old_event not in text:
    raise SystemExit("Event marker not found")
text = text.replace(old_event, new_event, 1)

text = text.replace(
    "10. 每个事件必须保留原 id、primary_source、link 和 sources，不得删除来源。",
    "10. 每个事件必须保留原 id、primary_source、link、source_type 和 sources，不得删除来源。\n11. 优先分析与 SST、SiC、GaN、GFM、PCS、DAB、CLLC、LLC、800V、AI 数据中心、高频磁件直接相关的事件；仅擦边的泛能源新闻不要写进重点事件。",
    1,
)
text = text.replace(
    '"id":"原id","title":"","category":[],"importance":"重点|一般","evidence_level":"","summary":"",',
    '"id":"原id","title":"","category":[],"source_type":"国内资讯|国内论文|国际资讯","importance":"重点|一般","evidence_level":"","plain_summary":"","technical_summary":"",',
    1,
)

exec(compile(text, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
