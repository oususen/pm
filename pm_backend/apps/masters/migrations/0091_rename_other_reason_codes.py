from django.db import migrations


# 「その他」コードの末尾2桁を固定パターン化（中断=97, 強制終了=98）。
# 類別9のラベルを「その他」から「一般」に改名した（0090）ため、
# 類別内の「その他」理由と区別しやすいようコードも統一する。
CODE_RENAMES = [
    ('2907', '2997'),  # ライン種別2 中断 その他
    ('2908', '2998'),  # ライン種別2 強制終了 その他
    ('3907', '3997'),  # ライン種別3 中断 その他
    ('3908', '3998'),  # ライン種別3 強制終了 その他
]


def rename_forward(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    for old_code, new_code in CODE_RENAMES:
        InterruptionReason.objects.filter(code=old_code).update(code=new_code)


def rename_backward(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    for old_code, new_code in CODE_RENAMES:
        InterruptionReason.objects.filter(code=new_code).update(code=old_code)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0090_alter_interruptionreason_category'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
