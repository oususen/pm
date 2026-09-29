from django.db import migrations


def fix_openrouter_model(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    provider_model.objects.filter(provider='openrouter').update(default_model='qwen/qwen3.8-27b:free')


def revert_openrouter_model(apps, schema_editor):
    provider_model = apps.get_model('ai', 'AIProviderConfig')
    provider_model.objects.filter(provider='openrouter').update(default_model='qwen/qwen3.8-27b')


class Migration(migrations.Migration):
    dependencies = [('ai', '0006_add_openrouter_provider')]

    operations = [migrations.RunPython(fix_openrouter_model, revert_openrouter_model)]
