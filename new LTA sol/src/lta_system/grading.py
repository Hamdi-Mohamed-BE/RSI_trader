from __future__ import annotations


GRADE_ORDER = {"REJECT": 0, "B": 1, "B+": 2, "A": 3, "A+": 4}


def grade_for_score(score: int) -> str:
    if score >= 13:
        return "A+"
    if score >= 11:
        return "A"
    if score >= 9:
        return "B+"
    if score >= 7:
        return "B"
    return "REJECT"


def grade_at_least(grade: str, minimum: str) -> bool:
    return GRADE_ORDER.get(grade, 0) >= GRADE_ORDER.get(minimum, 3)

