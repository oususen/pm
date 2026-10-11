from django.db import migrations


# グループとラインの紐付(accounts_unit_line_mapping)をAI用に公開するビュー。
# 紐付を主とし、グループ(accounts_department)の名称と、ライン(m_line)のコード・名称を LEFT JOIN で付ける。
# 結合はすべて相手の主キー(u.id・l.id)との1対1のため、行数は accounts_unit_line_mapping と同じ。WHEREなし(全行)。
# 公開8列はBOSS承認(AI用ビュー作成計画 §28。2026-10-11。元テーブルの公開列は id・unit_id・line_id・sort_order・is_default の5列)。
# 非公開(ビューに含めない): created_at・updated_at
# 将来のPostgreSQL移行を考え、MySQL固有の記法(バッククォート・DEFINER・SQL SECURITY・DBの修飾)を使わない標準SQLだけで書く。
# (定義者・権限の付与は、DBごとに異なるため、マイグレーションに含めず、別の手順SQLで行う。AI用ビュー作成計画 §28)
CREATE_VIEW = """
CREATE OR REPLACE VIEW v_ai_unit_line AS
SELECT
    m.id,
    m.unit_id,
    u.name AS unit_name,
    m.line_id,
    l.line_code,
    l.line_name,
    m.sort_order,
    m.is_default
FROM accounts_unit_line_mapping m
LEFT JOIN accounts_department u ON u.id = m.unit_id
LEFT JOIN m_line l ON l.id = m.line_id
"""

DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_unit_line'


class Migration(migrations.Migration):
    # ビューの元になる列は accounts 0072(現行の最新)までで揃う(accounts_unit_line_mapping=0024〜0026)。m_line は既存。
    # ai 0047_aianalysisrun_purpose(別の作業で追加済みの AIAnalysisRun.purpose)の後に並べる(同じ 0046 から分岐させない)。
    dependencies = [
        ('ai', '0047_aianalysisrun_purpose'),
    ]

    operations = [migrations.RunSQL(CREATE_VIEW, DROP_VIEW)]
