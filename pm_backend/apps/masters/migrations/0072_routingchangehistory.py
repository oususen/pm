from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0071_linecycletime'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RoutingChangeHistory',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('target_type', models.CharField(choices=[('ROUTING', 'ヘッダ'), ('STEP', '工程')], max_length=20, verbose_name='対象種別')),
                ('action', models.CharField(choices=[('CREATE', '作成'), ('UPDATE', '更新'), ('DELETE', '削除')], max_length=20, verbose_name='操作')),
                ('target_label', models.CharField(blank=True, default='', max_length=200, verbose_name='対象表示名')),
                ('change_summary', models.TextField(blank=True, default='', verbose_name='変更概要')),
                ('before_data', models.JSONField(blank=True, null=True, verbose_name='変更前データ')),
                ('after_data', models.JSONField(blank=True, null=True, verbose_name='変更後データ')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='記録日時')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='変更者')),
                ('routing', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_histories', to='masters.routing', verbose_name='ルーティング')),
                ('routing_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_histories', to='masters.routingstep', verbose_name='ルーティング工程')),
            ],
            options={
                'verbose_name': 'ルーティング変更履歴',
                'verbose_name_plural': 'ルーティング変更履歴',
                'db_table': 't_routing_change_history',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='routingchangehistory',
            index=models.Index(fields=['routing', 'created_at'], name='t_routing_c_routing_4377ed_idx'),
        ),
        migrations.AddIndex(
            model_name='routingchangehistory',
            index=models.Index(fields=['routing_step', 'created_at'], name='t_routing_c_routing_7308f0_idx'),
        ),
    ]
