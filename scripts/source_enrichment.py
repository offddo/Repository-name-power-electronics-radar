import html
import re
from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None

UA = "Mozilla/5.0 PowerElectronicsRadar/1.0"
TIMEOUT = 12
MAX_BODY = 14000

RELEVANT = [
    "电力电子", "构网型", "构网", "变流器", "储能变流器", "SiC", "GaN",
    "碳化硅", "氮化镓", "阻抗", "振荡", "虚拟同步", "STATCOM", "SST",
    "固态变压器", "DAB", "CLLC", "LLC", "800V", "宽禁带", "磁性元件",
]

# Google News is used only as a discovery index. An item becomes a domestic paper
# only after its URL resolves to the official journal domain and the official page
# itself can be fetched. This prevents fabricated paper records.
PAPER_FEEDS = [
    ("电力电子技术", "site:dldz.cbpt.cnki.net (构网型 OR SiC OR GaN OR DAB OR CLLC OR LLC OR 变流器)", "dldz.cbpt.cnki.net"),
    ("电力自动化设备", "site:epae.cn (构网型 OR SiC OR GaN OR 变流器 OR STATCOM)", "epae.cn"),
    ("电力系统自动化", "site:aeps-info.com (构网型 OR SiC OR GaN OR 变流器)", "aeps-info.com"),
    ("电工技术学报", "site:castjournals.cast.org.cn (SiC OR GaN OR 电力电子 OR 变流器)", "castjournals.cast.org.cn"),
    ("中国电机工程学报", "site:cjepe.com.cn (构网型 OR SiC OR GaN OR 电力电子)", "cjepe.com.cn"),
]


def clean_text(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_html(url):
    if not url or not url.startswith(("http://", "https://")):
        return "", ""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA}, allow_redirects=True)
        r.raise_for_status()
        return r.url, r.text
    except Exception as exc:
        print("source fetch failed:", url, repr(exc))
        return url, ""


def extract_text(raw):
    if not raw:
        return ""
    raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", raw, flags=re.I | re.S)
    blocks = re.findall(r"<(?:article|main|section)[^>]*>(.*?)</(?:article|main|section)>", raw, flags=re.I | re.S)
    candidates = blocks + re.findall(r"<p[^>]*>(.*?)</p>", raw, flags=re.I | re.S)
    texts = []
    for block in candidates:
        t = clean_text(re.sub(r"<[^>]+>", " ", block))
        if len(t) >= 45:
            texts.append(t)
    if not texts:
        return clean_text(re.sub(r"<[^>]+>", " ", raw))[:MAX_BODY]
    out, seen = [], set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return "\n".join(out)[:MAX_BODY]


def fetch_source_text(url):
    final_url, raw = fetch_html(url)
    return final_url, extract_text(raw)


def parse_cn_date(text):
    m = re.search(r"(?:出版日期|发布时间|出版时间|网络发布时间)\s*[:：]\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})", text or "")
    if m:
        return m.group(1).replace(".", "-").replace("/", "-") + "T00:00:00+08:00"
    m = re.search(r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})", text or "")
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}T00:00:00+08:00"
    return ""


def relevant(text):
    t = (text or "").lower()
    return sum(1 for k in RELEVANT if k.lower() in t) >= 2


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
            print("Google News decode failed:", repr(exc))
    try:
        r = requests.get(resolved, timeout=8, allow_redirects=True, headers={"User-Agent": UA})
        if r.url and "news.google.com" not in r.url:
            resolved = r.url
    except Exception:
        pass
    return resolved


def google_feed_url(query):
    from urllib.parse import quote_plus
    return "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"


def collect_domestic_papers():
    """Discover domestic papers through Google News, but keep only verified official pages."""
    events = []
    seen = set()
    for journal, query, domain in PAPER_FEEDS:
        try:
            feed = feedparser.parse(google_feed_url(query))
        except Exception as exc:
            print("paper RSS error:", journal, repr(exc))
            continue
        for item in feed.entries[:20]:
            title = clean_text(item.get("title", ""))
            if not title or not relevant(title):
                continue
            link = resolve_google(item.get("link", ""))
            if not link or domain not in link:
                continue
            final, body = fetch_source_text(link)
            if not body or domain not in (final or link):
                continue
            date = parse_cn_date(body)
            if not date:
                try:
                    date = parsedate_to_datetime(item.get("published", "")).astimezone(timezone.utc).isoformat()
                except Exception:
                    date = ""
            if not date:
                continue
            key = (title + "|" + (final or link)).lower()
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "source_type": "国内论文",
                "primary_source": journal,
                "published_at": date,
                "link": final or link,
                "summary_raw": body[:9000],
                "source_text": body[:12000],
                "sources": [],
                "score": 100,
                "paper": True,
            })
    return events


def enrich_events(events):
    for e in events:
        url = e.get("link", "")
        final, body = fetch_source_text(url)
        if final and final != url:
            e["link"] = final
        if body:
            e["source_text"] = body[:MAX_BODY]
            e["source_content_status"] = "full_or_article_text"
        else:
            e["source_content_status"] = "rss_only"

    papers = collect_domestic_papers()
    existing_titles = {clean_text(e.get("title", "")).lower() for e in events}
    for paper in papers:
        key = paper["title"].lower()
        if key not in existing_titles:
            events.append(paper)
            existing_titles.add(key)
    print("Verified domestic papers collected:", sum(1 for e in papers if e.get("source_type") == "国内论文"))
    return events
