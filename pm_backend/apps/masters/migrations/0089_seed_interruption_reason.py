from django.db import migrations


# 中断理由マスタ 初期データ34件
# 欠番: 2903・3903（機種間違い）は投入しない
INITIAL_INTERRUPTION_REASONS = [
    # ライン種別2(ブレーキ・板金スポット) 中断(PAUSE)
    {'code': '2101', 'line_category': '2', 'category': '1', 'display_name': '設備トラブル', 'operation': 'PAUSE', 'display_order': 10},
    {'code': '2201', 'line_category': '2', 'category': '2', 'display_name': '治具トラブル', 'operation': 'PAUSE', 'display_order': 20},
    {'code': '2301', 'line_category': '2', 'category': '3', 'display_name': '品質トラブル', 'operation': 'PAUSE', 'display_order': 30},
    {'code': '2401', 'line_category': '2', 'category': '4', 'display_name': '3S活動', 'operation': 'PAUSE', 'display_order': 40},
    {'code': '2402', 'line_category': '2', 'category': '4', 'display_name': '改善活動', 'operation': 'PAUSE', 'display_order': 50},
    {'code': '2403', 'line_category': '2', 'category': '4', 'display_name': '工程指導', 'operation': 'PAUSE', 'display_order': 60},
    {'code': '2404', 'line_category': '2', 'category': '4', 'display_name': '班長/対応者待ち', 'operation': 'PAUSE', 'display_order': 70},
    {'code': '2901', 'line_category': '2', 'category': '9', 'display_name': '部品待ち', 'operation': 'PAUSE', 'display_order': 80},
    {'code': '2902', 'line_category': '2', 'category': '9', 'display_name': '段取り替え', 'operation': 'PAUSE', 'display_order': 90},
    {'code': '2904', 'line_category': '2', 'category': '9', 'display_name': '品番間違い', 'operation': 'PAUSE', 'display_order': 100},
    {'code': '2907', 'line_category': '2', 'category': '9', 'display_name': 'その他', 'operation': 'PAUSE', 'display_order': 900},
    # ライン種別2 強制終了(TEMP_END)
    {'code': '2102', 'line_category': '2', 'category': '1', 'display_name': '本日設備復旧不可', 'operation': 'TEMP_END', 'display_order': 10},
    {'code': '2202', 'line_category': '2', 'category': '2', 'display_name': '本日治具使用不可', 'operation': 'TEMP_END', 'display_order': 20},
    {'code': '2905', 'line_category': '2', 'category': '9', 'display_name': '他へ製品切り替え', 'operation': 'TEMP_END', 'display_order': 30},
    {'code': '2906', 'line_category': '2', 'category': '9', 'display_name': '材料不足', 'operation': 'TEMP_END', 'display_order': 40},
    {'code': '2908', 'line_category': '2', 'category': '9', 'display_name': 'その他', 'operation': 'TEMP_END', 'display_order': 900},
    # ライン種別3(その他の一般の工程) 中断(PAUSE)
    {'code': '3101', 'line_category': '3', 'category': '1', 'display_name': '設備トラブル', 'operation': 'PAUSE', 'display_order': 10},
    {'code': '3201', 'line_category': '3', 'category': '2', 'display_name': '治具トラブル', 'operation': 'PAUSE', 'display_order': 20},
    {'code': '3301', 'line_category': '3', 'category': '3', 'display_name': '品質トラブル', 'operation': 'PAUSE', 'display_order': 30},
    {'code': '3401', 'line_category': '3', 'category': '4', 'display_name': '3S活動', 'operation': 'PAUSE', 'display_order': 40},
    {'code': '3402', 'line_category': '3', 'category': '4', 'display_name': '改善活動', 'operation': 'PAUSE', 'display_order': 50},
    {'code': '3403', 'line_category': '3', 'category': '4', 'display_name': '工程指導', 'operation': 'PAUSE', 'display_order': 60},
    {'code': '3404', 'line_category': '3', 'category': '4', 'display_name': '班長/対応者待ち', 'operation': 'PAUSE', 'display_order': 70},
    {'code': '3901', 'line_category': '3', 'category': '9', 'display_name': '部品待ち', 'operation': 'PAUSE', 'display_order': 80},
    {'code': '3902', 'line_category': '3', 'category': '9', 'display_name': '段取り替え', 'operation': 'PAUSE', 'display_order': 90},
    {'code': '3904', 'line_category': '3', 'category': '9', 'display_name': '品番間違い', 'operation': 'PAUSE', 'display_order': 100},
    {'code': '3921', 'line_category': '3', 'category': '9', 'display_name': 'ティーチング', 'operation': 'PAUSE', 'display_order': 110},
    {'code': '3922', 'line_category': '3', 'category': '9', 'display_name': 'ワイヤ交換', 'operation': 'PAUSE', 'display_order': 120},
    {'code': '3907', 'line_category': '3', 'category': '9', 'display_name': 'その他', 'operation': 'PAUSE', 'display_order': 900},
    # ライン種別3 強制終了(TEMP_END)
    {'code': '3102', 'line_category': '3', 'category': '1', 'display_name': '本日設備復旧不可', 'operation': 'TEMP_END', 'display_order': 10},
    {'code': '3202', 'line_category': '3', 'category': '2', 'display_name': '本日治具使用不可', 'operation': 'TEMP_END', 'display_order': 20},
    {'code': '3905', 'line_category': '3', 'category': '9', 'display_name': '他へ製品切り替え', 'operation': 'TEMP_END', 'display_order': 30},
    {'code': '3906', 'line_category': '3', 'category': '9', 'display_name': '材料不足', 'operation': 'TEMP_END', 'display_order': 40},
    {'code': '3908', 'line_category': '3', 'category': '9', 'display_name': 'その他', 'operation': 'TEMP_END', 'display_order': 900},
]


def seed_interruption_reasons(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    for item in INITIAL_INTERRUPTION_REASONS:
        InterruptionReason.objects.get_or_create(code=item['code'], defaults=item)


def delete_seeded_interruption_reasons(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    InterruptionReason.objects.filter(
        code__in=[item['code'] for item in INITIAL_INTERRUPTION_REASONS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0088_interruptionreason'),
    ]

    operations = [
        migrations.RunPython(seed_interruption_reasons, delete_seeded_interruption_reasons),
    ]
