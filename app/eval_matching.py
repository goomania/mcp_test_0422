from typing import Any


from __future__ import annotations

import json
from pathlib import Path

from app.matching import MatchRequest, match_courses


CASES_PATH = Path(__file__).resolve().parent.parent / "data" / "matching_eval_cases.json"


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    total = 0
    passed = 0

    for case in cases:
        total += 1
        req = MatchRequest.model_validate(case["request"])
        resp = match_courses(req)
        got_ids = [r.course.get("id") for r in resp.results]
        expected = set[Any](case.get("expected_contains", []))
        ok = bool(expected.intersection(got_ids))
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['name']} -> {got_ids}")

    print(f"\nSummary: {passed}/{total} cases passed")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

