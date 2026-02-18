-- ============================================================
-- YD60010942（タンク；オイル）BOM 本番導入SQL
-- Generated: 2026-02-18
-- 対象BOM: 6階層、15BOM、全関連製品・BOM明細含む
-- 実行方法: mysql -u root -p pm_db < bom_YD60010942_prod.sql
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ========================================
-- 1. 製品マスタ（NOT EXISTSで安全にスキップ）
-- ========================================

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '14X8X10', 'ｳｪﾙﾄﾞﾅｯﾄ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '14X8X10');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '3093554', 'ﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '3093554');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '3094857', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '3094857');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4137294', 'M10XP1.5 ｱｼﾅｼNUT', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4137294');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4198414', 'ｿｹｯﾄ;M', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4198414');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4222008', 'M10XP1.5 ﾄｸNUT', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4222008');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4250261', 'ｶﾞｽｹｯﾄ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4250261');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4257926', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4257926');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4364696', 'ﾌﾟﾗｸﾞ ﾕｳｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4364696');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4434017', 'ﾌﾞﾘｰｻﾞ;ｴｱ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4434017');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4443596', 'ｴﾚﾒﾝﾄﾌｨﾙﾀ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4443596');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4443782', 'ｶﾊﾞｰ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4443782');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4444193', 'ｶﾊﾞｰ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4444193');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4444482', 'ｽﾌﾟﾘﾝｸﾞ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4444482');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4477456', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4477456');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4609532', 'ﾅｯﾄ;ｳｪﾙﾄﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4609532');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '4670343', 'ﾌｨﾙﾀ;ｻｸｼｮﾝ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '4670343');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-04', 'ﾌﾟﾚｰﾄ（小）', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '6027849-04');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-05', 'ﾌﾟﾚｰﾄ（大)', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '6027849-05');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '6027849-11', 'ﾌﾟﾚｰﾄ T-75-5', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '6027849-11');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7043112-03', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7043112-03');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7043112-03B', 'ﾌﾞﾗｹｯﾄＢ', 'SINGLE', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7043112-03B');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749', 'ｹｰｽ;ﾌｨﾙﾀ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7052749');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-01', 'ﾊﾟｲﾌﾟ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7052749-01');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-04', '◆外作◆(ﾀﾝｸ）Φ42.7Ｘ3.5Ｘ118', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7052749-04');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '7052749-06', '◆外作◆（ﾀﾝｸ)Φ34Ｘ3.2Ｘ315曲', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '7052749-06');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8049310', 'ﾌﾗﾝｼﾞ', 'ASSEMBLY', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '8049310');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8049310-00', 'ﾌﾗﾝｼﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '8049310-00');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197', 'ﾊﾟｲﾌﾟ;ｻｸｼｮﾝ', 'ASSEMBLY', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '8109197');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197-00', 'ﾊﾟｲﾌﾟ U-00', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '8109197-00');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '8109197-01', 'ﾊﾟｲﾌﾟ U-01', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '8109197-01');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002169', 'ﾌﾟﾗｸﾞ中 SR1013-12677', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980002169');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002170', 'ﾌﾟﾗｸﾞ大SR1013-12681', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980002170');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002175', 'ｷｬｯﾌﾟSCM34.0X38.0', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980002175');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980002179', 'ｷｬｯﾌﾟSCM2.250X1-1/2IL', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980002179');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003298', 'ﾌﾟﾗｸﾞ小SR1013-12672', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980003298');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003299', 'ｷｬｯﾌﾟSC1.000X1IL', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980003299');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '89980003306', 'ｷｬｯﾌﾟSCM43.0X38.0L', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '89980003306');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9.0X19.0X160.0', 'FB19X9X160', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9.0X19.0X160.0');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9210864', 'ｶﾊﾞｰ ■ﾑｼｮｳｼｷｭｳ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9210864');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9761676', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9761676');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9761676-00', 'ﾌﾞﾗｹｯﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9761676-00');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9764308', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9764308');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT '9765592', 'ﾌﾞﾗｹｯﾄ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = '9765592');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810060', 'Oﾘﾝｸﾞ 1AG060', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'HA810060');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA810160', 'Oﾘﾝｸﾞ 1AG160', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'HA810160');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HA885004', 'ﾌﾟﾗｸﾞ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'HA885004');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HC9.0X19.0X645.0', 'ﾎｷｮｳﾌﾟﾚｰﾄ_6027849-07', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'HC9.0X19.0X645.0');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'HZ997330', 'Oﾘﾝｸﾞ 1AP140', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'HZ997330');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'J271025', 'ﾛｯｶｸﾎﾞﾙﾄ(ﾜｯｼｬｰ)', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'J271025');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'J780616', 'ﾎﾞﾙﾄ;ｿｹｯﾄ M6X16', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'J780616');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'M10X16', 'ﾛｯｶｸﾎﾞﾙﾄ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'M10X16');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD00011669', 'ｿｹｯﾄ;M', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD00011669');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40000999-10', 'ﾌﾟﾚｰﾄ T-75-5', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40000999-10');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001', 'ｼｰﾄ;ｽｸﾘｭ', 'ASSEMBLY', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001-00', 'ｼｰﾄ;ｽｸﾘｭ', 'SINGLE', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001-00');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40001001-00B', 'ｼｰﾄ;ｽｸﾘｭ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40001001-00B');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997', 'ﾀﾝｸ;ｵｲﾙ ｾｲｶﾝ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-00', 'ｵｲﾙﾀﾝｸ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-00');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-00B', 'タンク00B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-00B');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-00SUB', 'ﾀﾝｸ;ｵｲﾙ ｻﾌﾞｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-00SUB');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-01', 'ｵｲﾙﾀﾝｸ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-01');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-01B', 'タンク01B', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-01B');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-01SUB', 'ﾀﾝｸ;ｵｲﾙ ｻﾌﾞｺﾝﾌﾟ', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-01SUB');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-21', 'ﾌﾟﾚｰﾄ', 'SINGLE', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-21');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997-22B', 'ﾌﾟﾚｰﾄB', 'SINGLE', '個', 1, 0, 0, 0, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997-22B');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997H', 'タンク　箱組後', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997H');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD40005997S', 'ﾀﾝｸ;ｵｲﾙ 水没', 'ASSEMBLY', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD40005997S');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'YD60010942', 'タンク；オイル', 'ASSEMBLY', '個', 1, 0, 0, 1, 1, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'YD60010942');

INSERT INTO m_product (product_code, product_name, category, unit, is_active, is_phantom, is_virtual_set, is_final_product, is_line_final_product, created_at, updated_at)
SELECT 'Z449558', 'ｼｰﾙﾜｯｼｬ', 'PURCHASED', '個', 1, 0, 0, 0, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM m_product p WHERE p.product_code = 'Z449558');

-- ========================================
-- 2. BOMヘッダ（NOT EXISTSで安全にスキップ）
-- ========================================

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = '7043112-03B'), 'v1', '2026-02-04', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = '7043112-03B' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = '7052749'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = '7052749' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = '8049310'), 'v1', '2025-12-09', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = '8049310' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = '8109197'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = '8109197' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = '9761676'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = '9761676' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40001001'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40001001' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40001001-00B'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40001001-00B' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997-00B'), 'v1', '2026-02-13', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997-00B' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997-00SUB'), 'v1', '2026-02-13', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997-00SUB' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997-01B'), 'v1', '2026-02-13', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997-01B' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997-01SUB'), 'v1', '2026-02-13', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997-01SUB' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997H'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997H' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD40005997S'), 'v1', '2026-02-13', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD40005997S' AND b2.version = 'v1');

INSERT INTO m_bom (parent_product_id, version, valid_from, valid_to, is_active, is_coproduct, created_at, updated_at)
SELECT (SELECT id FROM m_product WHERE product_code = 'YD60010942'), 'v1', '2026-02-11', NULL, 1, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom b2 JOIN m_product p2 ON p2.id = b2.parent_product_id
  WHERE p2.product_code = 'YD60010942' AND b2.version = 'v1');

-- ========================================
-- 3. BOM明細（NOT EXISTSで安全にスキップ）
-- ========================================

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7043112-03B' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7043112-03'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7043112-03B' AND cp3.product_code = '7043112-03' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '3093554'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '010017'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '3093554' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4444193'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000072'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '4444193' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7043112-03B'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4010'), (SELECT id FROM m_line WHERE line_code = 'L0010'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '7043112-03B' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7052749-01'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000095'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '7052749-01' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7052749-04'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000034'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '7052749-04' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '7052749' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7052749-06'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000034'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '7052749' AND cp3.product_code = '7052749-06' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '8049310' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '14X8X10'),
  6.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000038'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '8049310' AND cp3.product_code = '14X8X10' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '8049310' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '8049310-00'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000072'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '8049310' AND cp3.product_code = '8049310-00' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '8109197' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '8109197-00'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '8109197' AND cp3.product_code = '8109197-00' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '8109197' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '8109197-01'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '8109197' AND cp3.product_code = '8109197-01' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '9761676' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4609532'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000044'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '9761676' AND cp3.product_code = '4609532' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = '9761676' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9761676-00'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000061'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = '9761676' AND cp3.product_code = '9761676-00' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40001001' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4222008'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000044'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40001001' AND cp3.product_code = '4222008' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40001001' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40001001-00B'),
  1.000, NULL, 'SUBCON', (SELECT id FROM m_process WHERE process_code = 'G'), (SELECT id FROM m_line WHERE line_code = 'GAISAKU'), (SELECT id FROM m_supplier WHERE supplier_code = '000061'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40001001' AND cp3.product_code = 'YD40001001-00B' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40001001-00B' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40001001-00'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40001001-00B' AND cp3.product_code = 'YD40001001-00' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '8049310'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4013'), (SELECT id FROM m_line WHERE line_code = 'L0013'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = '8049310' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9761676'),
  2.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4221'), (SELECT id FROM m_line WHERE line_code = 'L2201'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = '9761676' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9764308'),
  2.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000180'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = '9764308' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9765592'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000180'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = '9765592' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD00011669'),
  2.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = 'YD00011669' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40001001'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4221'), (SELECT id FROM m_line WHERE line_code = 'L2201'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = 'YD40001001' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997H'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4019'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 20, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997' AND cp3.product_code = 'YD40005997H' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-00B' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-00'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-00B' AND cp3.product_code = 'YD40005997-00' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-00SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000048'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-00SUB' AND cp3.product_code = 'HC9.0X19.0X645.0' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-00SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-00B'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4021'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 15, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-00SUB' AND cp3.product_code = 'YD40005997-00B' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-01B' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-01'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-01B' AND cp3.product_code = 'YD40005997-01' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-01SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4137294'),
  2.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000044'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-01SUB' AND cp3.product_code = '4137294' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-01SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9.0X19.0X160.0'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-01SUB' AND cp3.product_code = '9.0X19.0X160.0' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-01SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HC9.0X19.0X645.0'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000048'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-01SUB' AND cp3.product_code = 'HC9.0X19.0X645.0' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997-01SUB' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-01B'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4021'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 15, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997-01SUB' AND cp3.product_code = 'YD40005997-01B' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '3094857'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '3094857' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4198414'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '010017'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '4198414' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4257926'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '4257926' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4477456'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '010017'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '4477456' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '6027849-04'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000352'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '6027849-04' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '6027849-05'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000352'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '6027849-05' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '6027849-11'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000387'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '6027849-11' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '7052749'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4021'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 15, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '7052749' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '8109197'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4221'), (SELECT id FROM m_line WHERE line_code = 'L2201'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '8109197' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9761676'),
  2.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4221'), (SELECT id FROM m_line WHERE line_code = 'L2201'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = '9761676' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD00011669'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000132'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD00011669' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40000999-10'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000387'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD40000999-10' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-00SUB'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4021'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 15, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD40005997-00SUB' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-01SUB'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4021'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 15, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD40005997-01SUB' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-21'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '0801'), (SELECT id FROM m_line WHERE line_code = 'L0801'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD40005997-21' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997H' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997-22B'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4010'), (SELECT id FROM m_line WHERE line_code = 'L0010'), NULL, 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997H' AND cp3.product_code = 'YD40005997-22B' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD40005997S' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4053'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 20, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD40005997S' AND cp3.product_code = 'YD40005997' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4250261'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4250261' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4364696'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4364696' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4434017'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4434017' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4443596'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4443596' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4443782'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4443782' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4444482'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4444482' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '4670343'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '4670343' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980002169'),
  6.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980002169' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980002170'),
  4.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980002170' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980002175'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980002175' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980002179'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980002179' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980003298'),
  3.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980003298' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980003299'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980003299' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '89980003306'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000654'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '89980003306' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = '9210864'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = 'G00001'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = '9210864' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HA810060'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'HA810060' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HA810160'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'HA810160' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HA885004'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'HA885004' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'HZ997330'),
  1.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'HZ997330' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'J271025'),
  12.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'J271025' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'J780616'),
  4.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000038'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'J780616' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'M10X16'),
  2.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000038'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'M10X16' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'YD40005997S'),
  1.000, NULL, 'MAKE', (SELECT id FROM m_process WHERE process_code = '4030'), (SELECT id FROM m_line WHERE line_code = 'L2200'), NULL, 'MINUTE', 0, 20, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'YD40005997S' AND b3.version = 'v1');

INSERT INTO m_bom_item (bom_id, child_product_id, quantity, loss_rate, sourcing_type, process_id, line_id, supplier_id, time_unit, lead_time_days, duration_min, is_coproduct_driver, created_at, updated_at)
SELECT
  (SELECT b2.id FROM m_bom b2 JOIN m_product pp2 ON pp2.id = b2.parent_product_id WHERE pp2.product_code = 'YD60010942' AND b2.version = 'v1'),
  (SELECT id FROM m_product WHERE product_code = 'Z449558'),
  2.000, NULL, 'BUY', NULL, NULL, (SELECT id FROM m_supplier WHERE supplier_code = '000030'), 'DAY', 1, NULL, 0, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM m_bom_item bi2
  JOIN m_bom b3 ON b3.id = bi2.bom_id
  JOIN m_product pp3 ON pp3.id = b3.parent_product_id
  JOIN m_product cp3 ON cp3.id = bi2.child_product_id
  WHERE pp3.product_code = 'YD60010942' AND cp3.product_code = 'Z449558' AND b3.version = 'v1');

SET FOREIGN_KEY_CHECKS = 1;

-- 完了