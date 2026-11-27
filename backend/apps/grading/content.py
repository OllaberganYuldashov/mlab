"""`content/labs/` — amaliy topshiriqlar importi (AGR-07, AGR-05; I3-02).

Tuzilma (`content/README.md`):
    labs/<A##>-<slug>/assignment.yaml          kod, nom, mavzu, shart ({parametr}),
                                               qadamlar va ballar (jami 100)
    labs/<A##>-<slug>/variants/<daraja>-<n>.yaml   params: {...}; har daraja kamida 5 variant;
                                               questions: tushunish savollari (INT-02, ixtiyoriy,
                                               bo'lsa kamida 2: text, options, answer)
    labs/<A##>-<slug>/tests/visible/<qadam>.py  brauzerda (ixtiyoriy)
    labs/<A##>-<slug>/tests/hidden/<qadam>.py   faqat sandbox'da (har qadamda majburiy)
    labs/<A##>-<slug>/solutions/                import qilinmaydi (CI tekshiruvi uchun)

Test funksiyalari: `def test_<nom>(ns, params)` — `ns` talaba kodi bajarilgandan keyingi
global nomlar.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.courses.content import ContentError, ImportReport, _Reader
from apps.courses.models import Course, Topic
from apps.grading.models import (
    Assignment,
    AssignmentStep,
    Level,
    StudentAssignment,
    TestFile,
    TestKind,
    Variant,
)

MIN_VARIANTS = 5  # AGR-07: har daraja kamida 5 variant
_DIR_RE = re.compile(r"^(A[0-9]{2})-[a-z0-9-]{1,50}\Z")
_CODE_RE = re.compile(r"^A[0-9]{2}\Z")
_VARIANT_RE = re.compile(r"^([a-z]+)-([0-9]{1,3})\.yaml\Z")
_STEP_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")


@dataclass(frozen=True)
class StepData:
    key: str
    title: str
    points: int
    visible: str | None
    hidden: str


@dataclass(frozen=True)
class LabData:
    code: str
    title: str
    topic: str
    statement: str
    challenge: str
    independent: str
    steps: tuple[StepData, ...]
    variants: tuple[tuple[str, int, dict[str, Any]], ...]
    # (daraja, raqam) -> tushunish savollari; javoblar faqat serverda (INT-02)
    questions: dict[tuple[str, int], list[dict[str, Any]]]


def _compile(rel: str, source: str) -> None:
    try:
        compile(source, rel, "exec")
    except SyntaxError as exc:
        raise ContentError(rel, exc.lineno, f"Python sintaksis xatosi: {exc.msg}") from exc


MIN_QUESTIONS = 2  # INT-02: topshirgandan keyin 2 ta savol


def _questions(rel: str, line: int | None, raw: list[Any]) -> list[dict[str, Any]]:
    """INT-02: [{text, options: [2..6 satr], answer: indeks}], kamida 2 ta."""
    if len(raw) < MIN_QUESTIONS:
        raise ContentError(rel, line, f"questions: kamida {MIN_QUESTIONS} ta savol")
    out = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or set(item) != {"text", "options", "answer"}:
            raise ContentError(rel, line, f"questions[{i}]: text, options, answer")
        text, options, answer = item["text"], item["options"], item["answer"]
        if not isinstance(text, str) or not text.strip():
            raise ContentError(rel, line, f"questions[{i}]: text bo'sh")
        if (
            not isinstance(options, list)
            or not 2 <= len(options) <= 6
            or not all(isinstance(o, str) and o.strip() for o in options)
            or len({o.strip() for o in options}) != len(options)
        ):
            raise ContentError(rel, line, f"questions[{i}]: options — 2..6 ta har xil satr")
        if type(answer) is not int or not 0 <= answer < len(options):
            raise ContentError(rel, line, f"questions[{i}]: answer — variant indeksi (0 dan)")
        out.append(
            {"text": text.strip(), "options": [o.strip() for o in options], "answer": answer}
        )
    return out


def _load_one(reader: _Reader, lab_dir: Path) -> LabData:
    rel_dir = reader.rel(lab_dir)
    match = _DIR_RE.match(lab_dir.name)
    path = lab_dir / "assignment.yaml"
    meta = reader.yaml(
        path,
        {
            "code": str,
            "title": str,
            "topic": str,
            "statement": str,
            "steps": list,
            "challenge": str,
            "independent": str,
        },
        optional=frozenset({"challenge", "independent"}),
    )
    rel, lines = reader.rel(path), meta["__lines__"]
    code = meta["code"]
    if not _CODE_RE.match(code) or not match or match.group(1) != code:
        raise ContentError(
            rel, lines["code"], "kod formati A## va papka nomi '<kod>-<slug>' bo'lishi kerak"
        )
    steps_raw = meta["steps"]
    keys: list[str] = []
    total = 0
    for step in steps_raw:
        if not isinstance(step, dict) or set(step) != {"key", "title", "points"}:
            raise ContentError(rel, lines["steps"], "har qadam: key, title, points")
        key, points = step["key"], step["points"]
        if not isinstance(key, str) or not _STEP_RE.match(key):
            raise ContentError(rel, lines["steps"], f"qadam kaliti noto'g'ri: {key!r}")
        if key in keys:
            raise ContentError(rel, lines["steps"], f"qadam kaliti takrorlangan: {key}")
        if not isinstance(points, int) or isinstance(points, bool) or not 1 <= points <= 100:
            raise ContentError(rel, lines["steps"], f"{key}: points 1..100 butun son")
        if not isinstance(step["title"], str) or not step["title"].strip():
            raise ContentError(rel, lines["steps"], f"{key}: title bo'sh")
        keys.append(key)
        total += points
    if not keys or total != 100:
        raise ContentError(
            rel, lines["steps"], f"qadamlar ballari jami 100 bo'lishi kerak (hozir {total})"
        )

    # Testlar: har qadamga yashirin test majburiy; begona fayl — xato.
    tests: dict[tuple[str, str], str] = {}
    for kind in (TestKind.VISIBLE, TestKind.HIDDEN):
        folder = lab_dir / "tests" / kind
        for file in sorted(folder.glob("*")) if folder.is_dir() else []:
            frel = reader.rel(file)
            if file.suffix != ".py" or file.stem not in keys:
                raise ContentError(
                    frel, None, f"test fayli nomi qadam kaliti bo'lishi kerak ({', '.join(keys)})"
                )
            source = reader.read(file)
            _compile(frel, source)
            tests[(file.stem, str(kind))] = source
    for key in keys:
        if (key, TestKind.HIDDEN) not in tests:
            raise ContentError(
                rel_dir, None, f"'{key}' qadami uchun yashirin test yo'q: tests/hidden/{key}.py"
            )

    # Variantlar: shartdagi har {parametr} har variantda bo'lishi kerak.
    placeholders = {name for _, name, _, _ in string.Formatter().parse(meta["statement"]) if name}
    variants: list[tuple[str, int, dict[str, Any]]] = []
    questions: dict[tuple[str, int], list[dict[str, Any]]] = {}
    folder = lab_dir / "variants"
    for file in sorted(folder.glob("*")) if folder.is_dir() else []:
        vrel = reader.rel(file)
        vm = _VARIANT_RE.match(file.name)
        if not vm or vm.group(1) not in Level.values:
            raise ContentError(
                vrel, None, f"variant fayli '<daraja>-<n>.yaml', daraja: {', '.join(Level.values)}"
            )
        data = reader.yaml(
            file, {"params": dict, "questions": list}, optional=frozenset({"questions"})
        )
        params = {k: v for k, v in data["params"].items()}
        missing = placeholders - set(params)
        if missing:
            raise ContentError(
                vrel,
                data["__lines__"]["params"],
                f"shartdagi parametr yo'q: {', '.join(sorted(missing))}",
            )
        variants.append((vm.group(1), int(vm.group(2)), params))
        if "questions" in data:
            questions[(vm.group(1), int(vm.group(2)))] = _questions(
                vrel, data["__lines__"]["questions"], data["questions"]
            )
    for level in Level.values:
        count = sum(1 for v in variants if v[0] == level)
        if count < MIN_VARIANTS:
            raise ContentError(
                rel_dir,
                None,
                f"'{level}' darajasida kamida {MIN_VARIANTS} variant kerak (hozir {count})",
            )
    steps = tuple(
        StepData(
            key=s["key"],
            title=s["title"].strip(),
            points=s["points"],
            visible=tests.get((s["key"], str(TestKind.VISIBLE))),
            hidden=tests[(s["key"], str(TestKind.HIDDEN))],
        )
        for s in steps_raw
    )
    return LabData(
        code=code,
        title=meta["title"].strip(),
        topic=meta["topic"].strip(),
        statement=meta["statement"],
        challenge=meta.get("challenge", "").strip(),
        independent=meta.get("independent", "").strip(),
        steps=steps,
        variants=tuple(sorted(variants)),
        questions=questions,
    )


def load_labs(root: Path) -> tuple[LabData, ...]:
    """`content/labs/` ni o'qiydi va tekshiradi; `solutions/` o'qilmaydi. Bazaga tegmaydi."""
    root = root.resolve()
    labs_dir = root / "labs"
    if not labs_dir.is_dir():
        return ()
    reader = _Reader(root)
    return tuple(_load_one(reader, d) for d in sorted(p for p in labs_dir.iterdir() if p.is_dir()))


def _sync(obj: Any, values: dict[str, Any]) -> bool:
    changed = [k for k, v in values.items() if getattr(obj, k) != v]
    for k in changed:
        setattr(obj, k, values[k])
    if changed:
        obj.save(update_fields=changed)
    return bool(changed)


@transaction.atomic
def apply_labs(
    course: Course, labs: tuple[LabData, ...], report: ImportReport | None = None
) -> ImportReport:
    report = report or ImportReport()
    topics = set(Topic.objects.filter(course=course).values_list("code", flat=True))
    existing = {a.code: a for a in Assignment.objects.filter(course=course)}
    wanted = {lab.code for lab in labs}
    stale = [a.pk for code, a in existing.items() if code not in wanted]
    used = StudentAssignment.objects.filter(assignment_id__in=stale).values_list(
        "assignment__code", flat=True
    )
    if code := next(iter(used), None):
        raise ContentError(
            f"labs/{code}", None, "topshiriq talabalarga berilgan — o'chirib bo'lmaydi"
        )
    if stale:
        Assignment.objects.filter(pk__in=stale).delete()
        report.bump("deleted", "assignment", len(stale))
    for lab in labs:
        if topics and lab.topic not in topics:
            raise ContentError(f"labs/{lab.code}", None, f"mavzu topilmadi: {lab.topic}")
        values = {
            "title": lab.title,
            "topic_code": lab.topic,
            "statement": lab.statement,
            "challenge": lab.challenge,
            "independent": lab.independent,
        }
        assignment = existing.get(lab.code)
        if assignment is None:
            assignment = Assignment.objects.create(course=course, code=lab.code, **values)
            report.bump("created", "assignment")
        elif _sync(assignment, values):
            report.bump("updated", "assignment")
        _sync_steps(assignment, lab, report)
        _sync_variants(assignment, lab, report)
    return report


def _sync_steps(assignment: Assignment, lab: LabData, report: ImportReport) -> None:
    steps = {s.key: s for s in AssignmentStep.objects.filter(assignment=assignment)}
    wanted = {s.key for s in lab.steps}
    stale = [s.pk for k, s in steps.items() if k not in wanted]
    if stale:
        AssignmentStep.objects.filter(pk__in=stale).delete()
        report.bump("deleted", "step", len(stale))
    for order, item in enumerate(lab.steps, start=1):
        step = steps.get(item.key)
        values = {"order": order, "title": item.title, "points": item.points}
        if step is None:
            step = AssignmentStep.objects.create(assignment=assignment, key=item.key, **values)
            report.bump("created", "step")
        elif _sync(step, values):
            report.bump("updated", "step")
        for kind, source in ((TestKind.VISIBLE, item.visible), (TestKind.HIDDEN, item.hidden)):
            current = TestFile.objects.filter(step=step, kind=kind).first()
            if source is None:
                if current is not None:
                    current.delete()
                    report.bump("deleted", "test")
            elif current is None:
                TestFile.objects.create(step=step, kind=kind, source=source)
                report.bump("created", "test")
            elif _sync(current, {"source": source}):
                report.bump("updated", "test")


def _sync_variants(assignment: Assignment, lab: LabData, report: ImportReport) -> None:
    existing = {(v.level, v.number): v for v in Variant.objects.filter(assignment=assignment)}
    wanted = {(level, number): params for level, number, params in lab.variants}
    stale = [v.pk for k, v in existing.items() if k not in wanted]
    used = Variant.objects.filter(pk__in=stale, student_assignments__isnull=False).first()
    if used is not None:
        raise ContentError(
            f"labs/{assignment.code}/variants/{used.level}-{used.number}.yaml",
            None,
            "variant talabaga berilgan — o'chirib bo'lmaydi",
        )
    if stale:
        Variant.objects.filter(pk__in=stale).delete()
        report.bump("deleted", "variant", len(stale))
    for (level, number), params in wanted.items():
        current = existing.get((level, number))
        values = {"params": params, "questions": lab.questions.get((level, number), [])}
        if current is None:
            Variant.objects.create(assignment=assignment, level=level, number=number, **values)
            report.bump("created", "variant")
        elif _sync(current, values):
            report.bump("updated", "variant")


def import_labs(root: Path, course: Course) -> ImportReport:
    return apply_labs(course, load_labs(root))
