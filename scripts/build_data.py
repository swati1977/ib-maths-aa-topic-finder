#!/usr/bin/env python3
"""Merge reviewed paper JSON into the static site's question bank."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = {
    "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
    "Sequences - Series", "Complex Numbers", "Permutation - Combination",
    "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
    "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
    "Statistics", "Probability", "Differentiation", "Integration",
    "Differential Equations", "Kinematics",
}


def main() -> None:
    questions: list[dict] = []
    paper_summaries: list[dict] = []
    ids: set[str] = set()

    for path in [ROOT / "data" / f"{name}.json" for name in ("p1-a", "p1-c", "p2-a", "p2-c")]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        paper = payload["paper"]
        required_paper = {"id", "title", "paper", "zone", "year", "source_url", "pdf_url", "solution_status"}
        missing = required_paper - paper.keys()
        if missing:
            raise ValueError(f"{path.name}: missing paper fields {sorted(missing)}")

        count = 0
        for raw in payload["questions"]:
            qid = raw["id"]
            if qid in ids:
                raise ValueError(f"Duplicate question id: {qid}")
            ids.add(qid)
            labels = raw["labels"]
            unknown = set(labels) - TOPICS
            if unknown:
                raise ValueError(f"{qid}: unknown labels {sorted(unknown)}")
            if not labels:
                raise ValueError(f"{qid}: at least one topic label is required")
            if not raw["solution"].strip():
                raise ValueError(f"{qid}: solution is empty")
            marks = int(raw["marks"])
            pages = raw["pages"] if isinstance(raw["pages"], list) else [raw["pages"]]
            questions.append({
                "id": qid,
                "number": int(raw["number"]),
                "paper": int(paper["paper"]),
                "zone": str(paper["zone"]),
                "year": int(paper["year"]),
                "pages": [int(page) for page in pages],
                "marks": marks,
                "summary": raw["summary"].strip(),
                "labels": labels,
                "solution": raw["solution"].strip(),
                "sourceUrl": paper["source_url"],
                "pdfUrl": paper["pdf_url"],
                "solutionStatus": paper["solution_status"],
            })
            count += 1
        paper_summaries.append({**paper, "question_count": count})

    questions.sort(key=lambda q: (q["paper"], q["zone"], q["number"]))
    output = {"version": 1, "papers": paper_summaries, "questions": questions}
    target = ROOT / "site" / "data" / "questions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} questions from {len(paper_summaries)} papers to {target}")


if __name__ == "__main__":
    main()
