import json
import re
from pathlib import Path

from django.db import migrations


TRACKS = [
    {"id": "safety", "no": 1, "title": "【全員必須】安全教育", "bookId": "book2", "hasTest": True},
    {"id": "dojo", "no": 2, "title": "【全員必須】安全道場体験", "bookId": None, "hasTest": False},
    {"id": "quality", "no": 3, "title": "【全員必須】品質基本ルール", "bookId": "book3", "hasTest": True},
    {"id": "change", "no": 4, "title": "【社員必須】DMS「変化点管理」", "bookId": "book6", "hasTest": True},
    {"id": "nonconform", "no": 5, "title": "【社員必須】DMS「不適合製品管理」", "bookId": "book5", "hasTest": True},
    {"id": "measure", "no": 6, "title": "【社員必須】DMS「計測機器管理」", "bookId": "book4", "hasTest": True},
    {"id": "identify", "no": 7, "title": "【社員必須】DMS「識別管理」", "bookId": "book1", "hasTest": True},
]


def load_app_data():
    root = Path(__file__).resolve().parents[4]
    prototype_path = root / "pm-ui" / "public" / "prototypes" / "education-test-certification" / "index.html"
    text = prototype_path.read_text(encoding="utf-8")
    match = re.search(r"const APP_DATA = (.*?);\s*const STORAGE", text, re.S)
    if not match:
        raise RuntimeError(f"APP_DATA を {prototype_path} から抽出できません。")
    return json.loads(match.group(1))


def seed_training_data(apps, schema_editor):
    TrainingBook = apps.get_model("quality", "TrainingBook")
    TrainingQuestion = apps.get_model("quality", "TrainingQuestion")
    TrainingExamDefinition = apps.get_model("quality", "TrainingExamDefinition")
    TrainingExamQuestion = apps.get_model("quality", "TrainingExamQuestion")
    TrainingTrack = apps.get_model("quality", "TrainingTrack")

    app_data = load_app_data()
    books_by_code = {}

    for book_order, book in enumerate(app_data.get("books", []), start=1):
        book_obj, _ = TrainingBook.objects.update_or_create(
            book_code=book["id"],
            defaults={
                "title": book.get("title", ""),
                "source_file": book.get("sourceFile", ""),
                "source_sheet": book.get("sourceSheet", ""),
                "question_count": int(book.get("questionCount") or 0),
                "display_order": book_order,
                "is_active": True,
            },
        )
        books_by_code[book["id"]] = book_obj

        question_codes = []
        question_by_code = {}
        for question_order, question in enumerate(book.get("questions", []), start=1):
            question_codes.append(question["id"])
            question_obj, _ = TrainingQuestion.objects.update_or_create(
                question_code=question["id"],
                defaults={
                    "book": book_obj,
                    "category": question.get("category", ""),
                    "question_type": question.get("type", ""),
                    "level": question.get("level", ""),
                    "importance": question.get("importance", ""),
                    "risk": question.get("risk", ""),
                    "question_text": question.get("question", ""),
                    "choices_json": question.get("choices", []),
                    "choices_raw": question.get("choicesRaw", ""),
                    "answer": question.get("answer", ""),
                    "explanation": question.get("explanation", ""),
                    "refs_json": question.get("refs", []),
                    "extra_json": question.get("extra", {}),
                    "display_order": question_order,
                    "is_active": True,
                },
            )
            question_by_code[question["id"]] = question_obj

        TrainingQuestion.objects.filter(book=book_obj).exclude(question_code__in=question_codes).update(is_active=False)

        exam_names = []
        for exam_order, exam in enumerate(book.get("exams", []), start=1):
            exam_names.append(exam["name"])
            exam_obj, _ = TrainingExamDefinition.objects.update_or_create(
                book=book_obj,
                name=exam["name"],
                defaults={
                    "source_sheet": exam.get("sourceSheet", ""),
                    "is_random": bool(exam.get("isRandom")),
                    "bank_all": bool(exam.get("bankAll")),
                    "random_question_count": 10,
                    "display_order": exam_order,
                    "is_active": True,
                },
            )

            if exam_obj.is_random:
                TrainingExamQuestion.objects.filter(exam=exam_obj).delete()
                continue

            exam_ids = exam.get("ids", [])
            TrainingExamQuestion.objects.filter(exam=exam_obj).exclude(
                question__question_code__in=exam_ids
            ).delete()
            for link_order, question_code in enumerate(exam_ids, start=1):
                question_obj = question_by_code.get(question_code)
                if not question_obj:
                    continue
                TrainingExamQuestion.objects.update_or_create(
                    exam=exam_obj,
                    question=question_obj,
                    defaults={"display_order": link_order},
                )

        TrainingExamDefinition.objects.filter(book=book_obj).exclude(name__in=exam_names).update(is_active=False)

    TrainingBook.objects.exclude(book_code__in=list(books_by_code.keys())).update(is_active=False)

    track_codes = []
    for track in TRACKS:
        track_codes.append(track["id"])
        TrainingTrack.objects.update_or_create(
            track_code=track["id"],
            defaults={
                "track_no": track["no"],
                "title": track["title"],
                "book": books_by_code.get(track["bookId"]),
                "has_test": bool(track["hasTest"]),
                "is_active": True,
            },
        )

    TrainingTrack.objects.exclude(track_code__in=track_codes).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0037_trainingbook_trainingexamdefinition_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_training_data, migrations.RunPython.noop),
    ]
