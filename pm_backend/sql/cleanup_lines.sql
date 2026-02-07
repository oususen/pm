-- 本番DB用SQL: 未使用ライン削除 + ラインコード変更
-- 実行日: 2026-02-07

-- 1. 未使用ラインに紐づくPurchasePlanChangeLogを削除
DELETE FROM t_purchase_plan_change_log WHERE line_id IN (SELECT id FROM m_line WHERE id BETWEEN 15 AND 48);

-- 2. 未使用ライン削除 (id=15~48)
DELETE FROM m_line WHERE id BETWEEN 15 AND 48;

-- 3. ラインコード変更 (id=49~66) SUP-00xxxx → 仕入先コード
UPDATE m_line SET line_code = '000044' WHERE id = 49;
UPDATE m_line SET line_code = 'G00001' WHERE id = 50;
UPDATE m_line SET line_code = '000132' WHERE id = 51;
UPDATE m_line SET line_code = '000387' WHERE id = 52;
UPDATE m_line SET line_code = '010017' WHERE id = 53;
UPDATE m_line SET line_code = '000352' WHERE id = 54;
UPDATE m_line SET line_code = '000279' WHERE id = 55;
UPDATE m_line SET line_code = '000095' WHERE id = 56;
UPDATE m_line SET line_code = '000072' WHERE id = 57;
UPDATE m_line SET line_code = '000061' WHERE id = 58;
UPDATE m_line SET line_code = '000038' WHERE id = 59;
UPDATE m_line SET line_code = '000030' WHERE id = 60;
UPDATE m_line SET line_code = '000596' WHERE id = 61;
UPDATE m_line SET line_code = '000654' WHERE id = 62;
UPDATE m_line SET line_code = '000180' WHERE id = 63;
UPDATE m_line SET line_code = '000034' WHERE id = 64;
UPDATE m_line SET line_code = '000651' WHERE id = 65;
UPDATE m_line SET line_code = '000543' WHERE id = 66;

-- 4. 購入先ラインを有効化 (id=49~66) → 定時再計算の対象に含める
UPDATE m_line SET is_active = 1 WHERE id BETWEEN 49 AND 66;
