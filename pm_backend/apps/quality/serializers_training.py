from django.contrib.auth.models import User
from rest_framework import serializers

from .models_training import (
    TrainingBook,
    TrainingExamAttempt,
    TrainingExamDefinition,
    TrainingExamSession,
    TrainingQuestion,
    TrainingStepRecord,
    TrainingTrack,
)


def user_display_name(user):
    if not user:
        return ""
    name = f"{user.last_name or ''} {user.first_name or ''}".strip()
    return name or user.username or user.email or f"ID:{user.id}"


class TrainingExamDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingExamDefinition
        fields = [
            "id",
            "name",
            "source_sheet",
            "is_random",
            "bank_all",
            "random_question_count",
            "display_order",
        ]


class TrainingBookSerializer(serializers.ModelSerializer):
    exams = TrainingExamDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingBook
        fields = [
            "id",
            "book_code",
            "title",
            "source_file",
            "source_sheet",
            "question_count",
            "material_url",
            "display_order",
            "exams",
        ]


class TrainingQuestionPublicSerializer(serializers.ModelSerializer):
    question = serializers.CharField(source="question_text", read_only=True)
    type = serializers.CharField(source="question_type", read_only=True)
    choices = serializers.JSONField(source="choices_json", read_only=True)
    refs = serializers.JSONField(source="refs_json", read_only=True)
    extra = serializers.JSONField(source="extra_json", read_only=True)

    class Meta:
        model = TrainingQuestion
        fields = [
            "id",
            "question_code",
            "category",
            "type",
            "level",
            "importance",
            "risk",
            "question",
            "choices",
            "choices_raw",
            "refs",
            "extra",
        ]


class TrainingTrackSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_code = serializers.CharField(source="book.book_code", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = TrainingTrack
        fields = [
            "id",
            "track_code",
            "track_no",
            "title",
            "book_id",
            "book_code",
            "book_title",
            "has_test",
        ]


class TrainingExamSessionStartSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(required=False, allow_null=True)
    book_id = serializers.IntegerField(required=False, allow_null=True)
    trainee_user = serializers.IntegerField()
    supervisor_user = serializers.IntegerField(required=False, allow_null=True)
    performed_at = serializers.DateTimeField()
    location = serializers.CharField(required=False, allow_blank=True, max_length=120)
    formal_exam = serializers.BooleanField(required=False, default=False)


class TrainingPracticeStartSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(required=False, allow_null=True)
    book_id = serializers.IntegerField(required=False, allow_null=True)


class TrainingPracticeGradeSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(required=False, allow_null=True)
    book_id = serializers.IntegerField(required=False, allow_null=True)
    question_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    answers = serializers.JSONField()


class TrainingExamAttemptCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    answers = serializers.JSONField()


class TrainingStepRecordCreateSerializer(serializers.Serializer):
    trainee = serializers.IntegerField()
    supervisor = serializers.IntegerField(required=False, allow_null=True)
    track = serializers.IntegerField()
    step_type = serializers.ChoiceField(choices=TrainingStepRecord.STEP_TYPE_CHOICES)
    performed_at = serializers.DateTimeField()
    location = serializers.CharField(required=False, allow_blank=True, max_length=120)
    note = serializers.CharField(required=False, allow_blank=True)


class TrainingAttemptSerializer(serializers.ModelSerializer):
    trainee_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    result_label = serializers.CharField(source="get_result_display", read_only=True)
    book_code = serializers.CharField(source="book.book_code", read_only=True)
    exam_id = serializers.IntegerField(source="exam.id", read_only=True)

    class Meta:
        model = TrainingExamAttempt
        fields = [
            "id",
            "session",
            "book",
            "book_code",
            "book_title",
            "exam",
            "exam_id",
            "exam_name",
            "trainee",
            "trainee_name",
            "supervisor",
            "supervisor_name",
            "performed_at",
            "location",
            "formal_exam",
            "score",
            "total",
            "rate",
            "result",
            "result_label",
            "answers_json",
            "question_results_json",
            "graded_at",
            "trainee_division",
            "trainee_group",
            "trainee_team",
            "trainee_unit",
        ]

    def get_trainee_name(self, obj):
        return user_display_name(obj.trainee)

    def get_supervisor_name(self, obj):
        return user_display_name(obj.supervisor)


class TrainingStepRecordSerializer(serializers.ModelSerializer):
    trainee_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    step_type_label = serializers.CharField(source="get_step_type_display", read_only=True)
    track_title = serializers.CharField(source="track.title", read_only=True)
    track_no = serializers.IntegerField(source="track.track_no", read_only=True)

    class Meta:
        model = TrainingStepRecord
        fields = [
            "id",
            "trainee",
            "trainee_name",
            "supervisor",
            "supervisor_name",
            "track",
            "track_no",
            "track_title",
            "step_type",
            "step_type_label",
            "performed_at",
            "location",
            "note",
            "trainee_division",
            "trainee_group",
            "trainee_team",
            "trainee_unit",
        ]

    def get_trainee_name(self, obj):
        return user_display_name(obj.trainee)

    def get_supervisor_name(self, obj):
        return user_display_name(obj.supervisor)


class TrainingProgressStepSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    performed_at = serializers.DateTimeField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    supervisor_name = serializers.CharField(required=False, allow_blank=True)
    score = serializers.IntegerField(required=False)
    total = serializers.IntegerField(required=False)
    exam_name = serializers.CharField(required=False, allow_blank=True)
    rate = serializers.IntegerField(required=False)


class TrainingProgressRowSerializer(serializers.Serializer):
    track_id = serializers.IntegerField()
    track_code = serializers.CharField()
    no = serializers.IntegerField()
    title = serializers.CharField()
    has_test = serializers.BooleanField()
    book_id = serializers.IntegerField(required=False, allow_null=True)
    book_title = serializers.CharField(required=False, allow_blank=True)
    education = TrainingProgressStepSerializer(required=False, allow_null=True)
    test = TrainingProgressStepSerializer(required=False, allow_null=True)
    certification = TrainingProgressStepSerializer(required=False, allow_null=True)
    can_certify = serializers.BooleanField()


class TrainingProgressSummarySerializer(serializers.Serializer):
    trainee = serializers.DictField()
    rows = TrainingProgressRowSerializer(many=True)


class TrainingUserCompactSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    team_name = serializers.CharField(source="profile.team.name", read_only=True)
    unit_name = serializers.CharField(source="profile.unit.name", read_only=True)
    division_name = serializers.CharField(source="profile.division.name", read_only=True)
    employee_code = serializers.CharField(source="profile.employee_code", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "label",
            "employee_code",
            "division_name",
            "team_name",
            "unit_name",
        ]

    def get_label(self, obj):
        return user_display_name(obj)
