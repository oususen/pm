# 手動作成マイグレーション
# orders アプリから production / quality / shipping アプリへ移管済みのモデルを
# Django の migration state から削除する。
# SeparateDatabaseAndState を使用し、DB は一切変更しない。
#
# 移管先:
#   production: LineBacklog, LineDemand, LineGanttPlan, LineRealtimeRecord,
#               LineStatus, ProcessActual, ProcessRealtimeRecord,
#               ProductionOrder, StockAllocation
#   quality:    ScrapRecord, ScrapRecordDetail
#   shipping:   ShipmentActual, ShipmentActualHistory, DeliveryProgress

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0041_stgorderrawtiera_order_document_no'),
        ('quality', '0005_initial'),  # quality が ScrapRecord の ownership を取得後
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                # FK参照元（子）から先に削除
                migrations.DeleteModel('ScrapRecordDetail'),     # → ScrapRecord
                migrations.DeleteModel('ScrapRecord'),           # → ProcessRealtimeRecord
                migrations.DeleteModel('ProcessActual'),         # → ProductionOrder, ProcessRealtimeRecord
                migrations.DeleteModel('ShipmentActualHistory'), # → ShipmentActual
                migrations.DeleteModel('ProductionOrder'),       # → StockAllocation
                # FK参照先（親）を削除
                migrations.DeleteModel('ProcessRealtimeRecord'),
                migrations.DeleteModel('StockAllocation'),
                migrations.DeleteModel('ShipmentActual'),
                migrations.DeleteModel('DeliveryProgress'),
                # masters への FK のみの独立モデルを削除
                migrations.DeleteModel('LineBacklog'),
                migrations.DeleteModel('LineDemand'),
                migrations.DeleteModel('LineGanttPlan'),
                migrations.DeleteModel('LineRealtimeRecord'),
                migrations.DeleteModel('LineStatus'),
            ],
        ),
    ]
