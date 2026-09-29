from django.db import migrations


def add_openrouter_provider(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    provider_model.objects.update_or_create(
        provider='openrouter',
        defaults={'default_model': 'qwen/qwen3.8-27b', 'is_enabled': True, 'display_order': 3},
    )


def remove_openrouter_provider(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    provider_model.objects.filter(provider='openrouter').delete()


class Migration(migrations.Migration):
    dependencies = [('ai', '0005_alter_aiproviderconfig_provider')]

    operations = [migrations.RunPython(add_openrouter_provider, remove_openrouter_provider)]
