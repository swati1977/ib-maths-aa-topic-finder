#!/usr/bin/env python3
"""Validate completeness and schema of the generated AA SL question bank."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "site" / "data" / "questions.json"
MANIFEST = ROOT / "data" / "source-manifest-2022-2025.json"
TOPICS = {
    "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
    "Sequences - Series", "Complex Numbers", "Permutation - Combination",
    "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
    "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
    "Statistics", "Probability", "Differentiation", "Integration",
    "Differential Equations", "Kinematics",
}


def main() -> None:
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    questions = bank["questions"]
    papers = bank["papers"]
    paper_metadata = {paper["id"]: paper for paper in papers}
    ids = [q["id"] for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question IDs")

    by_paper: dict[str, list[dict]] = defaultdict(list)
    for question in questions:
        paper_id = question["id"].rsplit("-q", 1)[0]
        by_paper[paper_id].append(question)
        if not question["accessibleText"].strip():
            raise ValueError(f"{question['id']}: empty accessible text")
        if not question["accessibleText"].lstrip().startswith(f"{question['number']}."):
            raise ValueError(f"{question['id']}: accessible text does not start with its question number")
        mark_heading = rf"Maximum marks?:\s*{question['marks']}"
        if not re.search(mark_heading, question["accessibleText"]):
            raise ValueError(f"{question['id']}: maximum-mark heading does not match metadata")
        if not question["solution"].strip():
            raise ValueError(f"{question['id']}: empty solution")
        if not question["labels"] or set(question["labels"]) - TOPICS:
            raise ValueError(f"{question['id']}: invalid labels")
        if not question["pages"] or any(int(page) < 1 for page in question["pages"]):
            raise ValueError(f"{question['id']}: invalid pages")

    for paper_id, items in by_paper.items():
        numbers = sorted(q["number"] for q in items)
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"{paper_id}: non-sequential questions {numbers}")
        marks = sum(q["marks"] for q in items)
        expected_marks = int(paper_metadata[paper_id].get("expected_marks", 80))
        if marks != expected_marks:
            raise ValueError(f"{paper_id}: expected {expected_marks} marks, found {marks}")

    expected_manifest_ids = {
        paper["id"] for paper in json.loads(MANIFEST.read_text(encoding="utf-8"))["papers"]
    }
    missing = expected_manifest_ids - set(by_paper)
    if missing:
        raise ValueError(f"Missing manifest papers: {sorted(missing)}")

    years = Counter(q["year"] for q in questions)
    print(
        json.dumps(
            {
                "papers": len(papers),
                "questions": len(questions),
                "questions_by_year": dict(sorted(years.items())),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
