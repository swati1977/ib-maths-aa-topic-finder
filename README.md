# IB Maths Topic Finder

A static question bank for browsing Mathematics SL (2017–2020) and Mathematics: Analysis and Approaches SL (2021–2026) past-paper questions by course, year, session, paper, timezone and topic.

**Live site:** https://swati1977.github.io/ib-maths-aa-topic-finder/

## What it does

- indexes reviewed English Mathematics SL and AA SL Paper 1/2 questions from 2017–2026
- supports multiple topic labels per question
- filters by year, session, paper, timezone/zone, topic and full-question text search
- displays the official question page image as the primary content, preserving the paper's exact mathematical layout
- shows question-specific official IB markscheme crops as the default answer, with a direct link to the exact full-document page
- falls back to an independent worked solution only when no official markscheme is available (currently 2026 papers)
- provides an accessible text transcript behind a collapsible toggle for searchability
- exports current filtered matches to PDF as questions, solutions, or both, using clean text or original question images
- uses verified IB Docs sources with Publit mirrors as acquisition fallbacks

## Important content note

The user confirmed permission to reproduce both question and markscheme content used by this project. The repository excludes full source PDFs, markscheme PDFs and extraction/OCR dumps. It contains original question-page crops, reviewed accessible transcripts, classifications, source references, and question-specific official IB markscheme crops for 2017–2025. The 2026 papers use independently prepared worked solutions because no official 2026 markschemes were available. The project is not affiliated with or endorsed by the International Baccalaureate Organization; only content explicitly labelled “Official IB markscheme” comes from an official markscheme.

The primary May 2026 Paper 2 Zone A scan ends at page 11. Question 9 is restored from the complete verified alternate source text and is explicitly labelled as a reconstruction because the alternate host did not permit original page-image retrieval. No official 2026 markschemes were available; the 2026 answers use independent worked solutions clearly labelled as such.

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
- `scripts/build_markscheme_crops.py` — builds and audits question-specific official markscheme crops
- `data/official-markscheme-images.json` — verified question-to-markscheme page/image mapping
- `data/source-manifest-2017-2021.json`, `data/source-manifest-2022-2025.json`, and `data/source-manifest-2026.json` — verified multi-source manifests
- `site/vendor/` — vendored jsPDF and DejaVu Sans with license files for browser-side PDF generation
- `data/raw/` and `data/extracted/` — local ingestion artifacts, ignored by Git
