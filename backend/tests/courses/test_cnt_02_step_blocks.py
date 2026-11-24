"""CNT-02 (I2-02): ma'ruza qadamlarida rasm, "O'zing sinab ko'r" kod bloki va tezkor savol."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from apps.courses.content import ContentError, import_content, load_course
from apps.courses.models import MAX_IMAGE_BYTES, Course, LectureImage, LectureStep

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 64
WEBP = b"RIFF\0\0\0\0WEBPVP8 " + b"\0" * 64

QUIZ = """```quiz
question: Qaysi biri nazoratli o'qitish?
options:
  - Klasterlash
  - Regressiya
  - PCA
answer: B
explain: Regressiyada har misolning javobi bor.
```"""

LECTURE = f"""# Sinov

## Matn va rasm

Quyidagi rasmga qarang:

![Chiziqli bog'liqlik](images/line.png)

## Sinab ko'r

```python try
print(2 + 2)
```

## Savol

Bir savol:

{QUIZ}
"""


def _write(root: Path, rel: str, data: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
    return path


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    _write(root, "course.yaml", 'slug: test-kurs\ntitle: Test kurs\nversion: "1"\n')
    _write(root, "topics/M01-bir/meta.yaml", "code: M01\ntitle: Bir\norder: 1\n")
    _write(root, "topics/M01-bir/lecture.md", LECTURE)
    _write(root, "topics/M01-bir/images/line.png", PNG)
    return root


def _steps() -> list[LectureStep]:
    return list(LectureStep.objects.order_by("order"))


def test_cnt_02_try_block_kept_and_quiz_extracted(content: Path) -> None:
    import_content(content)
    text, code, quiz = _steps()
    assert "```python try\nprint(2 + 2)\n```" in code.body
    assert code.question is None
    assert "```quiz" not in quiz.body
    assert quiz.body == "Bir savol:"
    assert quiz.question == {
        "question": "Qaysi biri nazoratli o'qitish?",
        "options": ["Klasterlash", "Regressiya", "PCA"],
        "answer": 1,
        "explain": "Regressiyada har misolning javobi bor.",
    }
    assert text.question is None


def test_cnt_02_quiz_only_step_has_empty_body(content: Path) -> None:
    _write(content, "topics/M01-bir/lecture.md", f"# Sinov\n\n## Faqat savol\n\n{QUIZ}\n")
    import_content(content)
    (step,) = _steps()
    assert step.body == ""
    assert step.question is not None


def test_cnt_02_images_stored_in_db_with_hash(content: Path) -> None:
    import_content(content)
    image = LectureImage.objects.get()
    assert image.name == "line.png"
    assert image.content_type == "image/png"
    assert bytes(image.data) == PNG
    assert image.sha256 == hashlib.sha256(PNG).hexdigest()
    assert image.topic.code == "M01"


def test_cnt_02_reimport_idempotent_update_and_delete_images(content: Path) -> None:
    import_content(content)
    first_hash = Course.objects.get().content_hash
    assert not import_content(content).changed

    _write(content, "topics/M01-bir/images/line.png", PNG + b"x")
    report = import_content(content)
    assert report.updated.get("image") == 1
    assert Course.objects.get().content_hash != first_hash  # rasm baytlari versiyaga kiradi

    _write(
        content,
        "topics/M01-bir/lecture.md",
        LECTURE.replace("![Chiziqli bog'liqlik](images/line.png)", ""),
    )
    report = import_content(content)
    assert report.deleted.get("image") == 1
    assert not LectureImage.objects.exists()


def test_cnt_02_jpeg_and_webp_accepted(content: Path) -> None:
    _write(content, "topics/M01-bir/images/a.jpg", JPEG)
    _write(content, "topics/M01-bir/images/b.webp", WEBP)
    _write(
        content,
        "topics/M01-bir/lecture.md",
        "# S\n\n## Q\n\n![A](images/a.jpg) va ![B](images/b.webp)\n",
    )
    import_content(content)
    assert dict(LectureImage.objects.values_list("name", "content_type")) == {
        "a.jpg": "image/jpeg",
        "b.webp": "image/webp",
    }


def test_cnt_02_image_syntax_inside_code_fence_ignored(content: Path) -> None:
    _write(
        content,
        "topics/M01-bir/lecture.md",
        "# S\n\n## Q\n\n```text\n![yo'q](images/none.png)\n```\n",
    )
    import_content(content)
    assert not LectureImage.objects.exists()


@pytest.mark.parametrize(
    ("markdown", "files", "message", "line"),
    [
        ("![a](../M02/x.png)", {}, "images/", 5),
        ("![a](/etc/passwd)", {}, "images/", 5),
        ("![a](https://example.com/x.png)", {}, "images/", 5),
        ("![a](images/x.svg)", {"images/x.svg": b"<svg/>"}, "images/", 5),
        ("![a](images/none.png)", {}, "topilmadi", 5),
        ("![a](images/fake.png)", {"images/fake.png": JPEG}, "PNG", 5),
        ("![](images/line.png)", {}, "alt", 5),
        (
            "text\n\n![a](images/big.png)",
            {"images/big.png": PNG + b"\0" * MAX_IMAGE_BYTES},
            "KB",
            7,
        ),
    ],
)
def test_cnt_02_bad_images_rejected_with_line(
    content: Path, markdown: str, files: dict[str, bytes], message: str, line: int
) -> None:
    for rel, data in files.items():
        _write(content, f"topics/M01-bir/{rel}", data)
    _write(content, "topics/M01-bir/lecture.md", f"# S\n\n## Q\n\n{markdown}\n")
    with pytest.raises(ContentError) as exc:
        load_course(content)
    assert exc.value.path == "topics/M01-bir/lecture.md"
    assert exc.value.line == line
    assert message in exc.value.message


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("question: Savol?\noptions: [A]\nanswer: A", "2..6"),
        ("question: Savol?\noptions: [a, b]\nanswer: C", "answer"),
        ("question: Savol?\noptions: [a, b]\nanswer: 1", "answer"),
        ("options: [a, b]\nanswer: A", "question"),
        ("question: Savol?\noptions: [a, '']\nanswer: A", "bo'sh"),
        ("question: Savol?\noptions: [a, b]\nanswer: A\nextra: 1", "noma'lum"),
        ("question: [buzuq", "YAML"),
        ("- ro'yxat", "obyekt"),
    ],
)
def test_cnt_02_bad_quiz_rejected_with_line(content: Path, block: str, message: str) -> None:
    _write(content, "topics/M01-bir/lecture.md", f"# S\n\n## Q\n\nMatn\n\n```quiz\n{block}\n```\n")
    with pytest.raises(ContentError) as exc:
        load_course(content)
    assert exc.value.line == 7  # ```quiz qatori
    assert message in exc.value.message


def test_cnt_02_one_quiz_per_step(content: Path) -> None:
    _write(content, "topics/M01-bir/lecture.md", f"# S\n\n## Q\n\n{QUIZ}\n\n{QUIZ}\n")
    with pytest.raises(ContentError, match="bitta"):
        load_course(content)


def test_cnt_02_try_modifier_only_for_python(content: Path) -> None:
    _write(content, "topics/M01-bir/lecture.md", "# S\n\n## Q\n\n```bash try\nls\n```\n")
    with pytest.raises(ContentError, match="try") as exc:
        load_course(content)
    assert exc.value.line == 5


def test_cnt_02_step_must_have_text_or_quiz(content: Path) -> None:
    _write(content, "topics/M01-bir/lecture.md", "# S\n\n## Bo'sh\n\n## Keyingi\n\nMatn\n")
    with pytest.raises(ContentError, match="bo'sh"):
        load_course(content)
