from django.db import migrations


# 稼働カレンダ(m_calendar_day)をAI用に公開するビュー。m_calendar_day を主とし、カレンダの属性(コード・名称・区分)を LEFT JOIN で付ける。
# 結合は m_calendar の主キー(id)との1対1のため、行数は m_calendar_day と同じ。WHEREなし(全行)。
# 公開12列はBOSS承認(AI用ビュー作成計画 §24。2026-10-10)。
# 非公開(ビューに含めない): m_calendar_day の note(備考)・created_at・updated_at、m_calendar の上記3列以外の列
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §24)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_calendar_day AS
SELECT
    d.id,
    d.calendar_id,
    c.calendar_code,
    c.calendar_name,
    c.calendar_type,
    d.target_date,
    d.is_working_day,
    d.is_delivery_day,
    d.is_order_day,
    d.is_holiday_work,
    d.work_minutes,
    d.work_pattern_id
FROM m_calendar_day d
LEFT JOIN m_calendar c ON c.id = d.calendar_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_calendar_day'


class Migration(migrations.Migration):
    # ビューの元になる列は masters 0086 までで揃う
    # (m_calendar_day: id・calendar_id・target_date・is_working_day・work_minutes=0001、work_pattern_id=0016、
    #  is_holiday_work=0074、is_delivery_day=0075、is_order_day=0086。
    #  m_calendar: id・calendar_code・calendar_name=0001、calendar_type=0057)
    dependencies = [
        ('ai', '0039_ai_customer_view'),
        ('masters', '0086_add_is_order_day_to_calendar_day'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
