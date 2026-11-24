"""CNT-05 (I2-06): Aiken formatidagi testlarni import qilish va savollar banki."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.courses.aiken import AikenError, parse_aiken
from apps.courses.content import ContentError, import_content, load_course
from apps.courses.models import Question

pytestmark = pytest.mark.django_db

AIKEN = """Qaysi algoritm nazoratli?
A) k-means
B) Chiziqli regressiya
C) PCA
ANSWER: B

O'qitish to'plami nima uchun kerak?
A. Modelni o'qitish uchun
B. Faqat tekshirish uchun
ANSWER: A
"""


def test_cnt_05_parse_basic_with_both_option_styles() -> None:
    questions = parse_aiken(AIKEN)
    assert [q.text for q in questions] == [
        "Qaysi algoritm nazoratli?",
        "O'qitish to'plami nima uchun kerak?",
    ]
    assert questions[0].options == ("k-means", "Chiziqli regressiya", "PCA")
    assert questions[0].answer == 1
    assert questions[1].answer == 0
    assert questions[0].line == 1
    assert questions[1].line == 7


def test_cnt_05_bom_crlf_and_multiline_question() -> None:
    text = "﻿Birinchi qator\r\nikkinchi qator?\r\nA) ha\r\nB) yo'q\r\nANSWER: A\r\n"
    (q,) = parse_aiken(text)
    assert q.text == "Birinchi qator\nikkinchi qator?"
    assert q.options == ("ha", "yo'q")


def test_cnt_05_uzbek_apostrophes_preserved_but_key_is_nfc() -> None:
    decomposed = "Oʻzbek tili? Café"
    composed = "Oʻzbek tili? Café"
    (a,) = parse_aiken(f"{decomposed}\nA) x\nB) y\nANSWER: A\n")
    (b,) = parse_aiken(f"{composed}\nA) x\nB) y\nANSWER: A\n")
    assert "ʻ" in a.text  # oʻ (U+02BB) o'zgarmaydi
    assert a.key == b.key


@pytest.mark.parametrize(
    ("text", "line", "message"),
    [
        ("Savol?\nA) bir\nANSWER: A\n", 3, "2..6"),
        ("Savol?\nA) bir\nB) ikki\nANSWER: C\n", 4, "ANSWER"),
        ("Savol?\nA) bir\nB) ikki\n", 3, "ANSWER"),
        ("Savol?\nA) bir\nC) ikki\nANSWER: A\n", 3, "B"),
        ("A) bir\nB) ikki\nANSWER: A\n", 1, "savol"),
        ("Savol?\nA)\nB) ikki\nANSWER: A\n", 2, "bo'sh"),
        ("Savol?\nA) bir\nB) ikki\nANSWER: A\nortiqcha\n", 5, "bo'sh qator"),
        ("Savol?\nA) bir\nB) bir\nANSWER: A\n", 3, "takror"),
        ("Savol?\nA) a\nB) b\nANSWER: A\n\nSavol?\nA) a\nB) b\nANSWER: B\n", 6, "takror"),
        ("", None, "savol yo'q"),
        ("S?\nA) a\nB) b\nC) c\nD) d\nE) e\nF) f\nG) g\nANSWER: A\n", 8, "2..6"),
        ("S?\nANSWER: A\n", 2, "ANSWER"),
    ],
)
def test_cnt_05_errors_have_line_numbers(text: str, line: int | None, message: str) -> None:
    with pytest.raises(AikenError) as exc:
        parse_aiken(text)
    assert exc.value.line == line
    assert message in exc.value.message


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    _write(root, "course.yaml", 'slug: test-kurs\ntitle: Test kurs\nversion: "1"\n')
    _write(root, "topics/M01-bir/meta.yaml", "code: M01\ntitle: Bir\norder: 1\n")
    _write(root, "topics/M01-bir/lecture.md", "# Bir\n\n## Qadam\n\nMatn.\n")
    _write(root, "topics/M01-bir/quiz.aiken", AIKEN)
    return root


def test_cnt_05_import_creates_question_bank(content: Path) -> None:
    report = import_content(content)
    assert report.created.get("question") == 2
    first, second = Question.objects.order_by("position")
    assert first.topic.code == "M01"
    assert first.options == ["k-means", "Chiziqli regressiya", "PCA"]
    assert first.answer == 1
    assert first.position == 1
    assert first.is_active
    assert second.position == 2


def test_cnt_05_reimport_idempotent_update_and_archive(content: Path) -> None:
    import_content(content)
    assert not import_content(content).changed

    # Variant matni o'zgardi — o'sha savol (kalit matndan) yangilanadi.
    _write(
        content,
        "topics/M01-bir/quiz.aiken",
        AIKEN.replace("B) Chiziqli regressiya", "B) Regressiya"),
    )
    report = import_content(content)
    assert report.updated.get("question") == 1
    assert Question.objects.count() == 2

    # Fayldan olib tashlangan savol o'chirilmaydi — arxivlanadi (keyingi urinishlar tarixi uchun).
    _write(content, "topics/M01-bir/quiz.aiken", AIKEN.split("\n\n")[1])
    report = import_content(content)
    assert report.updated.get("question") == 2  # biri arxivga, biri pozitsiyasi o'zgardi
    archived = Question.objects.get(text="Qaysi algoritm nazoratli?")
    assert archived.is_active is False

    # Qaytarilsa — yana faol.
    _write(content, "topics/M01-bir/quiz.aiken", AIKEN)
    import_content(content)
    assert Question.objects.filter(is_active=True).count() == 2


def test_cnt_05_topic_without_quiz_file_is_fine(content: Path) -> None:
    (content / "topics/M01-bir/quiz.aiken").unlink()
    import_content(content)
    assert not Question.objects.exists()


def test_cnt_05_import_error_reports_file_and_line(content: Path) -> None:
    _write(content, "topics/M01-bir/quiz.aiken", "Savol?\nA) bir\nB) ikki\nANSWER: Z\n")
    with pytest.raises(ContentError) as exc:
        load_course(content)
    assert exc.value.path == "topics/M01-bir/quiz.aiken"
    assert exc.value.line == 4


def test_cnt_05_quiz_file_changes_content_hash(content: Path) -> None:
    before = load_course(content).content_hash
    _write(content, "topics/M01-bir/quiz.aiken", AIKEN.replace("PCA", "SVD"))
    assert load_course(content).content_hash != before
