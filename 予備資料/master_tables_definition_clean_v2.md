# 生産管理システム マスタテーブル定義（清書版・最新版）

本ドキュメントは、量産・日単位管理・工程統合モデルに基づき、\
必要最小限で安定稼働できる **マスタテーブル構成の正式版** です。\
構成マスタ（BOM）の画面情報を精査し、「親数 /
自数」を含む正しいモデルとして再整理済み。

------------------------------------------------------------------------

# 1. 製品マスタ `m_product`

製品（品番）の基本情報。

  カラム名                  型                                    説明
  ------------------------- ------------------------------------- --------------------------------------
  id                        BIGINT PK                             内部ID
  product_code              VARCHAR(30) UNIQUE                    品番
  product_name              VARCHAR(100)                          品名
  product_type              ENUM('集合','単体','材料','購入品')   品番区分
  unit                      VARCHAR(10)                           単位
  daily_target_qty          INT                                   標準日産数（量産用）
  standard_lt_days          INT                                   完成品としての標準リードタイム（日）
  self_lt_days              INT                                   親品番に対する生産リードタイム（日）
  is_final_product          TINYINT(1)                            最終製品フラグ
  is_active                 TINYINT(1)                            有効/無効
  created_at / updated_at   DATETIME                              

------------------------------------------------------------------------

# 2. 得意先マスタ `m_customer`

  カラム名                  型                   説明
  ------------------------- -------------------- --------------
  id                        BIGINT PK            
  customer_code             VARCHAR(20) UNIQUE   
  customer_name             VARCHAR(100)         
  short_name                VARCHAR(40)          
  calendar_id               BIGINT FK            工場カレンダ
  is_active                 TINYINT(1)           
  created_at / updated_at   DATETIME             

------------------------------------------------------------------------

# 3. 工程マスタ `m_process`

  カラム名                  型                   説明
  ------------------------- -------------------- ------------
  id                        BIGINT PK            
  process_code              VARCHAR(20) UNIQUE   
  process_name              VARCHAR(50)          
  is_outsource              TINYINT(1)           外作工程か
  default_line_id           BIGINT FK            標準ライン
  is_active                 TINYINT(1)           
  created_at / updated_at   DATETIME             

------------------------------------------------------------------------

# 4. ラインマスタ `m_line`

  カラム名                  型                   説明
  ------------------------- -------------------- ------
  id                        BIGINT PK            
  line_code                 VARCHAR(20) UNIQUE   
  line_name                 VARCHAR(50)          
  is_active                 TINYINT(1)           
  created_at / updated_at   DATETIME             

------------------------------------------------------------------------

# 5. ルーティング（工程順序）

## 5.1 ルーティングヘッダ `m_routing`

  カラム名                  型            説明
  ------------------------- ------------- ------
  id                        BIGINT PK     
  product_id                BIGINT FK     
  routing_code              VARCHAR(30)   
  description               TEXT          
  is_default                TINYINT(1)    
  is_active                 TINYINT(1)    
  created_at / updated_at   DATETIME      

## 5.2 ルーティング工程明細 `m_routing_step`

  カラム名                  型             説明
  ------------------------- -------------- ----------------
  id                        BIGINT PK      
  routing_id                BIGINT FK      
  step_no                   INT            工程順序
  process_id                BIGINT FK      
  line_id                   BIGINT FK      
  lead_time_days            INT            日単位の工程LT
  remark                    VARCHAR(200)   
  created_at / updated_at   DATETIME       

------------------------------------------------------------------------

# 6. 構成（BOM）マスタ

## 6.1 BOMヘッダ `m_bom`

  カラム名                  型            説明
  ------------------------- ------------- --------
  id                        BIGINT PK     
  parent_product_id         BIGINT FK     親品番
  version                   VARCHAR(20)   
  valid_from                DATE          
  valid_to                  DATE NULL     
  is_active                 TINYINT(1)    
  created_at / updated_at   DATETIME      

------------------------------------------------------------------------

## 6.2 BOM明細 `m_bom_item`

  カラム名                  型              説明
  ------------------------- --------------- --------
  id                        BIGINT PK       
  bom_id                    BIGINT FK       
  child_product_id          BIGINT FK       子品番
  parent_qty                DECIMAL(12,3)   親数
  self_qty                  DECIMAL(12,3)   自数
  seq_no                    INT             表示順
  remark                    VARCHAR(200)    
  created_at / updated_at   DATETIME        

------------------------------------------------------------------------

# 7. カレンダ（工場カレンダ）

## 7.1 `m_calendar`

  カラム名                  型            説明
  ------------------------- ------------- ------
  id                        BIGINT PK     
  calendar_code             VARCHAR(20)   
  calendar_name             VARCHAR(50)   
  description               TEXT          
  created_at / updated_at   DATETIME      

## 7.2 `m_calendar_day`

  カラム名                  型             説明
  ------------------------- -------------- -------------
  id                        BIGINT PK      
  calendar_id               BIGINT FK      
  target_date               DATE           
  is_working_day            TINYINT(1)     稼働日/休日
  note                      VARCHAR(100)   
  created_at / updated_at   DATETIME       

------------------------------------------------------------------------

# 8. ユーザー

（Django標準 auth_user を使用）

------------------------------------------------------------------------
9. 従業員マスタ：m_employee

現段階ではシンプルでOK。

カラム名	型	説明
id	BIGINT PK	
employee_code	VARCHAR(20)	社員コード
employee_name	VARCHAR(50)	氏名
belong_dept	VARCHAR(50)	部署
default_line_id	BIGINT FK	所属ライン（任意）
is_active	TINYINT(1)	
created_at / updated_at	DATETIME	

# ✔ まとめ

-   「親数 × 自数」に対応\
-   品番区分は m_product に一元化\
-   BOM は正規化済みで矛盾ゼロ\
-   量産・日単位スケジューリングに最適化済み
