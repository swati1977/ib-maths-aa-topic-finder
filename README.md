# IB Maths AA Topic Finder

A static question bank for browsing Mathematics: Analysis and Approaches SL past-paper questions by year, session, paper, timezone and topic.

**Live site:** https://swati1977.github.io/ib-maths-aa-topic-finder/

## What it does

- indexes reviewed English AA SL Paper 1 and Paper 2 questions from 2022–2026
- supports multiple topic labels per question
- filters by year, session, paper, timezone/zone, topic and full-question text search
- displays the complete accessible question transcription as the main card content
- opens the source PDF at the mapped question page from “View exact question” when available, and otherwise opens its source record
- reveals concise independent worked solutions, formatted by question part
- checks 2022–2025 solutions against the matching official markscheme while keeping the wording independent

## Important content note

The user confirmed permission to reproduce the question content used by this project. The repository excludes full source PDFs, markscheme PDFs and extraction/OCR dumps. It contains reviewed accessible transcriptions, classifications, source references and independently prepared solutions. It is not affiliated with or endorsed by the International Baccalaureate Organization, and the solutions are not official IB markschemes.

The available Paper 2 Zone A scan ends at page 11, so its final 15-mark question is not indexed. Nothing was guessed or reconstructed.

## Build the data

```bash
uv run --with pymupdf --with pillow --with numpy python scripts/build_question_crops.py
python3 scripts/build_data.py
python3 scripts/validate_bank.py
```

## Run locally

```bash
python3 -m http.server 8000 --directory site
```

Then open http://localhost:8000.

## Structure

- `site/` — static website
- `data/*.json` and `data/papers/*.json` — reviewed per-paper metadata, accessible text and solutions
- `scripts/build_data.py` — validates and merges paper data
- `data/source-manifest-2022-2025.json` — verified source/markscheme manifest
- `data/raw/` and `data/extracted/` — local ingestion artifacts, ignored by Git
