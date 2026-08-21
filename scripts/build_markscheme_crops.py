#!/usr/bin/env python3
"""Build deterministic, question-specific crops from official IB markschemes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pymupdf
from PIL import Image

try:
    from ingestion_paths import safe_output_path, validate_paper_id
except ModuleNotFoundError:  # imported as scripts.build_markscheme_crops
    from scripts.ingestion_paths import safe_output_path, validate_paper_id

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "site" / "markschemes"
MANIFEST_PATH = ROOT / "data" / "official-markscheme-images.json"
PAPER_ID_RE = re.compile(r"^[0-9]{4}-(?:may|november)-p[12]-tz(?:[123n])$")
CONTINUED_RE = re.compile(r"\bquestion\s+(\d+)(?:\s*\([^)]*\))?\s+continued\b", re.I)
DOCUMENT_CODE_RE = re.compile(r"(?:[MN]\d{2}/5/|\d{4}\s*[–-]\s*\d{4,}M)", re.I)


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    year: int
    payload: dict
    pdf_path: Path


@dataclass(frozen=True)
class TextLine:
    rect: pymupdf.Rect
    text: str


def resolve_markscheme_pdf(root: Path, paper: dict) -> Path:
    """Resolve one exact local PDF without permitting path traversal or fuzzy matches."""
    paper_id = str(paper["id"])
    if not PAPER_ID_RE.fullmatch(paper_id):
        raise ValueError(f"Unsafe paper id: {paper_id!r}")
    year = int(paper["year"])
    if year > 2025:
        raise ValueError(f"No official markscheme crop source for year {year}")
    group = "2017-2021" if year <= 2021 else "2022-2025"
    raw_root = (root / "data" / "raw").resolve()
    path = (raw_root / group / f"{paper_id}-markscheme.pdf").resolve()
    if raw_root not in path.parents:
        raise ValueError(f"Unsafe markscheme path for {paper_id}")
    if not path.is_file():
        raise FileNotFoundError(f"Missing markscheme PDF for {paper_id}: {path}")
    return path


def discover_papers(root: Path = ROOT) -> list[PaperSpec]:
    specs: list[PaperSpec] = []
    for path in sorted((root / "data" / "papers").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        paper = payload["paper"]
        year = int(paper["year"])
        if year > 2025:
            continue
        specs.append(PaperSpec(str(paper["id"]), year, payload, resolve_markscheme_pdf(root, paper)))
    return sorted(specs, key=lambda spec: spec.paper_id)


def _text_lines(page: pymupdf.Page) -> list[TextLine]:
    words = page.get_text("words", sort=True)
    grouped: dict[tuple[int, int], list[tuple]] = {}
    for word in words:
        grouped.setdefault((int(word[5]), int(word[6])), []).append(word)
    lines: list[TextLine] = []
    for words_in_line in grouped.values():
        ordered = sorted(words_in_line, key=lambda word: word[0])
        rect = pymupdf.Rect(
            min(word[0] for word in ordered), min(word[1] for word in ordered),
            max(word[2] for word in ordered), max(word[3] for word in ordered),
        )
        lines.append(TextLine(rect, " ".join(str(word[4]) for word in ordered).strip()))
    return sorted(lines, key=lambda line: (line.rect.y0, line.rect.x0))


def _heading_number(line: TextLine) -> int | None:
    if line.rect.x0 > 135:
        return None
    match = re.match(r"^\s*(\d+)\s*\.(?:\s|$)", line.text)
    return int(match.group(1)) if match else None


def _continued_number(line: TextLine) -> int | None:
    match = CONTINUED_RE.search(line.text)
    return int(match.group(1)) if match else None


def _is_furniture(line: TextLine, height: float) -> bool:
    text = " ".join(line.text.split())
    return bool(
        line.rect.y0 < 45
        or line.rect.y1 > height - 42
        or re.fullmatch(r"[–-]\s*\d+\s*[–-]", text)
        or DOCUMENT_CODE_RE.search(text)
        or text.lower() in {"turn over", "section a", "section b"}
    )


def _substantive_before(lines: list[TextLine], boundary: float, height: float) -> bool:
    return any(
        line.rect.y1 < boundary - 2.0
        and not _is_furniture(line, height)
        and _heading_number(line) is None
        and _continued_number(line) is None
        for line in lines
    )


def derive_question_pages(
    document: pymupdf.Document, question_number: int, stored_pages: Iterable[int]
) -> list[int]:
    """Correct stored physical pages using own/continued/next-question headings."""
    selected: list[int] = []
    started = False
    seen: set[int] = set()
    for raw_page in stored_pages:
        page_number = int(raw_page)
        if page_number in seen:
            continue
        seen.add(page_number)
        if not 1 <= page_number <= len(document):
            raise ValueError(f"Stored markscheme page {page_number} is outside the PDF")
        page = document[page_number - 1]
        lines = _text_lines(page)
        own = any(_heading_number(line) == question_number for line in lines)
        continued = any(_continued_number(line) == question_number for line in lines)
        next_lines = [line for line in lines if _heading_number(line) == question_number + 1]
        boundary = min((line.rect.y0 for line in next_lines), default=page.rect.height)
        prior_content = _substantive_before(lines, boundary, page.rect.height)
        if not started and (own or continued):
            selected.append(page_number)
            started = True
            continue
        if not started:
            continue
        if own or continued:
            selected.append(page_number)
            continue
        if next_lines:
            if prior_content:
                selected.append(page_number)
            break
        if any((_heading_number(line) or 0) > question_number for line in lines):
            break
        if prior_content:
            selected.append(page_number)
    if not selected:
        raise ValueError(f"Could not locate question {question_number} on stored pages {list(stored_pages)}")
    return selected


def content_crop_rect(
    page: pymupdf.Page, *, question_number: int, continuation: bool
) -> pymupdf.Rect:
    """Return a text-geometry crop from the relevant heading/content to next heading/footer."""
    lines = _text_lines(page)
    own_headings = [line for line in lines if _heading_number(line) == question_number]
    own_continued = [line for line in lines if _continued_number(line) == question_number]

    if not continuation and own_headings:
        anchor = own_headings[0]
    elif own_continued:
        anchor = own_continued[0]
    else:
        candidates = [
            line for line in lines
            if not _is_furniture(line, page.rect.height)
            and _heading_number(line) != question_number + 1
        ]
        if not candidates:
            raise ValueError(f"No crop start for question {question_number}")
        anchor = candidates[0]
    top = max(0.0, anchor.rect.y0 - 8.0)

    next_headings = [
        line for line in lines
        if line.rect.y0 > max(top + 20.0, anchor.rect.y1 + 4.0)
        and (_heading_number(line) or 0) > question_number
    ]
    footers = [
        line for line in lines
        if line.rect.y0 > max(top + 20, page.rect.height * 0.82)
        and (_is_furniture(line, page.rect.height) or DOCUMENT_CODE_RE.search(line.text))
    ]
    boundaries = [line.rect.y0 - 8.0 for line in next_headings + footers]
    bottom = min(boundaries) if boundaries else page.rect.height - 30.0
    if bottom <= top + 12:
        raise ValueError(
            f"Invalid crop bounds for question {question_number}: {top:.1f}..{bottom:.1f}"
        )
    return pymupdf.Rect(0, top, page.rect.width, min(bottom, page.rect.height))


def render_crop(page: pymupdf.Page, clip: pymupdf.Rect) -> Image.Image:
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def atomic_save_webp(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w+b") as stream:
            # High-quality 2x rendering keeps small equations/mark codes legible while
            # method 2 makes the complete-bank rebuild practical and deterministic.
            image.save(stream, "WEBP", quality=94, method=2, exact=True)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary.stat().st_size <= 0:
            raise OSError(f"Empty WebP for {target}")
        with Image.open(temporary) as check:
            check.load()
        os.replace(temporary, target)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def image_is_decodable(path: Path) -> bool:
    """Return whether a completed crop can safely be reused on a resumed build."""
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        with Image.open(path) as image:
            image.load()
            return image.width > 0 and image.height > 0
    except Exception:
        return False


def _atomic_json(payload: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}-", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def build(
    *, root: Path = ROOT, years: set[int] | None = None, clean: bool = True,
    force: bool = False,
) -> dict:
    output_dir = root / "site" / "markschemes"
    manifest_path = root / "data" / "official-markscheme-images.json"
    papers = discover_papers(root)
    selected = [paper for paper in papers if years is None or paper.year in years]
    manifest: dict = {}
    previous_manifest: dict = {}
    if manifest_path.is_file():
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if years:
            manifest = dict(previous_manifest)
    expected: set[Path] = set()

    for paper in selected:
        with pymupdf.open(paper.pdf_path) as document:
            for question in paper.payload["questions"]:
                qid = validate_paper_id(str(question["id"]))
                number = int(question["number"])
                prior = previous_manifest.get(qid)
                if not force and isinstance(prior, dict):
                    prior_pages = prior.get("pages")
                    prior_images = prior.get("images")
                    expected_images = (
                        [f"markschemes/{qid}-page-{int(page)}.webp" for page in prior_pages]
                        if isinstance(prior_pages, list) and prior_pages
                        else []
                    )
                    prior_targets = [
                        safe_output_path(output_dir, qid, f"-page-{int(page)}.webp")
                        for page in (prior_pages or [])
                    ]
                    if (
                        isinstance(prior_images, list)
                        and prior_images == expected_images
                        and all(image_is_decodable(target) for target in prior_targets)
                    ):
                        manifest[qid] = {"pages": list(prior_pages), "images": list(prior_images)}
                        expected.update(prior_targets)
                        continue
                if not isinstance(prior, dict) or not prior.get("pages"):
                    raise ValueError(
                        f"{qid}: verified page mapping is required in {manifest_path}"
                    )
                # The tracked manifest is the reviewed source of truth. Re-derive only
                # within those bounded pages to reject an accidentally over-included
                # next-question page without guessing from instruction/front-matter text.
                pages = derive_question_pages(document, number, prior["pages"])
                images: list[str] = []
                for index, page_number in enumerate(pages):
                    filename = f"{qid}-page-{page_number}.webp"
                    target = safe_output_path(output_dir, qid, f"-page-{page_number}.webp")
                    if force or not image_is_decodable(target):
                        clip = content_crop_rect(
                            document[page_number - 1],
                            question_number=number,
                            continuation=index > 0,
                        )
                        atomic_save_webp(render_crop(document[page_number - 1], clip), target)
                    images.append(f"markschemes/{filename}")
                    expected.add(target)
                manifest[qid] = {"pages": pages, "images": images}

    if clean and years is None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for stale in output_dir.glob("*.webp"):
            if stale not in expected:
                stale.unlink()
    _atomic_json(dict(sorted(manifest.items())), manifest_path)
    print(f"Generated {sum(len(v['images']) for v in manifest.values())} crops for {len(manifest)} questions")
    return manifest


def audit(*, root: Path = ROOT, years: set[int] | None = None) -> dict:
    manifest_path = root / "data" / "official-markscheme-images.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = discover_papers(root)
    qids = {
        q["id"] for p in papers if years is None or p.year in years for q in p.payload["questions"]
    }
    missing_qids = sorted(qids - manifest.keys())
    unexpected_qids = sorted(manifest.keys() - qids) if years is None else []
    missing: list[str] = []
    invalid: list[str] = list(unexpected_qids)
    hashes: dict[str, list[str]] = {}
    leakage: list[str] = []
    by_qid = {q["id"]: (p, q) for p in papers for q in p.payload["questions"]}
    documents: dict[Path, pymupdf.Document] = {}
    try:
        for qid in sorted(qids & manifest.keys()):
            try:
                qid = validate_paper_id(qid)
            except ValueError:
                invalid.append(str(qid))
                continue
            record = manifest[qid]
            if len(record.get("pages", [])) != len(record.get("images", [])) or not record.get("images"):
                invalid.append(qid)
                continue
            try:
                record_pages = [int(page) for page in record["pages"]]
            except (TypeError, ValueError):
                invalid.append(qid)
                continue
            expected_images = [
                f"markschemes/{qid}-page-{page}.webp" for page in record_pages
            ]
            if record["images"] != expected_images:
                invalid.append(qid)
                continue
            for page_number, relative in zip(record["pages"], record["images"]):
                path = safe_output_path(
                    root / "site" / "markschemes", qid, f"-page-{int(page_number)}.webp"
                )
                if not path.is_file() or path.stat().st_size == 0:
                    missing.append(relative)
                    continue
                try:
                    with Image.open(path) as image:
                        image.load()
                        if image.width <= 0 or image.height <= 0:
                            invalid.append(relative)
                except Exception:
                    invalid.append(relative)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.setdefault(digest, []).append(relative)
            paper, question = by_qid[qid]
            if paper.pdf_path not in documents:
                documents[paper.pdf_path] = pymupdf.open(paper.pdf_path)
            document = documents[paper.pdf_path]
            derived = derive_question_pages(
                document, int(question["number"]), record_pages
            )
            if list(record["pages"]) != derived:
                invalid.append(qid)
            for page_number in derived:
                lines = _text_lines(document[page_number - 1])
                own = int(question["number"])
                next_lines = [line for line in lines if _heading_number(line) == own + 1]
                if next_lines and not (
                    any(_heading_number(line) == own for line in lines)
                    or any(_continued_number(line) == own for line in lines)
                    or _substantive_before(lines, min(x.rect.y0 for x in next_lines), document[page_number - 1].rect.height)
                ):
                    leakage.append(f"{qid}:{page_number}")
    finally:
        for document in documents.values():
            document.close()
    identical = [names for names in hashes.values() if len(names) > 1]
    report = {
        "questions_expected": len(qids),
        "questions_present": len(qids) - len(missing_qids),
        "missing_qids": missing_qids,
        "missing_images": missing,
        "invalid": sorted(set(invalid)),
        "identical_groups": identical,
        "next_question_only_leakage": leakage,
    }
    print(json.dumps(report, indent=2))
    if missing_qids or missing or invalid or identical or leakage:
        raise RuntimeError("Official markscheme crop audit failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, action="append", help="Limit to one or more years")
    parser.add_argument("--no-clean", action="store_true", help="Do not remove stale markscheme WebPs")
    parser.add_argument("--force", action="store_true", help="Re-render existing decodable crops")
    parser.add_argument("--audit", action="store_true", help="Audit generated assets")
    args = parser.parse_args()
    years = set(args.year or []) or None
    build(years=years, clean=not args.no_clean, force=args.force)
    if args.audit:
        audit(years=years)


if __name__ == "__main__":
    main()
