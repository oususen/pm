-- V053904703 ルーティング/BOM 生成SQL
START TRANSACTION;
SET collation_connection='utf8mb4_unicode_ci';
SET @BOM_VER := 'v_auto_20260313_1';
SET @BOM_DATE := CURDATE();

-- BOMヘッダ
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @BOM_VER, @BOM_DATE, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'V053904703'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id AND b.version = @BOM_VER AND b.valid_from = @BOM_DATE
);
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @BOM_VER, @BOM_DATE, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'V053104701-02S'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id AND b.version = @BOM_VER AND b.valid_from = @BOM_DATE
);
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, @BOM_VER, @BOM_DATE, NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'V053104701-02B'
AND NOT EXISTS (
  SELECT 1 FROM m_bom b
  WHERE b.parent_product_id = p.id AND b.version = @BOM_VER AND b.valid_from = @BOM_DATE
);
-- 2層目: V053904703 -> 4013(V*) すべて
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-01S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-02S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-07S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-07S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-07S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-10S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-10S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-10S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-01S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-02S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104704-07PS' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104704-07PS')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104704-07PS'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-07S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-07S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-07S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-09S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-09S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-09S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143613-05S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143613-05S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143613-05S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-03S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-03S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-03S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-04S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053904701-06S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053904701-06S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053904701-06S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104641-01S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104641-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104641-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104642-03S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104642-03S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104642-03S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104643-04S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104643-04S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104643-04S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-01S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-01S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-01S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-02S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-02S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-02S'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-19PS' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-19PS')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-19PS'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-21S' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-21S')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053904703' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-21S'
);
-- 3層目: V053104701-02S -> 4040(B) すべて
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102031B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102031B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102031B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102041B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102041B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102041B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102121B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102121B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102121B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102131B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102131B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102131B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102161B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102161B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102161B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102171B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102171B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102171B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC7A102031B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC7A102031B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC7A102031B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC7A102041B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC7A102041B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC7A102041B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC7A102121B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC7A102121B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC7A102121B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC7A102131B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC7A102131B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC7A102131B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841261-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841261-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841261-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841261-04B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841261-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841261-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841262-02B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841262-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841262-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053103704-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053103704-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053103704-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-01B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-02B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-07B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-07B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-07B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-09B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-09B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-09B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-10B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-10B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-10B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-02B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104703-04B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104703-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104703-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143521-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143521-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143521-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-02B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-06B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-06B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-06B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-07B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-07B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-07B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-08B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-08B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-08B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-09B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-09B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-09B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-10B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-10B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-10B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-11B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-11B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-11B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-12B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-12B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-12B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-13B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-13B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-13B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-19B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-19B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-19B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-20B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-20B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-20B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-21B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-21B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-21B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143613-05B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143613-05B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143613-05B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-04B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053904702-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053904702-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053904702-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104641-01B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104641-01B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104641-01B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104642-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104642-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104642-03B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104643-04B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104643-04B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104643-04B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-02B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-02B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-02B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-21B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-21B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-21B'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104703-03B' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104703-03B')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02S' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104703-03B'
);
-- 4層目: V053104701-02B -> 801(V/R) すべて
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RB44104461' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RB44104461')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RB44104461'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RC6A102091' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RC6A102091')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RC6A102091'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18804601' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18804601')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18804601'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841261-01' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841261-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841261-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841261-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841261-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841261-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841261-04' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841261-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841261-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='RD18841262-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='RD18841262-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='RD18841262-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053103704-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053103704-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053103704-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-01' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-07' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-07')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-07'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-09' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-09')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-09'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104641-10' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104641-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104641-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-17' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-17')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-17'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104701-18' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104701-18')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104701-18'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053104703-04' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053104703-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053104703-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143521-01' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143521-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143521-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143521-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143521-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143521-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143521-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143521-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143521-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143521-05' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143521-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143521-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-01' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-04' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-06' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-06')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-06'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-07' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-07')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-07'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-08' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-08')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-08'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-09' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-09')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-09'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-10' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-10')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-10'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-11' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-11')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-11'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-12' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-12')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-12'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-13' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-13')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-13'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-15' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-15')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-15'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-17' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-17')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-17'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-18' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-18')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-18'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-19' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-19')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-19'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-20' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-20')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-20'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143612-21' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143612-21')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143612-21'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053143613-05' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053143613-05')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053143613-05'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053504641-04' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053504641-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053504641-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053904702-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V053904702-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V053904702-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104641-01' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104641-01')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104641-01'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104642-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104642-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104642-03'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104643-04' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104643-04')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104643-04'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-02' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-02')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-02'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104701-21' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104701-21')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104701-21'
);
INSERT INTO m_bom_item (bom_id, child_product_id, quantity, sourcing_type, time_unit, lead_time_days, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id=pp.id WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V065104703-03' LIMIT 1),
  1.000, 'MAKE', 'DAY', 0, 0, NOW(), NOW()
FROM DUAL
WHERE EXISTS (SELECT 1 FROM m_product WHERE product_code='V065104703-03')
AND NOT EXISTS (
  SELECT 1 FROM m_bom_item bi
  JOIN m_bom b ON bi.bom_id=b.id
  JOIN m_product pp ON b.parent_product_id=pp.id
  JOIN m_product cp ON bi.child_product_id=cp.id
  WHERE pp.product_code='V053104701-02B' AND b.version=@BOM_VER AND b.valid_from=@BOM_DATE AND cp.product_code='V065104703-03'
);
-- ルーティング: V053904703 (L6200/6001)
INSERT INTO m_routing (product_id, routing_code, description, is_default, is_active, created_at, updated_at)
SELECT p.id, 'R_V053904703_6001', '自動作成: L6200/6001', 1, 1, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'V053904703'
AND NOT EXISTS (
  SELECT 1 FROM m_routing r WHERE r.product_id = p.id AND r.routing_code = 'R_V053904703_6001'
);

INSERT INTO m_routing_step (
  routing_id, step_no, process_id, line_id, output_product_id,
  hierarchy_path, hierarchy_depth, time_unit, lead_time_days,
  start_offset_min, duration_min, parallel_count, parallel_group, remark,
  created_at, updated_at
)
SELECT
  r.id, 1,
  (SELECT id FROM m_process WHERE process_code='6001' LIMIT 1),
  (SELECT id FROM m_line WHERE line_code='L6200' LIMIT 1),
  (SELECT id FROM m_product WHERE product_code='V053904703' LIMIT 1),
  '', 0, 'DAY', 1,
  NULL, NULL, 1, 1, '自動作成',
  NOW(), NOW()
FROM m_routing r
JOIN m_product p ON r.product_id = p.id
WHERE p.product_code='V053904703' AND r.routing_code='R_V053904703_6001'
AND NOT EXISTS (
  SELECT 1 FROM m_routing_step rs WHERE rs.routing_id=r.id AND rs.step_no=1 AND rs.parallel_group=1
);
COMMIT;
