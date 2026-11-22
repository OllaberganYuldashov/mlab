"""CNT-01 (R0-13): kontent fayllaridan import — idempotent, tranzaksiyali, aniq xatolar."""

from __future__ import annotations

import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from apps.courses.content import PRIVATE_DIRS, ContentError, import_content, load_course
from apps.courses.models import Course, Lecture, LectureStep, Topic

pytestmark = pytest.mark.django_db

REPO_CONTENT = Path(settings.BASE_DIR).parent / "content"

LECTURE = """# Sinov ma'ruzasi

## Birinchi qadam

Matn 1.

## Ikkinchi qadam

```python
## bu sarlavha emas — kod ichida
print("salom")
```
"""


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    _write(root, "course.yaml", 'slug: test-kurs\ntitle: Test kurs\nversion: "1"\n')
    _write(root, "topics/M01-birinchi/meta.yaml", "code: M01\ntitle: Birinchi\norder: 1\n")
    _write(root, "topics/M01-birinchi/lecture.md", LECTURE)
    _write(root, "topics/M02-ikkinchi/meta.yaml", "code: M02\ntitle: Ikkinchi\norder: 2\n")
    _write(root, "topics/M02-ikkinchi/lecture.md", "# Ikkinchi\n\n## Yagona qadam\n\nMatn.\n")
    return root


def _snapshot() -> list[tuple[object, ...]]:
    return [
        *Course.objects.values_list(
            "id", "slug", "title", "version", "content_hash", "imported_at"
        ),
        *Topic.objects.values_list("id", "code", "title", "order"),
        *Lecture.objects.values_list("id", "title"),
        *LectureStep.objects.order_by("id").values_list(
            "id", "lecture_id", "order", "title", "body"
        ),
    ]


def test_cnt_01_import_creates_course_topics_lectures_steps(content: Path) -> None:
    report = import_content(content)
    course = Course.objects.get(slug="test-kurs")
    assert course.version == "1"
    assert len(course.content_hash) == 64
    assert [t.code for t in course.topics.all()] == ["M01", "M02"]
    lecture = Lecture.objects.get(topic__code="M01")
    assert lecture.title == "Sinov ma'ruzasi"
    steps = list(lecture.steps.all())
    assert [(s.order, s.title) for s in steps] == [(1, "Birinchi qadam"), (2, "Ikkinchi qadam")]
    assert "## bu sarlavha emas" in steps[1].body  # kod bloki ichidagi ## qadam emas
    assert report.created == {"course": 1, "topic": 2, "lecture": 2, "step": 3}


def test_cnt_01_import_is_idempotent(content: Path) -> None:
    import_content(content)
    before = _snapshot()
    report = import_content(content)
    assert not report.changed
    assert _snapshot() == before


def test_cnt_01_reimport_updates_and_deletes(content: Path) -> None:
    import_content(content)
    first_hash = Course.objects.get().content_hash
    _write(
        content, "topics/M01-birinchi/lecture.md", "# Yangi nom\n\n## Faqat bitta\n\nYangi matn.\n"
    )
    shutil.rmtree(content / "topics/M02-ikkinchi")
    report = import_content(content)
    assert report.updated == {"course": 1, "lecture": 1, "step": 1}
    assert report.deleted == {"topic": 1, "step": 1}
    assert list(Topic.objects.values_list("code", flat=True)) == ["M01"]
    step = LectureStep.objects.get()
    assert (step.title, step.body) == ("Faqat bitta", "Yangi matn.")
    assert Course.objects.get().content_hash != first_hash


def test_cnt_01_topic_order_swap(content: Path) -> None:
    import_content(content)
    _write(content, "topics/M01-birinchi/meta.yaml", "code: M01\ntitle: Birinchi\norder: 2\n")
    _write(content, "topics/M02-ikkinchi/meta.yaml", "code: M02\ntitle: Ikkinchi\norder: 1\n")
    import_content(content)
    assert list(Topic.objects.values_list("code", flat=True)) == ["M02", "M01"]


@pytest.mark.parametrize(
    ("rel", "text", "where", "message"),
    [
        ("course.yaml", "slug: x\ntitle: [yopilmagan\n", "course.yaml:3", "YAML xatosi"),
        ("course.yaml", "slug: x\ntitle: T\n", "course.yaml:1", "'version' kaliti yo'q"),
        ("course.yaml", "slug: x\ntitle: T\nversion: 1\n", "course.yaml:3", "'version'"),
        ("course.yaml", 'slug: X Y\ntitle: T\nversion: "1"\n', "course.yaml:1", "slug"),
        ("course.yaml", 'slug: x\ntitle: T\nversion: "1"\ntitel: y\n', "course.yaml:4", "noma'lum"),
        ("course.yaml", "- bir\n- ikki\n", "course.yaml:1", "obyekt"),
        (
            "topics/M02-ikkinchi/meta.yaml",
            "code: M01\ntitle: X\norder: 2\n",
            "topics/M02-ikkinchi/meta.yaml:1",
            "papka nomi",
        ),
        (
            "topics/M02-ikkinchi/meta.yaml",
            "code: M02\ntitle: X\norder: 1\n",
            "topics/M02-ikkinchi/meta.yaml:3",
            "order takrorlangan",
        ),
        (
            "topics/M02-ikkinchi/meta.yaml",
            "code: m2\ntitle: X\norder: 2\n",
            "topics/M02-ikkinchi/meta.yaml:1",
            "kod formati",
        ),
        (
            "topics/M02-ikkinchi/meta.yaml",
            "code: M02\ntitle: '  '\norder: 2\n",
            "topics/M02-ikkinchi/meta.yaml:2",
            "bo'sh",
        ),
        (
            "topics/M02-ikkinchi/meta.yaml",
            "code: M02\ntitle: X\norder: 0\n",
            "topics/M02-ikkinchi/meta.yaml:3",
            "order 1",
        ),
        ("topics/M02-ikkinchi/lecture.md", "Sarlavhasiz\n", "lecture.md:1", "boshlanishi"),
        ("topics/M02-ikkinchi/lecture.md", "# T\n\nkirish\n## Q\n\nm\n", "lecture.md:3", "oldin"),
        (
            "topics/M02-ikkinchi/lecture.md",
            "# T\n\n## Bo'sh\n\n## Q\n\nm\n",
            "lecture.md:3",
            "bo'sh",
        ),
        ("topics/M02-ikkinchi/lecture.md", "# T\n", "lecture.md", "kamida bitta"),
        (
            "topics/M02-ikkinchi/lecture.md",
            "# T\n\n## Q\n\n```\nkod\n",
            "lecture.md:6",
            "yopilmagan",
        ),
        ("topics/M02-ikkinchi/lecture.md", "## Q\n\nm\n", "lecture.md:1", "avval"),
    ],
)
def test_cnt_01_invalid_content_reports_file_and_line_and_keeps_db(
    content: Path, rel: str, text: str, where: str, message: str
) -> None:
    import_content(content)
    before = _snapshot()
    _write(content, rel, text)
    with pytest.raises(ContentError) as exc:
        import_content(content)
    assert where in str(exc.value)
    assert message in str(exc.value)
    assert _snapshot() == before


def test_cnt_01_missing_files_reported(content: Path) -> None:
    (content / "topics/M02-ikkinchi/lecture.md").unlink()
    with pytest.raises(ContentError, match=r"topics/M02-ikkinchi/lecture.md: fayl topilmadi"):
        load_course(content)
    with pytest.raises(ContentError, match="papka topilmadi"):
        load_course(content / "yoq")


def test_cnt_01_non_utf8_reported(content: Path) -> None:
    (content / "topics/M02-ikkinchi/lecture.md").write_bytes(b"# \xff\xfe\n")
    with pytest.raises(ContentError, match="UTF-8"):
        load_course(content)


def test_cnt_01_yaml_tags_cannot_build_python_objects(content: Path) -> None:
    _write(content, "course.yaml", 'slug: x\ntitle: !!python/object/apply:os.system ["id"]\n')
    with pytest.raises(ContentError, match="YAML xatosi"):
        load_course(content)


def test_agr_05_private_dirs_never_imported(content: Path) -> None:
    secret = "MAXFIY-YECHIM-123"
    for private in PRIVATE_DIRS:
        _write(content, f"topics/M01-birinchi/{private}/x.py", secret)
    import_content(content)
    assert not LectureStep.objects.filter(body__contains=secret).exists()
    assert PRIVATE_DIRS == ("tests/hidden", "solutions")


def test_cnt_01_repo_content_imports(capsys: pytest.CaptureFixture[str]) -> None:
    # content/ dagi haqiqiy kontent har PR'da import testidan o'tadi.
    out = StringIO()
    call_command("import_content", str(REPO_CONTENT), stdout=out)
    assert "Import tugadi." in out.getvalue()
    lecture = Lecture.objects.get(topic__code="M01")
    assert lecture.steps.count() >= 5
    out = StringIO()
    call_command("import_content", str(REPO_CONTENT), stdout=out)
    assert "O'zgarish yo'q." in out.getvalue()


def test_cnt_01_command_error_message(content: Path) -> None:
    _write(content, "course.yaml", "slug: [\n")
    with pytest.raises(CommandError, match=r"baza o'zgarmadi: course\.yaml:\d+"):
        call_command("import_content", str(content))
