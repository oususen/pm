# 9月17日の共通連絡の復元

本番の `orders.0068` / `0069` 適用後、対象の共通連絡が存在しない場合に実行するSQL。開発DBの原文を確認済み。本番では未実行。

```sql
-- 本番反映後、orders.0068 / 0069 の適用後に使用する。
-- 開発DBの内示明細 id=6814 で確認した原文を復元する。
-- 同じキーの共通メモが存在する場合は、空文字も含めて上書きしない。
-- 対象: 2026-09-17 / V053504641 / ZGHC
SET NAMES utf8mb4;

INSERT INTO t_kubota_sakai_due_shared_note
    (product_code, ship_to_code, due_date, coordination_note)
SELECT 'V053504641', 'ZGHC', '2026-09-17', '検査行き　３台含む'
WHERE NOT EXISTS (
    SELECT 1 FROM t_kubota_sakai_due_shared_note
    WHERE product_code = 'V053504641'
      AND ship_to_code = 'ZGHC'
      AND due_date = '2026-09-17'
);

SELECT product_code, ship_to_code, due_date, coordination_note
FROM t_kubota_sakai_due_shared_note
WHERE product_code = 'V053504641'
  AND ship_to_code = 'ZGHC'
  AND due_date = '2026-09-17';
```
