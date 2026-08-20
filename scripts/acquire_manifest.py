#!/usr/bin/env python3
"""Download and validate question/markscheme PDFs from a source manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pymupdf

from ingestion_paths import safe_output_path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "source-manifest-2022-2025.json"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "2022-2025"


def download(url: str, target: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Not a PDF: {url} ({content_type}, {len(data)} bytes)")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    with pymupdf.open(target) as document:
        pages = len(document)
        if pages < 1:
            raise ValueError(f"Zero-page PDF: {url}")
    return {
        "path": str(target),
        "bytes": len(data),
        "pages": pages,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def download_first(urls: list[str], target: Path) -> dict:
    errors = []
    for url in [value for value in urls if value]:
        try:
            result = download(url, target)
            result["source_url"] = url
            return result
        except Exception as error:  # try the next verified mirror
            errors.append(f"{url}: {error}")
    raise RuntimeError("All verified PDF sources failed: " + " | ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = []
    for paper in payload["papers"]:
        tasks.append((paper, "question", [
            paper["question_pdf_url"], paper.get("alternate_question_pdf_url")
        ]))
        if paper.get("markscheme_pdf_url"):
            tasks.append((paper, "markscheme", [
                paper["markscheme_pdf_url"], paper.get("alternate_markscheme_pdf_url")
            ]))

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for paper, kind, urls in tasks:
            target = safe_output_path(args.output, paper["id"], f"-{kind}.pdf")
            futures[executor.submit(download_first, urls, target)] = (paper, kind)
        for future in as_completed(futures):
            paper, kind = futures[future]
            key = f"{paper['id']}:{kind}"
            results[key] = future.result()
            print(f"{key}: {results[key]['pages']} pages, {results[key]['bytes']} bytes")

    report = args.output / "download-report.json"
    report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded and validated {len(results)} PDFs; report: {report}")


if __name__ == "__main__":
    main()
