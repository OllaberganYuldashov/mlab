"""AGR-07, AGR-08, INT-02 (I3-15..I3-17): kursdagi topshiriqlar (`content/labs/`) to'liq tarkibda.

Yechimlarning yashirin testlardan o'tishi — `manage.py check_lab_solutions` (sandbox paketlari).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from apps.grading.content import LabData, load_labs

CONTENT = Path(__file__).resolve().parents[3] / "content"
LEVELS = ("basic", "medium", "advanced")


@pytest.fixture(scope="module")
def labs() -> tuple[LabData, ...]:
    return load_labs(CONTENT)


def test_agr_07_course_has_labs_a01_to_a15_in_order(labs: tuple[LabData, ...]) -> None:
    codes = [lab.code for lab in labs]
    assert codes == [f"A{n:02d}" for n in range(1, 16)]


def test_agr_07_each_lab_is_complete(labs: tuple[LabData, ...]) -> None:
    topics = {p.name.split("-")[0] for p in (CONTENT / "topics").iterdir() if p.is_dir()}
    for lab in labs:
        assert lab.topic in topics, lab.code
        assert sum(step.points for step in lab.steps) == 100, lab.code
        assert all(step.hidden for step in lab.steps), f"{lab.code}: har qadamga yashirin test"
        assert lab.challenge.strip(), lab.code
        assert lab.independent.strip(), lab.code
        per_level = Counter(level for level, _, _ in lab.variants)
        assert all(per_level[level] >= 5 for level in LEVELS), (lab.code, per_level)


def test_agr_08_variants_differ_within_a_level(labs: tuple[LabData, ...]) -> None:
    for lab in labs:
        for level in LEVELS:
            params = [repr(sorted(p.items())) for lv, _, p in lab.variants if lv == level]
            assert len(set(params)) == len(params), f"{lab.code} {level}: bir xil variantlar"


def test_int_02_every_variant_has_understanding_questions(labs: tuple[LabData, ...]) -> None:
    for lab in labs:
        for level, number, _ in lab.variants:
            questions = lab.questions.get((level, number), [])
            assert len(questions) >= 2, f"{lab.code} {level}-{number}"
