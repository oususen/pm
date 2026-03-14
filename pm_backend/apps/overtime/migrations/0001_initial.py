from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0023_add_record_inquiry_permission_resource'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OvertimeApplication',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('work_date', models.DateField(verbose_name='実施日')),
                ('application_type', models.CharField(
                    choices=[('overtime', '時間外'), ('holiday', '休日出勤')],
                    default='overtime', max_length=10, verbose_name='申請種別',
                )),
                ('start_time', models.TimeField(verbose_name='開始時刻')),
                ('end_time', models.TimeField(verbose_name='終了時刻')),
                ('hours', models.DecimalField(
                    decimal_places=1, default=0, max_digits=5, verbose_name='時間外時間(H)',
                )),
                ('midnight_hours', models.DecimalField(
                    decimal_places=1, default=0, max_digits=5, verbose_name='深夜残業時間(H)',
                )),
                ('reason', models.TextField(blank=True, verbose_name='発生理由')),
                ('status', models.CharField(
                    choices=[
                        ('draft', '下書き'),
                        ('submitted', '申請中'),
                        ('approved_supervisor', '班長承認済み'),
                        ('approved_chief', '係長承認済み'),
                        ('approved_manager', '最終承認済み'),
                        ('rejected', '却下'),
                    ],
                    default='draft', max_length=30, verbose_name='ステータス',
                )),
                ('rejection_reason', models.TextField(blank=True, verbose_name='却下理由')),
                ('submitted_at', models.DateTimeField(blank=True, null=True, verbose_name='申請日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('applicant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='overtime_applications',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='申請者',
                )),
                ('team', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='overtime_applications',
                    to='accounts.department',
                    verbose_name='班',
                    limit_choices_to={'level': 'team'},
                )),
            ],
            options={
                'verbose_name': '残業申請',
                'verbose_name_plural': '残業申請',
                'db_table': 't_overtime_application',
                'ordering': ['-work_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OvertimeApprovalLog',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('role', models.CharField(
                    choices=[
                        ('supervisor', '班長'),
                        ('chief', '係長'),
                        ('manager', '課長/部長'),
                    ],
                    max_length=20, verbose_name='役割',
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', '承認待ち'),
                        ('approved', '承認済み'),
                        ('rejected', '却下'),
                    ],
                    default='pending', max_length=20, verbose_name='状態',
                )),
                ('comment', models.TextField(blank=True, verbose_name='コメント')),
                ('acted_at', models.DateTimeField(blank=True, null=True, verbose_name='対応日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('application', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='approval_logs',
                    to='overtime.overtimeapplication',
                    verbose_name='申請',
                )),
                ('approver', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='overtime_approval_logs',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='承認者',
                )),
            ],
            options={
                'verbose_name': '残業承認ログ',
                'verbose_name_plural': '残業承認ログ',
                'db_table': 't_overtime_approval_log',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='overtimeapplication',
            index=models.Index(fields=['applicant', 'work_date'], name='t_overtime_applic_work_idx'),
        ),
        migrations.AddIndex(
            model_name='overtimeapplication',
            index=models.Index(fields=['status'], name='t_overtime_applic_status_idx'),
        ),
        migrations.AddIndex(
            model_name='overtimeapprovallog',
            index=models.Index(
                fields=['application', 'status'], name='t_overtime_approvallog_idx'
            ),
        ),
    ]
