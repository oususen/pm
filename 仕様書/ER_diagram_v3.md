# ER 図（Mermaid, v3.1 / ENUM値明記）

## ⚠️ 購買ラインの is_active について

`m_line` で `line_type='PURCHASE'` のラインは **意図的に `is_active=0`** で作成されます。
UIのライン選択に表示させないためであり、**使用中でも is_active=0 が正常**です。
削除前は必ず `m_routing_step` や `m_product` からの参照を確認してください。

```mermaid
erDiagram
    m_line {
      BIGINT id PK
      VARCHAR(20) line_code UNIQUE
      VARCHAR(50) line_name
      BIGINT calendar_id FK
      INT lead_time_days
      ENUM line_type "PROD,PURCHASE,OUTSOURCE,OTHER"
      TINYINT is_active "購買ラインは意図的に0"
      DATETIME created_at
      DATETIME updated_at
    }

    m_product {
      BIGINT id PK
      VARCHAR(30) product_code UNIQUE
      VARCHAR(100) product_name
      VARCHAR(100) product_name_halfwidth
      ENUM category "ASSEMBLY,SINGLE,MATERIAL,PURCHASED"
      VARCHAR(10) unit
      INT standard_lt_days
      INT self_lt_days
      TINYINT is_final_product
      TINYINT is_phantom
      TINYINT is_active
      DATETIME created_at
      DATETIME updated_at
    }

    m_customer {
      BIGINT id PK
      VARCHAR(20) customer_code UNIQUE
      VARCHAR(100) customer_name
      VARCHAR(40) short_name
      BIGINT calendar_id FK
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
      ENUM sourcing_type "MAKE,BUY,SUBCON"
      BIGINT supplier_id
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    m_routing_step {
      BIGINT id PK
      BIGINT routing_id FK
      INT step_no
      BIGINT process_id FK
      BIGINT line_id FK
      BIGINT output_product_id FK
      ENUM time_unit "DAY,MINUTE"
      INT lead_time_days
      INT start_offset_min
      INT duration_min
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    t_schedule_detail {
      BIGINT id PK
      BIGINT order_id
      BIGINT routing_step_id FK
      DATETIME planned_start
      DATETIME planned_end
      INT batch_no
      INT quantity
      ENUM status "WAITING,RUNNING,COMPLETED"
      DATETIME created_at
      DATETIME updated_at
    }

    t_order {
      BIGINT id PK
      BIGINT customer_id FK
      VARCHAR(50) order_no
      ENUM order_type "FIRM,FORECAST"
      VARCHAR(20) version_no
      DATE order_date
      VARCHAR(200) source_file
      ENUM status "PENDING,CONFIRMED,COMPLETED"
      DATETIME created_at
      DATETIME updated_at
    }

    t_order_line {
      BIGINT id PK
      BIGINT order_id FK
      INT line_no
      BIGINT product_id FK
      VARCHAR(50) product_code
      DECIMAL(14,3) quantity
      DATE due_date
      VARCHAR(20) plant_code
      VARCHAR(40) ship_to_code
      VARCHAR(200) remark
      DATETIME created_at
      DATETIME updated_at
    }

    stg_order_raw {
      BIGINT id PK
      VARCHAR(20) customer_code
      ENUM order_type "FIRM,FORECAST"
      VARCHAR(50) source_system
      VARCHAR(200) source_file
      INT source_row_no
      VARCHAR(50) record_token
      DATE start_month
      DATE due_date
      VARCHAR(50) product_code
      VARCHAR(100) product_name
      VARCHAR(100) product_name_halfwidth
      DECIMAL(14,3) quantity
      JSON raw_payload
      ENUM parse_status "PENDING,PARSED,ERROR"
      VARCHAR(200) error_message
      DATETIME created_at
      DATETIME updated_at
    }

    stg_order_daily {
      BIGINT id PK
      BIGINT raw_id FK
      BIGINT customer_id FK
      ENUM order_type "FIRM,FORECAST"
      VARCHAR(20) version_no
      VARCHAR(50) product_code
      VARCHAR(100) product_name
      VARCHAR(100) product_name_halfwidth
      DATE due_date
      DECIMAL(14,3) quantity
      VARCHAR(20) plant_code
      VARCHAR(40) ship_to_code
      VARCHAR(50) source_system
      VARCHAR(200) source_file
      DATETIME created_at
      DATETIME updated_at
    }

    t_line_demand {
      BIGINT id PK
      BIGINT line_id FK
      BIGINT routing_step_id FK
      BIGINT product_id FK
      VARCHAR(50) product_code
      DATE plan_date
      INT lead_time_days
      DECIMAL(14,3) forecast_qty
      DECIMAL(14,3) firm_qty
      DECIMAL(14,3) plan_qty
      DECIMAL(14,3) actual_qty
      TEXT order_numbers
      DATETIME created_at
      DATETIME updated_at
    }

    line_backlog {
      BIGINT id PK
      BIGINT line_id FK
      BIGINT process_id FK
      BIGINT product_id FK
      DATE plan_date
      BIGINT source_line_id FK
      BIGINT source_routing_step_id FK
      BIGINT plan_id FK
      INT sequence_no
      DECIMAL(14,3) demand_qty_plan "需要計画数量"
      DECIMAL(14,3) order_qty "必要数量（最終ラインは受注、中間ラインは後工程からの引当）"
      DECIMAL(14,3) plan_qty "計画数量（生産予定）"
      DECIMAL(14,3) actual_qty "生産実績数量（このラインでの生産実績）"
      DECIMAL(14,3) actual_shipment_qty "出荷実績数量（後工程への引き渡し実績）"
      DECIMAL(14,3) adjust_qty "調整数量"
      DECIMAL(14,3) scrap_qty "仕損数量"
      DECIMAL(14,3) stock_qty "実在庫数量"
      DECIMAL(14,3) planned_stock_qty "計画在庫数量"
      DATETIME updated_at
    }

    m_customer }o--|| m_calendar : "calendar_id -> id"
    t_order }o--|| m_customer : "customer_id -> id"
    t_order_line }o--|| t_order : "order_id -> id"
    t_order_line }o--|| m_product : "product_id -> id"
    stg_order_daily }o--|| stg_order_raw : "raw_id -> id"
    stg_order_daily }o--|| m_customer : "customer_id -> id"
    t_line_demand }o--|| m_line : "line_id -> id"
    t_line_demand }o--|| m_product : "product_id -> id"
    t_line_demand }o--|| m_routing_step : "routing_step_id -> id"
    line_backlog }o--|| m_process : "process_id -> id"
    line_backlog }o--|| m_product : "product_id -> id"
    line_backlog }o--|| m_line : "line_id -> id"
    line_backlog }o--o| m_line : "source_line_id -> id"
    line_backlog }o--o| m_routing_step : "source_routing_step_id -> id"
```
