from django.conf import settings
from django.db import models

from accounts.models import Department


class TrainingBook(models.Model):
    """教材マスタ"""

    book_code = models.CharField(max_length=40, unique=True, verbose_name="教材コード")
    title = models.CharField(max_length=200, verbose_name="教材名")
    source_file = models.CharField(max_length=255, blank=True, default="", verbose_name="取込元ファイル")
    source_sheet = models.CharField(max_length=120, blank=True, default="", verbose_name="取込元シート")
    question_count = models.PositiveIntegerField(default=0, verbose_name="問題数")
    material_url = models.CharField(max_length=255, blank=True, default="", verbose_name="教材URL")
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_training_book"
        verbose_name = "教育教材"
        verbose_name_plural = "教育教材"
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.book_code}:{self.title}"


class TrainingQuestion(models.Model):
    """教材ごとの問題バンク"""

    book = models.ForeignKey(
        TrainingBook,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="教材",
    )
    question_code = models.CharField(max_length=60, unique=True, verbose_name="問題コード")
    category = models.CharField(max_length=120, blank=True, default="", verbose_name="カテゴリ")
    question_type = models.CharField(max_length=40, blank=True, default="", verbose_name="問題形式")
    level = models.CharField(max_length=40, blank=True, default="", verbose_name="難易度")
    importance = models.CharField(max_length=20, blank=True, default="", verbose_name="重要度")
    risk = models.CharField(max_length=255, blank=True, default="", verbose_name="リスク")
    question_text = models.TextField(verbose_name="問題文")
    choices_json = models.JSONField(default=list, blank=True, verbose_name="選択肢")
    choices_raw = models.TextField(blank=True, default="", verbose_name="選択肢原文")
    answer = models.CharField(max_length=40, blank=True, default="", verbose_name="正答")
    explanation = models.TextField(blank=True, default="", verbose_name="解説")
    refs_json = models.JSONField(default=list, blank=True, verbose_name="根拠情報")
    extra_json = models.JSONField(default=dict, blank=True, verbose_name="追加情報")
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_training_question"
        verbose_name = "教育問題"
        verbose_name_plural = "教育問題"
        ordering = ["book_id", "display_order", "id"]
        indexes = [
            models.Index(fields=["book", "display_order"]),
            models.Index(fields=["book", "is_active"]),
        ]

    def __str__(self):
        return self.question_code


class TrainingExamDefinition(models.Model):
    """試験定義"""

    book = models.ForeignKey(
        TrainingBook,
        on_delete=models.CASCADE,
        related_name="exams",
        verbose_name="教材",
    )
    name = models.CharField(max_length=120, verbose_name="試験名")
    source_sheet = models.CharField(max_length=120, blank=True, default="", verbose_name="取込元シート")
    is_random = models.BooleanField(default=False, verbose_name="ランダム出題")
    bank_all = models.BooleanField(default=False, verbose_name="全問題バンク")
    random_question_count = models.PositiveIntegerField(default=10, verbose_name="ランダム出題数")
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_training_exam_definition"
        verbose_name = "教育試験定義"
        verbose_name_plural = "教育試験定義"
        ordering = ["book_id", "display_order", "id"]
        unique_together = [["book", "name"]]

    def __str__(self):
        return f"{self.book.title}:{self.name}"


class TrainingExamQuestion(models.Model):
    """固定試験の出題問題"""

    exam = models.ForeignKey(
        TrainingExamDefinition,
        on_delete=models.CASCADE,
        related_name="exam_questions",
        verbose_name="試験",
    )
    question = models.ForeignKey(
        TrainingQuestion,
        on_delete=models.CASCADE,
        related_name="exam_links",
        verbose_name="問題",
    )
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")

    class Meta:
        db_table = "quality_training_exam_question"
        verbose_name = "教育試験問題"
        verbose_name_plural = "教育試験問題"
        ordering = ["exam_id", "display_order", "id"]
        unique_together = [["exam", "question"]]

    def __str__(self):
        return f"{self.exam_id}:{self.question_id}"


class TrainingTrack(models.Model):
    """教育推進状況で使う管理項目"""

    track_code = models.CharField(max_length=40, unique=True, verbose_name="進捗項目コード")
    track_no = models.PositiveIntegerField(default=1, verbose_name="No")
    title = models.CharField(max_length=200, verbose_name="進捗項目名")
    book = models.ForeignKey(
        TrainingBook,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tracks",
        verbose_name="教材",
    )
    has_test = models.BooleanField(default=True, verbose_name="テスト有無")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_training_track"
        verbose_name = "教育進捗項目"
        verbose_name_plural = "教育進捗項目"
        ordering = ["track_no", "id"]

    def __str__(self):
        return f"{self.track_no}:{self.title}"


class TrainingOrgSnapshotMixin(models.Model):
    """受講時点の組織スナップショット"""

    trainee_department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="受講者所属部署",
    )
    trainee_division = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="受講者事業部",
        limit_choices_to={"level": "division"},
    )
    trainee_group = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="受講者係",
        limit_choices_to={"level": "group"},
    )
    trainee_team = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="受講者班",
        limit_choices_to={"level": "team"},
    )
    trainee_unit = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="受講者グループ",
        limit_choices_to={"level": "unit"},
    )

    class Meta:
        abstract = True


class TrainingExamSession(TrainingOrgSnapshotMixin):
    """試験開始時点の出題セッション"""

    book = models.ForeignKey(
        TrainingBook,
        on_delete=models.CASCADE,
        related_name="exam_sessions",
        verbose_name="教材",
    )
    exam = models.ForeignKey(
        TrainingExamDefinition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="exam_sessions",
        verbose_name="試験",
    )
    trainee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_exam_sessions",
        verbose_name="受講者",
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_training_exam_sessions",
        verbose_name="試験官",
    )
    performed_at = models.DateTimeField(verbose_name="実施日時")
    location = models.CharField(max_length=120, blank=True, default="", verbose_name="実施場所")
    formal_exam = models.BooleanField(default=False, verbose_name="推進判定対象")
    question_ids_json = models.JSONField(default=list, blank=True, verbose_name="出題問題ID")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_training_exam_sessions",
        verbose_name="作成者",
    )
    is_completed = models.BooleanField(default=False, verbose_name="完了")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")

    class Meta:
        db_table = "quality_training_exam_session"
        verbose_name = "教育試験セッション"
        verbose_name_plural = "教育試験セッション"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["trainee", "is_completed"]),
            models.Index(fields=["book", "created_at"]),
        ]

    def __str__(self):
        return f"{self.trainee_id}:{self.book_id}:{self.created_at}"


class TrainingExamAttempt(TrainingOrgSnapshotMixin):
    """採点済み試験結果"""

    RESULT_PASS = "PASS"
    RESULT_RETRAIN = "RETRAIN"
    RESULT_CHOICES = [
        (RESULT_PASS, "合格"),
        (RESULT_RETRAIN, "補足教育・再教育"),
    ]

    session = models.OneToOneField(
        TrainingExamSession,
        on_delete=models.CASCADE,
        related_name="attempt",
        verbose_name="試験セッション",
    )
    book = models.ForeignKey(
        TrainingBook,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attempts",
        verbose_name="教材",
    )
    exam = models.ForeignKey(
        TrainingExamDefinition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attempts",
        verbose_name="試験",
    )
    trainee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_exam_attempts",
        verbose_name="受講者",
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_training_exam_attempts",
        verbose_name="試験官",
    )
    book_title = models.CharField(max_length=200, blank=True, default="", verbose_name="教材名スナップショット")
    exam_name = models.CharField(max_length=120, blank=True, default="", verbose_name="試験名スナップショット")
    performed_at = models.DateTimeField(verbose_name="実施日時")
    location = models.CharField(max_length=120, blank=True, default="", verbose_name="実施場所")
    formal_exam = models.BooleanField(default=False, verbose_name="推進判定対象")
    score = models.PositiveIntegerField(default=0, verbose_name="得点")
    total = models.PositiveIntegerField(default=0, verbose_name="総問題数")
    rate = models.PositiveIntegerField(default=0, verbose_name="正答率")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, verbose_name="判定")
    answers_json = models.JSONField(default=dict, blank=True, verbose_name="回答")
    question_results_json = models.JSONField(default=list, blank=True, verbose_name="採点明細")
    graded_at = models.DateTimeField(verbose_name="採点日時")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_training_exam_attempts",
        verbose_name="登録者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_training_exam_attempt"
        verbose_name = "教育試験結果"
        verbose_name_plural = "教育試験結果"
        ordering = ["-performed_at", "-id"]
        indexes = [
            models.Index(fields=["trainee", "performed_at"]),
            models.Index(fields=["book", "performed_at"]),
            models.Index(fields=["formal_exam", "result"]),
        ]

    def __str__(self):
        return f"{self.trainee_id}:{self.book_title}:{self.result}"


class TrainingStepRecord(TrainingOrgSnapshotMixin):
    """教育/認定の手動実績"""

    STEP_EDUCATION = "EDUCATION"
    STEP_CERTIFICATION = "CERTIFICATION"
    STEP_TYPE_CHOICES = [
        (STEP_EDUCATION, "教育"),
        (STEP_CERTIFICATION, "認定"),
    ]

    trainee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_step_records",
        verbose_name="受講者",
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_training_step_records",
        verbose_name="試験官",
    )
    track = models.ForeignKey(
        TrainingTrack,
        on_delete=models.CASCADE,
        related_name="step_records",
        verbose_name="進捗項目",
    )
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, verbose_name="工程")
    performed_at = models.DateTimeField(verbose_name="実施日時")
    location = models.CharField(max_length=120, blank=True, default="", verbose_name="実施場所")
    note = models.TextField(blank=True, default="", verbose_name="備考")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_training_step_records",
        verbose_name="登録者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_training_step_record"
        verbose_name = "教育進捗実績"
        verbose_name_plural = "教育進捗実績"
        ordering = ["-performed_at", "-id"]
        indexes = [
            models.Index(fields=["trainee", "track", "step_type"]),
            models.Index(fields=["track", "step_type", "performed_at"]),
        ]

    def __str__(self):
        return f"{self.trainee_id}:{self.track_id}:{self.step_type}"
