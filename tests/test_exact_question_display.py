import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "site/index.html").read_text(encoding="utf-8")
APP = (ROOT / "site/app.js").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "site/data/questions.json").read_text(encoding="utf-8"))


def test_question_card_has_authoritative_source_viewer():
    assert 'question-button' in INDEX
    assert 'class="source-viewer"' in INDEX
    assert 'class="question-image-list"' in INDEX
    assert "View exact question" in INDEX


def test_question_viewer_uses_hosted_question_images_not_pdf_iframes():
    assert "renderQuestionImages" in APP
    assert 'document.createElement("img")' in APP
    assert 'className = "question-image"' in APP
    assert "iframe" not in INDEX.lower()
    assert "question-page-frame" not in APP


def test_every_question_has_accessible_exact_text_alternative():
    assert 'class="accessible-transcript"' in INDEX
    assert 'card.querySelector(".accessible-question-text").textContent = q.accessibleText' in APP
    for q in DATA["questions"]:
        assert len(q["accessibleText"].strip()) >= 80, q["id"]


def test_summary_is_explicitly_labelled_not_presented_as_question_text():
    assert 'class="summary-label"' in INDEX
    assert 'class="question-summary"' in INDEX
    assert 'card.querySelector(".question-summary").textContent = q.summary' in APP
    assert 'card.querySelector("h3").textContent = q.summary' not in APP


def test_every_question_has_one_hosted_image_per_display_page():
    for q in DATA["questions"]:
        assert q["displayPages"]
        assert set(q["displayPages"]).issubset(q["pages"])
        assert len(q["questionImages"]) == len(q["displayPages"])
        for image in q["questionImages"]:
            path = ROOT / "site" / image
            assert path.is_file(), path
            assert path.stat().st_size > 1000, path


def test_solution_renderer_preserves_labelled_subparts_without_splitting_function_notation():
    assert "renderSolutionParts" in APP
    assert 'className = "solution-part"' in APP
    assert 'className = "solution-part-label"' in APP
    assert "(?<!\\S)" in APP
    assert "[ivx]+" not in APP


def test_every_question_has_https_pdf_and_valid_pages():
    questions = DATA["questions"]
    assert len(questions) == 35
    for q in questions:
        assert q["pdfUrl"].startswith("https://")
        assert q["pages"] and all(isinstance(page, int) and page > 0 for page in q["pages"])
        assert q["solution"].strip()


def test_malformed_paper_uses_explicit_source_fallback_instead_of_blank_pdf_viewer():
    p2a = [q for q in DATA["questions"] if q["paper"] == 2 and q["zone"] == "A"]
    others = [q for q in DATA["questions"] if not (q["paper"] == 2 and q["zone"] == "A")]
    assert p2a and all(q["viewerAvailable"] is False for q in p2a)
    assert all(q["viewerAvailable"] is True for q in others)
    assert all(q["questionImages"] for q in p2a)
    assert "if (!q.questionImages?.length)" in APP


def test_answer_only_continuation_pages_are_not_displayed():
    by_id = {q["id"]: q for q in DATA["questions"]}
    assert by_id["m26-math-aasl-p1-tza-q7"]["displayPages"] == [8]
    assert by_id["m26-math-aasl-p1-tza-q8"]["displayPages"] == [10]
    assert by_id["m26-math-aasl-p1-tza-q9"]["displayPages"] == [13]
    assert by_id["m26-math-aasl-p1-c-q1"]["displayPages"] == [2]


def test_quadratics_example_maps_to_paper_1_zone_a_page_3_with_three_solution_parts():
    q = next(item for item in DATA["questions"] if item["id"] == "m26-math-aasl-p1-tza-q2")
    assert q["pages"] == [3]
    assert "Quadratics" in q["labels"]
    assert re.search(r"\(a\)", q["solution"])
    assert re.search(r"\(b\)", q["solution"])
    assert re.search(r"\(c\)", q["solution"])


def test_audited_nested_solution_labels_match_printed_subparts():
    expected = {
        "m26-math-aasl-p1-tza-q7": ["(a)(i)", "(a)(ii)", "(b)", "(c)(i)", "(c)(ii)"],
        "m26-math-aasl-p1-c-q7": ["(a)(i)", "(a)(ii)", "(b)(i)", "(b)(ii)", "(c)", "(d)(i)", "(d)(ii)"],
        "m26-math-aasl-p2-tza-q4": ["(a)", "(b)"],
        "m26-math-aasl-p2-tza-q5": ["(a)", "(b)"],
        "m26-math-aasl-p2-tzc-q2": ["(a)(i)", "(a)(ii)", "(b)", "(c)"],
        "m26-math-aasl-p2-tzc-q4": ["(a)(i)", "(a)(ii)", "(b)", "(c)"],
        "m26-math-aasl-p2-tzc-q7": ["(a)(i)", "(a)(ii)", "(b)", "(c)(i)", "(c)(ii)", "(d)(i)", "(d)(ii)", "(d)(iii)"],
        "m26-math-aasl-p2-tzc-q9": ["(a)", "(b)", "(c)(i)", "(c)(ii)", "(c)(iii)", "(d)", "(e)"],
    }
    by_id = {q["id"]: q for q in DATA["questions"]}
    for question_id, labels in expected.items():
        for label in labels:
            assert label in by_id[question_id]["solution"], (question_id, label)
