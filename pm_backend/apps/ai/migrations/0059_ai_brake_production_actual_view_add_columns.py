from django.db import migrations

# v_ai_brake_production_actual に operator_login_id・interruption_reason_code・remarks の3列を追加公開する。
# 2026-10-17、BOSS判断により非公開→公開に変更(経緯は AI用ビュー作成計画 §35.6 参照)。
# 0057は既にDBへ適用済み(13列版)のため、ここで CREATE OR REPLACE VIEW を再発行して16列へ更新する。
# 0057のファイル自体は適用済み内容(13列)のまま変更しない(適用済みマイグレーションの中身を後から
# 書き換えても、Djangoは再実行しないため)。
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を
# 使わない標準SQLだけで書く。
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_brake_production_actual AS
SELECT
    id,
    plan_date,
    product_code,
    operator_action,
    operator_action_reason,
    qty,
    sequence_no,
    recorded_at,
    equipment_id,
    line_id,
    process_id,
    product_id,
    operator_user_id,
    operator_login_id,
    interruption_reason_code,
    remarks
FROM brake_line_record
"""

# ロールバックは0057が作成した13列版に戻す
REVERT_VIEW = """
CREATE OR REPLACE VIEW v_ai_brake_production_actual AS
SELECT
    id,
    plan_date,
    product_code,
    operator_action,
    operator_action_reason,
    qty,
    sequence_no,
    recorded_at,
    equipment_id,
    line_id,
    process_id,
    product_id,
    operator_user_id
FROM brake_line_record
"""


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0057_ai_brake_production_actual_view'),
        ('ai', '0058_ai_laser_interruption_view'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, REVERT_VIEW)]
