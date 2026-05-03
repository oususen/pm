from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('masters', '0001_initial'),
        ('quality', '0018_add_plan_date_to_batch'),
    ]

    operations = [
        migrations.CreateModel(
            name='IntegratedChecksheetTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='テンプレート名')),
                ('version', models.PositiveIntegerField(default=1, verbose_name='版')),
                ('status', models.CharField(choices=[('DRAFT', '下書き'), ('APPROVED', '承認済み')], default='DRAFT', max_length=20, verbose_name='状態')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='integrated_checksheet_templates', to='masters.product', verbose_name='製品')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='作成者')),
            ],
            options={
                'verbose_name': '工程一体チェックシートテンプレート',
                'verbose_name_plural': '工程一体チェックシートテンプレート',
                'db_table': 'quality_integrated_checksheet_template',
                'ordering': ['-version'],
                'unique_together': {('product', 'version')},
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetProcessBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='工程順序')),
                ('sketch_image', models.ImageField(blank=True, upload_to='integrated_checksheets/sketches/', verbose_name='略図（台紙）')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='process_blocks', to='quality.integratedchecksheettemplate', verbose_name='テンプレート')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='masters.process', verbose_name='工程')),
            ],
            options={
                'verbose_name': '工程ブロック',
                'verbose_name_plural': '工程ブロック',
                'db_table': 'quality_integrated_cs_process_block',
                'ordering': ['sort_order'],
                'unique_together': {('template', 'process')},
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='表示順')),
                ('item_name', models.CharField(max_length=300, verbose_name='点検項目')),
                ('standard', models.TextField(blank=True, default='', verbose_name='規格')),
                ('frequency', models.CharField(blank=True, default='', max_length=50, verbose_name='確認頻度')),
                ('method', models.TextField(blank=True, default='', verbose_name='方法')),
                ('record_type', models.CharField(choices=[('CHECK', 'チェック'), ('NUMERIC', '数値'), ('TEXT', '文字')], default='CHECK', max_length=20, verbose_name='記録種別')),
                ('unit', models.CharField(blank=True, default='', max_length=30, verbose_name='単位')),
                ('criteria', models.TextField(blank=True, default='', verbose_name='判定基準')),
                ('is_required', models.BooleanField(default=True, verbose_name='必須')),
                ('process_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='quality.integratedchecksheetprocessblock', verbose_name='工程ブロック')),
            ],
            options={
                'verbose_name': 'チェック項目',
                'verbose_name_plural': 'チェック項目',
                'db_table': 'quality_integrated_cs_item',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(blank=True, null=True, verbose_name='計画日')),
                ('quantity', models.PositiveIntegerField(verbose_name='台数')),
                ('lot_no', models.CharField(blank=True, default='', max_length=100, verbose_name='ロットNo')),
                ('status', models.CharField(choices=[('OPEN', '実施中'), ('COMPLETED', '完了')], default='OPEN', max_length=20, verbose_name='状態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='batches', to='quality.integratedchecksheettemplate', verbose_name='テンプレート')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='integrated_checksheet_batches', to='masters.product', verbose_name='製品')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='integrated_checksheet_batches', to='masters.line', verbose_name='ライン')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='作成者')),
            ],
            options={
                'verbose_name': '工程一体チェックシートバッチ',
                'verbose_name_plural': '工程一体チェックシートバッチ',
                'db_table': 'quality_integrated_checksheet_batch',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['product', 'plan_date'], name='idx_intcs_batch_prod_date'),
                    models.Index(fields=['status', 'created_at'], name='idx_intcs_batch_status'),
                ],
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_no', models.PositiveIntegerField(verbose_name='台目番号')),
                ('status', models.CharField(choices=[('PENDING', '未着手'), ('IN_PROGRESS', '入力中'), ('COMPLETED', '入力完了'), ('APPROVED', '承認済み')], default='PENDING', max_length=20, verbose_name='状態')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完了日時')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='承認日時')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='quality.integratedchecksheetbatch', verbose_name='バッチ')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='承認者')),
            ],
            options={
                'verbose_name': '台目レコード',
                'verbose_name_plural': '台目レコード',
                'db_table': 'quality_integrated_checksheet_unit',
                'ordering': ['sequence_no'],
                'unique_together': {('batch', 'sequence_no')},
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('judgement', models.CharField(blank=True, choices=[('OK', 'OK'), ('NG', 'NG')], default='', max_length=10, verbose_name='判定')),
                ('numeric_value', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='数値')),
                ('text_value', models.TextField(blank=True, default='', verbose_name='テキスト')),
                ('checked_at', models.DateTimeField(blank=True, null=True, verbose_name='入力日時')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checks', to='quality.integratedchecksheetunit', verbose_name='台目')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='quality.integratedchecksheetitem', verbose_name='チェック項目')),
                ('checked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='入力者')),
            ],
            options={
                'verbose_name': 'チェック結果',
                'verbose_name_plural': 'チェック結果',
                'db_table': 'quality_integrated_cs_check',
                'unique_together': {('unit', 'item')},
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetSketchField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=80, verbose_name='内部キー')),
                ('label', models.CharField(max_length=120, verbose_name='表示名')),
                ('field_type', models.CharField(choices=[('checkbox', 'チェック'), ('text', 'テキスト'), ('aggregate_okng', 'OK/NG'), ('date', '日付'), ('photo', '写真'), ('pen', '手書き'), ('worker_name', '作業者名')], default='text', max_length=30, verbose_name='項目種類')),
                ('x', models.FloatField(default=0, verbose_name='左位置')),
                ('y', models.FloatField(default=0, verbose_name='上位置')),
                ('width', models.FloatField(default=160, verbose_name='幅')),
                ('height', models.FloatField(default=36, verbose_name='高さ')),
                ('required', models.BooleanField(default=False, verbose_name='必須')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='並び順')),
                ('process_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sketch_fields', to='quality.integratedchecksheetprocessblock', verbose_name='工程ブロック')),
            ],
            options={
                'verbose_name': '台紙フィールド',
                'verbose_name_plural': '台紙フィールド',
                'db_table': 'quality_integrated_cs_sketch_field',
                'ordering': ['sort_order', 'id'],
                'unique_together': {('process_block', 'key')},
            },
        ),
        migrations.CreateModel(
            name='IntegratedChecksheetSketchResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drawing_data', models.JSONField(default=dict, verbose_name='手書き描画データ')),
                ('field_responses', models.JSONField(default=dict, verbose_name='フィールド回答')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sketch_responses', to='quality.integratedchecksheetunit', verbose_name='台目')),
                ('process_block', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='quality.integratedchecksheetprocessblock', verbose_name='工程ブロック')),
            ],
            options={
                'verbose_name': '台紙回答',
                'verbose_name_plural': '台紙回答',
                'db_table': 'quality_integrated_cs_sketch_response',
                'unique_together': {('unit', 'process_block')},
            },
        ),
    ]
