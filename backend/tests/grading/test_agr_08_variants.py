"""AGR-08, INT-03 (I3-03): deterministik variant va StudentAssignment."""

from __future__ import annotations

import shutil
import threading
from collections import Counter
from pathlib import Path

import pytest
from django.db import connection
from django.test import override_settings

from apps.courses.content import ContentError
from apps.grading import variants
from apps.grading.content import import_labs
from apps.grading.models import Assignment, Level, StudentAssignment, Variant
from tests.accounts.factories import make_user
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.sections.factories import make_course

pytestmark = pytest.mark.django_db


@pytest.fixture
def assignment(content: Path) -> Assignment:  # noqa: F811
    import_labs(content, make_course())
    return Assignment.objects.get()


def test_agr_08_pick_is_stable_and_depends_on_student_assignment_level() -> None:
    first = variants.pick_index(7, "A01", "basic", 5)
    assert all(variants.pick_index(7, "A01", "basic", 5) == first for _ in range(5))
    others = {variants.pick_index(s, "A01", "basic", 5) for s in range(1, 40)}
    assert len(others) == 5  # turli talabalar turli variantlarni oladi


def test_agr_08_distribution_is_roughly_uniform() -> None:
    counts = Counter(variants.pick_index(s, "A03", "medium", 5) for s in range(1, 5001))
    assert set(counts) == {0, 1, 2, 3, 4}
    assert all(900 <= c <= 1100 for c in counts.values()), counts  # kutilgan 1000 ± 10%


def test_agr_08_secret_changes_mapping() -> None:
    picks = [variants.pick_index(s, "A01", "basic", 5) for s in range(1, 50)]
    with override_settings(VARIANT_SECRET="boshqa-kalit"):
        other = [variants.pick_index(s, "A01", "basic", 5) for s in range(1, 50)]
    assert picks != other  # kalitsiz taxmin qilib bo'lmaydi


def test_agr_08_assign_creates_once_and_keeps_choice(assignment: Assignment) -> None:
    student = make_user()
    record = variants.assign(student, assignment)
    expected = variants.pick_index(student.pk, "A01", Level.BASIC, 5) + 1
    assert (record.level, record.variant.number) == (Level.BASIC, expected)
    assert record.variant.assignment_id == assignment.pk
    assert record.seed == variants.dataset_seed(student.pk, "A01")
    # Kalit almashsa ham berilgan variant o'zgarmaydi.
    with override_settings(VARIANT_SECRET="yangi"):
        again = variants.assign(student, assignment)
    assert (again.pk, again.variant_id) == (record.pk, record.variant_id)
    assert StudentAssignment.objects.count() == 1


def test_agr_08_assign_without_variants_raises(assignment: Assignment) -> None:
    Variant.objects.filter(level=Level.ADVANCED).delete()
    with pytest.raises(variants.NoVariants):
        variants.assign(make_user(), assignment, Level.ADVANCED)


@pytest.mark.django_db(transaction=True)
def test_agr_08_concurrent_first_open_creates_single_record(content: Path) -> None:  # noqa: F811
    import_labs(content, make_course())
    assignment = Assignment.objects.get()
    student = make_user()
    results: list[int] = []
    barrier = threading.Barrier(4)

    def worker() -> None:
        try:
            barrier.wait()
            results.append(variants.assign(student, assignment).pk)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 4
    assert len(set(results)) == 1
    assert StudentAssignment.objects.count() == 1


def test_agr_08_import_refuses_to_delete_used_variant_or_assignment(
    content: Path,  # noqa: F811
) -> None:
    course = make_course()
    import_labs(content, course)
    record = variants.assign(make_user(), Assignment.objects.get())
    used = content / "labs/A01-pandas/variants" / f"basic-{record.variant.number}.yaml"
    used.rename(used.with_name("basic-9.yaml"))  # (basic, N) o'chadi, soni 5 qoladi
    with pytest.raises(ContentError, match="variant talabaga berilgan"):
        import_labs(content, course)
    shutil.rmtree(content / "labs/A01-pandas")
    (content / "labs").mkdir(exist_ok=True)
    with pytest.raises(ContentError, match="topshiriq talabalarga berilgan"):
        import_labs(content, course)
    assert Variant.objects.count() == 15
