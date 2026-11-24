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
from django.db.models import Field, ProtectedError
from django.utils import timezone

from apps.courses.aiken import AikenError, AikenQuestion, parse_aiken
from apps.courses.models import (
    MAX_IMAGE_BYTES,
    MAX_LATE_HOURS,
    AiMode,
    Course,
    ImageType,
    Lecture,
    LectureImage,
    LectureStep,
    Question,
    Topic,
)

# AGR-05: bu papkalar ma'ruza importida o'qilmaydi va hech qachon API'ga chiqmaydi.
PRIVATE_DIRS = ("tests/hidden", "solutions")

_CODE_RE = re.compile(r"^[A-Z][0-9]{2}\Z")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}\Z")
_FENCE_RE = re.compile(r"^(```|~~~)")
_INFO_RE = re.compile(r"^(?:```|~~~)\s*(.*)$")
_IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_IMAGE_PATH_RE = re.compile(r"^images/([A-Za-z0-9_-]+\.(png|jpg|jpeg|webp))\Z")
# Kengaytma -> (MIME, fayl boshidagi "magic bytes" tekshiruvi, nomi).
# SVG yo'q: u skript ichishi mumkin.
_IMAGE_KINDS: dict[str, tuple[str, Any, str]] = {
    "png": (ImageType.PNG, lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"), "PNG"),
    "jpg": (ImageType.JPEG, lambda b: b.startswith(b"\xff\xd8\xff"), "JPEG"),
    "jpeg": (ImageType.JPEG, lambda b: b.startswith(b"\xff\xd8\xff"), "JPEG"),
    "webp": (ImageType.WEBP, lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP", "WEBP"),
}
_QUIZ_LETTERS = "ABCDEF"


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
    question: dict[str, Any] | None = None


@dataclass(frozen=True)
class ImageData:
    name: str
    content_type: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True)
class TopicData:
    code: str
    title: str
    order: int
    lecture_title: str
    steps: tuple[StepData, ...]
    images: tuple[ImageData, ...] = ()
    questions: tuple[AikenQuestion, ...] = ()


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

    def read_bytes(self, path: Path) -> bytes:
        data = path.read_bytes()
        self.digest.update(self.rel(path).encode() + b"\0" + data + b"\0")
        return data

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


def _parse_quiz(rel: str, line: int, text: str) -> dict[str, Any]:
    """```quiz bloki (CNT-02): question, options (2..6), answer (harf), explain (ixtiyoriy)."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContentError(rel, line, f"quiz: YAML xatosi ({exc.__class__.__name__})") from exc
    if not isinstance(data, dict):
        raise ContentError(rel, line, "quiz: YAML obyekt (kalit: qiymat) bo'lishi kerak")
    unknown = set(data) - {"question", "options", "answer", "explain"}
    if unknown:
        raise ContentError(rel, line, f"quiz: noma'lum kalit '{sorted(map(str, unknown))[0]}'")
    question, options, answer = data.get("question"), data.get("options"), data.get("answer")
    explain = data.get("explain", "")
    if not isinstance(question, str) or not question.strip():
        raise ContentError(rel, line, "quiz: 'question' matni kerak")
    if not isinstance(options, list) or not 2 <= len(options) <= len(_QUIZ_LETTERS):
        raise ContentError(rel, line, f"quiz: 'options' 2..{len(_QUIZ_LETTERS)} ta variant")
    if not all(isinstance(o, str) and o.strip() for o in options):
        raise ContentError(rel, line, "quiz: variant bo'sh yoki matn emas")
    letters = _QUIZ_LETTERS[: len(options)]
    if not isinstance(answer, str) or len(answer) != 1 or answer not in letters:
        raise ContentError(rel, line, f"quiz: 'answer' bittasi: {', '.join(letters)}")
    if not isinstance(explain, str):
        raise ContentError(rel, line, "quiz: 'explain' matn bo'lishi kerak")
    return {
        "question": question.strip(),
        "options": [o.strip() for o in options],
        "answer": letters.index(answer),
        "explain": explain.strip(),
    }


def _load_image(
    reader: _Reader, topic_dir: Path, rel: str, line: int, alt: str, target: str
) -> ImageData:
    match = _IMAGE_PATH_RE.match(target.strip())
    if not match:
        raise ContentError(rel, line, "rasm yo'li 'images/<nom>.png|jpg|webp' bo'lishi kerak")
    if not alt.strip():
        raise ContentError(rel, line, "rasm uchun alt matn kerak (NFR-13)")
    name, ext = match.group(1), match.group(2)
    path = topic_dir / "images" / name
    if path.is_symlink() or not path.is_file():
        raise ContentError(rel, line, f"rasm fayli topilmadi: images/{name}")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ContentError(rel, line, f"rasm {MAX_IMAGE_BYTES // 1024} KB dan katta")
    content_type, check, label = _IMAGE_KINDS[ext]
    data = reader.read_bytes(path)
    if not data or not check(data):
        raise ContentError(rel, line, f"rasm fayli {label} formatida emas")
    return ImageData(name=name, content_type=str(content_type), data=data)


def _parse_step(
    reader: _Reader, topic_dir: Path, rel: str, numbered: list[tuple[int, str]]
) -> tuple[str, dict[str, Any] | None, list[ImageData]]:
    body: list[str] = []
    question: dict[str, Any] | None = None
    images: list[ImageData] = []
    fence: tuple[int, str, list[str]] | None = None  # (qator, info, quiz qatorlari)
    for number, line in numbered:
        if _FENCE_RE.match(line.lstrip()):
            if fence is None:
                info = _INFO_RE.match(line.lstrip())
                words = info.group(1).split() if info else []
                if "try" in words[1:] and words[0] != "python":
                    raise ContentError(rel, number, "'try' faqat python kod blokida")
                fence = (number, words[0] if words else "", [])
                if fence[1] == "quiz":
                    continue
            else:
                start, kind, quiz_lines = fence
                fence = None
                if kind == "quiz":
                    if question is not None:
                        raise ContentError(rel, start, "qadamda faqat bitta tezkor savol bo'ladi")
                    question = _parse_quiz(rel, start, "\n".join(quiz_lines))
                    continue
        elif fence is not None and fence[1] == "quiz":
            fence[2].append(line)
            continue
        elif fence is None:
            for match in _IMAGE_MD_RE.finditer(line):
                image = _load_image(reader, topic_dir, rel, number, match.group(1), match.group(2))
                if all(i.name != image.name for i in images):
                    images.append(image)
        body.append(line)
    return "\n".join(body).strip(), question, images


def _parse_lecture(
    reader: _Reader, topic_dir: Path, rel: str, text: str
) -> tuple[str, tuple[StepData, ...], tuple[ImageData, ...]]:
    lines = text.splitlines()
    title: str | None = None
    steps: list[tuple[int, str, list[tuple[int, str]]]] = []  # (qator, sarlavha, qatorlar)
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
            steps[-1][2].append((number, line))
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
    result: list[StepData] = []
    images: dict[str, ImageData] = {}
    for order, (number, step_title, numbered) in enumerate(steps, start=1):
        if not step_title:
            raise ContentError(rel, number, "qadam sarlavhasi bo'sh")
        body, question, step_images = _parse_step(reader, topic_dir, rel, numbered)
        if not body and question is None:
            raise ContentError(rel, number, f"'{step_title}' qadamining matni bo'sh")
        result.append(StepData(order=order, title=step_title, body=body, question=question))
        for image in step_images:
            images.setdefault(image.name, image)
    return title, tuple(result), tuple(images.values())


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
        lecture_title, steps, images = _parse_lecture(
            reader, topic_dir, reader.rel(lecture_path), reader.read(lecture_path)
        )
        questions: tuple[AikenQuestion, ...] = ()
        quiz_path = topic_dir / "quiz.aiken"
        if quiz_path.exists():
            quiz_rel = reader.rel(quiz_path)
            try:
                questions = parse_aiken(reader.read(quiz_path))
            except AikenError as exc:
                raise ContentError(quiz_rel, exc.line, exc.message) from exc
        topics.append(
            TopicData(code, meta["title"].strip(), order, lecture_title, steps, images, questions)
        )

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
        try:
            with transaction.atomic():
                Topic.objects.filter(pk__in=stale).delete()
        except ProtectedError as exc:
            # Guruhlarda kirish oynasi (keyin progress) bor mavzu jim o'chmaydi.
            codes = sorted(code for code, t in existing.items() if t.pk in stale)
            raise ContentError(
                "topics/",
                None,
                f"mavzu(lar) {', '.join(codes)} guruhlarda ishlatilmoqda — o'chirib bo'lmaydi",
            ) from exc
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
            values = {"title": step.title, "body": step.body, "question": step.question}
            if current is None:
                LectureStep.objects.create(lecture=lecture, order=step.order, **values)
                report.bump("created", "step")
            elif _sync(current, values):
                report.bump("updated", "step")
        _sync_images(topic, item.images, report)
        _sync_questions(topic, item.questions, report)
    return report


def _sync_questions(
    topic: Topic, questions: tuple[AikenQuestion, ...], report: ImportReport
) -> None:
    """CNT-05: tabiiy kalit bo'yicha yaratadi/yangilaydi; fayldan yo'qolgani arxivga
    o'tadi (o'chirilmaydi)."""
    existing = {q.key: q for q in Question.objects.filter(topic=topic)}
    wanted = {q.key for q in questions}
    for key, current in existing.items():
        if key not in wanted and _sync(current, {"is_active": False}):
            report.bump("updated", "question")
    for position, item in enumerate(questions, start=1):
        values = {
            "text": item.text,
            "options": list(item.options),
            "answer": item.answer,
            "position": position,
            "is_active": True,
        }
        found = existing.get(item.key)
        if found is None:
            Question.objects.create(topic=topic, key=item.key, **values)
            report.bump("created", "question")
        elif _sync(found, values):
            report.bump("updated", "question")


def _sync_images(topic: Topic, images: tuple[ImageData, ...], report: ImportReport) -> None:
    existing = {i.name: i for i in LectureImage.objects.filter(topic=topic).defer("data")}
    wanted = {i.name: i for i in images}
    stale = [i.pk for name, i in existing.items() if name not in wanted]
    if stale:
        LectureImage.objects.filter(pk__in=stale).delete()
        report.bump("deleted", "image", len(stale))
    for name, image in wanted.items():
        values = {
            "content_type": image.content_type,
            "sha256": image.sha256,
            "size": len(image.data),
            "data": image.data,
        }
        current = existing.get(name)
        if current is None:
            LectureImage.objects.create(topic=topic, name=name, **values)
            report.bump("created", "image")
        elif current.sha256 != image.sha256 or current.content_type != image.content_type:
            for key, value in values.items():
                setattr(current, key, value)
            current.save(update_fields=list(values))
            report.bump("updated", "image")


def import_content(root: Path) -> ImportReport:
    return apply(load_course(root))
