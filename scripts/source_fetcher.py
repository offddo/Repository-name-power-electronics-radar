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

def fetch_source(url, max_chars=9000):
    if not url or url.startswith("mailto:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"})
        r.raise_for_status()
        content_type = r.headers.get("content-type", "").lower()
        # Never treat PDFs/binary documents as article text. PDF bytes can look like
        # mojibake when decoded as UTF-8 and must not enter AI grounding/history.
        if "text/html" not in content_type or "application/pdf" in content_type or r.content[:5] == b"%PDF-":
            return ""
        parser = TextParser()
        parser.feed(r.text[:3000000])
        text = clean_text(" ".join(parser.parts))
        if len(text) < 500:
            return ""
        text = re.sub(r"(?:cookie|privacy policy|subscribe|sign in|all rights reserved)\b[^.。]{0,220}", " ", text, flags=re.I)
        return clean_text(text)[:max_chars]
    except Exception as exc:
        print("Source fetch failed:", url, repr(exc))
        return ""

def _paper_matches(title, abstract, keywords):
    hay = (title + " " + abstract).lower()
    return any(k.lower() in hay for k in keywords)

def _crossref_items(params):
    r = requests.get("https://api.crossref.org/works", params=params, timeout=15, headers={"User-Agent": "PowerElectronicsRadar/1.0 (mailto:radar@example.com)"})
    r.raise_for_status()
    return r.json().get("message", {}).get("items", [])

def _make_paper(x, journal, keywords):
    title = clean_text(" ".join(x.get("title") or []))
    containers = [clean_text(v) for v in (x.get("container-title") or [])]
    if not title or not any(journal.lower() in c.lower() or c.lower() in journal.lower() for c in containers):
        return None
    abstract = clean_text(x.get("abstract", ""))
    if not _paper_matches(title, abstract, keywords):
        return None
    parts = ((x.get("published") or x.get("published-print") or x.get("published-online") or {}).get("date-parts") or [[]])[0]
    date = "-".join(str(v).zfill(2) if i else str(v) for i, v in enumerate(parts[:3])) if parts else ""
    link = x.get("URL") or (("https://doi.org/" + x.get("DOI")) if x.get("DOI") else "")
    if not link or not abstract:
        return None
    return {
        "source": containers[0] if containers else journal,
        "source_type": "国内论文",
        "title": title,
        "summary": abstract[:5000],
        "link": link,
        "published_at": date + "T00:00:00+00:00" if date else "",
        "score": 96,
        "paper": True
    }

def crossref_papers(journal_names, keywords, since="2026-01-01", rows=20):
    """Discover domestic papers using two Crossref strategies.

    Strategy 1 queries the journal container directly. Some Chinese journals have sparse
    container metadata in Crossref, so Strategy 2 searches journal+keyword bibliographic
    combinations and then applies the same strict journal/title/abstract checks.
    """
    items = []
    for journal in journal_names:
        try:
            params = {
                "query.container-title": journal,
                "filter": f"from-pub-date:{since}",
                "rows": rows,
                "select": "DOI,title,container-title,published,published-print,published-online,URL,abstract"
            }
            for x in _crossref_items(params):
                paper = _make_paper(x, journal, keywords)
                if paper:
                    items.append(paper)
        except Exception as exc:
            print("Crossref container error:", journal, repr(exc))

        # Fallback: Crossref's container-title index is often incomplete for Chinese journals.
        # Search several high-value technical terms against the bibliographic index instead.
        for keyword in keywords[:6]:
            try:
                params = {
                    "query.bibliographic": f"{journal} {keyword}",
                    "filter": f"from-pub-date:{since}",
                    "rows": max(8, rows // 2),
                    "select": "DOI,title,container-title,published,published-print,published-online,URL,abstract"
                }
                for x in _crossref_items(params):
                    paper = _make_paper(x, journal, keywords)
                    if paper:
                        items.append(paper)
            except Exception as exc:
                print("Crossref fallback error:", journal, keyword, repr(exc))

    out, seen = [], set()
    for x in sorted(items, key=lambda v: v.get("published_at", ""), reverse=True):
        key = (x.get("link") or "").lower() or x["title"].lower()
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out
