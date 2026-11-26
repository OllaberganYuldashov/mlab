"""Talabaga ko'rsatiladigan natija (I3-08; AGR-05, AGR-06).

Saqlangan runner natijasidan qadamlar bo'yicha ball, o'tgan/o'tmagan soni va xabarlar yasaladi.
AGR-05: yashirin test nomi va xabari runner nima yozganidan qat'i nazar **shu yerda qayta**
yashiriladi ("yashirin test N", "O'tmadi") — runner'ga ishonilmaydi (talaba kodi u bilan bir
jarayonda). Talabaning `stdout` i ko'rsatilmaydi: u testlar bajarilayotganda ham yig'iladi,
yashirin test ichidagi qiymat talaba kodi orqali chop etilishi mumkin. Kod xatosi (`error`) faqat
talaba kodi bosqichidan.

Ball butun son (qadam bali * o'tgan / jami, pastga yaxlitlash) — `service.compute_score` shu
funksiyadan foydalanadi, shuning uchun qadamlar yig'indisi saqlangan ball bilan aynan bir xil.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Max

from apps.grading.models import (
    StudentAssignment,
    Submission,
    SubmissionPolicy,
    SubmissionStatus,
    TestKind,
    Understanding,
)

HIDDEN_FAILED = "O'tmadi"
MAX_MESSAGE = 500


def step_breakdown(
    result: dict[str, Any], steps: list[tuple[str, str, int]]
) -> list[dict[str, Any]]:
    """`steps` — (kalit, sarlavha, ball) tartib bilan. Har qadam: ball, o'tgan/jami va testlar."""
    out: list[dict[str, Any]] = []
    hidden_n = 0
    for key, title, points in steps:
        tests: list[dict[str, Any]] = []
        for test in result.get("tests", []):
            if test.get("step") != key:
                continue
            passed = test.get("passed") is True
            if test.get("kind") == TestKind.VISIBLE:
                name = str(test.get("name", ""))[:100]
                message = "" if passed else str(test.get("message", ""))[:MAX_MESSAGE]
                tests.append({"name": name, "visible": True, "passed": passed, "message": message})
            else:
                hidden_n += 1
                tests.append(
                    {
                        "name": f"yashirin test {hidden_n}",
                        "visible": False,
                        "passed": passed,
                        "message": "" if passed else HIDDEN_FAILED,
                    }
                )
        passed_n = sum(1 for t in tests if t["passed"])
        score = points * passed_n // len(tests) if tests else 0
        out.append(
            {
                "key": key,
                "title": title,
                "points": points,
                "score": score,
                "passed": passed_n,
                "total": len(tests),
                "tests": tests,
            }
        )
    return out


def student_result(
    submission: Submission, steps: list[tuple[str, str, int]]
) -> dict[str, Any] | None:
    """Faqat baholangan urinish uchun; boshqa holatlarda `None`."""
    if submission.status != SubmissionStatus.DONE or submission.result is None:
        return None
    result = submission.result
    error = result.get("error") if result.get("status") == "code_error" else None
    return {
        "code_error": None if error is None else str(error)[:MAX_MESSAGE],
        "steps": step_breakdown(result, steps),
    }


def best_score(record: StudentAssignment | None) -> Decimal | None:
    """AGR-06: rasmiy eng yuqori ball — baholangan, mashq emas urinishlar orasida."""
    if record is None:
        return None
    best: Decimal | None = (
        Submission.objects.filter(student_assignment=record, status=SubmissionStatus.DONE)
        .exclude(policy=SubmissionPolicy.PRACTICE)
        .exclude(understanding=Understanding.PENDING)  # INT-02: javobsiz — hali rasmiy emas
        .aggregate(best=Max("final_score"))["best"]
    )
    return best
