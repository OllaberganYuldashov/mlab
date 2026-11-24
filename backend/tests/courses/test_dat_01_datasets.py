"""DAT-01..03, LAB-04 (I2-19): datasetlar importi, litsenziya tekshiruvi va API."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.content import ContentError, import_content, load_course
from apps.courses.models import Dataset
from apps.sections.models import MembershipStatus
from tests.accounts.factories import make_user
from tests.sections.factories import make_membership, make_section

pytestmark = pytest.mark.django_db

CSV = b"x,y\n1,2\n3,4\n"
SHA = hashlib.sha256(CSV).hexdigest()


def _write(root: Path, rel: str, data: str | bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def _entry(**over: str) -> str:
    values = {
        "name": "toy",
        "title": "O'yinchoq",
        "description": "Ikki ustun.",
        "file": "toy.csv",
        "sha256": SHA,
        "source_url": "https://example.org/toy",
        "license": "CC0-1.0",
    } | over
    return "  - " + "\n    ".join(f"{k}: {v}" for k, v in values.items()) + "\n"


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    _write(root, "course.yaml", 'slug: k\ntitle: K\nversion: "1"\n')
    _write(root, "datasets/toy.csv", CSV)
    _write(root, "datasets/sources.yaml", "datasets:\n" + _entry())
    return root


def test_dat_01_import_and_idempotent(content: Path) -> None:
    report = import_content(content)
    assert report.created.get("dataset") == 1
    ds = Dataset.objects.get()
    assert (ds.name, ds.license, ds.sha256, bytes(ds.data), ds.rows, ds.columns) == (
        "toy",
        "CC0-1.0",
        SHA,
        CSV,
        2,
        ["x", "y"],
    )
    assert not import_content(content).changed
    _write(content, "datasets/sources.yaml", "datasets: []\n")
    assert import_content(content).deleted.get("dataset") == 1


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"license": "Proprietary"}, "litsenziya"),
        ({"sha256": "f" * 64}, "sha256"),
        ({"file": "../course.yaml"}, "fayl"),
        ({"file": "none.csv"}, "topilmadi"),
        ({"name": "Bad Name"}, "name"),
        ({"source_url": "ftp://x"}, "source_url"),
    ],
)
def test_dat_03_invalid_entries_rejected(content: Path, over: dict[str, str], message: str) -> None:
    _write(content, "datasets/sources.yaml", "datasets:\n" + _entry(**over))
    with pytest.raises(ContentError, match=message) as exc:
        load_course(content)
    assert exc.value.path == "datasets/sources.yaml"


def test_dat_01_duplicate_and_size_limit(content: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(content, "datasets/sources.yaml", "datasets:\n" + _entry() + _entry())
    with pytest.raises(ContentError, match="takror"):
        load_course(content)
    from apps.courses import content as module

    monkeypatch.setattr(module, "MAX_DATASET_BYTES", 5)
    _write(content, "datasets/sources.yaml", "datasets:\n" + _entry())
    with pytest.raises(ContentError, match="MB"):
        load_course(content)


def test_dat_01_repo_datasets_import() -> None:
    root = Path(settings.BASE_DIR).parent / "content"
    import_content(root)
    assert set(Dataset.objects.values_list("name", flat=True)) >= {"iris", "wine", "breast_cancer"}
    iris = Dataset.objects.get(name="iris")
    assert iris.rows == 150
    assert iris.columns[-1] == "species"


def _student() -> User:
    membership = make_membership(section=make_section(), student=make_user())
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership.student


def test_dat_02_list_detail_and_file(content: Path) -> None:
    import_content(content)
    client = APIClient()
    client.force_authenticate(_student())
    listed = client.get("/api/datasets").json()
    assert listed == [
        {
            "name": "toy",
            "title": "O'yinchoq",
            "description": "Ikki ustun.",
            "source_url": "https://example.org/toy",
            "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "rows": 2,
            "columns": ["x", "y"],
            "size": len(CSV),
        }
    ]
    response = client.get("/api/datasets/toy/file")
    assert response.status_code == 200
    assert response.content == CSV
    assert response["Content-Type"].startswith("text/csv")
    assert response["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/datasets/none/file").status_code == 404


def test_dat_01_non_members_forbidden(content: Path) -> None:
    import_content(content)
    client = APIClient()
    assert client.get("/api/datasets").status_code in (401, 403)
    client.force_authenticate(make_user())
    assert client.get("/api/datasets").status_code == 403
    assert client.get("/api/datasets/toy/file").status_code == 403
