"""Production runner for the power-electronics radar.

The runner enriches every candidate with source text before DeepSeek sees it,
then prioritizes verified domestic papers and the radar's core engineering topics.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import radar_impl
from source_enrichment import enrich_events

CORE_TOPICS = {
    "sst", "sic", "gan", "gfm", "pcs", "dab", "cllc", "llc", "800v", "magnetics"
}


def is_strongly_relevant(event):
    if event.get("source_type") in {"国内论文", "国际论文"}:
        return True
    cats = {str(x).lower() for x in (event.get("category") or [])}
    title = str(event.get("title", "")).lower()
    text = " ".join([
        title,
        str(event.get("summary_raw", "")),
        str(event.get("source_text", "")),
    ]).lower()
    if cats & CORE_TOPICS:
        return True
    # Do not let generic power-electronics/automotive stories crowd out the core radar.
    strong_terms = [
        "solid-state transformer", "solid state transformer", "grid-forming",
        "800v", "ai data center", "dual active bridge", "differential active bridge",
        "sic mosfet", "gan power", "wide-bandgap", "magnetics", "磁性元件",
        "构网型", "储能变流器", "固态变压器", "双有源桥", "谐振变换器",
    ]
    return any(term in text for term in strong_terms)


def main():
    original_collect = radar_impl.collect_events

    def collect_with_sources():
        events = original_collect()
        events = enrich_events(events)

        # Keep only strong topical matches for the daily radar, while always
        # retaining verified papers because they are a first-class research stream.
        events = [e for e in events if is_strongly_relevant(e)]
        events.sort(
            key=lambda e: (
                e.get("source_type") in {"国内论文", "国际论文"},
                e.get("score", 0),
                e.get("published_at", ""),
            ),
            reverse=True,
        )
        events = events[:36]
        for e in events:
            if e.get("source_text"):
                e["source_text"] = e["source_text"][:5000]
            elif e.get("summary_raw"):
                e["source_text"] = e["summary_raw"][:3500]
        print("Source-enriched strong events:", len(events))
        print("Domestic papers:", sum(1 for e in events if e.get("source_type") == "国内论文"))
        return events

    radar_impl.collect_events = collect_with_sources
    radar_impl.main()


if __name__ == "__main__":
    main()
