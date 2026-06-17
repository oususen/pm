from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_target_users'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CallSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('call_type', models.CharField(choices=[('voice', '音声'), ('video', 'ビデオ')], max_length=10, verbose_name='通話種別')),
                ('status', models.CharField(choices=[('ringing', '呼出中'), ('accepted', '通話中'), ('declined', '辞退'), ('ended', '終了'), ('missed', '不在'), ('canceled', 'キャンセル')], default='ringing', max_length=10, verbose_name='状態')),
                ('initiated_at', models.DateTimeField(auto_now_add=True, verbose_name='発信日時')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='応答日時')),
                ('ended_at', models.DateTimeField(blank=True, null=True, verbose_name='終了日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('callee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_call_sessions', to=settings.AUTH_USER_MODEL, verbose_name='着信者')),
                ('caller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_call_sessions', to=settings.AUTH_USER_MODEL, verbose_name='発信者')),
            ],
            options={
                'verbose_name': '通話セッション',
                'verbose_name_plural': '通話セッション',
                'db_table': 'call_sessions',
                'ordering': ['-initiated_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='CallSignal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signal_type', models.CharField(choices=[('offer', 'Offer'), ('answer', 'Answer'), ('ice_candidate', 'ICE Candidate'), ('hangup', 'Hangup')], max_length=20, verbose_name='シグナル種別')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='シグナル内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_call_signals', to=settings.AUTH_USER_MODEL, verbose_name='送信者')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signals', to='notifications.callsession', verbose_name='通話セッション')),
                ('target_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_call_signals', to=settings.AUTH_USER_MODEL, verbose_name='送信先ユーザー')),
            ],
            options={
                'verbose_name': '通話シグナル',
                'verbose_name_plural': '通話シグナル',
                'db_table': 'call_signals',
                'ordering': ['id'],
            },
        ),
    ]
