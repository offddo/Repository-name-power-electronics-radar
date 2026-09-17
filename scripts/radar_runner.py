from pathlib import Path

# Runtime patch layer: keep the core radar.py readable while enforcing the site's
# source, date, scoring, and summary rules in one place.
path = Path(__file__).with_name("radar.py")
text = path.read_text(encoding="utf-8")

# -------------------- source coverage --------------------
marker = '    ("Google News - Grid Forming", "https://news.google.com/rss/search?q=%22grid-forming%22+power&hl=en-US&gl=US&ceid=US:en"),\n]'
extra = '''    ("国内资讯 - 中国电力电子", "https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 构网型变流器", "https://news.google.com/rss/search?q=%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+GFM+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - SiC GaN", "https://news.google.com/rss/search?q=SiC+GaN+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E5%8A%9F%E7%8E%87%E5%8D%8A%E5%AF%BC%E4%BD%93&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 800V 数据中心电源", "https://news.google.com/rss/search?q=800V+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 阳光电源", "https://news.google.com/rss/search?q=%E9%98%B3%E5%85%89%E7%94%B5%E6%BA%90+%E5%8F%98%E6%B5%81%E5%99%A8+SiC+PCS&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 华为数字能源", "https://news.google.com/rss/search?q=%E5%8D%8E%E4%B8%BA+%E6%95%B0%E5%AD%97%E8%83%BD%E6%BA%90+800V+%E7%94%B5%E6%源&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 中车时代电气", "https://news.google.com/rss/search?q=%E4%B8%AD%E8%BD%A6%E6%97%B6%E4%BB%A3%E7%94%B5%E6%B0%94+SiC+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 上能电气", "https://news.google.com/rss/search?q=%E4%B8%8A%E8%83%BD%E7%94%B5%E6%B0%94+PCS+%E5%82%A8%E能+变流器&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内资讯 - 科华数据", "https://news.google.com/rss/search?q=%E7%A7%91%E5%8D%8E%E6%95%B0%E6%8D%AE+UPS+%E6%95%B0%E6%8D%AE%E4%B8%AD%E5%BF%83+%E7%94%B5%E6%BA%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力电子技术", "https://news.google.com/rss/search?q=site%3Adldzqk.com+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90%E6%8A%80%E6%9C%AF+SiC+GaN+DAB+CLLC+GFM&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力自动化设备", "https://news.google.com/rss/search?q=site%3Aepae.cn+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电力系统自动化", "https://news.google.com/rss/search?q=site%3Aaeps-info.com+%E6%9E%84%E7%BD%91%E5%9E%8B+%E5%8F%98%E6%B5%81%E5%99%A8+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 电工技术学报", "https://news.google.com/rss/search?q=site%3Adgjsxb.ces-transaction.com+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+%E5%8F%98%E6%B5%81%E5%99%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - 中国电机工程学报", "https://news.google.com/rss/search?q=site%3Acjepe.com.cn+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+%E6%9E%84%E7%BD%91+SiC+GaN&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("国内论文 - CNKI 电力电子", "https://news.google.com/rss/search?q=site%3Acnki.net+%E7%94%B5%E5%8A%9B%E7%94%B5%E5%AD%90+SiC+GaN+GFM+DAB+CLLC&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]'''
if marker in text:
    # extra already contains the closing bracket; do not append another one.
    text = text.replace(marker, marker[:-1] + extra, 1)

# Prefer domestic journals when ranking candidates.
text = text.replace(
    '    "data center knowledge": 60, "pr newswire": 58, "yahoo finance": 30,',
    '    "dldzqk": 100, "电力电子技术": 100, "epae.cn": 99, "电力自动化设备": 99,\n    "aeps-info": 98, "电力系统自动化": 98, "dgjsxb": 98, "电工技术学报": 98,\n    "cjepe": 98, "中国电机工程学报": 98, "cnki": 94,\n    "data center knowledge": 60, "pr newswire": 58, "yahoo finance": 30,', 1)

# More candidates, but cap the final daily report at a practical engineering-reading size.
text = text.replace("MAX_CANDIDATES = 80", "MAX_CANDIDATES = 240", 1)
text = text.replace("MAX_EVENTS = 15", "MAX_EVENTS = 30", 1)
text = text.replace("for item in feed.entries[:25]:", "for item in feed.entries[:40]:", 1)

# -------------------- publication date --------------------
text = text.replace(
    "from datetime import datetime, timezone, timedelta",
    "from datetime import datetime, timezone, timedelta\nfrom email.utils import parsedate_to_datetime",
    1)
helper = '''\n\ndef parse_published(item):\n    raw = item.get("published") or item.get("updated") or item.get("created") or ""\n    try:\n        dt = parsedate_to_datetime(raw)\n        if dt.tzinfo is None:\n            dt = dt.replace(tzinfo=timezone.utc)\n        return dt.astimezone(timezone(timedelta(hours=8))).isoformat()\n    except Exception:\n        return ""\n'''
if "def parse_published(item):" not in text:
    text = text.replace("\ndef clean(text):", helper + "\ndef clean(text):", 1)
text = text.replace(
    '            candidates.append({"source": source, "title": title, "summary": summary, "link": link, "score": score(source)})',
    '            candidates.append({"source": source, "title": title, "summary": summary, "link": link, "score": score(source), "published_at": parse_published(item), "source_type": ("国内论文" if fallback.startswith("国内论文") else "国内资讯" if fallback.startswith("国内资讯") else "国际资讯")})',
    1)
text = text.replace(
    '            "summary_raw": p["summary"],\n            "sources": c["sources"][:10]',
    '            "summary_raw": p["summary"],\n            "published_at": p.get("published_at", ""),\n            "source_type": p.get("source_type", "国际资讯"),\n            "sources": c["sources"][:10]',
    1)

# -------------------- richer AI summaries --------------------
old_rule = '7. summary 必须短而具体，并在句首使用一个标签：[已证实]、[来源声称]、[模型推断]、[趋势判断]、[信息不足]。'
new_rule = '''7. 必须分别输出 plain_summary 和 technical_summary，禁止只写一句笼统摘要。plain_summary 写 3～5 句：先说明发生了什么，再说明涉及的产品/技术，再说明为什么值得关注；只使用原文事实。technical_summary 写 5～8 句：围绕器件、拓扑、控制、参数、测试、应用和工程意义展开；有数据就写数据，没有数据不要猜。两者内容不能简单重复。'''
text = text.replace(old_rule, new_rule, 1)
text = text.replace(
    '"id":"原id","title":"","category":[],"importance":"重点|一般","evidence_level":"","summary":"",',
    '"id":"原id","title":"","category":[],"source_type":"国内资讯|国内论文|国际资讯|国际论文","importance":"重点|一般","evidence_level":"","plain_summary":"","technical_summary":"",',
    1)
text = text.replace(
    '"technical":{"voltage":"原文未提供","power":"原文未提供","topology":"原文未提供","device":"原文未提供","switching_frequency":"原文未提供","efficiency":"原文未提供","power_density":"原文未提供","isolation":"原文未提供","control":"原文未提供","application":"原文未提供"}',
    '"technical":{}', 1)
text = text.replace('"industrialization":{"stage":"未知","status":"","target":""}', '"industrialization":{}', 1)
text = text.replace('"evidence":{"confirmed_facts":[],"source_claims":[],"inferences":[],"unknowns":[]}', '"evidence":{"confirmed_facts":[],"source_claims":[],"inferences":[]}', 1)
text = text.replace('"max_tokens": 12000', '"max_tokens": 24000', 1)

# Ensure AI cannot invent a source/date/type that was not in the collected event.
text = text.replace(
    '    e["primary_source"] = base.get("primary_source", e.get("primary_source", ""))',
    '    e["primary_source"] = base.get("primary_source", e.get("primary_source", ""))\n    e["published_at"] = base.get("published_at", e.get("published_at", ""))\n    e["source_type"] = base.get("source_type", e.get("source_type", "国际资讯"))',
    1)

exec(compile(text, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
