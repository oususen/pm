-- 4010既存9件の設定補正
START TRANSACTION;

UPDATE m_product p
SET
  p.standard_lt_days = 1,
  p.line_id = (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  p.process_id = (SELECT id FROM m_process WHERE process_code = '4010' LIMIT 1),
  p.management_unit = 'DAY',
  p.is_line_final_product = 1,
  p.updated_at = NOW()
WHERE p.product_code IN ('YD40001005-00B','YD40002386-01B','YD40002386-28B','YD40003380-00B','YD40003380-01B','YD40003380-16B','YD40003380-19B','YD40003380-21B','YD40005997-22B');

COMMIT;