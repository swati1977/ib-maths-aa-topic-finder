import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "site/index.html").read_text(encoding="utf-8")
APP = (ROOT / "site/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "site/styles.css").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "site/data/questions.json").read_text(encoding="utf-8"))


def test_question_card_uses_source_image_as_primary_and_accessible_text_as_secondary():
    assert 'class="question-text"' in INDEX
    assert 'class="question-primary-images"' in INDEX
    assert 'class="accessible-transcript"' in INDEX
    assert "renderAccessibleQuestion" in APP
    assert 'className = "visual-description sr-only"' in APP
    assert 'question-summary' not in INDEX
    assert 'q.summary' not in APP.split("function renderQuestion(q)", 1)[1].split("return card", 1)[0]
    for q in DATA["questions"]:
        assert len(q["accessibleText"].strip()) >= 30, q["id"]


def test_questions_with_visuals_render_actual_source_images():
    assert 'class="question-primary-images"' in INDEX
    assert 'renderQuestionImages(card.querySelector(".question-primary-images"), q)' in APP


def test_long_math_text_cannot_expand_cards_beyond_the_viewport():
    assert ".question-card {" in STYLES and "min-width: 0" in STYLES
    assert ".question-text" in STYLES and "overflow-wrap: anywhere" in STYLES
    assert ".solution-content" in STYLES and ".solution-part > p" in STYLES


def test_exact_question_images_are_embedded_directly_without_pdf_iframes():
    assert 'class="question-primary-images"' in INDEX
    assert "renderQuestionImages" in APP
    assert 'document.createElement("img")' in APP
    assert "iframe" not in INDEX.lower()


def test_original_source_remains_a_separate_external_link():
    assert "buildPaperUrl" in APP
    assert "paperLink.href = buildPaperUrl(q)" in APP
    assert 'target="_blank"' in INDEX
    assert "Open source paper" in INDEX
    assert 'paperLink.setAttribute("aria-label", `Open source record for Paper ${q.paper} ${formatZone(q.zone)}, question ${q.number}`)' in APP
    assert "Source-faithful practice" in INDEX


def test_default_sort_label_describes_year_then_paper_order():
    assert '<option value="paper">Sort by year and paper</option>' in INDEX


def test_search_uses_accessible_question_text():
    assert "q.accessibleText" in APP.split("function filteredQuestions", 1)[1].split("return items.sort", 1)[0]


def test_year_session_and_zone_filters_are_data_driven():
    assert 'id="year-filters"' in INDEX
    assert 'id="session-filters"' in INDEX
    assert 'id="zone-filters"' in INDEX
    assert "buildDynamicFilters(payload.questions)" in APP
    assert 'selectedValues("year")' in APP
    assert 'selectedValues("session")' in APP
    assert "matchesYear" in APP
    assert "matchesSession" in APP


def test_course_labels_and_filters_distinguish_math_sl_from_aa_sl():
    assert 'id="subject-filters"' in INDEX
    assert "formatSubject" in APP
    assert 'selectedValues("subject")' in APP
    assert "matchesSubject" in APP
    assert '"subject": subject' in (ROOT / "scripts/build_data.py").read_text(encoding="utf-8")


def test_filter_updates_do_not_announce_entire_result_sets():
    assert 'id="visible-count" aria-live="polite"' in INDEX
    assert 'id="pdf-export-status" class="export-status" aria-live="polite"' in INDEX
    assert 'id="questions" class="question-list" aria-live=' not in INDEX
    assert 'id="active-filters" class="active-filters" aria-live=' not in INDEX


def test_desktop_filters_scroll_independently_and_mobile_returns_to_page_flow():
    assert "max-height: calc(100vh - 40px)" in STYLES
    assert "overflow-y: auto" in STYLES
    mobile = STYLES.split("@media (max-width: 820px)", 1)[1]
    assert "max-height: none" in mobile
    assert "overflow: visible" in mobile


def test_mobile_filters_are_collapsible():
    assert 'id="toggle-filters"' in INDEX
    assert 'id="filter-body"' in INDEX
    assert "filters-open" in APP
    mobile = STYLES.split("@media (max-width: 820px)", 1)[1]
    assert ".filter-body { display: none; }" in mobile
    assert ".filters-open .filter-body { display: block; }" in mobile


def test_large_banks_render_in_batches_without_limiting_filter_or_export_results():
    assert 'id="load-more"' in INDEX
    assert "PAGE_SIZE" in APP
    assert "items.slice(0, state.visibleLimit)" in APP
    assert "state.visibleLimit += PAGE_SIZE" in APP
    assert "const items = filteredQuestions();" in APP


def test_hosted_question_images_match_display_pages_when_present():
    for q in DATA["questions"]:
        assert q["displayPages"]
        assert set(q["displayPages"]).issubset(q["pages"])
        if not q["questionImages"]:
            continue
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
    assert len(questions) >= 35
    assert {q["year"] for q in questions}.issubset(set(range(2017, 2027)))
    for q in questions:
        assert q["pdfUrl"].startswith("https://")
        assert q["pages"] and all(isinstance(page, int) and page > 0 for page in q["pages"])
        assert q["solution"].strip()
        assert re.search(rf"Maximum marks?:\s*{q['marks']}", q["accessibleText"]), q["id"]


def test_verified_2022_to_2026_baseline_remains_present_during_expansion():
    assert len(DATA["papers"]) >= 36
    assert len(DATA["questions"]) >= 323
    assert {2022, 2023, 2024, 2025, 2026}.issubset({q["year"] for q in DATA["questions"]})
    paper_ids = {paper["id"] for paper in DATA["papers"]}
    manifest = json.loads((ROOT / "data/source-manifest-2022-2025.json").read_text(encoding="utf-8"))
    assert {paper["id"] for paper in manifest["papers"]}.issubset(paper_ids)


def test_complete_2017_to_2026_collection_is_present():
    assert len(DATA["papers"]) == 62
    assert len(DATA["questions"]) == 578
    assert {q["year"] for q in DATA["questions"]} == set(range(2017, 2027))
    paper_ids = {paper["id"] for paper in DATA["papers"]}
    old_manifest = json.loads((ROOT / "data/source-manifest-2017-2021.json").read_text(encoding="utf-8"))
    current_manifest = json.loads((ROOT / "data/source-manifest-2026.json").read_text(encoding="utf-8"))
    assert old_manifest["count"] == 26
    assert {paper["id"] for paper in old_manifest["papers"]}.issubset(paper_ids)
    assert current_manifest["count"] == 4
    assert {paper["id"] for paper in current_manifest["papers"]}.issubset(paper_ids)
    assert old_manifest["unavailable_sessions"][0]["year"] == 2020


def test_malformed_paper_uses_source_record_fallback():
    p2a = [q for q in DATA["questions"] if q["paper"] == 2 and q["zone"] == "A"]
    others = [q for q in DATA["questions"] if not (q["paper"] == 2 and q["zone"] == "A")]
    assert p2a and all(q["viewerAvailable"] is False for q in p2a)
    assert all(q["viewerAvailable"] is True for q in others)
    assert "if (!q.viewerAvailable)" in APP
    assert "paperLink.href = q.sourceUrl" in APP


def test_missing_2026_p2a_question_is_restored_as_a_labelled_reconstruction():
    source = json.loads((ROOT / "data/p2-a.json").read_text(encoding="utf-8"))
    assert len(source["questions"]) == 9
    assert sum(q["marks"] for q in source["questions"]) == 80
    q9 = next(q for q in source["questions"] if q["number"] == 9)
    assert q9["pages"] == [12, 13]
    assert q9["image_status"] == "verified reconstruction"
    assert "Jacinta has a bag of counters" in q9["accessible_text"]
    assert 'q.imageStatus === "verified reconstruction"' in APP


def test_answer_only_continuation_pages_are_not_displayed():
    by_id = {q["id"]: q for q in DATA["questions"]}
    assert by_id["m26-math-aasl-p1-tza-q7"]["displayPages"] == [8]
    assert by_id["m26-math-aasl-p1-tza-q8"]["displayPages"] == [10]
    assert by_id["m26-math-aasl-p1-tza-q9"]["displayPages"] == [13]
    assert by_id["m26-math-aasl-p1-c-q1"]["displayPages"] == [2]


def test_p2a_q6_uses_reviewed_crop_and_exact_mark_text():
    source = json.loads((ROOT / "data/p2-a.json").read_text(encoding="utf-8"))
    q = next(item for item in source["questions"] if item["number"] == 6)
    assert q["crop_bottom_fractions"] == {"9": 0.25}
    assert q["accessible_text"].endswith("Find the value of μ and the value of σ.")
    assert not q["accessible_text"].endswith("[7]")


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
