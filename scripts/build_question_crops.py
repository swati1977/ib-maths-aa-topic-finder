#!/usr/bin/env python3
"""Render permission-approved, question-only page images for the static site."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageChops, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RECOVERED_P2A = DATA_DIR / "extracted" / "p2-a-pages"
OUTPUT_DIR = ROOT / "site" / "questions"
PAPERS = ("p1-a", "p1-c", "p2-a", "p2-c")
MAX_WIDTH = 1400


def red_ink_removed(image: Image.Image) -> Image.Image:
    """Remove red-dominant annotations while preserving black printed content."""
    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    strongest_non_red = ImageChops.lighter(green, blue)
    red_dominance = ImageChops.subtract(red, strongest_non_red)
    mask = red_dominance.point(lambda value: 255 if value > 8 else 0)
    mask = mask.filter(ImageFilter.MaxFilter(5))
    cleaned = rgb.copy()
    cleaned.paste((255, 255, 255), mask=mask)
    gray = ImageOps.autocontrast(ImageOps.grayscale(cleaned), cutoff=0.2)
    return Image.merge("RGB", (gray, gray, gray))


def normalize_page(image: Image.Image, *, remove_red: bool) -> Image.Image:
    image = image.convert("RGB")
    if remove_red:
        image = red_ink_removed(image)
    else:
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=0.2)
        image = Image.merge("RGB", (gray, gray, gray))
    if image.width > MAX_WIDTH:
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
    return image


def crop_answer_area(image: Image.Image) -> Image.Image:
    """Crop at the first wide answer-box rule while retaining the full question."""
    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    x0, x1 = int(width * 0.04), int(width * 0.96)
    dark = gray[:, x0:x1] < 180
    window = max(12, height // 120)
    best_score = 0.0
    best_y: int | None = None
    for y in range(int(height * 0.16), int(height * 0.86) - window):
        occupied_columns = np.any(dark[y : y + window], axis=0)
        padded = np.concatenate(([False], occupied_columns, [False])).astype(np.int8)
        changes = np.diff(padded)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        longest_run = int((ends - starts).max()) if len(starts) else 0
        score = longest_run / len(occupied_columns)
        if score > best_score:
            best_score = score
            best_y = y
    if best_y is None or best_score < 0.72:
        return image
    bottom = min(height, max(int(height * 0.2), best_y + window))
    return image.crop((0, 0, width, bottom))


def render_pdf_page(document: pymupdf.Document, page_number: int) -> Image.Image:
    page = document.load_page(page_number - 1)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def load_recovered_page(page_number: int) -> Image.Image:
    path = RECOVERED_P2A / f"page-{page_number:02d}.jpg"
    if not path.is_file():
        raise FileNotFoundError(f"Missing recovered Paper 2 Zone A page: {path}")
    return Image.open(path)


def build(*, clean: bool = True) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected: set[Path] = set()
    generated = 0

    for paper_name in PAPERS:
        payload = json.loads((DATA_DIR / f"{paper_name}.json").read_text(encoding="utf-8"))
        document = None if paper_name == "p2-a" else pymupdf.open(RAW_DIR / f"{paper_name}.pdf")
        try:
            for question in payload["questions"]:
                display_pages = question.get("display_pages", question["pages"])
                for page_number in display_pages:
                    target = OUTPUT_DIR / f"{question['id']}-page-{page_number}.webp"
                    expected.add(target)
                    source = (
                        load_recovered_page(page_number)
                        if paper_name == "p2-a"
                        else render_pdf_page(document, page_number)
                    )
                    normalized = normalize_page(source, remove_red=paper_name == "p1-a")
                    crop_overrides = question.get("crop_bottom_fractions", {})
                    crop_fraction = crop_overrides.get(str(page_number))
                    if crop_fraction is not None:
                        crop_fraction = float(crop_fraction)
                        if not 0.2 <= crop_fraction <= 1.0:
                            raise ValueError(f"Invalid crop fraction for {question['id']} page {page_number}")
                        question_only = normalized.crop(
                            (0, 0, normalized.width, round(normalized.height * crop_fraction))
                        )
                    else:
                        question_only = crop_answer_area(normalized)
                    question_only.save(target, "WEBP", quality=88, method=6)
                    generated += 1
        finally:
            if document is not None:
                document.close()

    if clean:
        for stale in OUTPUT_DIR.glob("*.webp"):
            if stale not in expected:
                stale.unlink()

    print(f"Generated {generated} question page images in {OUTPUT_DIR}")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-clean", action="store_true", help="Keep stale generated images")
    args = parser.parse_args()
    build(clean=not args.no_clean)


if __name__ == "__main__":
    main()
