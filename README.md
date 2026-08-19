# IB Maths AA Topic Finder

A static prototype for browsing Mathematics: Analysis and Approaches SL past-paper questions by topic, paper and examination zone.

## What it does

- indexes four May 2026 AA SL papers (Papers 1 and 2, Zones A and C)
- supports multiple topic labels per question
- filters by topic, paper, zone and text search
- reveals concise independent worked solutions
- links every item back to its source paper

## Important content note

This repository intentionally excludes the source PDFs and question-page images. The index contains short original summaries, classifications and independently prepared solutions. It is not affiliated with or endorsed by the International Baccalaureate Organization, and the solutions are not official IB markschemes.

## Build the data

```bash
python3 scripts/build_data.py
```

## Run locally

```bash
python3 -m http.server 8000 --directory site
```

Then open http://localhost:8000.

## Structure

- `site/` — static website
- `data/*.json` — reviewed per-paper metadata and solutions
- `scripts/build_data.py` — validates and merges paper data
- `data/raw/` and `data/extracted/` — local ingestion artifacts, ignored by Git
