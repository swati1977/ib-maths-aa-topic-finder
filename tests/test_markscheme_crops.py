import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_markscheme_crops import (  # noqa: E402
    atomic_save_webp,
    content_crop_rect,
    derive_question_pages,
    discover_papers,
    image_is_decodable,
    resolve_markscheme_pdf,
    validate_paper_id,
)


def make_document(page_lines: list[list[tuple[float, str]]]) -> pymupdf.Document:
    document = pymupdf.open()
    for lines in page_lines:
        page = document.new_page(width=600, height=840)
        for y, text in lines:
            page.insert_text((45, y), text, fontsize=11)
    return document


def test_discovers_exactly_the_542_official_questions():
    papers = discover_papers(ROOT)
    assert len(papers) == 58
    assert sum(len(p.payload["questions"]) for p in papers) == 542
    assert all(p.year <= 2025 for p in papers)
    assert [p.paper_id for p in papers] == sorted(p.paper_id for p in papers)


def test_markscheme_pdf_resolution_is_exact_and_cannot_escape_raw_tree(tmp_path):
    paper = {"id": "2023-may-p1-tz1", "year": 2023}
    expected = tmp_path / "data/raw/2022-2025/2023-may-p1-tz1-markscheme.pdf"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"pdf")
    assert resolve_markscheme_pdf(tmp_path, paper) == expected

    with pytest.raises(ValueError, match="Unsafe paper id"):
        resolve_markscheme_pdf(tmp_path, {"id": "../../escape", "year": 2023})


def test_derive_pages_removes_a_stored_page_containing_only_next_question():
    document = make_document([
        [(70, "1."), (110, "answer one"), (810, "- 1 -")],
        [(70, "Question 1 continued"), (110, "more answer one")],
        [(70, "2."), (110, "answer two")],
    ])
    try:
        assert derive_question_pages(document, 1, [1, 2, 3]) == [1, 2]
    finally:
        document.close()


def test_next_question_text_on_same_row_is_not_prior_question_content():
    document = pymupdf.open()
    first = document.new_page(width=600, height=840)
    first.insert_text((45, 80), "2.", fontsize=11)
    first.insert_text((75, 80), "answer two", fontsize=11)
    second = document.new_page(width=600, height=840)
    second.insert_text((45, 90), "3.", fontsize=11)
    second.insert_text((100, 89), "answer three begins", fontsize=11)
    try:
        assert derive_question_pages(document, 2, [1, 2]) == [1]
    finally:
        document.close()


def test_derive_pages_keeps_shared_page_content_before_next_heading():
    document = make_document([
        [(70, "Question 7 continued"), (110, "first part")],
        [(70, "last line of question seven"), (360, "8."), (400, "answer eight")],
    ])
    try:
        assert derive_question_pages(document, 7, [1, 2]) == [1, 2]
    finally:
        document.close()


def test_crop_starts_at_own_heading_and_stops_before_next_heading():
    document = make_document([[
        (60, "Question 9 continued"),
        (100, "tail of question nine"),
        (350, "10."),
        (390, "answer ten"),
        (700, "11."),
        (740, "answer eleven"),
        (810, "- 14 -"),
    ]])
    try:
        page = document[0]
        crop = content_crop_rect(page, question_number=10, continuation=False)
        assert crop.y0 == pytest.approx(page.search_for("10.")[0].y0 - 8)
        assert crop.y1 == pytest.approx(page.search_for("11.")[0].y0 - 8)
    finally:
        document.close()


def test_continuation_crop_includes_continuation_heading_and_excludes_footer():
    document = make_document([[
        (45, "- 8 -"),
        (80, "Question 4(c) continued"),
        (120, "markscheme content"),
        (805, "8825 - 7119M"),
    ]])
    try:
        page = document[0]
        crop = content_crop_rect(page, question_number=4, continuation=True)
        assert crop.y0 == pytest.approx(page.search_for("Question 4(c) continued")[0].y0 - 8)
        assert crop.y1 < page.search_for("8825 - 7119M")[0].y0
        assert crop.y1 > page.search_for("markscheme content")[0].y1
    finally:
        document.close()


def test_nearby_numeric_line_does_not_create_zero_height_crop():
    document = pymupdf.open()
    page = document.new_page(width=600, height=840)
    page.insert_text((45, 80), "2.", fontsize=11)
    page.insert_text((100, 81), "3.", fontsize=11)
    page.insert_text((75, 120), "answer content", fontsize=11)
    try:
        crop = content_crop_rect(page, question_number=2, continuation=False)
        assert crop.y1 > page.search_for("answer content")[0].y1
    finally:
        document.close()


def test_resume_recognizes_only_nonempty_decodable_images(tmp_path):
    valid = tmp_path / "valid.webp"
    Image.new("RGB", (20, 20), "white").save(valid, "WEBP")
    broken = tmp_path / "broken.webp"
    broken.write_bytes(b"not an image")
    assert image_is_decodable(valid)
    assert not image_is_decodable(broken)
    assert not image_is_decodable(tmp_path / "missing.webp")


@pytest.mark.parametrize("unsafe", ["../escape", "paper/q1", "paper\\q1", "/absolute", "safe..not"])
def test_markscheme_crop_ids_reject_path_traversal(unsafe):
    with pytest.raises(ValueError):
        validate_paper_id(unsafe)


def test_derive_pages_stops_after_next_question_when_scanning_whole_document():
    document = make_document([
        [(70, "1."), (110, "question one marking")],
        [(70, "Question 1 continued"), (110, "last marking")],
        [(70, "2."), (110, "question two marking")],
        [(70, "3."), (110, "question three marking")],
    ])
    try:
        assert derive_question_pages(document, 1, range(1, len(document) + 1)) == [1, 2]
    finally:
        document.close()


def test_atomic_webp_save_is_decodable_and_deterministic(tmp_path):
    target = tmp_path / "crop.webp"
    image = Image.new("RGB", (80, 60), "white")
    atomic_save_webp(image, target)
    first = hashlib.sha256(target.read_bytes()).hexdigest()
    with Image.open(target) as decoded:
        decoded.load()
        assert decoded.size == (80, 60)
    atomic_save_webp(image, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == first


def test_cli_exposes_bounded_year_reruns():
    result = subprocess.run(
        [sys.executable, "scripts/build_markscheme_crops.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--year" in result.stdout
