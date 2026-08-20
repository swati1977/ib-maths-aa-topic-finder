#!/usr/bin/env python3
"""Render deterministic, question-only WebP assets for the static site."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np
import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RECOVERED_P2A = DATA_DIR / "extracted" / "p2-a-pages"
OUTPUT_DIR = ROOT / "site" / "questions"
LEGACY_PAPERS = ("p1-a", "p1-c", "p2-a", "p2-c")
MAX_WIDTH = 1400
HEADING_RE = re.compile(r"^\s*(\d+)\.\s*\[Maximum\s+marks?\s*:", re.IGNORECASE)
CONTINUED_RE = re.compile(r"question\s+\d+\s+continued", re.IGNORECASE)


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    payload: dict
    pdf_path: Path | None
    legacy: bool = False
    recovered_pages: bool = False


@dataclass(frozen=True)
class PageJob:
    paper: PaperSpec
    question: dict
    page_number: int
    continuation: bool


def discover_papers(root: Path = ROOT) -> list[PaperSpec]:
    """Discover the complete current bank, retaining the four 2026 sources."""
    data_dir = root / "data"
    specs: list[PaperSpec] = []
    for path in sorted((data_dir / "papers").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        paper_id = payload["paper"]["id"]
        raw_group = "2017-2021" if int(payload["paper"]["year"]) <= 2021 else "2022-2025"
        pdf_path = data_dir / "raw" / raw_group / f"{paper_id}-question.pdf"
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Missing question PDF for {paper_id}: {pdf_path}")
        specs.append(PaperSpec(paper_id, payload, pdf_path))
    for paper_id in LEGACY_PAPERS:
        payload = json.loads((data_dir / f"{paper_id}.json").read_text(encoding="utf-8"))
        recovered = paper_id == "p2-a"
        pdf_path = None if recovered else data_dir / "raw" / f"{paper_id}.pdf"
        if pdf_path is not None and not pdf_path.is_file():
            raise FileNotFoundError(f"Missing legacy question PDF: {pdf_path}")
        specs.append(PaperSpec(paper_id, payload, pdf_path, legacy=True, recovered_pages=recovered))
    return sorted(specs, key=lambda spec: spec.paper_id)


def question_page_jobs(papers: list[PaperSpec]) -> Iterator[PageJob]:
    for paper in papers:
        for question in paper.payload["questions"]:
            display_pages = question.get("display_pages", question["pages"])
            for index, page_number in enumerate(display_pages):
                yield PageJob(paper, question, page_number, continuation=index > 0)


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
    """Legacy raster fallback: stop at the first wide answer-box rule."""
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


def _is_answer_area(text: str) -> bool:
    # compact without spaces to catch underscore and glyph patterns
    compact = "".join(text.split())
    return (
        compact.count("_") >= 20
        or compact.count("\ufffd") >= 20
        or compact.count("\x08") + compact.count("\uf0a3") >= 10
        # dotted answer pages: a single block of ". . . ." segments (IB answer-booklet pattern)
        or _block_is_dotted_answer(text)
    )


def _block_is_dotted_answer(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) < 10:
        return False
    # Count how many chars are dot/space vs non-dot
    dot_chars = stripped.count(".") + stripped.count("·")
    # If more than half the non-space characters are dots, treat as answer area
    nonspace = stripped.replace(" ", "")
    return len(nonspace) >= 5 and dot_chars >= len(nonspace) * 0.7


def _validated_fraction(value: object) -> float:
    fraction = float(value)
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"Invalid crop fraction: {value}")
    return fraction


def _is_page_furniture(text: str) -> bool:
    normalized = " ".join(text.split())
    return bool(
        CONTINUED_RE.search(normalized)
        or re.fullmatch(r"[–-]\s*\d+\s*[–-].*", normalized)
        or re.fullmatch(r"\d+EP\d+", normalized)
        or normalized in {"Turn over", "Do not write solutions on this page."}
    )


def _substantive_blocks(text_blocks: list[tuple[pymupdf.Rect, str]]) -> list[pymupdf.Rect]:
    return [
        rect
        for rect, text in text_blocks
        if 55 < rect.y0 < 780 and not _is_answer_area(text) and not _is_page_furniture(text)
    ]


def page_has_question_content(page: pymupdf.Page, *, continuation: bool) -> bool:
    if not continuation:
        return True
    blocks = [(pymupdf.Rect(*b[:4]), b[4].strip()) for b in page.get_text("blocks") if b[4].strip()]
    return bool(_substantive_blocks(blocks))


def content_crop_rect(
    page: pymupdf.Page,
    *,
    question_number: int,
    continuation: bool,
    override: dict | None = None,
) -> pymupdf.Rect:
    """Find a stable vertical crop using PDF text geometry, without OCR."""
    height = page.rect.height
    blocks = sorted(page.get_text("blocks"), key=lambda block: (block[1], block[0]))
    text_blocks = [(pymupdf.Rect(*block[:4]), block[4].strip()) for block in blocks if block[4].strip()]

    heading: pymupdf.Rect | None = None
    next_heading: pymupdf.Rect | None = None
    for rect, text in text_blocks:
        match = HEADING_RE.match(" ".join(text.split()))
        if not match:
            continue
        number = int(match.group(1))
        if number == question_number and heading is None:
            heading = rect
        elif heading is not None and rect.y0 > heading.y0:
            next_heading = rect
            break

    substantive = _substantive_blocks(text_blocks)
    if continuation:
        top = (substantive[0].y0 if substantive else 60.0) - 10.0
    elif heading is not None:
        top = heading.y0 - 10.0
    else:
        # A malformed text layer should remain usable and auditable, not lose content.
        top = 50.0

    candidates: list[float] = []
    if next_heading is not None:
        candidates.append(next_heading.y0 - 10.0)
    search_after = heading.y1 if heading is not None else (
        substantive[0].y1 if substantive else top
    )
    for rect, text in text_blocks:
        if rect.y0 > search_after and _is_answer_area(text):
            candidates.append(rect.y0)
            break
    bottom = min(candidates) if candidates else height - 35.0

    override = override or {}
    if "top" in override:
        top = height * _validated_fraction(override["top"])
    if "bottom" in override:
        bottom = height * _validated_fraction(override["bottom"])
    top = max(0.0, top)
    bottom = min(height, bottom)
    if bottom <= top + 20:
        raise ValueError(
            f"Invalid crop bounds for question {question_number}: top={top:.1f}, bottom={bottom:.1f}"
        )
    return pymupdf.Rect(0, top, page.rect.width, bottom)


def render_pdf_page(
    document: pymupdf.Document, page_number: int, clip: pymupdf.Rect | None = None
) -> Image.Image:
    page = document.load_page(page_number - 1)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def load_recovered_page(page_number: int, root: Path = ROOT) -> Image.Image:
    path = root / "data" / "extracted" / "p2-a-pages" / f"page-{page_number:02d}.jpg"
    if not path.is_file():
        raise FileNotFoundError(f"Missing recovered Paper 2 Zone A page: {path}")
    return Image.open(path)


def atomic_save_webp(image: Image.Image, target: Path) -> None:
    """Encode and validate beside the target, then atomically replace it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w+b") as file_object:
            image.save(file_object, "WEBP", quality=88, method=6, exact=True)
            file_object.flush()
            os.fsync(file_object.fileno())
        if temporary.stat().st_size == 0:
            raise OSError(f"Encoded empty WebP for {target.name}")
        with Image.open(temporary) as check:
            check.verify()
        os.replace(temporary, target)
    except Exception:
        # fdopen owns descriptor after success; close it if image.save failed early.
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def _page_override(question: dict, page_number: int) -> dict:
    override = dict(question.get("crop_fractions", {}).get(str(page_number), {}))
    old_bottom = question.get("crop_bottom_fractions", {}).get(str(page_number))
    if old_bottom is not None:
        override["bottom"] = old_bottom
    return override


def _legacy_question_image(job: PageJob, document: pymupdf.Document | None, root: Path) -> Image.Image:
    source = (
        load_recovered_page(job.page_number, root)
        if job.paper.recovered_pages
        else render_pdf_page(document, job.page_number)  # type: ignore[arg-type]
    )
    normalized = normalize_page(source, remove_red=job.paper.paper_id == "p1-a")
    override = _page_override(job.question, job.page_number)
    if "bottom" in override:
        fraction = _validated_fraction(override["bottom"])
        if fraction < 0.2:
            raise ValueError(
                f"Invalid crop fraction for {job.question['id']} page {job.page_number}"
            )
        return normalized.crop((0, 0, normalized.width, round(normalized.height * fraction)))
    return crop_answer_area(normalized)


def build(*, clean: bool = True, root: Path = ROOT, years: set[int] | None = None) -> int:
    output_dir = root / "site" / "questions"
    output_dir.mkdir(parents=True, exist_ok=True)
    expected: set[Path] = set()
    generated = 0
    papers = discover_papers(root)
    if years:
        papers = [paper for paper in papers if int(paper.payload["paper"]["year"]) in years]

    for paper in papers:
        document = None if paper.recovered_pages else pymupdf.open(paper.pdf_path)
        try:
            for job in question_page_jobs([paper]):
                target = output_dir / f"{job.question['id']}-page-{job.page_number}.webp"
                if job.question.get("image_status") == "verified reconstruction":
                    expected.add(target)
                    if not target.is_file() or target.stat().st_size == 0:
                        raise FileNotFoundError(f"Missing verified reconstruction asset: {target}")
                    continue
                if paper.legacy:
                    expected.add(target)
                    question_only = _legacy_question_image(job, document, root)
                else:
                    page = document.load_page(job.page_number - 1)  # type: ignore[union-attr]
                    if not page_has_question_content(page, continuation=job.continuation):
                        continue
                    expected.add(target)
                    clip = content_crop_rect(
                        page,
                        question_number=int(job.question["number"]),
                        continuation=job.continuation,
                        override=_page_override(job.question, job.page_number),
                    )
                    source = render_pdf_page(document, job.page_number, clip)  # type: ignore[arg-type]
                    question_only = normalize_page(source, remove_red=False)
                atomic_save_webp(question_only, target)
                generated += 1
        finally:
            if document is not None:
                document.close()

    if clean:
        for stale in output_dir.glob("*.webp"):
            if stale not in expected:
                stale.unlink()

    print(f"Generated {generated} question page images in {output_dir}")
    return generated


def audit(*, root: Path = ROOT, audit_dir: Path, years: set[int] | None = None) -> dict:
    """Write machine-readable crop checks and a contact sheet of suspicious assets."""
    output_dir = root / "site" / "questions"
    expected: dict[Path, PageJob] = {}
    omitted_answer_only: list[str] = []
    papers = discover_papers(root)
    if years:
        papers = [paper for paper in papers if int(paper.payload["paper"]["year"]) in years]
    for paper in papers:
        document = None if paper.recovered_pages else pymupdf.open(paper.pdf_path)
        try:
            for job in question_page_jobs([paper]):
                name = f"{job.question['id']}-page-{job.page_number}.webp"
                if job.question.get("image_status") == "verified reconstruction":
                    expected[output_dir / name] = job
                    continue
                if (
                    not paper.legacy
                    and not page_has_question_content(
                        document.load_page(job.page_number - 1),  # type: ignore[union-attr]
                        continuation=job.continuation,
                    )
                ):
                    omitted_answer_only.append(name)
                    continue
                expected[output_dir / name] = job
        finally:
            if document is not None:
                document.close()
    missing = [path.name for path in expected if not path.is_file()]
    records = []
    hashes: dict[str, list[str]] = defaultdict(list)
    for path in sorted(expected):
        if not path.is_file():
            continue
        with Image.open(path) as image:
            width, height = image.size
        ratio = height / width
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[digest].append(path.name)
        reasons = []
        if ratio < 0.12:
            reasons.append("too-short")
        if ratio > 1.35:
            reasons.append("too-tall")
        if reasons:
            records.append({"file": path.name, "width": width, "height": height, "reasons": reasons})
    identical = [names for names in hashes.values() if len(names) > 1]
    for names in identical:
        for name in names:
            records.append({"file": name, "reasons": ["identical"]})

    audit_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "expected": len(expected),
        "present": len(expected) - len(missing),
        "missing": missing,
        "omitted_answer_only": omitted_answer_only,
        "suspicious": records,
        "identical_groups": identical,
    }
    (audit_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    suspicious_names = sorted({record["file"] for record in records})
    if suspicious_names:
        thumb_w, thumb_h, label_h, columns = 280, 396, 34, 4
        rows = (len(suspicious_names) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), "white")
        draw = ImageDraw.Draw(sheet)
        for index, name in enumerate(suspicious_names):
            with Image.open(output_dir / name) as image:
                tile = ImageOps.contain(image.convert("RGB"), (thumb_w, thumb_h))
            x = (index % columns) * thumb_w
            y = (index // columns) * (thumb_h + label_h)
            sheet.paste(tile, (x + (thumb_w - tile.width) // 2, y))
            draw.text((x + 4, y + thumb_h + 3), name[:43], fill="black")
        sheet.save(audit_dir / "suspicious-contact-sheet.webp", "WEBP", quality=88, method=6)
    print(
        f"Audit: {report['present']}/{report['expected']} present, "
        f"{len(records)} suspicious, {len(identical)} identical groups"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-clean", action="store_true", help="Keep stale generated images")
    parser.add_argument("--audit-dir", type=Path, help="Write crop audit report/contact sheet")
    parser.add_argument("--year", type=int, action="append", help="Limit generation to one or more years")
    args = parser.parse_args()
    years = set(args.year or [])
    build(clean=not args.no_clean and not years, years=years or None)
    if args.audit_dir:
        audit(audit_dir=args.audit_dir, years=years or None)


if __name__ == "__main__":
    main()
