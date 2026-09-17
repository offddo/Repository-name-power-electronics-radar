"""Production runner for the power-electronics radar.

The old version modified source code as a string at runtime. This runner now
keeps the core implementation intact and enriches collected events with the
actual source text before DeepSeek sees them.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import radar_impl
from source_enrichment import enrich_events


def main():
    original_collect = radar_impl.collect_events

    def collect_with_sources():
        events = original_collect()
        events = enrich_events(events)

        # Keep the daily AI request within a predictable context window while
        # retaining enough article/abstract text to ground technical claims.
        events.sort(
            key=lambda e: (
                e.get("source_type") == "国内论文",
                e.get("score", 0),
                e.get("published_at", ""),
            ),
            reverse=True,
        )
        events = events[:30]
        for e in events:
            if e.get("source_text"):
                e["source_text"] = e["source_text"][:3500]
            elif e.get("summary_raw"):
                e["source_text"] = e["summary_raw"][:3500]
        print("Source-enriched events:", len(events))
        print("Domestic papers:", sum(1 for e in events if e.get("source_type") == "国内论文"))
        return events

    radar_impl.collect_events = collect_with_sources
    radar_impl.main()


if __name__ == "__main__":
    main()
