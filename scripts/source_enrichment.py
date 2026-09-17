import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

import requests

UA = "Mozilla/5.0 PowerElectronicsRadar/1.0"
TIMEOUT = 12
MAX_BODY = 14000

RELEVANT = [
    "电力电子", "构网型", "构网", "变流器", "储能变流器", "SiC", "GaN",
    "碳化硅", "氮化镓", "阻抗", "振荡", "直驱风机", "虚拟同步", "STATCOM",
    "SST", "固态变压器", "DAB", "CLLC", "LLC", "800V", "宽禁带",
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
        t = re.sub(r"<[^>]+>", " ", block)
        t = clean_text(t)
        if len(t) >= 45:
            texts.append(t)
    if not texts:
        t = re.sub(r"<[^>]+>", " ", raw)
        return clean_text(t)[:MAX_BODY]
    seen = set()
    out = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return "\n".join(out)[:MAX_BODY]


def fetch_source_text(url):
    final_url, raw = fetch_html(url)
    text = extract_text(raw)
    return final_url, text


def parse_cn_date(text):
    m = re.search(r"出版日期\s*[:：]\s*(\d{4}-\d{1,2}-\d{1,2})", text or "")
    if m:
        return m.group(1) + "T00:00:00+08:00"
    m = re.search(r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})", text or "")
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}T00:00:00+08:00"
    return ""


def relevant(text):
    t = (text or "").lower()
    hits = sum(1 for k in RELEVANT if k.lower() in t)
    return hits >= 2


def collect_epae_papers():
    """Collect actual paper pages from the official 电力自动化设备 site, not Google News."""
    index = "https://www.epae.cn/dlzdhsb/ch/index.aspx"
    final_url, raw = fetch_html(index)
    if not raw:
        return []
    pairs = re.findall(r'href=[\"\']([^\"\']*view_abstract\.aspx[^\"\']*)[\"\'][^>]*>(.*?)</a>', raw, flags=re.I | re.S)
    events = []
    seen = set()
    for href, title_html in pairs:
        title = clean_text(re.sub(r"<[^>]+>", " ", title_html))
        if not title or title in seen or not relevant(title):
            continue
        link = html.unescape(href).replace("&amp;", "&")
        if link.startswith("/"):
            link = "https://www.epae.cn" + link
        elif link.startswith("./"):
            link = "https://www.epae.cn/dlzdhsb/ch/" + link[2:]
        elif not link.startswith("http"):
            link = "https://www.epae.cn/dlzdhsb/ch/reader/" + link
        final, body = fetch_source_text(link)
        if not body:
            continue
        date = parse_cn_date(body)
        if not date:
            date = parse_cn_date(title + " " + body[:3000])
        if not date:
            continue
        key = re.sub(r"\W+", "", title.lower())
        seen.add(title)
        events.append({
            "id": "cnpaper-" + key[:32],
            "title": title,
            "category": ["gfm", "pcs"] if any(k in title for k in ["构网", "变流器", "STATCOM"]) else ["power_electronics"],
            "source_type": "国内论文",
            "primary_source": "电力自动化设备",
            "published_at": date,
            "link": final or link,
            "summary_raw": body[:9000],
            "source_text": body[:12000],
            "sources": [],
            "score": 100,
        })
        if len(events) >= 20:
            break
    return events


def enrich_events(events):
    for e in events:
        url = e.get("link", "")
        final, body = fetch_source_text(url)
        if final and final != url:
            e["link"] = final
        if body:
            e["source_text"] = body[:MAX_BODY]
            # Keep the RSS summary as metadata; AI gets the fetched source as the factual basis.
            e["source_content_status"] = "full_or_article_text"
        else:
            e["source_content_status"] = "rss_only"
    papers = collect_epae_papers()
    existing_titles = {clean_text(e.get("title", "")).lower() for e in events}
    for p in papers:
        if p["title"].lower() not in existing_titles:
            events.append(p)
            existing_titles.add(p["title"].lower())
    return events
