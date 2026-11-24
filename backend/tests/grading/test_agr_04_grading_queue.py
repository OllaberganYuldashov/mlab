"""AGR-02, AGR-04, AGR-06 (I3-06): Submission, baholash navbati, idempotentlik va qayta urinish.

Sandbox — `FakeSandbox` (talaba kodi testlarda ham hech qachon bajarilmaydi, AGR-03).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.courses.models import Topic
from apps.grading import service, tasks
from apps.grading.content import import_labs
from apps.grading.models import Assignment, StudentAssignment, Submission, SubmissionStatus
from apps.grading.sandbox import LauncherSandbox, SandboxUnavailable, fake
from apps.grading.variants import assign
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _approved
from tests.test_nfr_16_settings_fail_fast import DEV_ENV, STRONG_KEY, run_django

pytestmark = pytest.mark.django_db

HIDDEN_LOAD = "def test_shape(ns, params):\n    assert ns['df'].shape[0] > 0\n"


@pytest.fixture(autouse=True)
def _fresh_fake() -> Iterator[None]:
    fake.responses.clear()
    fake.calls.clear()
    yield
    fake.responses.clear()
    fake.calls.clear()


@pytest.fixture
def record(content: Path) -> StudentAssignment:  # noqa: F811
    membership = _approved()
    Topic.objects.create(course=membership.section.course, code="M02", title="T2", order=2)
    import_labs(content, membership.section.course)
    return assign(membership.student, Assignment.objects.get())


def _submit(record: StudentAssignment, code: str = "df = 1") -> Submission:
    dispatched: list[int] = []
    submission = service.enqueue(record, code, dispatch=dispatched.append)
    return submission


def _result(*tests: tuple[str, str, bool], status: str = "ok") -> dict[str, Any]:
    return {
        "status": status,
        "error": None,
        "stdout": "",
        "tests": [
            {"step": step, "kind": kind, "name": "t", "passed": passed, "message": "", "ms": 1}
            for step, kind, passed in tests
        ],
    }


def test_agr_06_each_attempt_is_a_record_and_dispatch_waits_for_commit(
    record: StudentAssignment, django_capture_on_commit_callbacks: Any
) -> None:
    dispatched: list[int] = []
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        first = service.enqueue(record, "a = 1", dispatch=dispatched.append)
        second = service.enqueue(record, "a = 2", dispatch=dispatched.append)
        assert dispatched == []  # commit'dan oldin navbatga qo'yilmaydi
    for callback in callbacks:
        callback()
    assert dispatched == [first.pk, second.pk]
    assert [s.status for s in Submission.objects.order_by("pk")] == ["queued", "queued"]
    assert service.queue_depth() == {"queued": 2, "running": 0}


def test_agr_02_grade_sends_all_tests_and_params_and_stores_score(
    record: StudentAssignment,
) -> None:
    submission = _submit(record)
    assert service.grade(submission.pk) == "done"
    submission.refresh_from_db()
    assert (submission.status, submission.score, submission.attempts) == ("done", 100, 1)
    assert submission.finished_at is not None
    assert submission.started_at is not None
    (payload,) = fake.calls
    assert payload["code"] == "df = 1"
    assert payload["params"] == record.variant.params
    assert payload["time_limit"] == service.TIME_LIMIT
    # Yashirin testlar sandbox'ga boradi (faqat shu yerda), ko'rinadigan ham.
    kinds = sorted((t["step"], t["kind"]) for t in payload["tests"])
    assert kinds == [("clean", "hidden"), ("load", "hidden"), ("load", "visible")]
    assert HIDDEN_LOAD in [t["source"] for t in payload["tests"]]


def test_agr_05_score_is_points_times_passed_share_per_step(record: StudentAssignment) -> None:
    # load (40): 2 testdan 1 o'tdi → 20; clean (60): 3 dan 2 → 40. Jami 60, butun son.
    fake.responses.append(
        _result(
            ("load", "visible", True),
            ("load", "hidden", False),
            ("clean", "hidden", True),
            ("clean", "hidden", True),
            ("clean", "hidden", False),
        )
    )
    submission = _submit(record)
    service.grade(submission.pk)
    submission.refresh_from_db()
    assert submission.score == 60
    assert submission.result is not None
    assert len(submission.result["tests"]) == 5


def test_agr_05_compute_score_edges() -> None:
    steps = [("a", 33), ("b", 67)]
    assert service.compute_score(_result(("a", "hidden", True)), steps) == 33  # b — natija yo'q
    third = _result(("b", "hidden", True), ("b", "hidden", False), ("b", "hidden", False))
    assert service.compute_score(third, steps) == 22  # 67 // 3
    assert service.compute_score(_result(), steps) == 0


def test_agr_02_code_error_is_a_result_not_a_retry(record: StudentAssignment) -> None:
    fake.responses.append(
        _result(("load", "visible", False), ("clean", "hidden", False), status="code_error")
    )
    submission = _submit(record)
    assert service.grade(submission.pk) == "done"
    submission.refresh_from_db()
    assert (submission.status, submission.score, submission.attempts) == ("done", 0, 1)


def test_agr_04_duplicate_delivery_grades_once(record: StudentAssignment) -> None:
    submission = _submit(record)
    assert service.grade(submission.pk) == "done"
    assert service.grade(submission.pk) == "skipped"
    assert service.grade(999_999) == "skipped"
    assert len(fake.calls) == 1
    submission.refresh_from_db()
    assert submission.attempts == 1


def test_agr_04_infra_error_retries_then_error(record: StudentAssignment) -> None:
    fake.responses.extend(SandboxUnavailable("down") for _ in range(service.MAX_ATTEMPTS))
    submission = _submit(record)
    for attempt in range(1, service.MAX_ATTEMPTS):
        with pytest.raises(service.RetryLater):
            service.grade(submission.pk)
        submission.refresh_from_db()
        assert (submission.status, submission.attempts) == ("queued", attempt)
    assert service.grade(submission.pk) == "error"
    submission.refresh_from_db()
    assert (submission.status, submission.error) == ("error", "sandbox_unavailable")
    assert submission.score is None
    assert submission.finished_at is not None
    assert len(fake.calls) == service.MAX_ATTEMPTS


def test_agr_04_infra_error_then_success(record: StudentAssignment) -> None:
    fake.responses.append(SandboxUnavailable("down"))
    submission = _submit(record)
    with pytest.raises(service.RetryLater):
        service.grade(submission.pk)
    assert service.grade(submission.pk) == "done"
    submission.refresh_from_db()
    assert (submission.status, submission.score, submission.attempts) == ("done", 100, 2)


@pytest.mark.parametrize(
    "response",
    [
        {"status": "bad_input", "error": "tests"},
        {"status": "ok", "tests": "yo'q"},
        {"status": "ok", "tests": [{"step": "load", "kind": "hidden", "passed": "ha"}]},
    ],
)
def test_agr_04_bad_runner_result_is_error_without_retry(
    record: StudentAssignment, response: dict[str, Any]
) -> None:
    fake.responses.append(response)
    submission = _submit(record)
    assert service.grade(submission.pk) == "error"
    submission.refresh_from_db()
    assert (submission.status, submission.error, submission.attempts) == ("error", "bad_result", 1)


def test_agr_04_stale_running_is_reclaimed_fresh_running_is_not(
    record: StudentAssignment,
) -> None:
    submission = _submit(record)
    Submission.objects.filter(pk=submission.pk).update(
        status=SubmissionStatus.RUNNING, started_at=timezone.now(), attempts=1
    )
    assert service.grade(submission.pk) == "skipped"  # boshqa worker hali ishlayapti
    Submission.objects.filter(pk=submission.pk).update(
        started_at=timezone.now() - service.STALE_RUNNING - timedelta(seconds=1)
    )
    assert service.grade(submission.pk) == "done"  # worker o'lgan — qayta egallandi
    submission.refresh_from_db()
    assert submission.attempts == 2


def test_agr_04_late_finish_of_reclaimed_attempt_is_ignored(record: StudentAssignment) -> None:
    submission = _submit(record)
    claimed = service._claim(submission.pk)
    assert claimed is not None
    # Boshqa worker shu orada qayta egalladi (attempts oshdi): eski urinish natijasi yozilmaydi.
    Submission.objects.filter(pk=submission.pk).update(attempts=claimed.attempts + 1)
    assert service._finish(claimed, status=SubmissionStatus.DONE, score=5, result={}) is False
    submission.refresh_from_db()
    assert (submission.status, submission.score) == ("running", None)


def test_agr_04_requeue_stale_dispatches_only_stuck(record: StudentAssignment) -> None:
    old = timezone.now() - timedelta(minutes=10)
    stuck_queued = _submit(record)
    Submission.objects.filter(pk=stuck_queued.pk).update(created_at=old)
    fresh = _submit(record)
    stuck_running = _submit(record)
    Submission.objects.filter(pk=stuck_running.pk).update(
        status=SubmissionStatus.RUNNING, started_at=old, attempts=1
    )
    done = _submit(record)
    Submission.objects.filter(pk=done.pk).update(created_at=old)
    service.grade(done.pk)
    dispatched: list[int] = []
    assert service.requeue_stale(dispatch=dispatched.append) == 2
    assert sorted(dispatched) == sorted([stuck_queued.pk, stuck_running.pk])
    assert fresh.pk not in dispatched
    assert service.requeue_stale(dispatch=dispatched.append, limit=1) == 1


def test_agr_04_schema_rejects_inconsistent_states(record: StudentAssignment) -> None:
    submission = _submit(record)
    for values in (
        {"status": "done"},  # ball va natijasiz
        {"status": "error", "finished_at": timezone.now()},  # sababsiz
        {"status": "running"},  # boshlanish vaqtisiz
        {"score": 101},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Submission.objects.filter(pk=submission.pk).update(**values)


def test_agr_04_celery_task_runs_grade_and_retries_on_infra_error(
    record: StudentAssignment,
) -> None:
    fake.responses.append(SandboxUnavailable("down"))
    submission = _submit(record)
    # Eager: retry shu jarayonda darhol qayta bajariladi.
    outcome = tasks.grade_submission.apply(args=(submission.pk,))
    assert outcome.get() == "done"
    submission.refresh_from_db()
    assert (submission.status, submission.attempts) == ("done", 2)
    assert tasks.requeue_stale_submissions.apply().get() == 0


def test_agr_04_backoff_grows_with_jitter_and_cap() -> None:
    assert 5 <= tasks.backoff(0) <= 10
    assert 20 <= tasks.backoff(2) <= 25
    assert 60 <= tasks.backoff(10) <= 65


def test_agr_04_celery_settings() -> None:
    assert settings.CELERY_WORKER_CONCURRENCY == 2
    assert settings.CELERY_TASK_ACKS_LATE is True
    assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True
    assert settings.CELERY_WORKER_PREFETCH_MULTIPLIER == 1
    assert tasks.grade_submission.acks_late is True


# --- LauncherSandbox: haqiqiy HTTP (lokal server), Docker'siz ---


class _Handler(BaseHTTPRequestHandler):
    reply: bytes = b"{}"
    status_code = 200
    received: list[dict[str, Any]] = []  # noqa: RUF012

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        type(self).received.append(json.loads(self.rfile.read(length)))
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.reply)

    def log_message(self, *_args: Any) -> None:
        return


@pytest.fixture
def launcher() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Handler.received = []
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_agr_04_launcher_posts_payload_and_parses_result(launcher: str) -> None:
    _Handler.reply, _Handler.status_code = json.dumps(_result(("a", "hidden", True))).encode(), 200
    assert LauncherSandbox(launcher + "/").run({"code": "x", "tests": []})["status"] == "ok"
    assert _Handler.received == [{"code": "x", "tests": []}]


@pytest.mark.parametrize(
    ("reply", "status_code"),
    [(b"not json", 200), (b"[]", 200), (b'{"x": 1}', 500), (b" " * 600_000, 200)],
)
def test_agr_04_launcher_bad_responses_are_infra_errors(
    launcher: str, reply: bytes, status_code: int
) -> None:
    _Handler.reply, _Handler.status_code = reply, status_code
    with pytest.raises(SandboxUnavailable):
        LauncherSandbox(launcher).run({})


def test_agr_04_launcher_unreachable_or_unset() -> None:
    with pytest.raises(SandboxUnavailable):
        LauncherSandbox("http://127.0.0.1:9").run({})
    with pytest.raises(SandboxUnavailable):
        LauncherSandbox("")
    with pytest.raises(SandboxUnavailable):
        LauncherSandbox("file:///etc/passwd")


def test_agr_03_prod_refuses_fake_sandbox() -> None:
    env = {
        **DEV_ENV,
        "SECRET_KEY": STRONG_KEY,
        "ALLOWED_HOSTS": "mlab.example.uz",
        "TRUSTED_PROXY_COUNT": "1",
        "SANDBOX_BACKEND": "fake",
    }
    result = run_django("config.settings.prod", env)
    assert result.returncode != 0
    assert "SANDBOX_BACKEND" in result.stderr
    bad = run_django("config.settings.dev", {**DEV_ENV, "SANDBOX_BACKEND": "docker"})
    assert bad.returncode != 0
