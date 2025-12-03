-- schema.sql  段階BOM＋セル工程・時間運用＋ライン/購買LT (v3統合版)

-- 文字セット設定
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 1) Products
CREATE TABLE m_product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_code VARCHAR(30) NOT NULL UNIQUE,
  product_name VARCHAR(100) NOT NULL,
  category ENUM('ASSEMBLY','SINGLE','MATERIAL','PURCHASED') NOT NULL,
  unit VARCHAR(10) NOT NULL DEFAULT '個',
  standard_lt_days INT NULL,
  self_lt_days INT NULL,
  is_final_product TINYINT(1) NOT NULL DEFAULT 0,
  is_phantom TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2) Customer
CREATE TABLE m_customer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_code VARCHAR(20) NOT NULL UNIQUE,
  customer_name VARCHAR(100) NOT NULL,
  short_name VARCHAR(40) NULL,
  calendar_id BIGINT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3) Process / Line
CREATE TABLE m_process (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  process_code VARCHAR(20) NOT NULL UNIQUE,
  process_name VARCHAR(50) NOT NULL,
  is_outsource TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE m_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  line_code VARCHAR(20) NOT NULL UNIQUE,
  line_name VARCHAR(50) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Optional defaults for line LT
CREATE TABLE m_line_default (
  line_id BIGINT PRIMARY KEY,
  default_lt_days INT NOT NULL,
  CONSTRAINT fk_line_default_line FOREIGN KEY (line_id) REFERENCES m_line(id)
) ENGINE=InnoDB;

CREATE TABLE m_line_product_lt (
  line_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  lt_days INT NOT NULL,
  PRIMARY KEY (line_id, product_id),
  CONSTRAINT fk_line_prod_lt_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_line_prod_lt_prod FOREIGN KEY (product_id) REFERENCES m_product(id)
) ENGINE=InnoDB;

-- 4) Routing
CREATE TABLE m_routing (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_id BIGINT NOT NULL,
  routing_code VARCHAR(30) NOT NULL,
  description TEXT NULL,
  is_default TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_routing_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_routing (product_id, routing_code)
) ENGINE=InnoDB;

CREATE TABLE m_routing_step (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  routing_id BIGINT NOT NULL,
  step_no INT NOT NULL,
  process_id BIGINT NOT NULL,
  line_id BIGINT NULL,
  time_unit ENUM('DAY','MINUTE') NOT NULL DEFAULT 'DAY',
  lead_time_days INT NOT NULL DEFAULT 0,
  start_offset_min INT NULL,
  duration_min INT NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_rstep_routing FOREIGN KEY (routing_id) REFERENCES m_routing(id),
  CONSTRAINT fk_rstep_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_rstep_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  UNIQUE KEY uk_rstep (routing_id, step_no)
) ENGINE=InnoDB;

CREATE TABLE m_routing_step_output (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  routing_step_id BIGINT NOT NULL,
  output_product_id BIGINT NOT NULL,
  yield_rate DECIMAL(5,3) NULL,
  is_final_stage TINYINT(1) NOT NULL DEFAULT 0,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_rstepout_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  CONSTRAINT fk_rstepout_product FOREIGN KEY (output_product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_rstepout (routing_step_id, output_product_id)
) ENGINE=InnoDB;

CREATE TABLE m_routing_step_param (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  routing_step_id BIGINT NOT NULL,
  lot_size INT NULL,
  transfer_batch_qty INT NULL,
  start_trigger ENUM('on_first_unit','on_transfer_batch','on_complete') NOT NULL DEFAULT 'on_transfer_batch',
  target_buffer_qty INT NULL,
  max_buffer_qty INT NULL,
  daily_time_window_min INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_rstepparam_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  UNIQUE KEY uk_rstepparam (routing_step_id)
) ENGINE=InnoDB;

-- 5) Capacity (Cycle time)
CREATE TABLE m_cycle_time (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_id BIGINT NOT NULL,
  process_id BIGINT NOT NULL,
  line_id BIGINT NOT NULL,
  cycle_time_sec DECIMAL(10,2) NOT NULL,
  setup_time_min DECIMAL(10,2) NOT NULL DEFAULT 0,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_ct_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_ct_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_ct_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  UNIQUE KEY uk_ct (product_id, process_id, line_id, valid_from)
) ENGINE=InnoDB;

-- 6) BOM
CREATE TABLE m_bom (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_product_id BIGINT NOT NULL,
  version VARCHAR(20) NOT NULL DEFAULT 'v1',
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_bom_parent FOREIGN KEY (parent_product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_bom (parent_product_id, version, valid_from)
) ENGINE=InnoDB;

CREATE TABLE m_bom_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  bom_id BIGINT NOT NULL,
  child_product_id BIGINT NOT NULL,
  quantity DECIMAL(12,3) NOT NULL,
  loss_rate DECIMAL(5,3) NULL,
  sourcing_type ENUM('MAKE','BUY','SUBCON') NOT NULL DEFAULT 'MAKE',
  supplier_id BIGINT NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_bi_bom FOREIGN KEY (bom_id) REFERENCES m_bom(id),
  CONSTRAINT fk_bi_child FOREIGN KEY (child_product_id) REFERENCES m_product(id),
  CONSTRAINT chk_bi_sourcing CHECK (
    (sourcing_type = 'MAKE' AND supplier_id IS NULL) OR
    (sourcing_type IN ('BUY', 'SUBCON') AND supplier_id IS NOT NULL)
  )
) ENGINE=InnoDB;

-- 7) Suppliers / purchasing LT
CREATE TABLE m_supplier (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  supplier_code VARCHAR(20) NOT NULL UNIQUE,
  supplier_name VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE m_supplier_item (
  supplier_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  purchase_lt_days INT NOT NULL,
  min_lot INT NULL,
  order_cycle_days INT NULL,
  PRIMARY KEY (supplier_id, product_id),
  CONSTRAINT fk_si_supplier FOREIGN KEY (supplier_id) REFERENCES m_supplier(id),
  CONSTRAINT fk_si_product FOREIGN KEY (product_id) REFERENCES m_product(id)
) ENGINE=InnoDB;

ALTER TABLE m_bom_item
  ADD CONSTRAINT fk_bi_supplier FOREIGN KEY (supplier_id) REFERENCES m_supplier(id);

-- 8) Calendar
CREATE TABLE m_calendar (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  calendar_code VARCHAR(20) NOT NULL UNIQUE,
  calendar_name VARCHAR(50) NOT NULL,
  description TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE m_calendar_day (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  calendar_id BIGINT NOT NULL,
  target_date DATE NOT NULL,
  is_working_day TINYINT(1) NOT NULL,
  work_minutes INT NULL,
  note VARCHAR(100) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_cday_calendar FOREIGN KEY (calendar_id) REFERENCES m_calendar(id),
  UNIQUE KEY uk_cday (calendar_id, target_date)
) ENGINE=InnoDB;

-- Add FK constraint for m_customer.calendar_id
ALTER TABLE m_customer
  ADD CONSTRAINT fk_customer_calendar FOREIGN KEY (calendar_id) REFERENCES m_calendar(id);

-- 9) Orders (header / line) + staging for intake
CREATE TABLE t_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  order_no VARCHAR(50) NOT NULL,
  order_type ENUM('FIRM','FORECAST') NOT NULL,
  version_no VARCHAR(20) NOT NULL DEFAULT 'v1',
  source_system VARCHAR(50) NULL,
  source_file VARCHAR(200) NULL,
  order_date DATE NULL,
  freeze_from DATE NULL,
  status ENUM('OPEN','CLOSED','CANCELED') NOT NULL DEFAULT 'OPEN',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES m_customer(id),
  UNIQUE KEY uk_order (customer_id, order_no, order_type, version_no),
  INDEX idx_order_status (status)
) ENGINE=InnoDB;

CREATE TABLE t_order_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  product_id BIGINT NULL,
  product_code VARCHAR(50) NOT NULL,
  quantity DECIMAL(14,3) NOT NULL,
  due_date DATE NOT NULL,
  plant_code VARCHAR(20) NULL,
  ship_to_code VARCHAR(40) NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_orderline_order FOREIGN KEY (order_id) REFERENCES t_order(id),
  CONSTRAINT fk_orderline_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_orderline (order_id, line_no),
  INDEX idx_orderline_due (due_date),
  INDEX idx_orderline_product (product_code)
) ENGINE=InnoDB;

-- Staging: raw rows per file and normalized daily demand
CREATE TABLE stg_order_raw (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_code VARCHAR(20) NOT NULL,
  order_type ENUM('FIRM','FORECAST') NOT NULL,
  source_system VARCHAR(50) NULL,
  source_file VARCHAR(200) NULL,
  source_row_no INT NOT NULL,
  record_token VARCHAR(50) NULL,           -- e.g., V1/V2, 送付Noなど
  start_month DATE NULL,                   -- forecast開始月度
  due_date DATE NULL,                      -- 確定系は納期
  product_code VARCHAR(50) NULL,
  quantity DECIMAL(14,3) NULL,
  raw_payload JSON NOT NULL,
  parse_status ENUM('PENDING','PARSED','ERROR') NOT NULL DEFAULT 'PENDING',
  error_message VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_stg_raw_customer (customer_code),
  INDEX idx_stg_raw_status (parse_status)
) ENGINE=InnoDB;

CREATE TABLE stg_order_daily (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  raw_id BIGINT NOT NULL,
  customer_id BIGINT NULL,
  order_type ENUM('FIRM','FORECAST') NOT NULL,
  version_no VARCHAR(20) NOT NULL DEFAULT 'v1',
  product_code VARCHAR(50) NOT NULL,
  due_date DATE NOT NULL,
  quantity DECIMAL(14,3) NOT NULL,
  plant_code VARCHAR(20) NULL,
  ship_to_code VARCHAR(40) NULL,
  source_system VARCHAR(50) NULL,
  source_file VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_stg_daily_raw FOREIGN KEY (raw_id) REFERENCES stg_order_raw(id),
  CONSTRAINT fk_stg_daily_customer FOREIGN KEY (customer_id) REFERENCES m_customer(id),
  INDEX idx_stg_daily_due (due_date),
  INDEX idx_stg_daily_customer (customer_id, due_date)
) ENGINE=InnoDB;

-- 10) Scheduling result (transactional)
CREATE TABLE t_schedule_detail (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,                 -- t_order.id
  routing_step_id BIGINT NOT NULL,          -- どのステップか
  planned_start DATETIME NOT NULL,
  planned_end DATETIME NOT NULL,
  batch_no INT NOT NULL DEFAULT 1,          -- バッチ連番（移送単位）
  quantity INT NOT NULL,
  status ENUM('WAITING','RUNNING','COMPLETED') NOT NULL DEFAULT 'WAITING',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_sched_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  CONSTRAINT fk_sched_order FOREIGN KEY (order_id) REFERENCES t_order(id),
  INDEX idx_sched_order (order_id),
  INDEX idx_sched_status (status)
) ENGINE=InnoDB;

-- ============================================================
-- 運用ルール・補足説明
-- ============================================================
-- 【DAY工程の日内位置】
--   - time_unit='DAY' の工程は「その日の作業終了時刻(planned_end=営業日末)」に完了したものとして扱う
--   - 複数DAY工程が同日に収まる場合は step_no 順で"並べる"（開始=前ステップ完了の直後）
--   - MINUTE工程と混在する場合は、MINUTE工程の end に DAY工程の start をスナップさせる
--
-- 【時間単位の整合性】
--   - time_unit='DAY' → lead_time_days > 0 必須
--   - time_unit='MINUTE' → duration_min > 0 または m_cycle_time から算出必須
--
-- 【調達整合性】
--   - sourcing_type='BUY' または 'SUBCON' の場合、supplier_id は NOT NULL (CHECK制約で保証)
--   - sourcing_type='MAKE' の場合、supplier_id は NULL
--
-- 【サイクルタイム参照】
--   - m_routing_step_output.output_product_id を基準に m_cycle_time を参照
--   - 所要時間 = setup_time_min + (cycle_time_sec × 数量 / 60)
