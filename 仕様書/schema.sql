-- schema.sql  段階BOM＋セル工程・時間運用＋ライン/購買LT (v3統合版)

-- 文字セット設定
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- タイムゾーン設定（日本時間）
SET time_zone = '+09:00';

-- 1) Products
CREATE TABLE m_product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_code VARCHAR(30) NOT NULL UNIQUE,
  product_name VARCHAR(100) NOT NULL,
  product_name_halfwidth VARCHAR(100) NULL,
  category VARCHAR(20) NULL,
  unit VARCHAR(10) NOT NULL DEFAULT '個',
  standard_lt_days INT NULL,
  image_url VARCHAR(255) NULL,
  line_id BIGINT NULL,
  process_id BIGINT NULL,
  management_unit VARCHAR(10) NULL,
  self_lt_days INT NULL,
  is_final_product TINYINT(1) NOT NULL DEFAULT 0,
  is_line_final_product TINYINT(1) NOT NULL,
  is_phantom TINYINT(1) NOT NULL DEFAULT 0,
  is_virtual_set TINYINT(1) NOT NULL,
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
CREATE TABLE m_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  line_code VARCHAR(20) NOT NULL UNIQUE,
  line_name VARCHAR(50) NOT NULL,
  calendar_id BIGINT NULL,
  lead_time_days INT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE m_process (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  process_code VARCHAR(20) NOT NULL UNIQUE,
  process_name VARCHAR(50) NOT NULL,
  line_id BIGINT NULL,
  is_outsource TINYINT(1) NOT NULL DEFAULT 0,
  management_unit VARCHAR(10) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_process_line FOREIGN KEY (line_id) REFERENCES m_line(id)
) ENGINE=InnoDB;

ALTER TABLE m_product
  ADD CONSTRAINT fk_product_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  ADD CONSTRAINT fk_product_process FOREIGN KEY (process_id) REFERENCES m_process(id);

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
  output_product_id BIGINT NULL,
  hierarchy_path VARCHAR(100) NOT NULL,
  hierarchy_depth INT NOT NULL,
  step_type ENUM('FLOW','PARALLEL_POOL') NOT NULL DEFAULT 'FLOW',
  time_unit ENUM('DAY','MINUTE') NOT NULL DEFAULT 'DAY',
  lead_time_days INT NOT NULL DEFAULT 0,
  start_offset_min INT NULL,
  duration_min INT NULL,
  parallel_count INT NOT NULL,
  parallel_group INT NOT NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_rstep_routing FOREIGN KEY (routing_id) REFERENCES m_routing(id),
  CONSTRAINT fk_rstep_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_rstep_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_rstep_output_product FOREIGN KEY (output_product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_rstep (routing_id, step_no, parallel_group)
) ENGINE=InnoDB;

CREATE TABLE m_routing_step_material (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  routing_step_id BIGINT NOT NULL,
  component_id BIGINT NOT NULL,
  quantity DECIMAL(12,3) NOT NULL,
  consume_timing VARCHAR(10) NOT NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_rstepmat_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  CONSTRAINT fk_rstepmat_component FOREIGN KEY (component_id) REFERENCES m_product(id),
  UNIQUE KEY uk_rstepmat (routing_step_id, component_id)
) ENGINE=InnoDB;

CREATE TABLE m_routing_step_param (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  routing_step_id BIGINT NOT NULL,
  lot_size INT NULL,
  transfer_batch_qty INT NULL,
  start_trigger ENUM('on_first_unit','on_transfer_batch','on_complete') NOT NULL DEFAULT 'on_transfer_batch',
  target_buffer_qty INT NULL,
  max_buffer_qty INT NULL,
  buffer_before_min INT NULL,
  buffer_after_min INT NULL,
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
  yield_rate DECIMAL(5,3) NULL,
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

CREATE TABLE m_process_cycle_time (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_id BIGINT NOT NULL,
  process_id BIGINT NOT NULL,
  line_id BIGINT NULL,
  cycle_time_min DECIMAL(10,2) NOT NULL,
  setup_time_min INT NOT NULL,
  lot_size INT NOT NULL,
  is_active TINYINT(1) NOT NULL,
  valid_from DATE NULL,
  valid_to DATE NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_pct_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_pct_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_pct_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  UNIQUE KEY uk_pct (product_id, process_id, line_id, valid_from)
) ENGINE=InnoDB;

-- 6) BOM
CREATE TABLE m_bom (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_product_id BIGINT NOT NULL,
  version VARCHAR(20) NOT NULL DEFAULT 'v1',
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  is_coproduct TINYINT(1) NOT NULL,
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
  process_id BIGINT NULL,
  line_id BIGINT NULL,
  time_unit VARCHAR(10) NOT NULL,
  lead_time_days INT NOT NULL,
  duration_min INT NULL,
  remark VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_bi_bom FOREIGN KEY (bom_id) REFERENCES m_bom(id),
  CONSTRAINT fk_bi_child FOREIGN KEY (child_product_id) REFERENCES m_product(id),
  CONSTRAINT fk_bi_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_bi_line FOREIGN KEY (line_id) REFERENCES m_line(id),
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

CREATE TABLE m_work_pattern (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  pattern_code VARCHAR(20) NOT NULL UNIQUE,
  pattern_name VARCHAR(50) NOT NULL,
  start_time TIME(6) NOT NULL,
  end_time TIME(6) NULL,
  description LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE m_break_time (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  work_pattern_id BIGINT NOT NULL,
  break_start TIME(6) NOT NULL,
  break_end TIME(6) NOT NULL,
  `order` INT NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_break_time_work_pattern FOREIGN KEY (work_pattern_id) REFERENCES m_work_pattern(id)
) ENGINE=InnoDB;

CREATE TABLE m_calendar_day (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  calendar_id BIGINT NOT NULL,
  target_date DATE NOT NULL,
  is_working_day TINYINT(1) NOT NULL,
  work_minutes INT NULL,
  work_pattern_id BIGINT NULL,
  note VARCHAR(100) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_cday_calendar FOREIGN KEY (calendar_id) REFERENCES m_calendar(id),
  CONSTRAINT fk_cday_work_pattern FOREIGN KEY (work_pattern_id) REFERENCES m_work_pattern(id),
  UNIQUE KEY uk_cday (calendar_id, target_date)
) ENGINE=InnoDB;

-- Add FK constraint for m_line.calendar_id
ALTER TABLE m_line
  ADD CONSTRAINT fk_line_calendar FOREIGN KEY (calendar_id) REFERENCES m_calendar(id);

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
  product_name VARCHAR(100) NULL,
  product_name_halfwidth VARCHAR(100) NULL,
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
  product_name VARCHAR(100) NULL,
  product_name_halfwidth VARCHAR(100) NULL,
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

-- 11) Line backlog (transactional)
CREATE TABLE line_backlog (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  plan_date DATE NOT NULL,
  line_id BIGINT NOT NULL,
  process_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  source_line_id BIGINT NULL,
  source_routing_step_id BIGINT NULL,
  plan_id VARCHAR(255) NULL,
  sequence_no INT NULL,
  demand_qty_plan INT NOT NULL,
  order_qty INT NOT NULL,
  plan_qty INT NOT NULL,
  actual_qty INT NOT NULL,
  actual_shipment_qty INT NOT NULL,
  adjust_qty INT NOT NULL,
  scrap_qty INT NOT NULL,
  stock_qty INT NOT NULL,
  planned_stock_qty INT NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_backlog_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_backlog_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_backlog_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_backlog_source_line FOREIGN KEY (source_line_id) REFERENCES m_line(id),
  CONSTRAINT fk_backlog_source_step FOREIGN KEY (source_routing_step_id) REFERENCES m_routing_step(id),
  UNIQUE KEY uniq_backlog_date_process_product_line (plan_date, process_id, product_id, line_id),
  INDEX idx_backlog_date_line (plan_date, line_id),
  INDEX idx_backlog_plan_id (plan_id)
) ENGINE=InnoDB;

-- 12) Line demand / gantt / realtime / status
CREATE TABLE t_line_demand (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  line_id BIGINT NOT NULL,
  routing_step_id BIGINT NULL,
  product_id BIGINT NULL,
  product_code VARCHAR(50) NOT NULL,
  plan_date DATE NOT NULL,
  lead_time_days INT NOT NULL,
  forecast_qty DECIMAL(14,3) NOT NULL,
  firm_qty DECIMAL(14,3) NOT NULL,
  plan_qty DECIMAL(14,3) NOT NULL,
  actual_qty DECIMAL(14,3) NOT NULL,
  plan_progress DECIMAL(9,3) NOT NULL,
  actual_progress DECIMAL(9,3) NOT NULL,
  order_numbers VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_linedemand_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_linedemand_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  CONSTRAINT fk_linedemand_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_line_demand (line_id, product_code, plan_date),
  INDEX idx_line_demand_line_date (line_id, plan_date),
  INDEX idx_line_demand_product (product_code)
) ENGINE=InnoDB;

CREATE TABLE t_line_gantt_plan (
  plan_id VARCHAR(160) PRIMARY KEY,
  plan_date DATE NOT NULL,
  plan_qty DECIMAL(14,3) NOT NULL,
  sequence_no INT NULL,
  start_datetime DATETIME(6) NOT NULL,
  end_datetime DATETIME(6) NOT NULL,
  processes_plan JSON NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  line_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  CONSTRAINT fk_gantt_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_gantt_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  INDEX idx_gantt_line_date (line_id, plan_date)
) ENGINE=InnoDB;

CREATE TABLE t_line_realtime_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  timestamp DATETIME(6) NOT NULL,
  record_type VARCHAR(20) NOT NULL,
  qty DECIMAL(10,3) NOT NULL,
  equipment_state VARCHAR(20) NULL,
  event_data JSON NULL,
  batch_no VARCHAR(100) NULL,
  operator_name VARCHAR(50) NULL,
  remarks LONGTEXT NULL,
  line_id BIGINT NOT NULL,
  product_id BIGINT NULL,
  product_code VARCHAR(50) NULL,
  product_name VARCHAR(100) NULL,
  CONSTRAINT fk_line_rt_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_line_rt_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  INDEX idx_line_rt_line_ts (line_id, timestamp),
  INDEX idx_line_rt_record_type (record_type),
  INDEX idx_line_rt_product_code (product_code)
) ENGINE=InnoDB;

CREATE TABLE t_line_status (
  line_id BIGINT PRIMARY KEY,
  current_state VARCHAR(20) NOT NULL,
  today_output DECIMAL(10,3) NOT NULL,
  today_plan DECIMAL(10,3) NOT NULL,
  current_product_code VARCHAR(50) NULL,
  current_product_name VARCHAR(100) NULL,
  last_update DATETIME(6) NOT NULL,
  CONSTRAINT fk_line_status_line FOREIGN KEY (line_id) REFERENCES m_line(id)
) ENGINE=InnoDB;

CREATE TABLE t_process_realtime_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_code VARCHAR(50) NULL,
  product_name VARCHAR(100) NULL,
  timestamp DATETIME(6) NOT NULL,
  record_type VARCHAR(20) NOT NULL,
  qty DECIMAL(10,3) NOT NULL,
  equipment_state VARCHAR(20) NULL,
  event_data JSON NULL,
  batch_no VARCHAR(100) NULL,
  operator_name VARCHAR(50) NULL,
  remarks LONGTEXT NULL,
  process_id BIGINT NOT NULL,
  product_id BIGINT NULL,
  CONSTRAINT fk_proc_rt_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_proc_rt_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  INDEX idx_proc_rt_process_ts (process_id, timestamp),
  INDEX idx_proc_rt_record_type (record_type),
  INDEX idx_proc_rt_product_code (product_code)
) ENGINE=InnoDB;

-- 13) Production / inventory / actual / scrap
CREATE TABLE t_stock_allocation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  location VARCHAR(50) NOT NULL,
  current_stock DECIMAL(14,3) NOT NULL,
  reserved_qty DECIMAL(14,3) NOT NULL,
  min_stock_qty DECIMAL(14,3) NOT NULL,
  is_bottleneck TINYINT(1) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  product_id BIGINT NOT NULL,
  CONSTRAINT fk_stock_alloc_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  UNIQUE KEY uk_stock_alloc (product_id, location),
  INDEX idx_stock_alloc_product (product_id),
  INDEX idx_stock_alloc_bottleneck (is_bottleneck)
) ENGINE=InnoDB;

CREATE TABLE t_production_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_no VARCHAR(50) NOT NULL UNIQUE,
  order_qty DECIMAL(14,3) NOT NULL,
  scheduled_start_date DATE NOT NULL,
  scheduled_end_date DATE NOT NULL,
  actual_start_date DATE NULL,
  actual_end_date DATE NULL,
  status VARCHAR(20) NOT NULL,
  priority INT NOT NULL,
  remark LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  line_id BIGINT NULL,
  product_id BIGINT NOT NULL,
  routing_id BIGINT NULL,
  allocation_id BIGINT NULL,
  CONSTRAINT fk_prod_order_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_prod_order_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_prod_order_routing FOREIGN KEY (routing_id) REFERENCES m_routing(id),
  CONSTRAINT fk_prod_order_allocation FOREIGN KEY (allocation_id) REFERENCES t_stock_allocation(id),
  INDEX idx_prod_order_status (status),
  INDEX idx_prod_order_start (scheduled_start_date),
  INDEX idx_prod_order_product (product_id),
  INDEX idx_prod_order_line (line_id)
) ENGINE=InnoDB;

CREATE TABLE t_process_actual (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  completed_qty DECIMAL(14,3) NOT NULL,
  actual_duration_min INT NOT NULL,
  completed_at DATETIME(6) NOT NULL,
  operator VARCHAR(50) NULL,
  remark LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  line_id BIGINT NOT NULL,
  process_id BIGINT NOT NULL,
  routing_step_id BIGINT NOT NULL,
  production_order_id BIGINT NOT NULL,
  CONSTRAINT fk_actual_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_actual_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_actual_step FOREIGN KEY (routing_step_id) REFERENCES m_routing_step(id),
  CONSTRAINT fk_actual_order FOREIGN KEY (production_order_id) REFERENCES t_production_order(id),
  INDEX idx_actual_order_step (production_order_id, routing_step_id),
  INDEX idx_actual_completed (completed_at),
  INDEX idx_actual_process (process_id),
  INDEX idx_actual_line (line_id)
) ENGINE=InnoDB;

CREATE TABLE t_scrap_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_code VARCHAR(50) NULL,
  product_name VARCHAR(100) NULL,
  qty DECIMAL(14,3) NOT NULL,
  recorded_at DATETIME(6) NOT NULL,
  reason VARCHAR(100) NULL,
  batch_no VARCHAR(100) NULL,
  operator_name VARCHAR(50) NULL,
  remarks LONGTEXT NULL,
  line_id BIGINT NULL,
  process_id BIGINT NULL,
  product_id BIGINT NULL,
  reason_detail VARCHAR(200) NULL,
  is_replenished TINYINT(1) NOT NULL,
  process_record_id BIGINT NULL,
  replenished_at DATETIME(6) NULL,
  replenished_by VARCHAR(50) NULL,
  decided_at DATETIME(6) NULL,
  decided_by VARCHAR(50) NULL,
  disposition_status VARCHAR(20) NOT NULL,
  return_qty DECIMAL(14,3) NOT NULL,
  plan_date DATE NULL,
  CONSTRAINT fk_scrap_line FOREIGN KEY (line_id) REFERENCES m_line(id),
  CONSTRAINT fk_scrap_process FOREIGN KEY (process_id) REFERENCES m_process(id),
  CONSTRAINT fk_scrap_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_scrap_process_record FOREIGN KEY (process_record_id) REFERENCES t_process_realtime_record(id),
  UNIQUE KEY uk_scrap_process_record (process_record_id),
  INDEX idx_scrap_process_time (process_id, recorded_at),
  INDEX idx_scrap_line_time (line_id, recorded_at),
  INDEX idx_scrap_product_code (product_code),
  INDEX idx_scrap_plan_date (plan_date)
) ENGINE=InnoDB;

CREATE TABLE t_scrap_record_detail (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  product_code VARCHAR(50) NULL,
  product_name VARCHAR(100) NULL,
  process_id BIGINT NULL,
  line_id BIGINT NULL,
  supplier_id BIGINT NULL,
  sourcing_type VARCHAR(20) NULL,
  deduct_qty DECIMAL(14,3) NOT NULL,
  is_replenished TINYINT(1) NOT NULL,
  replenished_at DATETIME(6) NULL,
  replenished_by VARCHAR(50) NULL,
  product_id BIGINT NULL,
  scrap_record_id BIGINT NOT NULL,
  CONSTRAINT fk_scrap_detail_product FOREIGN KEY (product_id) REFERENCES m_product(id),
  CONSTRAINT fk_scrap_detail_record FOREIGN KEY (scrap_record_id) REFERENCES t_scrap_record(id),
  INDEX idx_scrap_detail_product_code (product_code)
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
--   - m_routing_step.output_product_id を基準に m_cycle_time を参照
--   - 所要時間 = setup_time_min + (cycle_time_sec × 数量 / 60)
