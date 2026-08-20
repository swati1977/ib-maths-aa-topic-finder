#!/usr/bin/env python3
"""Render manifest question papers into review pages and page-text JSON."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pymupdf
from PIL import Image

from ingestion_paths import safe_output_path, validate_paper_id

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source-manifest-2022-2025.json"
RAW = ROOT / "data" / "raw" / "2022-2025"
OUTPUT = ROOT / "data" / "extracted" / "2022-2025"


def prepare(paper: dict) -> tuple[str, int]:
    paper_id = validate_paper_id(paper["id"])
    source = safe_output_path(RAW, paper_id, "-question.pdf")
    target = safe_output_path(OUTPUT, paper_id)
    target.mkdir(parents=True, exist_ok=True)
    page_records = []
    with pymupdf.open(source) as document:
        for index, page in enumerate(document):
            number = index + 1
            text = page.get_text("text")
            page_records.append({"page": number, "text": text, "chars": len(text)})
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            image.save(target / f"page-{number:02d}.jpg", "JPEG", quality=82, optimize=True)
    (target / "pages.json").write_text(
        json.dumps({"paper": paper, "pages": page_records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return paper_id, len(page_records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    papers = json.loads(MANIFEST.read_text(encoding="utf-8"))["papers"]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(prepare, paper): paper["id"] for paper in papers}
        for future in as_completed(futures):
            paper_id, pages = future.result()
            print(f"{paper_id}: {pages} pages")
    print(f"Prepared {len(papers)} papers in {OUTPUT}")


if __name__ == "__main__":
    main()
