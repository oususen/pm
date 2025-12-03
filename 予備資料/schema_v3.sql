-- schema_v3.sql  (v3.1: category ENUM / t_schedule_detail 追加)

-- 既存schema_v2.sqlに対する差分のみ記載（適用順に注意）

-- 1) m_product.category を ENUM 化
ALTER TABLE m_product
  MODIFY COLUMN category ENUM('ASSEMBLY','SINGLE','MATERIAL','PURCHASED') NOT NULL;

-- 2) スケジューリング中間テーブル（逆算・順算の結果書き出し用）
CREATE TABLE t_schedule_detail (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,                 -- 受注（別テーブル想定）
  routing_step_id BIGINT NOT NULL,          -- どのステップか
  planned_start DATETIME NOT NULL,
  planned_end DATETIME NOT NULL,
  batch_no INT NOT NULL DEFAULT 1,          -- バッチ連番（移送単位）
  quantity INT NOT NULL,
  status ENUM('WAITING','RUNNING','COMPLETED') NOT NULL DEFAULT 'WAITING',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_sched_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id)
) ENGINE=InnoDB;

-- 3) 参考：DAY工程の“日内位置”の運用ルール
--  スキーマ追加は不要。スケジューラ側で以下の方針を採用：
--    - DAY工程は「その日の作業終了時刻(planned_end=営業日末)に完了したものとして扱う」
--    - 複数DAY工程が同日に収まる場合は step_no 順で“並べる”（開始=前ステップ完了の直後）
--    - MINUTE工程と混在する場合は、MINUTE工程の end に DAY工程の start をスナップさせる
