-- V053904703 BOM明細の工程/ライン補正 (ID直指定)
START TRANSACTION;
SET collation_connection='utf8mb4_unicode_ci';
SET @V:='v_auto_20260313_1';
SET @D:=CURDATE();

-- 2層目: 親 V053904703 -> L0013(id=10) / 4013(id=12)
UPDATE m_bom_item bi
JOIN m_bom b ON bi.bom_id=b.id
JOIN m_product pp ON b.parent_product_id=pp.id
SET bi.line_id = 10, bi.process_id = 12, bi.updated_at = NOW()
WHERE b.version=@V AND b.valid_from=@D AND pp.product_code='V053904703';

-- 3層目: 親 V053104701-02S -> L0010(id=9) / 4040(id=20)
UPDATE m_bom_item bi
JOIN m_bom b ON bi.bom_id=b.id
JOIN m_product pp ON b.parent_product_id=pp.id
SET bi.line_id = 9, bi.process_id = 20, bi.updated_at = NOW()
WHERE b.version=@V AND b.valid_from=@D AND pp.product_code='V053104701-02S';

-- 4層目: 親 V053104701-02B -> L0801(id=8) / 0801(id=10)
UPDATE m_bom_item bi
JOIN m_bom b ON bi.bom_id=b.id
JOIN m_product pp ON b.parent_product_id=pp.id
SET bi.line_id = 8, bi.process_id = 10, bi.updated_at = NOW()
WHERE b.version=@V AND b.valid_from=@D AND pp.product_code='V053104701-02B';

COMMIT;