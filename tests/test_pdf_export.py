import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "site/index.html").read_text(encoding="utf-8")
APP = (ROOT / "site/app.js").read_text(encoding="utf-8")


def test_export_dialog_offers_required_content_and_visual_modes():
    assert 'id="download-pdf"' in INDEX
    assert 'id="pdf-export-dialog"' in INDEX
    assert '<option value="questions">Questions only</option>' in INDEX
    assert '<option value="solutions">Solutions only</option>' in INDEX
    assert '<option value="both">Questions and solutions</option>' in INDEX
    assert '<option value="clean">Clean text with original visuals</option>' in INDEX
    assert '<option value="original">Original question images</option>' in INDEX


def test_export_uses_current_filtered_results_and_downloads_a_pdf():
    assert "filteredQuestions()" in APP
    assert "exportMatchingQuestions" in APP
    assert ".save(" in APP
    assert "questionImages" in APP
    assert "accessibleText" in APP
    assert "solution" in APP


def test_pdf_engine_and_unicode_font_are_vendored():
    assert (ROOT / "site/vendor/jspdf.umd.min.js").stat().st_size > 100_000
    assert (ROOT / "site/vendor/DejaVuSans.ttf").stat().st_size > 100_000
    assert 'src="vendor/jspdf.umd.min.js"' in INDEX


def test_export_function_executes_for_questions_and_solutions():
    result = subprocess.run(
        ["node", "tests/pdf_export_smoke.js"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "pdf export smoke passed" in result.stdout
