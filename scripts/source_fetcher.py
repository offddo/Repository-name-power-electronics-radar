import html
import re
import requests
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; PowerElectronicsRadar/1.0)"

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form"} and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if self.skip:
            return
        s = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if s:
            self.parts.append(s)

def clean_text(text):
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip()

def fetch_source(url, max_chars=6000):
    if not url or url.startswith("mailto:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=7, allow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.7"})
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type", ""):
            return ""
        parser = TextParser()
        parser.feed(r.text[:2000000])
        text = clean_text(" ".join(parser.parts))
        if len(text) < 500:
            return ""
        text = re.sub(r"(?:cookie|privacy policy|subscribe|sign in|menu)\b[^.]{0,180}", " ", text, flags=re.I)
        return clean_text(text)[:max_chars]
    except Exception as exc:
        print("Source fetch failed:", url, repr(exc))
        return ""

def crossref_papers(journal_names, keywords, since="2026-01-01", rows=8):
    items = []
    for journal in journal_names:
        for query in keywords:
            try:
                params = {"query.container-title": journal, "query.bibliographic": query, "filter": f"from-pub-date:{since}", "rows": rows, "select": "DOI,title,container-title,published,URL,abstract"}
                r = requests.get("https://api.crossref.org/works", params=params, timeout=12, headers={"User-Agent": "PowerElectronicsRadar/1.0"})
                r.raise_for_status()
                for x in r.json().get("message", {}).get("items", []):
                    title = clean_text(" ".join(x.get("title") or []))
                    containers = [clean_text(v) for v in (x.get("container-title") or [])]
                    if not title or not any(journal.lower() in c.lower() for c in containers):
                        continue
                    hay = (title + " " + clean_text(x.get("abstract", ""))).lower()
                    if not any(k.lower() in hay for k in keywords):
                        continue
                    parts = ((x.get("published") or {}).get("date-parts") or [[]])[0]
                    date = "-".join(str(v).zfill(2) if i else str(v) for i, v in enumerate(parts[:3])) if parts else ""
                    link = x.get("URL") or (("https://doi.org/" + x.get("DOI")) if x.get("DOI") else "")
                    items.append({"source": containers[0] if containers else journal, "source_type": "国内论文", "title": title, "summary": clean_text(x.get("abstract", ""))[:5000], "link": link, "published_at": date + "T00:00:00+00:00" if date else "", "score": 94, "paper": True})
            except Exception as exc:
                print("Crossref error:", journal, query, repr(exc))
    out, seen = [], set()
    for x in items:
        key = (x.get("link") or "").lower() or x["title"].lower()
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out
