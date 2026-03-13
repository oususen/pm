-- YD40002876 4層BOM 生成SQL
START TRANSACTION;
SET collation_connection='utf8mb4_unicode_ci';
SET @V := 'v_auto_20260313_2';
SET @D := CURDATE();

-- BOMヘッダ
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @V, @D, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD40002876'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id
    AND b.version COLLATE utf8mb4_unicode_ci = @V COLLATE utf8mb4_unicode_ci
    AND b.valid_from = @D
);
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @V, @D, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD40007244-00S'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id
    AND b.version COLLATE utf8mb4_unicode_ci = @V COLLATE utf8mb4_unicode_ci
    AND b.valid_from = @D
);
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @V, @D, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD40007244-00B'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id
    AND b.version COLLATE utf8mb4_unicode_ci = @V COLLATE utf8mb4_unicode_ci
    AND b.valid_from = @D
);
-- 2層目: YD40002876 -> 4013のV以外 (L0013/4013)
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046930-04S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046930-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046930-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046939-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046939-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046939-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046945-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046945-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046945-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='8049310' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='8049310')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='8049310'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='8093111' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='8093111')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='8093111'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9761613' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9761613')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9761613'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9763579' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9763579')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9763579'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9764973' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9764973')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9764973'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9770345' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9770345')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9770345'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00008119S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00008119S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00008119S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000396' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000396')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000396'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000402-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000402-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000402-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000406' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000406')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000406'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000419' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000419')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000419'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000420' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000420')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000420'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000424-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000424-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000424-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000426-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000426-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000426-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000428-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000428-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000428-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000432-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000432-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000432-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000433-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000433-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000433-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000437-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000437-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000437-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000444-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000444-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000444-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000445' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000445')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000445'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000447' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000447')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000447'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000451' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000451')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000451'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000470-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000470-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000470-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000472' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000472')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000472'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000474-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000474-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000474-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000474-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000474-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000474-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000476' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000476')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000476'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001005' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001005')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001005'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-01S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002332' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002332')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002332'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-30SUB' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-30SUB')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-30SUB'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002923-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002923-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002923-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003094-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003094-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003094-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003102-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003102-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003102-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003207-04S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003207-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003207-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-16S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-16S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-16S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-19S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-19S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-19S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-21S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-21S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-21S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-05S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-05S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-05S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003916-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003916-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003916-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005062-01S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005062-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005062-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005063-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005063-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005063-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-01S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-03S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-03S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-03S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-06S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-06S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-06S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005075-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005075-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005075-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005076-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005076-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005076-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006239-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006239-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006239-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006243-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006243-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006243-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006244' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006244')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006244'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006247-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006247-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006247-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006248-05S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006248-05S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006248-05S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-04S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006389-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006389-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006389-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-03S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-03S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-03S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006510' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006510')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006510'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006696-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006696-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006696-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-01S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-03S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-03S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-03S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-04S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006844-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006844-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006844-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006845' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006845')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006845'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006847-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006847-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006847-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006954-02S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006954-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006954-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007244-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007244-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007244-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007604-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007604-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007604-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007690-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007690-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007690-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007694-00S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007694-00S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007694-00S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007722-11S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007722-11S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007722-11S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40002876' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007722-12S' LIMIT 1),
  1.000, 'MAKE', 12, 10, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007722-12S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40002876'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007722-12S'
);
-- 3層目: YD40007244-00S -> 4010全 (L0010/4010)
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6024181-08B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6024181-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6024181-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6024273-10B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6024273-10B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6024273-10B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6025515-08B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6025515-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6025515-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046930-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046930-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046930-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046939-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046939-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046939-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046945-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046945-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046945-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9766120-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9766120-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9766120-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000869B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000869B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000869B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000886B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000886B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000886B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00003932B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00003932B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00003932B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00004405B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00004405B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00004405B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007853B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007853B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007853B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007854B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007854B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007854B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007856B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007856B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007856B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007876B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007876B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007876B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007877B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007877B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007877B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007878B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007878B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007878B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007879B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007879B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007879B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007880B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007880B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007880B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007881B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007881B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007881B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007882B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007882B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007882B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011326B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011326B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011326B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011327B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011327B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011327B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011328B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011328B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011328B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00012377B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00012377B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00012377B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00013052B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00013052B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00013052B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000396-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000396-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000396-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000402-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000402-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000402-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000406-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000406-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000406-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000419-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000419-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000419-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000420-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000420-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000420-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000424-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000424-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000424-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000427-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000427-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000427-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000427-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000427-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000427-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000428-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000428-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000428-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000428-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000428-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000428-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000432-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000432-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000432-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000432-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000432-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000432-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000433-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000433-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000433-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000433-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000433-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000433-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000437-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000437-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000437-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000441-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000441-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000441-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000444-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000444-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000444-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000444-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000444-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000444-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000447-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000447-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000447-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000448-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000448-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000448-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000451-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000451-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000451-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000460-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000460-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000460-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000460-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000460-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000460-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000470-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000470-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000470-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-10B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-10B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-10B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-16B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-16B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-16B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001005-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001005-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001005-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001049-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001049-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001049-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001454-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001454-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001454-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-01SB' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-01SB')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-01SB'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-02SB' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-02SB')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-02SB'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002332-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002332-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002332-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-28B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-28B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-28B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002876-05B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002876-05B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002876-05B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002923-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002923-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002923-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002923-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002923-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002923-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003091-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003091-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003091-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003094-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003094-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003094-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003095-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003095-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003095-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003095-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003095-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003095-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003207-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003207-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003207-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-16B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-16B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-16B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-19B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-19B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-19B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-21B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-21B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-21B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-05B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-05B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-05B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003916-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003916-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003916-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003916-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003916-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003916-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004397-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004397-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004397-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-06B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-06B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-06B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-07B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-07B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-07B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-08B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-10B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-10B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-10B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-27B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-27B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-27B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-28B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-28B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-28B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-31B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-31B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-31B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005063-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005063-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005063-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-06B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-06B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-06B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005075-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005075-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005075-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005076-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005076-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005076-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-05B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-05B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-05B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-08B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005997-22B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005997-22B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005997-22B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-13B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-13B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-13B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006239-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006239-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006239-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006244-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006244-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006244-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006247-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006247-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006247-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006248-05B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006248-05B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006248-05B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006510-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006510-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006510-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-04B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006844-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006844-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006844-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006845-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006845-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006845-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006847-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006847-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006847-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006849-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006849-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006849-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006941-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006941-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006941-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006954-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006954-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006954-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007244-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007244-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007244-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007604-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007604-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007604-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007690-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007690-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007690-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007693-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007693-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007693-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007693-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007693-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007693-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007694-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007694-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007694-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007695-08B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007695-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007695-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008342-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008342-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008342-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-00B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-00B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-00B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-03B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-21B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-21B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-21B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008485-01B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008485-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008485-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00S' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008485-02B' LIMIT 1),
  1.000, 'MAKE', 11, 9, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008485-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00S'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008485-02B'
);
-- 4層目: YD40007244-00B -> 801のV/R以外 (L0801/0801)
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='3056678' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='3056678')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='3056678'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='3109876' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='3109876')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='3109876'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='3109879' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='3109879')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='3109879'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='4373812' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='4373812')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='4373812'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='4642177' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='4642177')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='4642177'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6024181-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6024181-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6024181-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6024273-10' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6024273-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6024273-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6025515-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6025515-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6025515-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='6026280-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='6026280-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='6026280-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7043112-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7043112-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7043112-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046930-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046930-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046930-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='7046983-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='7046983-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='7046983-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='8084658-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='8084658-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='8084658-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='8103255-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='8103255-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='8103255-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9764973-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9764973-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9764973-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9766120-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9766120-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9766120-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='9766876-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='9766876-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='9766876-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000217' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000217')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000217'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000839' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000839')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000839'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000869' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000869')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000869'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00000886' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00000886')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00000886'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00003799' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00003799')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00003799'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00003932' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00003932')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00003932'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00004405' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00004405')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00004405'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007853' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007853')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007853'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007854' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007854')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007854'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007856' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007856')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007856'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007876' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007876')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007876'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007877' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007877')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007877'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007878' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007878')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007878'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007879' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007879')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007879'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007880' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007880')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007880'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007881' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007881')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007881'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00007882' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00007882')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00007882'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011326' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011326')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011326'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011327' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011327')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011327'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00011328' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00011328')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00011328'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00012365' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00012365')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00012365'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00012372' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00012372')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00012372'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00012377' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00012377')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00012377'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00013052' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00013052')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00013052'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD00016647' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD00016647')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD00016647'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000148' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000148')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000148'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000396-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000396-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000396-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000402-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000402-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000402-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000406-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000406-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000406-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000419-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000419-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000419-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000420-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000420-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000420-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000424-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000424-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000424-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000426-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000426-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000426-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000427-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000427-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000427-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000427-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000427-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000427-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000428-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000428-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000428-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000428-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000428-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000428-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000432-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000432-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000432-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000432-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000432-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000432-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000433-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000433-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000433-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000433-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000433-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000433-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000437-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000437-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000437-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000441-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000441-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000441-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000444-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000444-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000444-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000444-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000444-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000444-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000447-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000447-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000447-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000448-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000448-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000448-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000451-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000451-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000451-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000460-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000460-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000460-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000460-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000460-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000460-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000470-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000470-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000470-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000476-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000476-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000476-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-06' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-06')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-06'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-10' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000608-16' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000608-16')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000608-16'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000999-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000999-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000999-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40000999-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40000999-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40000999-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001001-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001001-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001001-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001005-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001005-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001005-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001049-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001049-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001049-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001049-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001049-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001049-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001053-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001053-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001053-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001341-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001341-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001341-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001403-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001403-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001403-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001454-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001454-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001454-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40001480-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40001480-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40001480-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002332-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002332-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002332-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002361-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002361-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002361-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002361-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002361-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002361-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002386-30' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002386-30')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002386-30'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002736-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002736-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002736-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002876-05' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002876-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002876-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002876-06' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002876-06')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002876-06'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002876-10' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002876-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002876-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002923-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002923-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002923-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002923-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002923-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002923-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40002946-29' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40002946-29')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40002946-29'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003032-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003032-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003032-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003032-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003032-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003032-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003091-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003091-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003091-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003094-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003094-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003094-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003095-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003095-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003095-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003095-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003095-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003095-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003102-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003102-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003102-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003111-11' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003111-11')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003111-11'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003207-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003207-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003207-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-09' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-09')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-09'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-16' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-16')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-16'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-19' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-19')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-19'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003380-21' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003380-21')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003380-21'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003912-05' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003912-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003912-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003916-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003916-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003916-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40003916-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40003916-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40003916-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004397-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004397-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004397-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004397-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004397-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004397-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004397-09' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004397-09')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004397-09'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-06' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-06')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-06'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-07' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-07')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-07'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-10' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-11' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-11')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-11'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-22' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-22')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-22'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-26' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-26')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-26'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-27' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-27')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-27'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-28' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-28')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-28'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-29' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-29')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-29'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-31' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-31')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-31'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-34' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-34')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-34'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40004738-35' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40004738-35')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40004738-35'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005062-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005062-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005062-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005063-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005063-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005063-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005073-06' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005073-06')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005073-06'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005075-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005075-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005075-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005076-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005076-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005076-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005551-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005551-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005551-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-05' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-09' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-09')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-09'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-23' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-23')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-23'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005598-24' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005598-24')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005598-24'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-05' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005763-13' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005763-13')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005763-13'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005997-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005997-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005997-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005997-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005997-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005997-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005997-21' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005997-21')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005997-21'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40005997-22' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40005997-22')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40005997-22'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006000-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006000-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006000-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006000-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006000-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006000-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006000-13' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006000-13')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006000-13'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006000-14' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006000-14')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006000-14'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-11' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-11')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-11'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-12' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-12')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-12'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006108-13' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006108-13')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006108-13'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006239-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006239-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006239-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006244-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006244-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006244-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006247-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006247-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006247-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006248-05' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006248-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006248-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006345-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006345-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006345-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006389-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006389-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006389-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006389-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006389-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006389-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006389-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006389-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006389-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006491-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006491-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006491-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006510-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006510-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006510-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006843-04' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006843-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006843-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006844-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006844-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006844-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006845-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006845-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006845-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006847-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006847-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006847-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006849-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006849-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006849-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006941-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006941-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006941-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40006954-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40006954-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40006954-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007244-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007244-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007244-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007244-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007244-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007244-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007604-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007604-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007604-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007690-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007690-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007690-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007693-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007693-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007693-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007693-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007693-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007693-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007694-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007694-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007694-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007695-07' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007695-07')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007695-07'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40007695-08' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40007695-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40007695-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008342-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008342-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008342-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008342-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008342-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008342-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-00' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-00')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-00'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-03' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008362-21' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008362-21')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008362-21'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008485-01' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008485-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008485-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, process_id, line_id, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='YD40007244-00B' AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci AND b.valid_from=@D LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='YD40008485-02' LIMIT 1),
  1.000, 'MAKE', 10, 8, 'DAY', 1, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='YD40008485-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='YD40007244-00B'
    AND b.version COLLATE utf8mb4_unicode_ci=@V COLLATE utf8mb4_unicode_ci
    AND b.valid_from=@D
    AND cp.product_code='YD40008485-02'
);
COMMIT;
