import json
import sys
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_question_crops import discover_papers, question_page_jobs

def test_discovers_every_current_paper_and_question_page_job():
    papers = discover_papers(ROOT)
    assert len(papers) >= 36
    assert sum(len(p.payload["questions"]) for p in papers) >= 323
