import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingestion_paths import safe_output_path, validate_paper_id


def test_manifest_paper_ids_use_a_conservative_filename_pattern():
    assert validate_paper_id("2025-may-p2-tz3") == "2025-may-p2-tz3"
    for unsafe in ("../escape", "/tmp/escape", "paper/child", "paper..escape", "Paper 1", ""):
        with pytest.raises(ValueError):
            validate_paper_id(unsafe)


def test_manifest_output_paths_cannot_escape_the_output_root(tmp_path):
    target = safe_output_path(tmp_path, "2025-may-p2-tz3", "-question.pdf")
    assert target == tmp_path / "2025-may-p2-tz3-question.pdf"
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, "../escape", "-question.pdf")
