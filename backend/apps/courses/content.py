"""`content/` papkasini o'qish, tekshirish va bazaga yuklash (CNT-01, ADR-0002).

Ikki bosqich: `load_course()` faqat fayllarni o'qiydi va tekshiradi (bazaga tegmaydi),
`apply()` bitta
tranzaksiyada yozadi. Xato — `ContentError("fayl:qator: xabar")`, baza o'zgarmaydi.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml
from django.db import transaction
from django.db.models import Field
from django.utils import timezone

from apps.courses.models import MAX_LATE_HOURS, AiMode, Course, Lecture, LectureStep, Topic

# AGR-05: bu papkalar ma'ruza importida o'qilmaydi va hech qachon API'ga chiqmaydi.
PRIVATE_DIRS = ("tests/hidden", "solutions")

_CODE_RE = re.compile(r"^[A-Z][0-9]{2}\Z")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}\Z")
_FENCE_RE = re.compile(r"^(```|~~~)")


class ContentError(Exception):
    def __init__(self, path: str, line: int | None, message: str) -> None:
        self.path, self.line, self.message = path, line, message
        where = f"{path}:{line}" if line else path
        super().__init__(f"{where}: {message}")


@dataclass(frozen=True)
class StepData:
    order: int
    title: str
    body: str


@dataclass(frozen=True)
class TopicData:
    code: str
    title: str
    order: int
    lecture_title: str
    steps: tuple[StepData, ...]


@dataclass(frozen=True)
class CourseData:
    slug: str
    title: str
    version: str
    content_hash: str
    topics: tuple[TopicData, ...]
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportReport:
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    deleted: dict[str, int] = field(default_factory=dict)

    def bump(self, kind: str, model: str, n: int = 1) -> None:
        bucket = getattr(self, kind)
        bucket[model] = bucket.get(model, 0) + n

    @property
    def changed(self) -> bool:
        return (
            any(self.created.values()) or any(self.updated.values()) or any(self.deleted.values())
        )


# --- O'qish va tekshirish ---


class _Reader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.digest = hashlib.sha256()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read(self, path: Path) -> str:
        rel = self.rel(path)
        if not path.is_file():
            raise ContentError(rel, None, "fayl topilmadi")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ContentError(rel, None, "fayl UTF-8 emas") from exc
        self.digest.update(rel.encode() + b"\0" + text.encode() + b"\0")
        return text

    def yaml(
        self,
        path: Path,
        schema: dict[str, type | tuple[type, ...]],
        optional: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        rel, text = self.rel(path), self.read(path)
        try:
            node = yaml.compose(text, Loader=yaml.SafeLoader)
            data = yaml.safe_load(text)
        except yaml.MarkedYAMLError as exc:
            line = exc.problem_mark.line + 1 if exc.problem_mark else None
            raise ContentError(rel, line, f"YAML xatosi: {exc.problem}") from exc
        if not isinstance(node, yaml.MappingNode) or not isinstance(data, dict):
            raise ContentError(rel, 1, "YAML obyekt (kalit: qiymat) bo'lishi kerak")
        lines = {key.value: key.start_mark.line + 1 for key, _ in node.value}
        for key in data:
            if key not in schema:
                raise ContentError(rel, lines.get(str(key)), f"noma'lum kalit '{key}'")
        for key, expected in schema.items():
            if key not in data:
                if key in optional:
                    continue
                raise ContentError(rel, 1, f"'{key}' kaliti yo'q")
            value = data[key]
            if isinstance(value, bool) or not isinstance(value, expected):
                raise ContentError(rel, lines[key], f"'{key}' qiymati noto'g'ri turda")
            if isinstance(value, str) and not value.strip():
                raise ContentError(rel, lines[key], f"'{key}' bo'sh")
        return {**data, "__lines__": lines}


def _parse_lecture(rel: str, text: str) -> tuple[str, tuple[StepData, ...]]:
    lines = text.splitlines()
    title: str | None = None
    steps: list[tuple[int, str, list[str]]] = []  # (qator, sarlavha, matn qatorlari)
    in_fence = False
    for number, line in enumerate(lines, start=1):
        if _FENCE_RE.match(line.lstrip()):
            in_fence = not in_fence
        if not in_fence and line.startswith("# ") and title is None and not steps:
            title = line[2:].strip()
            continue
        if not in_fence and line.startswith("## "):
            if title is None:
                raise ContentError(rel, number, "avval '# Ma'ruza sarlavhasi' bo'lishi kerak")
            steps.append((number, line[3:].strip(), []))
            continue
        if steps:
            steps[-1][2].append(line)
        elif line.strip() and title is None:
            raise ContentError(rel, number, "fayl '# Ma'ruza sarlavhasi' bilan boshlanishi kerak")
        elif line.strip():
            raise ContentError(rel, number, "birinchi '## Qadam' dan oldin matn bo'lmasligi kerak")
    if in_fence:
        raise ContentError(rel, len(lines), "kod bloki (```) yopilmagan")
    if not title:
        raise ContentError(rel, 1, "'# Ma'ruza sarlavhasi' yo'q")
    if not steps:
        raise ContentError(rel, None, "kamida bitta '## Qadam' bo'lishi kerak")
    result = []
    for order, (number, step_title, body_lines) in enumerate(steps, start=1):
        body = "\n".join(body_lines).strip()
        if not step_title:
            raise ContentError(rel, number, "qadam sarlavhasi bo'sh")
        if not body:
            raise ContentError(rel, number, f"'{step_title}' qadamining matni bo'sh")
        result.append(StepData(order=order, title=step_title, body=body))
    return title, tuple(result)


def load_course(root: Path) -> CourseData:
    """`content/` ni o'qiydi va tekshiradi. Bazaga tegmaydi."""
    root = root.resolve()
    if not root.is_dir():
        raise ContentError(str(root), None, "papka topilmadi")
    reader = _Reader(root)
    course = reader.yaml(
        root / "course.yaml",
        {"slug": str, "title": str, "version": str, "defaults": dict},
        optional=frozenset({"defaults"}),
    )
    if not _SLUG_RE.match(course["slug"]):
        raise ContentError("course.yaml", course["__lines__"]["slug"], "slug: a-z, 0-9 va '-'")

    topics: list[TopicData] = []
    seen_codes: dict[str, str] = {}
    seen_orders: dict[int, str] = {}
    topics_dir = root / "topics"
    for topic_dir in (
        sorted(p for p in topics_dir.iterdir() if p.is_dir()) if topics_dir.is_dir() else []
    ):
        meta_path = topic_dir / "meta.yaml"
        meta = reader.yaml(meta_path, {"code": str, "title": str, "order": int})
        rel, lines = reader.rel(meta_path), meta["__lines__"]
        code, order = meta["code"], meta["order"]
        if not _CODE_RE.match(code):
            raise ContentError(rel, lines["code"], "kod formati: harf va 2 raqam (masalan, M01)")
        if not topic_dir.name.startswith(f"{code}-"):
            raise ContentError(rel, lines["code"], f"papka nomi '{code}-' bilan boshlanishi kerak")
        if order < 1:
            raise ContentError(rel, lines["order"], "order 1 dan boshlanadi")
        if code in seen_codes:
            raise ContentError(rel, lines["code"], f"kod takrorlangan ({seen_codes[code]})")
        if order in seen_orders:
            raise ContentError(rel, lines["order"], f"order takrorlangan ({seen_orders[order]})")
        seen_codes[code], seen_orders[order] = rel, rel
        lecture_path = topic_dir / "lecture.md"
        lecture_title, steps = _parse_lecture(reader.rel(lecture_path), reader.read(lecture_path))
        topics.append(TopicData(code, meta["title"].strip(), order, lecture_title, steps))

    return CourseData(
        slug=course["slug"],
        title=course["title"].strip(),
        version=course["version"].strip(),
        content_hash=reader.digest.hexdigest(),
        topics=tuple(sorted(topics, key=lambda t: t.order)),
        defaults=_parse_defaults(course.get("defaults"), course["__lines__"].get("defaults")),
    )


# SET: kurs default sozlamalari — kalit: (tur, tekshiruv, xato matni).
_DEFAULTS: dict[str, tuple[type, Any, str]] = {
    "ai_enabled": (bool, lambda v: True, "true yoki false"),
    "ai_max_mode": (str, lambda v: v in AiMode.values, f"bittasi: {', '.join(AiMode.values)}"),
    "practice_after_close": (bool, lambda v: True, "true yoki false"),
    "late_hours": (int, lambda v: 0 <= v <= MAX_LATE_HOURS, f"0..{MAX_LATE_HOURS} soat"),
    "late_penalty_percent": (int, lambda v: 0 <= v <= 100, "0..100"),
    "chat_enabled": (bool, lambda v: True, "true yoki false"),
}


def _parse_defaults(raw: Any, line: int | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ContentError(
            "course.yaml", line, "'defaults' kalit: qiymat ko'rinishida bo'lishi kerak"
        )
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in _DEFAULTS:
            raise ContentError("course.yaml", line, f"defaults: noma'lum kalit '{key}'")
        expected, valid, hint = _DEFAULTS[key]
        # bool int'ning bolasi — `late_hours: true` ni rad etish uchun turini aniq solishtiramiz.
        if type(value) is not expected or not valid(value):
            raise ContentError("course.yaml", line, f"defaults.{key}: {hint}")
        result[key] = value
    return result


# --- Bazaga yozish ---


def _sync(obj: Any, values: dict[str, Any]) -> bool:
    changed = [name for name, value in values.items() if getattr(obj, name) != value]
    for name in changed:
        setattr(obj, name, values[name])
    if changed:
        obj.save(update_fields=changed)
    return bool(changed)


@transaction.atomic
def apply(data: CourseData) -> ImportReport:
    """Idempotent: bir xil fayllarni qayta import qilish hech narsani o'zgartirmaydi."""
    report = ImportReport()
    course = Course.objects.select_for_update().filter(slug=data.slug).first()
    # Fayldan olib tashlangan default — model default'iga qaytadi (fayl — yagona manba).
    defaults = {
        name: data.defaults.get(
            name, cast("Field[Any, Any]", Course._meta.get_field(name)).get_default()
        )
        for name in _DEFAULTS
    }
    if course is None:
        course = Course.objects.create(
            slug=data.slug,
            title=data.title,
            version=data.version,
            content_hash=data.content_hash,
            **defaults,
        )
        report.bump("created", "course")
    elif _sync(
        course,
        {
            "title": data.title,
            "version": data.version,
            "content_hash": data.content_hash,
            **defaults,
        },
    ):
        _sync(course, {"imported_at": timezone.now()})
        report.bump("updated", "course")

    existing = {t.code: t for t in Topic.objects.filter(course=course)}
    wanted = {t.code for t in data.topics}
    stale = [t.pk for code, t in existing.items() if code not in wanted]
    if stale:
        Topic.objects.filter(pk__in=stale).delete()
        report.bump("deleted", "topic", len(stale))

    for item in data.topics:
        topic = existing.get(item.code)
        if topic is None:
            topic = Topic.objects.create(
                course=course, code=item.code, title=item.title, order=item.order
            )
            report.bump("created", "topic")
        elif _sync(topic, {"title": item.title, "order": item.order}):
            report.bump("updated", "topic")

        lecture = Lecture.objects.filter(topic=topic).first()
        if lecture is None:
            lecture = Lecture.objects.create(topic=topic, title=item.lecture_title)
            report.bump("created", "lecture")
        elif _sync(lecture, {"title": item.lecture_title}):
            report.bump("updated", "lecture")

        steps = {s.order: s for s in LectureStep.objects.filter(lecture=lecture)}
        extra = [s.pk for order, s in steps.items() if order > len(item.steps)]
        if extra:
            LectureStep.objects.filter(pk__in=extra).delete()
            report.bump("deleted", "step", len(extra))
        for step in item.steps:
            current = steps.get(step.order)
            if current is None:
                LectureStep.objects.create(
                    lecture=lecture, order=step.order, title=step.title, body=step.body
                )
                report.bump("created", "step")
            elif _sync(current, {"title": step.title, "body": step.body}):
                report.bump("updated", "step")
    return report


def import_content(root: Path) -> ImportReport:
    return apply(load_course(root))
