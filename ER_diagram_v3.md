# ER 図（Mermaid, v3.1 / ENUM値明記）
```mermaid
erDiagram
    m_product {
      BIGINT id PK
      VARCHAR(30) product_code UNIQUE
      VARCHAR(100) product_name
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

    m_customer }o--|| m_calendar : "calendar_id -> id"
```
