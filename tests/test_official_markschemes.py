import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "site/index.html").read_text(encoding="utf-8")
APP = (ROOT / "site/app.js").read_text(encoding="utf-8")
BUILD = (ROOT / "scripts/build_data.py").read_text(encoding="utf-8")
CROP_BUILD = (ROOT / "scripts/build_markscheme_crops.py").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "site/data/questions.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "data/official-markscheme-images.json").read_text(encoding="utf-8"))


def test_official_markscheme_image_manifest_is_complete_and_assets_exist():
    assert len(MANIFEST) == 542
    assert sum(len(entry["images"]) for entry in MANIFEST.values()) == 824
    for question_id, entry in MANIFEST.items():
        assert entry["pages"]
        assert len(entry["images"]) == len(entry["pages"])
        for image in entry["images"]:
            path = ROOT / "site" / image
            assert path.is_file(), (question_id, path)
            assert path.stat().st_size > 1000, path


def test_generated_bank_propagates_official_images_and_fallback_fields():
    assert "official-markscheme-images.json" in BUILD
    by_id = {question["id"]: question for question in DATA["questions"]}
    official = [question for question in DATA["questions"] if question["year"] <= 2025]
    fallback = [question for question in DATA["questions"] if question["year"] == 2026]
    assert len(official) == 542
    assert len(fallback) == 36
    for question in official:
        source = MANIFEST[question["id"]]
        assert question["officialMarkscheme"] == source
        assert question["markschemeUrl"].startswith("https://")
    assert all(question["officialMarkscheme"] is None for question in fallback)
    assert all(question["independentSolution"].strip() for question in fallback)
    assert "unsafe or unexpected official markscheme image paths" in BUILD
    assert "official markscheme image escapes asset root" in BUILD
    assert "record[\"images\"] != expected_images" in CROP_BUILD
    assert "safe_output_path(" in CROP_BUILD


def test_known_overincluded_page_is_removed_by_crop_manifest():
    assert MANIFEST["2020-november-p2-tzn-q2"]["pages"] == [7]


def test_official_markscheme_images_are_primary_answer_with_page_link():
    assert 'class="markscheme-images"' in INDEX
    assert "renderMarkschemeImages" in APP
    assert 'className = "markscheme-image"' in APP
    assert "buildMarkschemeUrl" in APP
    assert 'class="markscheme-link"' in INDEX
    assert "Official IB markscheme" in INDEX
    assert "Independent worked solution — official markscheme unavailable" in APP


def test_pdf_export_uses_official_images_before_independent_fallback():
    export_body = APP.split("async function exportMatchingQuestions", 1)[1].split("function renderQuestion", 1)[0]
    assert "q.officialMarkscheme?.images?.length" in export_body
    assert "await addPdfImagePage" in export_body
    assert "answerText(q)" in export_body


def test_question_images_are_primary_and_accessible_text_is_secondary():
    assert 'class="question-primary-images"' in INDEX
    assert 'class="accessible-transcript"' in INDEX
    image_position = INDEX.index('class="question-primary-images"')
    transcript_position = INDEX.index('class="accessible-transcript"')
    assert image_position < transcript_position
    assert "renderQuestionImages(card.querySelector(\".question-primary-images\"), q)" in APP
