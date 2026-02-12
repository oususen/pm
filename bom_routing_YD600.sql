-- Auto-generated SQL: BOM/Routing Import
-- Generated: 2026-02-13 05:26:08.191628
-- Includes m_product inserts (NOT EXISTS skip)

SET NAMES utf8mb4;

-- ========================================
-- Product data import (upsert by product_code)
-- ========================================

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8049310', 'ﾌﾗﾝｼﾞ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8049310'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4222008', 'M10XP1.5 ﾄｸNUT', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4222008'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810160', 'Oﾘﾝｸﾞ 1AG160', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA810160'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'P1.5X14X8X10', 'M10XP1.5 4ｶｸNUT', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'P1.5X14X8X10'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4137294', 'M10XP1.5 ｱｼﾅｼNUT', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4137294'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'Z449558', 'ｼｰﾙﾜｯｼｬ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'Z449558'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002179', 'ｷｬｯﾌﾟSCM2.250X1-1/2IL', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002179'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002175', 'ｷｬｯﾌﾟSCM34.0X38.0', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002175'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'J271025', 'ﾛｯｶｸﾎﾞﾙﾄ(ﾜｯｼｬｰ)', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'J271025'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'M10X16', 'ﾛｯｶｸﾎﾞﾙﾄ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'M10X16'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HJ260820990', 'ﾎﾞﾙﾄ;ｾﾑｽ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HJ260820990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002449', 'ﾏｽｷﾝｸﾞｷｬｯﾌﾟSC0.343×1"IL', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002449'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8049310-00', 'ﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8049310-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA885004', 'ﾌﾟﾗｸﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA885004'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002165', 'ｷｬｯﾌﾟSC0.187X1-1/2', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002165'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '12X6X8', '12X6X8', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '12X6X8'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40002386-04', '◆外作◆（ﾀﾝｸ）', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40002386-04'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6026280-03', 'ｶｰﾄﾘｯｼﾞﾎﾙﾀﾞﾎﾞﾄﾑ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '6026280-03'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '14X8X10', 'ｳｪﾙﾄﾞﾅｯﾄ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '14X8X10'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4684873', 'ｶｰﾄﾘｯｼﾞﾄｯﾌﾟﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4684873'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6026280-141516', 'ﾊﾟｲﾌﾟSUB COMP', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '6026280-141516'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4684874', 'EXﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4684874'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810110990', 'Oﾘﾝｸﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA810110990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003052', 'ｶﾊﾞｰ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003052'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003052-00', 'ﾌﾟﾚｰﾄ T', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003052-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8113793-01', '◆外作◆(ﾀﾝｸ)φ70Ｘ3.5Ｘ10', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8113793-01'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HJ260816990', 'ﾎﾞﾙﾄ;ｾﾑｽ XXXｼﾖｳｾｽﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HJ260816990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HJ260814990', 'ﾎﾞﾙﾄ;ｾﾑｽ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HJ260814990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810070990', 'Oﾘﾝｸﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA810070990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003299', 'ｷｬｯﾌﾟSC1.000X1IL', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980003299'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003298', 'ﾌﾟﾗｸﾞ小SR1013-12672', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980003298'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980004023', 'ﾏｽｷﾝｸﾞｷｬｯﾌﾟSCM13.0X20.0L', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980004023'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4442446', 'ﾌｨﾙﾀ;ﾘﾀｰﾝ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4442446'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4479355', 'ﾌｨﾙﾀ;ｻｸｼｮﾝ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4479355'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD60011305', 'タンク；オイル', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD60011305'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD60009874', 'タンク；オイル（Ｋ）', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD60009874'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003052SUB', 'カバー', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003052SUB'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4198414', 'ｿｹｯﾄ;M', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4198414'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4444193', 'ｶﾊﾞｰ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4444193'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4440432', 'ｿｹｯﾄ;M', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4440432'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4477456', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4477456'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7043112-03', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7043112-03'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810060', 'Oﾘﾝｸﾞ 1AG060', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA810060'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'J780616', 'ﾎﾞﾙﾄ;ｿｹｯﾄ M6X16', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'J780616'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4364696', 'ﾌﾟﾗｸﾞ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4364696'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4250261', 'ｶﾞｽｹｯﾄ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4250261'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002169', 'ﾌﾟﾗｸﾞ中 SR1013-12677', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002169'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002170', 'ﾌﾟﾗｸﾞ大SR1013-12681', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980002170'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003306', 'ｷｬｯﾌﾟSCM43.0X38.0L', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '89980003306'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4444482', 'ｽﾌﾟﾘﾝｸﾞ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4444482'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4434017', 'ﾌﾞﾘｰｻﾞ;ｴｱ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4434017'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7043112-03B', 'ﾌﾞﾗｹｯﾄＢ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7043112-03B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4448602', 'ｴﾚﾒﾝﾄﾌｨﾙﾀ(K) ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4448602'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4449478', 'ｲﾝｼﾞｹｰﾀ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4449478'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40006531', 'ﾀﾝｸ;ｵｲﾙ ｾｲｶﾝ(EN)', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006531'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-00SUB', 'ﾀﾝｸ;ｵｲﾙSUB00', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-00SUB'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-00', 'ﾀﾝｸ;ｵｲﾙ00', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-10', 'ﾊﾟｲﾌﾟ;ﾘﾀｰﾝ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-10'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-11', 'ﾊﾟｲﾌﾟ;ﾌｨﾙﾀｰｹｰｽEX', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-11'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-01', 'ﾀﾝｸ;ｵｲﾙ01', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-01'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40006531-02S', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006531-02S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40006531-02', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006531-02'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-27', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-27'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-04', 'ﾌﾞﾗｹｯﾄ T-19-6', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-04'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-16S', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-16S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-16', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-16'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD00009850', 'ｿｹｯﾄ;M', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD00009850'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD00009851', 'ｿｹｯﾄ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD00009851'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4338830', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4338830'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-19S', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-19S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-19', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-19'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-21S', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-21S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-21', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-21'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-24', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-24'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'H4667127990', 'ｱﾀﾞﾌﾟﾀ;S', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'H4667127990'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA885002', 'ﾌﾟﾗｸﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA885002'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA885008', 'ﾏｽｷﾝｸﾞｷｬｯﾌﾟ G1ﾈｼﾞﾖｳ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HA885008'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4239713', 'ﾁｰ;S ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4239713'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'A852432', 'ﾁｰ;S ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'A852432'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'A852132', 'ｱﾀﾞﾌﾟﾀ;S ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'A852132'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'A852133', 'ｱﾀﾞﾌﾟﾀ;S ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'A852133'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40006531S', 'ﾀﾝｸ;ｵｲﾙ (EN)水没', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006531S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40006531H', '19-EN箱組後', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40006531H'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-19B', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-19B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-21B', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-21B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-00B', 'ﾀﾝｸ;ｵｲﾙ00B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-00B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-01B', 'ﾀﾝｸ;ｵｲﾙ01B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-01B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40003380-16B', 'ブラケット', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40003380-16B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551', 'ﾀﾝｸ;ｵｲﾙ ｾｲｶﾝ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40000999-00SUB', 'ﾀﾝｸ;ｵｲﾙ ｻﾌﾞｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000999-00SUB'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40000999-00', 'ｵｲﾙﾀﾝｸ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000999-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749', 'ｹｰｽ;ﾌｨﾙﾀ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7052749'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '3093554', 'ﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '3093554'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-01', 'ﾊﾟｲﾌﾟ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7052749-01'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-04', '◆外作◆(ﾀﾝｸ）Φ42.7Ｘ3.5Ｘ118', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7052749-04'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-06', '◆外作◆（ﾀﾝｸ)Φ34Ｘ3.2Ｘ315曲', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '7052749-06'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-04', 'ﾌﾟﾚｰﾄ（小）', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '6027849-04'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HC9.0X19.0X645.0', 'ﾎｷｮｳﾌﾟﾚｰﾄ_6027849-07', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HC9.0X19.0X645.0'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551-01SUB', 'ﾀﾝｸ;ｵｲﾙ ｻﾌﾞｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551-01SUB'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551-01', 'ｵｲﾙﾀﾝｸ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551-01'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-05', 'ﾌﾟﾚｰﾄ（大)', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '6027849-05'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '3094857', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '3094857'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9761676', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '9761676'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9761676-00', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '9761676-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4609532', 'ﾅｯﾄ;ｳｪﾙﾄﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4609532'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4257926', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4257926'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197', 'ﾊﾟｲﾌﾟ;ｻｸｼｮﾝ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8109197'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197-00', 'ﾊﾟｲﾌﾟ U-00', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8109197-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197-01', 'ﾊﾟｲﾌﾟ U-01', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '8109197-01'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40000999-10', 'ﾌﾟﾚｰﾄ T-75-5', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000999-10'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001005', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001005'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001005-00', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001005-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9764308', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '9764308'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001', 'ｼｰﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001-00', 'ｼｰﾄ;ｽｸﾘｭ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001-00'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD00004260', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD00004260'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-11', 'ﾌﾟﾚｰﾄ T-75-5', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '6027849-11'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9765592', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '9765592'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HZ997330', 'Oﾘﾝｸﾞ 1AP140', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'HZ997330'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4448606', 'ｶﾊﾞｰ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4448606'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4670343', 'ﾌｨﾙﾀ;ｻｸｼｮﾝ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '4670343'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9210864', 'ｶﾊﾞｰ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = '9210864'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001005-00B', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001005-00B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551-01B', '5型７Ｔ０1B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551-01B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40000999-00B', '5型７Ｔ０0B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000999-00B'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551S', 'ﾀﾝｸ;ｵｲﾙ 水没', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551S'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005551H', '５型7T　箱組後', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005551H'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001005SUB', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001005SUB'
);

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001-00B', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001-00B'
);

-- ========================================
-- BOM data import
-- ========================================

-- BOM: YD60009874 v1
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD60009874'
AND NOT EXISTS (
    SELECT 1 FROM m_bom b
    JOIN m_product pp ON b.parent_product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND b.valid_from = '2026-02-11'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980002169'),
    6.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000596'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980002169'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980002170'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980002170'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980002175'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980002175'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980002179'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980002179'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980003298'),
    3.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980003298'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980003299'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980003299'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '89980003306'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '89980003306'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'Z449558'),
    2.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'Z449558'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'HA810060'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'HA810060'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'HA810160'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'HA810160'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'HA885004'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'HA885004'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'HZ997330'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'HZ997330'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'J271025'),
    12.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'J271025'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'J780616'),
    4.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000038'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'J780616'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'M10X16'),
    2.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000038'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'M10X16'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4250261'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4250261'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4364696'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4364696'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4434017'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4434017'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4444482'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4444482'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4448602'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4448602'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4448606'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4448606'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4449478'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4449478'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '9210864'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '9210864'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = '4670343'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = '4670343'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND b.version = 'v1' AND b.valid_from = '2026-02-11'),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551S'),
    1.000, NULL, 'MAKE',
    NULL, (SELECT id FROM m_process WHERE process_code = '4030'), (SELECT id FROM m_line WHERE line_code = 'L2200'),
    'MINUTE', 0, 20,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND b.version = 'v1'
    AND cp.product_code = 'YD40005551S'
);

-- BOM: YD60011305 v1
INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT p.id, 'v1', '2026-02-09', NULL, 1, 0, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD60011305'
AND NOT EXISTS (
    SELECT 1 FROM m_bom b
    JOIN m_product pp ON b.parent_product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND b.valid_from = '2026-02-09'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '89980002165'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '89980002165'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '89980002175'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '89980002175'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '89980002449'),
    4.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '89980002449'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '89980004023'),
    2.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000654'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '89980004023'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'H4667127990'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000651'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'H4667127990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HA810070990'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HA810070990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HA810110990'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HA810110990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HA885002'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = '000030'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HA885002'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HA885008'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HA885008'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HJ260814990'),
    4.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HJ260814990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HJ260816990'),
    4.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HJ260816990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'HJ260820990'),
    4.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'HJ260820990'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '4239713'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '4239713'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '4442446'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '4442446'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = '4479355'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = '4479355'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'A852132'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'A852132'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'A852133'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'A852133'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'A852432'),
    1.000, NULL, 'BUY',
    (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), NULL, NULL,
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'A852432'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'YD40003052'),
    1.000, NULL, 'SUBCON',
    (SELECT id FROM m_supplier WHERE supplier_code = '000543'), (SELECT id FROM m_process WHERE process_code = 'G'), (SELECT id FROM m_line WHERE line_code = 'GAISAKU'),
    'DAY', 1, NULL,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'YD40003052'
);

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, supplier_id, process_id, line_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, remark, created_at, updated_at)
SELECT
    (SELECT b.id FROM m_bom b JOIN m_product pp ON b.parent_product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND b.version = 'v1' AND b.valid_from = '2026-02-09'),
    (SELECT id FROM m_product WHERE product_code = 'YD40006531S'),
    1.000, NULL, 'MAKE',
    NULL, (SELECT id FROM m_process WHERE process_code = '4030'), (SELECT id FROM m_line WHERE line_code = 'L2200'),
    'MINUTE', 0, 15,
    0, '', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_bom_item bi
    JOIN m_bom b ON bi.bom_id = b.id
    JOIN m_product pp ON b.parent_product_id = pp.id
    JOIN m_product cp ON bi.child_product_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND b.version = 'v1'
    AND cp.product_code = 'YD40006531S'
);

-- ========================================
-- Routing data import
-- ========================================

-- Routing: YD60009874 - YD60009874
INSERT INTO m_routing (product_id, routing_code, description, is_default, is_active, created_at, updated_at)
SELECT p.id, 'YD60009874', 'bomから自動生成', 1, 1, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD60009874'
AND NOT EXISTS (
    SELECT 1 FROM m_routing r
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40000999-00'),
    '25.1.1.1.1.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2511111, 'YD40000999-00B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 0
    AND rs.parallel_group = 2511111
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40005551-01'),
    '25.1.1.2.1.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2511211, 'YD40005551-01B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 0
    AND rs.parallel_group = 2511211
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = '7043112-03'),
    '25.1.1.3.4.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2511341, '7043112-03B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 0
    AND rs.parallel_group = 2511341
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40001005-00'),
    '25.1.3.1.1.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2513111, 'YD40001005-00B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 0
    AND rs.parallel_group = 2513111
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40000999-00B'),
    '25.1.1.1.1', 4, 'MINUTE',
    0, NULL, 15,
    1, 251111, 'YD40000999-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251111
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 1000
     AND rs.parallel_group = 251111),
    (SELECT id FROM m_product WHERE product_code = 'YD40000999-00'),
    1.000, 'START', 'Auto from child BOM 72', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND cp.product_code = 'YD40000999-00'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000048'), (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
    '25.1.1.1.2', 4, 'DAY',
    1, NULL, NULL,
    1, 251112, 'YD40000999-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251112
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40005551-01B'),
    '25.1.1.2.1', 4, 'MINUTE',
    0, NULL, 16,
    1, 251121, 'YD40005551-01SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251121
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 1000
     AND rs.parallel_group = 251121),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551-01'),
    1.000, 'START', 'Auto from child BOM 70', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND cp.product_code = 'YD40005551-01'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000048'), (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
    '25.1.1.2.2', 4, 'DAY',
    1, NULL, NULL,
    1, 251122, 'YD40005551-01SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251122
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000095'), (SELECT id FROM m_product WHERE product_code = '7052749-01'),
    '25.1.1.3.1', 4, 'DAY',
    1, NULL, NULL,
    1, 251131, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251131
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000034'), (SELECT id FROM m_product WHERE product_code = '7052749-04'),
    '25.1.1.3.2', 4, 'DAY',
    1, NULL, NULL,
    1, 251132, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251132
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000034'), (SELECT id FROM m_product WHERE product_code = '7052749-06'),
    '25.1.1.3.3', 4, 'DAY',
    1, NULL, NULL,
    1, 251133, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251133
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = '7043112-03B'),
    '25.1.1.3.4', 4, 'DAY',
    1, NULL, NULL,
    1, 251134, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251134
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 1000
     AND rs.parallel_group = 251134),
    (SELECT id FROM m_product WHERE product_code = '7043112-03'),
    1.000, 'START', 'Auto from child BOM 47', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND cp.product_code = '7043112-03'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000072'), (SELECT id FROM m_product WHERE product_code = '4444193'),
    '25.1.1.3.5', 4, 'DAY',
    1, NULL, NULL,
    1, 251135, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251135
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '010017'), (SELECT id FROM m_product WHERE product_code = '3093554'),
    '25.1.1.3.6', 4, 'DAY',
    1, NULL, NULL,
    1, 251136, '7052749', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251136
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40001001-00'),
    '25.1.2.1.1', 4, 'DAY',
    1, NULL, NULL,
    1, 251211, 'YD40001001-00B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251211
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40001005-00B'),
    '25.1.3.1.1', 4, 'DAY',
    1, NULL, NULL,
    1, 251311, 'YD40001005', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251311
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 1000
     AND rs.parallel_group = 251311),
    (SELECT id FROM m_product WHERE product_code = 'YD40001005-00'),
    1.000, 'START', 'Auto from child BOM 81', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND cp.product_code = 'YD40001005-00'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = 'P1.5X14X8X10'),
    '25.1.3.1.2', 4, 'DAY',
    1, NULL, NULL,
    1, 251312, 'YD40001005', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 251312
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000061'), (SELECT id FROM m_product WHERE product_code = '9761676-00'),
    '25.1.1.10.1', 4, 'DAY',
    1, NULL, NULL,
    1, 2511101, '9761676', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 2511101
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000044'), (SELECT id FROM m_product WHERE product_code = '4609532'),
    '25.1.1.10.2', 4, 'DAY',
    1, NULL, NULL,
    1, 2511102, '9761676', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 2511102
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = '8109197-01'),
    '25.1.1.14.1', 4, 'DAY',
    1, NULL, NULL,
    1, 2511141, '8109197', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 2511141
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = '8109197-00'),
    '25.1.1.14.2', 4, 'DAY',
    1, NULL, NULL,
    1, 2511142, '8109197', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 1000
    AND rs.parallel_group = 2511142
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40000999-00SUB'),
    '25.1.1.1', 3, 'MINUTE',
    0, NULL, 15,
    1, 25111, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25111
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25111),
    (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
    1.000, 'START', 'Auto from child BOM 73', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'HC9.0X19.0X645.0'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25111),
    (SELECT id FROM m_product WHERE product_code = 'YD40000999-00B'),
    1.000, 'START', 'Auto from child BOM 73', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40000999-00B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40005551-01SUB'),
    '25.1.1.2', 3, 'MINUTE',
    0, NULL, 15,
    1, 25112, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25112
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25112),
    (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
    1.000, 'START', 'Auto from child BOM 71', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'HC9.0X19.0X645.0'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25112),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551-01B'),
    1.000, 'START', 'Auto from child BOM 71', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40005551-01B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = '7052749'),
    '25.1.1.3', 3, 'MINUTE',
    0, NULL, 15,
    1, 25113, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25113
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '4444193'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '4444193'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '7043112-03B'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '7043112-03B'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '3093554'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '3093554'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '7052749-01'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '7052749-01'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '7052749-04'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '7052749-04'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25113),
    (SELECT id FROM m_product WHERE product_code = '7052749-06'),
    1.000, 'START', 'Auto from child BOM 83', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '7052749-06'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000352'), (SELECT id FROM m_product WHERE product_code = '6027849-04'),
    '25.1.1.4', 3, 'DAY',
    1, NULL, NULL,
    1, 25114, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25114
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000352'), (SELECT id FROM m_product WHERE product_code = '6027849-05'),
    '25.1.1.5', 3, 'DAY',
    1, NULL, NULL,
    1, 25115, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25115
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = '4257926'),
    '25.1.1.6', 3, 'DAY',
    1, NULL, NULL,
    1, 25116, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25116
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '010017'), (SELECT id FROM m_product WHERE product_code = '4477456'),
    '25.1.1.7', 3, 'DAY',
    1, NULL, NULL,
    1, 25117, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25117
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = '3094857'),
    '25.1.1.8', 3, 'DAY',
    1, NULL, NULL,
    1, 25118, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25118
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '010017'), (SELECT id FROM m_product WHERE product_code = '4198414'),
    '25.1.1.9', 3, 'DAY',
    1, NULL, NULL,
    1, 25119, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25119
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'G'),
    (SELECT id FROM m_line WHERE line_code = 'GAISAKU'), (SELECT id FROM m_product WHERE product_code = 'YD40001001-00B'),
    '25.1.2.1', 3, 'DAY',
    1, NULL, NULL,
    1, 25121, 'YD40001001', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25121
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25121),
    (SELECT id FROM m_product WHERE product_code = 'YD40001001-00'),
    1.000, 'START', 'Auto from child BOM 79', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40001001-00'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000044'), (SELECT id FROM m_product WHERE product_code = '4222008'),
    '25.1.2.2', 3, 'DAY',
    1, NULL, NULL,
    1, 25122, 'YD40001001', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25122
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4013'),
    (SELECT id FROM m_line WHERE line_code = 'L0013'), (SELECT id FROM m_product WHERE product_code = 'YD40001005'),
    '25.1.3.1', 3, 'DAY',
    1, NULL, NULL,
    1, 25131, 'YD40001005SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25131
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25131),
    (SELECT id FROM m_product WHERE product_code = 'P1.5X14X8X10'),
    2.000, 'START', 'Auto from child BOM 68', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'P1.5X14X8X10'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 25131),
    (SELECT id FROM m_product WHERE product_code = 'YD40001005-00B'),
    1.000, 'START', 'Auto from child BOM 68', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40001005-00B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000072'), (SELECT id FROM m_product WHERE product_code = '8049310-00'),
    '25.1.8.1', 3, 'DAY',
    1, NULL, NULL,
    1, 25181, '8049310', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25181
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = '14X8X10'),
    '25.1.8.2', 3, 'DAY',
    1, NULL, NULL,
    1, 25182, '8049310', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 25182
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = '9761676'),
    '25.1.1.10', 3, 'DAY',
    1, NULL, NULL,
    1, 251110, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 251110
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 251110),
    (SELECT id FROM m_product WHERE product_code = '9761676-00'),
    1.000, 'START', 'Auto from child BOM 77', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '9761676-00'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 251110),
    (SELECT id FROM m_product WHERE product_code = '4609532'),
    1.000, 'START', 'Auto from child BOM 77', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '4609532'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '010017'), (SELECT id FROM m_product WHERE product_code = '4440432'),
    '25.1.1.11', 3, 'DAY',
    1, NULL, NULL,
    1, 251111, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 251111
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000387'), (SELECT id FROM m_product WHERE product_code = 'YD40000999-10'),
    '25.1.1.12', 3, 'DAY',
    1, NULL, NULL,
    1, 251112, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 251112
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000387'), (SELECT id FROM m_product WHERE product_code = '6027849-11'),
    '25.1.1.13', 3, 'DAY',
    1, NULL, NULL,
    1, 251113, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 251113
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = '8109197'),
    '25.1.1.14', 3, 'DAY',
    1, NULL, NULL,
    1, 251114, 'YD40005551H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND rs.parallel_group = 251114
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 251114),
    (SELECT id FROM m_product WHERE product_code = '8109197-00'),
    1.000, 'START', 'Auto from child BOM 82', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '8109197-00'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 2000
     AND rs.parallel_group = 251114),
    (SELECT id FROM m_product WHERE product_code = '8109197-01'),
    1.000, 'START', 'Auto from child BOM 82', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 2000
    AND cp.product_code = '8109197-01'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4019'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40005551H'),
    '25.1.1', 2, 'MINUTE',
    0, NULL, 20,
    1, 2511, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2511
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '4198414'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4198414'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '4440432'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4440432'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '4477456'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4477456'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = 'YD40000999-00SUB'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40000999-00SUB'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '7052749'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '7052749'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '6027849-04'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '6027849-04'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551-01SUB'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40005551-01SUB'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '6027849-05'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '6027849-05'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '3094857'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '3094857'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '9761676'),
    2.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '9761676'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '4257926'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4257926'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '8109197'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '8109197'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = 'YD40000999-10'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40000999-10'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2511),
    (SELECT id FROM m_product WHERE product_code = '6027849-11'),
    1.000, 'START', 'Auto from child BOM 74', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '6027849-11'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = 'YD40001001'),
    '25.1.2', 2, 'DAY',
    1, NULL, NULL,
    1, 2512, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2512
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2512),
    (SELECT id FROM m_product WHERE product_code = '4222008'),
    1.000, 'START', 'Auto from child BOM 78', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4222008'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2512),
    (SELECT id FROM m_product WHERE product_code = 'YD40001001-00B'),
    1.000, 'START', 'Auto from child BOM 78', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40001001-00B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = 'YD40001005SUB'),
    '25.1.3', 2, 'DAY',
    1, NULL, NULL,
    1, 2513, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2513
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2513),
    (SELECT id FROM m_product WHERE product_code = 'YD40001005'),
    1.000, 'START', 'Auto from child BOM 80', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40001005'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = '9761676'),
    '25.1.4', 2, 'DAY',
    1, NULL, NULL,
    1, 2514, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2514
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2514),
    (SELECT id FROM m_product WHERE product_code = '9761676-00'),
    1.000, 'START', 'Auto from child BOM 77', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '9761676-00'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2514),
    (SELECT id FROM m_product WHERE product_code = '4609532'),
    1.000, 'START', 'Auto from child BOM 77', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '4609532'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000180'), (SELECT id FROM m_product WHERE product_code = '9764308'),
    '25.1.5', 2, 'DAY',
    1, NULL, NULL,
    1, 2515, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2515
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000180'), (SELECT id FROM m_product WHERE product_code = '9765592'),
    '25.1.6', 2, 'DAY',
    1, NULL, NULL,
    1, 2516, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2516
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = 'YD00004260'),
    '25.1.7', 2, 'DAY',
    1, NULL, NULL,
    1, 2517, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2517
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4013'),
    (SELECT id FROM m_line WHERE line_code = 'L0013'), (SELECT id FROM m_product WHERE product_code = '8049310'),
    '25.1.8', 2, 'DAY',
    1, NULL, NULL,
    1, 2518, 'YD40005551', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2518
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2518),
    (SELECT id FROM m_product WHERE product_code = '8049310-00'),
    1.000, 'START', 'Auto from child BOM 18', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '8049310-00'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2518),
    (SELECT id FROM m_product WHERE product_code = '14X8X10'),
    6.000, 'START', 'Auto from child BOM 18', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 3000
    AND cp.product_code = '14X8X10'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    4000,
    (SELECT id FROM m_process WHERE process_code = '4053'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40005551'),
    '25.1', 1, 'MINUTE',
    0, NULL, 15,
    1, 251, 'YD40005551S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND rs.parallel_group = 251
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = '8049310'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = '8049310'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = '9761676'),
    2.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = '9761676'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = '9764308'),
    2.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = '9764308'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = 'YD40001001'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40001001'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = 'YD00004260'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD00004260'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = '9765592'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = '9765592'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551H'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40005551H'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 4000
     AND rs.parallel_group = 251),
    (SELECT id FROM m_product WHERE product_code = 'YD40001005SUB'),
    1.000, 'START', 'Auto from child BOM 76', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40001005SUB'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000596'), (SELECT id FROM m_product WHERE product_code = '89980002169'),
    '1', 0, 'DAY',
    1, NULL, NULL,
    1, 1, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 1
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002170'),
    '2', 0, 'DAY',
    1, NULL, NULL,
    1, 2, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 2
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002175'),
    '3', 0, 'DAY',
    1, NULL, NULL,
    1, 3, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 3
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002179'),
    '4', 0, 'DAY',
    1, NULL, NULL,
    1, 4, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 4
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980003298'),
    '5', 0, 'DAY',
    1, NULL, NULL,
    1, 5, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 5
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980003299'),
    '6', 0, 'DAY',
    1, NULL, NULL,
    1, 6, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 6
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980003306'),
    '7', 0, 'DAY',
    1, NULL, NULL,
    1, 7, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 7
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'Z449558'),
    '8', 0, 'DAY',
    1, NULL, NULL,
    1, 8, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 8
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA810060'),
    '9', 0, 'DAY',
    1, NULL, NULL,
    1, 9, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 9
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA810160'),
    '10', 0, 'DAY',
    1, NULL, NULL,
    1, 10, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 10
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA885004'),
    '11', 0, 'DAY',
    1, NULL, NULL,
    1, 11, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 11
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HZ997330'),
    '12', 0, 'DAY',
    1, NULL, NULL,
    1, 12, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 12
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'J271025'),
    '13', 0, 'DAY',
    1, NULL, NULL,
    1, 13, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 13
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = 'J780616'),
    '14', 0, 'DAY',
    1, NULL, NULL,
    1, 14, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 14
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = 'M10X16'),
    '15', 0, 'DAY',
    1, NULL, NULL,
    1, 15, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 15
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4250261'),
    '16', 0, 'DAY',
    1, NULL, NULL,
    1, 16, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 16
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4364696'),
    '17', 0, 'DAY',
    1, NULL, NULL,
    1, 17, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 17
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4434017'),
    '18', 0, 'DAY',
    1, NULL, NULL,
    1, 18, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 18
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4444482'),
    '19', 0, 'DAY',
    1, NULL, NULL,
    1, 19, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 19
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4448602'),
    '20', 0, 'DAY',
    1, NULL, NULL,
    1, 20, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 20
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4448606'),
    '21', 0, 'DAY',
    1, NULL, NULL,
    1, 21, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 21
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4449478'),
    '22', 0, 'DAY',
    1, NULL, NULL,
    1, 22, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 22
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '9210864'),
    '23', 0, 'DAY',
    1, NULL, NULL,
    1, 23, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 23
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4670343'),
    '24', 0, 'DAY',
    1, NULL, NULL,
    1, 24, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 24
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5000,
    (SELECT id FROM m_process WHERE process_code = '4030'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40005551S'),
    '25', 0, 'MINUTE',
    0, NULL, 20,
    1, 25, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND rs.parallel_group = 25
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874'
     AND r.routing_code = 'YD60009874'
     AND rs.step_no = 5000
     AND rs.parallel_group = 25),
    (SELECT id FROM m_product WHERE product_code = 'YD40005551'),
    1.000, 'START', 'Auto from child BOM 75', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5000
    AND cp.product_code = 'YD40005551'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60009874' AND r.routing_code = 'YD60009874'),
    5001,
    (SELECT id FROM m_process WHERE process_code = '4007'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD60009874'),
    'final', 0, 'MINUTE',
    0, NULL, 20,
    1, 1, 'YD60009874', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60009874'
    AND r.routing_code = 'YD60009874'
    AND rs.step_no = 5001
    AND rs.parallel_group = 1
);

-- Routing: YD60011305 - YD60011305
INSERT INTO m_routing (product_id, routing_code, description, is_default, is_active, created_at, updated_at)
SELECT p.id, 'YD60011305', 'BOMから自動生成', 1, 1, NOW(), NOW()
FROM m_product p
WHERE p.product_code = 'YD60011305'
AND NOT EXISTS (
    SELECT 1 FROM m_routing r
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-00'),
    '20.1.6.6.5.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2016651, 'YD40003380-00B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 0
    AND rs.parallel_group = 2016651
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    0,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-16'),
    '20.1.6.9.1.1', 5, 'DAY',
    1, NULL, NULL,
    1, 2016911, 'YD40003380-16B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 0
    AND rs.parallel_group = 2016911
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-19'),
    '20.1.1.1.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201111, 'YD40003380-19B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201111
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-21'),
    '20.1.2.1.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201211, 'YD40003380-21B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201211
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000034'), (SELECT id FROM m_product WHERE product_code = 'YD40002386-04'),
    '20.1.6.6.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201661, 'YD40003380-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201661
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = '6026280-03'),
    '20.1.6.6.2', 4, 'DAY',
    1, NULL, NULL,
    1, 201662, 'YD40003380-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201662
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000279'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-10'),
    '20.1.6.6.3', 4, 'DAY',
    1, NULL, NULL,
    1, 201663, 'YD40003380-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201663
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000279'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-11'),
    '20.1.6.6.4', 4, 'DAY',
    1, NULL, NULL,
    1, 201664, 'YD40003380-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201664
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-00B'),
    '20.1.6.6.5', 4, 'DAY',
    1, NULL, NULL,
    1, 201665, 'YD40003380-00SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201665
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 1000
     AND rs.parallel_group = 201665),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-00'),
    1.000, 'START', 'Auto from child BOM 61', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND cp.product_code = 'YD40003380-00'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '0801'),
    (SELECT id FROM m_line WHERE line_code = 'L0801'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-01'),
    '20.1.6.7.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201671, 'YD40003380-01B', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201671
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000180'), (SELECT id FROM m_product WHERE product_code = 'YD40006531-02'),
    '20.1.6.8.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201681, 'YD40006531-02S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201681
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000180'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-27'),
    '20.1.6.8.2', 4, 'DAY',
    1, NULL, NULL,
    1, 201682, 'YD40006531-02S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201682
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000044'), (SELECT id FROM m_product WHERE product_code = '4137294'),
    '20.1.6.8.3', 4, 'DAY',
    1, NULL, NULL,
    1, 201683, 'YD40006531-02S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201683
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-16B'),
    '20.1.6.9.1', 4, 'DAY',
    1, NULL, NULL,
    1, 201691, 'YD40003380-16S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201691
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 1000
     AND rs.parallel_group = 201691),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-16'),
    1.000, 'START', 'Auto from child BOM 67', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND cp.product_code = 'YD40003380-16'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    1000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = '14X8X10'),
    '20.1.6.9.2', 4, 'DAY',
    1, NULL, NULL,
    1, 201692, 'YD40003380-16S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 1000
    AND rs.parallel_group = 201692
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-19B'),
    '20.1.1.1', 3, 'DAY',
    1, NULL, NULL,
    1, 20111, 'YD40003380-19S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20111
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20111),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-19'),
    1.000, 'START', 'Auto from child BOM 57', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-19'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = '12X6X8'),
    '20.1.1.2', 3, 'DAY',
    1, NULL, NULL,
    1, 20112, 'YD40003380-19S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20112
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-21B'),
    '20.1.2.1', 3, 'DAY',
    1, NULL, NULL,
    1, 20121, 'YD40003380-21S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20121
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20121),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-21'),
    1.000, 'START', 'Auto from child BOM 59', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-21'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000038'), (SELECT id FROM m_product WHERE product_code = '12X6X8'),
    '20.1.2.2', 3, 'DAY',
    1, NULL, NULL,
    1, 20122, 'YD40003380-21S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20122
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = 'YD00009850'),
    '20.1.6.1', 3, 'DAY',
    1, NULL, NULL,
    1, 20161, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20161
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = 'YD00009851'),
    '20.1.6.2', 3, 'DAY',
    1, NULL, NULL,
    1, 20162, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20162
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = '4684873'),
    '20.1.6.3', 3, 'DAY',
    1, NULL, NULL,
    1, 20163, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20163
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = '4684874'),
    '20.1.6.4', 3, 'DAY',
    1, NULL, NULL,
    1, 20164, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20164
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000387'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-04'),
    '20.1.6.5', 3, 'DAY',
    1, NULL, NULL,
    1, 20165, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20165
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-00SUB'),
    '20.1.6.6', 3, 'MINUTE',
    0, NULL, 15,
    1, 20166, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20166
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20166),
    (SELECT id FROM m_product WHERE product_code = 'YD40002386-04'),
    1.000, 'START', 'Auto from child BOM 60', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40002386-04'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20166),
    (SELECT id FROM m_product WHERE product_code = '6026280-03'),
    1.000, 'START', 'Auto from child BOM 60', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = '6026280-03'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20166),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-10'),
    1.000, 'START', 'Auto from child BOM 60', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-10'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20166),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-11'),
    1.000, 'START', 'Auto from child BOM 60', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-11'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20166),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-00B'),
    1.000, 'START', 'Auto from child BOM 60', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-00B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4010'),
    (SELECT id FROM m_line WHERE line_code = 'L0010'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-01B'),
    '20.1.6.7', 3, 'DAY',
    1, NULL, NULL,
    1, 20167, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20167
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20167),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-01'),
    1.000, 'START', 'Auto from child BOM 62', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-01'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4021'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40006531-02S'),
    '20.1.6.8', 3, 'MINUTE',
    0, NULL, 15,
    1, 20168, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20168
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20168),
    (SELECT id FROM m_product WHERE product_code = '4137294'),
    1.000, 'START', 'Auto from child BOM 64', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = '4137294'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20168),
    (SELECT id FROM m_product WHERE product_code = 'YD40006531-02'),
    1.000, 'START', 'Auto from child BOM 64', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40006531-02'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20168),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-27'),
    1.000, 'START', 'Auto from child BOM 64', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-27'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    2000,
    (SELECT id FROM m_process WHERE process_code = '4013'),
    (SELECT id FROM m_line WHERE line_code = 'L0013'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-16S'),
    '20.1.6.9', 3, 'DAY',
    1, NULL, NULL,
    1, 20169, 'YD40006531H', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND rs.parallel_group = 20169
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20169),
    (SELECT id FROM m_product WHERE product_code = '14X8X10'),
    1.000, 'START', 'Auto from child BOM 65', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = '14X8X10'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 2000
     AND rs.parallel_group = 20169),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-16B'),
    1.000, 'START', 'Auto from child BOM 65', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 2000
    AND cp.product_code = 'YD40003380-16B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000387'), (SELECT id FROM m_product WHERE product_code = 'YD40003052-00'),
    '19.1.1', 2, 'DAY',
    1, NULL, NULL,
    1, 1911, 'YD40003052SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 1911
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000034'), (SELECT id FROM m_product WHERE product_code = '8113793-01'),
    '19.1.2', 2, 'DAY',
    1, NULL, NULL,
    1, 1912, 'YD40003052SUB', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 1912
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4013'),
    (SELECT id FROM m_line WHERE line_code = 'L0013'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-19S'),
    '20.1.1', 2, 'DAY',
    1, NULL, NULL,
    1, 2011, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2011
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2011),
    (SELECT id FROM m_product WHERE product_code = '12X6X8'),
    1.000, 'START', 'Auto from child BOM 56', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = '12X6X8'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2011),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-19B'),
    1.000, 'START', 'Auto from child BOM 56', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-19B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4013'),
    (SELECT id FROM m_line WHERE line_code = 'L0013'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-21S'),
    '20.1.2', 2, 'DAY',
    1, NULL, NULL,
    1, 2012, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2012
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2012),
    (SELECT id FROM m_product WHERE product_code = '12X6X8'),
    1.000, 'START', 'Auto from child BOM 58', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = '12X6X8'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2012),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-21B'),
    1.000, 'START', 'Auto from child BOM 58', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-21B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000180'), (SELECT id FROM m_product WHERE product_code = 'YD40003380-24'),
    '20.1.3', 2, 'DAY',
    1, NULL, NULL,
    1, 2013, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2013
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000651'), (SELECT id FROM m_product WHERE product_code = '6026280-141516'),
    '20.1.4', 2, 'DAY',
    1, NULL, NULL,
    1, 2014, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2014
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000132'), (SELECT id FROM m_product WHERE product_code = '4338830'),
    '20.1.5', 2, 'DAY',
    1, NULL, NULL,
    1, 2015, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2015
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    3000,
    (SELECT id FROM m_process WHERE process_code = '4019'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40006531H'),
    '20.1.6', 2, 'MINUTE',
    0, NULL, 15,
    1, 2016, 'YD40006531', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND rs.parallel_group = 2016
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = '4684873'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = '4684873'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = '4684874'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = '4684874'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-00SUB'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-00SUB'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD40006531-02S'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40006531-02S'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-04'),
    2.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-04'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-16S'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-16S'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD00009850'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD00009850'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD00009851'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD00009851'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 3000
     AND rs.parallel_group = 2016),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-01B'),
    1.000, 'START', 'Auto from child BOM 63', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 3000
    AND cp.product_code = 'YD40003380-01B'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    4000,
    (SELECT id FROM m_process WHERE process_code = '4221'),
    (SELECT id FROM m_line WHERE line_code = 'L2201'), (SELECT id FROM m_product WHERE product_code = 'YD40003052SUB'),
    '19.1', 1, 'DAY',
    7, NULL, NULL,
    1, 191, 'YD40003052', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND rs.parallel_group = 191
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 191),
    (SELECT id FROM m_product WHERE product_code = 'YD40003052-00'),
    1.000, 'START', 'Auto from child BOM 35', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40003052-00'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 191),
    (SELECT id FROM m_product WHERE product_code = '8113793-01'),
    1.000, 'START', 'Auto from child BOM 35', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = '8113793-01'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    4000,
    (SELECT id FROM m_process WHERE process_code = '4053'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40006531'),
    '20.1', 1, 'MINUTE',
    0, NULL, 15,
    1, 201, 'YD40006531S', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND rs.parallel_group = 201
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = '6026280-141516'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = '6026280-141516'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = '4338830'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = '4338830'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-19S'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40003380-19S'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-21S'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40003380-21S'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = 'YD40003380-24'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40003380-24'
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 4000
     AND rs.parallel_group = 201),
    (SELECT id FROM m_product WHERE product_code = 'YD40006531H'),
    1.000, 'START', 'Auto from child BOM 55', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 4000
    AND cp.product_code = 'YD40006531H'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002165'),
    '1', 0, 'DAY',
    1, NULL, NULL,
    1, 1, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 1
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002175'),
    '2', 0, 'DAY',
    1, NULL, NULL,
    1, 2, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 2
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980002449'),
    '3', 0, 'DAY',
    1, NULL, NULL,
    1, 3, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 3
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000654'), (SELECT id FROM m_product WHERE product_code = '89980004023'),
    '4', 0, 'DAY',
    1, NULL, NULL,
    1, 4, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 4
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000651'), (SELECT id FROM m_product WHERE product_code = 'H4667127990'),
    '5', 0, 'DAY',
    1, NULL, NULL,
    1, 5, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 5
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA810070990'),
    '6', 0, 'DAY',
    1, NULL, NULL,
    1, 6, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 6
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA810110990'),
    '7', 0, 'DAY',
    1, NULL, NULL,
    1, 7, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 7
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = '000030'), (SELECT id FROM m_product WHERE product_code = 'HA885002'),
    '8', 0, 'DAY',
    1, NULL, NULL,
    1, 8, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 8
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'HA885008'),
    '9', 0, 'DAY',
    1, NULL, NULL,
    1, 9, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 9
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'HJ260814990'),
    '10', 0, 'DAY',
    1, NULL, NULL,
    1, 10, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 10
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'HJ260816990'),
    '11', 0, 'DAY',
    1, NULL, NULL,
    1, 11, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 11
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'HJ260820990'),
    '12', 0, 'DAY',
    1, NULL, NULL,
    1, 12, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 12
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4239713'),
    '13', 0, 'DAY',
    1, NULL, NULL,
    1, 13, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 13
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4442446'),
    '14', 0, 'DAY',
    1, NULL, NULL,
    1, 14, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 14
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = '4479355'),
    '15', 0, 'DAY',
    1, NULL, NULL,
    1, 15, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 15
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'A852132'),
    '16', 0, 'DAY',
    1, NULL, NULL,
    1, 16, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 16
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'A852133'),
    '17', 0, 'DAY',
    1, NULL, NULL,
    1, 17, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 17
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'PURCHASE'),
    (SELECT id FROM m_line WHERE line_code = 'G00001'), (SELECT id FROM m_product WHERE product_code = 'A852432'),
    '18', 0, 'DAY',
    1, NULL, NULL,
    1, 18, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 18
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = 'G'),
    (SELECT id FROM m_line WHERE line_code = 'GAISAKU'), (SELECT id FROM m_product WHERE product_code = 'YD40003052'),
    '19', 0, 'DAY',
    1, NULL, NULL,
    1, 19, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 19
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 5000
     AND rs.parallel_group = 19),
    (SELECT id FROM m_product WHERE product_code = 'YD40003052SUB'),
    1.000, 'START', 'Auto from child BOM 34', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND cp.product_code = 'YD40003052SUB'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5000,
    (SELECT id FROM m_process WHERE process_code = '4030'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD40006531S'),
    '20', 0, 'MINUTE',
    0, NULL, 15,
    1, 20, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND rs.parallel_group = 20
);

INSERT INTO m_routing_step_material (routing_step_id, component_id, quantity, consume_timing, remark, created_at, updated_at)
SELECT
    (SELECT rs.id FROM m_routing_step rs
     JOIN m_routing r ON rs.routing_id = r.id
     JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305'
     AND r.routing_code = 'YD60011305'
     AND rs.step_no = 5000
     AND rs.parallel_group = 20),
    (SELECT id FROM m_product WHERE product_code = 'YD40006531'),
    1.000, 'START', 'Auto from child BOM 54', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step_material rsm
    JOIN m_routing_step rs ON rsm.routing_step_id = rs.id
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    JOIN m_product cp ON rsm.component_id = cp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5000
    AND cp.product_code = 'YD40006531'
);

INSERT INTO m_routing_step (routing_id, step_no, process_id, line_id, output_product_id, hierarchy_path, hierarchy_depth, time_unit, lead_time_days, start_offset_min, duration_min, parallel_count, parallel_group, remark, created_at, updated_at)
SELECT
    (SELECT r.id FROM m_routing r JOIN m_product pp ON r.product_id = pp.id
     WHERE pp.product_code = 'YD60011305' AND r.routing_code = 'YD60011305'),
    5001,
    (SELECT id FROM m_process WHERE process_code = '4007'),
    (SELECT id FROM m_line WHERE line_code = 'L2200'), (SELECT id FROM m_product WHERE product_code = 'YD60011305'),
    'final', 0, 'MINUTE',
    0, NULL, 15,
    1, 1, 'YD60011305', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM m_routing_step rs
    JOIN m_routing r ON rs.routing_id = r.id
    JOIN m_product pp ON r.product_id = pp.id
    WHERE pp.product_code = 'YD60011305'
    AND r.routing_code = 'YD60011305'
    AND rs.step_no = 5001
    AND rs.parallel_group = 1
);

-- ========================================
-- Process cycle time import
-- ========================================
