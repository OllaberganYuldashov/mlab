"""CNT-03 (I2-05): ```visual bloki tekshiriladi va kanonik JSON'ga aylanadi."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.courses.content import ContentError, import_content, load_course
from apps.courses.models import LectureStep

pytestmark = pytest.mark.django_db


def _content(tmp_path: Path, block: str) -> Path:
    root = tmp_path / "content"
    (root / "topics/M01-bir").mkdir(parents=True)
    (root / "course.yaml").write_text('slug: k\ntitle: K\nversion: "1"\n', encoding="utf-8")
    (root / "topics/M01-bir/meta.yaml").write_text(
        "code: M01\ntitle: Bir\norder: 1\n", encoding="utf-8"
    )
    (root / "topics/M01-bir/lecture.md").write_text(
        f"# Bir\n\n## Vizual\n\nSlayderni suring:\n\n```visual\n{block}\n```\n", encoding="utf-8"
    )
    return root


def test_cnt_03_visual_block_becomes_canonical_json(tmp_path: Path) -> None:
    root = _content(tmp_path, "widget: line-fit\ntitle: Chiziq\npoints:\n  - [1, 2]\n  - [2, 4.5]")
    import_content(root)
    body = LectureStep.objects.get().body
    assert body.startswith("Slayderni suring:\n\n```visual\n")
    spec = json.loads(body.split("```visual\n")[1].split("\n```")[0])
    assert spec == {"widget": "line-fit", "title": "Chiziq", "points": [[1, 2], [2, 4.5]]}


def test_cnt_03_knn_params(tmp_path: Path) -> None:
    root = _content(tmp_path, "widget: knn\nseed: 7\nk_max: 15")
    import_content(root)
    assert '{"widget": "knn", "seed": 7, "k_max": 15}' in LectureStep.objects.get().body


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("widget: tsne", "widget"),
        ("widget: knn\npoints: [[1, 2], [3, 4]]", "noma'lum"),
        ("widget: line-fit\npoints: [[1, 2]]", "points"),
        ("widget: line-fit\npoints: [[1, true], [2, 3]]", "points"),
        ("widget: knn\nk_max: 99", "k_max"),
        ("widget: knn\nseed: -1", "seed"),
        ("widget: knn\ntitle: ''", "title"),
        ("- ro'yxat", "obyekt"),
        ("widget: [buzuq", "YAML"),
    ],
)
def test_cnt_03_invalid_visual_rejected_with_line(tmp_path: Path, block: str, message: str) -> None:
    with pytest.raises(ContentError) as exc:
        load_course(_content(tmp_path, block))
    assert exc.value.line == 7  # ```visual qatori
    assert message in exc.value.message
