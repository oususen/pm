from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0042_add_purchase_menu_permission_resources'),
        ('masters', '0064_add_identification_code_and_sei_ban'),
        ('production', '0071_update_change_history_operation_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='MorningMeeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting_date', models.DateField(verbose_name='朝礼日')),
                ('title', models.CharField(max_length=200, verbose_name='タイトル')),
                ('agenda', models.TextField(blank=True, default='', verbose_name='議題')),
                ('notices', models.TextField(blank=True, default='', verbose_name='連絡事項')),
                ('cautions', models.TextField(blank=True, default='', verbose_name='注意事項')),
                ('execution_note', models.TextField(blank=True, default='', verbose_name='実行メモ')),
                ('status', models.CharField(choices=[('DRAFT', '下書き'), ('READY', '準備完了'), ('IN_PROGRESS', '実行中'), ('COMPLETED', '完了')], default='DRAFT', max_length=20, verbose_name='状態')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='開始日時')),
                ('ended_at', models.DateTimeField(blank=True, null=True, verbose_name='終了日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_morning_meetings', to=settings.AUTH_USER_MODEL, verbose_name='作成者')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='morning_meetings', to='accounts.department', verbose_name='対象部署')),
                ('facilitator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='facilitated_morning_meetings', to=settings.AUTH_USER_MODEL, verbose_name='司会者')),
                ('line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='morning_meetings', to='masters.line', verbose_name='対象ライン')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_morning_meetings', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': '朝礼',
                'verbose_name_plural': '朝礼',
                'db_table': 't_morning_meeting',
                'ordering': ['-meeting_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='MorningMeetingParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attendance_status', models.CharField(choices=[('PENDING', '未確認'), ('PRESENT', '出席'), ('ABSENT', '欠席'), ('LATE', '遅刻')], default='PENDING', max_length=20, verbose_name='参加状態')),
                ('checked_at', models.DateTimeField(blank=True, null=True, verbose_name='確認日時')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='備考')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='表示順')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='production.morningmeeting', verbose_name='朝礼')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='morning_meeting_participants', to=settings.AUTH_USER_MODEL, verbose_name='参加者')),
            ],
            options={
                'verbose_name': '朝礼参加者',
                'verbose_name_plural': '朝礼参加者',
                'db_table': 't_morning_meeting_participant',
                'ordering': ['display_order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='morningmeeting',
            index=models.Index(fields=['meeting_date', 'status'], name='pm_mm_date_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='morningmeeting',
            index=models.Index(fields=['department', 'meeting_date'], name='pm_mm_dept_date_idx'),
        ),
        migrations.AddIndex(
            model_name='morningmeeting',
            index=models.Index(fields=['line', 'meeting_date'], name='pm_mm_line_date_idx'),
        ),
        migrations.AddIndex(
            model_name='morningmeetingparticipant',
            index=models.Index(fields=['meeting', 'attendance_status'], name='pm_mmp_meet_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='morningmeetingparticipant',
            index=models.Index(fields=['user'], name='pm_mmp_user_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='morningmeetingparticipant',
            unique_together={('meeting', 'user')},
        ),
    ]
