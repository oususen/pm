-- 4040.CSV ブレーキ加工品 m_product 取込SQL
-- 条件: 品番末尾B付与 / 既存product_codeはスキップ / 品名空は「なし"
START TRANSACTION;

INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102031B', 'ﾀﾃｲﾀ・ｳｼﾛ(T-03)', 'ﾀﾃｲﾀ・ｳｼﾛ(T-03)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102031B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102041B', 'ﾀﾃｲﾀ・ﾏｴ(T-04)', 'ﾀﾃｲﾀ・ﾏｴ(T-04)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102041B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102121B', 'ﾀﾃｲﾀﾅｶ・L(T-12)', 'ﾀﾃｲﾀﾅｶ・L(T-12)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102121B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102131B', 'ﾀﾃｲﾀﾅｶ・R(T-13)', 'ﾀﾃｲﾀﾅｶ・R(T-13)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102131B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102161B', 'ﾎｷｮｳ ﾅｶ L(T-16)', 'ﾎｷｮｳ ﾅｶ L(T-16)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102161B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC6A102171B', 'ﾎｷｮｳ ﾅｶ R(T-17)', 'ﾎｷｮｳ ﾅｶ R(T-17)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC6A102171B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC7A102031B', 'ﾀﾃｲﾀｳｼﾛ(T-03)', 'ﾀﾃｲﾀｳｼﾛ(T-03)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC7A102031B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC7A102041B', 'ﾀﾃｲﾀﾏｴ(T-04)', 'ﾀﾃｲﾀﾏｴ(T-04)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC7A102041B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC7A102121B', 'ﾀﾃｲﾀﾅｶL(T-12)', 'ﾀﾃｲﾀﾅｶL(T-12)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC7A102121B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RC7A102131B', 'ﾀﾃｲﾀﾅｶR(T-13)', 'ﾀﾃｲﾀﾅｶR(T-13)', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RC7A102131B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RD18841261-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RD18841261-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RD18841261-04B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RD18841261-04B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'RD18841262-02B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'RD18841262-02B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053103704-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053103704-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-01B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-01B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-02B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-02B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-07B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-07B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-09B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-09B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104641-10B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104641-10B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104701-02B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104701-02B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053104703-04B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053104703-04B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143521-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143521-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-02B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-02B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-06B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-06B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-07B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-07B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-08B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-08B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-09B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-09B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-10B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-10B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-11B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-11B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-12B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-12B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-13B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-13B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-19B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-19B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-20B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-20B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143612-21B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143612-21B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053143613-05B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053143613-05B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053504641-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053504641-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053504641-04B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053504641-04B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V053904702-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V053904702-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104641-01B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104641-01B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104642-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104642-03B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104643-04B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104643-04B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-02B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-02B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104701-21B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104701-21B'
);
INSERT INTO m_product (
  product_code, product_name, product_name_halfwidth, category, unit, standard_lt_days, image_url,
  line_id, process_id, management_unit, self_lt_days,
  is_final_product, is_line_final_product, is_phantom, is_virtual_set,
  order_lot_min, order_lot_multiple, model_name, product_group_id, used_container_id, capacity,
  is_active, created_at, updated_at
)
SELECT
  'V065104703-03B', 'なし', 'なし', 'SINGLE', '個', 1, NULL,
  (SELECT id FROM m_line WHERE line_code = 'L0010' LIMIT 1),
  (SELECT id FROM m_process WHERE process_code = '4040' LIMIT 1),
  'DAY', NULL,
  0, 1, 0, 0,
  NULL, 1, NULL, NULL, NULL, NULL,
  1, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM m_product p WHERE p.product_code = 'V065104703-03B'
);
COMMIT;
