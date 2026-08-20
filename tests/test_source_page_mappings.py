import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def question_start_pages(pdf_path: Path) -> dict[int, int]:
    starts = {}
    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            text = page.get_text("text")
            for match in re.finditer(r"(?m)^\s*(\d+)\.\s*\[Maximum marks?:\s*\d+\]", text):
                starts.setdefault(int(match.group(1)), page_number)
    return starts


def test_historical_question_mappings_use_physical_pdf_pages():
    errors = []
    for path in sorted((ROOT / "data/papers").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        year = int(payload["paper"]["year"])
        if not 2017 <= year <= 2021:
            continue
        pdf = ROOT / "data/raw/2017-2021" / f"{payload['paper']['id']}-question.pdf"
        starts = question_start_pages(pdf)
        for question in payload["questions"]:
            expected = starts.get(int(question["number"]))
            if expected is not None and int(question["pages"][0]) != expected:
                errors.append((question["id"], question["pages"][0], expected))
    assert errors == []
