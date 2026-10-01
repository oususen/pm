from django.db import migrations


DEFAULT_POLICIES = (
    ('production', 'quality', '日別の生産数と確定仕損を比較する'),
    ('production', 'overtime', '日別の生産数と残業申請時間を比較する'),
    ('production', 'purchase', '生産数と入荷実績を確認する'),
)


def add_default_policies(apps, schema_editor):
    Policy = apps.get_model('ai', 'AICrossScreenAccessPolicy')
    for source_screen_id, target_screen_id, purpose in DEFAULT_POLICIES:
        Policy.objects.get_or_create(
            source_screen_id=source_screen_id,
            target_screen_id=target_screen_id,
            defaults={'purpose': purpose, 'is_enabled': True, 'allow_external_transfer': True},
        )


def remove_default_policies(apps, schema_editor):
    Policy = apps.get_model('ai', 'AICrossScreenAccessPolicy')
    for source_screen_id, target_screen_id, purpose in DEFAULT_POLICIES:
        Policy.objects.filter(
            source_screen_id=source_screen_id,
            target_screen_id=target_screen_id,
            purpose=purpose,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0020_alter_aicrossscreenaccesspolicy_options'),
    ]

    operations = [
        migrations.RunPython(add_default_policies, remove_default_policies),
    ]
