-- 4013.csv ナットスポット m_product 取込SQL
-- 条件: B付与なし / 既存product_codeはスキップ / 品名空は「なし」
-- 固定値: category=ASSEMBLY, unit=個, standard_lt_days=1, line=L0013, process=4013, management_unit=DAY,
--         is_line_final_product=1, is_active=1, is_final_product=0, is_virtual_set=0, is_phantom=0, order_lot_multiple=1
START TRANSACTION;

INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '7046930-04S', 'ﾌﾞﾗｹｯﾄ ｺﾝﾌﾟ', 'ﾌﾞﾗｹｯﾄ ｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '7046930-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '7046939-00S', 'ﾌﾞﾗｹｯﾄSUB', 'ﾌﾞﾗｹｯﾄSUB', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '7046939-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '7046945-00S', 'ﾌﾞﾗｹｯﾄSUB', 'ﾌﾞﾗｹｯﾄSUB', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '7046945-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '7046983-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '7046983-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '7046983-02S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '7046983-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '8049310', 'ﾌﾗﾝｼﾞ', 'ﾌﾗﾝｼﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '8049310'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '8093111', 'ﾌﾗﾝｼﾞ', 'ﾌﾗﾝｼﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '8093111'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '9761613', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '9761613'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '9763579', 'ｼ-ﾄ;ｽｸﾘｭ', 'ｼ-ﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '9763579'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '9764973', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '9764973'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  '9770345', 'ｼｰﾄ;ｽｸﾘｭ', 'ｼｰﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = '9770345'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-01S', '"COVER,AIRCT"', '"COVER,AIRCT"', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-02S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-07S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-07S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-10S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-10S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104701-01S', 'FRAME COMP', 'FRAME COMP', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104701-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104701-02S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104701-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104704-07PS', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104704-07PS'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-07S', 'RAG', 'RAG', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-07S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-09S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-09S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143613-05S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143613-05S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053504641-03S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053504641-03S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053504641-04S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053504641-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053904701-06S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053904701-06S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104641-01S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104641-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104642-03S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104642-03S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104643-04S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104643-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-01S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-02S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-19PS', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-19PS'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-21S', 'なし', 'なし', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-21S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD00008119S', 'ｶﾊﾞｰS', 'ｶﾊﾞｰS', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD00008119S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000396', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000396'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000402-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000402-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000406', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000406'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000419', 'ｼｰﾄ;ｽｸﾘｭ', 'ｼｰﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000419'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000420', 'ｼｰﾄ;ｽｸﾘｭ', 'ｼｰﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000420'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000424-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000424-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000426-00S', 'ｶﾊﾞｰ ﾎﾝﾀｲ', 'ｶﾊﾞｰ ﾎﾝﾀｲ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000426-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000428-00S', 'ﾌﾞﾗｹｯﾄ STIFF-C1', 'ﾌﾞﾗｹｯﾄ STIFF-C1', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000428-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000432-00S', 'ﾌﾞﾗｹｯﾄ STIFF-B1', 'ﾌﾞﾗｹｯﾄ STIFF-B1', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000432-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000433-00S', 'ﾌﾞﾗｹｯﾄ STIFF-A1', 'ﾌﾞﾗｹｯﾄ STIFF-A1', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000433-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000437-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000437-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000444-00S', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳｼﾀ', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳｼﾀ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000444-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000445', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾋﾀﾞﾘｼﾀﾀﾞｸﾄ', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾋﾀﾞﾘｼﾀﾀﾞｸﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000445'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000447', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳｼﾀ', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳｼﾀ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000447'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000451', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳ', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000451'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000470-00S', 'ｶﾊﾞｰ ﾌﾛｱﾍﾞｰｽ', 'ｶﾊﾞｰ ﾌﾛｱﾍﾞｰｽ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000470-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000472', 'ﾌﾞﾗｹｯﾄ ｹｼｮｳｶﾊﾞｰｼﾀ', 'ﾌﾞﾗｹｯﾄ ｹｼｮｳｶﾊﾞｰｼﾀ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000472'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000474-00S', 'ｶﾊﾞｰ U-5', 'ｶﾊﾞｰ U-5', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000474-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000474-02S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000474-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40000476', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000476'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40001005', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001005'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40001480-01S', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001480-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40001480-01S', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001480-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40001480-02S', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001480-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40001480-02S', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ﾌﾚｰﾑ ｻﾌﾞ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001480-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40002332', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40002332'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40002386-30SUB', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40002386-30SUB'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40002923-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40002923-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003094-00S', 'ｶﾊﾞｰ ﾌﾛｱﾍﾞｰｽ', 'ｶﾊﾞｰ ﾌﾛｱﾍﾞｰｽ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003094-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003102-00S', 'ｶﾊﾞｰ ﾎﾝﾀｲ', 'ｶﾊﾞｰ ﾎﾝﾀｲ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003102-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003207-04S', 'ﾌﾞﾗｹｯﾄ ｺﾝﾌﾟ', 'ﾌﾞﾗｹｯﾄ ｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003207-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003380-16S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-16S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003380-19S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-19S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003380-21S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-21S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003912-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003912-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003912-05S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003912-05S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40003916-02S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003916-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005062-01S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005062-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005063-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005063-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005073-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005073-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005073-01S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005073-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005073-02S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005073-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005073-03S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005073-03S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005073-06S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005073-06S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005075-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005075-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40005076-00S', 'ｶﾊﾞｰ', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005076-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006239-00S', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC 55UR-5', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC 55UR-5', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006239-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006243-00S', 'ｶﾊﾞｰ MC 55UR-5', 'ｶﾊﾞｰ MC 55UR-5', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006243-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006244', 'ｶﾊﾞｰ 内側ﾀﾞｸﾄ', 'ｶﾊﾞｰ 内側ﾀﾞｸﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006244'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006247-00S', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC U-5', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC U-5', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006247-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006248-05S', 'ﾌﾞﾗｹｯﾄ ﾌｨﾙﾀ', 'ﾌﾞﾗｹｯﾄ ﾌｨﾙﾀ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006248-05S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006345-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006345-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006345-04S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006345-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006389-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006389-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006491-00S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006491-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006491-02S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006491-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006491-03S', 'ﾌﾞﾗｹｯﾄ', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006491-03S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006510', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳ 5tonEN', 'ﾌﾞﾗｹｯﾄ ﾀﾃｶﾍﾞﾁｭｳｵｳ 5tonEN', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006510'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006696-00S', 'ｶﾊﾞｰ MC CANOPY', 'ｶﾊﾞｰ MC CANOPY', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006696-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006843-00S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-BK0', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-BK0', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006843-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006843-01S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-RH', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-RH', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006843-01S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006843-02S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-LH', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-LH', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006843-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006843-03S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-CTR', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-CTR', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006843-03S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006843-04S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-BK4', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-BK4', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006843-04S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006844-00S', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC 5tonEN', 'ﾌﾞﾗｹｯﾄ LH_ｼｰﾄﾍﾞｰｽMC 5tonEN', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006844-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006845', 'ﾌﾞﾗｹｯﾄ_ｼｰﾄﾍﾞｰｽｼﾀﾎｷｮｳEN', 'ﾌﾞﾗｹｯﾄ_ｼｰﾄﾍﾞｰｽｼﾀﾎｷｮｳEN', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006845'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006847-00S', 'ｶﾊﾞｰ 5tonEN', 'ｶﾊﾞｰ 5tonEN', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006847-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40006954-02S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-LH KTEG', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽEN-LH KTEG', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006954-02S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007244-00S', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽMC U-5NA', 'ｶﾊﾞｰ ｼｰﾄﾍﾞｰｽMC U-5NA', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007244-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007604-00S', 'ｶﾊﾞｰﾀﾃｶﾍﾞﾐｷﾞ_KTEG', 'ｶﾊﾞｰﾀﾃｶﾍﾞﾐｷﾞ_KTEG', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007604-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007690-00S', 'ｶﾊﾞｰ;ｼｰﾄﾍﾞｰｽLH 55US', 'ｶﾊﾞｰ;ｼｰﾄﾍﾞｰｽLH 55US', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007690-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007694-00S', 'ｶﾊﾞｰ;ﾌﾛｱﾍﾞｰｽ中央55US', 'ｶﾊﾞｰ;ﾌﾛｱﾍﾞｰｽ中央55US', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007694-00S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007722-11S', 'ﾌﾞﾗｹｯﾄ KTEG-CTR-UP-SUB', 'ﾌﾞﾗｹｯﾄ KTEG-CTR-UP-SUB', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007722-11S'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'YD40007722-12S', 'ﾌﾞﾗｹｯﾄ KTEG-CTR-LW-SUB', 'ﾌﾞﾗｹｯﾄ KTEG-CTR-LW-SUB', 'ASSEMBLY', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0013' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4013' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'YD40007722-12S'
);
COMMIT;
