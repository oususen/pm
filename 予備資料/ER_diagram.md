# ER 図（Mermaid）
```mermaid
erDiagram
    m_product {
      BIGINT id PK
      VARCHAR(30) product_code UNIQUE
      VARCHAR(100) product_name
      VARCHAR(20) category
      VARCHAR(10) unit
      INT standard_lt_days
      INT self_lt_days
      TINYINT is_final_product
      TINYINT is_phantom
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_bom {
      BIGINT id PK
      BIGINT parent_product_id FK
      VARCHAR(20) version
      DATE valid_from
      DATE valid_to
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_bom_item {
      BIGINT id PK
      BIGINT bom_id FK
      BIGINT child_product_id FK
      DECIMAL(12,3) quantity
      DECIMAL(5,3) loss_rate
      ENUM sourcing_type
      BIGINT supplier_id
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    m_process {
      BIGINT id PK
      VARCHAR(20) process_code UNIQUE
      VARCHAR(50) process_name
      TINYINT is_outsource
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_line {
      BIGINT id PK
      VARCHAR(20) line_code UNIQUE
      VARCHAR(50) line_name
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_line_default {
      BIGINT line_id PK/FK
      INT default_lt_days
    }

    m_line_product_lt {
      BIGINT line_id PK/FK
      BIGINT product_id PK/FK
      INT lt_days
    }

    m_routing {
      BIGINT id PK
      BIGINT product_id FK
      VARCHAR(30) routing_code
      TEXT description
      TINYINT is_default
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_routing_step {
      BIGINT id PK
      BIGINT routing_id FK
      INT step_no
      BIGINT process_id FK
      BIGINT line_id FK
      INT start_offset_min
      INT duration_min
      INT lead_time_days
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    m_routing_step_output {
      BIGINT id PK
      BIGINT routing_step_id FK
      BIGINT output_product_id FK
      DECIMAL(5,3) yield_rate
      TINYINT is_final_stage
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    m_routing_step_param {
      BIGINT id PK
      BIGINT routing_step_id FK
      INT lot_size
      INT transfer_batch_qty
      ENUM start_trigger
      INT target_buffer_qty
      INT max_buffer_qty
      INT daily_time_window_min
      DATETIME created_at
      DATETIME updated_at
    }

    m_cycle_time {
      BIGINT id PK
      BIGINT product_id FK
      BIGINT process_id FK
      BIGINT line_id FK
      DECIMAL(10,2) cycle_time_sec
      DECIMAL(10,2) setup_time_min
      DATE valid_from
      DATE valid_to
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_supplier {
      BIGINT id PK
      VARCHAR(20) supplier_code UNIQUE
      VARCHAR(100) supplier_name
    }

    m_supplier_item {
      BIGINT supplier_id PK/FK
      BIGINT product_id PK/FK
      INT purchase_lt_days
      INT min_lot
      INT order_cycle_days
    }

    m_calendar {
      BIGINT id PK
      VARCHAR(20) calendar_code UNIQUE
      VARCHAR(50) calendar_name
      TEXT description
      DATETIME created_at
      DATETIME updated_at
    }

    m_calendar_day {
      BIGINT id PK
      BIGINT calendar_id FK
      DATE target_date
      TINYINT is_working_day
      INT work_minutes
      VARCHAR(100) note
      DATETIME created_at
      DATETIME updated_at
    }

    m_bom }o--|| m_product : "parent_product_id -> id"
    m_bom_item }o--|| m_bom : "bom_id -> id"
    m_bom_item }o--|| m_product : "child -> id"
    m_bom_item }o..o{ m_supplier : "supplier_id -> id"

    m_routing }o--|| m_product : "product_id -> id"
    m_routing_step }o--|| m_routing : "routing_id -> id"
    m_routing_step }o--|| m_process : "process_id -> id"
    m_routing_step }o--|| m_line : "line_id -> id"
    m_routing_step_param }o--|| m_routing_step : "routing_step_id -> id"
    m_routing_step_output }o--|| m_routing_step : "routing_step_id -> id"
    m_routing_step_output }o--|| m_product : "output_product_id -> id"

    m_cycle_time }o--|| m_product : "product_id -> id"
    m_cycle_time }o--|| m_process : "process_id -> id"
    m_cycle_time }o--|| m_line : "line_id -> id"

    m_line_default }o--|| m_line : "line_id -> id"
    m_line_product_lt }o--|| m_line : "line_id -> id"
    m_line_product_lt }o--|| m_product : "product_id -> id"

    m_calendar_day }o--|| m_calendar : "calendar_id -> id"
```
