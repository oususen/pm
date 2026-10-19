from django.db import migrations


# レーザー(ライン種別1)の中断理由コード1901の表示名を「部品待ち」から「材料待ち」へ改名する。
# BOSS判断(2026-10-19): レーザーでは「部品」と「材料」が同じもの(シート材を切断して
# 構成部品を作るため、別の部品在庫概念がない)であり、「材料待ち」の方が実態に合う。
# コード(1901)・類別(9)・操作(PAUSE)は変更しない。表示名のみの改名。
OLD_NAME = '部品待ち'
NEW_NAME = '材料待ち'
TARGET_CODE = '1901'


def rename_forward(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    InterruptionReason.objects.filter(code=TARGET_CODE, display_name=OLD_NAME).update(display_name=NEW_NAME)


def rename_backward(apps, schema_editor):
    InterruptionReason = apps.get_model('masters', 'InterruptionReason')
    InterruptionReason.objects.filter(code=TARGET_CODE, display_name=NEW_NAME).update(display_name=OLD_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0092_seed_interruption_reason_laser'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
