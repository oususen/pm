from django.db import migrations


def add_anthropic_provider(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    # 無効で作る。BOSSがAPIキーを環境変数へ入れ、動作を確認してから、AI設定で有効にする(既存の行があっても有効化しない)
    provider_model.objects.update_or_create(
        provider='anthropic',
        defaults={'default_model': 'claude-haiku-5-5', 'is_enabled': False, 'display_order': 4},
    )


def remove_anthropic_provider(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    provider_model.objects.filter(provider='anthropic').delete()


class Migration(migrations.Migration):
    dependencies = [('ai', '0052_alter_aiproviderconfig_provider_anthropic')]

    operations = [migrations.RunPython(add_anthropic_provider, remove_anthropic_provider)]
