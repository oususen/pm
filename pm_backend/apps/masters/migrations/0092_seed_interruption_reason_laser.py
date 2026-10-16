from django.db import migrations


# 中断理由マスタ ライン種別1(レーザー・予約) 初期データ14件
INITIAL_INTERRUPTION_REASONS_LASER = [
    # ライン種別1(レーザー・予約) 中断(PAUSE)
    {'code': '1101', 'line_category': '1', 'category': '1', 'display_name': '設備トラブル', 'operation': 'PAUSE', 'display_order': 10},
    {'code': '1201', 'line_category': '1', 'category': '2', 'display_name': '治具トラブル', 'operation': 'PAUSE', 'display_order': 20},
    {'code': '1301', 'line_category': '1', 'category': '3', 'display_name': '品質トラブル', 'operation': 'PAUSE', 'display_order': 30},
    {'code': '1401', 'line_category': '1', 'category': '4', 'display_name': '3S活動', 'operation': 'PAUSE', 'display_order': 40},
    {'code': '1402', 'line_category': '1', 'category': '4', 'display_name': '改善活動', 'operation': 'PAUSE', 'display_order': 50},
    {'code': '1403', 'line_category': '1', 'category': '4', 'display_name': '工程指導', 'operation': 'PAUSE', 'display_order': 60},
    {'code': '1404', 'line_category': '1', 'category': '4', 'display_name': '班長/対応者待ち', 'operation': 'PAUSE', 'display_order': 70},
    {'code': '1901', 'line_category': '1', 'category': '9', 'display_name': '部品待ち', 'operation': 'PAUSE', 'display_order': 80},
    {'code': '1904', 'line_category': '1', 'category': '9', 'display_name': 'パターン違い', 'operation': 'PAUSE', 'display_order': 90},
    {'code': '1997', 'line_category': '1', 'category': '9', 'display_name': 'その他', 'operation': 'PAUSE', 'display_order': 900},
    # ライン種別1 強制終了(TEMP_END)
    {'code': '1102', 'line_category': '1', 'category': '1', 'display_name': '本日設備復旧不可', 'operation': 'TEMP_END', 'display_order': 10},
    {'code': '1202', 'line_category': '1', 'category': '2', 'display_name': '本日治具使用不可', 'operation': 'TEMP_END', 'display_order': 20},
    {'code': '1905', 'line_category': '1', 'category': '9', 'display_name': '他へ製品切り替え', 'operation': 'TEMP_END', 'display_order': 30},
    {'code': '1998', 'line_category': '1', 'category': '9', 'display_name': 'その他', 'operation': 'TEMP_END', 'display_order': 900},
]


def seed_interruption_reasons(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    for item in INITIAL_INTERRUPTION_REASONS_LASER:
        InterruptionReason.objects.get_or_create(code=item['code'], defaults=item)


def delete_seeded_interruption_reasons(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    InterruptionReason.objects.filter(
        code__in=[item['code'] for item in INITIAL_INTERRUPTION_REASONS_LASER]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0091_rename_other_reason_codes'),
    ]

    operations = [
        migrations.RunPython(seed_interruption_reasons, delete_seeded_interruption_reasons),
    ]
