# IB Maths Topic Finder

A static question bank for browsing Mathematics SL (2017–2020) and Mathematics: Analysis and Approaches SL (2021–2026) past-paper questions by course, year, session, paper, timezone and topic.

**Live site:** https://swati1977.github.io/ib-maths-aa-topic-finder/

## What it does

- indexes reviewed English Mathematics SL and AA SL Paper 1/2 questions from 2017–2026
- supports multiple topic labels per question
- filters by year, session, paper, timezone/zone, topic and full-question text search
- displays the complete accessible question transcription with actual source diagrams/tables
- opens a locked question-only image panel from “View exact question”, with the original source linked separately
- exports current filtered matches to PDF as questions, solutions, or both, using clean text or original question images
- uses verified IB Docs sources with Publit mirrors as acquisition fallbacks
- reveals concise independent worked solutions, formatted by question part
- checks 2017–2025 solutions against the matching official markscheme while keeping the wording independent

## Important content note

The user confirmed permission to reproduce the question content used by this project. The repository excludes full source PDFs, markscheme PDFs and extraction/OCR dumps. It contains reviewed accessible transcriptions, classifications, source references and independently prepared solutions. It is not affiliated with or endorsed by the International Baccalaureate Organization, and the solutions are not official IB markschemes.

The primary May 2026 Paper 2 Zone A scan ends at page 11. Question 9 is restored from the complete verified alternate source text and is explicitly labelled as a reconstruction because the alternate host did not permit original page-image retrieval.

## Build the data

```bash
uv run --with pillow python scripts/build_verified_reconstructions.py
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
- `data/source-manifest-2017-2021.json`, `data/source-manifest-2022-2025.json`, and `data/source-manifest-2026.json` — verified multi-source manifests
- `site/vendor/` — vendored jsPDF and DejaVu Sans with license files for browser-side PDF generation
- `data/raw/` and `data/extracted/` — local ingestion artifacts, ignored by Git
