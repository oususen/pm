from datetime import datetime
import random

from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_training import (
    TrainingBook,
    TrainingExamAttempt,
    TrainingExamDefinition,
    TrainingExamSession,
    TrainingQuestion,
    TrainingStepRecord,
    TrainingTrack,
)
from .serializers_training import (
    TrainingAttemptSerializer,
    TrainingBookSerializer,
    TrainingExamAttemptCreateSerializer,
    TrainingExamSessionStartSerializer,
    TrainingProgressSummarySerializer,
    TrainingQuestionPublicSerializer,
    TrainingStepRecordCreateSerializer,
    TrainingStepRecordSerializer,
    TrainingTrackSerializer,
    user_display_name,
)


def now_naive():
    return datetime.now()


def get_profile(user):
    try:
        return user.profile
    except Exception:
        return None


def apply_org_snapshot(instance, trainee):
    profile = get_profile(trainee)
    instance.trainee_department = getattr(profile, "department", None) if profile else None
    instance.trainee_division = getattr(profile, "division", None) if profile else None
    instance.trainee_group = getattr(profile, "group", None) if profile else None
    instance.trainee_team = getattr(profile, "team", None) if profile else None
    instance.trainee_unit = getattr(profile, "unit", None) if profile else None


def serialize_user_summary(user):
    profile = get_profile(user)
    return {
        "id": user.id,
        "name": user_display_name(user),
        "employee_code": getattr(profile, "employee_code", "") if profile else "",
        "division_name": getattr(getattr(profile, "division", None), "name", "") if profile else "",
        "team_name": getattr(getattr(profile, "team", None), "name", "") if profile else "",
        "unit_name": getattr(getattr(profile, "unit", None), "name", "") if profile else "",
    }


def resolve_exam_questions(exam):
    book = exam.book
    if exam.is_random:
        pool = list(book.questions.filter(is_active=True).order_by("display_order", "id"))
        if not pool:
            return []
        count = min(exam.random_question_count or 10, len(pool))
        return random.sample(pool, count)

    fixed_questions = [
        link.question
        for link in exam.exam_questions.select_related("question").order_by("display_order", "id")
        if link.question and link.question.is_active
    ]
    if fixed_questions:
        return fixed_questions

    return list(book.questions.filter(is_active=True).order_by("display_order", "id"))


class TrainingBookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        TrainingBook.objects.filter(is_active=True)
        .prefetch_related("exams")
        .order_by("display_order", "id")
    )
    serializer_class = TrainingBookSerializer
    permission_classes = [IsAuthenticated]


class TrainingTrackViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        TrainingTrack.objects.filter(is_active=True)
        .select_related("book")
        .order_by("track_no", "id")
    )
    serializer_class = TrainingTrackSerializer
    permission_classes = [IsAuthenticated]


class TrainingExamSessionStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TrainingExamSessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        exam = None
        if data.get("exam_id"):
            exam = get_object_or_404(
                TrainingExamDefinition.objects.select_related("book").prefetch_related("exam_questions__question"),
                pk=data["exam_id"],
                is_active=True,
            )
            book = exam.book
        elif data.get("book_id"):
            book = get_object_or_404(TrainingBook, pk=data["book_id"], is_active=True)
            exam = (
                TrainingExamDefinition.objects.filter(book=book, bank_all=True, is_active=True)
                .order_by("display_order", "id")
                .first()
            )
            if not exam:
                return Response({"detail": "試験定義が見つかりません。"}, status=status.HTTP_400_BAD_REQUEST)
            exam = TrainingExamDefinition.objects.prefetch_related("exam_questions__question").get(pk=exam.pk)
        else:
            return Response({"detail": "exam_id または book_id が必要です。"}, status=status.HTTP_400_BAD_REQUEST)

        trainee = get_object_or_404(User.objects.select_related("profile"), pk=data["trainee_user"], is_active=True)
        supervisor = None
        if data.get("supervisor_user"):
            supervisor = get_object_or_404(User.objects.select_related("profile"), pk=data["supervisor_user"], is_active=True)

        questions = resolve_exam_questions(exam)
        if not questions:
            return Response({"detail": "出題できる問題がありません。"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            session = TrainingExamSession(
                book=book,
                exam=exam,
                trainee=trainee,
                supervisor=supervisor,
                performed_at=data["performed_at"],
                location=data.get("location", ""),
                formal_exam=data.get("formal_exam", False),
                question_ids_json=[question.id for question in questions],
                created_by=request.user,
            )
            apply_org_snapshot(session, trainee)
            session.save()

        return Response(
            {
                "session_id": session.id,
                "book": TrainingBookSerializer(book).data,
                "exam": {
                    "id": exam.id,
                    "name": exam.name,
                    "is_random": exam.is_random,
                },
                "trainee": serialize_user_summary(trainee),
                "supervisor": serialize_user_summary(supervisor) if supervisor else None,
                "performed_at": session.performed_at,
                "location": session.location,
                "formal_exam": session.formal_exam,
                "pass_threshold_rate": 100,
                "questions": TrainingQuestionPublicSerializer(questions, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TrainingAttemptViewSet(viewsets.ModelViewSet):
    queryset = (
        TrainingExamAttempt.objects.select_related(
            "session",
            "book",
            "exam",
            "trainee",
            "supervisor",
            "trainee_division",
            "trainee_group",
            "trainee_team",
            "trainee_unit",
        )
        .order_by("-performed_at", "-id")
    )
    serializer_class = TrainingAttemptSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        trainee_id = self.request.query_params.get("trainee")
        book_id = self.request.query_params.get("book")
        formal_exam = self.request.query_params.get("formal_exam")
        if trainee_id:
            queryset = queryset.filter(trainee_id=trainee_id)
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        if formal_exam is not None and formal_exam != "":
            queryset = queryset.filter(formal_exam=str(formal_exam).lower() in ("1", "true", "yes"))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = TrainingExamAttemptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = get_object_or_404(
            TrainingExamSession.objects.select_related(
                "book",
                "exam",
                "trainee",
                "supervisor",
                "trainee_department",
                "trainee_division",
                "trainee_group",
                "trainee_team",
                "trainee_unit",
            ),
            pk=data["session_id"],
        )
        if session.is_completed:
            return Response({"detail": "この試験セッションは既に提出済みです。"}, status=status.HTTP_400_BAD_REQUEST)

        raw_answers = data.get("answers") or {}
        if not isinstance(raw_answers, dict):
            return Response({"detail": "answers はオブジェクトで送信してください。"}, status=status.HTTP_400_BAD_REQUEST)

        question_ids = session.question_ids_json or []
        questions = {
            question.id: question
            for question in TrainingQuestion.objects.filter(id__in=question_ids, is_active=True)
        }
        ordered_questions = [questions[qid] for qid in question_ids if qid in questions]
        if not ordered_questions:
            return Response({"detail": "採点対象の問題が見つかりません。"}, status=status.HTTP_400_BAD_REQUEST)

        question_results = []
        score = 0
        for question in ordered_questions:
            answer_value = raw_answers.get(str(question.id))
            if answer_value is None:
                answer_value = raw_answers.get(question.question_code)
            if answer_value is None:
                answer_value = raw_answers.get(question.id)
            answer_value = "" if answer_value is None else str(answer_value).strip()
            is_correct = answer_value == str(question.answer or "").strip()
            if is_correct:
                score += 1
            question_results.append(
                {
                    "question_id": question.id,
                    "question_code": question.question_code,
                    "question": question.question_text,
                    "answer": answer_value,
                    "correct_answer": question.answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )

        total = len(ordered_questions)
        rate = round(score / total * 100) if total else 0
        result = (
            TrainingExamAttempt.RESULT_PASS
            if total > 0 and score == total
            else TrainingExamAttempt.RESULT_RETRAIN
        )

        with transaction.atomic():
            attempt = TrainingExamAttempt(
                session=session,
                book=session.book,
                exam=session.exam,
                trainee=session.trainee,
                supervisor=session.supervisor,
                book_title=session.book.title if session.book_id else "",
                exam_name=session.exam.name if session.exam_id else "",
                performed_at=session.performed_at,
                location=session.location,
                formal_exam=session.formal_exam,
                score=score,
                total=total,
                rate=rate,
                result=result,
                answers_json={str(key): value for key, value in raw_answers.items()},
                question_results_json=question_results,
                graded_at=now_naive(),
                created_by=request.user,
                trainee_department=session.trainee_department,
                trainee_division=session.trainee_division,
                trainee_group=session.trainee_group,
                trainee_team=session.trainee_team,
                trainee_unit=session.trainee_unit,
            )
            attempt.save()

            session.is_completed = True
            session.completed_at = now_naive()
            session.save(update_fields=["is_completed", "completed_at"])

        output = self.get_serializer(attempt)
        return Response(output.data, status=status.HTTP_201_CREATED)


class TrainingStepRecordViewSet(viewsets.ModelViewSet):
    queryset = (
        TrainingStepRecord.objects.select_related(
            "trainee",
            "supervisor",
            "track",
            "trainee_division",
            "trainee_group",
            "trainee_team",
            "trainee_unit",
        )
        .order_by("-performed_at", "-id")
    )
    serializer_class = TrainingStepRecordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        trainee_id = self.request.query_params.get("trainee")
        track_id = self.request.query_params.get("track")
        step_type = self.request.query_params.get("step_type")
        if trainee_id:
            queryset = queryset.filter(trainee_id=trainee_id)
        if track_id:
            queryset = queryset.filter(track_id=track_id)
        if step_type:
            queryset = queryset.filter(step_type=step_type)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = TrainingStepRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trainee = get_object_or_404(User.objects.select_related("profile"), pk=data["trainee"], is_active=True)
        supervisor = None
        if data.get("supervisor"):
            supervisor = get_object_or_404(User.objects.select_related("profile"), pk=data["supervisor"], is_active=True)
        track = get_object_or_404(TrainingTrack, pk=data["track"], is_active=True)

        with transaction.atomic():
            record = TrainingStepRecord(
                trainee=trainee,
                supervisor=supervisor,
                track=track,
                step_type=data["step_type"],
                performed_at=data["performed_at"],
                location=data.get("location", ""),
                note=data.get("note", ""),
                created_by=request.user,
            )
            apply_org_snapshot(record, trainee)
            record.save()

        output = self.get_serializer(record)
        return Response(output.data, status=status.HTTP_201_CREATED)


class TrainingProgressSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trainee_id = request.query_params.get("trainee") or request.user.id
        trainee = get_object_or_404(User.objects.select_related("profile__division", "profile__team", "profile__unit"), pk=trainee_id)

        tracks = list(
            TrainingTrack.objects.filter(is_active=True)
            .select_related("book")
            .order_by("track_no", "id")
        )
        step_records = list(
            TrainingStepRecord.objects.filter(trainee=trainee)
            .select_related("track", "supervisor")
            .order_by("-performed_at", "-id")
        )
        attempts = list(
            TrainingExamAttempt.objects.filter(trainee=trainee, formal_exam=True)
            .select_related("book", "exam", "supervisor")
            .order_by("-performed_at", "-id")
        )

        latest_education = {}
        latest_certification = {}
        for record in step_records:
            key = record.track_id
            if record.step_type == TrainingStepRecord.STEP_EDUCATION and key not in latest_education:
                latest_education[key] = record
            if record.step_type == TrainingStepRecord.STEP_CERTIFICATION and key not in latest_certification:
                latest_certification[key] = record

        latest_pass_attempt = {}
        for attempt in attempts:
            if attempt.result != TrainingExamAttempt.RESULT_PASS:
                continue
            if attempt.book_id and attempt.book_id not in latest_pass_attempt:
                latest_pass_attempt[attempt.book_id] = attempt

        rows = []
        for track in tracks:
            test = latest_pass_attempt.get(track.book_id) if track.book_id and track.has_test else None
            education = latest_education.get(track.id)
            certification = latest_certification.get(track.id)
            rows.append(
                {
                    "track_id": track.id,
                    "track_code": track.track_code,
                    "no": track.track_no,
                    "title": track.title,
                    "has_test": track.has_test,
                    "book_id": track.book_id,
                    "book_title": track.book.title if track.book_id else "",
                    "education": (
                        {
                            "id": education.id,
                            "performed_at": education.performed_at,
                            "location": education.location,
                            "supervisor_name": user_display_name(education.supervisor),
                        }
                        if education
                        else None
                    ),
                    "test": (
                        {
                            "id": test.id,
                            "performed_at": test.performed_at,
                            "location": test.location,
                            "supervisor_name": user_display_name(test.supervisor),
                            "score": test.score,
                            "total": test.total,
                            "exam_name": test.exam_name,
                            "rate": test.rate,
                        }
                        if test
                        else None
                    ),
                    "certification": (
                        {
                            "id": certification.id,
                            "performed_at": certification.performed_at,
                            "location": certification.location,
                            "supervisor_name": user_display_name(certification.supervisor),
                        }
                        if certification
                        else None
                    ),
                    "can_certify": (not track.has_test) or bool(test),
                }
            )

        payload = {
            "trainee": serialize_user_summary(trainee),
            "rows": rows,
        }
        output = TrainingProgressSummarySerializer(payload)
        return Response(output.data)
