"""AGR-07, AGR-05 (I3-02): topshiriq formati va importi — yashirin testlar faqat serverda."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.courses.content import ContentError
from apps.grading.content import import_labs, load_labs
from apps.grading.models import Assignment, AssignmentStep, TestFile, Variant
from tests.sections.factories import make_course

pytestmark = pytest.mark.django_db

ASSIGNMENT = """code: A01
title: Pandas bilan tozalash
topic: M02
statement: |
  `{dataset}` datasetidagi `{column}` ustunini tozalang.
steps:
  - key: load
    title: Yuklash
    points: 40
  - key: clean
    title: Tozalash
    points: 60
challenge: Outlier'larni IQR bilan toping.
independent: Boshqa datasetda takrorlang.
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    lab = "labs/A01-pandas"
    _write(root, f"{lab}/assignment.yaml", ASSIGNMENT)
    for level in ("basic", "medium", "advanced"):
        for n in range(1, 6):
            _write(
                root,
                f"{lab}/variants/{level}-{n}.yaml",
                f"params:\n  dataset: iris\n  column: c{n}\n",
            )
    _write(
        root,
        f"{lab}/tests/visible/load.py",
        "def test_loaded(ns, params):\n    assert 'df' in ns\n",
    )
    _write(
        root,
        f"{lab}/tests/hidden/load.py",
        "def test_shape(ns, params):\n    assert ns['df'].shape[0] > 0\n",
    )
    _write(
        root,
        f"{lab}/tests/hidden/clean.py",
        "def test_no_nan(ns, params):\n    assert not ns['df'].isna().any().any()\n",
    )
    _write(root, f"{lab}/solutions/basic.py", "import mlab\ndf = mlab.load('iris')\n")
    return root


def test_agr_07_import_creates_assignment_steps_variants_tests(content: Path) -> None:
    course = make_course()
    report = import_labs(content, course)
    a = Assignment.objects.get()
    assert (a.code, a.title, a.topic_code) == ("A01", "Pandas bilan tozalash", "M02")
    assert "`{dataset}`" in a.statement
    assert list(AssignmentStep.objects.values_list("key", "points")) == [
        ("load", 40),
        ("clean", 60),
    ]
    assert Variant.objects.count() == 15
    assert Variant.objects.get(level="medium", number=3).params == {
        "dataset": "iris",
        "column": "c3",
    }
    assert TestFile.objects.filter(kind="hidden").count() == 2
    assert TestFile.objects.filter(kind="visible").count() == 1
    assert report.created["assignment"] == 1
    assert not import_labs(content, course).changed  # idempotent


def test_agr_05_solutions_never_imported(content: Path) -> None:
    import_labs(content, make_course())
    assert not TestFile.objects.filter(source__contains="mlab.load('iris')").exists()


def test_agr_07_reimport_updates_and_removes(content: Path) -> None:
    course = make_course()
    import_labs(content, course)
    _write(
        content,
        "labs/A01-pandas/tests/hidden/clean.py",
        "def test_x(ns, params):\n    assert True\n",
    )
    assert import_labs(content, course).updated.get("test") == 1
    (content / "labs/A01-pandas/variants/basic-5.yaml").unlink()
    with pytest.raises(ContentError, match="kamida 5"):
        load_labs(content)


@pytest.mark.parametrize(
    ("rel", "text", "message"),
    [
        ("assignment.yaml", ASSIGNMENT.replace("points: 60", "points: 50"), "100"),
        ("assignment.yaml", ASSIGNMENT.replace("code: A01", "code: B01"), "kod"),
        ("assignment.yaml", ASSIGNMENT.replace("{column}", "{yoq}"), "yoq"),
        ("assignment.yaml", ASSIGNMENT.replace("key: clean", "key: load"), "takror"),
        ("tests/hidden/clean.py", "def test_x(:\n", "sintaksis"),
        ("tests/hidden/extra.py", "def test_x(ns, params):\n    pass\n", "qadam"),
        ("variants/basic-1.yaml", "params: [1, 2]\n", "params"),
        ("variants/expert-1.yaml", "params: {}\n", "daraja"),
    ],
)
def test_agr_07_invalid_content_reported(content: Path, rel: str, text: str, message: str) -> None:
    _write(content, f"labs/A01-pandas/{rel}", text)
    with pytest.raises(ContentError, match=message):
        load_labs(content)


def test_agr_07_every_step_needs_hidden_test(content: Path) -> None:
    (content / "labs/A01-pandas/tests/hidden/clean.py").unlink()
    with pytest.raises(ContentError, match="yashirin"):
        load_labs(content)


def test_agr_07_no_labs_dir_is_fine(tmp_path: Path) -> None:
    assert load_labs(tmp_path) == ()
