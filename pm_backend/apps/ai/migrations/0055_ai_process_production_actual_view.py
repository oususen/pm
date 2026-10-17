from django.db import migrations

# 一般工程の生産実績(t_process_realtime_record)のうち、record_type='PRODUCTION'の行だけを
# AI用に公開するビュー。公開14列はBOSS判断(AI用ビュー作成計画 §33)。
# 非公開(ビューに含めない): batch_no, event_data
# (2026-10-17 BOSS判断で公開列構成を変更: operator_nameを公開に追加、event_dataを非公開に変更。
#  event_dataはJSON型で、分析実行時の値変換(_cell())がJSON型に対応しておらず実行が100%失敗するため非公開化)
# business_dayは新規の計算列。8時区切りの業務日(timestampから-8時間した日付)。
# Python側のresolve_workday_date_for_process()と、開発DB全PRODUCTION行(15,731件)で一致確認済み。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。INTERVAL構文はMySQL/PostgreSQL共通だが、数値リテラルの書式は
# PostgreSQL移行時に要確認。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_process_production_actual AS
SELECT
    id,
    DATE(timestamp - INTERVAL 8 HOUR) AS business_day,
    operator_login_id,
    operator_name,
    process_id,
    product_code,
    product_id,
    product_name,
    qty,
    record_type,
    timestamp,
    equipment_state,
    interruption_reason_code,
    remarks
FROM t_process_realtime_record
WHERE record_type = 'PRODUCTION'
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_process_production_actual'


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0054_ai_equipment_view'),
        ('production', '0124_processrealtimerecord_interruption_reason_code'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
