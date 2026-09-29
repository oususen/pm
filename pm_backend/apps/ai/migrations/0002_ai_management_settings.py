from django.db import migrations, models


def create_initial_ai_settings(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    tool_policy_model = apps.get_model('ai', 'AIToolPolicy')
    data_policy_model = apps.get_model('ai', 'AIDataPolicy')
    knowledge_model = apps.get_model('ai', 'AIKnowledgeSource')

    provider_model.objects.bulk_create([
        provider_model(provider='deepseek', default_model='deepseek-v4-pro', is_enabled=True, display_order=1),
        provider_model(provider='qwen', default_model='qwen3:4b-instruct', is_enabled=True, display_order=2),
    ])
    enabled_tools = {
        'ai_home': ('search_product', 'count_products', 'get_business_data', 'search_employee', 'get_individual_overtime', 'get_personal_overtime_threshold'),
        'orders': ('get_missing_routing_orders',),
        'production': ('search_product', 'count_products', 'get_business_data'),
        'quality': ('search_product', 'get_business_data'),
        'overtime': ('get_business_data', 'search_employee', 'get_individual_overtime', 'get_personal_overtime_threshold'),
    }
    tool_policy_model.objects.bulk_create([
        tool_policy_model(screen_id=screen_id, tool_code=tool_code, is_enabled=True, allow_external_transfer=True)
        for screen_id, tool_codes in enabled_tools.items()
        for tool_code in tool_codes
    ])
    data_policy_model.objects.create(
        allow_aggregated_external_transfer=True,
        allow_authorized_personal_data=True,
        max_external_result_rows=30,
    )
    knowledge_model.objects.bulk_create([
        knowledge_model(category='pm_structure', name='PMアプリ構造辞書', relative_path='apps/ai/knowledge/pm_structure/README.md', description='画面・データ構造・集計規則', display_order=1),
        knowledge_model(category='manual', name='マニュアル', relative_path='apps/ai/knowledge/manuals/README.md', description='業務画面の操作マニュアル', display_order=1),
        knowledge_model(category='procedure', name='手順書', relative_path='apps/ai/knowledge/procedures/README.md', description='運用・調査手順', display_order=1),
        knowledge_model(category='security', name='AI運用規約', relative_path='apps/ai/knowledge/security/README.md', description='安全・外部送信・DB利用ルール', display_order=1),
    ])


class Migration(migrations.Migration):
    dependencies = [('ai', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AIDataPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allow_aggregated_external_transfer', models.BooleanField(default=True, verbose_name='集計結果の外部送信を許可')),
                ('allow_authorized_personal_data', models.BooleanField(default=True, verbose_name='権限者への個人別集計を許可')),
                ('max_external_result_rows', models.PositiveIntegerField(default=30, verbose_name='外部送信する最大集計行数')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'AIデータ送信設定', 'verbose_name_plural': 'AIデータ送信設定', 'db_table': 'ai_data_policy'},
        ),
        migrations.CreateModel(
            name='AIKnowledgeSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('pm_structure', 'PMアプリ構造'), ('manual', 'マニュアル'), ('procedure', '手順書'), ('security', '安全・運用規約')], max_length=30, verbose_name='区分')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('relative_path', models.CharField(max_length=300, unique=True, verbose_name='相対パス')),
                ('description', models.CharField(blank=True, default='', max_length=300, verbose_name='説明')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='表示順')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'AIナレッジ登録', 'verbose_name_plural': 'AIナレッジ登録', 'db_table': 'ai_knowledge_source', 'ordering': ['category', 'display_order', 'name']},
        ),
        migrations.CreateModel(
            name='AIProviderConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('deepseek', 'DeepSeek API'), ('qwen', 'ローカルQwen')], max_length=30, unique=True)),
                ('default_model', models.CharField(max_length=100)),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='表示順')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'AIプロバイダ設定', 'verbose_name_plural': 'AIプロバイダ設定', 'db_table': 'ai_provider_config', 'ordering': ['display_order', 'provider']},
        ),
        migrations.CreateModel(
            name='AIToolPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('screen_id', models.CharField(choices=[('ai_home', '本社横断'), ('orders', '受注'), ('production', '生産'), ('quality', '品質'), ('overtime', '勤務'), ('purchase', '仕入'), ('shipping', '出荷'), ('inventory', '在庫')], max_length=40, verbose_name='画面領域')),
                ('tool_code', models.CharField(choices=[('search_product', '品番マスタ検索'), ('count_products', '品番マスタ件数集計'), ('get_business_data', '生産・品質・残業の集計'), ('get_missing_routing_orders', 'ルーティング未設定品の確認'), ('search_employee', '社員候補検索'), ('get_individual_overtime', '個人別残業集計'), ('get_personal_overtime_threshold', '残業しきい値超過者集計')], max_length=80, verbose_name='ツール')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='有効')),
                ('allow_external_transfer', models.BooleanField(default=True, verbose_name='外部AIへの集計結果送信を許可')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'AIツール利用設定', 'verbose_name_plural': 'AIツール利用設定', 'db_table': 'ai_tool_policy', 'ordering': ['screen_id', 'tool_code']},
        ),
        migrations.AddConstraint(
            model_name='aitoolpolicy',
            constraint=models.UniqueConstraint(fields=('screen_id', 'tool_code'), name='ai_tool_policy_screen_tool_unique'),
        ),
        migrations.RunPython(create_initial_ai_settings, migrations.RunPython.noop),
    ]
