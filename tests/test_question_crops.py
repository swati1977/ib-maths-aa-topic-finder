import json
import sys
import subprocess
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_question_crops import (  # noqa: E402
    atomic_save_webp,
    content_crop_rect,
    discover_papers,
    page_has_question_content,
    question_page_jobs,
)


def make_page(tmp_path: Path, blocks: list[tuple[float, str]]) -> pymupdf.Page:
    document = pymupdf.open()
    page = document.new_page(width=600, height=840)
    for y, text in blocks:
        page.insert_text((45, y), text, fontsize=11)
    # Keep the owning document alive for PyMuPDF's orphan checks.
    page._test_document = document
    return page


def test_discovers_every_current_paper_and_question_page_job():
    papers = discover_papers(ROOT)

    assert len(papers) >= 36
    assert sum(len(p.payload["questions"]) for p in papers) >= 323
    jobs = list(question_page_jobs(papers))
    expected = sum(
        len(question.get("display_pages", question["pages"]))
        for paper in papers
        for question in paper.payload["questions"]
    )
    assert len(jobs) == expected
    assert [p.paper_id for p in papers] == sorted(p.paper_id for p in papers)
    assert next(p for p in papers if p.paper_id == "2025-may-p2-tz1").pdf_path == (
        ROOT / "data/raw/2022-2025/2025-may-p2-tz1-question.pdf"
    )
    assert next(p for p in papers if p.paper_id == "p2-a").recovered_pages is True


def test_crop_cli_can_limit_generation_to_a_year():
    result = subprocess.run(
        [sys.executable, "scripts/build_question_crops.py", "--help"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--year" in result.stdout


def test_crop_starts_at_question_heading_and_stops_before_answer_area(tmp_path):
    page = make_page(
        tmp_path,
        [(45, "- 3 -"), (220, "3. [Maximum mark: 6]"), (260, "Question text"),
         (430, "_" * 70), (810, "12EP03")],
    )

    crop = content_crop_rect(page, question_number=3, continuation=False)

    assert crop.y0 == pytest.approx(page.search_for("3. [Maximum mark: 6]")[0].y0 - 10)
    assert crop.y1 == pytest.approx(page.search_for("_" * 70)[0].y0)


def test_shared_page_crop_stops_at_next_question_heading(tmp_path):
    page = make_page(
        tmp_path,
        [(90, "7. [Maximum mark: 5]"), (130, "Question seven"),
         (390, "8. [Maximum mark: 7]"), (430, "Question eight")],
    )

    crop = content_crop_rect(page, question_number=7, continuation=False)

    assert crop.y1 == pytest.approx(page.search_for("8. [Maximum mark: 7]")[0].y0 - 10)


def test_continuation_page_skips_header_and_keeps_question_content(tmp_path):
    page = make_page(
        tmp_path,
        [(45, "- 6 -"), (82, "(Question 4 continued)"), (115, "(c) Hence find x."),
         (310, "_" * 70), (810, "12EP06")],
    )

    assert page_has_question_content(page, continuation=True)
    crop = content_crop_rect(page, question_number=4, continuation=True)

    assert crop.y0 == pytest.approx(page.search_for("(c) Hence find x.")[0].y0 - 10)
    assert crop.y1 == pytest.approx(page.search_for("_" * 70)[0].y0)


def test_answer_only_continuation_is_not_question_content(tmp_path):
    page = make_page(
        tmp_path,
        [(45, "- 6 -"), (82, "(Question 4 continued)"), (110, "_" * 70),
         (810, "12EP06")],
    )

    assert not page_has_question_content(page, continuation=True)


def test_explicit_fraction_override_wins_over_detected_bottom(tmp_path):
    page = make_page(
        tmp_path,
        [(100, "6. [Maximum mark: 7]"), (150, "Question text"), (500, "_" * 70)],
    )

    crop = content_crop_rect(
        page,
        question_number=6,
        continuation=False,
        override={"bottom": 0.25, "top": 0.10},
    )

    assert crop.y0 == pytest.approx(84)
    assert crop.y1 == pytest.approx(210)


def test_invalid_override_is_rejected(tmp_path):
    page = make_page(tmp_path, [(100, "1. [Maximum mark: 2]")])
    with pytest.raises(ValueError, match="crop fraction"):
        content_crop_rect(
            page, question_number=1, continuation=False, override={"bottom": 1.2}
        )


def test_atomic_save_never_exposes_a_partial_replacement(tmp_path, monkeypatch):
    target = tmp_path / "question.webp"
    Image.new("RGB", (20, 20), "red").save(target, "WEBP")
    before = target.read_bytes()

    def fail_save(file_object, *args, **kwargs):
        file_object.write(b"")
        raise OSError("simulated interrupted encode")

    replacement = Image.new("RGB", (20, 20), "blue")
    monkeypatch.setattr(replacement, "save", fail_save)
    with pytest.raises(OSError, match="interrupted"):
        atomic_save_webp(replacement, target)

    assert target.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))
