"""SET-01..05 (I1-07): kurs default sozlamalari `course.yaml` dagi `defaults:` blokidan."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.courses.content import ContentError, import_content
from apps.courses.models import AiMode, Course

pytestmark = pytest.mark.django_db

BASE = 'slug: test-kurs\ntitle: Test kurs\nversion: "1"\n'


def _root(tmp_path: Path, course_yaml: str) -> Path:
    root = tmp_path / "content"
    root.mkdir()
    (root / "course.yaml").write_text(course_yaml, encoding="utf-8")
    return root


def test_set_defaults_block_is_optional_with_safe_defaults(tmp_path: Path) -> None:
    import_content(_root(tmp_path, BASE))
    course = Course.objects.get()
    assert course.ai_enabled is True
    assert course.ai_max_mode == AiMode.EXPLAIN
    assert course.practice_after_close is False
    assert course.late_hours == 0
    assert course.late_penalty_percent == 0
    assert course.chat_enabled is True


def test_set_defaults_imported_and_reimport_idempotent(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        BASE
        + "defaults:\n  ai_enabled: false\n  ai_max_mode: guide\n  practice_after_close: true\n"
        "  late_hours: 24\n  late_penalty_percent: 10\n  chat_enabled: false\n",
    )
    import_content(root)
    report = import_content(root)
    assert not report.changed
    course = Course.objects.get()
    assert (course.ai_enabled, course.ai_max_mode) == (False, AiMode.GUIDE)
    assert (course.practice_after_close, course.late_hours) == (True, 24)
    assert (course.late_penalty_percent, course.chat_enabled) == (10, False)


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("defaults:\n  ai_max_mode: magic\n", "ai_max_mode"),
        ("defaults:\n  late_hours: -1\n", "late_hours"),
        ("defaults:\n  late_hours: 200\n", "late_hours"),
        ("defaults:\n  late_penalty_percent: 101\n", "late_penalty_percent"),
        ("defaults:\n  ai_enabled: 'ha'\n", "ai_enabled"),
        ("defaults:\n  late_hours: true\n", "late_hours"),
        ("defaults:\n  unknown_key: 1\n", "unknown_key"),
        ("defaults: 5\n", "defaults"),
    ],
)
def test_set_invalid_defaults_reported_with_line(tmp_path: Path, block: str, message: str) -> None:
    with pytest.raises(ContentError, match=message) as exc:
        import_content(_root(tmp_path, BASE + block))
    assert "course.yaml:" in str(exc.value)
    assert not Course.objects.exists()
